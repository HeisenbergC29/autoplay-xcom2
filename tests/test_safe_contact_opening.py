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
        cls.soft_penalty = staticmethod(load_uc_function(MISSION, 'ApplyConstructiveSoftPenalty'))
        cls.route_score = staticmethod(load_uc_function(MISSION, 'ScoreRouteAdvance'))
        cls.reaction_ready = staticmethod(load_uc_function(SQUAD, 'OpeningReactionReserveReady'))
        cls.concealment_penalty = staticmethod(load_uc_function(
            CLASSES / 'APX_ConcealmentPlanner.uc', 'RouteConcealmentPenalty'))

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

    def test_retained_legal_route_survives_soft_costs_without_no_plan_stop(self):
        route = self.route_score(0, -8)
        self.assertEqual(route, 19.0)
        for concealed, previous_result in ((True, -3.0), (False, 1.0)):
            with self.subTest(concealed=concealed):
                stealth = self.concealment_penalty(concealed, True, True, 18)
                self.assertEqual(route - stealth - 18.0, previous_result)
                self.assertEqual(self.soft_penalty(route, stealth + 18.0), 3.0)
        choose = function_body(self.mission, 'ChooseMove')
        retained = choose.split('Path = RiskyRoute;', 1)[1].split('return true;', 1)[0]
        self.assertIn('ApplyConstructiveSoftPenalty(RiskyRouteScore,', retained)
        self.assertIn('UnitState.IsConcealed(), true, true,', retained)
        self.assertNotIn('true, true, true,', retained)
        self.assertIn('BestScore <= 2.0', function_body(self.controller, 'MakeDecision'))

    def test_sole_legal_opening_shot_is_not_lost_to_the_soft_penalty(self):
        # A 35-point legal shot with no ready support in open cover previously
        # became -11 and could trip the controller's global NoPlan/OFF gate.
        penalty = self.opening_penalty(0, True, False, True)
        self.assertEqual(35 - penalty, -11)
        self.assertEqual(self.soft_penalty(35, penalty), 3)
        self.assertLessEqual(self.soft_penalty(2, penalty), 2)
        decision = function_body(self.controller, 'MakeDecision')
        opening = decision.index('UnsupportedOpeningPenaltyForAction(')
        self.assertIn('ApplyConstructiveSoftPenalty(Score,', decision[:opening])
        self.assertLess(opening, decision.index('TraceCandidateAction(UnitState, "combat"'))

    def test_soft_penalty_does_not_rehabilitate_nonconstructive_moves_or_boost_scores(self):
        for base in (-20.0, 0.0, 1.0, 2.0):
            self.assertEqual(self.soft_penalty(base, 18), base - 18)
        for base in (2.1, 2.5, 3.0, 19.0, 45.0):
            for cost in (0.0, 4.0, 22.0, 42.0):
                with self.subTest(base=base, cost=cost):
                    result = self.soft_penalty(base, cost)
                    self.assertGreater(result, 2.0)
                    self.assertLessEqual(result, base)
        self.assertEqual(self.soft_penalty(19, -10), 19)

    def test_accepted_prefix_exposure_cost_keeps_constructive_progress(self):
        # The relative risk allowance grows with current exposure, so its
        # soft cost can exceed the entire route score without a bounded floor.
        self.assertTrue(self.risk(1000, 1250, False))
        self.assertEqual(self.soft_penalty(19, (1250 - 1000) * 0.6), 3.0)
        choose = function_body(self.mission, 'ChooseMove')
        exposure = choose.index('FMax(0.0, CandidateRisk - CurrentRisk) * 0.6')
        self.assertIn('ApplyConstructiveSoftPenalty(Score,', choose[:exposure])
        self.assertLess(exposure, choose.index('RiskyRouteScore = Score;'))
        rejected = choose.split('if (!RoutineRouteExposureAllowed(', 1)[1].split('else', 1)[0]
        self.assertIn('Path.Length = 0;', rejected)
        self.assertNotIn('RiskyRoute = Path;', rejected)

    def test_local_fallback_preserves_opportunity_and_hard_guards(self):
        combat_score = load_uc_function(MISSION, 'ScoreCombatReposition')
        opportunity = load_uc_function(MISSION, 'MoveOpportunityPenalty')
        base = combat_score(20, 14, 14, 1.0, 2) - opportunity(70, 0, 1.0, 0)
        self.assertLessEqual(base, 2.0)
        self.assertLessEqual(self.soft_penalty(base, 22), 2.0)
        choose = function_body(self.mission, 'ChooseMove')
        restore = choose.index('Path = LocalFallbackPath;')
        soft_cost = choose.index('Score = ApplyConstructiveSoftPenalty(Score,', restore)
        self.assertLess(choose.index('Score -= MoveOpportunityPenalty(', restore), soft_cost)
        save = choose.index('LocalFallbackPath = CandidatePath;')
        for guard in ('IsUsefulReposition(', 'IsBerserkerObjectiveRiskAllowed(',
                      'for (PathIndex = 1;', 'if (bSafe)'):
            self.assertLess(choose.index(guard), save)

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
                         'HasReadyOpeningOverwatch(Friend)', 'CanSeeTileToTile(',
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

    def test_unrelated_or_unaffordable_reserves_do_not_count_as_overwatch(self):
        # Suppression, KillZone and Interrupt reserves leave both ordinary
        # and pistol overwatch counts at zero, even with installed shot skills.
        self.assertFalse(self.reaction_ready(0, 0, True, True))
        self.assertFalse(self.reaction_ready(1, 0, False, True))
        self.assertFalse(self.reaction_ready(0, 1, True, False))
        self.assertTrue(self.reaction_ready(1, 0, True, False))
        self.assertTrue(self.reaction_ready(0, 1, False, True))
        self.assertFalse(self.reaction_ready(2, 2, False, False))
        ready = function_body(self.squad, 'HasReadyOpeningOverwatch')
        for expected in ('NumReserveActionPoints(',
                         "class'X2CharacterTemplateManager'.default.OverwatchReserveActionPoint",
                         "class'X2CharacterTemplateManager'.default.PistolOverwatchReserveActionPoint",
                         "HasAffordableOpeningReaction(Soldier, 'OverwatchShot')",
                         "HasAffordableOpeningReaction(Soldier, 'LongWatchShot')",
                         "HasAffordableOpeningReaction(Soldier, 'PistolOverwatchShot')"):
            self.assertIn(expected, ready)
        self.assertNotIn('NumAllReserveActionPoints()', ready)
        self.assertNotIn('NumAllReserveActionPoints()',
                         function_body(self.squad, 'CountRangedOpeningSupport'))
        reaction = function_body(self.squad, 'HasAffordableOpeningReaction')
        self.assertIn('Ability.OwnerStateObject.ObjectID == Soldier.ObjectID', reaction)
        self.assertIn("CanAfford(Ability, Soldier) == 'AA_Success'", reaction)
        self.assertNotIn('CanActivateAbility(', reaction)

    def test_opening_policy_does_not_read_enemy_group_alert_or_private_knowledge(self):
        for source in (self.mission, self.squad, self.controller):
            for forbidden in ('SecondaryGroupEngagementPenalty', 'IsSecondaryGroupOpening',
                              'XComGameState_AIGroup', 'IsEngaged(', 'HasAbsoluteKnowledge('):
                with self.subTest(forbidden=forbidden):
                    self.assertNotIn(forbidden, source)

    def test_cover_inspections_share_one_decision_budget_across_units(self):
        decision = function_body(self.controller, 'MakeDecision')
        self.assertEqual(decision.count('RemainingCoverChecks = 6;'), 1)
        self.assertLess(decision.index('RemainingCoverChecks = 6;'),
                        decision.index('foreach `XCOMHISTORY.IterateByClassType('))
        call = decision.split("class'APX_MissionPlanner'.static.ChooseMove(", 1)[1].split(';', 1)[0]
        self.assertIn('RemainingConcealmentChecks,\n                RemainingCoverChecks)', call)
        choose = function_body(self.mission, 'ChooseMove')
        self.assertEqual(choose.count('.static.InspectRiskAtTile('), 2)
        for call in choose.split('.static.InspectRiskAtTile(')[1:]:
            self.assertIn('VisibleEnemies, RemainingCoverChecks)', call.split(';', 1)[0])
        self.assertNotIn('.static.RiskAtTile(', choose)
        self.assertNotIn('++CoverChecks', choose)
        self.assertNotIn('RemainingCoverChecks =', choose)
        self.assertNotIn('CoverRisk = 8.0', choose)
        self.assertIn('optional out int RemainingConcealmentChecks,\n'
                      '    optional out int RemainingCoverChecks)', self.mission)

    def test_local_fallback_records_cover_risk_before_either_soft_penalty(self):
        choose = function_body(self.mission, 'ChooseMove')
        save = choose.index('LocalFallbackPath = CandidatePath;')
        cover = choose.index('LocalFallbackCoverRisk = CoverRisk;', save)
        stealth = choose.index('CandidateScore -= class\'APX_ConcealmentPlanner\'', save)
        self.assertLess(save, cover)
        self.assertLess(cover, stealth)
        self.assertLess(cover, choose.index('CandidateScore -= CoverRisk;', save))

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
        # Free native actions remain legal with zero standard AP. Ownership
        # must not be implemented as an extra AP gate in this final guard.
        self.assertNotIn('NumActionPoints(', guard)
        self.assertNotIn('ActionPoints.Length', guard)


if __name__ == '__main__':
    unittest.main()
