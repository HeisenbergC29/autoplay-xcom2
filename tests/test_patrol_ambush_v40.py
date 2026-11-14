"""#88 bounded pre-contact staging, native opener/OW policy and lifecycle.

Numeric policy tests execute helper bodies from REAL UnrealScript via uc_math.
Source contracts check dispatch wiring. These are not Windows/game tests.
"""
from pathlib import Path
import os
import unittest

from uc_math import load_uc_function
from test_ui_gating import CHECKS, function_body

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
AMBUSH = SRC / "APX_PatrolAmbushPlanner.uc"
CONTACT = SRC / "APX_ContactEnvelope.uc"
CONTROLLER = SRC / "APX_Controller.uc"
SQUAD = SRC / "APX_SquadPlanner.uc"
INI = ROOT / "AutoplayXCom2/Config/XComAutoplayXCom2.ini"


class PatrolAmbushNumericPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = staticmethod(load_uc_function(AMBUSH, "CanStage"))
        cls.defer = staticmethod(load_uc_function(AMBUSH, "CanDeferOpener"))

    def test_precontact_staging_requires_native_move_and_unused_blue_ap(self):
        self.assertTrue(self.stage(True, False, False, True, 2, 0, 3, 0, 2))
        self.assertTrue(self.stage(True, False, False, True, 2, 2, 3, 1, 2))
        native_stage = load_uc_function(SQUAD, "CanStageMove")
        self.assertTrue(native_stage(2, 1, False))
        self.assertFalse(native_stage(2, 2, False))
        self.assertFalse(native_stage(1, 1, False))
        for args in (
            (False, False, False, True, 2, 0, 3, 0, 2),
            (True, True, False, True, 2, 0, 3, 0, 2),
            (True, False, True, True, 2, 0, 3, 0, 2),
            (True, False, False, False, 2, 0, 3, 0, 2),
            (True, False, False, True, 1, 0, 3, 0, 2),
            (True, False, False, True, 2, 3, 3, 0, 2),
            (True, False, False, True, 2, 0, 3, -1, 2),
            (True, False, False, True, 2, 0, 3, 2, 2),
        ):
            with self.subTest(args=args):
                self.assertFalse(self.stage(*args))

    def test_only_legal_current_opener_with_support_can_delay_direct_shot(self):
        self.assertTrue(self.defer(True, False, False, 250.0, 2, 0, 3, 60.0))
        self.assertTrue(self.defer(True, False, True, 55.0, 2, 1, 3, 60.0))
        for args in (
            (False, False, False, 10.0, 3, 0, 3, 60.0),
            (True, True, False, 10.0, 3, 0, 3, 60.0),
            (True, False, False, 10.0, 1, 0, 3, 60.0),
            (True, False, False, 10.0, 3, 3, 3, 60.0),
            (True, False, True, 61.0, 3, 1, 3, 60.0),
            (True, False, True, 250.0, 3, 1, 3, 60.0),
        ):
            with self.subTest(args=args):
                self.assertFalse(self.defer(*args))


class PatrolAmbushSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ambush = AMBUSH.read_text(encoding="utf-8-sig")
        cls.contact = CONTACT.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")
        cls.squad = SQUAD.read_text(encoding="utf-8-sig")

    def test_one_validated_shared_snapshot_exposes_current_waypoint(self):
        snapshot = function_body(self.contact, "BuildSnapshot")
        decision = function_body(self.controller, "MakeDecision")
        self.assertIn("PatrolGroup.ObjectID = 0", snapshot)
        self.assertIn("StoredPatrolEvidence(", snapshot)
        self.assertIn("PatrolGroup.ObjectID = Group.ObjectID", snapshot)
        self.assertIn("Group.CurrentTargetLocation", snapshot)
        self.assertIn("AmbushPatrolRef, AmbushPatrolWaypoint", decision)
        self.assertIn("bContactSnapshotComplete", decision)
        self.assertIn("PatrolAmbushPlanner.Refresh(", decision)
        self.assertIn("if (!bPatrolRefreshed)", decision)
        self.assertNotIn("ComputeGroupPath(", self.ambush)
        self.assertNotIn("ShouldMoveToIntercept(", self.ambush)

    def test_bounded_setup_epoch_and_no_rearm_on_same_expired_waypoint(self):
        refresh = function_body(self.ambush, "Refresh")
        reset = function_body(self.ambush, "Reset")
        for key in ("OwnedHistory != `XCOMHISTORY", "OwnedStartIndex != StartIndex",
                    "OwnedBattleID != Battle.ObjectID", "OwnedPlayerID !=",
                    "HistoryIndex < LastHistory", "Turn < LastTurn",
                    "CurrentWaypoint != Waypoint", "Turn - StartTurn",
                    "bExpired = true", "setup_wait_limit", "urgent_mission_preempts",
                    "patrol_evidence_unknown"):
            self.assertIn(key, refresh)
        self.assertIn("verified_group_entered_contact", refresh)
        self.assertIn("GetImmediateThreats(", refresh)
        self.assertIn("CurrentEnemies.Length <= 24", refresh)
        self.assertIn("Group.m_arrMembers.Find('ObjectID',", refresh)
        self.assertIn("StartTurn = INDEX_NONE;", reset)
        self.assertIn("OrderedReactions = 0;", reset)
        self.assertIn("PatrolAmbushPlanner.Reset();",
                      function_body(self.controller, "StopAutoplay"))
        self.assertIn("bEnabled = false;", function_body(self.controller, "StopAutoplay"))

    def test_variant_corridors_rank_without_certifying_future_clear(self):
        lanes = function_body(self.ambush, "CountVariantLanes")
        approach = function_body(self.ambush, "ChooseApproach")
        for key in ("Index < 3", "Variant.X += 2", "Variant.Y += 2",
                    "CanSeeTileToTile(Position, Variant, Visibility)",
                    "Visibility.DefaultTargetDist <= SightSq",
                    "--RemainingLOS;", "RemainingLOS <= 0"):
            self.assertIn(key, lanes)
        for key in ("m_kReachableTilesCache.GetPathCostToTile",
                    "Cost > Visualizer.GetMobility()", "GetImmediateThreats(",
                    "GetVisibleThreats(", "BuildPathToTile(",
                    "PreparationPathIsSafe(", "AssessRoute(",
                    "ContactStatus == 1", "CountVariantLanes(",
                    "VariantPositionScore(", "RemainingConcealmentChecks",
                    "MaxPositionSamples", "CanStageMove(", "OWCost, false",
                    "SquadPositionScore(",
                    "IsSupportedAdvance"):
            # Support is inherited from PreparationPathIsSafe, which is
            # invoked on EVERY tested full path.
            if key == "IsSupportedAdvance":
                self.assertIn(key, function_body(self.squad, "PreparationPathIsSafe"))
            else:
                self.assertIn(key, approach)
        self.assertIn("horizon=variants_unknown", self.controller)
        self.assertNotIn("Rand(", CHECKS.without_comments(self.ambush))
        self.assertNotIn("GetNextDestination(", CHECKS.without_comments(self.ambush))
        self.assertNotIn("SubmitGameState(", CHECKS.without_comments(self.ambush))

    def test_actual_native_shot_before_any_overwatch_support(self):
        support = function_body(self.ambush, "ChooseReactionSupport")
        opener = function_body(self.ambush, "IsActualOpener")
        decision = function_body(self.controller, "MakeDecision")
        for key in ("OpenerTarget >= NativeOpener.AvailableTargets.Length",
                    "Ability.OwnerStateObject.ObjectID != Opener.ObjectID",
                    "eHostility_Offensive", "StandardShot",
                    "m_arrMembers.Find('ObjectID', Enemy.ObjectID)",
                    "IsVisibleHostile(", "CanSeeTileToTile(",
                    "HasReadyOpeningOverwatch(", "FindOverwatch(",
                    "CanDeferOpener(", "MaxReactionSupport",
                    "RemainingLOS <= 0", "--RemainingLOS;"):
            self.assertIn(key, support)
        self.assertIn("Enemy.GetMyTemplate().UnitSize != 1", support)
        self.assertIn("Soldier.GetMyTemplate().UnitSize != 1", support)
        self.assertIn("Soldier.GetMyTemplate().UnitSize != 1",
                      function_body(self.ambush, "ChooseApproach"))
        self.assertIn("Candidate.AvailableCode != 'AA_Success'", opener)
        self.assertIn("PatrolAmbushPlanner.ChooseReactionSupport(", decision)
        self.assertIn("CanUseAction(PatrolSupporter, PatrolReaction", decision)
        self.assertIn("PatrolAmbushPlanner.IsActualOpener(", decision)
        self.assertIn("PatrolAmbushPlanner.NoteSubmitted(", decision)
        self.assertLess(decision.index("PatrolAmbushPlanner.ChooseReactionSupport("),
                        decision.index("MissionRecorder.PrepareChosenAction("))

    def test_safety_mission_priorities_and_no_new_dispatcher(self):
        decision = function_body(self.controller, "MakeDecision")
        for token in ("HasActiveMissionDeadline()", "HasBleedingSquadmate(",
                      "ShouldEvacuate(", "bPatrolActive && !bCombatThreats",
                      "CanUseMove(UnitState, PatrolApproachPath)",
                      "CanUseAction(PatrolSupporter, PatrolReaction",
                      "if (!bHavePlan)", "StopWithStatus(",
                      "GameStateMoveUnitSingle(", "ActivateAbility_ReturnContext("):
            self.assertIn(token, decision)
        self.assertNotIn("GameStateMoveUnitSingle(", self.ambush)
        self.assertNotIn("ActivateAbility_ReturnContext(", self.ambush)
        self.assertIn("BestScore < 80.0", decision)
        self.assertIn('FocusBattle.MapData.ActiveMission.sType != "SabotageTransmitter"', decision)
        self.assertIn("PatrolApproachScore > BestScore + 6.0", decision)
        self.assertIn("MaxSetupTurns=2", INI.read_text(encoding="utf-8-sig"))
        self.assertIn("MaxReactionSupport=3", INI.read_text(encoding="utf-8-sig"))
        self.assertIn("mission-report-v40",
                      (SRC / "APX_MissionRecorder.uc").read_text(encoding="utf-8-sig"))


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"),
                     "Private WOTC SDK classes not available")
class PatrolAmbushSDKContracts(unittest.TestCase):
    def test_read_only_native_source_contracts(self):
        root = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"]))
        group = (root / "XComGame/Classes/XComGameState_AIGroup.uc").read_text(encoding="utf-8-sig")
        unit = (root / "XComGame/Classes/XComGameState_Unit.uc").read_text(encoding="utf-8-sig")
        for token in ("CurrentTargetLocation", "TurnCountForLastDestination", "m_arrMembers"):
            self.assertIn(token, group)
        for token in ("GetVisibilityRadius(", "NumAllReserveActionPoints("):
            self.assertIn(token, unit)


if __name__ == "__main__":
    unittest.main()
