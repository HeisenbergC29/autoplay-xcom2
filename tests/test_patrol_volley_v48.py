"""Exercise patrol volley evidence, including the normal ZIP-to-report entry point."""

import importlib.util
from pathlib import Path
import unittest

from test_revealed_shooter_tactics_e2e_v45 import run_synthetic_bundle


SPEC = importlib.util.spec_from_file_location(
    'patrol_volley_tests', Path(__file__).resolve().parents[1] / 'tools/patrol_overwatch.py')
PATROL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATROL)


def shot(history, unit, *, group=71, payment='spent', ability='OverwatchShot', hit='eHit_Miss'):
    """Build a completed friendly reaction at the given historical player turn."""
    return (f'result|turn=4|history={history}|source={unit}|source_scope=friendly|target=70'
            f'|target_group={group}|ability={ability}|ow_reserve={payment}|hit={hit}')


WINDOW = 'patrol_window|turn=4|history=30|group=71|kind=wait|armed=8,9|complete=True'
DRAIN = 'patrol_drain|turn=5|history=55'
PAUSE = 'marker|kind=autoplay_stop|turn=4|history=35'


def report_sessions(**scenarios):
    """Analyze real ZIP files with consecutive recorder sequences and return reports by session."""
    sessions = [(name, list(enumerate(['start|revision=mission-report-v48|mission=GasStation', *rows])))
                for name, rows in scenarios.items()]
    result = run_synthetic_bundle(*sessions)
    return {session['session']: session['patrol_overwatch'] for session in result['sessions']}


class PatrolEvidenceTests(unittest.TestCase):
    """Check native indexes, roster validation, coalescing, ordering and control boundaries."""

    def test_only_valid_history_and_bounded_distinct_object_ids(self):
        """Preserve integer history zero while rejecting booleans, duplicates and unbounded rosters."""
        self.assertEqual(0, PATROL.native_index(0))
        for invalid in (True, False, -8, None, '3'):
            self.assertEqual(-1, PATROL.native_index(invalid))
        self.assertEqual(set(), PATROL.roster_ids('none'))
        self.assertEqual({5}, PATROL.roster_ids(5))
        self.assertEqual({2, 4}, PATROL.roster_ids('4,2'))
        for invalid in ('2,2', '0', '', None, True, '2147483648', ','.join(map(str, range(1, 258)))):
            self.assertIsNone(PATROL.roster_ids(invalid))

    def test_history_gaps_and_pause_boundaries_use_native_time(self):
        """Gap indexes and deferred markers use native history even when sequence order differs."""
        self.assertEqual([(1, 5), (8, 9)], PATROL.merge_gaps([(8, 9), (3, 5), (1, 2), (2, 4)]))
        rows = [
            dict(event='phase', phase='manual', turn=4, history=37, seq=2),
            dict(event='marker', kind='autoplay_stop', turn=4, history=35, seq=3),
            dict(event='patrol_drain', turn=5, history=55, seq=4),
        ]
        self.assertTrue(PATROL.is_pause(rows[0]))
        self.assertFalse(PATROL.is_pause(rows[-1]))
        evidence = PATROL.collect_evidence(rows)
        window = dict(turn=4, history=30, seq=9)
        self.assertEqual((35, 'autoplay_stopped', False), PATROL.window_boundary(window, 40, evidence))
        self.assertEqual((32, 'next_patrol_window', False), PATROL.window_boundary(window, 32, evidence))

    def test_unknown_and_unarmed_outcomes_are_distinct(self):
        """An empty complete roster has a separate outcome from a broken recording."""
        self.assertEqual('no_armed_soldiers', PATROL.window_outcome(set(), set(), set()))
        self.assertEqual('unknown', PATROL.window_outcome({1}, {1}, {'sequence_gaps'}))
        self.assertEqual({'windows': [], 'outcomes': {}}, PATROL.summarize_windows([]))

    def test_same_history_windows_and_missing_history_stay_uncertain(self):
        """A coincident handoff or gap in the window prevents positive certification."""
        records = [dict(event='patrol_window', turn=1, history=3, group=5,
                        kind='open', armed=9, complete=True, seq=i) for i in (1, 2)]
        records.append(dict(event='patrol_history_gap', seq=3, first=4, last=6))
        reports = PATROL.summarize_windows(records)['windows']
        self.assertTrue(all('coincident_windows' in row['reasons'] for row in reports))
        self.assertIn('missing_native_history', reports[-1]['reasons'])


