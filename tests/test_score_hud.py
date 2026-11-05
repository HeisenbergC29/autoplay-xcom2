"""Check the score row's HUD boundary against the supplied stock UI API.

These checks do not render Flash or attest an in-game layout. They protect the
existing button position and input behavior while the live score stays visible.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body


ROOT = Path(__file__).resolve().parents[1]
HUD = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_UITacticalControl.uc'


class ScoreHUDContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = HUD.read_text()

    def test_score_row_sits_above_the_button_without_moving_existing_controls(self):
        init = function_body(self.source, 'InitAutoplayControl')
        # Parent shifts up one row and its old children shift down by the same
        # amount, preserving user-configured absolute button/status positions.
        self.assertIn('SetPosition(OffsetX, OffsetY - 31.0)', init)
        self.assertIn('SetSize(ButtonWidth + 20.0, 85.0)', init)
        self.assertIn('ScoreLabel.SetPosition(0.0, 0.0)', init)
        self.assertIn('ScoreLabel.SetSize(ButtonWidth, 30.0)', init)
        self.assertIn('ToggleButton.SetPosition(0.0, 31.0)', init)
        self.assertIn('StatusLabel.SetPosition(0.0, 62.0)', init)
        self.assertIn("Indicator.InitBG('APX_Indicator', ButtonWidth + 8.0, 31.0, 8.0, 30.0)", init)

    def test_score_is_passive_and_does_not_hide_when_button_collapses(self):
        init = function_body(self.source, 'InitAutoplayControl')
        self.assertIn('ScoreLabel.DisableMouseHit()', init)
        self.assertIn('ScoreLabel.DisableNavigation()', init)
        self.assertNotIn('ScoreLabel.ProcessMouseEvents', self.source)
        for name in ('Expand', 'Collapse'):
            self.assertNotIn('ScoreLabel', function_body(self.source, name))
        collapse = function_body(self.source, 'Collapse')
        self.assertIn('ToggleButton.DisableMouseHit()', collapse)

    def test_score_refresh_uses_the_actual_button_font_even_with_autoplay_off(self):
        update = function_body(self.source, 'UpdateStatus')
        self.assertIn('ScoreText = GetDisplayedScoreText()', update)
        displayed = function_body(self.source, 'GetDisplayedScoreText')
        self.assertIn('CachedScoreText = ScoreCounter.GetText()', displayed)
        self.assertIn('ScoreText, eUIState_Normal, ToggleButton.FontSize', update)
        self.assertLess(update.index('ScoreText = GetDisplayedScoreText()'), update.index('if (Controller == none)'))
        tick = function_body(self.source, 'Tick')
        self.assertIn('RefreshRemaining = 0.25', tick)
        self.assertIn('UpdateStatus()', tick)
        self.assertNotIn('Controller == none', tick)
        self.assertNotIn('Controller.IsEnabled()', tick)
        init = function_body(self.source, 'InitAutoplayControl')
        self.assertIn("ScoreCounter = new(self) class'APX_MissionScore'", init)
        self.assertIn('ScoreCounter = none', function_body(self.source, 'Removed'))


    def test_telemetry_records_the_same_displayed_text_without_starting_autoplay(self):
        update = function_body(self.source, 'UpdateStatus')
        self.assertIn('Controller.RecordDisplayedScore(ScoreText)', update)
        self.assertLess(update.index('ScoreText = GetDisplayedScoreText()'),
                        update.index('Controller.RecordDisplayedScore(ScoreText)'))
        classes = HUD.parent
        forward = function_body((classes / 'APX_Controller.uc').read_text(), 'RecordDisplayedScore')
        self.assertIn('if (MissionRecorder != none)', forward)
        self.assertIn('MissionRecorder.RecordHUDScore(DisplayText)', forward)
        self.assertNotIn('new(', forward)
        for forbidden in ('Start(', 'Toggle(', 'ActivateAbility', 'SubmitGameState', 'bEnabled ='):
            self.assertNotIn(forbidden, forward)
        record = function_body((classes / 'APX_MissionRecorder.uc').read_text(), 'RecordHUDScore')
        self.assertIn('if (!bStarted || bFinished || DisplayText == LastHUDScore)', record)
        self.assertIn('LastHUDScore = DisplayText', record)
        self.assertIn('Fields = "|display=" $ Safe(DisplayText)', record)
        self.assertIn('Emit("hud_score", Fields)', record)
        self.assertIn('if (Left(DisplayText, 1) == "~")', record)
        self.assertIn('"|comparison_profile="', record)
        self.assertIn("class'APX_ComparisonScore'.static.GetProfileID()", record)
        self.assertLess(record.index('DisplayText == LastHUDScore'), record.index('Emit('))
        self.assertNotIn('CumulativeScore', record)
        self.assertNotIn('AddedPoints', record)
        self.assertNotIn('ModifyStateObject', record)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Score HUD contracts need SDK sources')
class ScoreHUDSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_stock_button_exposes_its_real_font_size(self):
        button = CHECKS.without_comments((self.sdk / 'UIButton.uc').read_text(encoding='utf-8-sig'))
        self.assertRegex(button, r'\bvar\s+int\s+FontSize\s*;')
        self.assertRegex(button, r'FontSize\s*=\s*FONT_SIZE_2D\s*;')
        self.assertRegex(function_body(button, 'SetStyle'),
                         re.compile(r'mc\.QueueNumber\(float\(FontSize\)\)', re.I))

    def test_stock_text_caches_centered_html_instead_of_updating_flash_each_tick(self):
        text = (self.sdk / 'UIText.uc').read_text(encoding='utf-8-sig')
        centered = function_body(text, 'SetCenteredText')
        self.assertIn('return SetHtmlText(', centered)
        html = function_body(text, 'SetHtmlText')
        self.assertIn('if(bForce || HtmlText != NewText)', html)
        self.assertLess(html.index('if(bForce || HtmlText != NewText)'),
                        html.index('mc.BeginFunctionOp("setText")'))


if __name__ == '__main__':
    unittest.main()
