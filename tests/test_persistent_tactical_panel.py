"""Runtime source contracts for permanent tactical autoplay panel.

These source checks do not compile UnrealScript or replace an in-game test.
"""
from pathlib import Path
import unittest

from test_ui_gating import function_body

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_UITacticalControl.uc'
CONTROLLER = ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_Controller.uc'
INI = ROOT/'AutoplayXCom2/Config/XComAutoplayXCom2.ini'
RECORDER = ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionRecorder.uc'


class PermanentTacticalPanelContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = UI.read_text(encoding='utf-8-sig')

    def test_config_defaults_to_permanent_without_removing_optout(self):
        config = INI.read_text()
        section = config.split('[AutoplayXCom2.APX_UITacticalControl]', 1)[1].split('[', 1)[0]
        self.assertIn('AlwaysExpanded=true', section)
        self.assertIn('var config bool AlwaysExpanded;', self.ui)
        self.assertIn('CollapseDelaySeconds=', section)
        self.assertIn('FadeSeconds=', section)

    def test_initialization_and_toggle_keep_all_readouts_alive(self):
        init = function_body(self.ui, 'InitAutoplayControl')
        clicked = function_body(self.ui, 'OnToggleClicked')
        self.assertLess(init.index('UpdateStatus();'), init.index('Expand();'))
        self.assertLess(init.index('Expand();'), init.index('ScheduleCollapse();'))
        for label in ("ToggleButton.InitButton(", "ScoreLabel.InitText(",
                      "StatusLabel.InitText(", "Indicator.InitBG("):
            self.assertIn(label, init)
        self.assertIn('Controller.Toggle();', clicked)
        self.assertIn('UpdateStatus();', clicked)
        self.assertIn('Expand();', clicked)
        self.assertIn('ScheduleCollapse();', clicked)

    def test_permanent_branch_cannot_set_pending_collapse(self):
        schedule = function_body(self.ui, 'ScheduleCollapse')
        permanent = schedule.index('if (default.AlwaysExpanded)')
        self.assertLess(permanent, schedule.index('bPendingCollapse = true;'))
        self.assertIn('bPendingCollapse = false;', schedule)
        self.assertLess(schedule.index('return;'), schedule.index('bPendingCollapse = true;'))
        self.assertIn('Expand();', schedule)

    def test_auto_hide_is_still_functional_when_opted_out(self):
        schedule = function_body(self.ui, 'ScheduleCollapse')
        collapse = function_body(self.ui, 'Collapse')
        tick = function_body(self.ui, 'Tick')
        self.assertIn('CollapseRemaining = FMax(0.25, CollapseDelaySeconds)', schedule)
        self.assertIn('ToggleButton.DisableMouseHit();', collapse)
        self.assertIn('ToggleButton.AddTween("_alpha", 0.0,', collapse)
        self.assertIn('StatusLabel.AddTween("_alpha", 0.0,', collapse)
        self.assertLess(collapse.index('if (default.AlwaysExpanded)'),
                        collapse.index('bExpanded = false;'))
        self.assertIn('if (bPendingCollapse && !default.AlwaysExpanded)', tick)
        self.assertIn('Collapse();', tick)

    def test_always_visible_has_clickable_button_and_can_recover(self):
        expand = function_body(self.ui, 'Expand')
        tick = function_body(self.ui, 'Tick')
        self.assertIn('ToggleButton.EnableMouseHit();', expand)
        self.assertIn('ToggleButton.AddTween("_alpha", 100.0,', expand)
        self.assertIn('StatusLabel.AddTween("_alpha", 100.0,', expand)
        self.assertIn('if (default.AlwaysExpanded && !bExpanded)', tick)
        self.assertLess(tick.index('if (default.AlwaysExpanded && !bExpanded)'),
                        tick.index('if (bPendingCollapse && !default.AlwaysExpanded)'))

    def test_score_provider_still_has_latent_update_gate_and_read_only_state(self):
        status = function_body(self.ui, 'UpdateStatus')
        read = function_body(self.ui, 'GetDisplayedScoreText')
        tick = function_body(self.ui, 'Tick')
        self.assertIn('GetDisplayedScoreText();', status)
        self.assertIn('Controller.RecordDisplayedScore(ScoreText);', status)
        self.assertIn("class'APX_MissionScore'.static.CanReadScoreNow()", read)
        self.assertIn('ScoreRefreshRemaining -= DeltaTime;', tick)
        self.assertIn('UpdateStatus();', tick)
        self.assertNotIn('GetTotalScore(', self.ui)
        self.assertNotIn('GetTotalScoreFromHistory(', self.ui)
        self.assertNotIn('SubmitGameState(', self.ui)

    def test_panel_is_removed_with_hud_not_with_combat_turns(self):
        removed = function_body(self.ui, 'Removed')
        self.assertIn('Controller.StopAutoplay("HUD removed");', removed)
        self.assertIn('ScoreCounter.Cleanup();', removed)
        self.assertIn('super.Removed();', removed)
        self.assertIn('mission-report-v40', RECORDER.read_text())


if __name__=='__main__':
    unittest.main()
