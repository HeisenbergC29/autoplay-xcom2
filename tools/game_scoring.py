"""Native score observations and an explicitly separate, game-derived benchmark.

The SDK's actual award routines are native. This module never claims that an
offline reconstruction is an official score, treats MaxScore as configuration,
and exposes incomplete observation coverage rather than inventing final totals.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re


PROFILE_PATH = Path(__file__).with_name('legacy-score-rules.json')
FIELD_NAMES = {
    'StartingPoints': 'starting_points', 'MinPoints': 'min_points',
    'DecreasePerTurn': 'decrease_per_turn', 'TurnOffset': 'turn_offset',
    'SpawnedPoints': 'spawned_points', 'ReinforcementPoints': 'reinforcement_points',
    'DisabledPoints': 'disabled_points', 'MinDisabledPoints': 'min_disabled_points',
    'UninjuredBonus': 'uninjured_bonus', 'WoundedBonus': 'survival_bonus',
    'RescuedCivilianBonus': 'rescued_bonus', 'NumSoldiers': 'num_soldiers',
    'NumCivilians': 'num_civilians', 'PointsPerInterval': 'points_per_interval',
    'IntervalInSeconds': 'interval_seconds', 'TimeLimit': 'time_limit',
    'TextPoolIndex': 'text_pool_index', 'GroupID': 'group_id', 'LineIndex': 'line_index',
}
RUNTIME_RULE_FIELDS = {
    'enemy': ('starting_points', 'min_points', 'decrease_per_turn', 'turn_offset',
              'spawned_points', 'reinforcement_points', 'disabled_points', 'min_disabled_points'),
    'objective': ('starting_points', 'min_points', 'decrease_per_turn', 'turn_offset',
                  'text_pool_index', 'group_id', 'line_index'),
    'soldier': ('uninjured_bonus', 'survival_bonus', 'rescued_bonus'),
    'time': ('points_per_interval', 'interval_seconds'),
}


def load_profile(path: Path | None = None) -> dict:
    profile = json.loads((path or PROFILE_PATH).read_text(encoding='utf-8'))
    if not profile.get('profile_id') or profile.get('is_official_game_score') is not False:
        raise ValueError('Comparison profile must be identified and explicitly unofficial.')
    return profile


def numeric_fields(text: str) -> dict:
    return {FIELD_NAMES[name]: int(value)
            for name, value in re.findall(r'([A-Za-z][A-Za-z0-9]*)\s*:\s*(-?\d+)', text)
            if name in FIELD_NAMES}


def native_rule_snapshots(logs: list[tuple[str, str]]) -> list[dict]:
    """Read only engine-labelled initialization tables, preserving boundaries."""
    profiles = []
    for filename, content in logs:
        current = None
        for number, line in enumerate(content.splitlines(), 1):
            if 'XCom_Challenge:' not in line:
                continue
            if 'ScoreType(0):' in line:
                if current:
                    profiles.append(current)
                current = None
            objective = re.search(r'MissionTypeObjectiveScoringValues\[MissionType:\s*([^\s\]]+)', line)
            if objective:
                mission = objective[1]
                if current is None or current['mission'] != mission:
                    if current:
                        profiles.append(current)
                    current = {'mission': mission, 'log_file': filename, 'log_line': number,
                               'objectives': [], 'enemies': {}, 'soldier': {}, 'time': {},
                               'initial_max_score': None}
                current['objectives'].append(numeric_fields(line))
            if current is None:
                continue
            objective_count = re.search(r'NumObjectives:\s*(\d+)', line)
            if objective_count:
                current['num_objectives'] = int(objective_count[1])
            enemy = re.search(r"Unit:\s*'([^']+)'\s+EnemyScoring\[([^]]+)\]", line)
            if enemy:
                rule = numeric_fields(enemy[2])
                previous = current['enemies'].get(enemy[1])
                if previous is not None and previous != rule:
                    current.setdefault('conflicting_enemy_templates', []).append(enemy[1])
                current['enemies'][enemy[1]] = rule
            soldier = re.search(r'SoldierScoring\[([^]]+)\]', line)
            if soldier:
                current['soldier'].update(numeric_fields(soldier[1]))
            time = re.search(r'TimeScoring\[([^]]+)\]', line)
            if time:
                current['time'].update(numeric_fields(time[1]))
                current['time'].update(numeric_fields(line[line.index('TimeScoring'):]))
            maximum = re.search(r'\bMaxScore:\s*(-?\d+)', line)
            if maximum:
                current['initial_max_score'] = int(maximum[1])
        if current:
            profiles.append(current)
    return profiles


def native_rules_for_session(records: list[dict], snapshots: list[dict]) -> dict | None:
    """Combine the matching startup table with this session's read-only getters.

    Keep every runtime observation so a later rule revision is not silently
    presented as the value used for an earlier award. These rules are evidence
    of configuration, never evidence of earned points or the comparison scale.
    """
    start = next((r for r in records if r['event'] == 'start'), {})
    candidates = [p for p in snapshots if p['mission'] == start.get('mission')
                  and p['log_file'] == start.get('log_file')
                  and p['log_line'] <= start.get('log_line', 0)]
    observed = [r for r in records if r['event'] == 'score_rule'
                and r.get('source') == 'legacy_runtime'
                and r.get('kind') in RUNTIME_RULE_FIELDS
                and (not r.get('mission') or r['mission'] == start.get('mission'))]
    if not candidates and not observed:
        return None
    rules = deepcopy(max(candidates, key=lambda p: p['log_line'])) if candidates else {
        'mission': start.get('mission'), 'objectives': [], 'enemies': {},
        'soldier': {}, 'time': {}, 'initial_max_score': None,
    }
    rules['observed_sources'] = ['engine_initialization_table'] if candidates else []
    rules['runtime_observations'] = []
    for event in observed:
        kind = event['kind']
        values = {name: event[name] for name in RUNTIME_RULE_FIELDS[kind]
                  if type(event.get(name)) is int}
        if not values:
            continue
        identity = {}
        if kind == 'enemy':
            template = event.get('template')
            if not isinstance(template, str) or not template:
                continue
            identity['template'] = template
            rules['enemies'].setdefault(template, {}).update(values)
        elif kind == 'objective':
            identity['objective_id'] = event.get('objective_id')
            key = tuple(values.get(name) for name in ('text_pool_index', 'group_id', 'line_index'))
            matching = next((rule for rule in rules['objectives']
                             if all(value is not None for value in key)
                             and tuple(rule.get(name) for name in ('text_pool_index', 'group_id', 'line_index')) == key), None)
            if matching is None:
                rules['objectives'].append(values.copy())
            else:
                matching.update(values)
        else:
            rules[kind].update(values)
        observation = {'kind': kind, **identity, **values,
                       'seq': event.get('seq'), 'history': event.get('history')}
        rules['runtime_observations'].append(observation)
    if rules['runtime_observations']:
        rules['observed_sources'].append('legacy_runtime_getters')
    return rules


def decayed_value(rule: dict, turn: int) -> int:
    """Declared benchmark convention; not a replacement for native awards."""
    elapsed = max(0, turn - int(rule['turn_offset']))
    return max(int(rule['min_points']),
               int(rule['starting_points']) - elapsed * int(rule['decrease_per_turn']))


def terminal_challenge_rollup(records: list[dict]) -> dict | None:
    """Bind an actual native total to a drained tactical end, never to a HUD.

    CMPT_TotalScore is a rollup, not another award to sum. Legacy's explicit
    mission-points/baseline contract retains priority over this fallback.
    """
    if any(r['event'] == 'game_score' and r.get('source') == 'legacy_runtime'
           for r in records):
        return None
    ends = [r for r in records if r['event'] == 'end']
    end = ends[-1] if ends else {}
    if (not isinstance(end.get('session'), str) or not end['session']
            or end.get('reason') != 'tactical_game_ended' or end.get('outcome') not in {'win', 'loss'}
            or type(end.get('history_pending')) is not int or end['history_pending'] != 0
            or type(end.get('history')) is not int or end['history'] < 0
            or type(end.get('seq')) is not int):
        return None
    starts = [r for r in records if r['event'] == 'start'
              and r.get('session') == end.get('session')
              and type(r.get('seq')) is int and r['seq'] < end['seq']]
    start = starts[-1] if starts else {}
    if type(start.get('history')) is not int or not 0 <= start['history'] <= end['history']:
        return None
    totals = [r for r in records if r['event'] == 'score_delta'
              and r.get('session') == end.get('session')
              and r.get('source') == 'game_runtime' and r.get('scoring_type') == 'CMPT_TotalScore'
              and type(r.get('score_id')) is int and r['score_id'] > 0
              and type(r.get('added_points')) is int and type(r.get('history')) is int
              and start['history'] <= r['history'] <= end['history']
              and type(r.get('seq')) is int and start['seq'] < r['seq'] < end['seq']]
    if not totals:
        return None
    values = sorted({r['added_points'] for r in totals})
    latest = max(totals, key=lambda r: (r['history'], r['seq']))
    # A later committed award can make an earlier rollup stale. Entries in
    # the same atomic history state may be emitted in either order.
    if any(r['event'] == 'score_delta' and r.get('session') == end.get('session')
           and r.get('source') == 'game_runtime'
           and r.get('scoring_type') not in {'CMPT_None', 'CMPT_TotalScore'}
           and type(r.get('history')) is int and latest['history'] < r['history'] <= end['history']
           and type(r.get('seq')) is int and start['seq'] < r['seq'] < end['seq']
           for r in records):
        return None
    return {'status': 'confirmed' if len(values) == 1 else 'conflicting',
            'source': 'native_total_score_rollup',
            'mission_points': values[0] if len(values) == 1 else None,
            'observed_totals': values, 'score_id': latest['score_id'],
            'history': latest['history'], 'seq': latest['seq'],
            'end_history': end['history'], 'end_seq': end['seq']}


def official_observations(records: list[dict]) -> dict:
    scores = [r for r in records if r['event'] == 'game_score'
              and r.get('source') == 'legacy_runtime'
              and isinstance(r.get('cumulative_score'), int)]
    deltas = [r for r in records if r['event'] == 'score_delta'
              and isinstance(r.get('added_points'), int)]
    unique_deltas = {}
    for event in deltas:
        # Native routines may revise a state object. Preserve each observed
        # history revision; deduplicate only repeat observations of that state.
        key = ((event['score_id'], event['history'])
               if 'score_id' in event and 'history' in event else ('seq', event['seq']))
        unique_deltas.setdefault(str(key), event)
    if not scores:
        rollup = terminal_challenge_rollup(records)
        return {'status': ('observed_native_rollup' if rollup['status'] == 'confirmed'
                           else 'conflicting_native_rollup') if rollup else 'not_recorded',
                'cumulative_score': None, 'recording_delta': None,
                'from_history': rollup['history'] if rollup else None,
                'to_history': rollup['end_history'] if rollup else None,
                'terminal_snapshot': bool(rollup and rollup['status'] == 'confirmed'),
                'terminal_rollup': rollup, 'score_events': list(unique_deltas.values())}
    first = scores[0]
    stage = (first.get('ladder_index'), first.get('ladder_rung'))
    same_stage_scores = [r for r in scores
                         if (r.get('ladder_index'), r.get('ladder_rung')) == stage]
    last = same_stage_scores[-1]
    anchored = first.get('phase') == 'start'
    return {'status': 'observed_native', 'source': 'legacy_runtime',
            'cumulative_score': last['cumulative_score'],
            'recording_delta': last['cumulative_score'] - first['cumulative_score'] if anchored else None,
            'from_history': first.get('history'), 'to_history': last.get('history'),
            'ladder_index': last.get('ladder_index'), 'ladder_rung': last.get('ladder_rung'),
            'terminal_snapshot': last.get('phase') in {'finish', 'end'},
            'other_stage_snapshots_ignored': len(scores) - len(same_stage_scores),
            'score_events': list(unique_deltas.values()),
            'limitation': 'The delta covers recording observations, not necessarily the whole mission. Observed native state does not prove that all later UI/end awards have been processed.'}


def comparison_score(records: list[dict], profile: dict) -> dict:
    """Apply the same frozen profile to scored and unscored missions.

    Only witnessed facts become components. Unknown eligibility, objectives or
    spawn origin are made explicit; no final total is invented from victory.
    """
    missing = set()
    assumptions = set()
    components = []
    unit_states = {}
    initially_friendly = set()
    eligible = set()
    eligibility_unknown = set()
    wounded = set()
    inferred_wounded = set()
    lost = set()
    enemy_seen_alive = set()
    first_scopes = {}
    eliminated = {}
    objective_ids = set()
    rescued_ids = set()
    first_phase_turn = None
    start = next((r for r in records if r['event'] == 'start'), {})
    ended = any(r['event'] == 'end' for r in records)
    profile_enemies = {name.casefold(): rule for name, rule in profile['enemies'].items()}

    def component(kind, value, **fields):
        components.append({'kind': kind, 'points': int(value), **fields})

    def eliminate(target, event, confirmed):
        if target in initially_friendly or target not in enemy_seen_alive:
            return
        previous = eliminated.get(target)
        explicit = event.get('turn')
        turn = explicit if isinstance(explicit, int) and explicit >= 0 else None
        if (previous is None or (confirmed and not previous[3])
                or (confirmed == previous[3] and previous[2] is None and turn is not None)):
            eliminated[target] = (event.copy(), unit_states.get(target, {}).copy(), turn, confirmed)

    for record in records:
        event = record['event']
        if event == 'phase' and first_phase_turn is None:
            # Recording after the first turn may omit earlier kills/objectives.
            if isinstance(record.get('turn'), int) and record['turn'] >= 0:
                first_phase_turn = record['turn']
        if event == 'unit' and isinstance(record.get('id'), int):
            target = record['id']
            previous = unit_states.get(target, {})
            state = {**previous, **record}
            first_scopes.setdefault(target, record.get('scope'))
            if record.get('scope') == 'friendly' and first_scopes[target] == 'friendly':
                initially_friendly.add(target)
                if state.get('score_eligible') is True:
                    eligible.add(target)
                    eligibility_unknown.discard(target)
                elif state.get('score_eligible') is False:
                    eligibility_unknown.discard(target)
                elif target not in eligible:
                    eligibility_unknown.add(target)
            elif record.get('scope') == 'visible_enemy' and record.get('alive') is True:
                enemy_seen_alive.add(target)
            if target in initially_friendly:
                hp, maximum = state.get('hp'), state.get('max_hp')
                high, low = state.get('highest_hp'), state.get('lowest_hp')
                if isinstance(high, (int, float)) and isinstance(low, (int, float)):
                    # Native mission HP history takes precedence over max HP:
                    # a soldier can enter this mission already injured.
                    inferred_wounded.discard(target)
                    if high > low:
                        wounded.add(target)
                elif (isinstance(hp, (int, float)) and isinstance(maximum, (int, float))
                      and hp < maximum):
                    inferred_wounded.add(target)
                # Bleeding out/incapacitated is not itself a confirmed death.
                if (record.get('alive') is False or record.get('ladder_killed_scored') is True
                        or (record.get('unconscious') is True and record.get('ladder_unkillable') is True)):
                    lost.add(target)
            unit_states[target] = state
            if (record.get('scope') == 'visible_enemy' and record.get('alive') is False
                    and previous.get('alive') is True):
                eliminate(target, record, True)
        elif event in {'result', 'result_target'}:
            before, after = record.get('target_hp_before'), record.get('target_hp_after')
            target = record.get('target')
            if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                if before > after and target in initially_friendly:
                    wounded.add(target)
                if before > 0 and after <= 0:
                    eliminate(target, record, record.get('target_alive_after') is False)
        elif event == 'objective_completed':
            identity = record.get('objective_id', record.get('objective_name'))
            if identity is None or str(identity) == '':
                missing.add('objective_identity')
            elif str(identity) not in objective_ids:
                objective_ids.add(str(identity))
                turn = record.get('completion_turn', record.get('turn'))
                if not isinstance(turn, int) or turn < 0:
                    missing.add('objective_completion_turn')
                else:
                    component('objective_completed', decayed_value(profile['objective'], turn),
                              objective_id=identity, turn=turn)
        elif event == 'civilian_rescued':
            identity = record.get('id', record.get('target', record.get('civilian_id')))
            # The owned rescuer's public event is deduplicated by the recorder
            # before the hidden civilian ID is redacted. No hidden ID is needed
            # to count that observed rescue exactly once.
            if identity == 0 and record.get('source') == 'mission_event' and isinstance(record.get('seq'), int):
                identity = ('recorded_rescue', record.get('session'), record['seq'])
            if identity is None or (isinstance(identity, int) and identity <= 0):
                missing.add('civilian_rescue_identity')
            elif identity not in rescued_ids:
                rescued_ids.add(identity)
                component('civilian_rescued', profile['civilian']['rescued_bonus'],
                          unit=identity if isinstance(identity, int) else None, event_seq=record.get('seq'))

    for target in sorted(eligible):
        # Retain the explicit v1 convention only for archived comparisons.
        # Native injury/loss weights do not establish an initial point award.
        if profile.get('initial_soldier_allowance', False):
            component('soldier_allowance', profile['soldier']['uninjured_bonus'] + profile['soldier']['survival_bonus'],
                      unit=target)
        if target in wounded or target in inferred_wounded:
            component('first_injury_penalty', -profile['soldier']['uninjured_bonus'], unit=target)
        if target in lost:
            component('soldier_loss_penalty', -profile['soldier']['survival_bonus'], unit=target)
    if eligibility_unknown:
        missing.add('soldier_score_eligibility')
    if (inferred_wounded - wounded) & (eligible | eligibility_unknown):
        missing.add('soldier_injury_history')
        assumptions.add('HP below max is provisional injury evidence when native mission HP history is absent; a pre-existing injury cannot be distinguished.')
    for target, (event, state, observed_turn, confirmed) in sorted(eliminated.items()):
        if not confirmed:
            missing.add('enemy_death_confirmation')
            continue
        template = state.get('template')
        if not template:
            missing.add('eliminated_enemy_template')
            continue
        rule = profile_enemies.get(str(template).casefold())
        rule_source = 'observed_runtime_template'
        if rule is None:
            rule = profile['enemy_default']
            rule_source = 'sdk_structure_default'
            assumptions.add('Unlisted enemy templates use the explicit SDK structure default, not an unobserved runtime override.')
            missing.add('enemy_runtime_override_not_observed')
        turn = observed_turn
        if not isinstance(turn, int) or turn < 0:
            missing.add('enemy_kill_turn')
            continue
        spawned, reinforced = state.get('spawned'), state.get('reinforcement')
        if spawned is True:
            value = rule['spawned_points']
            origin = 'spawned'
        elif reinforced is True:
            value = rule['reinforcement_points']
            origin = 'reinforcement'
        else:
            value = decayed_value(rule, turn)
            origin = 'ordinary' if spawned is False and reinforced is False else 'unrecorded_assumed_ordinary'
            if origin != 'ordinary':
                missing.add('enemy_spawn_reinforcement_origin')
        component('enemy_eliminated', value, unit=target, template=template, turn=turn,
                  rule_source=rule_source, origin=origin)

    # Explicit event coverage can establish that no completion/rescue events
    # were omitted; it cannot supply the native-only award algorithms.
    coverage = [r for r in records if r['event'] == 'scoring_coverage']
    complete_coverage = bool(coverage and coverage[-1].get('complete') is True)
    if not complete_coverage:
        missing.update({'objective_completion_coverage', 'civilian_rescue_coverage'})
    if not start:
        missing.add('recording_start')
    if not ended:
        missing.add('recording_end')
    if isinstance(first_phase_turn, int) and first_phase_turn > 1:
        missing.add('recording_started_after_first_turn')
    if any(r['event'] == 'limit' for r in records):
        missing.add('recorder_limit')
    sequences = [r['seq'] for r in records if isinstance(r.get('seq'), int)]
    if any(right > left + 1 for left, right in zip(sequences, sequences[1:])):
        missing.add('recording_sequence_gaps')
    if any(r['event'] == 'end' and isinstance(r.get('history_pending'), int)
           and r['history_pending'] > 0 for r in records):
        missing.add('pending_history_frames')
    if not unit_states:
        missing.add('unit_observations')
    # A witnessed eligible soldier with no scored events legitimately has zero
    # in the corrected profile. No observations still mean an unknown subtotal.
    subtotal = sum(entry['points'] for entry in components) if components or eligible else None
    return {'profile_id': profile['profile_id'], 'is_official_game_score': False,
            'status': 'partial' if missing else 'complete_for_comparison_convention',
            'observed_subtotal': subtotal, 'total': None if missing else subtotal,
            'components': components, 'scored_component_count': len(components),
            'missing_components': sorted(missing),
            'excluded_native_components': profile['excluded_native_components'],
            'observed_friendly_wounded': len(wounded | inferred_wounded), 'observed_friendly_losses': len(lost),
            'unknown_eligibility_units': sorted(eligibility_unknown),
            'assumptions': sorted(assumptions),
            'conventions': profile['comparison_conventions'],
            'provenance': profile['provenance']}


RUNTIME_V3_PROFILE = 'wotc_legacy_config_observed_v3_partial'
RUNTIME_V3_RATE_SOURCE = 'installed_ladder_config'


def runtime_observed_v3(records: list[dict]) -> dict:
    """Separate the v3 HUD observations from the frozen offline v2 rules.

    The runtime calls this profile partial. Installed rate tables, a native win,
    and a positive subtotal never prove event coverage or a final native score.
    Do not silently trust conflicting flags or incompatible rate attribution.
    """
    observations = [r for r in records if r.get('event') == 'hud_score'
                    and r.get('comparison_profile') == RUNTIME_V3_PROFILE]
    result = {
        'profile_id': RUNTIME_V3_PROFILE,
        'status': 'not_recorded' if not observations else 'partial',
        'rate_source': None,
        'native_parity_proven': False,
        'event_coverage_proven': False,
        'is_official_game_score': False,
        'observed_subtotal': None,
        'total': None,
        'observations': len(observations),
        'last_seq': None,
        'last_history': None,
        'missing_evidence': [],
    }
    if not observations:
        return result
    missing = {'native_rule_parity', 'complete_event_coverage', 'final_mission_score'}
    valid = []
    for entry in observations:
        if entry.get('rate_source') != RUNTIME_V3_RATE_SOURCE:
            missing.add('rate_source_missing_or_conflicting')
            continue
        if (entry.get('comparison_status') != 'partial'
                or entry.get('native_parity_proven') is not False
                or entry.get('event_coverage_proven') is not False):
            missing.add('partial_status_or_proof_flags_missing_or_conflicting')
            continue
        display = entry.get('display')
        value = (re.fullmatch(r'~(-?\d+)/[^\r\n|]+', display)
                 if isinstance(display, str) else None)
        if value is None:
            missing.add('unreadable_mod_hud_subtotal')
            continue
        valid.append((entry, int(value[1])))
    if valid and len(valid) == len(observations):
        last, subtotal = valid[-1]
        result.update(rate_source=RUNTIME_V3_RATE_SOURCE,
                      observed_subtotal=subtotal,
                      last_seq=last.get('seq'),
                      last_history=last.get('history'))
    else:
        missing.add('incomplete_runtime_v3_observations')
    result['missing_evidence'] = sorted(missing)
    return result


def score_session(records: list[dict], native_rules: dict | None = None,
                  profile: dict | None = None) -> dict:
    return {'official': official_observations(records),
            'comparison': comparison_score(records, profile or load_profile()),
            'runtime_observed_v3': runtime_observed_v3(records),
            'native_rules_observed': native_rules,
            'note': 'Planner candidate/chosen score and engine initialization MaxScore are not earned game points.'}


ATTEMPT_CRITERION = 'victory_and_positive_mission_score_v1'


def objective_failure_evidence(records: list[dict]) -> dict:
    """A failed UI checkbox does not identify a mandatory mission objective.

    Only an explicit boolean critical marker carries the recorder's verified
    native failure contract. Missing/unknown/false markers remain observations.
    """
    failures = [record for record in records if record['event'] == 'objective_failed']
    all_ids = {str(record.get('objective_id', 'unknown')) for record in failures}
    critical_ids = {str(record.get('objective_id', 'unknown')) for record in failures
                    if record.get('critical') is True}
    return {'failed_objective_ids': sorted(all_ids),
            'critical_failed_objective_ids': sorted(critical_ids),
            'unclassified_failed_objective_ids': sorted(all_ids - critical_ids)}


def assess_attempt(records: list[dict], outcome: str, scoring: dict,
                   conflicting_records: bool = False) -> dict:
    """Keep the native winner separate from the project's acceptance criterion.

    Ladder cumulative points and recorder-start deltas are not mission totals.
    A partial benchmark or an old HUD reading can describe an observation, but
    cannot establish that the final mission score was positive.
    """
    ends = [record for record in records if record['event'] == 'end']
    end = ends[-1] if ends else {}
    official = scoring['official']
    native_records = [record for record in records
                      if record['event'] == 'game_score'
                      and record.get('source') in {'legacy_runtime', 'challenge_runtime'}]
    if official['status'] == 'observed_native':
        stage = (official.get('ladder_index'), official.get('ladder_rung'))
        native_records = [record for record in native_records
                          if record.get('source') != 'legacy_runtime'
                          or (record.get('ladder_index'), record.get('ladder_rung')) == stage]
    native_hud = []
    for record in records:
        if record['event'] != 'hud_score' or record.get('comparison_profile'):
            continue
        match = re.fullmatch(r'(-?\d+)/(?:-?\d+|[^\d/]+)', str(record.get('display', '')))
        if match:
            native_hud.append((record, int(match[1])))

    score, observed_score, source, score_status, profile = None, None, None, 'not_recorded', None
    complete = False
    rollup = official.get('terminal_rollup')
    if rollup and not native_records:
        source = 'native_mission_points'
        complete = rollup['status'] == 'confirmed'
        score_status = 'final_native_observation' if complete else 'conflicting_native_totals'
        if complete:
            score = observed_score = rollup['mission_points']
    elif native_records or native_hud or official['status'] == 'observed_native':
        source = 'native_mission_points'
        if native_records:
            last = native_records[-1]
            if last.get('mission_points_known') is True and type(last.get('mission_points')) is int:
                observed_score = last['mission_points']
                # An explicit final marker comes from a source-backed terminal
                # read, never from the sign or stability of a cumulative score.
                complete = (last.get('mission_final') is True
                            and last.get('phase') in {'finish', 'end'}
                            and bool(end) and last.get('seq', 0) <= end.get('seq', -1)
                            and type(last.get('history')) is int and last['history'] >= 0
                            and type(end.get('history')) is int
                            and last['history'] == end['history']
                            and type(end.get('history_pending')) is int
                            and end['history_pending'] == 0)
                score_status = 'final_native_observation' if complete else 'partial_native_observation'
        if observed_score is None and native_hud and not official.get('other_stage_snapshots_ignored'):
            observed_score = native_hud[-1][1]
            source, score_status = 'native_hud_observation', 'partial_native_observation'
        if complete:
            score = observed_score
    elif scoring.get('runtime_observed_v3', {}).get('status') == 'partial':
        # Real v3 HUD provenance supersedes the archived OFFLINE v2
        # reconstruction, but never certifies a final mission total.
        runtime_v3 = scoring['runtime_observed_v3']
        source, profile = 'mod_observed_v3', runtime_v3['profile_id']
        observed_score = runtime_v3['observed_subtotal']
        score_status = 'partial_mod_observation'
    else:
        comparison = scoring['comparison']
        source, profile = 'comparison', comparison['profile_id']
        observed_score = comparison['observed_subtotal']
        complete = (profile == 'wotc_legacy_observed_v2'
                    and comparison['status'] == 'complete_for_comparison_convention'
                    and type(comparison['total']) is int)
        score_status = 'complete_comparison' if complete else 'partial_comparison'
        if complete:
            score = comparison['total']

    failure_evidence = objective_failure_evidence(records)
    critical_failures = failure_evidence['critical_failed_objective_ids']
    result = {'criterion': ATTEMPT_CRITERION, 'status': 'unknown',
              'mission_outcome': outcome, 'score': score, 'observed_score': observed_score,
              'score_source': source, 'score_status': score_status,
              'score_complete': complete, 'score_profile': profile,
              'critical_objective_failed': None if conflicting_records else bool(critical_failures),
              'objective_failure_evidence_status': 'conflicting_records' if conflicting_records else 'recorded',
              'failed_objectives': failure_evidence['failed_objective_ids'],
              'critical_failed_objectives': critical_failures}
    normalized = str(outcome).casefold()
    if conflicting_records:
        result.update(score=None, score_complete=False, score_status='conflicting_records',
                      reason='conflicting_records',
                      explanation='Conflicting recording observations prevent a reliable acceptance verdict.')
    elif critical_failures:
        # A required mission objective failed. Neither a later positive HUD
        # observation nor a missing terminal event can make this a PASS.
        result.update(status='fail', reason='critical_objective_failed',
                      explanation='A native mission objective failed; the attempt is a critical failure regardless of score.')
    elif normalized == 'loss':
        result.update(status='fail', reason='mission_lost',
                      explanation='The game recorded a defeat; positive points alone cannot pass the attempt.')
    elif normalized != 'win':
        result.update(reason='mission_outcome_unknown',
                      explanation='A confirmed mission victory has not been recorded.')
    elif not complete:
        result.update(reason='mission_score_incomplete',
                      explanation='The game recorded a victory, but the final mission score is unavailable or incomplete.')
    elif score <= 0:
        result.update(status='fail', reason='mission_score_not_positive',
                      explanation='The game recorded a victory, but the mission score is not greater than zero.')
    else:
        result.update(status='pass', reason='victory_with_positive_mission_score',
                      explanation='The game recorded a victory and a mission score greater than zero.')
    return result
