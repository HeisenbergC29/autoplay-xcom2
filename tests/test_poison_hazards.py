"""Public poison-cloud safety and its source-backed limits.

Pure tests execute the real UC helpers. Source contracts do not replace native
pathfinding, Windows compilation, cloud visualization or a game mission.
"""
import itertools
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body, braced_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_HazardKnowledge.uc'


class PoisonHazardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harmful = staticmethod(load_uc_function(HELPER, 'PoisonCloudIsHarmful'))
        cls.prefix = staticmethod(load_uc_function(HELPER, 'MayCrossStartingPoison'))

    def test_only_susceptible_non_robotic_units_treat_poison_cloud_as_harmful(self):
        for poison, robotic, immune in itertools.product((False, True), repeat=3):
            with self.subTest(poison=poison, robotic=robotic, immune=immune):
                self.assertEqual(self.harmful(poison, robotic, immune),
                                 poison and not robotic and not immune)

    def test_continuous_initial_poison_prefix_can_be_crossed_but_not_reentered(self):
        self.assertTrue(self.prefix(True, False, True, False))
        # Starting outside, having already left, a clean step, or another hazard
        # cannot use the poison exception to bypass the ordinary path guards.
        for started, left, poison, other in itertools.product((False, True), repeat=4):
            with self.subTest(started=started, left=left, poison=poison, other=other):
                self.assertEqual(self.prefix(started, left, poison, other),
                                 (started, left, poison, other) == (True, False, True, False))

    def test_poison_query_is_gated_by_own_tile_or_current_squad_visibility(self):
        body = function_body(HELPER.read_text(), 'IsKnownPoisonCloudAtTile')
        self.assertIn('UnitState == none', body)
        self.assertIn('Tile != UnitState.TileLocation', body)
        self.assertIn('CanSquadSeeLocation(', body)
        self.assertIn('UnitState.GetAssociatedPlayerID(), Tile)', body)
        self.assertLess(body.index('CanSquadSeeLocation('), body.index('TileContainsPoison(Tile)'))
        self.assertNotIn('IterateByClassType', body)
        self.assertNotIn('WorldEffectTileData', body)

    def test_existing_poisoned_status_is_not_mistaken_for_immunity(self):
        source = HELPER.read_text()
        body = function_body(source, 'IsHarmfulPoisonCloudAtTile')
        self.assertIn("UnitState.IsImmuneToDamage('Poison')", body)
        self.assertIn('UnitState.IsRobotic()', body)
        self.assertNotIn('IsPoisoned(', source)
        self.assertNotIn('IsAlreadyTakingEffectDamage(', source)
        escape = function_body(source, 'NeedsPoisonEscape')
        self.assertIn('IsHarmfulPoisonCloudAtTile(UnitState, UnitState.TileLocation)', escape)

    def test_explicit_poison_does_not_replace_native_hazard_safety(self):
        source = HELPER.read_text()
        body = function_body(source, 'HasBlockingHazard')
        self.assertIn("class'XComPath'.static.TileContainsHazard(UnitState, Tile)", body)
        self.assertIn('|| IsHarmfulPoisonCloudAtTile(UnitState, Tile)', body)
        exception = function_body(source, 'CanCrossStartingPoisonTile')
        self.assertIn('bAlreadyReachedCleanTile || !NeedsPoisonEscape(UnitState)', exception)
        self.assertIn('!IsHarmfulPoisonCloudAtTile(UnitState, Tile)', exception)
        self.assertIn('WorldData.TileContainsFire(Tile) || WorldData.TileContainsAcid(Tile)', exception)
        self.assertLess(exception.index('IsHarmfulPoisonCloudAtTile('),
                        exception.index('WorldData.TileContainsFire('))

    def test_helpers_are_read_only_and_do_not_inspect_enemy_readiness(self):
        source = HELPER.read_text()
        for forbidden in ('ModifyStateObject(', 'SubmitGameState(', 'CreateNewGameState(',
                          'CanActivateAbility(', '.ActionPoints', '.Ammo', 'GetUnitValue(',
                          'IterateByClassType', 'SourceStateObjectID'):
            self.assertNotIn(forbidden, source)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Poison contracts need SDK sources')
class PoisonSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_public_native_world_queries_and_damage_immunity_signatures_exist(self):
        world = (self.sdk / 'XComWorldData.uc').read_text(encoding='utf-8-sig')
        for name in ('Poison', 'Fire', 'Acid'):
            self.assertIn('native function bool TileContains' + name + '(const out TTile kTile)', world)
        unit = (self.sdk / 'XComGameState_Unit.uc').read_text(encoding='utf-8-sig')
        self.assertIn('simulated native function bool IsRobotic() const;', unit)
        self.assertIn('event bool IsImmuneToDamage(name DamageType)', unit)
        immune = function_body(unit, 'IsImmuneToDamage')
        self.assertIn('IsImmuneToDamageCharacterTemplate(DamageType)', immune)
        self.assertIn('ProvidesDamageImmunity(EffectState, DamageType)', immune)
        path = (self.sdk / 'XComPath.uc').read_text(encoding='utf-8-sig')
        self.assertIn('TileContainsHazard(const XComGameState_Unit PathingUnit, const out TTile Tile)', path)

    def test_cloud_applies_poisoned_status_and_existing_status_refreshes(self):
        cloud = (self.sdk / 'X2Effect_ApplyPoisonToWorld.uc').read_text(encoding='utf-8-sig')
        entered = re.search(r'event\s+array<X2Effect>\s+GetTileEnteredEffects\(\)\s*\{', cloud)
        self.assertIsNotNone(entered)
        self.assertIn("class'X2StatusEffects'.static.CreatePoisonedStatusEffect()",
                      braced_body(cloud, entered.end() - 1))
        status = (self.sdk / 'X2StatusEffects.uc').read_text(encoding='utf-8-sig')
        poisoned = function_body(status, 'CreatePoisonedStatusEffect')
        for actual in ('DuplicateResponse = eDupe_Refresh', 'ExcludeRobotic = true',
                       "DamageTypes.AddItem('Poison')", 'eStat_Mobility', 'eStat_Offense'):
            self.assertIn(actual, poisoned)


if __name__ == '__main__':
    unittest.main()
