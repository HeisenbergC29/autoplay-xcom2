"""Defensive ranking scenarios execute the actual scalar UnrealScript helpers.

Native availability, cover validity, reserve AP and reaction shots still require
the stock SDK compiler/game; these tests guard comparisons rather than simulate AI.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function


SOURCE = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_CombatPlanner.uc'


class TacticalDefenseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overwatch = staticmethod(load_uc_function(SOURCE, 'ScoreOverwatchDefense'))
        cls.hunker = staticmethod(load_uc_function(SOURCE, 'ScoreHunkerDefense'))
        cls.aid = staticmethod(load_uc_function(SOURCE, 'ScoreAidDefense'))
        cls.shot = staticmethod(load_uc_function(SOURCE, 'ScoreDamage'))

    def test_out_of_contact_overwatch_does_not_preempt_advancing(self):
        self.assertEqual(self.overwatch(False, False, 1, 0, 0), 2)
        self.assertLess(self.overwatch(False, True, 1, 0, 0), 9)

    def test_low_probability_shot_can_lose_to_overwatch(self):
        poor_shot = self.shot(3, 5, 6, 25, 1, 0)
        self.assertGreater(self.overwatch(True, False, 1, 4.2, 0), poor_shot)

    def test_healthy_full_cover_prefers_reaction_over_hunker(self):
        self.assertGreater(self.overwatch(True, False, 1, 4.2, 0),
                           self.hunker(1, 4.2, 1, 0, False, False))

    def test_wounded_exposed_soldier_prefers_hunker_over_bad_shot(self):
        defensive = self.hunker(0.25, 42, 1, 0, False, False)
        self.assertGreater(defensive, self.shot(3, 5, 6, 35, 1, 0))
        self.assertGreater(defensive, self.overwatch(True, False, 0.25, 42, 0))

    def test_reliable_kill_still_beats_nonemergency_hunker(self):
        reliable_kill = self.shot(3, 5, 3, 85, 1, 0)
        self.assertGreater(reliable_kill, self.hunker(0.25, 42, 1, 0, False, False))

    def test_hunker_does_not_pretend_to_stop_melee(self):
        self.assertEqual(self.hunker(0.25, 0, 0, 1, False, False), 1)
        self.assertLess(self.hunker(0.25, 42, 1, 1, False, False),
                        self.hunker(0.25, 42, 1, 0, False, False))
        self.assertGreater(self.overwatch(True, False, 1, 0, 1),
                           self.overwatch(True, False, 1, 0, 0))

    def test_hunker_extinguishes_fire_even_without_contact(self):
        self.assertEqual(self.hunker(0.5, 0, 0, 0, True, False), 130)
        self.assertGreater(self.hunker(0.5, 0, 0, 0, True, False),
                           self.shot(3, 5, 6, 85, 1, 0))

    def test_concealed_soldier_preserves_reaction_option(self):
        self.assertEqual(self.hunker(1, 42, 1, 0, False, True), 1)
        self.assertGreater(self.overwatch(True, True, 1, 4.2, 0),
                           self.overwatch(True, False, 1, 4.2, 0))

    def test_aid_protocol_is_saved_without_meaningful_ranged_risk(self):
        self.assertLess(self.aid(1, 0, 0), -1000)
        self.assertLess(self.aid(1, 4.2, 1), -1000)
        self.assertGreater(self.aid(0.25, 42, 1), self.aid(1, 42, 1))


if __name__ == '__main__':
    unittest.main()
