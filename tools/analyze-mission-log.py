#!/usr/bin/env python3
"""Summarize APXREC mission observations from a WOTC log or report ZIP.

The report describes recorded observations. It does not replay the game or infer
hidden enemy actions, unobserved damage, or why a mission was lost.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

MAX_LOG_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 32
MAX_RECORDS = 100000
KEY = re.compile(r'^[a-z_][a-z0-9_]*$')
INTEGER = re.compile(r'^-?\d+$')
DECIMAL = re.compile(r'^-?\d+(?:\.\d+)?$')
SCORING_SPEC = importlib.util.spec_from_file_location(
    'apx_game_scoring', Path(__file__).with_name('game_scoring.py'))
SCORING = importlib.util.module_from_spec(SCORING_SPEC)
SCORING_SPEC.loader.exec_module(SCORING)


def decode_log(data: bytes) -> str:
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16', errors='replace')
    return data.decode('utf-8-sig', errors='replace')


def read_logs(path: Path) -> list[tuple[str, str]]:
    if not zipfile.is_zipfile(path):
        if path.stat().st_size > MAX_LOG_BYTES:
            raise ValueError('Log exceeds the 128 MiB analysis limit.')
        return [(path.name, decode_log(path.read_bytes()))]
    logs = []
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ARCHIVE_ENTRIES:
            raise ValueError('Report ZIP has too many entries.')
        total = 0
        names = set()
        for entry in entries:
            relative = PurePosixPath(entry.filename.replace('\\', '/'))
            if relative.is_absolute() or '..' in relative.parts or ':' in str(relative):
                raise ValueError('Unsafe ZIP entry path.')
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('ZIP symbolic links are not supported.')
            key = str(relative).casefold()
            if key in names:
                raise ValueError('Duplicate ZIP entry name.')
            names.add(key)
            total += entry.file_size
            if entry.file_size > MAX_LOG_BYTES or total > MAX_ARCHIVE_BYTES:
                raise ValueError('Report ZIP exceeds the analysis size limit.')
            if not entry.is_dir() and relative.suffix.casefold() == '.log':
                logs.append((str(relative), decode_log(archive.read(entry))))
    if not logs:
        raise ValueError('Report ZIP contains no .log files.')
    return logs


def typed_value(key: str, value: str):
    # IDs and sequence numbers are integers; keep the session identifier literal.
    if key == 'session':
        return value
    if value.casefold() in ('true', 'false'):
        return value.casefold() == 'true'
    if INTEGER.fullmatch(value):
        return int(value)
    if DECIMAL.fullmatch(value):
        return float(value)
    return value


def parse_record(line: str) -> dict | None:
    marker = line.find('APXREC|')
    if marker < 0:
        return None
    fields = {}
    for fragment in line[marker + len('APXREC|'):].strip().split('|'):
        if '=' not in fragment:
            raise ValueError('incomplete key=value record')
        key, value = fragment.split('=', 1)
        if not KEY.fullmatch(key) or key in fields:
            raise ValueError('invalid or duplicate record field')
        fields[key] = typed_value(key, value)
    if fields.get('v') != 1:
        raise ValueError('unsupported recording version')
    if not fields.get('session') or not isinstance(fields.get('seq'), int):
        raise ValueError('missing session or sequence')
    if not isinstance(fields.get('event'), str) or not fields['event']:
        raise ValueError('missing event name')
    return fields


def action_family(ability: str) -> str:
    # Unreal FName comparisons are case insensitive; its displayed spelling can
    # be inherited from the first name interned by the engine (e.g. overwatch).
    ability = ability.casefold()
    if ability in {'overwatch', 'pistoloverwatch', 'sniperrifleoverwatch', 'longwatch'}:
        return 'overwatch'
    if ability == 'hunkerdown':
        return 'hunker'
    if ability in {'throwgrenade', 'launchgrenade'}:
        return 'grenade'
    if ability in {'evac', 'placeevaczone'}:
        return 'evacuation'
    if ability == 'reload':
        return 'reload'
    if ability == 'aidprotocol':
        return 'support'
    return 'other'


def marker_details(record: dict) -> dict[str, str]:
    """Read a marker's inline key/value diagnostics; never treat as a dispatch."""
    return dict(re.findall(r'\b([a-z_]+)=([^\s]+)', str(record.get('details', ''))))


