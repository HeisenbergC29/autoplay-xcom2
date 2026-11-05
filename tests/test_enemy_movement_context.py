"""Source-backed enemy reach and the shared context used by movement searches."""
import os
from pathlib import Path
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
MISSION = CLASSES / 'APX_MissionPlanner.uc'
SQUAD = CLASSES / 'APX_SquadPlanner.uc'


class EnemyMovementContextTests(unittest.TestCase):
    def test_zombie_stationary_melee_preserves_move_then_attack_budget(self):
        moves = load_uc_function(MISSION, 'MeleeMovementActions')
        reach = load_uc_function(MISSION, 'MeleeReachFromBudget')
        self.assertEqual(moves(2, 1, 0, False), 1)
        # Synthetic positive native world-range: conversion is separate from
        # whatever range the installed zombie weapon returns in a real game.
        self.assertAlmostEqual(reach(12 * 64 / 96, moves(2, 1, 0, False), 192 / 96), 10)
        body = function_body(MISSION.read_text(), 'GetMeleeThreatReach')
        self.assertIn("Template.AbilityTargetStyle.Class == class'X2AbilityTarget_Single'", body)
        self.assertIn('!SingleTarget.OnlyIncludeTargetsInsideWeaponRange', body)
        self.assertIn('SingleTarget.GetHitRange(Ability)', body)
        self.assertNotIn('bRequireMelee', body)
        self.assertNotIn('iRange == 0', body)

    def test_report_ambush_moves_cannot_materially_worsen_post_reveal_exposure(self):
        allowed = load_uc_function(SQUAD, 'PreparationRiskAllowed')
        self.assertFalse(allowed(24.7828, 55.65))
        self.assertFalse(allowed(44.2171, 80.97))
        self.assertTrue(allowed(24.7828, 2.1995))
        self.assertTrue(allowed(10, 10))
        self.assertTrue(allowed(0, 3))
        self.assertFalse(allowed(0, 10))
        prepare = function_body(SQUAD.read_text(), 'ChoosePreparationMove')
        self.assertLess(prepare.index('PreparationRiskAllowed(CurrentRisk, CandidateRisk)'),
                        prepare.index('bFiringLane = HasFiringLane'))

    def test_tile_searches_take_one_visible_weapon_snapshot_per_contact_list(self):
        text = MISSION.read_text()
        for name in ('ChooseMove', 'ChooseRescueMove'):
            body = function_body(text, name)
            self.assertEqual(body.count('GetThreatWeights('), 1)
            loop = 'for (SampleIndex' if name == 'ChooseMove' else 'foreach `XCOMHISTORY'
            self.assertLess(body.index('GetThreatWeights('), body.index(loop))
            self.assertIn('VisibleEnemies, MeleeThreatReaches, ThreatWeights)', body)
        prepare = function_body(SQUAD.read_text(), 'ChoosePreparationMove')
        self.assertEqual(prepare.count('GetThreatWeights('), 1)
        self.assertLess(prepare.index('GetThreatWeights('), prepare.index('for (Sample ='))
        exposure = function_body(text, 'ExposureRisk')
        self.assertIn('ThreatWeights.Length == VisibleEnemies.Length', exposure)
        self.assertIn('KnownWeight = ThreatWeights[Index]', exposure)
        threat = function_body(text, 'ThreatRiskAtTile')
        self.assertIn('Weight = KnownThreatWeight', threat)
        self.assertIn('if (Weight < 0.0)', threat)
        self.assertIn('MeleeReach) * Weight', threat)
        self.assertIn('Enemy.IsMeleeOnly()) * Weight', threat)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Enemy reach contracts need SDK sources')
class EnemyMovementSDKContracts(unittest.TestCase):
    def test_stock_standard_melee_and_single_range_are_not_guessed_from_weapon_range(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        weapon = function_body((sdk / 'X2Ability_WeaponCommon.uc').read_text(encoding='utf-8-sig'), 'Add_StandardMelee')
        self.assertIn('ActionPointCost.iNumPoints = 1', weapon)
        self.assertIn('ActionPointCost.bConsumeAllPoints = true', weapon)
        self.assertIn('Template.AbilityTargetStyle = default.SimpleSingleMeleeTarget', weapon)
        single = (sdk / 'X2AbilityTarget_Single.uc').read_text(encoding='utf-8-sig')
        self.assertIn('var() bool OnlyIncludeTargetsInsideWeaponRange', single)
        self.assertNotIn('bRequireMelee', single)
        ability = (sdk / 'XComGameState_Ability.uc').read_text(encoding='utf-8-sig')
        self.assertIn('Template.AbilityTargetStyle.GetHitRange(self)', function_body(ability, 'GetValidWeaponRange'))
        item = function_body((sdk / 'X2Item_DefaultWeapons.uc').read_text(encoding='cp1252'), 'CreateTemplate_PsiZombie_MeleeAttack')
        self.assertIn('Template.iRange = 2', item)


if __name__ == '__main__':
    unittest.main()
