"""Execute the planner's pure UnrealScript policy helpers on scouting scenarios.

These checks cover AP reservation and formation policy; they do not execute the
native pathfinder, fog-of-war queries, or an XCOM mission.
"""

from pathlib import Path
import unittest

from uc_math import load_uc_function


SOURCE = (Path(__file__).resolve().parents[1] /
          "AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_ExplorationPlanner.uc")


MOVEMENT_SOURCE = SOURCE.with_name("APX_MissionPlanner.uc")


class ExplorationPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.can_spend = staticmethod(load_uc_function(SOURCE, "CanSpendExplorationAP"))
        cls.step_allowed = staticmethod(load_uc_function(MOVEMENT_SOURCE, "IsSupportedAdvanceStep"))
        cls.destination_allowed = staticmethod(load_uc_function(
            MOVEMENT_SOURCE, "IsSupportedAdvanceDestination"))
        cls.score = staticmethod(load_uc_function(SOURCE, "ScoreExplorationMove"))

    def test_scout_reserves_an_action_to_answer_a_revealed_patrol(self):
        self.assertFalse(self.can_spend(0, False))
        self.assertFalse(self.can_spend(1, False))
        self.assertTrue(self.can_spend(2, False))
        self.assertTrue(self.can_spend(3, False))

    def test_visible_combat_blocks_exploration_even_with_extra_actions(self):
        for actions in (1, 2, 3, 8):
            with self.subTest(actions=actions):
                self.assertFalse(self.can_spend(actions, True))

    def test_formation_bound_checks_route_as_well_as_endpoint(self):
        self.assertTrue(self.destination_allowed(4.0, 8.0))
        # An endpoint near the squad cannot legitimize a route that first
        # wanders far beyond support around a wall.
        self.assertTrue(self.step_allowed(4.0, 10.0))
        self.assertFalse(self.step_allowed(4.0, 11.0))

    def test_separated_soldier_can_regroup_without_extending_separation(self):
        self.assertTrue(self.step_allowed(16.0, 15.0))
        self.assertFalse(self.step_allowed(16.0, 17.0))
        self.assertTrue(self.destination_allowed(16.0, 14.0))
        self.assertFalse(self.destination_allowed(16.0, 16.0))
        self.assertFalse(self.destination_allowed(16.0, 15.75))

    def test_catching_up_acts_before_front_soldier_stretches_formation(self):
        regroup = self.score(-20.0, -4.0)
        hold_formation = self.score(0.0, 0.0)
        stretch = self.score(0.0, -10.0)
        self.assertGreater(regroup, hold_formation)
        self.assertGreater(hold_formation, stretch)

    def test_exploration_priority_stays_between_idle_and_mission_route(self):
        for old, new in ((-1000, 0), (0, -1000), (0, 0), (-8, -5)):
            with self.subTest(old=old, new=new):
                score = self.score(old, new)
                self.assertGreater(score, 2.0)
                self.assertLess(score, 25.0)


if __name__ == "__main__":
    unittest.main()
