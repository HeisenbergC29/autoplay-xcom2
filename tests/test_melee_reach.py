"""Possible next-turn melee reach must not look like a successful escape.

Scenarios execute the actual scalar UC helpers. Native range, pathfinding and
enemy decision behavior still require the stock compiler and game.
"""
import os
from pathlib import Path
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionPlanner.uc'


class MeleeReachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.risk = staticmethod(load_uc_function(SOURCE, 'MeleeReachRisk'))
        cls.legacy = staticmethod(load_uc_function(SOURCE, 'DirectionalRisk'))
        cls.moves = staticmethod(load_uc_function(SOURCE, 'MeleeMovementActions'))
        cls.reach = staticmethod(load_uc_function(SOURCE, 'MeleeReachFromBudget'))

    def test_legacy_d10_retreat_remains_a_reachable_melee_threat(self):
        # D10: Central moves from distance4.2426 to7.6158 from Faceless.
        # Before v8 this removed13.49 of its raw melee risk, although the
        # enemy subsequently moved and hit Central. A recognized reach12
        # keeps the open-threat floor at both positions.
        current = self.risk(4.2426, 12)
        destination = self.risk(7.6158, 12)
        self.assertGreaterEqual(current, 30)
        self.assertEqual(destination, 30)
        self.assertLess(current - destination, 2)
        self.assertGreater(self.legacy(0, 4.2426, False, True)
                           - self.legacy(0, 7.6158, False, True), 13)

    def test_geometry_and_fresh_turn_budget_replace_the_fixed_reach_cutoff(self):
        # Stock: mobility meters/AP,64worldunits/m,96worldunits/tile.
        # One move remains when a separate melee cone attack costs1of2AP.
        moves = self.moves(2, 1, 0, False)
        cone_radius_tiles = (3 ** 2 + (5 / 2) ** 2) ** 0.5
        possible_reach = self.reach(14 * 64 / 96, moves, cone_radius_tiles)
        self.assertGreater(possible_reach, 13)
        self.assertEqual(self.legacy(0, 12.5, False, True), 0)
        self.assertEqual(self.risk(12.5, possible_reach), 30)

    def test_moving_attack_uses_its_native_movement_range_adjustment(self):
        self.assertEqual(self.moves(2, 1, 0, True), 2)
        self.assertEqual(self.moves(2, 1, 1, True), 1)
        self.assertEqual(self.moves(2, 1, 2, True), 0)
        self.assertEqual(self.moves(2, 2, 0, False), 0)
        self.assertGreater(self.reach(8, self.moves(2, 1, 0, True), 1.58),
                           self.reach(8, self.moves(2, 1, 0, False), 1.58))

    def test_unsupported_or_outside_envelope_keeps_residual_legacy_risk(self):
        for distance in (0, 3, 7, 10, 15, 30):
            self.assertEqual(self.risk(distance, -1),
                             self.legacy(0, distance, False, True))
        # Passing a recognized short reach must not erase the old residual.
        self.assertGreater(self.risk(9, 8), 0)
        self.assertEqual(self.risk(9, 8), self.legacy(0, 9, False, True))
        self.assertGreater(self.risk(0, 12), self.risk(7, 12))

    def test_reach_reads_templates_and_mobility_without_hidden_enemy_ap(self):
        text = SOURCE.read_text()
        reach = function_body(text, 'GetMeleeThreatReach')
        threat = function_body(text, 'ThreatRiskAtTile')
        for required in ('StandardActionsPerTurn', 'GetCurrentStat(eStat_Mobility)',
                         'WORLD_METERS_TO_UNITS_MULTIPLIER', 'WORLD_StepSize',
                         'MovementRangeAdjustment', 'Cone.GetHitRange(Ability)',
                         'APCost.GetPointCost(Ability, Enemy)', 'Enemy.Abilities'):
            self.assertIn(required, reach)
        for forbidden in ('Enemy.ActionPoints', 'NumActionPoints(',
                          'GetGameRulesCache_Unit', "'Faceless'", 'ApplyCost('):
            self.assertNotIn(forbidden, reach)
        self.assertIn('return -1.0;', reach)
        self.assertIn('Enemy.Abilities.Length > 64', reach)
        self.assertLess(reach.index('Enemy.Abilities.Length > 64'),
                        reach.index('foreach Enemy.Abilities'))
        self.assertLess(reach.index('if (APCost.bAddWeaponTypicalCost)'),
                        reach.index('APCost.GetPointCost(Ability, Enemy)'))
        self.assertIn('SourceWeapon == none || X2WeaponTemplate(SourceWeapon.GetMyTemplate()) == none', reach)
        self.assertLess(threat.index('GetMeleeThreatReach(Enemy)'),
                        threat.index('GetCoverTypeForTarget('))
        self.assertIn('MeleeReachRisk(TileDistance(Tile, Enemy.TileLocation), MeleeReach)', threat)

    def test_movement_search_reuses_its_local_reaches_outside_the_tile_loop(self):
        text = SOURCE.read_text()
        move = function_body(text, 'ChooseMove')
        cache = function_body(text, 'GetMeleeThreatReaches')
        exposure = function_body(text, 'ExposureRisk')
        position = function_body(text, 'PositionScore')
        threat = function_body(text, 'ThreatRiskAtTile')
        self.assertIn('local array<float> MeleeThreatReaches;', move)
        self.assertEqual(move.count('GetMeleeThreatReaches('), 1)
        self.assertLess(move.index('GetMeleeThreatReaches('),
                        move.index('for (SampleIndex = 0;'))
        self.assertNotIn('GetMeleeThreatReach(', move)
        self.assertIn('Reaches.Length = VisibleEnemies.Length;', cache)
        self.assertIn('Reaches[Index] = -1.0;', cache)
        self.assertIn('Reaches[Index] = GetMeleeThreatReach(Enemy);', cache)
        self.assertIn('MeleeThreatReaches.Length == VisibleEnemies.Length', exposure)
        self.assertIn('KnownMeleeReach = -2.0;', exposure)
        self.assertIn('KnownMeleeReach = MeleeThreatReaches[Index];', exposure)
        self.assertIn('ThreatRiskAtTile(UnitState, Enemy, Tile, KnownMeleeReach, KnownWeight)', exposure)
        self.assertIn('ExposureRisk(UnitState, Tile, VisibleEnemies, MeleeThreatReaches, ThreatWeights)', position)
        self.assertIn('if (MeleeReach == -2.0)', threat)
        self.assertEqual(threat.count('GetMeleeThreatReach(Enemy)'), 1)
        for body in (move, cache, exposure, position, threat):
            self.assertNotIn('default.MeleeThreatReaches', body)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'SDK reach contracts need APX_SDK_SOURCE_ROOT')
