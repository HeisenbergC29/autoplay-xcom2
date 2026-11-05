"""Regressions for losing a legal two-AP shot to a blue move.

Scalar policy tests execute the actual UC helper. Native cache/AP/path calls
are checked at their source boundaries; they still require Windows/game tests.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionPlanner.uc'


class MoveOpportunityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.penalty = staticmethod(load_uc_function(SOURCE, 'MoveOpportunityPenalty'))

    def test_legacy_d6_lost_rifle_value_overturns_the_recorded_move(self):
        # D6: move39.6857 narrowly beat ally-shot39.656 and own rifle36.92.
        # With a retained-attack value24.2 (the recorded post-move pistol),
        # the lost opportunity12.72 puts the move below both attacks.
        # Runtime recomputes retained value on CURRENT targets/position; this
        # illustrative scalar scenario does not predict destination hit chance.
        loss = self.penalty(36.92, 24.2, 1.0, 38.1675 - 4.2113)
        self.assertAlmostEqual(loss, 12.72)
        self.assertGreater(39.6857, 39.656)
        self.assertLess(39.6857 - loss, 39.656)
        self.assertLess(39.6857 - loss, 36.92)

    def test_ordinary_rifle_still_affordable_after_blue_move_has_no_penalty(self):
        self.assertEqual(self.penalty(39.656, 39.656, 1, 33), 0)

    def test_no_attack_does_not_discourage_movement(self):
        self.assertEqual(self.penalty(0, 0, 1, 0), 0)
        self.assertEqual(self.penalty(0, 0, 0.25, 20), 0)

    def test_free_or_special_ap_move_preserving_all_attacks_has_no_penalty(self):
        self.assertEqual(self.penalty(80, 80, 1, 12), 0)
        self.assertEqual(self.penalty(24, 30, 1, 12), 0)

    def test_wounded_emergency_escape_keeps_existing_priority(self):
        self.assertEqual(self.penalty(80, 0, 0.25, 8), 0)
        self.assertEqual(self.penalty(80, 0, 0.49, 40), 0)
        self.assertEqual(self.penalty(80, 0, 0.5, 40), 80)
        self.assertEqual(self.penalty(80, 0, 0.25, 7.9), 80)

    def test_budget_projection_does_not_change_live_action_points(self):
        projection = function_body(SOURCE.read_text(), 'ActionPointsAfterBlueMove')
        self.assertIn('RemainingPoints = UnitState.ActionPoints;', projection)
        self.assertIn('APCost.bFreeCost', projection)
        self.assertIn('APCost.GetPointCost(MoveAbility, UnitState)', projection)
        self.assertIn('APCost.ConsumeAllPoints(MoveAbility, UnitState)', projection)
        self.assertIn('APCost.AllowedTypes.Length - 1', projection)
        self.assertIn('RemainingPoints.Remove(PointIndex, 1)', projection)
        self.assertNotRegex(projection, r'UnitState\.ActionPoints\s*(?:=|\.|\[)')
        self.assertNotRegex(projection, r'\b(?:ApplyCost|SubmitGameState|ModifyStateObject)\s*\(')

    def test_attack_cost_eligibility_keeps_native_free_cost_requirement(self):
        budget = function_body(SOURCE.read_text(), 'CanAttackWithActionPoints')
        self.assertIn('APCost.AllowedTypes', budget)
        self.assertIn('APCost.GetPointCost(Ability, UnitState)', budget)
        # bFreeCost affects ApplyCost, not CanAfford: a free attack may still
        # require at least one eligible point and be lost after the last AP.
        self.assertNotIn('bFreeCost', budget)

    def test_opportunity_scan_uses_current_safe_legal_ranged_targets(self):
        source = SOURCE.read_text()
        scan = function_body(source, 'GetMoveAttackOptions')
        for gate in ('Cache.AvailableActions', 'AA_Success', 'bInputTriggered',
                     'bFreeAim', 'AttackAbilities.Find', 'ProvidesPath',
                     'IsVisibleHostile', 'AdditionalTargetsAreSafe',
                     'ScoreAttack(Ability, Target, TargetUnit)'):
            self.assertIn(gate, scan)
        self.assertNotIn('IterateByClassType', scan)
        self.assertNotIn('SniperStandardFire', scan)
        self.assertNotIn('PistolStandardShot', scan)
        self.assertIn('GetMoveAttackOptions(', function_body(source, 'ChooseMove'))
        self.assertIn('Score -= MoveOpportunityPenalty(', function_body(source, 'ChooseMove'))


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'SDK AP contracts need APX_SDK_SOURCE_ROOT')
class MoveOpportunitySDKContracts(unittest.TestCase):
    def test_stock_blue_move_and_ap_checks_match_the_read_only_projection(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        defaults = (sdk / 'X2Ability_DefaultAbilitySet.uc').read_text(encoding='utf-8-sig')
        move = function_body(defaults, 'AddStandardMoveAbility')
        self.assertIn("new class'X2AbilityCost_ActionPoints'", move)
        self.assertIn('ActionPointCost.bMoveCost = true', move)
        builder = function_body(defaults, 'MoveAbility_FillOutGameState')
        self.assertIn('AbilityTemplate.ApplyCost(', builder)
        ap = (sdk / 'X2AbilityCost_ActionPoints.uc').read_text(encoding='utf-8-sig')
        gate = function_body(ap, 'CanAfford')
        self.assertIn('PointCheck = GetPointCost(kAbility, kUnit)', gate)
        self.assertIn('AllowedTypes', gate)
        self.assertNotIn('bFreeCost', gate)
        apply = function_body(ap, 'ApplyCost')
        self.assertIn('bFreeCost', apply)
        self.assertIn('AllowedTypes.Length - 1', apply)
        self.assertIn('CostIncreases', apply)


if __name__ == '__main__':
    unittest.main()
