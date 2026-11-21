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


class VerifiedX4AStarUnitTests(unittest.TestCase):
    """Run exactly the pure UC helpers used by the new detour policy."""

    @classmethod
    def setUpClass(cls):
        """Load real UC, not copied Python algorithms."""
        cls.verify = staticmethod(load_uc_function(MISSION, "HasVerifiedX4AStarGeometry"))
        cls.detour = staticmethod(load_uc_function(MISSION, "ScoreSabotageAStarDetour"))
        cls.old_progress = staticmethod(load_uc_function(MISSION, "ScoreSabotageRecovery"))

    def test_complete_bounded_path_requires_verified_current_origin_and_socket(self):
        """Partial paths, wrong source, wrong socket and overlong paths fail."""
        self.assertTrue(self.verify(True, 20, True, True))
        self.assertTrue(self.verify(True, 256, True, True))
        for value in ((False, 20, True, True), (True, 1, True, True),
                      (True, 257, True, True), (True, 20, False, True),
                      (True, 20, True, False)):
            with self.subTest(value=value):
                self.assertFalse(self.verify(*value))

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

    def test_verified_actor_socket_precedes_advisory_full_astar(self):
        """A* never gets an unverified generic target promoted into PlantBomb."""
        recovery = function_body(self.mission, "ChooseSabotageCCRecoveryMove")
        for token in ("FindBerserkerSabotageGoal(Soldier, BattleData, GoalTile,",
                      "native_plant_already_consumed",
                      "X2PathSolver'.static.BuildPath(",
                      "HasVerifiedX4AStarGeometry(", "GoalAStarPath[0] == Soldier.TileLocation",
                      "GoalAStarPath[GoalAStarPath.Length - 1] == GoalTile",
                      "RouteSamples = Min(24, GoalAStarPath.Length - 1)"):
            self.assertIn(token, recovery)
        self.assertLess(recovery.index("FindBerserkerSabotageGoal("),
                        recovery.index("X2PathSolver'.static.BuildPath("))
        self.assertLess(recovery.index("HasVerifiedX4AStarGeometry("),
                        recovery.index("for (Sample = 0; Sample < Count; ++Sample)"))

    def test_bluerange_sampling_contains_astar_prefix_and_retains_combined_budget(self):
        """Up to 24 prefix nodes plus bounded other native endpoints, at most 48."""
        recovery = function_body(self.mission, "ChooseSabotageCCRecoveryMove")
        for token in ("GetAllPathableTiles(Tiles, Visualizer.GetMobility())",
                      "GetClosestReachableDestination(GoalTile)",
                      "Count = Min(48, Tiles.Length + RouteSamples + 1)",
                      "bRouteWaypoint = Sample > 0 && Sample <= RouteSamples",
                      "Tile = GoalAStarPath[Sample]",
                      "Tile = Tiles[Index]",
                      "(!bRouteWaypoint && Progress < 1.0)",
                      "ScoreSabotageAStarDetour(Sample,",
                      "ScoreSabotageRecovery(CurrentDistance,",
                      "safe_native_blue_on_verified_x4_astar_prefix"):
            self.assertIn(token, recovery)
        self.assertLess(recovery.index("Tile = GoalAStarPath[Sample]"),
                        recovery.index("BuildSabotageRecoveryPath("))

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
                      "skipped_no_progress=", "clear_routes="):
            self.assertIn(token, recovery)
        controller = function_body(self.controller, "SelectSquadSabotageRecovery")
        self.assertIn("ChooseSabotageCCRecoveryMove(", controller)
        self.assertIn("CanUseMove(Soldier, CandidatePath)", controller)
        self.assertIn('Marker("objective_recovery_candidate"', controller)


if __name__ == "__main__":
    unittest.main()
