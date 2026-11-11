"""Read-only tactical wait heartbeat: bounded diagnostics, never a hang fix.

The source-contract tests assert the actual UnrealScript call ordering. Pure
scheduling helpers are translated from their .uc bodies by the existing adapter.
Windows WOTC compilation and reproduction of the long wait remain separate.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_Controller.uc"
CONFIG = ROOT / "AutoplayXCom2/Config/XComAutoplayXCom2.ini"


class WaitHeartbeatContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CONTROLLER.read_text(encoding="utf-8-sig")
        cls.due = staticmethod(load_uc_function(CONTROLLER, "IsWaitHeartbeatDue"))
        cls.schedule = staticmethod(
            load_uc_function(CONTROLLER, "ScheduleNextWaitHeartbeat"))

    def test_initial_threshold_and_repeated_threshold_are_bounded(self):
        for seconds in (0, 4.9, 14.9):
            self.assertFalse(self.due(seconds, 15.0))
        self.assertTrue(self.due(15.0, 15.0))
        self.assertTrue(self.due(100.0, 15.0))
        self.assertFalse(self.due(100.0, 0.0))
        self.assertEqual(self.schedule(15.0, 30.0), 45.0)
        self.assertEqual(self.schedule(45.0, 0.0), 60.0)
        self.assertEqual(self.schedule(45.0, 300.0), 225.0)
        self.assertEqual(self.schedule(120.0, 30.0), 150.0)

    def test_config_is_diagnostic_only_and_has_slow_defaults(self):
        config = CONFIG.read_text(encoding="utf-8-sig")
        self.assertIn("WaitHeartbeatFirstSeconds=15.0", config)
        self.assertIn("WaitHeartbeatRepeatSeconds=30.0", config)
        self.assertIn("var config float WaitHeartbeatFirstSeconds;", self.source)
        self.assertIn("var config float WaitHeartbeatRepeatSeconds;", self.source)
        reset = function_body(self.source, "ResetWaitHeartbeat")
        self.assertIn("FClamp(WaitHeartbeatFirstSeconds, 10.0, 120.0)", reset)
        self.assertIn("WaitElapsedSeconds = 0.0", reset)
        self.assertIn("WaitHeartbeatHistory = none", reset)

    def test_wait_reason_resets_cadence_but_details_do_not(self):
        status = function_body(self.source, "SetWaitStatus")
        self.assertRegex(status, r"if\s*\(Reason\s*!=\s*LastWaitReason\)\s*BeginWaitHeartbeat\(\)")
        self.assertLess(status.index("BeginWaitHeartbeat()"),
                        status.index("Reason == LastWaitReason && Details == LastWaitDetails"))
        self.assertNotRegex(status, r"if\s*\([^)]*Details\s*!=\s*LastWaitDetails[^)]*\)\s*BeginWaitHeartbeat")
        begin = function_body(self.source, "BeginWaitHeartbeat")
        for token in ("ResetWaitHeartbeat()", "WaitHeartbeatHistory = `XCOMHISTORY",
                      "FindStartStateIndex()", "GetCurrentHistoryIndex()"):
            self.assertIn(token, begin)

    def test_reset_on_start_stop_resume_and_ready(self):
        for name in ("PostBeginPlay", "StopAutoplay", "Toggle", "Tick"):
            with self.subTest(name=name):
                self.assertIn("ResetWaitHeartbeat()", function_body(self.source, name))
        tick = function_body(self.source, "Tick")
        self.assertLess(tick.index("WorldInfo.Pauser != none"),
                        tick.index("MaybeRecordWaitHeartbeat(DeltaTime, PC)"))
        self.assertLess(tick.index("MaybeRecordWaitHeartbeat(DeltaTime, PC)"),
                        tick.index("PollEndTurnRequest(DeltaTime)"))
        self.assertLess(tick.index("MaybeRecordWaitHeartbeat(DeltaTime, PC)"),
                        tick.index("GetUIBlockReason(PC, UIBlockDetails)"))
        self.assertLess(tick.index("MaybeRecordWaitHeartbeat(DeltaTime, PC)"),
                        tick.index("HandleOwnedHack(DeltaTime)"))
        self.assertLess(tick.index("if (!bEnabled)"),
                        tick.index("MaybeRecordWaitHeartbeat(DeltaTime, PC)"))

    def test_heartbeat_is_observational_bounded_and_mission_scoped(self):
        watchdog = function_body(self.source, "MaybeRecordWaitHeartbeat")
        for token in ("!bEnabled", "LastWaitReason == ''",
                      "IsWaitHeartbeatDue(WaitElapsedSeconds, NextWaitHeartbeatSeconds)",
                      "WaitHeartbeatHistory", "WaitHeartbeatStartState",
                      "CurrentHistory < WaitHeartbeatLastHistory",
                      "BeginWaitHeartbeat()", "History.GetCurrentHistoryIndex()",
                      "History.FindStartStateIndex()",
                      "Visualizer.GetCurrenHistoryFrame()",
                      "Visualizer.LastStateHistoryVisualized",
                      "Presentation.GetTacticalHUD()",
                      "MissionRecorder.Marker(\"wait_heartbeat\"",
                      "ScheduleNextWaitHeartbeat(",
                      "history_delta=", "hud_visible=", "waiting_visualizer="):
            with self.subTest(token=token):
                self.assertIn(token, watchdog)
        for forbidden in ("SubmitGameState(", "CreateNewGameState(",
                          "ModifyStateObject(", "ForceComplete(", "DebugClearHangs(",
                          "PerformEndTurn(", "MakeDecision(", "SetCurrentHistoryFrame(",
                          "LastStateHistoryVisualized ="):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, watchdog)
        self.assertEqual(watchdog.count('MissionRecorder.Marker("wait_heartbeat"'), 1)
        self.assertLess(watchdog.index("IsWaitHeartbeatDue("),
                        watchdog.index("GetCurrenHistoryFrame()"))
        self.assertIn("WaitElapsedSeconds += FMax(0.0, DeltaTime)", watchdog)

    def test_unchanged_native_gameplay_gates(self):
        tick = function_body(self.source, "Tick")
        for token in ("PC.PlayerInput.PressedKeys.Find('Escape')",
                      "if (!bEnabled)", "PollEndTurnRequest(DeltaTime)",
                      "HandleOwnedHack(DeltaTime)", "GetUIBlockReason(",
                      "IsInState('TurnPhase_UnitActions')",
                      "IsWaitingForNewStates()", "WaitingForVisualizer()",
                      "MakeDecision(PC)"):
            self.assertIn(token, tick)


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"),
                     "Set APX_SDK_SOURCE_ROOT to check native visualization APIs")
class WaitHeartbeatSDKContracts(unittest.TestCase):
    def test_read_only_visualizer_and_history_methods_exist(self):
        root = Path(os.environ["APX_SDK_SOURCE_ROOT"])
        if (root / "XComGame/Classes").is_dir():
            sdk = root / "XComGame/Classes"
        elif (root / "SrcOrig/XComGame/Classes").is_dir():
            sdk = root / "SrcOrig/XComGame/Classes"
        else:
            self.fail("Expected SrcOrig/XComGame/Classes")
        visual = (sdk / "XComGameStateVisualizationMgr.uc").read_text(
            encoding="utf-8-sig", errors="replace")
        history = (sdk / "XComGameStateHistory.uc").read_text(
            encoding="utf-8-sig", errors="replace")
        rules = (sdk / "X2TacticalGameRuleset.uc").read_text(
            encoding="utf-8-sig", errors="replace")
        self.assertIn("function int GetCurrenHistoryFrame()", visual)
        self.assertRegex(visual, r"var\s+public\s+int\s+LastStateHistoryVisualized")
        self.assertIn("function int GetCurrentHistoryIndex()", history)
        self.assertIn("function bool WaitingForVisualizer()", rules)


if __name__ == "__main__":
    unittest.main()
