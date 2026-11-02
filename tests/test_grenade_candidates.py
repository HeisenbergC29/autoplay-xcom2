"""Range-edge proposals use native throw range without enlarging it.

The scalar geometry helpers are executed from the actual UnrealScript bodies;
native floor snapping, trajectory and blast protection remain engine checks.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body


SOURCE = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_AreaAttackPlanner.uc'


class GrenadeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.edge = staticmethod(load_uc_function(SOURCE, 'EdgeAimDistance'))
        cls.priority = staticmethod(load_uc_function(SOURCE, 'RejectionPriority'))

    def test_enemy_beyond_throw_range_can_be_inside_legal_blast(self):
        aim = self.edge(12, 10, 3, 0.25)
        self.assertLess(aim, 10)
        self.assertLessEqual(12 - aim, 3)
        self.assertGreater(aim, 0)

    def test_target_beyond_range_plus_blast_cannot_generate_edge(self):
        self.assertEqual(self.edge(14, 10, 3, 0.25), -1)
        self.assertEqual(self.edge(10, 10, 0, 0.25), -1)
        self.assertEqual(self.edge(10, -1, 3, 0.25), -1)

    def test_candidate_geometry_has_no_tiles_world_units_conversion_error(self):
        tiles = self.edge(12, 10, 3, 0.25)
        world = self.edge(12 * 96, 10 * 96, 3 * 96, 0.25 * 96)
        self.assertAlmostEqual(world, tiles * 96)

    def test_grid_margin_produces_two_interior_candidates(self):
        close_to_boundary = self.edge(12, 10, 3, 0.25)
        further_inside = self.edge(12, 10, 3, 0.75)
        self.assertLess(further_inside, close_to_boundary)
        self.assertLessEqual(12 - further_inside, 3)

    def test_rejection_priority_preserves_blaster_safety_reason_after_range(self):
        self.assertGreater(self.priority('blast'), self.priority('range'))
        self.assertGreater(self.priority('targets'), self.priority('trajectory'))
        self.assertGreater(self.priority('score'), self.priority('blast'))

    def test_candidate_budget_is_shared_between_direct_edge_and_pair_centers(self):
        body = function_body(SOURCE.read_text(), 'BuildCandidateCenters')
        self.assertIn('Budget = Clamp(MaxCandidateCenters, 1, 64);', body)
        self.assertIn('Index < Budget && Centers.Length < Budget', body)
        for pool in ('DirectCenters', 'EdgeCenters', 'MidpointCenters'):
            self.assertIn(f'AddCenter({pool}[Index], Centers);', body)
        choose = function_body(SOURCE.read_text(), 'ChooseAction')
        self.assertLess(choose.index('GetSupportedGrenade('), choose.index('BuildCandidateCenters('))
        self.assertLess(choose.index('BuildCandidateCenters('), choose.index('foreach Centers(Center)'))

    def test_range_and_actual_landing_protection_remain_authoritative(self):
        source = SOURCE.read_text()
        legal = function_body(source, 'IsLegalLocation')
        self.assertIn('Ability.GetValidWeaponRange(MinRange, MaxRange);', legal)
        self.assertIn('Distance >= MaxRange', legal)
        impact = function_body(source, 'ComputeImpact')
        self.assertIn('PathActor.CalculateTrajectoryToTarget(', impact)
        self.assertIn('Impact = PathActor.GetEndPosition();', impact)
        evaluate = function_body(source, 'EvaluateImpact')
        self.assertLess(evaluate.index('BlastIsSafe('), evaluate.index('ScoreBlast('))

    def test_diagnostic_reasons_are_kept_separate_from_last_candidate(self):
        source = SOURCE.read_text()
        reject = function_body(source, 'RejectScan')
        self.assertIn('RejectionPriority(Stage) >= DeepestRejection', reject)
        self.assertIn('ScanRangeReason = Reason;', reject)
        self.assertIn('ScanBlastReason = Reason;', reject)
        summary = function_body(source, 'GetDiagnosticSummary')
        for field in ('blast_reason=', 'range_reason=', 'max_range_units=', 'nearest_aim_units='):
            self.assertIn(field, summary)


if __name__ == '__main__':
    unittest.main()
