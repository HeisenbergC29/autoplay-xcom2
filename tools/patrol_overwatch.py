"""Attribute completed XCOM Overwatch reservations to their recorded patrol and player turn."""

from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from operator import itemgetter
import re


OVERWATCH_SHOTS = {'overwatchshot', 'pistoloverwatchshot', 'longwatchshot'}
OVERWATCH_STANCES = {'overwatch', 'pistoloverwatch', 'sniperrifleoverwatch', 'longwatch'}
TRACKED_ABILITIES = OVERWATCH_SHOTS | OVERWATCH_STANCES | {'pistolreturnfire'}
HISTORY = itemgetter(0)


def native_index(value):
    """Return a nonnegative native turn/history index, rejecting booleans and missing values."""
    return value if type(value) is int and value >= 0 else -1


def roster_ids(value):
    """Decode the recorder's bounded local ObjectIDs. None signals a malformed snapshot."""
    if value == 'none':
        return set()
    parts = str(value).split(',')
    if len(parts) > 256 or not all(re.fullmatch(r'[1-9][0-9]{0,9}', part) for part in parts):
        return None
    ids = {int(part) for part in parts}
    return ids if len(ids) == len(parts) and max(ids) <= 2147483647 else None


def is_pause(row):
    """Recognize explicit loss of autoplay control in marker and phase records."""
    return ((row['event'] == 'marker' and row.get('kind') == 'autoplay_stop')
            or (row['event'] == 'phase' and row.get('phase') == 'manual'))


@dataclass
class Evidence:
    """Indexes for native result time, observer control, missing frames and cursor progress."""

    frames: dict = field(default_factory=lambda: defaultdict(list))
    uncertain: dict = field(default_factory=lambda: defaultdict(set))
    pauses: dict = field(default_factory=lambda: defaultdict(list))
    unlocated_pauses: dict = field(default_factory=dict)
    arm_histories: dict = field(default_factory=lambda: defaultdict(list))
    controls: list = field(default_factory=list)
    drains: list = field(default_factory=list)
    gaps: list = field(default_factory=list)
    terminal_cursor: int = -1


def collect_evidence(records):
    """Index frames by native history so deferred emission does not change attribution."""
    evidence = Evidence()
    drains = {}
    for row in records:
        event = row['event']
        turn = native_index(row.get('turn'))
        history = native_index(row.get('history'))
        seq = row['seq']
        if event == 'end' and native_index(row.get('history_pending')) == 0 and row.get('reason') == 'tactical_game_ended':
            evidence.terminal_cursor = max(evidence.terminal_cursor, history)
        if is_pause(row):
            if history >= 0:
                evidence.pauses[turn].append((history, seq))
            else:
                evidence.unlocated_pauses[turn] = max(evidence.unlocated_pauses.get(turn, -1), seq)
        if event == 'phase' and history >= 0 and row.get('phase') in ('autoplay', 'decision', 'manual'):
            evidence.controls.append((history, seq, row['phase']))
        if event == 'patrol_history_gap':
            first, last = native_index(row.get('first')), native_index(row.get('last'))
            if 0 <= first <= last:
                evidence.gaps.append((first, last))
        if event == 'result' or event == 'patrol_drain' or (
                event == 'phase' and history <= native_index(row.get('history_drained'))):
            if history >= 0 and turn >= 0:
                drains[turn] = min(drains.get(turn, history), history)
        if event != 'result' or str(row.get('interruption', '')).casefold() == 'einterruptionstatus_interrupt':
            continue
        ability = str(row.get('ability', '')).casefold()
        group_eliminated = (row.get('source_scope') == 'friendly'
                            and native_index(row.get('target_group')) > 0
                            and native_index(row.get('patrol_targets_remaining')) == 0)
        if ability not in TRACKED_ABILITIES and not group_eliminated:
            continue
        if row.get('source_scope') in ('visible_enemy', 'unseen_other'):
            continue
        unit = native_index(row.get('source'))
        if history < 0 or turn < 0:
            evidence.uncertain[turn].add(unit)
            continue
        evidence.frames[turn].append((history, seq, row))
        if ability in OVERWATCH_STANCES and row.get('source_scope') == 'friendly':
            evidence.arm_histories[turn, unit].append(history)
    for rows in evidence.frames.values():
        rows.sort(key=itemgetter(0, 1))
    for rows in evidence.pauses.values():
        rows.sort()
    for histories in evidence.arm_histories.values():
        histories.sort()
    evidence.controls.sort()
    evidence.drains = sorted(drains.items())
    # Native cursor reports missing ranges in forward order. The log can merge backups.
    evidence.gaps = merge_gaps(evidence.gaps)
    return evidence


