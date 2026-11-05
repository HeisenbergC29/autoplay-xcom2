"""Regression contract: reversible mind-control must not make a former ally
an expendable enemy. Does not execute game logic or compile UnrealScript.
"""
import os
from pathlib import Path
import unittest

from test_ui_gating import CHECKS, function_body

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
COMBAT = CLASSES / 'APX_CombatPlanner.uc'
AREA = CLASSES / 'APX_AreaAttackPlanner.uc'


class ControlledAllyProtectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.combat = COMBAT.read_text(encoding='utf-8-sig')
        cls.area = AREA.read_text(encoding='utf-8-sig')

    def test_only_mind_controlled_hostiles_with_recoverable_prior_owner_are_protected(self):
        helper = function_body(self.combat, 'IsReclaimableControlledSquadmate')
        for required in ('SourceUnit.IsEnemyUnit(TargetUnit)',
                         'TargetUnit.IsMindControlled()',
                         'TargetUnit.AffectedByEffects(EffectRef)',
                         'EffectState.bRemoved',
                         'EffectState.ApplyEffectParameters.TargetStateObjectRef.ObjectID != TargetUnit.ObjectID',
                         'X2Effect_MindControl(EffectTemplate)',
                         'EffectTemplate.bRemoveWhenSourceDies',
                         'WasControlledByPlayerBeforeEffect('):
            with self.subTest(required=required):
                self.assertIn(required, helper)
        # State is read from the currently considered target; no enemy AI scans.
        for forbidden in ('IterateByClassType', 'CreateNewGameState',
                          'SubmitGameState', 'ModifyStateObject', 'TileLocation'):
            self.assertNotIn(forbidden, helper)

    def test_direct_and_multi_target_guards_precede_damage_preview(self):
        attack = function_body(self.combat, 'ScoreAttack')
        self.assertIn('if (IsReclaimableControlledSquadmate(SourceUnit, TargetUnit))',
                      attack)
        self.assertLess(attack.index('IsReclaimableControlledSquadmate('),
                        attack.index('Ability.GetDamagePreview('))
        self.assertIn('return -10000.0;', attack)
        secondary = function_body(self.combat, 'AdditionalTargetsAreSafe')
        self.assertIn('|| IsReclaimableControlledSquadmate(SourceUnit, TargetUnit)', secondary)
        self.assertIn('GetKnownSourceBenefits(SourceUnit, TargetUnit, ReleasedAllies, LinkedEnemies)', attack)

    def test_grenade_safety_keeps_existing_v16_revalidation(self):
        protection = function_body(self.area, 'IsProtectedUnit')
        self.assertIn("class'APX_CombatPlanner'.static.IsReclaimableControlledSquadmate(SourceUnit, OtherUnit)", protection)
        # V16's pre-dispatch check and bounded re-planning must remain intact.
        self.assertIn('area_revalidation_rejected', (CLASSES / 'APX_Controller.uc').read_text(encoding='utf-8-sig'))
        self.assertIn('LastFootprintGeometry', self.area)
        self.assertIn('RejectBlast(', self.area)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'Stock SDK is needed for active mind-control contracts')
class ControlledAllySDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_stock_mind_control_restores_previous_owner_and_is_removed_with_source(self):
        effect = (self.sdk / 'X2Effect_MindControl.uc').read_text(encoding='utf-8-sig')
        self.assertIn('SetControllingPlayer(', effect)
        self.assertIn('bRemoveWhenSourceDies', effect)


if __name__ == '__main__':
    unittest.main()
