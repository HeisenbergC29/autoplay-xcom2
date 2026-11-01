"""Scenario regressions executing numeric helpers from the real movement planner.

These validate policy ordering and AP conservation, not engine LOS or pathfinding.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function


SOURCE = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionPlanner.uc'


class TacticalMovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.risk = staticmethod(load_uc_function(SOURCE, 'DirectionalRisk'))
        cls.combine = staticmethod(load_uc_function(SOURCE, 'CombinedExposure'))
        cls.reposition = staticmethod(load_uc_function(SOURCE, 'IsUsefulReposition'))
        cls.route_score = staticmethod(load_uc_function(SOURCE, 'ScoreRouteAdvance'))
        cls.support_step = staticmethod(load_uc_function(SOURCE, 'IsSupportedAdvanceStep'))
        cls.support_destination = staticmethod(load_uc_function(SOURCE, 'IsSupportedAdvanceDestination'))
        cls.firing_value = staticmethod(load_uc_function(SOURCE, 'FiringPositionValue'))
        cls.known_threat = staticmethod(load_uc_function(SOURCE, 'KnownThreatRisk'))
        cls.advance_endpoint = staticmethod(load_uc_function(SOURCE, 'AdvanceEndpointScore'))

    def exposure(self, cover_levels, health=1.0):
        risks = [self.risk(cover, 9.0, True, False) for cover in cover_levels]
        return self.combine(sum(risks), max(risks, default=0), health)

    def test_high_cover_beats_half_cover_and_open_ground(self):
        self.assertLess(self.exposure([2]), self.exposure([1]))
        self.assertLess(self.exposure([1]), self.exposure([0]))

    def test_other_cover_directions_do_not_cancel_open_flank(self):
        self.assertGreater(self.exposure([2, 2, 0]), self.exposure([0]))
        self.assertGreater(self.exposure([2, 2, 0]), self.exposure([1, 1, 1]))

    def test_retreat_matters_more_for_wounded_soldier(self):
        healthy_gain = self.exposure([0]) - self.exposure([2])
        wounded_gain = self.exposure([0], 0.25) - self.exposure([2], 0.25)
        self.assertGreater(wounded_gain, healthy_gain)
        self.assertEqual(self.combine(0, 0, 0.25), 0)

    def test_cover_does_not_protect_against_nearby_melee(self):
        self.assertEqual(self.risk(0, 3, True, True), self.risk(2, 3, True, True))
        self.assertGreater(self.risk(2, 3, True, True), self.risk(2, 9, True, True))
        self.assertEqual(self.risk(2, 20, True, True), 0)

    def test_coverless_units_do_not_chase_cover_bonus(self):
        self.assertEqual(self.risk(0, 9, False, False), self.risk(2, 9, False, False))

    def test_final_action_allows_escape_but_not_speculative_flank(self):
        self.assertTrue(self.reposition(20, 42, 14, 1, 4))
        self.assertFalse(self.reposition(14, 14, 14, 1, 4))
        self.assertTrue(self.reposition(14, 14, 14, 2, 4))

    def test_large_flank_bonus_cannot_justify_open_ground(self):
        self.assertFalse(self.reposition(25, 4.2, 42, 2, 4))
        self.assertFalse(self.reposition(3, 42, 4.2, 2, 4))
        self.assertTrue(self.reposition(5, 4.2, 4.2, 2, 4))

    def test_mission_route_prefers_laggard_catching_up_over_front_scout(self):
        catching_up = self.route_score(-20, -4)
        front_scout = self.route_score(0, -8)
        self.assertGreater(catching_up, front_scout)
        self.assertGreater(front_scout, 2)

    def test_mission_marker_does_not_allow_unsupported_route_or_destination(self):
        self.assertFalse(self.support_step(5, 11))
        self.assertFalse(self.support_destination(5, 11))
        self.assertTrue(self.support_step(5, 9))
        self.assertTrue(self.support_destination(5, 9))

    def test_straggler_route_must_regroup_instead_of_extending_gap(self):
        self.assertTrue(self.support_step(15, 14))
        self.assertFalse(self.support_step(15, 16))
        self.assertTrue(self.support_destination(15, 14))
        self.assertFalse(self.support_destination(15, 15))

    def test_wall_blocks_speculative_flank_and_height_reward(self):
        blocked_flank = self.firing_value(9, 9, False, True, True)
        clear_shot = self.firing_value(9, 9, True, False, False)
        self.assertLess(blocked_flank, clear_shot)
        self.assertEqual(blocked_flank, self.firing_value(9, 9, False, False, False))

    def test_clear_flank_is_better_than_equally_distant_covered_target(self):
        self.assertGreater(self.firing_value(9, 9, True, True, False),
                           self.firing_value(9, 9, True, False, False))

    def test_obstructed_ranged_threat_retains_movement_risk_but_less_than_clear_shot(self):
        self.assertGreater(self.known_threat(30, False, False), 0)
        self.assertLess(self.known_threat(30, False, False), self.known_threat(30, True, False))
        self.assertEqual(self.known_threat(30, False, True), self.known_threat(30, True, True))

    def test_advance_prefers_nearby_cover_without_abandoning_progress(self):
        self.assertGreater(self.advance_endpoint(5, 2), self.advance_endpoint(7, 0))
        self.assertLess(self.advance_endpoint(2, 2), self.advance_endpoint(7, 0))


if __name__ == '__main__':
    unittest.main()
