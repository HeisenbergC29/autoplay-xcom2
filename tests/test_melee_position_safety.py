"""Moving attacks share normal combat-movement safety constraints.

Numeric scenarios execute the real support policy. Source contracts cover the
native path checks, which still require validation in the Windows game.
"""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function


CLASSES = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
MOVEMENT = CLASSES / 'APX_MissionPlanner.uc'
COMBAT = CLASSES / 'APX_CombatPlanner.uc'


class MeleePositionSafetyTests(unittest.TestCase):
    def test_legacy_melee_cannot_leave_the_existing_support_envelope(self):
        destination = load_uc_function(MOVEMENT, 'IsSupportedAdvanceDestination')
        step = load_uc_function(MOVEMENT, 'IsSupportedAdvanceStep')
        # D3: Central starts at (19,14), supported by (20,14). The native
        # sword destination (23,28) is closest to the ally at (25,18).
        start_distance = 1.0
        end_distance = (2 ** 2 + 10 ** 2) ** 0.5
        self.assertFalse(destination(start_distance, end_distance))
        self.assertFalse(step(start_distance, end_distance))
        # The existing policy still admits a supported strike and a move that
        # closes a pre-existing large gap; there is no blanket melee ban.
        self.assertTrue(destination(start_distance, 8.0))
        self.assertTrue(destination(14.0, end_distance))
        self.assertTrue(step(14.0, end_distance))

    def test_moving_melee_checks_the_same_destination_and_route_as_combat_movement(self):
        melee = function_body(COMBAT.read_text(encoding='utf-8-sig'), 'HasRequiredMeleePath')
        move = function_body(MOVEMENT.read_text(encoding='utf-8-sig'), 'ChooseMove')
        for guard in ('IsKnownCombatTile(', 'IsSupportedCombatDestination(',
                      'IsSupportedAdvanceDestination(', 'IsSupportedAdvanceStep(',
                      'CanSquadSeeLocation(', 'TileContainsHazard('):
            with self.subTest(guard=guard):
                self.assertIn(guard, melee)
                self.assertIn(guard, move)
        # Check the actual native attack destination, rather than the target's
        # occupied tile or an independently selected movement destination.
        self.assertIn('SelectAttackTile(', melee)
        self.assertIn('IsSupportedCombatDestination(SourceUnit, Destinations[0])', melee)
        self.assertIn('BuildPathToTile(Destinations[0], Path)', melee)
        self.assertIn('IsKnownCombatTile(Path[Index])', melee)
        self.assertIn('SourceUnit.ControllingPlayer.ObjectID, Path[Index])', melee)
        self.assertIn('NearestSupportDistance(SourceUnit, Path[Index])', melee)
        self.assertLess(melee.index('for (Index = 1;'), melee.index('TileContainsHazard('))
        self.assertLess(melee.index('IsSupportedCombatDestination('), melee.index('BuildPathToTile('))

    def test_stationary_melee_and_existing_evacuation_support_exception_remain(self):
        melee = function_body(COMBAT.read_text(encoding='utf-8-sig'), 'HasRequiredMeleePath')
        self.assertIn('if (Destinations[0] == SourceUnit.TileLocation)\n        return true;', melee)
        self.assertLess(melee.index('if (Destinations[0] == SourceUnit.TileLocation)'),
                        melee.index('IsSupportedCombatDestination('))
        self.assertIn('bRequireSupport = !class\'APX_MissionPlanner\'.static.ShouldEvacuate(SourceUnit);', melee)


if __name__ == '__main__':
    unittest.main()