def summarize_grenade_preparation(records: list[dict]) -> dict:
    """A rejected *preview* is not a chosen/engine-rejected grenade."""
    rejected = [r for r in records
                if (r['event'] == 'marker'
                    and r.get('kind') == 'area_revalidation_rejected')]
    reasons = Counter()
    for record in rejected:
        details = marker_details(record)
        reasons[details.get('reason') or details.get('evaluation_reason') or 'unspecified'] += 1
    return {'preview_rejections': len(rejected),
            'reasons': dict(sorted(reasons.items()))}


def summarize_end_turn(records: list[dict]) -> dict:
    """Match real turn tickets; a native false with later evidence is success.

    An unconfirmed marker represents an expired wait, not proof of a native
    rejection. The same ticket may be confirmed later, so do not count both
    as separate failed end-turn submissions.
    """
    relevant = {'end_turn_requested', 'end_turn_confirmed', 'end_turn_unconfirmed'}
    requests = {}
    totals = Counter()
    evidence = Counter()
    for record in records:
        if record['event'] != 'marker' or record.get('kind') not in relevant:
            continue
        kind = record['kind']
        totals[kind] += 1
        details = marker_details(record)
        key = (details.get('player'), details.get('turn'))
        if not all(k is not None and k.lstrip('-').isdigit() for k in key):
            totals['missing_ticket_identity'] += 1
            continue
        if kind == 'end_turn_requested':
            if key in requests and not requests[key]['confirmed']:
                totals['repeat_requests'] += 1
            requests[key] = {'confirmed': False, 'unconfirmed': False,
                             'native_false': details.get('native_return', '').casefold() == 'false'}
        elif key not in requests:
            totals['orphan_' + kind.removeprefix('end_turn_')] += 1
        elif kind == 'end_turn_unconfirmed':
            requests[key]['unconfirmed'] = True
        else:
            if not requests[key]['confirmed']:
                requests[key]['confirmed'] = True
                if requests[key]['native_false']:
                    totals['native_false_confirmed'] += 1
                if requests[key]['unconfirmed']:
                    totals['confirmed_after_timeout'] += 1
                evidence[details.get('evidence') or 'unspecified'] += 1

    totals['unresolved_after_timeout'] = sum(
        ticket['unconfirmed'] and not ticket['confirmed'] for ticket in requests.values())
    totals['pending_without_confirmation'] = sum(
        not ticket['confirmed'] for ticket in requests.values())
    return {
        'requested': totals['end_turn_requested'],
        'confirmed': totals['end_turn_confirmed'],
        'unconfirmed_markers': totals['end_turn_unconfirmed'],
        'native_false_confirmed': totals['native_false_confirmed'],
        'confirmed_after_timeout': totals['confirmed_after_timeout'],
        'unresolved_after_timeout': totals['unresolved_after_timeout'],
        'pending_without_confirmation': totals['pending_without_confirmation'],
        'repeat_requests': totals['repeat_requests'],
        'orphan_confirmed': totals['orphan_confirmed'],
        'orphan_unconfirmed': totals['orphan_unconfirmed'],
        'missing_ticket_identity': totals['missing_ticket_identity'],
        'evidence': dict(sorted(evidence.items())),
    }


