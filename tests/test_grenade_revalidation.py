"""Revalidation diagnostics retain the native trajectory and blast boundaries.

Only scalar policy helpers run here. Native trajectory/collateral calculations
still require a Windows build and a real mission.
"""
import math
import os
from pathlib import Path
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_AreaAttackPlanner.uc'


class GrenadeRevalidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text()
        cls.landing = staticmethod(load_uc_function(SOURCE, 'LandingMatches'))
        cls.counts = staticmethod(load_uc_function(SOURCE, 'TargetCountsMatch'))

    def test_original_one_unit_landing_tolerance_is_not_relaxed(self):
        for squared_distance in (0, 0.25, 0.999999, 1):
            self.assertTrue(self.landing(squared_distance))
        for squared_distance in (-1, 1.000001, 96 * 96, math.inf, math.nan):
            self.assertFalse(self.landing(squared_distance))

    def test_expected_and_fresh_target_counts_must_be_equal_and_nonempty(self):
        self.assertTrue(self.counts(1, 1))
        self.assertTrue(self.counts(3, 3))
        for expected, fresh in ((0, 0), (1, 0), (0, 1), (1, 2), (2, 1), (-1, -1)):
            self.assertFalse(self.counts(expected, fresh))

    def test_every_preparation_failure_has_a_distinct_stage_reason(self):
        body = function_body(self.source, 'PrepareForActivation')
        for reason in ('unit_unavailable', 'invalid_plan_shape', 'runtime_unavailable',
                       'activation_path_unavailable', 'unit_cache_unavailable',
                       'ability_not_in_cache', 'ability_unavailable_or_unsupported',
                       'impact_rejected', 'landing_changed', 'fresh_impact_rejected',
                       'location_count_changed', 'target_location_changed',
                       'primary_target_changed', 'additional_target_count_changed',
                       'additional_target_set_changed'):
            self.assertIn('return RejectPreparation("' + reason + '")', body)
        self.assertNotIn('return false;', body)
        self.assertIn('PreparationReason = "ready";', body)

    def test_fresh_safety_target_and_landing_checks_still_precede_success(self):
        body = function_body(self.source, 'PrepareForActivation')
        stages = ('GetGameRulesCache_Unit(', 'GetSupportedGrenade(', 'ComputeImpact(',
                  'LandingMatches(PreparationImpactDeltaSquared)', 'EvaluateImpact(',
                  'LandingMatches(PreparationLocationDeltaSquared)',
                  'FreshTarget.PrimaryTarget != Action.AvailableTargets[0].PrimaryTarget',
                  'TargetCountsMatch(', 'SeenTargetIDs.Find(', 'PreparationReason = "ready"')
        positions = [body.index(stage) for stage in stages]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Action.AvailableTargets[0].AdditionalTargets.Find('ObjectID', TargetRef.ObjectID)", body)
        self.assertIn('SeenTargetIDs.AddItem(TargetRef.ObjectID)', body)
        self.assertIn('local array<int> SeenTargetIDs;', body)

    def test_preparation_evaluation_reason_is_fresh_without_changing_scan_summary(self):
        rejection = function_body(self.source, 'RejectScan')
        self.assertLess(rejection.index('LastEvaluationStage = string(Stage)'),
                        rejection.index('if (!bCollectDiagnostics)'))
        self.assertLess(rejection.index('LastEvaluationReason = Reason'),
                        rejection.index('if (!bCollectDiagnostics)'))
        body = function_body(self.source, 'PrepareForActivation')
        for reset in ('LastEvaluationStage = "none"', 'LastEvaluationReason = "none"',
                      'PreparationFreshTargets = -1', 'PreparationImpactDeltaSquared = -1.0'):
            self.assertLess(body.index(reset), body.index('GetSupportedGrenade('))
        self.assertNotIn('Scan =', body)

    def test_diagnostics_do_not_disclose_failed_unfiltered_targets(self):
        summary = function_body(self.source, 'GetPreparationDiagnostic')
        for forbidden in ('FreshTarget.', 'TargetRef.', 'ScanBlastBlockerID',
                          'IterateByClassType', 'GetGameStateForObjectID'):
            self.assertNotIn(forbidden, summary)
        body = function_body(self.source, 'PrepareForActivation')
        safe = body.index('return RejectPreparation("fresh_impact_rejected")')
        known_count = body.index('PreparationFreshTargets = FreshTarget.AdditionalTargets.Length')
        self.assertLess(safe, known_count)
        for field in ('reason=', 'evaluation_stage=', 'evaluation_reason=',
                      'impact_delta_sq=', 'location_delta_sq=', 'expected_targets=', 'fresh_targets='):
            self.assertIn(field, summary)

    def test_success_leaves_the_real_path_prepared_without_dispatch_or_cleanup(self):
        body = function_body(self.source, 'PrepareForActivation')
        self.assertIn('ComputeImpact(UnitState, Ability, AimLocation, `PRECOMPUTEDPATH, Impact)', body)
        for forbidden in ('ActivateAbility', 'Cleanup()', 'ClearPathGraphics(', 'Destroy(',
                          'ModifyStateObject(', 'SubmitGameState('):
            self.assertNotIn(forbidden, body)
        compute = function_body(self.source, 'ComputeImpact')
        self.assertIn('PathActor.SetWeaponAndTargetLocation(', compute)
        self.assertIn('PathActor.CalculateTrajectoryToTarget(', compute)
        self.assertNotIn('`PRECOMPUTEDPATH', compute)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Grenade contracts need SDK sources')
class GrenadeRevalidationSDKContracts(unittest.TestCase):
    def test_preview_and_activation_keep_the_stock_ai_path_pipeline_and_location_contract(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        ai = (sdk / 'XGAIBehavior.uc').read_text(encoding='utf-8-sig')
        path = function_body(ai, 'PrecomputeGrenadePath')
        self.assertIn('PPath = `PRECOMPUTEDPATH', path)
        self.assertIn('PPath.SetWeaponAndTargetLocation(', path)
        self.assertIn('PPath.CalculateTrajectoryToTarget(', path)
        ability = (sdk / 'XComGameState_Ability.uc').read_text(encoding='utf-8-sig')
        locations = function_body(ability, 'GatherAbilityTargetLocationsForLocation')
        self.assertIn('TargetLocations.Length = 0', locations)
        self.assertIn('TargetLocations.AddItem(Location)', locations)
        precomputed = (sdk / 'XComPrecomputedPath.uc').read_text(encoding='utf-8-sig')
        configure = function_body(precomputed, 'SetWeaponAndTargetLocation')
        for assignment in ('kCurrentWeapon = kWeapon', 'OverrideTargetLocation = TargetLocation',
                           'bUseOverrideTargetLocation = true', 'm_WeaponPrecomputedPathData = PrePathData'):
            self.assertIn(assignment, configure)


if __name__ == '__main__':
    unittest.main()
