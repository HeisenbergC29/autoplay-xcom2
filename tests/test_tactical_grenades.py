"""Rank grenade scenarios with the actual UC numeric scoring functions."""
from pathlib import Path
import unittest

from uc_math import load_uc_function


CLASSES = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'


class TacticalGrenadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grenade = staticmethod(load_uc_function(CLASSES / 'APX_AreaAttackPlanner.uc', 'ScoreGrenadeOutcome'))
        cls.damage = staticmethod(load_uc_function(CLASSES / 'APX_CombatPlanner.uc', 'ScoreDamage'))

    def test_single_guaranteed_kill_is_allowed(self):
        damage = self.damage(3, 4, 3, 100, 1, 0)
        self.assertGreater(self.grenade(1, 1, 2, damage), 0)

    def test_single_damage_only_target_preserves_limited_grenade(self):
        damage = self.damage(3, 4, 6, 100, 1, 0)
        self.assertLess(self.grenade(1, 0, 2, damage), -1000)
        self.assertLess(self.grenade(0, 0, 1, 0), -1000)

    def test_equivalent_rifle_kill_saves_grenade(self):
        damage = self.damage(3, 4, 3, 100, 1, 0)
        self.assertGreater(damage, self.grenade(1, 1, 2, damage))

    def test_grenade_kill_beats_unreliable_rifle_shot(self):
        grenade = self.grenade(1, 1, 2, self.damage(3, 4, 3, 100, 1, 0))
        rifle = self.damage(3, 5, 3, 35, 1, 0)
        self.assertGreater(grenade, rifle)

    def test_group_damage_is_worth_more_than_single_target(self):
        damage = self.damage(3, 4, 6, 100, 1, 0)
        self.assertGreater(self.grenade(2, 0, 2, damage * 2), damage)


if __name__ == '__main__':
    unittest.main()
