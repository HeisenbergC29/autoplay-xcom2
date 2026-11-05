"""Bounded preparation/action combinations, without inventing future resources.

The policy helpers execute their real UC bodies. Native typed-AP costs and
availability/target scans have source contracts; Windows/game checks remain
necessary for activation order and actual retained follow-up actions.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_ActionEconomy.uc'


class ActionEconomyPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sequence = staticmethod(load_uc_function(SOURCE, 'PreparationSequenceScore'))
        cls.affords = staticmethod(load_uc_function(SOURCE, 'MeetsPointRequirement'))

    def test_useful_aid_then_retained_shot_can_beat_shooting_first(self):
        value = self.sequence(30, 80)
        self.assertEqual(value, 95)
        self.assertGreater(value, 80)
        # No second full copy of the shot or full sum of both heuristics.
        self.assertLess(value, 30 + 80)
        self.assertLess(value, 80 * 2)

    def test_no_affordable_followup_preserves_existing_action_value(self):
        for preparation in (20, 30, 140, 400):
            self.assertEqual(self.sequence(preparation, 0), preparation)

    def test_losing_two_ap_rifle_cannot_be_replaced_by_its_current_score(self):
        # After a 1-AP preparation with only one eligible point left, the 2-AP
        # rifle fails the native cost check. An available pistol can still remain.
        self.assertFalse(self.affords(1, 2))
        self.assertTrue(self.affords(1, 1))
        self.assertEqual(self.sequence(30, 20), 35)
        self.assertLess(self.sequence(30, 20), 100)

    def test_healing_and_stabilization_emergencies_keep_their_priority(self):
        self.assertEqual(self.sequence(140, 80), 140)
        self.assertEqual(self.sequence(400, 80), 400)

    def test_preparation_component_is_capped(self):
        self.assertEqual(self.sequence(60, 80), 100)
        self.assertEqual(self.sequence(80, 80), 100)

    def test_invalid_or_useless_preparation_does_not_receive_shot_value(self):
        self.assertEqual(self.sequence(-10000, 80), -10000)
        self.assertEqual(self.sequence(0, 80), 0)
        self.assertEqual(self.sequence(30, -10000), 30)

    def test_free_cost_still_needs_the_required_eligible_points(self):
        self.assertFalse(self.affords(0, 1))
        self.assertTrue(self.affords(1, 1))
        self.assertTrue(self.affords(0, 0))

    def test_unusable_special_points_do_not_satisfy_standard_point_requirement(self):
        # The inputs are ALLOWED point counts, not NumAllActionPoints. A unit
        # with one allowed standard AP plus other reserved types still has one.
        self.assertFalse(self.affords(1, 2))
        self.assertTrue(self.affords(2, 2))
        self.assertFalse(self.affords(0, 1))


class ActionEconomyIntegrationContracts(unittest.TestCase):
    def test_only_stationary_non_damage_preparations_are_supported(self):
        source = SOURCE.read_text()
        allowed = function_body(source, 'IsSupportedPreparation')
        names = set(re.findall(r"AbilityName == '([^']+)'", allowed))
        self.assertEqual(names, {'AidProtocol', 'MedikitHeal', 'NanoMedikitHeal',
                                'GremlinHeal', 'MedikitStabilize', 'GremlinStabilize'})
        for unsupported in ('Reload', 'StandardMove', 'LightningHands', 'StandardShot'):
            self.assertNotIn("'" + unsupported + "'", allowed)

    def test_ap_projection_uses_local_typed_points_and_native_consumption_order(self):
        projection = function_body(SOURCE.read_text(), 'ProjectAfterAction')
        self.assertIn('RemainingPoints = UnitState.ActionPoints;', projection)
        self.assertIn("APCost.Class != class'X2AbilityCost_ActionPoints'", projection)
        self.assertIn('APCost.bMoveCost', projection)
        self.assertIn('APCost.GetPointCost(Ability, UnitState)', projection)
        self.assertIn('APCost.ConsumeAllPoints(Ability, UnitState)', projection)
        self.assertIn('APCost.AllowedTypes.Length - 1', projection)
        self.assertIn('RemainingPoints.Remove(PointIndex, 1)', projection)
        self.assertLess(projection.index('MeetsPointRequirement(Allowed, Required)'),
                        projection.index('if (APCost.bFreeCost)'))
        self.assertLess(projection.index('if (APCost.bFreeCost)'),
                        projection.index('APCost.ConsumeAllPoints(Ability, UnitState)'))
        self.assertNotRegex(projection, r'UnitState\.ActionPoints\s*(?:=|\.|\[)')

    def test_followup_is_a_different_currently_legal_safe_visible_ranged_attack(self):
        scan = function_body(SOURCE.read_text(), 'GetRetainedAttack')
        for gate in ('Preparation.CanActivateAbility(UnitState)', 'Cache.AvailableActions',
                     'AA_Success', 'Candidate.bInputTriggered', 'Candidate.bFreeAim',
                     'Ability.ObjectID == Preparation.ObjectID',
                     'Ability.OwnerStateObject.ObjectID != UnitState.ObjectID',
                     'AttackAbilities.Find', 'CanAttackWithActionPoints(Ability, UnitState, RemainingPoints)',
                     'IsVisibleHostile', 'AdditionalTargetsAreSafe', 'ProvidesPath',
                     'X2AbilityTarget_MovingMelee', 'ScoreAttack(Ability, Target, TargetUnit)'):
            self.assertIn(gate, scan)
        self.assertIn('ActionCount > 128', scan)
        self.assertIn('TargetCount > 32', scan)
        self.assertNotIn('IterateByClassType', scan)
        self.assertNotIn('GetDamagePreview', scan)
        self.assertNotIn('Ammo', scan)

    def test_concealment_and_known_ruler_reactions_decline_combination_forecasts(self):
        source = SOURCE.read_text()
        scan = function_body(source, 'GetRetainedAttack')
        self.assertIn('UnitState.IsConcealed()', scan)
        self.assertIn('HasVisibleRulerReaction(UnitState, VisibleEnemies)', scan)
        rulers = function_body(source, 'HasVisibleRulerReaction')
        self.assertIn('foreach VisibleEnemies(EnemyRef)', rulers)
        self.assertIn('IsVisibleHostile(UnitState, Enemy, VisibleEnemies)', rulers)
        self.assertIn("Enemy.FindAbility('AlienRulerActionSystem')", rulers)
        for forbidden in ('Enemy.ActionPoints', 'Enemy.Ammo', 'CanActivateAbility(Enemy',
                          'GetUnitValue(', 'IterateByClassType'):
            self.assertNotIn(forbidden, rulers)

    def test_estimate_never_dispatches_a_promised_second_action_or_mutates_state(self):
        code = CHECKS.without_comments(SOURCE.read_text())
        self.assertNotRegex(code, r'\b(?:ApplyCost|ModifyStateObject|CreateNewGameState|SubmitGameState|'
                            r'ActivateAbility_ReturnContext|GameStateMoveUnitSingle|Rand|FRand)\s*\(')
        wrapper = function_body(code, 'ScoreWithRetainedAttack')
        self.assertIn('PreparationValue <= 0.0', wrapper)
        self.assertIn('PreparationSequenceScore(PreparationValue, FollowUpValue)', wrapper)
        self.assertIn('FollowUpAbilityID = 0', wrapper)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'AP action combinations need SDK sources')
class ActionEconomySDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT']))

    def test_native_free_cost_requirement_and_special_point_priority(self):
        sdk = self.sdk / 'XComGame/Classes'
        base = (sdk / 'X2AbilityCost.uc').read_text(encoding='utf-8-sig')
        self.assertIn('CanAfford will still check the requirements', base)
        ap = (sdk / 'X2AbilityCost_ActionPoints.uc').read_text(encoding='utf-8-sig')
        affordability = function_body(ap, 'CanAfford')
        self.assertIn('PointCheck = GetPointCost(kAbility, kUnit)', affordability)
        self.assertIn('kUnit.NumActionPoints(AllowedTypes[i])', affordability)
        self.assertNotIn('bFreeCost', affordability)
        consume = function_body(ap, 'ApplyCost')
        self.assertIn('if (bFreeCost', consume)
        self.assertIn('AllowedTypes.Length - 1', consume)
        self.assertIn('ModifiedUnitState.ActionPoints.Remove(j, 1)', consume)
        self.assertIn('ModifiedUnitState.ActionPoints.Length = 0', consume)
        ends = function_body(ap, 'ConsumeAllPoints')
        self.assertIn('DoNotConsumeAllEffects', ends)
        self.assertIn('DoNotConsumeAllSoldierAbilities', ends)

    def test_stock_aid_and_gremlin_preparations_use_one_non_ending_ap(self):
        source = (self.sdk / 'XComGame/Classes/X2Ability_SpecialistAbilitySet.uc').read_text(encoding='utf-8-sig')
        aid = function_body(source, 'AidProtocol')
        self.assertIn('ActionPointCost.iNumPoints = 1', aid)
        self.assertIn('ActionPointCost.bConsumeAllPoints = false', aid)
        for name in ('GremlinHeal', 'GremlinStabilize'):
            body = function_body(source, name)
            self.assertIn("new class'X2AbilityCost_ActionPoints'", body)
            self.assertIn('ActionPointCost.iNumPoints = 1', body)
            self.assertNotIn('bConsumeAllPoints = true', body)
            self.assertIn('ChargeCost.NumCharges = 1', body)

    def test_stock_medikit_heal_and_stabilize_are_stationary_one_ap_actions(self):
        source = (self.sdk / 'XComGame/Classes/X2Ability_DefaultAbilitySet.uc').read_text(encoding='utf-8-sig')
        for name in ('AddMedikitHeal', 'AddMedikitStabilize'):
            body = function_body(source, name)
            self.assertIn("new class'X2AbilityCost_ActionPoints'", body)
            self.assertIn('ActionPointCost.iNumPoints = 1', body)
            self.assertNotIn('bConsumeAllPoints = true', body)
            self.assertNotIn('bMoveCost = true', body)


if __name__ == '__main__':
    unittest.main()
