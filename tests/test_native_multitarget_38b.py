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

    def test_two_or_more_native_enemies_beats_one_and_protects_cooldown(self):
        self.assertLess(self.score(0, 0, 0), -1000)
        self.assertLess(self.score(1, 1, 90), -1000)
        self.assertEqual(self.score(2, 0, 75), 63)
        self.assertEqual(self.score(2, 1, 75), 68)
        self.assertEqual(self.score(2, 2, 75), 73)
        self.assertEqual(self.score(3, 3, 100), 100)
        self.assertLess(self.score(2, 0, 0), -1000)

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
                     "Template.TargetingMethod != none",
                     "Template.Hostility != eHostility_Offensive",
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
                     "Weapon.GetLoadedAmmoTemplate(Ability) != none"):
            self.assertIn(term, body)
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
        psi = (folder / "X2Ability_PsiOperativeAbilitySet.uc").read_text(encoding="utf-8-sig")
        for t in ("Faceoff()", "MultiTargetUnits.bUseAbilitySourceAsPrimaryTarget = true",
                  "MultiTargetUnits.bAcceptEnemyUnits = true",
                  "Template.AddTargetEffect(new class'X2Effect_ApplyWeaponDamage')",
                  "Template.AddMultiTargetEffect(new class'X2Effect_ApplyWeaponDamage')",
                  "//  Fire at the primary target first"):
            self.assertIn(t, sharp)
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
