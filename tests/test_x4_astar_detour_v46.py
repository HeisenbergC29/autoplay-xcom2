"""#106: source-verified native A* detour to stock X4 interaction point.

Pure rank/geometry predicates execute the actual UnrealScript source. Native
stock A*, reachability, hazards and game outcomes remain source contracts
and require a separate Windows WOTC gameplay E2E.
"""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
MISSION = CLASSES / "APX_MissionPlanner.uc"
CONTROLLER = CLASSES / "APX_Controller.uc"
PLANT = CLASSES / "APX_PlantInteractionKnowledge.uc"


class VerifiedX4AStarUnitTests(unittest.TestCase):
    """Run exactly the pure UC helpers used by the new detour policy."""

    @classmethod
    def setUpClass(cls):
        """Load real UC, not copied Python algorithms."""
        cls.verify = staticmethod(load_uc_function(MISSION, "HasVerifiedX4AStarGeometry"))
        cls.detour = staticmethod(load_uc_function(MISSION, "ScoreSabotageAStarDetour"))
        cls.old_progress = staticmethod(load_uc_function(MISSION, "ScoreSabotageRecovery"))
        cls.sample_index = staticmethod(load_uc_function(MISSION, "SabotageAStarSampleIndex"))
        cls.contact_budget = staticmethod(load_uc_function(MISSION, "HasSabotageContactScanBudget"))

    def test_complete_bounded_path_requires_verified_current_origin_and_socket(self):
        """Partial paths, wrong source, wrong socket and overlong paths fail."""
        self.assertTrue(self.verify(1, 20, True, True))
        self.assertTrue(self.verify(1, 256, True, True))
        for value in ((0, 20, True, True), (-1, 20, True, True), (1, 1, True, True),
                      (1, 257, True, True), (1, 20, False, True),
                      (1, 20, True, False)):
            with self.subTest(value=value):
                self.assertFalse(self.verify(*value))

    def test_longest_prefix_has_first_use_of_shared_budget(self):
        """Try deeper native waypoints before shorter ones and uniform samples."""
        self.assertEqual([4, 3, 2, 1, 0, 0], [self.sample_index(i, 4) for i in range(6)])
        self.assertEqual(0, self.sample_index(0, 0))
        self.assertEqual(0, self.sample_index(-1, 4))

    def test_unverifiable_long_candidate_cannot_consume_short_candidate_budget(self):
        """Every clear tile requires a visit to every known detector."""
        self.assertTrue(self.contact_budget(3, 11, 33, 3, 4))
        self.assertTrue(self.contact_budget(2, 11, 32, 3, 4))
        self.assertTrue(self.contact_budget(3, 0, 1, 3, 1))
        for args in ((3, 11, 32, 3, 4), (3, 11, 33, 2, 4), (3, 11, 33, 3, 0),
                     (3, 0, 0, 3, 4), (0, 11, 33, 3, 4)):
            with self.subTest(args=args):
                self.assertFalse(self.contact_budget(*args))

    def test_verified_detour_is_constructive_even_when_direct_distance_increases(self):
        """A true stock path waypoint can first go away from the X4 socket."""
        self.assertLess(self.old_progress(14, 16, 0, 0, 0, True, True), -1000)
        self.assertGreater(self.detour(1, 0, 0, 0, True, True), 2)
        self.assertGreater(self.detour(4, 0, 0, 0, True, True),
                           self.detour(1, 0, 0, 0, True, True))
        self.assertLessEqual(self.detour(40, 0, 0, 0, True, True), 36)

    def test_route_clear_risk_and_actual_waypoint_index_remain_hard_gates(self):
        """Neither unknown contacts nor a dangerous blue endpoint score positive."""
        for args in ((0, 0, 0, 0, True, True),
                     (-1, 0, 0, 0, True, True),
                     (2, 0, 0, 0, False, True),
                     (2, 0, 0, 0, True, False),
                     (2, 0, 3.01, 0, True, True)):
            with self.subTest(args=args):
                self.assertLess(self.detour(*args), -1000)
        self.assertGreater(self.detour(2, 0, 3, 24, True, True), 2)


