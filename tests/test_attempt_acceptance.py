"""Project success requires both a native victory and positive mission points."""
import unittest

from test_game_scoring import SCORING, LOG, events, friendly, enemy
from test_mission_log import record


def native_attempt(points, outcome='win', **changes):
    snapshot = {'event': 'game_score', 'source': 'legacy_runtime', 'phase': 'finish',
                'ladder_index': 1, 'ladder_rung': 2, 'cumulative_score': 50000,
                'history': 200,
                'mission_points_known': True, 'mission_points': points, 'mission_final': True,
                **changes}
    return events({'event': 'start'}, snapshot,
                  {'event': 'end', 'outcome': outcome, 'history': 200, 'history_pending': 0})


def assess(records, outcome='win', profile=None):
    scoring = SCORING.score_session(records, profile=profile)
    return SCORING.assess_attempt(records, outcome, scoring)


def complete_comparison(*observations, outcome='win'):
    return events({'event': 'start'}, {'event': 'phase', 'turn': 1},
                  friendly(highest_hp=6, lowest_hp=6), *observations,
                  {'event': 'scoring_coverage', 'complete': True},
                  {'event': 'end', 'outcome': outcome, 'history_pending': 0})


class AttemptAcceptanceTests(unittest.TestCase):
    def test_strict_positive_boundary_preserves_the_game_victory(self):
        for points, expected in ((-1, 'fail'), (0, 'fail'), (1, 'pass')):
            with self.subTest(points=points):
                result = assess(native_attempt(points))
                self.assertEqual(result['status'], expected)
                self.assertEqual(result['mission_outcome'], 'win')
                self.assertEqual(result['score'], points)
                self.assertTrue(result['score_complete'])
                self.assertEqual(result['score_source'], 'native_mission_points')

    def test_ladder_cumulative_points_cannot_mask_negative_mission_points(self):
        result = assess(native_attempt(-500, cumulative_score=50000))
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['score'], -500)
        self.assertEqual(result['reason'], 'mission_score_not_positive')

    def test_positive_mission_contribution_can_pass_with_negative_ladder_cumulative(self):
        result = assess(native_attempt(100, cumulative_score=-50000))
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['score'], 100)

    def test_native_defeat_fails_even_with_positive_points_or_no_score(self):
        for records in (native_attempt(1000, 'loss'), events({'event': 'end', 'outcome': 'loss'})):
            with self.subTest(records=records):
                result = assess(records, 'loss')
                self.assertEqual(result['status'], 'fail')
                self.assertEqual(result['reason'], 'mission_lost')

    def test_positive_points_do_not_establish_an_unconfirmed_victory(self):
        result = assess(native_attempt(1000, 'unknown'), 'unknown')
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['reason'], 'mission_outcome_unknown')

    def test_missing_false_or_invalid_native_known_flag_does_not_turn_zero_into_a_score(self):
        for flag in (None, False, 'True'):
            with self.subTest(flag=flag):
                result = assess(native_attempt(0, mission_points_known=flag))
                self.assertEqual(result['status'], 'unknown')
                self.assertIsNone(result['score'])
        result = assess(native_attempt(True))  # Python bool must not masquerade as an integer point total.
        self.assertEqual(result['status'], 'unknown')

    def test_nonterminal_native_score_cannot_pass(self):
        for changes in ({'mission_final': False}, {'phase': 'observe'}):
            with self.subTest(changes=changes):
                result = assess(native_attempt(1000, **changes))
                self.assertEqual(result['status'], 'unknown')
                self.assertIsNone(result['score'])
                self.assertEqual(result['observed_score'], 1000)

    def test_pending_history_prevents_terminal_score_acceptance(self):
        records = native_attempt(1000)
        records[-1]['history_pending'] = 1
        result = assess(records)
        self.assertEqual(result['status'], 'unknown')
        self.assertFalse(result['score_complete'])

    def test_stale_or_missing_terminal_history_prevents_approval(self):
        for changes in ({'history': 199}, {'history': None}, {'history': True}, {'history': -1}):
            with self.subTest(changes=changes):
                result = assess(native_attempt(1000, **changes))
                self.assertEqual(result['status'], 'unknown')
                self.assertFalse(result['score_complete'])
                self.assertIsNone(result['score'])
                self.assertEqual(result['observed_score'], 1000)
        records = native_attempt(1000)
        records[-1].pop('history')
        self.assertEqual(assess(records)['status'], 'unknown')

    def test_snapshot_recorded_after_end_is_not_a_terminal_snapshot_for_that_attempt(self):
        records = native_attempt(1000)
        records[1]['seq'], records[-1]['seq'] = records[-1]['seq'], records[1]['seq']
        self.assertEqual(assess(records)['status'], 'unknown')

    def test_old_native_delta_and_hud_observations_are_explicitly_provisional(self):
        records = events({'event': 'start'},
                         {'event': 'game_score', 'source': 'legacy_runtime', 'phase': 'start',
                          'cumulative_score': 10000},
                         {'event': 'hud_score', 'display': '-500/46000'},
                         {'event': 'game_score', 'source': 'legacy_runtime', 'phase': 'finish',
                          'cumulative_score': 9500},
                         {'event': 'end', 'outcome': 'win', 'history_pending': 0})
        result = assess(records)
        self.assertEqual(result['status'], 'unknown')
        self.assertIsNone(result['score'])
        self.assertEqual(result['observed_score'], -500)
        self.assertEqual(result['score_source'], 'native_hud_observation')

    def test_partial_native_data_takes_precedence_over_a_complete_comparison(self):
        records = complete_comparison(enemy(), enemy(hp=0, alive=False))
        records.insert(-1, {'seq': records[-1]['seq'], 'event': 'game_score',
                            'source': 'legacy_runtime', 'phase': 'finish', 'cumulative_score': 8000})
        records[-1]['seq'] += 1
        result = assess(records)
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['score_source'], 'native_mission_points')
        self.assertIsNone(result['score'])

    def test_unscored_complete_comparison_uses_v2_and_the_same_strict_boundary(self):
        cases = (([], 0, 'fail'),
                 ([friendly(hp=4, highest_hp=6, lowest_hp=4)], -1000, 'fail'),
                 ([enemy(), enemy(hp=0, alive=False)], 1500, 'pass'))
        for observations, points, expected in cases:
            with self.subTest(points=points):
                result = assess(complete_comparison(*observations))
                self.assertEqual(result['status'], expected)
                self.assertEqual(result['score'], points)
                self.assertEqual(result['score_source'], 'comparison')
                self.assertEqual(result['score_profile'], 'wotc_legacy_observed_v2')

    def test_partial_comparison_subtotal_never_approves_or_invents_a_final_total(self):
        records = complete_comparison(enemy(), enemy(hp=0, alive=False))
        records = [item for item in records if item['event'] != 'scoring_coverage']
        result = assess(records)
        self.assertEqual(result['status'], 'unknown')
        self.assertIsNone(result['score'])
        self.assertEqual(result['observed_score'], 1500)
        self.assertEqual(result['score_status'], 'partial_comparison')

    def test_archived_initial_allowance_profile_is_not_the_new_acceptance_scale(self):
        profile = SCORING.load_profile(SCORING.PROFILE_PATH.with_name('legacy-score-rules-v1.json'))
        result = assess(complete_comparison(), profile=profile)
        self.assertEqual(result['status'], 'unknown')
        self.assertIsNone(result['score'])
        self.assertEqual(result['score_profile'], profile['profile_id'])

    def test_later_ladder_rung_does_not_replace_the_mission_contribution(self):
        records = native_attempt(100)
        records.insert(-1, {'seq': records[-1]['seq'], 'event': 'game_score',
                            'source': 'legacy_runtime', 'phase': 'finish', 'ladder_index': 1,
                            'ladder_rung': 3, 'cumulative_score': 90000, 'mission_points_known': True,
                            'mission_points': -9000, 'mission_final': True})
        records[-1]['seq'] += 1
        result = assess(records)
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['score'], 100)

    def test_analyzer_renders_attempt_failure_without_rewriting_native_win(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start', 'mission=Legacy'),
            record(2, 'game_score', 'source=legacy_runtime|phase=finish|cumulative_score=50000|'
                   'mission_points_known=True|mission_points=-100|mission_final=True|history=200'),
            record(3, 'end', 'outcome=win|history=200|history_pending=0'),
        ]))])
        session = report['sessions'][0]
        self.assertEqual(session['outcome'], 'win')
        self.assertEqual(session['attempt_verdict']['status'], 'fail')
        self.assertEqual(report['attempt_criterion'], SCORING.ATTEMPT_CRITERION)
        rendered = LOG.human_summary(report)
        self.assertIn('outcome=win', rendered)
        self.assertIn('Attempt assessment (victory and mission score > 0): FAIL', rendered)
        self.assertIn('score=-100', rendered)

    def test_conflicting_native_score_records_cannot_approve_the_first_observation(self):
        report = LOG.analyze_logs([('Launch.log', '\n'.join([
            record(1, 'start', 'mission=Legacy'),
            record(2, 'game_score', 'source=legacy_runtime|phase=finish|cumulative_score=50000|'
                   'mission_points_known=True|mission_points=100|mission_final=True|history=200'),
            record(2, 'game_score', 'source=legacy_runtime|phase=finish|cumulative_score=50000|'
                   'mission_points_known=True|mission_points=-100|mission_final=True|history=200'),
            record(3, 'end', 'outcome=win|history=200|history_pending=0'),
        ]))])
        session = report['sessions'][0]
        self.assertEqual(session['outcome'], 'win')
        verdict = session['attempt_verdict']
        self.assertEqual(verdict['status'], 'unknown')
        self.assertEqual(verdict['reason'], 'conflicting_records')
        self.assertIsNone(verdict['score'])
        self.assertFalse(verdict['score_complete'])


if __name__ == '__main__':
    unittest.main()