def summarize_session(session: str, records: list[dict], conflicting_records: bool = False) -> dict:
    records.sort(key=lambda item: item['seq'])
    events = Counter(record['event'] for record in records)
    chosen = [record for record in records if record['event'] == 'chosen']
    accepted = [record for record in chosen if record.get('accepted') is True]
    abilities = Counter(str(record.get('ability', 'unknown')) for record in accepted
                        if record.get('kind') not in {'move', 'explore'})
    families = Counter(action_family(ability) for ability, count in abilities.items()
                       for _ in range(count))
    result_frames = [record for record in records if record['event'] == 'result']
    interrupted = [record for record in result_frames
                   if str(record.get('interruption', '')).casefold() == 'einterruptionstatus_interrupt']
    # Interrupt contexts precede resolution and can carry a default hit enum.
    # Count the resumed/completed context, not that provisional frame, as a roll.
    results = [record for record in result_frames
               if str(record.get('interruption', '')).casefold() != 'einterruptionstatus_interrupt']
    hit_results = Counter(str(record.get('hit', 'unknown')) for record in results)
    known_friendly_ids = {record['id'] for record in records
                          if record['event'] == 'unit' and record.get('scope') == 'friendly'
                          and 'id' in record}
    known_enemy_ids = {record['id'] for record in records
                       if record['event'] == 'unit' and record.get('scope') == 'visible_enemy'
                       and 'id' in record}

    def source_scope(record):
        explicit = record.get('source_scope')
        if explicit in {'friendly', 'visible_enemy', 'unseen_other'}:
            return explicit
        # Older recorder revisions lack scope fields. Only classify recorded
        # IDs, never assume that redacted source=0 identifies a hostile unit.
        if record.get('source') in known_friendly_ids:
            return 'friendly'
        if record.get('source') in known_enemy_ids:
            return 'visible_enemy'
        return 'unknown'

    results_by_source = {}
    for result in results:
        results_by_source.setdefault(source_scope(result), Counter())[str(result.get('hit', 'unknown'))] += 1
    confirmed_eliminations = set()
    for result in records:
        if result['event'] not in {'result', 'result_target'}:
            continue
        before, after = result.get('target_hp_before'), result.get('target_hp_after')
        target = result.get('target', 0)
        if (not isinstance(before, (int, float)) or not isinstance(after, (int, float))
                or before <= 0 or after > 0 or not isinstance(target, int) or target <= 0):
            continue
        scope = 'unknown'
        if target in known_friendly_ids:
            scope = 'friendly'
        elif target in known_enemy_ids:
            scope = 'visible_enemy'
        confirmed_eliminations.add((scope, target))
    observed_losses = Counter()
    deaths = set()
    last_units = {}
    for record in records:
        if record['event'] != 'unit' or 'id' not in record:
            continue
        unit = (str(record.get('scope', 'unknown')), record['id'])
        previous = last_units.get(unit)
        if previous:
            if isinstance(previous.get('hp'), (int, float)) and isinstance(record.get('hp'), (int, float)):
                observed_losses[unit[0]] += max(0, previous['hp'] - record['hp'])
            if previous.get('alive') is True and record.get('alive') is False:
                deaths.add(unit)
        last_units[unit] = record
    sequences = [record['seq'] for record in records]
    sequence_gaps = sum(max(0, right - left - 1) for left, right in zip(sequences, sequences[1:]))
    start = next((record for record in records if record['event'] == 'start'), {})
    ends = [record for record in records if record['event'] == 'end']
    outcome = ends[-1].get('outcome', 'unknown') if ends else 'unknown'
    failure_evidence = SCORING.objective_failure_evidence(records)
    critical_failures = failure_evidence['critical_failed_objective_ids']
    weak_shots = [record for record in accepted if isinstance(record.get('chance'), (int, float))
                  and 0 <= record['chance'] < 35]
    unsupported = Counter(str(record.get('ability', 'unknown')) for record in records
                          if record['event'] == 'unsupported'
                          or (record['event'] == 'candidate' and record.get('kind') in {'unsupported', 'unhandled'})
                          or (record['event'] == 'ability' and record.get('handler') == 'unhandled'
                              and str(record.get('code', '')).casefold() == 'aa_success'
                              and record.get('input') is True))
    grenade_scans = [record for record in records if record['event'] == 'marker'
                     and record.get('kind') == 'grenade_scan']
    grenade_totals = Counter()
    grenade_reasons = Counter()
    for scan in grenade_scans:
        fields = dict(re.findall(r'\b([a-z_]+)=([^\s]+)', str(scan.get('details', ''))))
        for key in ('available', 'supported', 'evaluated', 'accepted', 'edge_centers',
                    'range', 'visibility', 'visualizer', 'trajectory', 'blast', 'targets', 'score', 'unsupported',
                    'single_opportunities', 'single_rejected'):
            if fields.get(key, '').isdecimal():
                grenade_totals[key] += int(fields[key])
        for key in ('range_reason', 'blast_reason'):
            reason = fields.get(key)
            if reason and reason != 'none':
                grenade_reasons[reason] += 1
    grenade_preparation = summarize_grenade_preparation(records)
    end_turn = summarize_end_turn(records)
    warnings = []
    if end_turn['unresolved_after_timeout']:
        warnings.append(
            f"{end_turn['unresolved_after_timeout']} end-turn request(s) timed out without later confirmation; "
            "this is not proof of a native rejection.")
    if end_turn['orphan_confirmed'] or end_turn['orphan_unconfirmed']:
        warnings.append('End-turn evidence without a matching recorded request; report may be incomplete.')
    if conflicting_records:
        warnings.append('Objective failure observations cannot be verified because recording records conflict.')
    elif critical_failures:
        warnings.append('A verified native critical objective failed, regardless of mission points.')
    if not conflicting_records and failure_evidence['unclassified_failed_objective_ids']:
        warnings.append('A failed objective was observed, but its criticality is unverified.')
    if not start:
        warnings.append('Recording starts mid-session; the start record is missing.')
    if not ends:
        warnings.append('No end record; mission outcome is unknown and the recording may be incomplete.')
    elif str(outcome).casefold() not in {'win', 'loss'}:
        warnings.append('The recorder ended without a confirmed native mission result; outcome remains unknown.')
    if sequence_gaps:
        warnings.append(f'{sequence_gaps} sequence numbers missing; observations are incomplete.')
    if events['limit']:
        warnings.append('Recorder reached its configured record limit.')
    if ends and isinstance(ends[-1].get('history_pending'), int) and ends[-1]['history_pending'] > 0:
        warnings.append(f"{ends[-1]['history_pending']} history frames remain unrecorded; action results are incomplete.")
    return {
        'session': session,
        'mission': start.get('mission', 'unknown'),
        'difficulty': start.get('difficulty', 'unknown'),
        'outcome': outcome,
        'critical_objective_failed': None if conflicting_records else bool(critical_failures),
        'objective_failure_evidence_status': 'conflicting_records' if conflicting_records else 'recorded',
        **failure_evidence,
        'events': dict(sorted(events.items())),
        'accepted_actions': len(accepted),
        'rejected_actions': sum(record.get('accepted') is False for record in chosen),
        'abilities': dict(sorted(abilities.items())),
        'action_families': dict(sorted(families.items())),
        'moves': sum(record.get('kind') in {'move', 'explore'} for record in accepted),
        'hit_results': dict(sorted(hit_results.items())),
        'hit_results_by_source': {scope: dict(sorted(counts.items()))
                                  for scope, counts in sorted(results_by_source.items())},
        'interrupted_result_frames': len(interrupted) + events['interrupted'],
        'recorded_misses': sum(count for hit, count in hit_results.items()
                               if hit.casefold() in {'miss', 'ehit_miss'}),
        'recorded_misses_by_source': {
            scope: sum(count for hit, count in counts.items() if hit.casefold() in {'miss', 'ehit_miss'})
            for scope, counts in sorted(results_by_source.items())},
        'visibility_loss_events': events['visibility_lost'],
        'observed_hp_loss': dict(sorted(observed_losses.items())),
        'observed_deaths': dict(sorted(Counter(scope for scope, _ in deaths).items())),
        'confirmed_target_eliminations': dict(sorted(Counter(scope for scope, _ in confirmed_eliminations).items())),
        'low_chance_actions': weak_shots,
        'unsupported_abilities': dict(sorted(unsupported.items())),
        'grenade_diagnostics': {'scans': len(grenade_scans), 'totals': dict(sorted(grenade_totals.items())),
                                'reason_observations': dict(sorted(grenade_reasons.items()))},
        'grenade_preparation': grenade_preparation,
        'end_turn_diagnostics': end_turn,
        'warnings': warnings,
        'records': records,
    }


