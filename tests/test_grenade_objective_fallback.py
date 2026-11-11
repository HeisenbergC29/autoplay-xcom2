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
        cls.near=staticmethod(load_uc_function(SOURCE, 'RectangleNearImpact'))

    def test_rectangle_handles_large_offset_prop_instead_of_anchor_padding(self):
        # A prop anchored at x=0 reaches x=600. Its far panel is only 10 units
        # from this blast; the old anchor + 128 padding would call it safe.
        self.assertTrue(self.near(610,0,0,-40,600,40,20,True))
        self.assertFalse(self.near(650,0,0,-40,600,40,20,True))
        self.assertTrue(self.near(300,0,0,-40,600,40,0,True))

    def test_rectangle_checks_corners_edges_and_vertical_column(self):
        self.assertTrue(self.near(13,14,0,0,10,10,5,True))
        self.assertFalse(self.near(13,14,0,0,10,10,4.99,True))
        self.assertTrue(self.near(-3,5,0,0,10,10,3,True))
        self.assertTrue(self.near(10,10,0,0,10,10,0,True))
        # Helper deliberately has no Z parameter: ceilings/floors are protected.
        self.assertNotIn('ImpactZ',function_body(self.source,'RectangleNearImpact'))

    def test_unknown_invalid_or_nonfinite_geometry_fails_closed(self):
        self.assertTrue(self.near(1000,1000,0,0,10,10,1,False))
        self.assertTrue(self.near(1000,1000,20,0,10,10,1,True))
        self.assertTrue(self.near(1000,1000,0,0,10,10,-1,True))
        for value in (float('nan'),float('inf'),-float('inf')):
            self.assertTrue(self.near(value,0,0,0,10,10,1,True))
            self.assertTrue(self.near(0,0,0,0,value,10,1,True))

    def test_native_geometry_never_guesses_anchor_or_refreshes_live_state(self):
        f=function_body(self.source,'FootprintNearImpact')
        for token in ('KnownState == none', 'KnownState.bRemoved',
                      'UnitState.GetVisibilityForLocation(UnitState.TileLocation, Tiles)',
                      'IsTileOutOfRange(Tile)', 'TryGetObjectiveGeometry(',
                      'RectangleNearImpact(', 'unknown_objective_bounds'):
            with self.subTest(token=token):
                self.assertIn(token,f)
        self.assertIn('GetVisibilityLocation(Tiles)',f)
        self.assertIn('Delta.Z = 0.0;',f)
        self.assertNotIn('DestructibleState.TileLocation',f)
        self.assertNotIn('Tiles.AddItem(',f)
        self.assertNotIn('ConservativeFallbackRadius',self.source)
        bounds=function_body(self.source,'TryGetObjectiveGeometry')
        for token in ('KnownState.GetVisualizer()', 'Visualizer.bDeleteMe',
                      'Visualizer.ObjectID != KnownState.ObjectID',
                      'GetComponentsBoundingBox(GeometryBounds)',
                      "AllOwnedComponents(class'PrimitiveComponent'",
                      'Component.Owner != Visualizer', '!Component.bAttached',
                      'Component.bNeedsReattach', 'Component.bNeedsUpdateTransform',
                      'NumComponents > 64', 'Component.Bounds.Origin - Component.Bounds.BoxExtent',
                      'Component.Bounds.Origin + Component.Bounds.BoxExtent',
                      'CheckedComponents.Find(Interactive.AttachedMesh1)',
                      'CheckedComponents.Find(Interactive.AttachedMesh2)',
                      'UsableGeometryBox(GeometryBounds)'):
            with self.subTest(token=token):
                self.assertIn(token,bounds)
        for mutation in ('ForceUpdate(', 'UpdateComponent(', 'SetTranslation(',
                         'FindOrCreateVisualizer(', 'SyncVisualizer('):
            self.assertNotIn(mutation,bounds)

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
    def test_native_geometry_api_and_noncolliding_panels(self):
        path=Path(os.environ['APX_SDK_SOURCE_ROOT'])
        if not (path/'XComGame/Classes/XComGameState_Destructible.uc').is_file():
            path=path/'Development/SrcOrig'
        def read(package,name):
            return (path/package/'Classes'/f'{name}.uc').read_text(encoding='utf-8-sig',errors='replace')
        actor=read('Engine','Actor')
        component=read('Engine','ActorComponent')
        primitive=read('Engine','PrimitiveComponent')
        unit=read('XComGame','XComGameState_Unit')
        interactive=read('XComGame','XComInteractiveLevelActor')
        destructible=read('XComGame','XComDestructibleActor')
        self.assertIn('GetComponentsBoundingBox(out box ActorBox) const;',actor)
        self.assertIn('AllOwnedComponents(class<Component> BaseClass, out ActorComponent OutComponent)',actor)
        self.assertIn('GetComponentsBoundingBox(UBOOL bNonColliding=0)',actor)
        for flag in ('bAttached','bNeedsReattach','bNeedsUpdateTransform','Owner'):
            self.assertIn(flag,component)
        self.assertIn('BoxSphereBounds Bounds;',primitive)
        self.assertIn('GetVisibilityForLocation(const out TTile FromLocation, out array<TTile> VisibilityTiles) const;',unit)
        self.assertIn('protectedwrite int ObjectID;',destructible)
        for mesh in ('AttachedMesh1','AttachedMesh2'):
            self.assertIn('StaticMeshComponent '+mesh,interactive)
        for panel in ('CoveringMeshComponent1','CoveringMeshComponent2'):
            definition=interactive.split('Name='+panel,1)[1].split('End Object',1)[0]
            self.assertIn('CollideActors=false',definition)


if __name__=='__main__':
    unittest.main()
