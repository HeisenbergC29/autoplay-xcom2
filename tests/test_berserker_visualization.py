"""Template-only DevastatingPunchMP visualization experiment (#15).

Source tests are not UnrealScript compilation or an in-game crash fix.
"""
import os
from pathlib import Path
import unittest
from test_ui_gating import CHECKS, function_body

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/X2DownloadableContentInfo_AutoplayXCom2.uc'


class MPVisualizationPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PATCH.read_text(encoding='utf-8-sig')

    def test_registers_all_difficulty_template_instances(self):
        callback = function_body(self.source, 'OnPostTemplatesCreated')
        self.assertIn("FindAbilityTemplateAllDifficulties('DevastatingPunchMP', Templates)", callback)
        self.assertIn('PatchMPFailureVisualization(Templates[Index])', callback)
        self.assertIn('X2DownloadableContentInfo_AutoplayXCom2',
                      (ROOT / 'AutoplayXCom2/Config/XComGame.ini').read_text())

    def test_guarded_to_actual_mp_hit_miss_and_impairing_shape(self):
        body = function_body(self.source, 'PatchMPFailureVisualization')
        for item in ("Template.DataName != 'DevastatingPunchMP'",
                     'foreach Template.AbilityTargetEffects(Effect)',
                     'DamageEffect.bApplyOnHit && !DamageEffect.bApplyOnMiss',
                     '!DamageEffect.bApplyOnHit && DamageEffect.bApplyOnMiss',
                     'DamageEffect.bIgnoreBaseDamage',
                     "ImpairingEffect.AbilityName == class'X2Ability_Impairing'.default.ImpairingAbilityName",
                     'DamageCount != 2 || HitEffect == none || MissEffect == none',
                     'ImpairingCount != 1'):
            with self.subTest(item=item):
                self.assertIn(item, body)

    def test_both_flags_are_idempotent_and_visual_only(self):
        body = function_body(self.source, 'PatchMPFailureVisualization')
        self.assertEqual(body.count(".HideVisualizationOfResultsAdditional.Find('AA_HitResultFailure')"), 2)
        self.assertEqual(body.count(".HideVisualizationOfResultsAdditional.AddItem('AA_HitResultFailure')"), 2)
        for forbidden in ('EffectDamageValue =', 'AbilityCosts.AddItem', 'AbilityToHitCalc =',
                          'bApplyOnHit =', 'bApplyOnMiss =', 'bIgnoreBaseDamage =',
                          'BuildNewGameStateFn =', 'VisualizationFn =', 'XCOMHISTORY',
                          'SubmitGameState', 'GetGameRulesCache'):
            self.assertNotIn(forbidden, body)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'Stock SDK is required to establish the original MP difference')
class StockMPVisualizationContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_vanilla_punch_hides_failed_damage_visuals_but_mp_does_not(self):
        source = (self.sdk / 'X2Ability_Berserker.uc').read_text(encoding='utf-8-sig')
        ordinary = function_body(source, 'CreateDevastatingPunchAbility')
        mp = function_body(source, 'CreateDevastatingPunchAbilityMP')
        name = "HideVisualizationOfResultsAdditional.AddItem('AA_HitResultFailure')"
        self.assertEqual(ordinary.count(name), 2)
        self.assertNotIn(name, mp)

    def test_engine_damage_visualization_reads_this_flag(self):
        source = (self.sdk / 'X2Effect_ApplyWeaponDamage.uc').read_text(encoding='utf-8-sig')
        body = function_body(source, 'AddX2ActionsForVisualization')
        self.assertIn('HideVisualizationOfResultsAdditional.Find(EffectApplyResult)', body)
        self.assertIn('return;', body)


if __name__ == '__main__':
    unittest.main()