def analyze_logs(logs: list[tuple[str, str]]) -> dict:
    sessions = {}
    malformed = []
    seen = {}
    conflicting_sessions = set()
    duplicate_count = 0
    record_count = 0
    for filename, content in logs:
        for number, line in enumerate(content.splitlines(), 1):
            try:
                record = parse_record(line)
            except ValueError as error:
                malformed.append({'file': filename, 'line': number, 'reason': str(error)})
                continue
            if record is None:
                continue
            record_count += 1
            if record_count > MAX_RECORDS:
                raise ValueError('Recording exceeds the analysis record limit.')
            key = (record['session'], record['seq'])
            if key in seen:
                duplicate_count += 1
                if seen[key] != record:
                    conflicting_sessions.add(record['session'])
                    malformed.append({'file': filename, 'line': number,
                                      'reason': 'conflicting record with same session and sequence'})
                continue
            seen[key] = record.copy()
            record['log_file'] = filename
            record['log_line'] = number
            sessions.setdefault(record['session'], []).append(record)
    native_profiles = SCORING.native_rule_snapshots(logs)
    comparison_profile = SCORING.load_profile()
    summaries = []
    for name, records in sorted(sessions.items()):
        summary = summarize_session(name, records, name in conflicting_sessions)
        summary['game_scoring'] = SCORING.score_session(
            records, SCORING.native_rules_for_session(records, native_profiles), comparison_profile)
        summary['attempt_verdict'] = SCORING.assess_attempt(
            records, summary['outcome'], summary['game_scoring'], name in conflicting_sessions)
        # Point value is always present per mission, but the status says
        # whether that value is a final score or only a provisional reading.
        verdict = summary['attempt_verdict']
        value = verdict['score'] if verdict['score'] is not None else verdict['observed_score']
        summary['mission_points'] = {
            'value': value, 'confirmed': verdict['score'] is not None,
            'source': verdict['score_source'], 'status': verdict['score_status'],
        }
        summaries.append(summary)
    return {
        'format_version': 1,
        'input_logs': [name for name, _ in logs],
        'record_count': len(seen),
        'duplicate_records': duplicate_count,
        'malformed_records': malformed,
        'sessions': summaries,
        'native_scoring_profiles': native_profiles,
        'attempt_criterion': SCORING.ATTEMPT_CRITERION,
        'limitations': [
            'Observed HP losses are changes between snapshots, not a complete damage ledger.',
            'Enemy snapshots contain only player-visible contacts; disappearance is not a confirmed kill.',
            'Candidate scores describe planner preferences, not proven reasons for victory or defeat.',
            'Missing logs or end markers do not establish a mission result.',
            'Accepted actions are autoplay submissions; result records include friendly reactions and incoming actions too.',
            'Result hit enums include non-attack abilities; they are not a weapon accuracy percentage.',
            'Comparison points use one game-derived profile with explicit conventions; missing components prevent a final total.',
            'Native score snapshots are authoritative observations; initialization MaxScore is not earned score.',
            'Attempt acceptance uses the recorded terminal mission contribution; later debrief awards are not reconstructed.',
        ],
    }