def merge_gaps(gaps):
    """Merge overlapping history gaps for logarithmic intersection checks per window."""
    merged = []
    for first, last in sorted(gaps):
        if merged and first <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(last, merged[-1][1]))
        else:
            merged.append((first, last))
    return merged


def window_boundary(window, following_history, evidence):
    """Return inclusive last history, reason for an early cutoff and the presence of an undated pause."""
    history, seq, turn = native_index(window.get('history')), window['seq'], native_index(window.get('turn'))
    later = bisect_right(evidence.drains, turn, key=HISTORY)
    cutoff = evidence.drains[later][1] - 1 if later < len(evidence.drains) else None
    if cutoff is None and evidence.terminal_cursor >= history:
        cutoff = evidence.terminal_cursor
    boundary = None
    if following_history is not None and (cutoff is None or following_history <= cutoff):
        cutoff, boundary = following_history, 'next_patrol_window'
    unlocated = False
    for scope in {turn, -1}:
        pauses = evidence.pauses.get(scope, ())
        first = bisect_right(pauses, (history, seq))
        if first < len(pauses) and (cutoff is None or pauses[first][0] <= cutoff):
            cutoff, boundary = pauses[first][0], 'autoplay_stopped'
        unlocated |= evidence.unlocated_pauses.get(scope, -1) >= seq
    return cutoff, boundary, unlocated


def manually_armed(roster, turn, history, evidence):
    """Identify armed soldiers whose latest recorded stance on this turn was taken in a manual phase."""
    manual = []
    for unit in sorted(roster):
        arms = evidence.arm_histories.get((turn, unit), ())
        end = bisect_right(arms, history)
        if end:
            before = bisect_right(evidence.controls, arms[end - 1], key=HISTORY)
            if before and evidence.controls[before - 1][2] == 'manual':
                manual.append(unit)
    return manual


@dataclass
class Volley:
    """Independent observations used to count unique soldiers and distinguish reaction sources."""

    fired: set = field(default_factory=set)
    seen: set = field(default_factory=set)
    rearmed: set = field(default_factory=set)
    ambiguous: set = field(default_factory=set)
    other_targets: set = field(default_factory=set)
    other_reserve: set = field(default_factory=set)
    hits: Counter = field(default_factory=Counter)
    targets_killed: set = field(default_factory=set)
    last_target_death: int | None = None


def observe_frame(row, group, roster, volley):
    """Credit a resolved shot only for the original reserve, source and positively identified patrol."""
    ability = str(row.get('ability', '')).casefold()
    target = native_index(row.get('target'))
    if row.get('source_scope') == 'friendly' and target > 0 and row.get('target_group') == group:
        if (row.get('target_alive_after') is False and type(row.get('target_hp_before')) in (int, float)
                and row['target_hp_before'] > 0):
            volley.targets_killed.add(target)
        if native_index(row.get('patrol_targets_remaining')) == 0 and volley.last_target_death is None:
            volley.last_target_death = row['history']
    if ability not in TRACKED_ABILITIES:
        return
    unit = native_index(row.get('source'))
    if unit <= 0:
        volley.ambiguous.update(roster)
        return
    if unit not in roster:
        return
    if ability in OVERWATCH_STANCES:
        volley.rearmed.add(unit)
        return
    if ability == 'pistolreturnfire' or row.get('ow_reserve') == 'other':
        volley.other_reserve.add(unit)
        return
    if (row.get('source_scope') != 'friendly' or native_index(row.get('target')) <= 0
            or native_index(row.get('target_group')) <= 0):
        volley.ambiguous.add(unit)
        return
    if row['target_group'] != group:
        volley.other_targets.add(unit)
        return
    volley.seen.add(unit)
    if row.get('ow_reserve') == 'spent' and unit not in volley.rearmed:
        volley.fired.add(unit)
        volley.hits[str(row.get('hit', 'unknown'))] += 1
    else:
        volley.ambiguous.add(unit)


