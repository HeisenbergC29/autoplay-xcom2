"""Pair-area proposals execute the real scalar geometry helper.

Floor snapping, trajectory and actual affected objects remain native checks.
"""
import math
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function


SOURCE = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_AreaAttackPlanner.uc'


class GrenadePairGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.offset_squared = staticmethod(load_uc_function(SOURCE, 'PairAimOffsetSquared'))

    def test_offset_can_preserve_two_targets_and_avoid_a_protected_midpoint(self):
        # Enemies(0,0)/(4,0), blast radius3 and existing safety buffer1.
        # Friendly(2,-3) blocks the midpoint, but the upper lens point can
        # include both enemies while staying outside the friendly buffer.
        radius = 3.0
        offset = math.sqrt(self.offset_squared(4, 0, radius))
        self.assertLess(3.0, radius + 1)
        self.assertLess(math.hypot(2, offset), radius)
        self.assertGreater(offset + 3, radius + 1)
        self.assertLess(abs(3 - offset), radius + 1)

    def test_two_symmetric_offsets_leave_room_for_floor_snapping(self):
        offset = math.sqrt(self.offset_squared(4, 0, 3))
        self.assertGreater(offset, 0)
        self.assertLess(offset, math.sqrt(3 ** 2 - 2 ** 2))
        self.assertLess(math.hypot(2, offset), 3)
        self.assertEqual(math.hypot(2, offset), math.hypot(2, -offset))

    def test_radius_and_height_limit_the_pair_lens(self):
        self.assertEqual(self.offset_squared(7, 0, 3), -1)
        self.assertEqual(self.offset_squared(6, 0, 3), -1)
        self.assertEqual(self.offset_squared(4, 5, 3), -1)
        self.assertGreater(self.offset_squared(4, 2, 3), 0)
        self.assertLess(self.offset_squared(4, 2, 3), self.offset_squared(4, 0, 3))

    def test_degenerate_pairs_and_invalid_radius_do_not_divide_by_zero(self):
        self.assertEqual(self.offset_squared(0, 0, 3), -1)
        self.assertEqual(self.offset_squared(-1, 0, 3), -1)
        self.assertEqual(self.offset_squared(4, 0, 0), -1)

    def test_world_units_scale_squared_geometry_consistently(self):
        tiles = self.offset_squared(4, 2, 3)
        world = self.offset_squared(4 * 96, 2 * 96, 3 * 96)
        self.assertAlmostEqual(world, tiles * 96 ** 2)

    def test_new_pool_uses_existing_budget_floor_and_authoritative_native_checks(self):
        source = SOURCE.read_text()
        build = function_body(source, 'BuildCandidateCenters')
        self.assertIn('AddCenter(Midpoint + Perpendicular, PairOffsetCenters)', build)
        self.assertIn('AddCenter(Midpoint - Perpendicular, PairOffsetCenters)', build)
        for pool in ('DirectCenters', 'EdgeCenters', 'MidpointCenters', 'PairOffsetCenters'):
            self.assertIn(f'AddCenter({pool}[Index], Centers)', build)
        self.assertIn('Index < Budget && Centers.Length < Budget', build)
        self.assertIn('GetFloorPositionForTile(', function_body(source, 'AddCenter'))
        evaluate = function_body(source, 'EvaluateImpact')
        self.assertLess(evaluate.index('BlastIsSafe('), evaluate.index('ScoreBlast('))
        self.assertIn('GatherAdditionalAbilityTargetsForLocation(', evaluate)


if __name__ == '__main__':
    unittest.main()
