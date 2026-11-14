"""#89/#10: real UC helper execution and native-source guard contracts.

Not a Windows WOTC compile or an in-game demonstration of a fast route.
"""
import os
from pathlib import Path
import unittest
from uc_math import load_uc_function
from test_ui_gating import CHECKS, function_body

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
ROUTE = SRC / "APX_RouteTempo.uc"
MISSION = SRC / "APX_MissionPlanner.uc"
CONTROLLER = SRC / "APX_Controller.uc"
EXPLORATION = SRC / "APX_ExplorationPlanner.uc"
AMBUSH = SRC / "APX_PatrolAmbushPlanner.uc"
INI = ROOT / "AutoplayXCom2/Config/XComAutoplayXCom2.ini"


class RoutePolicies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.second = staticmethod(load_uc_function(ROUTE, "CanUseSecondBlue"))
        cls.penalty = staticmethod(load_uc_function(ROUTE, "SoftVisitPenalty"))
        cls.risk = staticmethod(load_uc_function(MISSION, "IsRoutineBlueExposureAllowed"))

    def test_second_blue_needs_accepted_actual_first_and_safe_new_context(self):
        self.assertTrue(self.second(True, True, True, True, False, False,
                                    False, True, 1, 1))
        for args in (
            (False, True, True, True, False, False, False, True, 1, 1),
            (True, False, True, True, False, False, False, True, 1, 1),
            (True, True, False, True, False, False, False, True, 1, 1),
            (True, True, True, False, False, False, False, True, 1, 1),
            (True, True, True, True, True, False, False, True, 1, 1),
            (True, True, True, True, False, True, False, True, 1, 1),
            (True, True, True, True, False, False, True, True, 1, 1),
            (True, True, True, True, False, False, False, False, 1, 1),
            (True, True, True, True, False, False, False, True, 2, 2),
            (True, True, True, True, False, False, False, True, 1, 0),
            (True, True, True, True, False, False, False, True, 0, 0),
        ):
            with self.subTest(args=args):
                self.assertFalse(self.second(*args))

    def test_current_route_middle_risk_cannot_be_hidden_by_safe_endpoint(self):
        # A = safe start, B = dangerous middle, C = safe end: B vetoes
        # the sequential tempo ticket even when endpoint C looks Clear.
        self.assertTrue(self.risk(10.0, 10.0))
        self.assertTrue(self.risk(10.0, 13.0))
        self.assertFalse(self.risk(10.0, 13.01))
        self.assertFalse(self.risk(10.0, 24.0))
        self.assertFalse(self.risk(0.0, 30.0))

    def test_cross_turn_aba_is_soft_decaying_and_expires(self):
        for turn, expected in ((10, 28), (11, 21), (12, 14), (13, 7), (14, 0)):
            self.assertEqual(self.penalty(turn, 10, 3, True, False, 28, 12), expected)
        self.assertEqual(self.penalty(11, 10, 3, False, True, 28, 12), 9)
        self.assertEqual(self.penalty(11, 10, 3, False, False, 28, 12), 0)
        self.assertEqual(self.penalty(9, 10, 3, True, False, 28, 12), 0)
        self.assertEqual(self.penalty(10, 10, 3, True, False, 100, 0), 40)
        self.assertEqual(self.penalty(10, 10, 3, False, True, 0, 100), 25)


class RouteSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.memory = ROUTE.read_text(encoding="utf-8-sig")
        cls.mission = MISSION.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")
        cls.exploration = EXPLORATION.read_text(encoding="utf-8-sig")
        cls.ambush = AMBUSH.read_text(encoding="utf-8-sig")

    def test_scoped_memory_and_goal_switch(self):
        scope = function_body(self.memory, "Refresh")
        setgoal = function_body(self.memory, "SetGoal")
        ticket = function_body(self.memory, "HasFirstBlueTicket")
        record = function_body(self.memory, "RecordAccepted")
        for t in ("OwnedHistory !=", "OwnedStartIndex != CurrentStart",
                  "OwnedBattleID != Battle.ObjectID", "OwnedPlayerID != LocalPlayerID",
                  "CurrentIndex < LastHistoryIndex", "MaxMemoryTurns",
                  "Visits.Remove(Index, 1)"):
            self.assertIn(t, scope)
        self.assertIn("Goals[Found].Tile != Tile", setgoal)
        self.assertIn("Visits[Index].UnitID == UnitID", setgoal)
        self.assertIn("Visits[Index].Turn != CurrentTurn", ticket)
        self.assertIn("Visits[Index].GoalTile != Goal", ticket)
        self.assertIn("Visits[Index].ToTile == CurrentTile", ticket)
        self.assertIn("bFirstBlueClear = bFirstBlueClear && EnableSequentialBlue", record)
        self.assertIn("MaxVisitEntries", record)

    def test_only_native_blue_and_shared_current_clear_allow_fast_continuation(self):
        choose = function_body(self.mission, "ChooseMove")
        prefix = function_body(self.mission, "ChooseRoutePrefix")
        decision = function_body(self.controller, "MakeDecision")
        for t in ("HasFirstBlueTicket(", "CanUseSecondBlue(", "bSecondBlue",
                  "NumActionPoints('standard') >= 2", "NumActionPointsForMoving() >= 2",
                  "NeedsPoisonEscape(", "bActivePatrolPreparation",
                  "bRecentContact", "bContactSnapshotComplete",
                  "ChooseInteraction(UnitState,", "ReadyObjectiveAction",
                  "bSecondBlue && ContactStatus != 0",
                  "bSecondBlue && CoverRisk > 0.0",
                  "bSecondBlue && bStealthRisk",
                  "if (!bSecondBlue && Path.Length < 2 && RiskyRoute.Length > 1)",
                  "if (!bSecondBlue && Path.Length < 2 && LocalFallbackPath.Length > 1)"):
            self.assertIn(t, choose)
        for t in ("BuildPathToTile(", "GetPathCostToTile(",
                  "PathCost > UnitVisualizer.GetMobility()",
                  "HasBlockingHazard(", "IsSupportedAdvanceStep("):
            self.assertIn(t, prefix)
        for t in ("RouteTempo.Refresh(", "RouteTempo.RecordAccepted(",
                  "BestUnit.ObjectID == SelectedRouteUnitID",
                  "BestPath[BestPath.Length - 1] == SelectedRouteDestination",
                  "PatrolAmbushPlanner.HasActiveStaging()", "GameStateMoveUnitSingle("):
            self.assertIn(t, decision)
        self.assertNotIn("Mobility * 2", choose)
        exposure = function_body(self.mission, "BlueRouteExposureSafe")
        self.assertIn("Path.Length > 64", exposure)
        self.assertIn("for (Index = 1; Index < Path.Length", exposure)
        self.assertIn("IsRoutineBlueExposureAllowed(", exposure)
        self.assertIn("BlueRouteExposureSafe(UnitState, Path", choose)
        self.assertIn("BlueRouteExposureSafe(UnitState,", choose)
        self.assertIn("bMemoryFallbackFirstClear", choose)
        self.assertIn("bTempoCurrentPathSafe", choose)
        cover = function_body(self.mission, "BlueRouteExplosiveSafe")
        self.assertIn("RemainingTempoCoverChecks < Path.Length - 1", cover)
        self.assertIn("for (Index = 1; Index < Path.Length", cover)
        self.assertIn("--RemainingTempoCoverChecks;", cover)
        self.assertIn("APX_ExplosiveCoverKnowledge'.static.RiskAtTile(", cover)
        self.assertIn("BlueRouteExplosiveSafe(UnitState, Path", choose)
        self.assertIn("BlueRouteExplosiveSafe(UnitState, CandidatePath", choose)
        self.assertIn("RemainingTempoCoverChecks", decision)

    def test_soft_memory_preferred_but_only_native_return_still_allowed(self):
        choose = function_body(self.mission, "ChooseMove")
        prefix = function_body(self.mission, "ChooseRoutePrefix")
        explore = function_body(self.exploration, "ChooseMove")
        explore_prefix = function_body(self.exploration, "BuildSafeBluePrefix")
        self.assertIn("MemoryFallbackPath", choose)
        can_use = function_body(self.controller, "CanUseMove")
        for emergency in ("ShouldEvacuate(UnitState)", "HasBleedingSquadmate(UnitState)",
                          "HasActiveMissionDeadline()", "NeedsPoisonEscape(UnitState)"):
            self.assertIn(emergency, can_use)
        self.assertIn("VisitedPositions[Index].Tile == Path[Path.Length - 1]", can_use)
        self.assertIn("if (Path.Length < 2 && MemoryFallbackPath.Length > 1)", choose)
        self.assertIn("RouteTempo.PenaltyFor(", choose)
        self.assertIn("RouteTempo.PenaltyFor(", prefix)
        self.assertIn("RouteTempo.SetGoal(", explore)
        self.assertIn("RouteTempo.PenaltyFor(", explore_prefix)
        self.assertIn("SelectedGoal = Goals[GoalIndex].Tile", explore)

    def test_active_ambush_is_real_preparation_not_just_approach(self):
        gate = function_body(self.ambush, "HasActiveStaging")
        for t in ("Phase == 'setup'", "Phase == 'armed'", "!bExpired",
                  "PreparedMoves > 0 || OrderedReactions > 0"):
            self.assertIn(t, gate)
        self.assertNotIn("Phase == 'approach'", gate)

    def test_off_and_destroy_reset_memory_and_no_game_state_mutation(self):
        self.assertIn("RouteTempo.Reset()", function_body(self.controller, "StopAutoplay"))
        self.assertIn("RouteTempo.Reset()", function_body(self.controller, "Destroyed"))
        for disallowed in ("SubmitGameState(", "ModifyStateObject(",
                           "CreateNewGameState(", "SYNC_RAND", "Rand(",
                           "ShouldMoveToIntercept("):
            self.assertNotIn(disallowed, CHECKS.without_comments(self.memory))
        for t in ("EnableSequentialBlue=true", "EnableSoftRouteMemory=true",
                  "MaxVisitEntries=96", "MaxMemoryTurns=3", "MaxTempoCoverChecks=48"):
            self.assertIn(t, INI.read_text(encoding="utf-8-sig"))
        self.assertIn("mission-report-v41",
                      (SRC / "APX_MissionRecorder.uc").read_text(encoding="utf-8-sig"))


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"),
                     "Private WOTC SDK unavailable on public CI")
class NativeSDKContracts(unittest.TestCase):
    def test_real_path_cost_native_ap_and_cache(self):
        root = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"]))
        def read(name):
            return (root / "XComGame/Classes" / name).read_text(encoding="utf-8-sig")
        c, u = read("XComTacticalController.uc"), read("XComGameState_Unit.uc")
        a, t = read("X2AbilityCost_ActionPoints.uc"), read("X2ReachableTilesCache.uc")
        for term in ("CostIncreases.AddItem(i)", "GetPathCostToTile(PathData.MovementTiles[i])"):
            self.assertIn(term, c)
        for term in ("NumActionPointsForMoving()", "GetStandardMoveAbilityActionTypes()"):
            self.assertIn(term, u)
        for term in ("iPointsToTake++", "CostIncreases.Length",
                     "AllowedTypes", "ApplyCost("):
            self.assertIn(term, a)
        for term in ("GetPathCostToTile(", "IsTileReachable(", "BuildPathToTile("):
            self.assertIn(term, t)


if __name__ == "__main__":
    unittest.main()
