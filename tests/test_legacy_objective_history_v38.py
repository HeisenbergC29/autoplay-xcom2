"""v38: conservative, bounded replay of native objective-display transitions.

These contracts inspect UnrealScript source and optional stock SDK logic.
They do NOT execute WOTC native code or certify complete Legacy scoring.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
V3 = CLASSES / "APX_LegacyObservedV3.uc"
REC = CLASSES / "APX_MissionRecorder.uc"
UI = CLASSES / "APX_UITacticalControl.uc"
DLC = CLASSES / "X2DownloadableContentInfo_AutoplayXCom2.uc"


class ObjectiveReplayV38SourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = V3.read_text(encoding="utf-8-sig")
        cls.replay = function_body(cls.code, "ObserveObjectiveHistory")
        cls.frame = function_body(cls.code, "ObserveFrame")
        cls.event = function_body(cls.code, "OnObjectiveCompleted")
        cls.score = function_body(cls.code, "GetObservedScore")

    def test_only_a_real_historical_transition_is_credited(self):
        replay = self.replay
        for required in (
            "HistoryIndex <= StartIndex",
            "GetGameStateFromHistory(HistoryIndex - 1) == none",
            "Frame.IterateByClassType(class'XComGameState_ObjectivesList'",
            "GetGameStateForObjectID(",
            "CurrentList.ObjectID, eReturnType_Reference, HistoryIndex - 1",
            "CurrentInfo.ShowCompleted",
            "CurrentInfo.ShowCheckBox",
            "CurrentInfo.HideInTactical",
            "PreviousInfo.ShowCompleted || PreviousInfo.ShowFailed",
            "if (bPreviouslySet)",
            "Turn = TurnAtHistory(HistoryIndex)",
            "CompletedObjectivePoints(Turn,",
        ):
            with self.subTest(required=required):
                self.assertIn(required, replay)
        self.assertLess(replay.index("if (bPreviouslySet)"),
                        replay.index("CompletedObjectives.AddItem(ObjectiveID)"))
        self.assertLess(replay.index("Turn = TurnAtHistory"),
                        replay.index("CompletedObjectives.AddItem(ObjectiveID)"))
        self.assertNotIn("GetCurrentHistoryIndex() +", replay)

    def test_native_identity_and_live_listener_dedupe(self):
        replay = self.replay
        for required in (
            "CurrentInfo.MissionType != MissionType",
            "CurrentInfo.TextPoolIndex",
            "CurrentInfo.LineIndex",
            "CurrentInfo.GroupID",
            "PreviousInfo.MissionType != CurrentInfo.MissionType",
            "PreviousInfo.TextPoolIndex != CurrentInfo.TextPoolIndex",
            "PreviousInfo.GroupID != CurrentInfo.GroupID",
            "PreviousInfo.LineIndex != CurrentInfo.LineIndex",
            "CompletedObjectives.Find(ObjectiveID) != INDEX_NONE",
        ):
            with self.subTest(required=required):
                self.assertIn(required, replay)
        self.assertIn("CompletedObjectives.Find(ObjectiveID) == INDEX_NONE", self.event)
        self.assertIn("CompletedObjectives.AddItem(ObjectiveID)", self.event)
        self.assertIn("CompletedObjectives.AddItem(ObjectiveID)", replay)
        self.assertIn("ObserveObjectiveHistory(Frame, HistoryIndex)", self.frame)

    def test_missing_data_bounded_and_partial_not_assumed_complete(self):
        replay = self.replay
        self.assertIn("CurrentList.ObjectiveDisplayInfos.Length > 128", replay)
        self.assertIn("PreviousList.ObjectiveDisplayInfos.Length > 128", replay)
        self.assertIn("CompletedObjectives.Length >= 128", replay)
        self.assertIn("if (Turn < 0", replay)
        self.assertIn("bObjectiveHistoryGap = true", replay)
        self.assertIn("bObjectiveHistoryGap = true", self.frame)
        coverage = function_body(self.code, "GetCoverageStatus")
        self.assertIn("partial_objective_history_gap", coverage)
        self.assertIn("partial_civilian_listener_started_late", coverage)
        self.assertIn("partial_native_disabled_restart_bonus_unverified", coverage)
        self.assertIn("bEarlyEventCoverage = false", function_body(self.code, "Cleanup"))
        self.assertIn("ReplayedObjectiveCount = 0", function_body(self.code, "Cleanup"))

    def test_no_score_fabrication_and_native_score_path_unchanged(self):
        self.assertIn("HistoryCursor + 256", self.score)
        self.assertIn("Score += Points", self.score)
        self.assertIn("RescuedCivilianIDs.Length", self.score)
        forbidden = (
            "GetTotalScore(", "SubmitGameState(", "CreateStateObject(",
            "ModifyStateObject(", "SetCurrentHistoryIndex(", "Rand(", "FRand(",
        )
        clean = CHECKS.without_comments(self.code)
        for token in forbidden:
            self.assertNotIn(token, clean)
        # The same revision appears in runtime logs and no staged version
        # may be mistaken for a Windows/game tested release.
        for marker_file in (REC, UI, DLC):
            self.assertIn("mission-report-v38", marker_file.read_text(encoding="utf-8-sig"))


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"),
                     "Private stock SDK UC required")
class ObjectiveReplayV38SDKContracts(unittest.TestCase):
    def test_native_objective_state_and_event_trigger(self):
        root = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"]))
        seq = (root / "XComGame/Classes/SeqAct_DisplayMissionObjective.uc").read_text(
            encoding="utf-8-sig")
        listing = (root / "XComGame/Classes/XComGameState_ObjectivesList.uc").read_text(
            encoding="utf-8-sig")
        for token in (
            "bPreviouslySet = DisplayInfo.ShowCompleted || DisplayInfo.ShowFailed",
            "if(!bPreviouslySet)",
            "if(DisplayInfo.ShowCompleted)",
            "'MissionObjectiveMarkedCompleted'",
            "ObjectiveList.SetObjectiveDisplay(DisplayInfo)",
            "DisplayInfo.GroupID = GroupID",
            "DisplayInfo.TextPoolIndex = TextPoolIndex",
            "DisplayInfo.LineIndex = LineIndex",
        ):
            with self.subTest(token=token):
                self.assertIn(token, seq)
        self.assertIn("var array<ObjectiveDisplayInfo> ObjectiveDisplayInfos", listing)
        self.assertIn("function SetObjectiveDisplay(", listing)


if __name__ == "__main__":
    unittest.main()
