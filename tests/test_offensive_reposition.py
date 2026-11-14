"""A safe blue move can compete as preparation for a better basic shot.

Numeric cases execute the real UC helpers. Native remote visibility, targeting
and AP contracts remain source checks, not an execution of the WOTC engine.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SOURCE = CLASSES / 'APX_RepositionPlanner.uc'
COMBAT = CLASSES / 'APX_CombatPlanner.uc'


class OffensiveRepositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text()
        cls.range_index = staticmethod(load_uc_function(SOURCE, 'RangeBandIndex'))
        cls.chance = staticmethod(load_uc_function(SOURCE, 'ProjectedHitChance'))
        cls.projected_score = staticmethod(load_uc_function(SOURCE, 'ProjectedShotScore'))
        cls.move_score = staticmethod(load_uc_function(SOURCE, 'MoveAndShotScore'))
        cls.damage_score = staticmethod(load_uc_function(COMBAT, 'ScoreDamage'))

    def test_safe_35_to_70_percent_retained_shot_can_beat_shooting_now(self):
        now = self.damage_score(3, 5, 4, 35, 1, 0)
        chance = self.chance(35, 15, 20)
        self.assertEqual(chance, 70)
        projected = self.projected_score(now, 35, chance)
        move = self.move_score(now, projected, 35, chance, 20, 18, 5, 2)
        self.assertGreater(move, now)
        self.assertLess(move, projected)  # Extra action and forecast uncertainty cost value.

    def test_basic_damage_and_kill_value_projection_matches_existing_numeric_core(self):
        for health, threat, wound in ((3, 1.2, .25), (8, .75, 0), (4, 1.5, .5)):
            with self.subTest(health=health):
                current = self.damage_score(3, 5, health, 35, threat, wound)
                expected = self.damage_score(3, 5, health, 70, threat, wound)
                self.assertAlmostEqual(self.projected_score(current, 35, 70), expected)

    def test_good_80_to_85_percent_shot_is_not_displaced_by_a_small_improvement(self):
        current = self.damage_score(3, 5, 4, 80, 1, 0)
        projected = self.projected_score(current, 80, 85)
        self.assertLess(self.move_score(current, projected, 80, 85, 20, 10, 3, 2), -1000)

    def test_last_ap_or_insufficient_ap_cannot_fund_move_and_shot(self):
        for points in (0, 1):
            self.assertLess(self.move_score(30, 60, 35, 70, 20, 10, 3, points), -1000)
        self.assertGreater(self.move_score(30, 60, 35, 70, 20, 10, 3, 2), 30)

    def test_improved_accuracy_cannot_buy_more_endpoint_exposure(self):
        self.assertLess(self.move_score(30, 60, 35, 70, 20, 20.01, 3, 2), -1000)
        self.assertGreater(self.move_score(30, 60, 35, 70, 20, 20, 3, 2), 30)

    def test_material_accuracy_and_attack_value_gains_are_both_required(self):
        self.assertLess(self.move_score(30, 70, 35, 46, 20, 10, 3, 2), -1000)
        self.assertLess(self.move_score(30, 37.9, 35, 70, 20, 10, 3, 2), -1000)
        self.assertLess(self.move_score(30, 60, 35, 70, 20, 10, -1, 2), -1000)

    def test_projection_is_bounded_and_never_invents_a_certain_hit(self):
        self.assertEqual(self.chance(35, 1000, 1000), 70)
        self.assertEqual(self.chance(80, 1000, 1000), 95)
        self.assertEqual(self.chance(20, -1000, -1000), 0)
        self.assertEqual(self.chance(50, -10, 20), 60)
        self.assertLess(self.projected_score(30, 0, 50), -1000)
        self.assertLess(self.projected_score(5, 30, 60), -1000)

    def test_native_range_table_uses_last_band_and_explicit_empty_fallback(self):
        for distance, length, expected in ((0, 0, 0), (-1, 5, 0), (2, 5, 2), (5, 5, 4), (100, 5, 4)):
            self.assertEqual(self.range_index(distance, length), expected)

    def test_forecasts_require_current_legal_own_basic_targets_and_retained_native_ap(self):
        gather = function_body(self.source, 'GatherForecasts')
        for guard in ('Candidate.bInputTriggered', "Candidate.AvailableCode != 'AA_Success'",
                      'Candidate.bFreeAim', 'Ability.OwnerStateObject.ObjectID != UnitState.ObjectID',
                      'ActionPointsAfterBlueMove(UnitState, RemainingPoints)', 'RemainingPoints.Length == 0',
                      'CanAttackWithActionPoints(Ability, UnitState, RemainingPoints)',
                      'IsVisibleHostile(UnitState, TargetUnit, VisibleEnemies)',
                      'Target.AdditionalTargets.Length > 0', "Breakdown.SpecialGuaranteedHit != ''"):
            self.assertIn(guard, gather)
        supports = function_body(self.source, 'SupportsForecast')
        for guard in ("'StandardShot'", "'PistolStandardShot'", 'AbilityToHitCalc.Class !=',
                      'AbilityMultiTargetStyle != none', '!Aim.bMeleeAttack', '!Aim.bIndirectFire',
                      '!Aim.bReactionFire', '!Aim.bGuaranteedHit', 'Aim.FinalMultiplier == 1.0'):
            self.assertIn(guard, supports)

    def test_known_movement_sensitive_or_extra_action_cases_decline_projection(self):
        unit = function_body(self.source, 'CanForecastUnit')
        for guard in ('UnitState.IsConcealed()', 'UnitState.NumActionPoints() < 2',
                      "FindAbility('SteadyHands')", "FindAbility('Aim')", 'HasBlockingHazard('):
            self.assertIn(guard, unit)
        ruler = function_body(self.source, 'HasVisibleRuler')
        self.assertIn('foreach VisibleEnemies(EnemyRef)', ruler)
        self.assertIn("FindAbility('AlienRulerActionSystem')", ruler)
        self.assertNotIn('GetUnitValue(', ruler)

    def test_one_shot_forecast_does_not_discard_a_repeatable_or_free_shot(self):
        gather = function_body(self.source, 'GatherForecasts')
        self.assertIn('!EndsTurnForForecast(Ability, UnitState)', gather)
        end = function_body(self.source, 'EndsTurnForForecast')
        self.assertIn('Ability.GetMyTemplate().AbilityCosts(Cost)', end)
        self.assertIn('!APCost.bFreeCost', end)
        self.assertIn('APCost.ConsumeAllPoints(Ability, UnitState)', end)
        # Query the actual installed cost and current own effects/abilities;
        # do not guess that every basic shot consumes all remaining AP.
        self.assertNotIn('APCost.bConsumeAllPoints', end)

    def test_remote_preview_respects_native_conditions_and_has_no_fake_history_tile(self):
        project = function_body(self.source, 'ProjectAtTile')
        for guard in ('Tile.Z < UnitState.TileLocation.Z', 'EnableElevatedShotForecast',
                      'MaxElevationGainTiles', 'ProjectedHeightAimBonus(',
                      'Visibility = EmptyVisibility',
                      'GetVisibilityInfoFromRemoteLocation(', '!Visibility.bClearLOS',
                      'VisibilityMgr.EvaluateConditions(', 'LivingHostileGameplayVisibleFilter',
                      'Visibility.TargetCover != CT_None', 'ValidatePrimaryTargetOptionFromRemoteLocation('):
            self.assertIn(guard, project)
        self.assertNotIn('Visibility.bVisibleGameplay', project)
        # A hypothetical current-position calculator is never created or submitted.
        code = CHECKS.without_comments(self.source)
        self.assertNotRegex(code, r'\.TileLocation\s*=')
        self.assertNotRegex(code, r'\b(?:ModifyStateObject|CreateNewGameState|SubmitGameState|ActivateAbility_ReturnContext|Rand|FRand)\s*\(')
        self.assertNotIn('IterateByClassType(', code)

    def test_candidate_and_entire_native_blue_path_keep_safety_and_bounded_work(self):
        move = function_body(self.source, 'ChooseMove')
        for guard in ('Samples = Min(64, Tiles.Length)', 'PathCost > Visualizer.GetMobility()',
                      'CandidateRisk > CurrentRisk', 'BuildPathToTile(Tile, CandidatePath)',
                      'for (PathIndex = 1;', 'CanSquadSeeLocation(', 'IsSupportedAdvanceStep(',
                      'HasBlockingHazard(UnitState, CandidatePath[PathIndex])'):
            self.assertIn(guard, move)
        gather = function_body(self.source, 'GatherForecasts')
        self.assertIn('Forecasts.Length >= 16', gather)
        self.assertIn('Min(64, Cache.AvailableActions.Length)', gather)
        self.assertIn('Min(8, Candidate.AvailableTargets.Length)', gather)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Remote visibility contracts need SDK sources')
class OffensiveRepositionSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_remote_visibility_and_target_validation_match_stock_hud_preview(self):
        visibility = (self.sdk / 'X2GameRulesetVisibilityManager.uc').read_text(encoding='utf-8-sig')
        self.assertIn('bool GetVisibilityInfoFromRemoteLocation(int SourceStateObjectID, const out TTile RemoteTile, int TargetStateObjectID, out GameRulesCache_VisibilityInfo OutVisInfo', visibility)
        self.assertIn('bool EvaluateConditions(const out GameRulesCache_VisibilityInfo VisInfo, int HistoryIndex, array<X2Condition> RequiredConditions)', visibility)
        target = (self.sdk / 'X2AbilityTarget_Single.uc').read_text(encoding='utf-8-sig')
        self.assertIn('bool ValidatePrimaryTargetOptionFromRemoteLocation(XComGameState_Unit SourceUnit, const out TTile RemoteTile, XComGameState_BaseObject TargetObject)', target)
        hud = (self.sdk / 'UITacticalHUD_EnemyPreview.uc').read_text(encoding='utf-8-sig')
        for native_call in ('GetVisibilityInfoFromRemoteLocation(', 'VisibilityMgr.EvaluateConditions(',
                            'default.LivingHostileGameplayVisibleFilter', 'ValidatePrimaryTargetOptionFromRemoteLocation('):
            self.assertIn(native_call, hud)

    def test_range_bands_and_cover_terms_are_the_native_standard_aim_terms(self):
        aim = (self.sdk / 'X2AbilityToHitCalc_StandardAim.uc').read_text(encoding='utf-8-sig')
        ranges = function_body(aim, 'GetWeaponRangeModifier')
        self.assertIn('Tiles = Shooter.TileDistanceBetween(Target)', ranges)
        self.assertIn('WeaponTemplate.RangeAccuracy[WeaponTemplate.RangeAccuracy.Length-1]', ranges)
        for reason in ('TargetLowCover', 'TargetHighCover', 'BadAngleToTargetCover', 'AngleToTargetCover'):
            self.assertIn("class'XLocalizedData'.default." + reason, aim)
            self.assertIn("class'XLocalizedData'.default." + reason, SOURCE.read_text())
        unit = (self.sdk / 'XComGameState_Unit.uc').read_text(encoding='utf-8-sig')
        distance = function_body(unit, 'TileDistanceBetween')
        self.assertIn('VSize(UnitLoc - TargetLoc)', distance)
        self.assertIn('Tiles = Dist / WorldData.WORLD_StepSize', distance)

    def test_native_turn_ending_cost_can_be_overridden_by_own_abilities_or_effects(self):
        costs = (self.sdk / 'X2AbilityCost_ActionPoints.uc').read_text(encoding='utf-8-sig')
        consume = function_body(costs, 'ConsumeAllPoints')
        self.assertIn('DoNotConsumeAllSoldierAbilities', consume)
        self.assertIn('DoNotConsumeAllEffects', consume)
        weapons = (self.sdk / 'X2Ability_WeaponCommon.uc').read_text(encoding='utf-8-sig')
        self.assertIn("DoNotConsumeAllSoldierAbilities.AddItem('SkirmisherStrike')", weapons)


if __name__ == '__main__':
    unittest.main()
