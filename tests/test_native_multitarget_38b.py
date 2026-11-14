"""#38b: stock Faceoff fires hostile primary then other native enemies.

Do not claim free-aim rockets, cones, lines or secondary car explosions are
supported by this one selected-target policy. WOTC Windows/game not run.
"""
import os
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import CHECKS, function_body

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
NATIVE = SRC / "APX_NativeMultiTarget.uc"
COMBAT = SRC / "APX_CombatPlanner.uc"
AREA = SRC / "APX_AreaAttackPlanner.uc"


class NativeMultiTargetMath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = staticmethod(load_uc_function(NATIVE, "ScoreFaceoffOutcome"))
        cls.damage = staticmethod(load_uc_function(COMBAT, "ScoreDamage"))
        cls.weapon = staticmethod(load_uc_function(NATIVE, "SupportsFaceoffWeapon"))

    def test_pistol_subset_rejects_extra_applied_effect_ammo_and_upgrade_channels(self):
        self.assertTrue(self.weapon(True, True, 0, 0, False, False))
        # A disabled bonus channel does not apply its template effects.
        self.assertTrue(self.weapon(True, False, 1, 0, False, False))
        for args in ((False, True, 0, 0, False, False),
                     (True, True, 1, 0, False, False),
                     (True, True, 0, 1, False, False),
                     (True, True, 0, 0, True, False),
                     (True, True, 0, 0, False, True)):
            with self.subTest(args=args):
                self.assertFalse(self.weapon(*args))

    def test_two_or_more_native_enemies_beats_one_and_protects_cooldown(self):
        self.assertLess(self.score(0, 0, 0), -1000)
        self.assertLess(self.score(1, 1, 90), -1000)
        self.assertEqual(self.score(2, 0, 75), 63)
        self.assertEqual(self.score(2, 1, 75), 68)
        self.assertEqual(self.score(2, 2, 75), 73)
        self.assertEqual(self.score(3, 3, 100), 100)
        self.assertLess(self.score(2, 0, 0), -1000)

    def test_expected_native_multitarget_preview_competes_with_good_single_shot(self):
        weak = self.damage(3, 4, 8, 35, 1.0, 0)
        strong_single = self.damage(3, 4, 3, 80, 1.0, 0)
        # Two weak 35%-hit shots are a poor use of an expensive cooldown.
        self.assertLess(self.score(2, 0, weak * 2), strong_single)
        # Three current strong damage shots beat a single ordinary hit,
        # but the score remains expected-value, NOT a guaranteed outcome.
        strong_multi = self.damage(3, 4, 3, 60, 1.0, 0)
        self.assertGreater(self.score(3, 0, strong_multi * 3), strong_single)

    def test_per_enemy_finish_bonus_bounded_no_fake_guaranteed_kill(self):
        self.assertEqual(self.score(4, 100, 80), 80)
        self.assertEqual(self.score(2, -1, 80), 68)
        self.assertLess(self.score(17, 2, 100), -1000)


class NativeMultiTargetSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = NATIVE.read_text(encoding="utf-8-sig")
        cls.combat = COMBAT.read_text(encoding="utf-8-sig")
        cls.area = AREA.read_text(encoding="utf-8-sig")

    def test_native_faceoff_template_exact_contract_not_grenade_or_blind_freeaim(self):
        body = function_body(self.native, "SupportedFaceoff")
        for term in ("Ability.GetMyTemplateName() != 'Faceoff'",
                     "Template.TargetingMethod != class'X2TargetingMethod_TopDown'",
                     "Template.Hostility != eHostility_Offensive",
                     "Template.AbilityToHitCalc.Class != class'X2AbilityToHitCalc_StandardAim'",
                     "Template.AbilityTargetStyle.Class != class'X2AbilityTarget_Single'",
                     "ToHitCalc.bOnlyMultiHitWithSuccess",
                     "X2AbilityMultiTarget_AllUnits(",
                     "Multi.Class != class'X2AbilityMultiTarget_AllUnits'",
                     "!Multi.bUseAbilitySourceAsPrimaryTarget",
                     "!Multi.bAcceptEnemyUnits", "Multi.bAcceptFriendlyUnits",
                     "!Multi.bDontAcceptNeutralUnits",
                     "Multi.bRandomlySelectOne", "Multi.RandomChance > 0",
                     "Template.AbilityTargetEffects.Length != 1",
                     "Template.AbilityMultiTargetEffects.Length != 1",
                     "PrimaryDamageEffect.bExplosiveDamage",
                     "DamageEffect.bExplosiveDamage",
                     "PrimaryDamageEffect.Class != class'X2Effect_ApplyWeaponDamage'",
                     "DamageEffect.Class != class'X2Effect_ApplyWeaponDamage'",
                     "PrimaryDamageEffect.EnvironmentalDamageAmount != 0",
                     "DamageEffect.EnvironmentalDamageAmount != 0",
                     "WeaponTemplate.WeaponCat == 'pistol'",
                     "Template.bAllowBonusWeaponEffects",
                     "WeaponTemplate.BonusWeaponEffects.Length",
                     "Weapon.GetMyWeaponUpgradeTemplateNames()",
                     "Ability.SourceAmmo.ObjectID > 0",
                     "Weapon.GetLoadedAmmoTemplate(Ability) != none"):
            self.assertIn(term, body)
        self.assertNotIn("GetMyWeaponUpgradeTemplates(", body)
        self.assertNotIn("RocketLauncher", body)
        self.assertNotIn("VoidRift", body)

    def test_every_native_additional_target_current_visible_hostile_no_controlled_ally(self):
        body = function_body(self.native, "ScoreFaceoff")
        for term in ("NativeTarget.PrimaryTarget.ObjectID == Shooter.ObjectID",
                     "NativeTarget.AdditionalTargets.Length < 1",
                     "NativeTarget.AdditionalTargets.Length > 15",
                     "for (Index = -1; Index < NativeTarget.AdditionalTargets.Length",
                     "TargetRef = NativeTarget.PrimaryTarget;",
                     "Template.AbilityTargetEffects[0]",
                     "Template.AbilityMultiTargetEffects[0]",
                     "Seen.Find(TargetRef.ObjectID) != INDEX_NONE",
                     "IsVisibleHostile(", "IsReclaimableControlledSquadmate(",
                     "Preview = NativeTarget;", "Preview.PrimaryTarget = TargetRef;",
                     "Preview.AdditionalTargets.Length = 0",
                     "Ability.GetShotBreakdown(", "Chance < 0 || Chance > 100",
                     "DamageEffect.GetDamagePreview(TargetRef, Ability, Index < 0,",
                     "PreviewDamageAfterArmor(", "Health <= 0.0",
                     "ScoreDamage(", "UsefulTargets",
                     "Chance < Max(1, class'APX_CombatPlanner'.default.MinimumHitChance)",
                     "MaxAfterArmor <= 0.0",
                     "ScoreFaceoffOutcome(UsefulTargets, StrongFinishes, Value)"):
            self.assertIn(term, body)
        self.assertNotIn("GetAllUnits(", body)
        self.assertNotIn("SYNC_RAND", CHECKS.without_comments(body))

    def test_actual_native_action_target_used_without_translating_to_area_cursor(self):
        body = function_body(self.combat, "ChooseAction")
        self.assertIn("if (AbilityName == 'Faceoff')", body)
        self.assertIn("class'APX_NativeMultiTarget'.static.ScoreFaceoff(", body)
        self.assertLess(body.index("if (AbilityName == 'Faceoff')"),
                        body.index("if (AbilityTemplate.AbilityMultiTargetStyle != none"))
        for term in ("Candidate.AvailableCode != 'AA_Success'",
                     "Candidate.bFreeAim", "Action = Candidate;",
                     "TargetIndex = Index;", "bFound = true;"):
            self.assertIn(term, body)
        for forbidden in ("ActivateAbility_ReturnContext(",
                          "GameStateMoveUnitSingle(", "SubmitGameState(",
                          "GetGroupMovePaths("):
            self.assertNotIn(forbidden, CHECKS.without_comments(self.native))

    def test_original_grenade_geometry_friendly_objective_secondary_guards_still_active(self):
        source = function_body(self.area, "GetSupportedGrenade")
        for t in ("AbilityName != 'ThrowGrenade'", "AbilityName != 'LaunchGrenade'",
                  "Grenade.DataName != 'FragGrenade'", "Grenade.DataName != 'AlienGrenade'"):
            self.assertIn(t, source)
        unsafe = function_body(self.area, "BlastIsSafe")
        for t in ("IsProtectedUnit(", "FootprintNearImpact(",
                  "GetValidTilesForLocation(", "HasDangerousScenery("):
            self.assertIn(t, unsafe)
        self.assertIn("HasRadialDamage()", function_body(self.area, "HasDangerousScenery"))
        self.assertIn("bDestroysSurroundingArea",
                      function_body(self.area, "HasDangerousScenery"))


