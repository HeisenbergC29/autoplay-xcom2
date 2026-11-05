"""Concealed opening regressions based on the third recorded Gatecrasher.

The actual numeric UC policy helpers run here; native paths, cover/detection
previews, overwatch reactions and activation still require SDK/game validation.
"""
import os
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import CHECKS, function_body


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SQUAD = CLASSES / 'APX_SquadPlanner.uc'


class AmbushPolicyTests(unittest.TestCase):
    def test_preparation_only_while_concealed_and_before_action_budget(self):
        prepare = load_uc_function(SQUAD, 'CanPrepare')
        self.assertTrue(prepare(True, True, 0, 6))
        self.assertTrue(prepare(True, True, 5, 6))
        self.assertFalse(prepare(True, True, 6, 6))
        self.assertFalse(prepare(False, True, 0, 6))
        self.assertFalse(prepare(True, False, 0, 6))
        self.assertFalse(prepare(True, True, 0, 0))

    def test_report_rear_soldiers_can_move_then_react_but_opener_keeps_last_ap(self):
        stage = load_uc_function(SQUAD, 'CanStageMove')
        self.assertTrue(stage(2, 1, False))
        self.assertFalse(stage(1, 1, False))
        self.assertFalse(stage(2, 2, False))
        self.assertFalse(stage(2, 1, True))

    def test_rear_positioning_precedes_reaction_setup_without_blind_overwatch(self):
        score = load_uc_function(SQUAD, 'PreparationScore')
        self.assertGreater(score(True, False, False), score(False, True, True))
        self.assertGreater(score(False, False, True), 0)
        self.assertLess(score(False, False, False), -1000)

    def test_report_opening_prepares_supporters_without_spending_reserved_opener(self):
        stage = load_uc_function(SQUAD, 'CanStageMove')
        score = load_uc_function(SQUAD, 'PreparationScore')
        # At D3 the opener422 had1AP;410 had1AP and a firing lane;
        #416/428 had2AP and needed positions. Safe move previews are inputs.
        soldiers = {422: [1, True, True, False], 410: [1, True, True, False],
                    416: [2, False, False, False], 428: [2, False, False, False]}
        actions = []
        for _ in range(6):
            candidates = []
            for unit, (ap, useful, lane, reserved) in soldiers.items():
                if unit == 422 or ap == 0 or reserved:
                    continue
                move = stage(ap, 1, useful)
                value = score(move, useful, lane)
                if value > 0:
                    candidates.append((value, unit, move))
            if not candidates:
                break
            _, unit, move = max(candidates)
            actions.append((unit, move))
            if move:
                soldiers[unit][0] -= 1
                soldiers[unit][2] = True
            else:
                soldiers[unit][0] = 0
                soldiers[unit][3] = True
        self.assertEqual(len(actions), 5)
        self.assertEqual(soldiers[422][0], 1)
        self.assertTrue(all(soldiers[unit][3] for unit in (410, 416, 428)))

    def test_known_detection_uses_los_radius_and_squared_distance(self):
        detected = load_uc_function(SQUAD, 'DetectedOnTile')
        self.assertTrue(detected(True, 25, 18, 5, False))
        self.assertFalse(detected(True, 36, 18, 5, False))
        self.assertFalse(detected(False, 4, 18, 5, False))
        self.assertTrue(detected(True, 36, 18, 5, True))
        self.assertFalse(detected(True, 400, 18, 5, True))

    def test_fourth_report_rear_soldiers_may_catch_up_without_immediate_los(self):
        catchup = load_uc_function(SQUAD, 'CatchupProgress')
        # D20: opener(25,34), rear409(12,34), rear415(14,33).
        # Recorded move proposal(19,33) closed the gap without immediate LOS;
        # full native concealment/path safety must still admit the proposal.
        gap409 = 13.0
        gap415 = (11 ** 2 + 1) ** 0.5
        destination_gap = (6 ** 2 + 1) ** 0.5
        self.assertGreater(catchup(gap409, destination_gap, 13.903, 4.2049, 8), 0)
        self.assertGreater(catchup(gap415, destination_gap, 15.1013, 4.2049, 8), 0)

    def test_catchup_cannot_extend_gap_increase_risk_or_shuffle_nearby_supporters(self):
        catchup = load_uc_function(SQUAD, 'CatchupProgress')
        self.assertLess(catchup(6, 3, 20, 4, 8), -1000)
        self.assertLess(catchup(13, 14, 20, 4, 8), -1000)
        self.assertLess(catchup(13, 12, 20, 4, 8), -1000)
        self.assertLess(catchup(13, 6, 4, 20, 8), -1000)
        self.assertEqual(catchup(13, 6, 4, 4, 8), 12)

    def test_preparation_rejects_destructive_path_traversals(self):
        destructive = load_uc_function(SQUAD, 'IsDestructiveTraversal')
        for name in ('eTraversal_BreakWindow', 'eTraversal_KickDoor', 'eTraversal_BreakWall'):
            self.assertTrue(destructive(name))
        for name in ('eTraversal_Normal', 'eTraversal_ClimbLadder', 'eTraversal_Ramp'):
            self.assertFalse(destructive(name))

    def test_native_cache_legality_and_reserved_opener_are_kept(self):
        source = SQUAD.read_text()
        choose = function_body(source, 'ChoosePreparation')
        self.assertIn('Soldier.ObjectID == Opener.ObjectID', choose)
        self.assertIn('Soldier.NumAllReserveActionPoints() > 0', choose)
        overwatch = function_body(source, 'FindOverwatch')
        self.assertIn("Candidate.AvailableCode != 'AA_Success'", overwatch)
        self.assertIn('APCost.GetPointCost(Ability, Soldier)', overwatch)
        path = function_body(source, 'PreparationPathIsSafe')
        self.assertIn('GetAllVisibleObjectsForPlayer(', path)
        self.assertIn('foreach VisibleObjects(DetectorRef)', path)
        self.assertNotIn('IterateByClassType', path)
        self.assertIn('GetPathPointsFromPath(', path)
        self.assertIn('HasBlockingHazard(', path)

    def test_coordinator_runs_before_dispatch_and_never_transfers_to_enemy_ai(self):
        source = (CLASSES / 'APX_Controller.uc').read_text()
        decision = function_body(source, 'MakeDecision')
        self.assertLess(decision.index("class'APX_SquadPlanner'.static.ChoosePreparation("),
                        decision.index('MissionRecorder.PrepareChosenAction('))
        self.assertIn('++AmbushPreparationActions;', decision)
        self.assertIn('AmbushPreparationActions = 0;', decision)
        self.assertIn('bArea = false;', decision)
        self.assertNotIn('AutoRunBehaviorTree(', SQUAD.read_text())
        self.assertNotIn('GetAllKnownEnemyStates(', SQUAD.read_text())


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'SDK source contracts need APX_SDK_SOURCE_ROOT')
class AmbushSDKContracts(unittest.TestCase):
    def test_native_concealment_cost_and_path_methods_are_present(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        unit = (sdk / 'XComGameState_Unit.uc').read_text(encoding='utf-8-sig')
        for method in ('GetConcealmentDetectionDistance', 'UnitBreaksConcealment',
                       'DoesUnitBreaksConcealmentIgnoringDistance', 'IsSquadConcealed',
                       'NumAllReserveActionPoints'):
            self.assertIn(method + '(', unit)
        path = (sdk / 'X2PathSolver.uc').read_text(encoding='utf-8-sig')
        self.assertIn('GetPathPointsFromPath(XComGameState_Unit Unit, const out array<TTile> Path, out array<PathPoint> PathPoints)', path)
        cost = (sdk / 'X2AbilityCost_ActionPoints.uc').read_text(encoding='utf-8-sig')
        self.assertIn('GetPointCost(XComGameState_Ability AbilityState, XComGameState_Unit AbilityOwner)', cost)


if __name__ == '__main__':
    unittest.main()