class VerifiedX4AStarIntegrationContracts(unittest.TestCase):
    """Source-level E2E pipeline: stock goal -> native blue -> full safety -> dispatch."""

    @classmethod
    def setUpClass(cls):
        """Inspect currently checked-in source for the real tactical pipeline."""
        cls.mission = MISSION.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")

    def test_verified_actor_socket_reuses_its_already_solved_route(self):
        """Recovery receives the native path from the verified actor, with no second solve."""
        recovery = function_body(self.mission, "ChooseSabotageCCRecoveryMove")
        for token in ("FindBerserkerSabotageGoal(Soldier, BattleData, GoalTile,",
                      "NativePlantReason, NativePlantStatus, GoalAStarPath",
                      "native_plant_already_consumed",
                      "HasVerifiedX4AStarGeometry(NativePlantStatus,",
                      "GoalAStarPath[0] == Soldier.TileLocation",
                      "GoalAStarPath[GoalAStarPath.Length - 1] == GoalTile",
                      "RouteSamples = Min(24, GoalAStarPath.Length - 1)"):
            self.assertIn(token, recovery)
        self.assertNotIn("X2PathSolver'.static.BuildPath(", recovery)
        resolver = function_body(self.mission, "FindBerserkerSabotageGoal")
        self.assertLess(resolver.index("VerifiedPath.Length = 0;"),
                        resolver.index("NativeGoalStatus = class'APX_PlantInteractionKnowledge'"))
        self.assertIn("UnitState, NativeGoalTile, NativeGoalReason, VerifiedPath", resolver)
        self.assertNotIn("BuildPath(", resolver)
        plant = PLANT.read_text(encoding="utf-8-sig")
        discovery = function_body(plant, "FindInteractionGoalResult")
        self.assertLess(discovery.index("VerifiedPath.Length = 0;"),
                        discovery.index("X2PathSolver'.static.BuildPath("))
        self.assertLess(discovery.index("FullPath[FullPath.Length - 1] == Candidate"),
                        discovery.index("VerifiedPath = FullPath;"))
        self.assertEqual(1, discovery.count("X2PathSolver'.static.BuildPath("))
        self.assertIn("PathChecks < 4", discovery)

    def test_bluerange_sampling_prioritizes_deep_unique_unvisited_points_within_budget(self):
        """Cheapest exclusions and inspection feasibility precede shared safety budget use."""
        recovery = function_body(self.mission, "ChooseSabotageCCRecoveryMove")
        for token in ("GetAllPathableTiles(Tiles, Visualizer.GetMobility())",
                      "GetClosestReachableDestination(GoalTile)",
                      "Count = Min(48, Tiles.Length + RouteSamples + 1)",
                      "RouteIndex = SabotageAStarSampleIndex(Sample, RouteSamples)",
                      "Tile = GoalAStarPath[RouteIndex]",
                      "else if (Sample == RouteSamples)", "Tile = Tiles[Index]",
                      "if (RouteIndex == 0 && Progress < 1.0)",
                      "ScoreSabotageAStarDetour(RouteIndex,",
                      "ScoreSabotageRecovery(CurrentDistance,",
                      "safe_native_blue_on_verified_x4_astar_prefix"):
            self.assertIn(token, recovery)
        stages = ("Tile = GoalAStarPath[RouteIndex]", "ContainsTile(CheckedEndpoints, Tile)",
                  "CheckedEndpoints.AddItem(Tile)", "ContainsTile(VisitedEndpoints, Tile)",
                  "BuildSabotageRecoveryPath(", "HasSabotageContactScanBudget(",
                  "BlueRouteExplosiveSafe(", "AssessRoute(")
        positions = [recovery.index(stage) for stage in stages]
        self.assertEqual(sorted(positions), positions)

    def test_native_full_blue_hazard_cover_contact_budgets_and_replan_remain_mandatory(self):
        """No bypass around source-gated hazards, FOW, contact or action points."""
        recovery = function_body(self.mission, "ChooseSabotageCCRecoveryMove")
        path = function_body(self.mission, "BuildSabotageRecoveryPath")
        for token in ("CanAttemptSabotageRecovery(", "BuildSabotageRecoveryPath(",
                      "InspectPathRisk(", "RemainingConcealmentChecks",
                      "BlueRouteExplosiveSafe(", "RemainingTempoCoverChecks",
                      "AssessRoute(", "if (ContactStatus != 0)",
                      "InspectRiskAtTile(", "RemainingCoverChecks"):
            self.assertIn(token, recovery)
        for token in ("IsTileReachable(Tile)", "GetPathCostToTile(Tile)",
                      "Cost > Visualizer.GetMobility()",
                      "BuildPathToTile(Tile, CandidatePath)",
                      "CandidatePath[0] != Soldier.TileLocation",
                      "CandidatePath[CandidatePath.Length - 1] != Tile",
                      "InspectSabotageStep(", "PathIndex = 1;"):
            self.assertIn(token, path)
        for forbidden in ("SubmitGameState(", "ModifyStateObject(",
                          "ActivateAbility_ReturnContext(",
                          "GameStateMoveUnitSingle("):
            self.assertNotIn(forbidden, recovery)

    def test_rejection_reasons_appear_before_native_controller_move_choice(self):
        """Previously six identical no-plan stops lacked per-stage rejection data."""
        recovery = function_body(self.mission, "ChooseSabotageCCRecoveryMove")
        for token in ("astar_verified=", "astar_prefix_samples=",
                      "rejected_native_path=", "rejected_concealment=",
                      "rejected_explosive=", "rejected_contact=",
                      "skipped_no_progress=", "skipped_visited=", "rejected_budget=",
                      "contact_detectors_before=", "contact_detectors_left=",
                      "tempo_cover_before=", "tempo_cover_left=", "clear_routes="):
            self.assertIn(token, recovery)
        controller = function_body(self.controller, "SelectSquadSabotageRecovery")
        self.assertIn("ChooseSabotageCCRecoveryMove(", controller)
        self.assertIn("CanUseMove(Soldier, CandidatePath)", controller)
        self.assertIn('Marker("objective_recovery_candidate"', controller)


if __name__ == "__main__":
    unittest.main()
