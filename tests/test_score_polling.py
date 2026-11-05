"""Regression scenarios for the isolated HUD score read-rate experiment (#17).

Numerical source helper checks are not XCOM engine execution. The complete
score computation and recording remain in the existing classes unchanged.
"""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function

CLASSES = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
HUD = CLASSES / 'APX_UITacticalControl.uc'
SCORE = CLASSES / 'APX_MissionScore.uc'
CONTROLLER = CLASSES / 'APX_Controller.uc'


class ScorePollingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.should_refresh = staticmethod(load_uc_function(HUD, 'ShouldRefreshScoreForHUD'))
        cls.hud = HUD.read_text(encoding='utf-8-sig')
        cls.score = SCORE.read_text(encoding='utf-8-sig')

    def test_first_read_and_history_change_are_immediate(self):
        self.assertTrue(self.should_refresh(False, False, 1.0))
        self.assertTrue(self.should_refresh(True, True, 1.0))
        self.assertTrue(self.should_refresh(True, True, 0.5))

    def test_unchanged_history_is_polled_periodically_not_every_quarter_second(self):
        self.assertFalse(self.should_refresh(True, False, 0.75))
        self.assertFalse(self.should_refresh(True, False, 0.25))
        self.assertTrue(self.should_refresh(True, False, 0.0))
        self.assertTrue(self.should_refresh(True, False, -0.1))

    def test_tick_keeps_status_four_hz_without_gating_automation_on_off(self):
        tick = function_body(self.hud, 'Tick')
        self.assertIn('ScoreRefreshRemaining -= DeltaTime;', tick)
        self.assertIn('RefreshRemaining = 0.25;', tick)
        self.assertIn('UpdateStatus();', tick)
        self.assertNotIn('Controller.IsEnabled()', tick)
        self.assertNotIn('Controller == none', tick)

    def test_visible_text_invalidates_on_history_identity_and_index(self):
        display = function_body(self.hud, 'GetDisplayedScoreText')
        for expected in ('History = `XCOMHISTORY',
                         'History.GetCurrentHistoryIndex()',
                         'History != CachedScoreHistory || HistoryIndex != CachedScoreHistoryIndex',
                         'CachedScoreText = ScoreCounter.GetText();',
                         'CachedScoreHistory = History;',
                         'CachedScoreHistoryIndex = HistoryIndex;',
                         'ScoreRefreshRemaining = 1.0;'):
            self.assertIn(expected, display)

    def test_authoritative_score_is_not_rerouted_through_hud_cache(self):
        native = function_body(self.score, 'ReadNativeMissionPoints')
        self.assertIn('GetText();', native)
        self.assertNotIn('GetDisplayedScoreText', native)
        scoring = function_body(self.score, 'GetText')
        self.assertIn('Manager.GetTotalScore()', scoring)
        self.assertIn('GetMaxChallengeScore()', scoring)
        self.assertIn('ComparisonCounter.GetObservedScore()', scoring)
        self.assertIn('return "~" $ string(ComparisonPoints)', scoring)

    def test_recorder_still_gets_exact_displayed_text_and_cleanup_resets(self):
        status = function_body(self.hud, 'UpdateStatus')
        self.assertIn('ScoreText = GetDisplayedScoreText()', status)
        self.assertIn('Controller.RecordDisplayedScore(ScoreText)', status)
        self.assertLess(status.index('ScoreText = GetDisplayedScoreText()'),
                        status.index('Controller.RecordDisplayedScore(ScoreText)'))
        removed = function_body(self.hud, 'Removed')
        for expected in ('ScoreCounter.Cleanup()', 'bScoreTextValid = false',
                         'CachedScoreText = ""', 'CachedScoreHistory = none'):
            self.assertIn(expected, removed)
        source = CONTROLLER.read_text(encoding='utf-8-sig')
        forwarding = function_body(source, 'RecordDisplayedScore')
        self.assertIn('MissionRecorder.RecordHUDScore(DisplayText)', forwarding)


if __name__ == '__main__':
    unittest.main()
