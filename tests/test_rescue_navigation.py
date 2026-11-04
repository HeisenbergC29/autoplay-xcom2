"""Rescue navigation policy and its integration with legal native actions."""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function


CLASSES = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
MOVEMENT = CLASSES / 'APX_MissionPlanner.uc'


class RescueNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = staticmethod(load_uc_function(MOVEMENT, 'ScoreRescueApproach'))

    def test_reaching_treatment_range_has_priority_over_ordinary_moves(self):
        # The reported medic had AP2 about five tiles from the bleeding ally.
        # Completing an approach is valuable even with a modest risk increase.
        self.assertGreater(self.score(True, 4, 40, 50, 1, 2), 200)
        self.assertLess(self.score(True, 4, 40, 50, 1, 2), 400)
        self.assertGreater(self.score(True, 4, 40, 50, 1, 1),
                           self.score(False, 4, 40, 50, 1, 2))

    def test_partial_approach_needs_progress_and_time_to_finish(self):
        self.assertLess(self.score(False, 1, 10, 10, 1, 3), 0)
        self.assertLess(self.score(False, 4, 10, 10, 1, 1), 0)
        self.assertGreater(self.score(False, 4, 10, 10, 1, 3), 100)

    def test_approach_does_not_ignore_danger_to_the_rescuer(self):
        safe = self.score(True, 4, 10, 10, 1, 2)
        dangerous = self.score(True, 4, 10, 150, 0.3, 2)
        self.assertGreater(safe, dangerous)
        self.assertLess(dangerous, 60)

    def test_route_preserves_treatment_resources_and_uses_real_patient_state(self):
        rescue = function_body(MOVEMENT.read_text(), 'ChooseRescueMove')
        for contract in ('GetReadyStabilizeAbility(UnitState, Patient)',
                         'ActionPointsAfterBlueMove(UnitState, RemainingPoints)',
                         'CanAttackWithActionPoints(Stabilize, UnitState, RemainingPoints)',
                         'GetBleedingOutTurnsRemaining()', 'CanStabilizeFromTile(',
                         'GetAllPathableTiles(', 'BuildPathToTile(',
                         'HasBlockingHazard(', 'IsKnownCombatTile(', 'CanSquadSeeLocation('):
            self.assertIn(contract, rescue)
        self.assertIn('Clamp(default.MaxCandidateTiles, 1, 96)', rescue)
        for forbidden in ('ModifyStateObject(', 'ApplyCost(', 'SetCurrentStat(', 'ActivateAbility_'):
            self.assertNotIn(forbidden, rescue)

    def test_every_squad_member_is_considered_for_rescue_and_loot(self):
        controller = (CLASSES / 'APX_Controller.uc').read_text()
        decision = function_body(controller, 'MakeDecision')
        start = decision.index("foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit'")
        opening = decision.index('{', start)
        depth, closing = 1, opening + 1
        while depth:
            depth += (decision[closing] == '{') - (decision[closing] == '}')
            closing += 1
        for helper in ('ChooseRescueMove(', 'ChooseLootMove(', 'ChooseLootInteraction('):
            self.assertGreater(decision.index(helper), opening)
            self.assertLess(decision.index(helper), closing)
        self.assertIn('rescue_candidate', decision)
        self.assertIn('loot_candidate', decision)


if __name__ == '__main__':
    unittest.main()
