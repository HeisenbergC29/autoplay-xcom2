"""#107 native tactical end -> passive HUD teardown safety.

Executable pure UC gate tests plus actual runtime source integration contracts.
The source-bound integration checks cannot reproduce a Windows UE3 crash or
assert that a native LadderProgress singleton must exist in normal campaigns.
"""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
HUD = CLASSES / "APX_UITacticalControl.uc"
CONTROLLER = CLASSES / "APX_Controller.uc"
RECORDER = CLASSES / "APX_MissionRecorder.uc"


class QuiescenceGateUnitTests(unittest.TestCase):
    """Execute the actual side-effect-free UnrealScript lifecycle predicate."""

    @classmethod
    def setUpClass(cls):
        """Load the committed native-end gate rather than a Python duplicate."""
        cls.gate = staticmethod(load_uc_function(HUD, "ShouldQuiesceHUD"))

    def test_uninitialized_rules_not_mistaken_for_completed_mission(self):
        """HUD constructed before stock match is active must still initialize."""
        self.assertFalse(self.gate(False, False, False))
        self.assertFalse(self.gate(False, True, False))

    def test_normal_tactical_play_and_interrupted_turns_remain_live(self):
        """Temporary UI waits and alien turns are not terminal transitions."""
        self.assertFalse(self.gate(True, True, False))

    def test_real_native_end_and_after_tactical_shutdown_quiesce(self):
        """Both HasTacticalGameEnded and loss of an active match quiesce."""
        self.assertTrue(self.gate(False, False, True))
        self.assertTrue(self.gate(True, True, True))
        self.assertTrue(self.gate(True, False, True))
        self.assertTrue(self.gate(True, False, False))


class QuiescenceIntegrationContracts(unittest.TestCase):
    """Check native guard ordering and separation of observer/recorder owners."""

    @classmethod
    def setUpClass(cls):
        """Read actual source of all three collaborating runtime classes."""
        cls.hud = HUD.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")
        cls.recorder = RECORDER.read_text(encoding="utf-8-sig")

    def test_hud_tick_quiesces_before_map_write_or_score_history_poll(self):
        """No UI tick may reveal FOW or query score after verified native end."""
        tick = function_body(self.hud, "Tick")
        for token in ("bIsRemoved || bPostMissionQuiesced", "TacticalGameIsInPlay()",
                      "HasTacticalGameEnded()", "bSawTacticalInPlay = true;",
                      "ShouldQuiesceHUD(", "QuiescePostMissionHUD();"):
            self.assertIn(token, tick)
        self.assertLess(tick.index("ShouldQuiesceHUD("),
                        tick.index("RevealMapForPlayer("))
        self.assertLess(tick.index("QuiescePostMissionHUD();"),
                        tick.index("ScoreRefreshRemaining -= DeltaTime;"))
        self.assertLess(tick.index("QuiescePostMissionHUD();"),
                        tick.index("UpdateStatus();"))

    def test_quiesce_is_idempotent_and_releases_only_observational_caches(self):
        """Do not tear down native controller before it records terminal WIN."""
        cleanup = function_body(self.hud, "QuiescePostMissionHUD")
        for token in ("if (bPostMissionQuiesced)", "bPostMissionQuiesced = true;",
                      "ScoreCounter.ResetCache();", "CachedScoreHistory = none;",
                      "CachedScoreHistoryIndex = -1;", "bScoreTextValid = false;",
                      "HUD quiesced after native tactical end"):
            self.assertIn(token, cleanup)
        for forbidden in ("Controller.Destroy(", "Controller.StopAutoplay(",
                          "SubmitGameState(", "ActivateAbility_ReturnContext(",
                          "GetTotalScore(", "RevealMapForPlayer("):
            self.assertNotIn(forbidden, cleanup)

    def test_real_recorder_finalizes_and_unsubscribes_after_win_not_by_hud_gate(self):
        """Final scoring and all four event unsubscriptions remain owned by recorder."""
        controller_tick = function_body(self.controller, "Tick")
        finish = function_body(self.recorder, "Finish")
        unregister = function_body(self.recorder, "UnregisterScoreObservers")
        self.assertLess(controller_tick.index('MissionRecorder.Finish("tactical_game_ended")'),
                        controller_tick.index('StopAutoplay("Mission ended or world changed")'))
        for token in ("RecordGameScore(", 'Emit("end"', "UnregisterScoreObservers();",
                      "bFinished = true;"):
            self.assertIn(token, finish)
        for event in ("MissionObjectiveMarkedCompleted", "MissionObjectiveMarkedFailed",
                      "ChallengeObjectiveFailed", "CivilianRescued"):
            self.assertIn(f"UnRegisterFromEvent(Listener, '{event}')", unregister)
        removed = function_body(self.hud, "Removed")
        self.assertIn("Controller.Destroy();", removed)
        self.assertIn("ScoreCounter.Cleanup();", removed)

    def test_startup_rearms_quiescence_and_version_marker(self):
        """A new tactical HUD begins with clean lifecycle booleans."""
        init = function_body(self.hud, "InitAutoplayControl")
        self.assertIn("bSawTacticalInPlay = false;", init)
        self.assertIn("bPostMissionQuiesced = false;", init)
        self.assertIn("mission-report-v46", init)
        self.assertIn("mission-report-v46", self.recorder)


if __name__ == "__main__":
    unittest.main()
