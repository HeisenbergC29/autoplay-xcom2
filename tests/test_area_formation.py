"""Regressions for the sampled formation heuristic, not native AoE hit tests.

Numeric checks execute the actual UC scalar helpers. Source contracts cover
the array/vector wiring that this small adapter cannot compile or execute.
"""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionPlanner.uc'


class AreaFormationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding='utf-8-sig')
        cls.inside = staticmethod(load_uc_function(SOURCE, 'AreaRiskPointInside'))
        cls.penalty = staticmethod(load_uc_function(SOURCE, 'ScoreSharedAreaTargets'))

    def count_sample(self, positions, center, radius=3.0):
        # The geometric predicate comes from UC; these explicit sample centers
        # are independently specified regression fixtures, not another search.
        return sum(self.inside(*(p[i] - center[i] for i in range(3)), radius)
                   for p in positions)

    def test_pair_triple_and_larger_group_have_bounded_growing_cost(self):
        self.assertEqual(self.penalty(1, 6.0), 0.0)
        self.assertEqual(self.penalty(2, 6.0), 6.0)
        self.assertEqual(self.penalty(3, 6.0), 18.0)
        self.assertEqual(self.penalty(4, 6.0), 36.0)
        self.assertEqual(self.penalty(5, 6.0), 48.0)
        self.assertEqual(self.penalty(100, 6.0), 48.0)
        self.assertLess(self.penalty(2, 6.0), self.penalty(3, 6.0))

    def test_disabled_weight_and_no_other_survivor_have_no_cost(self):
        for count in (0, 1, 2, 10):
            self.assertEqual(self.penalty(count, 0.0), 0.0)
            self.assertEqual(self.penalty(count, -5.0), 0.0)
        self.assertEqual(self.penalty(0, 6.0), 0.0)
        self.assertEqual(self.penalty(1, 100.0), 0.0)

    def test_between_target_center_finds_pair_missed_by_unit_centers(self):
        positions = [(0.0, 0.0, 0.0), (5.0, 0.0, 0.0)]
        self.assertEqual(self.count_sample(positions, positions[0]), 1)
        self.assertEqual(self.count_sample(positions, positions[1]), 1)
        count = self.count_sample(positions, (2.5, 0.0, 0.0))
        self.assertEqual(count, 2)
        self.assertGreater(self.penalty(count, 6.0), 0.0)

    def test_historical_poison_triple_is_not_zero_like_old_separation(self):
        positions = [(16.0, 15.0, 0.5), (18.0, 13.0, 0.5),
                     (20.0, 15.0, 0.5)]
        count = self.count_sample(positions, (18.0, 43.0 / 3.0, 0.5))
        self.assertEqual(count, 3)
        self.assertGreater(self.penalty(count, 6.0), self.penalty(2, 6.0))

    def test_latest_grenade_pair_has_cost_beyond_old_two_point_five_spacing(self):
        # One observed victim was incapacitated: still a living possible blast
        # target, although it must not become a formation support anchor.
        positions = [(34.0, 31.0, 0.5), (35.0, 35.0, 0.5)]
        count = self.count_sample(positions, (34.5, 33.0, 0.5))
        self.assertEqual(count, 2)
        self.assertGreater(self.penalty(count, 6.0), 0.0)

    def test_latest_poison_pair_and_dispersed_pair_are_distinguished(self):
        nearby = [(25.0, 15.0, 0.5), (27.0, 14.0, 0.5)]
        spread = [(25.0, 15.0, 0.5), (32.0, 15.0, 0.5)]
        self.assertEqual(self.count_sample(nearby, (26.0, 14.5, 0.5)), 2)
        self.assertEqual(self.count_sample(spread, (28.5, 15.0, 0.5)), 0)
        self.assertEqual(self.count_sample(spread, spread[0]), 1)

    def test_geometric_radius_boundary_and_disabled_radius(self):
        self.assertTrue(self.inside(3.0, 0.0, 0.0, 3.0))
        self.assertFalse(self.inside(3.01, 0.0, 0.0, 3.0))
        self.assertFalse(self.inside(0.0, 0.0, 0.0, 0.0))
        self.assertFalse(self.inside(0.0, 0.0, 0.0, -3.0))

    def test_area_search_is_observational_and_count_requires_moving_unit(self):
        count = function_body(self.source, 'CountSharedAreaTargets')
        worst = function_body(self.source, 'WorstSharedAreaTargets')
        self.assertIn('AreaRiskPointInside(', count)
        gate = count[:count.index('foreach Positions(')]
        self.assertIn('if (!AreaRiskPointInside(', gate)
        self.assertIn('return 0;', gate)
        self.assertIn('CountSharedAreaTargets(', worst)
        self.assertIn('AreaRiskLocation(', worst)
        for forbidden in ('ModifyStateObject', 'SubmitGameState', 'GetCurrentStat',
                          'GetGameRulesCache_Unit', 'ActivateAbility', 'Rand('):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, count + worst)

    def test_search_includes_between_units_centers_and_is_bounded(self):
        worst = function_body(self.source, 'WorstSharedAreaTargets')
        for required in (
            'Positions.Length >= 13',
            'RadiusTiles * 2.0',
            'Center = (Candidate + Positions[Index]) * 0.5;',
            'Center = (Positions[Index] + Positions[OtherIndex]) * 0.5;',
            'Center = (Candidate + Positions[Index] + Positions[OtherIndex]) / 3.0;',
        ):
            with self.subTest(required=required):
                self.assertIn(required, worst)

    def test_downed_survivors_count_for_blast_but_do_not_anchor_support(self):
        formation = function_body(self.source, 'SquadPositionScore')
        add = formation.index('AreaFriends.AddItem(Friend.TileLocation)')
        downed = formation.index('if (Friend.IsIncapacitated())')
        support = formation.index('NearestDistance = FMin(')
        self.assertLess(add, downed)
        self.assertLess(downed, support)
        self.assertIn('Friend.IsAlive()', formation)
        self.assertIn('AreaFriends.Length < 12', formation)
        self.assertIn('Result -= ScoreSharedAreaTargets(WorstSharedAreaTargets(', formation)
        self.assertNotIn('return false', formation)
        self.assertNotIn('return -10000', formation)
        support_distance = function_body(self.source, 'NearestSupportDistance')
        self.assertIn('Friendly.IsIncapacitated()', support_distance)


if __name__ == '__main__':
    unittest.main()
