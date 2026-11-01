"""Numerical combat scenarios running the mod's actual pure scoring helpers.

Native targeting, preview correctness, AP costs and gameplay still require the
WOTC SDK and game; this suite only guards the planner's ranking arithmetic.
"""
from pathlib import Path
import unittest
from uc_math import load_uc_function


SOURCE = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_CombatPlanner.uc'


class TacticalAttackRankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = staticmethod(load_uc_function(SOURCE, 'ScoreDamage'))
        cls.kill = staticmethod(load_uc_function(SOURCE, 'EstimatedKillChance'))
        cls.armor = staticmethod(load_uc_function(SOURCE, 'PreviewDamageAfterArmor'))
        cls.burst_kill = staticmethod(load_uc_function(SOURCE, 'BurstKillChance'))

    def test_finish_wounded_alien_before_spreading_damage(self):
        wounded = self.score(3, 5, 3, 65, 1, 0.5)
        healthy = self.score(3, 5, 6, 65, 1, 0)
        self.assertGreater(wounded, healthy)

    def test_reliable_kill_beats_speculative_high_damage(self):
        reliable = self.score(3, 5, 3, 85, 1, 0)
        speculative = self.score(6, 8, 10, 35, 1, 0)
        self.assertGreater(reliable, speculative)

    def test_overkill_does_not_inflate_ranking(self):
        pistol_finish = self.score(3, 3, 2, 100, 1, 0.5)
        cannon_finish = self.score(8, 10, 2, 100, 1, 0.5)
        self.assertAlmostEqual(pistol_finish, cannon_finish)

    def test_dangerous_target_wins_when_elimination_chances_equal(self):
        trooper = self.score(3, 5, 3, 75, 1, 0)
        dangerous = self.score(3, 5, 3, 75, 1.35, 0)
        self.assertGreater(dangerous, trooper)

    def test_low_chance_shot_leaves_room_for_useful_reposition(self):
        self.assertLess(self.score(3, 5, 6, 25, 1, 0), 20)
        self.assertGreater(self.score(3, 5, 6, 85, 1, 0), 30)

    def test_zero_damage_does_not_claim_a_kill(self):
        self.assertEqual(self.kill(0, 0, 1, 100), 0)
        self.assertLess(self.score(0, 0, 1, 100, 1, 0), -1000)

    def test_kill_probability_accounts_for_hit_and_damage_ranges(self):
        self.assertAlmostEqual(self.kill(3, 5, 3, 65), 0.65)
        self.assertAlmostEqual(self.kill(3, 5, 5, 60), 0.2)
        self.assertEqual(self.kill(3, 5, 6, 100), 0)
        self.assertAlmostEqual(self.kill(3, 5, 3, 150), 1)

    def test_armor_removes_false_guaranteed_kill(self):
        low = self.armor(3, 1, 0, 1)
        high = self.armor(5, 1, 0, 1)
        self.assertEqual((low, high), (2, 4))
        self.assertLess(self.kill(low, high, 3, 100), 1)
        self.assertEqual(self.kill(3, 5, 3, 100), 1)

    def test_armor_piercing_and_minimum_damage_follow_stock_rules(self):
        self.assertEqual(self.armor(4, 3, 2, 1), 3)
        self.assertEqual(self.armor(3, 20, 0, 1), 1)
        self.assertEqual(self.armor(0, 20, 0, 1), 0)

    def test_burst_preview_applies_armor_to_each_shot(self):
        self.assertEqual(self.armor(8, 2, 0, 2), 4)
        self.assertEqual(self.armor(8, 2, 0, 1), 6)
        self.assertEqual(self.armor(8, 2, 2, 2), 6)

    def test_rapid_fire_needing_both_hits_does_not_claim_single_roll_chance(self):
        self.assertAlmostEqual(self.burst_kill(6, 10, 6, 70, 2), 0.49)
        self.assertAlmostEqual(self.burst_kill(9, 15, 9, 70, 3), 0.343)

    def test_burst_where_each_hit_is_lethal_uses_at_least_one_hit(self):
        self.assertAlmostEqual(self.burst_kill(6, 10, 3, 70, 2), 0.91)


if __name__ == '__main__':
    unittest.main()
