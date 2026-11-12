"""Final native rollups need a real drained end; HUD/model totals are separate."""
from copy import deepcopy
import unittest

from test_game_scoring import SCORING, LOG, events


def rollup(**fields):
    return {'event': 'score_delta', 'source': 'game_runtime', 'score_id': 749,
            'scoring_type': 'CMPT_TotalScore', 'added_points': 7100,
            'ladder_bonus': 90000, 'history': 3924, **fields}


def attempt(points=7100, outcome='loss', extra=()):
    return events({'event': 'start', 'mission': 'SabotageTransmitter', 'history': 265},
                  {'event': 'hud_score', 'display': '6900/32950'},
                  *extra, rollup(added_points=points),
                  {'event': 'end', 'reason': 'tactical_game_ended', 'outcome': outcome,
                   'history': 3927, 'history_pending': 0})


def verdict(records, outcome='win'):
    return SCORING.assess_attempt(records, outcome, SCORING.score_session(records))


class TerminalNativeScoreTests(unittest.TestCase):
    def test_positive_native_total_with_loss_is_final_but_not_a_project_pass(self):
        rows = attempt()
        result = verdict(rows, 'loss')
        self.assertEqual(result['score'], 7100)
        self.assertEqual(result['observed_score'], 7100)
        self.assertTrue(result['score_complete'])
        self.assertEqual(result['score_status'], 'final_native_observation')
        self.assertEqual(result['score_source'], 'native_mission_points')
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['reason'], 'mission_lost')

    def test_win_requires_a_positive_signed_native_total(self):
        for points, status in [(7100, 'pass'), (0, 'fail'), (-21200, 'fail')]:
            with self.subTest(points=points):
                result = verdict(attempt(points=points, outcome='win'))
                self.assertEqual((result['score'], result['status']), (points, status))
                self.assertTrue(result['score_complete'])

    def test_rollup_is_not_summed_with_awards_or_ladder_bonus(self):
        rows = attempt(extra=({'event': 'score_delta', 'source': 'game_runtime',
                               'score_id': 1, 'scoring_type': 'CMPT_KilledEnemy',
                               'added_points': 400, 'ladder_bonus': 100, 'history': 1590},))
        self.assertEqual(verdict(rows, 'loss')['score'], 7100)
        native = SCORING.official_observations(rows)
        self.assertEqual(native['terminal_rollup']['mission_points'], 7100)
        self.assertIsNone(native['cumulative_score'])
        self.assertIsNone(native['recording_delta'])
        self.assertEqual((native['from_history'], native['to_history']), (3924, 3927))
        self.assertFalse(SCORING.score_session(rows)['comparison']['is_official_game_score'])

    def test_duplicate_equal_totals_are_one_value(self):
        rows = attempt(extra=(rollup(),))
        self.assertEqual(verdict(rows, 'loss')['score'], 7100)
        self.assertEqual(SCORING.terminal_challenge_rollup(rows)['observed_totals'], [7100])

    def test_conflicting_totals_do_not_select_the_positive_or_last_one(self):
        rows = attempt(extra=(rollup(score_id=700, added_points=-100),))
        result = verdict(rows)
        self.assertIsNone(result['score'])
        self.assertFalse(result['score_complete'])
        self.assertEqual(result['score_status'], 'conflicting_native_totals')
        self.assertNotEqual(result['status'], 'pass')

    def test_missing_terminal_or_start_cannot_confirm_a_rollup(self):
        for rows in (attempt()[:-1], attempt()[1:]):
            with self.subTest(events=[r['event'] for r in rows]):
                self.assertIsNone(SCORING.terminal_challenge_rollup(rows))
                self.assertFalse(verdict(rows)['score_complete'])

    def test_incomplete_manual_unknown_and_malformed_ends_stay_provisional(self):
        for fields in ({'history_pending': 1}, {'history_pending': None},
                       {'history_pending': False}, {'reason': 'User toggle'},
                       {'outcome': 'unknown'}, {'history': 3923},
                       {'history': True}, {'seq': None}):
            rows = attempt(outcome='win')
            rows[-1].update(fields)
            with self.subTest(fields=fields):
                self.assertIsNone(SCORING.terminal_challenge_rollup(rows))
                self.assertFalse(verdict(rows)['score_complete'])

    def test_foreign_non_native_or_out_of_boundary_totals_are_not_final(self):
        for fields in ({'session': 'other'}, {'source': 'comparison'},
                       {'scoring_type': 'CMPT_KilledEnemy'}, {'added_points': True},
                       {'score_id': 0}, {'history': True}, {'history': 264},
                       {'history': 3928}, {'seq': 999}):
            rows = attempt(outcome='win')
            rows[-2].update(fields)
            with self.subTest(fields=fields):
                self.assertIsNone(SCORING.terminal_challenge_rollup(rows))
                self.assertFalse(verdict(rows)['score_complete'])

    def test_a_new_start_in_the_session_invalidates_the_old_total(self):
        rows = attempt()
        rows.insert(-1, {'event': 'start', 'session': 's', 'seq': 3.5, 'history': 3925})
        # Valid integer sequences, as produced by the recorder.
        for seq, row in enumerate(rows, 1):
            row['seq'] = seq
        self.assertIsNone(SCORING.terminal_challenge_rollup(rows))

    def test_legacy_mission_baseline_keeps_priority_over_a_raw_rollup(self):
        rows = attempt(outcome='win', extra=(
            {'event': 'game_score', 'source': 'legacy_runtime', 'cumulative_score': 9999,
             'mission_points_known': True, 'mission_points': -100, 'mission_final': True,
             'phase': 'finish', 'history': 3927, 'ladder_index': 1, 'ladder_rung': 2},))
        result = verdict(rows)
        self.assertEqual(result['score'], -100)
        self.assertEqual(result['status'], 'fail')
        self.assertIsNone(SCORING.terminal_challenge_rollup(rows))

    def test_integration_summary_calls_it_confirmed_not_missing_or_provisional(self):
        rows = attempt()
        text = '\n'.join('APXREC|v=1|' + '|'.join(f'{k}={v}' for k, v in row.items())
                         for row in rows)
        report = LOG.analyze_logs([('Launch.log', text)])
        result = report['sessions'][0]['attempt_verdict']
        self.assertEqual((result['score'], result['status']), (7100, 'fail'))
        summary = LOG.human_summary(report)
        self.assertIn('Confirmed native final mission score=7100', summary)
        self.assertNotIn('Native earned score was not recorded', summary)
        self.assertNotIn('Provisional observed mission points', summary)

    def test_input_records_are_not_rewritten_into_synthetic_game_scores(self):
        rows = attempt()
        before = deepcopy(rows)
        verdict(rows, 'loss')
        self.assertEqual(rows, before)
