"""Blood Killer / SabotageTransmitter mission-first BerserkerMP contracts.

These tests execute pure policy and scoring helpers from the actual UC file.
They do NOT compile UnrealScript or demonstrate victory/stability in WOTC.
"""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
MISSION = CLASSES / 'APX_MissionPlanner.uc'


class BerserkerSabotageContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MISSION.read_text(encoding='utf-8-sig')
        cls.policy = staticmethod(load_uc_function(
            MISSION, 'ShouldPrioritizeBerserkerSabotage'))
        cls.route = staticmethod(load_uc_function(
            MISSION, 'ScoreBerserkerObjectiveRoute'))
        cls.risk_allowed = staticmethod(load_uc_function(
            MISSION, 'IsBerserkerObjectiveRiskAllowed'))
        cls.keep_objective = staticmethod(load_uc_function(
            MISSION, 'KeepSabotageGoalOnLastAP'))

    def test_only_enabled_berserker_mp_with_unfinished_sabotage_objective(self):
        self.assertTrue(self.policy(True, True, True, False))
        for args in [
            (False, True, True, False),
            (True, False, True, False),
            (True, True, False, False),
            (True, True, True, True)
        ]:
            with self.subTest(args=args):
                self.assertFalse(self.policy(*args))

    def test_route_score_outweighs_routine_backtracking_but_not_deadly_risk(self):
        # A healthy 20-HP melee-only unit should advance the real objective,
        # rather than scoring endless low-value defensive motion at ~20-30.
        self.assertGreater(self.route(5, 1.0, 20.0, 35.0), 30.0)
        self.assertGreater(self.route(5, 1.0, 20.0, 35.0),
                           self.route(2, 1.0, 20.0, 35.0))
        self.assertEqual(self.route(1, 1.0, 20.0, 20.0), -10000.0)
        self.assertEqual(self.route(5, 0.2, 20.0, 40.0), -10000.0)
        self.assertEqual(self.route(5, 1.0, 20.0, 96.0), -10000.0)

    def test_wounded_route_veto_cannot_be_evaded_by_local_fallback(self):
        # This previously rejected prefix could still win the fallback's
        # ordinary distance utility (7 tiles closer, exposure 20 -> 33).
        self.assertFalse(self.risk_allowed(0.2, 20.0, 33.0))
        self.assertEqual(self.route(8, 0.2, 20.0, 33.0), -10000.0)
        self.assertTrue(self.risk_allowed(0.2, 20.0, 32.0))
        self.assertTrue(self.risk_allowed(0.35, 20.0, 33.0))
        self.assertFalse(self.risk_allowed(1.0, 20.0, 96.0))
        self.assertTrue(self.risk_allowed(0.2, 40.0, 20.0))
        choose = function_body(self.source, 'ChooseMove')
        risk_guard = 'if (bSabotageRush && !IsBerserkerObjectiveRiskAllowed('
        self.assertIn(risk_guard, choose)
        self.assertLess(choose.index(risk_guard),
                        choose.index('CandidateScore = PositionScore('))

    def test_last_ap_still_advances_sabotage_but_never_bypasses_native_legality(self):
        self.assertTrue(self.keep_objective(True, 1))
        self.assertTrue(self.keep_objective(True, 2))
        self.assertFalse(self.keep_objective(True, 0))
        self.assertFalse(self.keep_objective(False, 1))
        choose = function_body(self.source, 'ChooseMove')
        rush = 'bSabotageRush = KeepSabotageGoalOnLastAP('
        override = 'if (bSabotageRush)'
        self.assertLess(choose.index(rush), choose.index(override))
        self.assertIn('Goal.bBerserkerSabotageGoal, UnitState.NumActionPoints()', choose)
        self.assertNotIn('if (Goal.bBerserkerSabotageGoal)', choose)
        self.assertIn('RequiresCombatMovement(Goal.bCombat, Goal.bImmediateThreats,', choose)
        self.assertIn('bCombatGoal && !IsUsefulReposition(', choose)
        self.assertIn('MoveOpportunityPenalty(BestAttackNow, BestAttackAfterMove,', choose)
        self.assertIn('if (!Goal.bImmediateThreats && !bRoutineRoute)', choose)
        self.assertIn('if (!HasLegalMove(UnitState)', choose)
        self.assertIn('m_kReachableTilesCache.BuildPathToTile(Tile, CandidatePath)', choose)
        self.assertIn('HasBlockingHazard(UnitState, CandidatePath[PathIndex])', choose)

    def test_only_valid_native_goal_objects_or_objective_marker(self):
        find = function_body(self.source, 'FindBerserkerSabotageGoal')
        for required in (
            'MapData.ObjectiveLocation',
            "IterateByClassType(",
            "class'XComGameState_InteractiveObject', ObjectState",
            'IsUnfinishedObject(ObjectState)',
            'ObjectState.GetRequiresObjectiveGlint()',
            'IsTileOutOfRange(ObjectState.TileLocation)',
            'Considered > 128',
            'BestDistance > 6.0',
            'GoalSource = "objective_glint"',
            'GoalSource = "mission_marker"',
        ):
            with self.subTest(required=required):
                self.assertIn(required, find)
        for forbidden in ('ModifyStateObject', 'CreateNewGameState',
                          'SubmitGameState', 'Interact_PlantBomb(', 'Rand('):
            self.assertNotIn(forbidden, find)

    def test_goal_precedes_contact_rush_only_for_this_mission(self):
        goal = function_body(self.source, 'FindGoal')
        self.assertIn("UnitState.GetMyTemplateName() == 'BerserkerMP'", goal)
        # MissionDefinition.sType is already string; WOTC rejects a redundant
        # string(...) cast with "No need to cast 'StrProperty' to itself".
        self.assertIn('BattleData.MapData.ActiveMission.sType == "SabotageTransmitter"', goal)
        self.assertIn('bCompletedStrategyObjective', goal)
        self.assertIn('Goal.bBerserkerSabotageGoal = true;', goal)
        self.assertIn('Goal.BerserkerSabotageGoalSource = SabotageGoalSource;',goal)
        self.assertLess(goal.index('Goal.bBerserkerSabotageGoal = true;'),
                        goal.index('foreach ImmediateEnemies(EnemyRef)'))
        # Evacuation must outrank any new objective pursuit.
        self.assertLess(goal.index('if (EvacZone != none && ShouldEvacuate(UnitState))'),
                        goal.index('Goal.bBerserkerSabotageGoal = true;'))

    def test_native_route_safety_and_existing_fallback_remain(self):
        choose = function_body(self.source, 'ChooseMove')
        for required in (
            'bSabotageRush = Goal.bBerserkerSabotageGoal',
            'KeepSabotageGoalOnLastAP(',
            'ChooseRoutePrefix(UnitState, UnitVisualizer, GoalTile, Path, bCombatGoal)',
            'HasBlockingHazard(UnitState, CandidatePath[PathIndex])',
            'IsSupportedAdvanceStep(StartSupport,',
            'ScoreBerserkerObjectivePath(UnitState, Path, VisibleEnemies,',
            'if (Score <= -9999.0)',
            'Path.Length = 0;',
            'GetAllPathableTiles(Tiles, UnitVisualizer.GetMobility())',
        ):
            with self.subTest(required=required):
                self.assertIn(required, choose)
        # Previously implemented controls are NOT traded away for a challenge.
        scored = function_body(self.source, 'ScoreBerserkerObjectivePath')
        self.assertIn('ScoreBerserkerObjectiveRoute(Path.Length, HealthFraction,', scored)
        self.assertIn('GetMeleeThreatReaches(UnitState, VisibleEnemies, Reaches)', scored)
        self.assertIn('GetThreatWeights(UnitState, VisibleEnemies, Weights)', scored)
        self.assertIn('"|source=" $ GoalSource', scored)
        self.assertIn('distance_before=', scored)
        self.assertIn('distance_after=', scored)
        self.assertIn('if (bSabotageRush)', choose)
        self.assertIn('bCombatGoal = false;', choose)
        self.assertIn('ScoreBerserkerObjectivePath(UnitState, Path, VisibleEnemies,', choose)
        prefix = function_body(self.source, 'ChooseRoutePrefix')
        self.assertIn('m_kReachableTilesCache.IsTileReachable(', prefix)
        self.assertIn('HasBlockingHazard(', prefix)
        self.assertIn('IsSupportedAdvanceDestination(', prefix)

    def test_config_is_reversible_and_berserker_actions_remain_native(self):
        config=(ROOT/'AutoplayXCom2/Config/XComAutoplayXCom2.ini').read_text()
        self.assertIn('PrioritizeBerserkerSabotage=true',config)
        self.assertIn('var config bool PrioritizeBerserkerSabotage;',self.source)
        combat=(CLASSES/'APX_CombatPlanner.uc').read_text()
        self.assertIn("AA_Success", combat)
        self.assertIn("DevastatingPunchMP", config)


if __name__ == '__main__':
    unittest.main()
