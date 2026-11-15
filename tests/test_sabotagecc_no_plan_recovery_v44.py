"""#101 — Windows v43 SabotageCC turn22 native-route deadlock regression.

The numeric policy runs actual UnrealScript source, while path/discovery
assertions are contracts, NOT a simulation of UnrealScript native execution.
Private game logs are deliberately not copied into the repository.
"""
from pathlib import Path
import math
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
MISSION = SRC / "APX_MissionPlanner.uc"
CONTROLLER = SRC / "APX_Controller.uc"
PLANT = SRC / "APX_PlantInteractionKnowledge.uc"


class NativeObjectiveRecoveryPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eligibility = staticmethod(load_uc_function(
            MISSION, "CanAttemptSabotageRecovery"))
        cls.formation = staticmethod(load_uc_function(
            MISSION, "IsRecoveryFormationAllowed"))
        cls.score = staticmethod(load_uc_function(
            MISSION, "ScoreSabotageRecovery"))

    def test_repro_from_real_v43_log_progress_while_two_ap_remain(self):
        # v43 session 2026-11-15_2-5-23-751_888 turn22:
        # D97-D104 eight stops, soldiers 416 at (16,32,1), 422 at
        # (23,32,1) and the native mission marker (40,34,2).
        # This is a scoring/eligibility fixture, NOT proof a particular
        # native tile (25,32,1) is reachable in the running game.
        goal = (40, 34, 2)
        def distance(tile):
            return math.sqrt((tile[0]-goal[0])**2
                             + (tile[1]-goal[1])**2
                             + ((tile[2]-goal[2])*0.5)**2)
        front = (23, 32, 1)
        candidate = (25, 32, 1)
        self.assertTrue(self.eligibility(True, True, False,
                                         False, False, True, 2))
        self.assertTrue(self.formation(7.0, 9.0))
        self.assertGreater(self.score(distance(front), distance(candidate),
                                      0.0, 0.0, 12.0, True, True), 20.0)

    def test_only_current_real_sabotage_objective_native_move_is_eligible(self):
        for args in (
            (False, True, False, False, False, True, 2),
            (True, False, False, False, False, True, 2),
            (True, True, True, False, False, True, 2),
            (True, True, False, True, False, True, 2),
            (True, True, False, False, True, True, 2),
            (True, True, False, False, False, False, 2),
            (True, True, False, False, False, True, 1),
        ):
            with self.subTest(args=args):
                self.assertFalse(self.eligibility(*args))
        self.assertTrue(self.eligibility(True, True, False, False,
                                         False, True, 3))

    def test_bounded_support_not_unrestricted_solo_overextension(self):
        self.assertTrue(self.formation(7.0, 10.0))
        self.assertTrue(self.formation(7.0, 11.0))
        self.assertFalse(self.formation(7.0, 11.1))
        self.assertTrue(self.formation(9.0, 13.0))
        self.assertFalse(self.formation(9.0, 13.1))
        self.assertTrue(self.formation(10.0, 14.0))
        self.assertFalse(self.formation(10.0, 14.01))
        self.assertFalse(self.formation(5.0, 10.1))

    def test_no_progress_hazard_or_unknown_cannot_be_scored_constructive(self):
        self.assertLess(self.score(17, 16, 0, 0, 0, False, True), -1000)
        self.assertLess(self.score(17, 16, 0, 0, 0, True, False), -1000)
        self.assertLess(self.score(17, 17, 0, 0, 0, True, True), -1000)
        self.assertLess(self.score(17, 18, 0, 0, 0, True, True), -1000)
        self.assertLess(self.score(17, 16, 0, 4.0, 0, True, True), -1000)
        self.assertLess(self.score(3, 2, 0, 0, 0, True, True), -1000)
        self.assertGreater(self.score(17, 16, 0, 3.0, 30, True, True), 2)
        self.assertGreater(self.score(17, 15, 0, 0, 12, True, True),
                           self.score(17, 16, 0, 0, 12, True, True))


class NativeRecoverySourceSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mission = MISSION.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")
        cls.plant = PLANT.read_text(encoding="utf-8-sig")

    def test_real_stock_socket_precedes_generic_high_z_marker_without_fake_interact(self):
        f = function_body(self.mission, "ChooseSabotageCCRecoveryMove")
        for token in (
            'BattleData.MapData.ActiveMission.sType == "SabotageCC"',
            "Soldier.FindAbility('Interact_PlantBomb').ObjectID > 0",
            "GetImmediateThreats(Soldier, Immediate)",
            "FindGoal(Soldier, Goal, KnownEnemies)",
            "class'APX_PlantInteractionKnowledge'.static.FindInteractionGoal(",
            "NativePlantStatus < 0", "if (NativePlantStatus > 0)",
            "GoalTile = VerifiedPlantTile", "GoalTile = Goal.Tile",
            '"native_plant_already_consumed"',
        ):
            self.assertIn(token, f)
        self.assertLess(f.index("FindInteractionGoal("),
                        f.index("GetClosestReachableDestination(GoalTile)"))
        self.assertIn("NativePlantPointOnTile(", self.plant)
        self.assertNotIn("ActivateAbility_ReturnContext(", f)
        self.assertNotIn("SubmitGameState(", f)
        self.assertNotIn("ModifyStateObject(", f)

    def test_bounded_native_cache_exact_path_current_clear_and_covered_all_tiles(self):
        f = function_body(self.mission, "ChooseSabotageCCRecoveryMove")
        for token in (
            "GetAllPathableTiles(Tiles, Visualizer.GetMobility())",
            "GetClosestReachableDestination(GoalTile)",
            "Count = Min(48, Tiles.Length)",
            "IsTileReachable(Tile)",
            "GetPathCostToTile(Tile)",
            "Cost > Visualizer.GetMobility()",
            "BuildPathToTile(Tile, CandidatePath)",
            "CandidatePath.Length > 48",
            "CandidatePath[0] != Soldier.TileLocation",
            "CandidatePath[CandidatePath.Length - 1] != Tile",
            "IsKnownCombatTile(",
            "HasBlockingHazard(",
            "IsRecoveryFormationAllowed(",
            "ExposureRisk(",
            "CurrentRisk + 3.0",
            "InspectPathRisk(",
            "BlueRouteExplosiveSafe(",
            "APX_ContactEnvelope'.static.AssessRoute(",
            "bSnapshotComplete, SnapshotReason, 0",
            "if (ContactStatus != 0)",
            "InspectRiskAtTile(",
            "RemainingContactDetectors",
            "RemainingContactTiles",
            "RemainingContactLOS",
            "RemainingCoverChecks",
            "RemainingTempoCoverChecks",
            "RemainingConcealmentChecks",
            "ScoreSabotageRecovery(",
            'SabotageCC objective recovery|unit=',
        ):
            self.assertIn(token, f)
        self.assertLess(f.index("BuildPathToTile("),
                        f.index("APX_ContactEnvelope'.static.AssessRoute("))
        self.assertLess(f.index("if (ContactStatus != 0)"),
                        f.index("ScoreSabotageRecovery("))

    def test_only_when_normal_planner_has_no_constructive_action_and_native_dispatch(self):
        f = function_body(self.controller, "MakeDecision")
        self.assertIn('if (BestScore <= 2.0 && FocusBattle != none', f)
        self.assertIn('FocusBattle.MapData.ActiveMission.sType == "SabotageCC"', f)
        self.assertLess(f.index("class'APX_MissionPlanner'.static.ChooseMove("),
                        f.index("class'APX_MissionPlanner'.static.ChooseSabotageCCRecoveryMove("))
        self.assertIn("TraceCandidateMove(UnitState, CandidatePath, Score)", f)
        self.assertIn("CanUseMove(UnitState, CandidatePath)", f)
        self.assertIn("BestPath = CandidatePath;", f)
        self.assertIn("bSelectedRoute = false;", f)
        self.assertIn('MissionRecorder.Marker("objective_recovery_scan"', f)
        self.assertIn('MissionRecorder.Marker("objective_recovery_candidate"', f)
        self.assertIn('"No constructive action or understood mission goal"', f)
        self.assertIn('"SabotageCC: no currently verified native X4 route;', f)
        self.assertIn("GameStateMoveUnitSingle(", f)
        self.assertNotIn("RequestEndTurn(PC); // Native confirmed end-turn ticket still applies.",
                         function_body(self.mission, "ChooseSabotageCCRecoveryMove"))

    def test_dont_change_other_sabotage_timers_bleeding_rescue_medical_aoe(self):
        decision = function_body(self.controller, "MakeDecision")
        for old in (
            "ChooseRescueMove(", "ChooseMedicalMove(", "ChoosePoisonEscape(",
            "ChooseReactionSupport(", "ChooseLootMove(", "ChooseInteraction(",
            "TraceCandidateAction(", "APX_AreaAttackPlanner",
            "PatrolAmbushPlanner.CanWaitForContact()",
        ):
            self.assertIn(old, decision)
        for old in ("ShouldEvacuate(Soldier)",
                    "HasBleedingSquadmate(Soldier)"):
            self.assertIn(old, function_body(self.mission, "ChooseSabotageCCRecoveryMove"))


if __name__ == "__main__":
    unittest.main()
