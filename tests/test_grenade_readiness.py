"""Stock grenade preview readiness and rejection-trace source contracts.

The native trajectory cannot run here. These checks protect the stock visualizer
initialization path and the bounded diagnostic boundary without weakening blast
safety or pretending to prove grenade use in the uploaded mission.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_AreaAttackPlanner.uc').read_text()


class GrenadeReadinessContracts(unittest.TestCase):
    def test_native_preview_initializes_stowed_grenade_before_trajectory(self):
        body = function_body(SOURCE, 'ComputeImpact')
        initialize = body.index("class'XGItem'.static.CreateVisualizer(SourceWeapon)")
        entity = body.index('WeaponVisualizer.CreateEntity(SourceWeapon)')
        pawn = body.index('WeaponEntity.m_kPawn = UnitVisualizer.GetPawn()')
        trajectory = body.index('PathActor.CalculateTrajectoryToTarget(')
        self.assertLess(initialize, entity)
        self.assertLess(entity, pawn)
        self.assertLess(pawn, trajectory)
        self.assertIn('if (WeaponVisualizer == none)', body)
        self.assertIn('if (WeaponEntity == none)', body)
        self.assertIn('if (WeaponEntity.m_kPawn == none)', body)
        self.assertIn('PathActor.ClearOverrideTargetLocation();', body)

    def test_preview_does_not_activate_player_targeting_or_issue_an_order(self):
        body = function_body(SOURCE, 'ComputeImpact')
        self.assertNotIn('`PRECOMPUTEDPATH', body)
        self.assertNotIn('ActivateAbility', body)
        self.assertNotIn('TargetingMethod.Init', body)
        self.assertIn('PathActor.SetWeaponAndTargetLocation(', body)

    def test_diagnostics_are_reset_per_scan_and_frozen_before_activation(self):
        choose = function_body(SOURCE, 'ChooseAction')
        self.assertIn('Scan = EmptyScan;', choose)
        self.assertIn('Scan.Centers += Centers.Length;', choose)
        self.assertIn('++Scan.Evaluated;', choose)
        self.assertIn('++Scan.Accepted;', choose)
        self.assertNotRegex(choose, r'\breturn\s+(?:false|bFound)\s*;')
        self.assertIn('bCollectDiagnostics = false;', function_body(SOURCE, 'EndScan'))
        self.assertIn('if (!bCollectDiagnostics)', function_body(SOURCE, 'RejectScan'))
        self.assertNotIn('`log(', CHECKS.without_comments(SOURCE))
        self.assertNotIn('Scan =', function_body(SOURCE, 'PrepareForActivation'))

    def test_diagnostics_keep_native_filters_and_safety_checks(self):
        evaluate = function_body(SOURCE, 'EvaluateImpact')
        self.assertLess(evaluate.index('BlastIsSafe('), evaluate.index('ScoreBlast('))
        self.assertIn('Radius.CheckFilteredMultiTargets(Ability, Target)', evaluate)
        self.assertIn("RejectScan('blast', LastBlastReason)", evaluate)
        self.assertIn("RejectScan('targets',", evaluate)
        self.assertIn("RejectScan('score',", evaluate)
        blast = function_body(SOURCE, 'BlastIsSafe')
        self.assertIn('IsProtectedUnit(UnitState, OtherUnit)', blast)
        self.assertIn('HasDangerousScenery(', blast)
        self.assertIn('FootprintNearImpact(', blast)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Set APX_SDK_SOURCE_ROOT to check stock grenade visualizer contracts')
class GrenadeReadinessSDKContracts(unittest.TestCase):
    def test_initialization_matches_stock_grenade_targeting_prerequisites(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        targeting = (sdk / 'X2TargetingMethod_Grenade.uc').read_text(encoding='utf-8-sig')
        self.assertIn("class'XGItem'.static.CreateVisualizer(WeaponItem)", targeting)
        self.assertIn('WeaponVisualizer.CreateEntity(WeaponItem)', targeting)
        self.assertIn('WeaponEntity.m_kPawn = FiringUnit.GetPawn()', targeting)
        item = (sdk / 'XGItem.uc').read_text(encoding='utf-8-sig')
        weapon = (sdk / 'XGWeapon.uc').read_text(encoding='utf-8-sig')
        self.assertRegex(item, r'static\s+function\s+XGItem\s+CreateVisualizer\(XComGameState_Item\s+ItemState')
        self.assertRegex(weapon, r'function\s+Actor\s+CreateEntity\(optional\s+XComGameState_Item')


if __name__ == '__main__':
    unittest.main()
