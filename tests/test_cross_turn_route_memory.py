"""Regression contracts for cross-turn navigation oscillation in GasStation v15.

Observed endpoint loops:
- unit 63474: (57,26,1) <-> (57,33,1)
- unit 63486: (57,24,1) <-> (57,30,1)

The source-only checks do not run XCOM engine movement or SDK compilation.
"""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function

CLASSES = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
CONTROLLER = CLASSES / 'APX_Controller.uc'
MISSION = CLASSES / 'APX_MissionPlanner.uc'
EXPLORATION = CLASSES / 'APX_ExplorationPlanner.uc'


class CrossTurnRouteLoopTests(unittest.TestCase):
    def test_finite_memory_catches_oscillation_but_expires(self):
        recent = load_uc_function(CONTROLLER, 'IsRecentRouteTurn')
        self.assertTrue(recent(58, 57, 6))
        self.assertTrue(recent(60, 57, 6))
        self.assertTrue(recent(63, 57, 6))
        self.assertFalse(recent(64, 57, 6))
        self.assertFalse(recent(58, 59, 6))

    def test_player_turn_reset_does_not_erase_cross_turn_memory(self):
        source = CONTROLLER.read_text(encoding='utf-8-sig')
        decision = function_body(source, 'MakeDecision')
        self.assertIn('VisitedPositions.Length = 0;', decision)
        self.assertIn('PruneRecentRoutePositions(PlayerState.PlayerTurnCount)', decision)
        self.assertIn('if (bCombatThreats)\n        RecentRoutePositions.Length = 0;', decision)
        self.assertIn('RememberRoutineRouteMove(BestUnit, BestPath);', decision)

    def test_each_soldier_remembers_only_their_own_endpoints(self):
        source = CONTROLLER.read_text(encoding='utf-8-sig')
        recent = function_body(source, 'GetRecentRouteTiles')
        self.assertIn('RecentRoutePositions[Index].UnitID != UnitID', recent)
        self.assertIn('IsRecentRouteTurn(', recent)
        memory = function_body(source, 'RememberRouteTile')
        self.assertIn('RecentRoutePositions.Length >= 128', memory)

    def test_neither_native_route_prefix_nor_fallback_reuses_recent_endpoints(self):
        source = MISSION.read_text(encoding='utf-8-sig')
        choose = function_body(source, 'ChooseMove')
        prefix = function_body(source, 'ChooseRoutePrefix')
        self.assertIn('IsRecentRouteTile(FullPath[Index], RecentTiles)', prefix)
        self.assertIn('IsRecentRouteTile(Tile, RecentTiles)', choose)
        self.assertIn('ChooseRoutePrefix(UnitState, UnitVisualizer, GoalTile, Path, RecentTiles)', choose)
        self.assertIn('!bCombatGoal && !ShouldEvacuate(UnitState)', choose)

    def test_exploration_gets_same_memory_and_emergencies_are_unfiltered(self):
        controller = function_body(CONTROLLER.read_text(encoding='utf-8-sig'), 'MakeDecision')
        self.assertIn('ChooseMove(UnitState, CandidatePath, Score, RecentRouteTiles)', controller)
        self.assertIn('ChoosePoisonEscape(UnitState, CandidatePath, Score)', controller)
        self.assertIn('ChooseRescueMove(UnitState, CandidatePath, Score, RescuePatientID)', controller)
        self.assertIn('ChooseContactSearchMove(UnitState, CandidatePath, Score)', controller)
        explore = function_body(EXPLORATION.read_text(encoding='utf-8-sig'), 'ChooseMove')
        self.assertIn('BuildSafeBluePrefix(UnitState, Goals[GoalIndex].Tile, Path, RecentTiles)', explore)
        prefix = function_body(EXPLORATION.read_text(encoding='utf-8-sig'), 'BuildSafeBluePrefix')
        self.assertIn('IsRecentRouteTile(FullPath[Index], RecentTiles)', prefix)


if __name__ == '__main__':
    unittest.main()
