"""#101 — Windows v43 SabotageCC turn22 native-route deadlock regression.

The numeric policy runs actual UnrealScript source, while path/discovery
assertions are contracts, NOT a simulation of UnrealScript native execution.
Private game logs are deliberately not copied into the repository.
"""
from pathlib import Path
from itertools import permutations
import math
import unittest

from test_ui_gating import braced_body, function_body
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
        self.assertLess(self.score(0.5, 0.1, 0, 0, 0, True, True), -1000)
        # A native-verified actor can be nearer than 3 tiles while the
        # generic map marker wrongly reports the objective as "arrived".
        self.assertGreater(self.score(2.5, 1.2, 0, 0, 0, True, True), 2)
        self.assertGreater(self.score(17, 16, 0, 3.0, 30, True, True), 2)
        self.assertGreater(self.score(17, 15, 0, 0, 12, True, True),
                           self.score(17, 16, 0, 0, 12, True, True))

    def test_later_constructive_action_prevents_expensive_recovery_for_both_roster_orders(self):
        """Exercise the actual recovery gate and its different utility scale."""
        may_search = load_uc_function(CONTROLLER, "ShouldSearchSabotageRecovery")
        recovery = self.score(17, 12, 0, 0, 0, True, True)
        self.assertEqual(recovery, 38)
        for scores in permutations((2, 33)):
            with self.subTest(order=scores):
                self.assertFalse(may_search(max(scores), True))
        self.assertTrue(may_search(2, True))
        self.assertTrue(may_search(-10000, True))
        self.assertFalse(may_search(2, False))


class NativeRecoverySourceSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mission = MISSION.read_text(encoding="utf-8-sig")
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")
        cls.plant = PLANT.read_text(encoding="utf-8-sig")

    def test_real_stock_socket_precedes_generic_high_z_marker_without_fake_interact(self):
        """Only the public mission marker can substitute for unknown X4 geometry."""
        f = function_body(self.mission, "ChooseSabotageCCRecoveryMove")
        resolver = function_body(self.mission, "FindBerserkerSabotageGoal")
        self.assertNotIn("FindGoal(", f)
        self.assertNotIn("ConsiderGoal(", resolver)
        self.assertNotIn("GetRequiresObjectiveGlint(", resolver)
        self.assertNotIn("IterateByClassType(", resolver)
        for token in ('BattleData.MapData.ActiveMission.sType == "SabotageCC"',
                      "GetImmediateThreats(Soldier, Immediate)",
                      "FindBerserkerSabotageGoal(Soldier, BattleData, GoalTile,",
                      "NativePlantReason, NativePlantStatus, GoalAStarPath)",
                      "NativePlantStatus == 0 && TileDistance(Soldier.TileLocation, GoalTile) <= 3.0",
                      '"native_plant_already_consumed"'):
            self.assertIn(token, f)
        self.assertLess(f.index("FindBerserkerSabotageGoal("), f.index("GetClosestReachableDestination("))
        self.assertEqual(1, resolver.count("FindInteractionGoal("))
        for ordering in ("if (NativeGoalStatus > 0)", "if (NativeGoalStatus < 0)"):
            self.assertLess(resolver.index(ordering), resolver.index("BattleData.MapData.ObjectiveLocation"))
        for token in ("GoalTile = NativeGoalTile;", "IsTileOutOfRange(MarkerTile)", "GoalTile = MarkerTile;"):
            self.assertIn(token, resolver)
        self.assertIn("NativePlantPointOnTile(", self.plant)
        for code in (f, resolver):
            for forbidden in ("ActivateAbility_ReturnContext(", "SubmitGameState(", "ModifyStateObject("):
                self.assertNotIn(forbidden, code)

    def test_one_recovery_step_requires_visibility_terrain_support_and_exposure(self):
        """A dangerous middle or final tile must veto a path through the same validator."""
        step = function_body(self.mission, "InspectSabotageStep")
        for token in ("!IsKnownCombatTile(Tile)", "HasBlockingHazard(Soldier, Tile)",
                      "!IsRecoveryFormationAllowed(StartSupport, NearestSupportDistance(Soldier, Tile))",
                      "Risk = ExposureRisk(Soldier, Tile, KnownEnemies, Reaches, Weights);",
                      "return Risk <= CurrentRisk + 3.0;"):
            self.assertIn(token, step)

    def test_bounded_native_cache_exact_path_current_clear_and_covered_all_tiles(self):
        """An unsafe step, unreachable endpoint or incomplete route cannot reach ranking."""
        path = function_body(self.mission, "BuildSabotageRecoveryPath")
        f = function_body(self.mission, "ChooseSabotageCCRecoveryMove")
        for token in ("CandidatePath.Length = 0;", "!Visualizer.m_kReachableTilesCache.IsTileReachable(Tile)",
                      "GetPathCostToTile(Tile)", "Cost < 0.0 || Cost > Visualizer.GetMobility()",
                      "!InspectSabotageStep(Soldier, Tile,", "BuildPathToTile(Tile, CandidatePath)",
                      "CandidatePath.Length < 2 || CandidatePath.Length > 48",
                      "CandidatePath[0] != Soldier.TileLocation", "CandidatePath[CandidatePath.Length - 1] != Tile",
                      "PathIndex = 1; PathIndex < CandidatePath.Length - 1; ++PathIndex",
                      "!InspectSabotageStep(Soldier, CandidatePath[PathIndex]"):
            self.assertIn(token, path)
        for token in ("GetAllPathableTiles(Tiles, Visualizer.GetMobility())",
                      "GetClosestReachableDestination(GoalTile)", "Count = Min(48, Tiles.Length + RouteSamples + 1)",
                      "GetVisibleThreats(Soldier, KnownEnemies)", "GetMeleeThreatReaches(Soldier, KnownEnemies",
                      "GetThreatWeights(Soldier, KnownEnemies", "AssessRoute(",
                      "bSnapshotComplete, SnapshotReason, 0", "RemainingContactDetectors",
                      "RemainingContactTiles", "RemainingContactLOS", "RemainingCoverChecks",
                      "RemainingTempoCoverChecks", "RemainingConcealmentChecks", "SabotageCC objective recovery|unit="):
            self.assertIn(token, f)
        stages = ("BuildSabotageRecoveryPath(", "InspectPathRisk(", "BlueRouteExplosiveSafe(",
                  "AssessRoute(", "if (ContactStatus != 0)", "InspectRiskAtTile(", "ScoreSabotageRecovery(")
        self.assertEqual(sorted(map(f.index, stages)), list(map(f.index, stages)))

    def test_recovery_runs_once_after_normal_and_ambush_plans_before_dispatch(self):
        """Bind the gate to squad-wide arbitration and the common native dispatch."""
        decision = function_body(self.controller, "MakeDecision")
        gate = decision.index("ShouldSearchSabotageRecovery(BestScore,")
        for normal in ("ChooseLootMove(", "ExplorationPlanner.ChooseMove(",
                       "PatrolAmbushPlanner.ChooseReactionSupport(", "ChoosePreparation("):
            self.assertLess(decision.index(normal), gate)
        self.assertEqual(1, decision.count("SelectSquadSabotageRecovery("))
        call = decision.index("SelectSquadSabotageRecovery(", gate)
        self.assertIn('FocusBattle.MapData.ActiveMission.sType == "SabotageCC"', decision[gate:call])
        self.assertIn("PC.m_XGPlayer, BestUnit, BestPath, BestScore", decision[call:])
        flags = braced_body(decision, decision.index("{", call))
        for update in ("bMove = true;", "bArea = false;", "bHavePlan = true;",
                       "BestLocations.Length = 0;", "bSelectedRoute = false;",
                       "bSelectedPatrolMove = false;", "bSelectedPatrolReaction = false;"):
            self.assertIn(update, flags)
        self.assertLess(call, decision.index('StopWithStatus("SabotageCC:'))
        self.assertLess(call, decision.index("PC.GameStateMoveUnitSingle("))

    def test_every_eligible_native_recovery_can_replace_an_earlier_lower_score(self):
        """Check the real roster loop ranks all candidates and keeps a winner after rejection."""
        select = function_body(self.controller, "SelectSquadSabotageRecovery")
        loop = select.index("for (Index = 0; Index < Count; ++Index)")
        for check in ("SquadPlayer == none", "SquadPlayer.m_kSquad == none",
                      "Squad.m_kPlayer != SquadPlayer", "Count <= 0 || Count > 24"):
            self.assertIn(check, select[:loop])
        body = braced_body(select, select.index("{", loop))
        for required in ("ResolveRecoverySoldier(Squad.GetMemberAt(Index), SquadPlayer.ObjectID)",
                         "ChooseSabotageCCRecoveryMove(", "RemainingContactDetectors",
                         "RemainingContactTiles", "RemainingContactLOS", "RemainingCoverChecks",
                         "RemainingConcealmentChecks", "RemainingTempoCoverChecks",
                         "CanUseMove(Soldier, CandidatePath)", 'Marker("objective_recovery_scan"'):
            self.assertIn(required, body)
        rank = body.index("Score <= BestScore")
        update = body.index("BestScore = Score;")
        self.assertLess(rank, body.index("continue;", rank))
        self.assertLess(body.index("continue;", rank), update)
        for op in ("BestUnit = Soldier;", "BestPath = CandidatePath;", "bSelected = true;"):
            self.assertIn(op, body[rank:])
        self.assertNotIn("break;", body)
        self.assertNotIn("return", body)
        self.assertNotIn("ShouldSearchSabotageRecovery(", body)
        self.assertNotIn("BestScore <= 2", body)
        self.assertIn('Marker("objective_recovery_candidate"', select[loop:])
        self.assertIn("return bSelected;", select[loop:])

    def test_recovery_passes_only_current_soldier_visited_tiles(self):
        """Reject individual same-turn endpoints before ranking, without touching other soldiers' paths."""
        copy = function_body(self.controller, 'GetVisitedRecoveryEndpoints')
        sequence = ('Endpoints.Length = 0;', 'foreach VisitedPositions(Position)',
                    'if (Position.UnitID == SoldierID)', 'Endpoints.AddItem(Position.Tile);')
        self.assertEqual(sorted(map(copy.index, sequence)), list(map(copy.index, sequence)))
        self.assertNotIn('VisitedPositions.Length =', copy)

        select = function_body(self.controller, 'SelectSquadSabotageRecovery')
        gather = select.index('GetVisitedRecoveryEndpoints(Soldier.ObjectID, VisitedEndpoints);')
        planner = select.index('ChooseSabotageCCRecoveryMove(', gather)
        guard = select.index('CanUseMove(Soldier, CandidatePath)', planner)
        self.assertIn('RemainingTempoCoverChecks, VisitedEndpoints);', select[planner:guard])

    def test_recovery_rereads_squad_member_and_rejects_missing_removed_or_hostile_state(self):
        """Reject stale visualizers and units that cannot issue the native move."""
        resolve = function_body(self.controller, "ResolveRecoverySoldier")
        for guard in ("Member == none || Member.ObjectID <= 0",
                      "GetGameStateForObjectID(Member.ObjectID)",
                      "Soldier == none || Soldier.GetMyTemplate() == none",
                      "Soldier.GetAssociatedPlayerID() != PlayerID",
                      "Soldier.GetTeam() != eTeam_XCom",
                      "!Soldier.IsAlive()", "!Soldier.IsAbleToAct()", "Soldier.IsCivilian()",
                      "Soldier.bRemoved || Soldier.bRemovedFromPlay",
                      "Soldier.GetMyTemplate().bIsCosmetic"):
            self.assertIn(guard, resolve)
        self.assertIn("return none;", resolve)
        self.assertIn("return Soldier;", resolve)

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
