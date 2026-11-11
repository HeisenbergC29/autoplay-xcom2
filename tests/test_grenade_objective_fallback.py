"""Regression checks for the legitimate native grenade-launcher geometry case.

The WOTC engine must still perform real ability, trajectory and damage checks.
These tests do not prove the fallback works in a built game.
"""
from pathlib import Path
import os
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_AreaAttackPlanner.uc'


class LauncherObjectiveFootprintContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SOURCE.read_text(encoding='utf-8-sig')
        cls.radius=staticmethod(load_uc_function(SOURCE, 'ConservativeFallbackRadius'))

    def test_state_location_requires_conservative_padding(self):
        self.assertEqual(self.radius(0, 64),128)
        self.assertEqual(self.radius(256, 64),384)
        self.assertEqual(self.radius(-1,64),128)
        self.assertEqual(self.radius(256,-1),256)
        self.assertGreater(self.radius(300, 64),300)

    def test_no_guessed_tile_and_missing_location_still_rejects(self):
        f=function_body(self.source,'FootprintNearImpact')
        for token in ('KnownState == none', 'KnownState.bRemoved',
                      'DestructibleState.TileLocation', 'UnitState.TileLocation',
                      'IsTileOutOfRange(Tile)', 'ConservativeFallbackRadius(',
                      'Tiles.AddItem(Tile)', 'known_state_tile_fallback'):
            with self.subTest(token=token):
                self.assertIn(token,f)
        self.assertGreaterEqual(f.count('return true;'),3)
        self.assertIn('GetVisibilityLocation(Tiles)',f)
        self.assertIn('Delta.Z = 0.0;',f)
        self.assertIn('VSizeSq(Delta) <= Square(TestedRadius)',f)

    def test_real_native_launch_grenade_still_requires_current_owner_and_contract(self):
        get=function_body(self.source,'GetSupportedGrenade')
        for token in ("AbilityName != 'ThrowGrenade' && AbilityName != 'LaunchGrenade'",
                      "Action.AvailableCode != 'AA_Success'",
                      "Ability.OwnerStateObject.ObjectID != UnitState.ObjectID",
                      "Template.TargetingMethod != class'X2TargetingMethod_Grenade'",
                      "Grenade.DataName != 'FragGrenade' && Grenade.DataName != 'AlienGrenade'"):
            self.assertIn(token,get)
        blast=function_body(self.source,'BlastIsSafe')
        self.assertIn('IsProtectedUnit(UnitState, OtherUnit)',blast)
        self.assertIn('HasDangerousScenery(',blast)
        self.assertIn('"objective_near_blast"',blast)
        self.assertIn('SafeRadius, ObjectiveOwner)',blast)
        self.assertIn('SafeRadius, OtherUnit)',blast)
        self.assertIn('SafeRadius, Interactive)',blast)

    def test_does_not_override_native_score_or_fire(self):
        for forbidden in ('SubmitGameState', 'CreateNewGameState',
                          'RollForAbility', 'ChangeAmmo', 'SetNumActionPoints',
                          'CompleteObjective'):
            self.assertNotIn(forbidden,self.source)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'Needs the private SDK (never publish SDK files)')
class LauncherObjectiveSDKContracts(unittest.TestCase):
    def test_state_tile_native_property(self):
        path=Path(os.environ['APX_SDK_SOURCE_ROOT'])
        if (path/'XComGame/Classes/XComGameState_Destructible.uc').is_file():
            folder=path/'XComGame/Classes'
        else:
            folder=path/'Development/SrcOrig/XComGame/Classes'
        destructible=(folder/'XComGameState_Destructible.uc').read_text(encoding='utf-8-sig')
        interactive=(folder/'XComGameState_InteractiveObject.uc').read_text(encoding='utf-8-sig')
        self.assertIn('var TTile TileLocation;',destructible)
        self.assertIn('NativeGetVisibilityLocation(',destructible)
        self.assertIn('extends XComGameState_Destructible',interactive)


if __name__=='__main__':
    unittest.main()