def human_summary(report: dict) -> str:
    lines = [f"APXREC records: {report['record_count']}; sessions: {len(report['sessions'])}"]
    for session in report['sessions']:
        points = session['mission_points']
        if points['value'] is None:
            points_label = 'unknown (not recorded)'
        elif points['confirmed']:
            points_label = f"{points['value']:+d} (confirmed, {points['source']})"
        else:
            points_label = f"{points['value']:+d} (provisional, {points['status']}, {points['source']})"
        lines.append(f"Session {session['session']}: mission={session['mission']}, "
                     f"difficulty={session['difficulty']}, outcome={session['outcome']}, "
                     f"mission points={points_label}")
        if session['objective_failure_evidence_status'] == 'conflicting_records':
            lines.append('  Objective failure evidence is unverified because recording records conflict.')
        elif session['critical_objective_failed']:
            lines.append('  CRITICAL OBJECTIVE FAILURE: '
                         + ', '.join(session['critical_failed_objective_ids'])
                         + '; any positive or provisional points cannot pass.')
        if (session['objective_failure_evidence_status'] != 'conflicting_records'
                and session['unclassified_failed_objective_ids']):
            lines.append('  Objective failure observed (criticality unverified): '
                         + ', '.join(session['unclassified_failed_objective_ids']))
        lines.append(f"  Accepted actions={session['accepted_actions']}, moves={session['moves']}, "
                     f"recorded misses={session['recorded_misses']}")
        if session['recorded_misses_by_source']:
            lines.append('  Misses by source: ' + ', '.join(
                f'{scope}={count}' for scope, count in session['recorded_misses_by_source'].items()))
        families = session['action_families']
        lines.append('  ' + ', '.join(f'{name}={families.get(name, 0)}'
                                     for name in ['overwatch', 'hunker', 'grenade', 'reload', 'support', 'evacuation']))
        if session['unsupported_abilities']:
            lines.append('  Recorded unsupported abilities: ' + ', '.join(session['unsupported_abilities']))
        if session['grenade_diagnostics']['scans']:
            totals = session['grenade_diagnostics']['totals']
            lines.append('  Grenade scan checks: ' + ', '.join(
                f'{key}={totals.get(key, 0)}' for key in ('supported', 'evaluated', 'accepted', 'range', 'trajectory', 'blast')))
        preparation = session['grenade_preparation']
        if preparation['preview_rejections']:
            lines.append(f"  Grenade preparation rejected before dispatch={preparation['preview_rejections']}; "
                         "reasons=" + ', '.join(f"{reason}:{count}" for reason, count in preparation['reasons'].items()))
        turns = session['end_turn_diagnostics']
        if turns['requested'] or turns['confirmed'] or turns['unconfirmed_markers']:
            lines.append(f"  End turns: requested={turns['requested']}, confirmed={turns['confirmed']}, "
                         f"timeout markers={turns['unconfirmed_markers']}, "
                         f"late confirmations={turns['confirmed_after_timeout']}, "
                         f"unresolved={turns['unresolved_after_timeout']}, "
                         f"native false but confirmed={turns['native_false_confirmed']}.")
        scoring = session['game_scoring']
        official = scoring['official']
        if official['status'] == 'observed_native':
            lines.append(f"  Observed native cumulative score={official['cumulative_score']}, "
                         f"recording delta={official['recording_delta']}; later end awards may be pending.")
        else:
            lines.append('  Native earned score was not recorded.')
        comparison = scoring['comparison']
        if comparison['observed_subtotal'] is not None:
            lines.append(f"  Comparison ({comparison['profile_id']}): {comparison['status']}, "
                         f"observed subtotal={comparison['observed_subtotal']}, total={comparison['total']}")
        else:
            lines.append(f"  Comparison ({comparison['profile_id']}): {comparison['status']}; "
                         'no award components could be reconstructed, total unavailable.')
        if comparison['missing_components']:
            lines.append('  Comparison incomplete: ' + ', '.join(comparison['missing_components']))
        verdict = session['attempt_verdict']
        lines.append(f"  Attempt assessment (victory and mission score > 0): {verdict['status'].upper()}; "
                     f"score={verdict['score']}, source={verdict['score_source']}, "
                     f"score status={verdict['score_status']}. {verdict['explanation']}")
        if verdict['score'] is None and verdict['observed_score'] is not None:
            lines.append(f"  Provisional observed mission points={verdict['observed_score']}; not a final acceptance score.")
        for warning in session['warnings']:
            lines.append('  Warning: ' + warning)
    if report['malformed_records']:
        lines.append(f"Warning: {len(report['malformed_records'])} malformed/conflicting records.")
    if not report['sessions']:
        lines.append('No APXREC mission recording found. Enable recording and use a newly compiled mod.')
    lines.append('This is an observation summary, not a replay or proof of tactical correctness.')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Launch.log or ZIP created by collect-mission-recording.ps1')
    parser.add_argument('--json', type=Path, help='Write detailed JSON report (refuses an existing file)')
    args = parser.parse_args()
    try:
        report = analyze_logs(read_logs(args.input))
        if args.json:
            with args.json.open('x', encoding='utf-8') as output:
                json.dump(report, output, ensure_ascii=False, indent=2)
                output.write('\n')
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    print(human_summary(report))
    return 0 if report['sessions'] else 1


if __name__ == '__main__':
    sys.exit(main())