class PatrolVolleyEndToEnd(unittest.TestCase):
    """Exercise CLI parser, per-session evidence attribution, deduplication and uncertainty."""

    def test_full_miss_partial_no_shot_final_casualty_and_no_roster(self):
        """A miss counts, repeated shots by one soldier do not stand in for a second soldier."""
        sessions = report_sessions(
            full=[WINDOW, shot(36, 9, ability='LongWatchShot'), DRAIN, shot(32, 8, hit='eHit_Success')],
            partial=[WINDOW, shot(32, 8), shot(36, 8, hit='eHit_Success') +
                     '|target_hp_before=3|target_alive_after=False|patrol_targets_remaining=0', DRAIN],
            unfired=[WINDOW, shot(35, 8, group=99), DRAIN],
            empty=[WINDOW.replace('8,9', 'none'), DRAIN],
            legacy=[shot(32, 8), DRAIN],
        )
        full = sessions['full']['windows'][0]
        self.assertEqual('full', full['outcome'])
        self.assertEqual([8, 9], full['fired_at_patrol'])
        self.assertEqual({'eHit_Miss': 1, 'eHit_Success': 1}, full['hit_results'])
        partial = sessions['partial']['windows'][0]
        self.assertEqual('partial', partial['outcome'])
        self.assertEqual([8], partial['fired_at_patrol'])
        self.assertEqual([9], partial['unconfirmed'])
        self.assertEqual([70], partial['observed_patrol_target_kills'])
        self.assertEqual(36, partial['last_patrol_target_killed_history'])
        self.assertEqual([8], sessions['unfired']['windows'][0]['fired_at_other_group'])
        self.assertEqual({'no_patrol_shot_observed': 1}, sessions['unfired']['outcomes'])
        self.assertEqual({'no_armed_soldiers': 1}, sessions['empty']['outcomes'])
        self.assertEqual([], sessions['legacy']['windows'])

    def test_no_false_full_from_other_reserves_group_or_interrupted_frames(self):
        """Separate Return Fire and known other-group shots from ambiguous or unresolved reactions."""
        sessions = report_sessions(
            wrong=[WINDOW, shot(32, 8, group=99), shot(33, 9, payment='other', ability='PistolOverwatchShot'),
                   shot(34, 9, payment='unknown', ability='PistolReturnFire'),
                   shot(35, 8) + '|interruption=eInterruptionStatus_Interrupt', DRAIN],
            ambiguous=[WINDOW, shot(32, 8, group=0), shot(33, 9, payment='unknown'), DRAIN],
            rearm=[WINDOW, 'result|turn=4|history=31|source=8|source_scope=friendly|ability=Overwatch',
                   shot(32, 8), shot(33, 9), DRAIN],
        )
        wrong = sessions['wrong']['windows'][0]
        self.assertEqual('no_patrol_shot_observed', wrong['outcome'])
        self.assertEqual([9], wrong['other_reaction_reserve_or_return_fire'])
        self.assertEqual([8], wrong['fired_at_other_group'])
        for scenario in ('ambiguous', 'rearm'):
            row = sessions[scenario]['windows'][0]
            self.assertEqual('unknown', row['outcome'])
            self.assertIn('ambiguous_source_target_or_reserve', row['reasons'])
        self.assertEqual([9], sessions['rearm']['windows'][0]['fired_at_patrol'])

    def test_final_target_killed_by_opener_outside_waiting_roster(self):
        """A native group extinction can explain a lost opportunity without crediting any OW shot."""
        killed = ('result|turn=4|history=32|source=10|source_scope=friendly|target=70|target_group=71'
                  '|ability=StandardShot|target_alive_after=False|target_hp_before=3|patrol_targets_remaining=0')
        sessions = report_sessions(opener=[WINDOW.replace('wait', 'open'), killed, DRAIN],
                                   unrelated=[WINDOW, killed.replace('group=71', 'group=72'), DRAIN])
        opener = sessions['opener']['windows'][0]
        self.assertEqual('no_patrol_shot_observed', opener['outcome'])
        self.assertEqual([], opener['fired_at_patrol'])
        self.assertEqual([70], opener['observed_patrol_target_kills'])
        self.assertEqual(32, opener['last_patrol_target_killed_history'])
        self.assertIsNone(sessions['unrelated']['windows'][0]['last_patrol_target_killed_history'])

    def test_manual_control_incomplete_recording_and_arm_origins(self):
        """Exclude later manual results and report explicitly observed manual arming separately."""
        sessions = report_sessions(
            manual=['phase|phase=manual|history=10|turn=4',
                    'result|ability=Overwatch|source_scope=friendly|source=9|history=20|turn=4',
                    'phase|phase=autoplay|history=22|turn=4', WINDOW, shot(39, 9), PAUSE,
                    shot(33, 8), DRAIN],
            cut=[WINDOW, shot(33, 8)],
            gap=[WINDOW, shot(32, 8), shot(34, 9), 'patrol_history_gap|first=31|last=31', DRAIN],
        )
        manual = sessions['manual']['windows'][0]
        self.assertEqual('unknown', manual['outcome'])
        self.assertEqual([9], manual['armed_in_observed_manual_phase'])
        self.assertEqual([8], manual['fired_at_patrol'])
        self.assertIn('autoplay_stopped', manual['reasons'])
        self.assertIn('window_not_fully_recorded', sessions['cut']['windows'][0]['reasons'])
        self.assertIn('missing_native_history', sessions['gap']['windows'][0]['reasons'])
