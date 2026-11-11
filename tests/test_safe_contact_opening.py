"""Focused contact-opening safety regression tests.

The pure helpers are extracted from the actual UnrealScript files. No
Windows compiler or in-game result is implied by these checks.
"""
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
MISSION = CLASSES / 'APX_MissionPlanner.uc'
SQUAD = CLASSES / 'APX_SquadPlanner.uc'
CONTROLLER = CLASSES / 'APX_Controller.uc'


class SafeContactOpeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mission = MISSION.read_text(encoding='utf-8-sig')
        cls.squad = SQUAD.read_text(encoding='utf-8-sig')
        cls.controller = CONTROLLER.read_text(encoding='utf-8-sig')
        cls.risk = staticmethod(load_uc_function(MISSION, 'RoutineRouteExposureAllowed'))
        cls.opening_penalty = staticmethod(load_uc_function(SQUAD, 'OpeningSupportPenalty'))

    def test_route_delta_from_v23_rejected_when_not_urgent(self):
        # Real logged D9 SabotageCC route: risk 59.2117 -> 109.9195.
        self.assertFalse(self.risk(59.2117, 109.9195, False))
        self.assertTrue(self.risk(59.2117, 65.0, False))
        self.assertTrue(self.risk(59.2117, 109.9195, True))
        self.assertTrue(self.risk(0.0, 12.0, False))
        self.assertFalse(self.risk(0.0, 12.01, False))

    def test_opening_penalty_for_isolated_uncovered_shooter(self):
        self.assertEqual(self.opening_penalty(0, True, False, True), 46.0)
        self.assertEqual(self.opening_penalty(0, True, False, False), 36.0)
        self.assertEqual(self.opening_penalty(1, True, False, False), 18.0)
        self.assertEqual(self.opening_penalty(2, True, False, False), 0.0)
        self.assertEqual(self.opening_penalty(5, True, False, True), 10.0)
        self.assertEqual(self.opening_penalty(0, False, False, True), 0.0)
        self.assertEqual(self.opening_penalty(0, True, True, True), 0.0)

    def test_route_guards_reuse_threat_samples_and_fallback_local(self):
        choose = function_body(self.mission, 'ChooseMove')
        self.assertIn('RoutineRouteExposureAllowed(CurrentRisk, CandidateRisk,', choose)
        self.assertIn('Path.Length = 0;', choose)
        self.assertEqual(choose.count('GetThreatWeights(UnitState, VisibleEnemies, ThreatWeights);'), 1)
        self.assertEqual(choose.count('GetMeleeThreatReaches(UnitState, VisibleEnemies, MeleeThreatReaches);'), 1)
        self.assertIn('GetMeleeThreatReaches(UnitState, VisibleEnemies, MeleeThreatReaches);', choose)
        self.assertIn('GetThreatWeights(UnitState, VisibleEnemies, ThreatWeights);', choose)
        self.assertIn('ShouldEvacuate(UnitState) || HasBleedingSquadmate(UnitState)', choose)
        self.assertIn('HasActiveMissionDeadline()', choose)
        self.assertIn('BuildPathToTile(Tile, CandidatePath)', choose)
        self.assertIn('HasBlockingHazard(UnitState, CandidatePath[PathIndex])', choose)
        self.assertIn('IsSupportedAdvanceStep(', choose)

    def test_support_lanes_are_native_bounded_current_geometry(self):
        support = function_body(self.squad, 'CountRangedOpeningSupport')
        for expected in ('IsLocalSoldier(Friend,', 'Friend.IsAbleToAct()',
                         'NumAllReserveActionPoints()', 'CanSeeTileToTile(',
                         'GetVisibilityRadius()', 'FindOverwatch(',
                         'if (Count >= 2)'):
            self.assertIn(expected, support)
        opener = function_body(self.squad, 'UnsupportedOpeningPenaltyForAction')
        self.assertIn('SquadIsConcealed(', opener)
        self.assertIn('HasActiveMissionDeadline()', opener)
        self.assertIn("Ability.OwnerStateObject.ObjectID != Opener.ObjectID", opener)
        self.assertIn("AbilityName != 'StandardShot'", opener)
        self.assertIn("AbilityName != 'SniperStandardFire'", opener)
        self.assertIn('GetCoverTypeForTarget(', opener)
        self.assertIn('OpeningSupportPenalty(', opener)

    def test_legal_attack_scoring_competes_with_real_moves(self):
        decision = function_body(self.controller, 'MakeDecision')
        self.assertIn('UnsupportedOpeningPenaltyForAction(', decision)
        self.assertLess(decision.index('UnsupportedOpeningPenaltyForAction('),
                        decision.index('TraceCandidateAction(UnitState, "combat"'))
        self.assertIn('CanUseAction(UnitState, Candidate, TargetIndex)', decision)
        self.assertIn('class\'APX_MissionPlanner\'.static.ChooseMove(', decision)
        self.assertIn('CanUseMove(UnitState, CandidatePath)', decision)
        self.assertIn('ChoosePreparation(PlayerRef.ObjectID, BestUnit,', decision)
        self.assertIn('if (CoordinateConcealedAmbush && bHavePlan', decision)

    def test_available_action_belongs_to_real_source_unit(self):
        guard = function_body(self.controller, 'CanUseAction')
        for expected in ("Action.AvailableCode != 'AA_Success'",
                         'Action.AbilityObjectRef.ObjectID',
                         'Ability.OwnerStateObject.ObjectID != UnitState.ObjectID',
                         'TargetIndex < 0 || TargetIndex >= Action.AvailableTargets.Length'):
            self.assertIn(expected, guard)
        self.assertIn('MaxSameActionPerTurn', guard)
        self.assertNotIn('CreateNewGameState(', guard)
        self.assertNotIn('SubmitGameState(', guard)


if __name__ == '__main__':
    unittest.main()