@unittest.skipUnless(os.environ.get("APX_SDK_SOURCE_ROOT"),
                     "Private SDK not in public CI")
class NativeFaceoffSDK(unittest.TestCase):
    def test_stock_faceoff_and_unsupported_family_signatures(self):
        root = CHECKS.find_sdk_root(Path(os.environ["APX_SDK_SOURCE_ROOT"]))
        folder = root / "XComGame/Classes"
        sharp = (folder / "X2Ability_SharpshooterAbilitySet.uc").read_text(encoding="utf-8-sig")
        targets = (folder / "X2AbilityMultiTarget_AllUnits.uc").read_text(encoding="utf-8-sig")
        heavy = (folder / "X2Ability_HeavyWeapons.uc").read_text(encoding="utf-8-sig")
        template = (folder / "X2AbilityTemplate.uc").read_text(encoding="utf-8-sig")
        ability_base = (folder / "X2Ability.uc").read_text(encoding="utf-8-sig")
        damage = (folder / "X2Effect_ApplyWeaponDamage.uc").read_text(encoding="utf-8-sig")
        weapon = (folder / "X2WeaponTemplate.uc").read_text(encoding="utf-8-sig")
        item = (folder / "XComGameState_Item.uc").read_text(encoding="utf-8-sig")
        psi = (folder / "X2Ability_PsiOperativeAbilitySet.uc").read_text(encoding="utf-8-sig")
        for t in ("Faceoff()", "MultiTargetUnits.bUseAbilitySourceAsPrimaryTarget = true",
                  "MultiTargetUnits.bAcceptEnemyUnits = true",
                  "Template.AddTargetEffect(new class'X2Effect_ApplyWeaponDamage')",
                  "Template.AddMultiTargetEffect(new class'X2Effect_ApplyWeaponDamage')",
                  "//  Fire at the primary target first",
                  "FireAction.SetFireParameters(Context.IsResultContextHit()",
                  "History.GetVisualizer(AbilityContext.PrimaryTarget.ObjectID)"):
            self.assertIn(t, sharp)
        self.assertIn("TargetingMethod = class'X2TargetingMethod_TopDown'", template)
        # Faceoff does NOT override the stock default with a free-aim cursor.
        faceoff_src = sharp.split("static function X2AbilityTemplate Faceoff()", 1)[1].split(
            "function Faceoff_BuildVisualization", 1)[0]
        self.assertNotIn("Template.TargetingMethod =", faceoff_src)
        self.assertIn("ToHitCalc = new class'X2AbilityToHitCalc_StandardAim'", faceoff_src)
        self.assertIn("ToHitCalc.bOnlyMultiHitWithSuccess = false", faceoff_src)
        self.assertIn("Template.AbilityTargetStyle = default.SimpleSingleTarget", faceoff_src)
        self.assertIn("Begin Object Class=X2AbilityTarget_Single Name=DefaultSimpleSingleTarget", ability_base)
        self.assertIn("var int EnvironmentalDamageAmount;", damage)
        # This property is defined here and has no base-class assignment;
        # stock direct weapon damage therefore has the native int default0.
        self.assertNotRegex(damage, r"\bEnvironmentalDamageAmount\s*=")
        self.assertIn("BonusWeaponEffects", weapon)
        self.assertIn("WeaponCat", weapon)
        self.assertRegex(item, r"function\s+array<name>\s+GetMyWeaponUpgradeTemplateNames\(\)"
                         r"\s*\{\s*return m_arrWeaponUpgradeNames;\s*\}")
        for t in ("bAcceptFriendlyUnits", "bDontAcceptNeutralUnits",
                  "bRandomlySelectOne", "GetMultiTargetOptions"):
            self.assertIn(t, targets)
        for t in ("X2TargetingMethod_RocketLauncher", "X2TargetingMethod_BlasterLauncher",
                  "X2TargetingMethod_Cone", "X2TargetingMethod_Line"):
            self.assertIn(t, heavy)
        for t in ("X2TargetingMethod_VoidRift", "X2TargetingMethod_Line",
                  "TriggerEventName", "X2AbilityMultiTarget_Radius"):
            self.assertIn(t, psi)


if __name__ == "__main__":
    unittest.main()
