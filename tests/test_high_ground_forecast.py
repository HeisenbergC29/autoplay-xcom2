"""Conservative new high-ground forecast, not an additional native shot bonus.

Pure helper is interpreted from current UnrealScript; structural tests assert
retained native remote LOS/target/AP/path and no history mutation. Windows WOTC
compiler/gameplay are separate checks.
"""
import os
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import CHECKS, function_body

ROOT=Path(__file__).resolve().parents[1]
CLASSES=ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes'
REPOSITION=CLASSES/'APX_RepositionPlanner.uc'
MISSION=CLASSES/'APX_MissionPlanner.uc'
INI=ROOT/'AutoplayXCom2/Config/XComAutoplayXCom2.ini'

class HighGroundForecastContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=REPOSITION.read_text(encoding='utf-8-sig')
        cls.mission=MISSION.read_text(encoding='utf-8-sig')
        cls.height=staticmethod(load_uc_function(REPOSITION,'ProjectedHeightAimBonus'))
        cls.chance=staticmethod(load_uc_function(REPOSITION,'ProjectedHitChance'))

    def test_crossing_stock_three_z_estimates_only_discounted_new_gain(self):
        self.assertEqual(self.height(0,3,3,20,5,False),15)
        self.assertEqual(self.height(-2,4,3,20,5,False),15)
        # The same unit may already get the native height modifier now.
        self.assertEqual(self.height(3,4,3,20,5,False),0)
        self.assertEqual(self.height(0,3,3,20,5,True),0)
        self.assertEqual(self.height(0,2,3,20,5,False),0)
        self.assertEqual(self.height(0,0,3,20,5,False),0)
        self.assertEqual(self.height(4,3,3,20,5,False),0)

    def test_invalid_settings_and_large_discounts_fail_closed(self):
        self.assertEqual(self.height(0,3,0,20,5,False),0)
        self.assertEqual(self.height(0,3,3,0,5,False),0)
        self.assertEqual(self.height(0,3,3,-2,5,False),0)
        self.assertEqual(self.height(0,3,3,20,30,False),0)
        self.assertEqual(self.height(0,3,3,20,-4,False),20)

    def test_bounded_projected_chance_retains_uncertainty(self):
        bonus=self.height(0,3,3,20,5,False)
        self.assertEqual(self.chance(55,bonus,0),70)
        self.assertEqual(self.chance(80,bonus,0),95)
        self.assertEqual(self.chance(40,1000,1000),75)
        self.assertEqual(self.chance(70,-1000,-1000),35)

    def test_current_native_height_not_added_twice(self):
        gather=function_body(self.source,'GatherForecasts')
        project=function_body(self.source,'ProjectAtTile')
        self.assertIn('Forecast.bCurrentNativeHeightAdvantage = UnitState.HasHeightAdvantageOver(',gather)
        self.assertIn('TargetUnit, true',gather)
        self.assertIn('Forecast.bCurrentNativeHeightAdvantage',project)
        self.assertIn('ProjectedHeightAimBonus(',project)
        self.assertIn('UnitState.GetHeightAdvantageBonusZ()',project)
        self.assertIn("class'X2TacticalGameRuleset'.default.UnitHeightAdvantageBonus",project)
        self.assertIn("class'X2TacticalGameRuleset'.default.UnitHeightAdvantage",project)
        self.assertIn('RangeModifier - Forecast.CurrentRangeModifier + HeightBonus',project)
        self.assertIn('Forecast.NativeChance',project)
        self.assertIn('Ability.GetShotBreakdown(Target, Breakdown)',gather)

    def test_remote_legal_moves_and_no_unanchored_rooftop_assumptions(self):
        project=function_body(self.source,'ProjectAtTile')
        move=function_body(self.source,'ChooseMove')
        for required in ('GetVisibilityInfoFromRemoteLocation(', 'EvaluateConditions(',
                         'ValidatePrimaryTargetOptionFromRemoteLocation(',
                         'Visibility.TargetCover != CT_None',
                         'Tile.Z < UnitState.TileLocation.Z',
                         'Clamp(default.MaxElevationGainTiles, 1, 8)'):
            with self.subTest(required=required):
                self.assertIn(required,project)
        for required in ('GetAllPathableTiles(', 'GetPathCostToTile(',
                         'IsSupportedCombatDestination(', 'IsSupportedAdvanceDestination(',
                         'CandidateRisk > CurrentRisk', 'BuildPathToTile(',
                         'IsSupportedAdvanceStep(', 'HasBlockingHazard(UnitState, CandidatePath[PathIndex])',
                         'bSafe', 'MaxElevationGainTiles'):
            with self.subTest(required=required):
                self.assertIn(required,move)
        self.assertIn('!Aim.bMeleeAttack',function_body(self.source,'SupportsForecast'))
        for forbidden in ('ModifyStateObject(', 'SubmitGameState(', 'CreateNewGameState(',
                          'ActivateAbility_ReturnContext(', 'Rand(', 'FRand('):
            self.assertNotIn(forbidden,self.source)
        self.assertNotIn('.TileLocation =',self.source)

    def test_position_utility_uses_stock_height_threshold_not_any_one_z(self):
        offensive=function_body(self.mission,'OffensivePositionScore')
        self.assertIn('Tile.Z + UnitState.GetHeightAdvantageBonusZ()',offensive)
        self.assertIn('!UnitState.IsMeleeOnly()',offensive)
        self.assertIn("EnemyTile.Z + Max(1, class'X2TacticalGameRuleset'.default.UnitHeightAdvantage)",offensive)
        self.assertNotIn('Tile.Z > EnemyTile.Z',offensive)
        fire=function_body(self.mission,'FiringPositionValue')
        self.assertIn('bHighGround && Distance <= 18.0',fire)
        self.assertNotIn('UnitHeightAdvantageBonus',fire)  # utility != hit chance

    def test_opt_out_and_conservative_default(self):
        ini=INI.read_text()
        section=ini.split('[AutoplayXCom2.APX_RepositionPlanner]',1)[1].split('[',1)[0]
        self.assertIn('EnableElevatedShotForecast=true',section)
        self.assertIn('MaxElevationGainTiles=6',section)
        self.assertIn('HeightForecastDiscount=5',section)
        for field in ('EnableElevatedShotForecast','MaxElevationGainTiles',
                      'HeightForecastDiscount'):
            self.assertIn('var config',self.source)
            self.assertIn(field,self.source)

@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'Private WOTC SDK required for native height API contracts')
class NativeHighGroundSDKContracts(unittest.TestCase):
    def test_stock_height_rule_and_ability_source(self):
        sdk=CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT']))/'XComGame/Classes'
        rules=(sdk/'X2TacticalGameRuleset.uc').read_text(encoding='utf-8-sig')
        unit=(sdk/'XComGameState_Unit.uc').read_text(encoding='utf-8-sig')
        aim=(sdk/'X2AbilityToHitCalc_StandardAim.uc').read_text(encoding='utf-8-sig')
        self.assertIn('var config int UnitHeightAdvantage;',rules)
        self.assertIn('var config int UnitHeightAdvantageBonus;',rules)
        self.assertIn('HasHeightAdvantageOver(',unit)
        self.assertIn('GetHeightAdvantageBonusZ()',unit)
        self.assertIn('UnitState.HasHeightAdvantageOver(TargetState, true)',aim)

if __name__ == '__main__':
    unittest.main()