class MeleeReachSDKContracts(unittest.TestCase):
    def test_native_movement_budget_and_cone_range_units_match_the_model(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        moving = (sdk / 'X2AbilityTarget_MovingMelee.uc').read_text(encoding='utf-8-sig')
        self.assertIn('NumMovementPoints - MovementRangeAdjustment', moving)
        cone = (sdk / 'X2AbilityMultiTarget_Cone.uc').read_text(encoding='utf-8-sig')
        self.assertIn('Returns distance in Units', cone)
        self.assertIn('GetHitRange(const XComGameState_Ability Ability)', cone)
        world = (sdk / 'XComWorldData.uc').read_text(encoding='utf-8-sig')
        self.assertRegex(world, r'const\s+WORLD_METERS_TO_UNITS_MULTIPLIER\s*=\s*64\.0')
        self.assertRegex(world, r'const\s+WORLD_StepSize\s*=\s*96\.0')
        unit = (sdk / 'XGUnit.uc').read_text(encoding='utf-8-sig')
        distance = function_body(unit, 'GetMaxPathDistance')
        self.assertIn('GetCurrentStat(eStat_Mobility)', distance)
        self.assertIn('StandardActionsPerTurn', distance)

    def test_optional_read_only_array_parameters_have_stock_sdk_precedent(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        path = (sdk / 'XComPath.uc').read_text(encoding='utf-8-sig')
        self.assertIn('optional const out array<TTile> PinnedTiles', path)
        panel = (sdk / 'UIPanel.uc').read_text(encoding='utf-8-sig')
        self.assertIn('optional float Delay = -1.0', panel)
        source = SOURCE.read_text()
        self.assertIn('optional const out array<float> MeleeThreatReaches', source)
        self.assertIn('optional float KnownMeleeReach=-2.0', source)


if __name__ == '__main__':
    unittest.main()