def window_outcome(roster, fired, reasons):
    """Classify the observed volley; missing evidence cannot prove a negative or a complete salvo."""
    if reasons:
        return 'unknown'
    if not roster:
        return 'no_armed_soldiers'
    if fired == roster:
        return 'full'
    if fired:
        return 'partial'
    return 'no_patrol_shot_observed'


def evaluate_window(window, following_history, evidence, recording_issue):
    """Evaluate a reserve snapshot within native turn/control bounds, with uncertainty and hit outcomes."""
    turn = native_index(window.get('turn'))
    history = native_index(window.get('history'))
    group = native_index(window.get('group'))
    kind = str(window.get('kind', '')).casefold()
    roster = roster_ids(window.get('armed'))
    reasons = {recording_issue} if recording_issue else set()
    if (group <= 0 or history < 0 or turn < 0 or kind not in ('open', 'wait')
            or window.get('complete') is not True or roster is None):
        reasons.add('incomplete_window')
    roster = roster or set()
    cutoff, boundary, unlocated = window_boundary(window, following_history, evidence)
    if unlocated:
        reasons.add('unlocated_pause')
    gap = bisect_right(evidence.gaps, history, key=itemgetter(1))
    if gap < len(evidence.gaps) and (cutoff is None or evidence.gaps[gap][0] <= cutoff):
        reasons.add('missing_native_history')
    rows = evidence.frames[turn]
    left = bisect_right(rows, history, key=HISTORY)
    right = len(rows) if cutoff is None else bisect_right(rows, cutoff, key=HISTORY)
    volley = Volley()
    for _, _, row in rows[left:right]:
        observe_frame(row, group, roster, volley)
    missing = roster - volley.fired
    if missing:
        unavailable = evidence.uncertain.get(turn, set()) | evidence.uncertain.get(-1, set())
        if missing & (volley.ambiguous | volley.rearmed | unavailable) or (unavailable and min(unavailable) <= 0):
            reasons.add('ambiguous_source_target_or_reserve')
        if boundary:
            reasons.add(boundary)
        elif cutoff is None:
            reasons.add('window_not_fully_recorded')
    return {'group': group, 'turn': turn, 'history': history, 'kind': kind,
            'armed': sorted(roster), 'fired_at_patrol': sorted(volley.fired), 'unconfirmed': sorted(missing),
            'armed_in_observed_manual_phase': manually_armed(roster, turn, history, evidence),
            'observed_shooters_at_patrol': sorted(volley.seen), 'fired_at_other_group': sorted(volley.other_targets),
            'other_reaction_reserve_or_return_fire': sorted(volley.other_reserve), 'hit_results': dict(sorted(volley.hits.items())),
            'observed_patrol_target_kills': sorted(volley.targets_killed), 'last_patrol_target_killed_history': volley.last_target_death,
            'outcome': window_outcome(roster, volley.fired, reasons), 'reasons': sorted(reasons)}


def summarize_windows(records, recording_issue=None):
    """Return a report per native handoff. Older logs lack an attributable patrol window."""
    windows = [row for row in records if row['event'] == 'patrol_window']
    if not windows:
        return {'windows': [], 'outcomes': {}}
    windows.sort(key=lambda row: (native_index(row.get('turn')), native_index(row.get('history')), row['seq']))
    evidence = collect_evidence(records)
    keys = [(native_index(row.get('turn')), native_index(row.get('history'))) for row in windows]
    counts = Counter(keys)
    reports = []
    for index, (turn, history) in enumerate(keys):
        following = None
        if index + 1 < len(windows) and turn == keys[index + 1][0]:
            following = keys[index + 1][1]
        issue = recording_issue or ('coincident_windows' if counts[turn, history] > 1 else None)
        reports.append(evaluate_window(windows[index], following, evidence, issue))
    outcomes = Counter(report['outcome'] for report in reports)
    return {'windows': reports, 'outcomes': dict(sorted(outcomes.items()))}
