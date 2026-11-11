"""Source-level and pure-policy checks for concealment-aware native routes.

SDK source tests require a private WOTC tree and never run by default in
public CI. Even with all tests passing, Windows compilation/gameplay is needed.
"""
import os
from pathlib import Path
import unittest

from test_ui_gating import function_body, CHECKS
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SOURCE = CLASSES / 'APX_ConcealmentPlanner.uc'


class ConcealmentRouteContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding='utf-8-sig')
        cls.traversal = staticmethod(load_uc_function(SOURCE,
                                                       'DestructiveTraversalBreaksConcealment'))
        cls.score = staticmethod(load_uc_function(SOURCE, 'RouteConcealmentPenalty'))
        cls.detected = staticmethod(load_uc_function(SOURCE, 'DetectedOnTile'))

    def test_challenge_exempts_destructive_movement_without_granting_general_stealth(self):
        self.assertTrue(self.traversal(False, True, True))
        for args in ((True, True, True), (False, False, True),
                     (False, True, False)):
            self.assertFalse(self.traversal(*args))
        body = function_body(self.source, 'PathRisksRevealing')
        self.assertIn("class'XComGameState_ChallengeData'", body)
        self.assertIn('DestructiveTraversalBreaksConcealment(', body)

    def test_soft_scoring_never_makes_a_native_path_illegal(self):
        self.assertEqual(self.score(False, True, False, 18), 0)
        self.assertEqual(self.score(True, False, False, 18), 0)
        self.assertEqual(self.score(True, True, True, 18), 4)
        self.assertEqual(self.score(True, True, False, 18), 18)
        self.assertEqual(self.score(True, True, False, -10), 0)
        self.assertEqual(self.score(True, True, True, 2), 2)

    def test_visible_contact_alone_does_not_make_a_concealed_approach_urgent(self):
        urgent = load_uc_function(SOURCE, 'ConcealmentIsUrgent')
        # A concealed squad may observe an unengaged pod. Seeing it does not
        # justify walking through a window or a civilian's detection zone.
        self.assertFalse(urgent(True, False, False, False, False))
        self.assertTrue(urgent(False, False, False, False, False))
        for emergency in range(4):
            reasons = [False] * 4
            reasons[emergency] = True
            with self.subTest(emergency=emergency):
                self.assertTrue(urgent(True, *reasons))
        mission = (CLASSES / 'APX_MissionPlanner.uc').read_text()
        choose = function_body(mission, 'ChooseMove')
        assignment = choose.split('bConcealmentUrgent =', 1)[1].split(';', 1)[0]
        self.assertIn('ConcealmentIsUrgent(', assignment)
        self.assertNotIn('Goal.bImmediateThreats', assignment)

    def test_inspection_budget_is_shared_across_units_and_planners(self):
        inspect = load_uc_function(SOURCE, 'ShouldInspectConcealmentPath')
        consume = load_uc_function(SOURCE, 'RemainingConcealmentBudget')
        remaining = 6
        inspected = []
        requests = [('mission_prefix', True, 5), ('mission_local', True, 5),
                    ('loot', False, 5), ('exploration', True, 1),
                    ('loot', True, 4), ('ambush', True, 4),
                    ('another_soldier', True, 4), ('another_prefix', True, 4),
                    ('another_ambush', True, 4), ('another_local', True, 4)]
        for planner, concealed, length in requests:
            if inspect(concealed, length, remaining):
                inspected.append(planner)
                remaining = consume(remaining)
        self.assertEqual(len(inspected), 6)
        self.assertEqual(remaining, 0)
        self.assertFalse(inspect(True, 4, remaining))
        self.assertEqual(consume(0), 0)
        self.assertEqual(consume(-2), 0)

    def test_exhausted_budget_does_not_call_the_native_inspector(self):
        wrapper = function_body(self.source, 'InspectPathRisk')
        native_call = wrapper.index('PathRisksRevealing(')
        budget_gate = wrapper[:native_call]
        self.assertIn('decision_budget', budget_gate)
        self.assertIn('return true;', budget_gate)
        self.assertIn('ShouldInspectConcealmentPath(', budget_gate)
        self.assertIn('RemainingConcealmentBudget(', budget_gate)
        self.assertNotIn('CanSeeTileToTile(', budget_gate)
        for name in ('APX_MissionPlanner.uc', 'APX_ExplorationPlanner.uc',
                     'APX_SquadPlanner.uc'):
            source = (CLASSES / name).read_text()
            self.assertIn('InspectPathRisk(', source)
            self.assertNotIn('.static.PathRisksRevealing(', source)

    def test_one_decision_owns_and_propagates_the_inspection_budget(self):
        controller = (CLASSES / 'APX_Controller.uc').read_text()
        decision = function_body(controller, 'MakeDecision')
        initialization = 'RemainingConcealmentChecks = 6;'
        self.assertEqual(decision.count(initialization), 1)
        self.assertLess(decision.index(initialization),
                        decision.index('foreach `XCOMHISTORY.IterateByClassType('))
        for call in ("class'APX_MissionPlanner'.static.ChooseMove(",
                     "class'APX_MissionPlanner'.static.ChooseLootMove(",
                     'ExplorationPlanner.ChooseMove(',
                     "class'APX_SquadPlanner'.static.ChoosePreparation("):
            statement = decision.split(call, 1)[1].split(';', 1)[0]
            with self.subTest(call=call):
                self.assertIn('RemainingConcealmentChecks', statement)

    def test_uncertain_paths_do_not_receive_a_cheaper_uninspected_subsidy(self):
        for name, function in (('APX_MissionPlanner.uc', 'ChooseMove'),
                               ('APX_ExplorationPlanner.uc', 'BuildSafeBluePrefix')):
            body = function_body((CLASSES / name).read_text(), function)
            self.assertNotIn('FMin(8.0', body)
            self.assertNotIn('ConcealmentChecks <= 6', body)
            self.assertIn('InspectPathRisk(', body)
            self.assertIn('RouteConcealmentPenalty(', body)
        self.assertEqual(self.score(True, True, False, 18), 18)
        self.assertEqual(self.score(True, True, False, -3), 0)

    def test_local_fallback_prevents_a_stealth_penalty_from_removing_all_progress(self):
        # Without an A* prefix, a legal local approach used to pass a +4
        # improvement threshold. The finite -18 stealth penalty must not turn
        # the only +10 approach into "No constructive action" / global OFF.
        self.assertGreater(10.0, 4.0)
        self.assertLess(10.0 - self.score(True, True, False, 18), 4.0)
        mission = (CLASSES / 'APX_MissionPlanner.uc').read_text()
        choose = function_body(mission, 'ChooseMove')
        saved = choose.index('LocalFallbackPath = CandidatePath;')
        self.assertLess(choose.index('if (bSafe)'), saved)
        self.assertLess(choose.index('IsUsefulReposition('), saved)
        self.assertLess(choose.index('IsBerserkerObjectiveRiskAllowed('), saved)
        self.assertLess(choose.index('for (PathIndex = 1;'), saved)
        self.assertLess(saved, choose.index('CandidateScore -=', saved))
        restored = choose.index('Path = LocalFallbackPath;')
        self.assertLess(restored, choose.index('if (Path.Length < 2)\n        return false;'))
        self.assertIn('MoveOpportunityPenalty(', choose[restored:])
        self.assertIn('ScoreCombatReposition(', choose[restored:])

    def test_native_detector_geometry_obeys_sight_and_detection_radius(self):
        self.assertFalse(self.detected(False, 9, 10, 5, True))
        self.assertFalse(self.detected(True, 101, 10, 5, True))
        self.assertFalse(self.detected(True, 26, 10, 5, False))
        self.assertTrue(self.detected(True, 25, 10, 5, False))
        self.assertTrue(self.detected(True, 80, 10, 5, True))

    def test_native_los_work_has_a_separate_finite_budget(self):
        path = function_body(self.source, 'PathRisksRevealing')
        detect = function_body(self.source, 'IsDetectingUnit')
        self.assertIn('Clamp(default.MaxNativeLOSChecksPerInspection, 1, 512)', path)
        self.assertEqual(path.count('Reason = "native_los_budget";'), 2)
        self.assertIn('Visibility, NativeLOSRemaining)', path)
        distance_cull = detect.index('VSizeSq(TilePosition - DetectorPosition)')
        budget_gate = detect.index('if (NativeLOSRemaining <= 0)')
        consume = detect.index('--NativeLOSRemaining;')
        native_los = detect.index('CanSeeTileToTile(')
        self.assertLess(distance_cull, budget_gate)
        self.assertLess(budget_gate, consume)
        self.assertLess(consume, native_los)
        wrapper = function_body(self.source, 'InspectPathRisk')
        self.assertLess(wrapper.index('Reason = "decision_budget";'),
                        wrapper.index('Concealment inspection|unit='))
        self.assertLess(wrapper.index('PathRisksRevealing('),
                        wrapper.index('Concealment inspection|unit='))

    def test_safe_read_only_path_and_source_bounded(self):
        body = function_body(self.source, 'PathRisksRevealing')
        for token in ('Soldier.IsConcealed()', 'Path.Length < 2',
                      'MaxPathTilesToInspect', 'MaxDetectorsToInspect',
                      'GetPathPointsFromPath(', 'GetAllVisibleObjectsForPlayer(',
                      'GetKnownEnemies(Soldier, KnownEnemies)',
                      'CanIgnoreInteractiveDetectors(Soldier)',
                      'bHasBeenHacked', 'IsDetectingUnit(',
                      'VisibleObjects.Length > Limit',
                      'KnownEnemies.Length > Limit',
                      'path_sample_limit', 'detector_sample_limit'):
            with self.subTest(token=token):
                self.assertIn(token, body)
        for mutation in ('ModifyStateObject', 'SubmitGameState',
                         'CreateNewGameState', 'BreakConcealment(',
                         'PerformEndTurn(', 'ActivateAbility(', 'Rand('):
            self.assertNotIn(mutation, self.source)

    def test_civilians_and_interactives_are_discriminated(self):
        body = function_body(self.source, 'PathRisksRevealing')
        self.assertIn('Detector.IsCivilian()', body)
        self.assertIn('interactive_detector', body)
        self.assertIn('known_enemy', body)
        suppress = function_body(self.source, 'CanIgnoreInteractiveDetectors')
        self.assertIn('AbilityRetainsConcealmentVsInteractives', suppress)
        self.assertIn('Soldier.HasSoldierAbility(', suppress)
        unit = function_body(self.source, 'IsDetectingUnit')
        self.assertIn('Soldier.UnitBreaksConcealment(Detector)', unit)
        self.assertLess(unit.index('VSizeSq(TilePosition - DetectorPosition)'),
                        unit.index('CanSeeTileToTile('))
        self.assertIn('Detector.GetVisibilityRadius()', unit)
        self.assertIn('Soldier.GetConcealmentDetectionDistance(Detector)', unit)
        self.assertIn('DoesUnitBreaksConcealmentIgnoringDistance()', unit)

    def test_planner_integrations_preserve_native_paths_and_urgent_objectives(self):
        squad=(CLASSES/'APX_SquadPlanner.uc').read_text()
        mission=(CLASSES/'APX_MissionPlanner.uc').read_text()
        explore=(CLASSES/'APX_ExplorationPlanner.uc').read_text()
        s=function_body(squad,'PreparationPathIsSafe')
        m=function_body(mission,'ChooseMove')
        e=function_body(explore,'BuildSafeBluePrefix')
        self.assertIn('InspectPathRisk(',s)
        self.assertNotIn('foreach VisibleObjects(',s)
        self.assertNotIn('CanSeeTileToTile(',s)
        self.assertIn("!class'APX_FullIntel'.default.EnableFullIntel",s)
        for t in ('bConcealmentUrgent', 'Goal.bBerserkerSabotageGoal',
                  'HasActiveMissionDeadline()', 'HasBleedingSquadmate(UnitState)',
                  'RiskyRoute = Path', 'Path = RiskyRoute',
                  'ChooseRoutePrefix(', 'BuildPathToTile(',
                  'HasBlockingHazard(', 'InspectPathRisk('):
            with self.subTest(token=t):
                self.assertIn(t,m)
        for t in ('InspectPathRisk(',
                  'BuildPathToTile(', 'HasBlockingHazard('):
            self.assertIn(t,e)
        # Keep the new AoE-formation feature added by LEAD in v22.
        formation=function_body(mission,'SquadPositionScore')
        self.assertIn('SquadAreaRiskRadiusTiles',formation)

    def test_config_budgets_are_bounded(self):
        ini=(ROOT/'AutoplayXCom2/Config/XComAutoplayXCom2.ini').read_text()
        self.assertIn('[AutoplayXCom2.APX_ConcealmentPlanner]',ini)
        self.assertIn('MaxPathTilesToInspect=48',ini)
        self.assertIn('MaxDetectorsToInspect=96',ini)
        self.assertIn('MaxNativeLOSChecksPerInspection=128',ini)
        self.assertIn('ConcealmentRiskPenalty=18.0',ini)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'Private WOTC SDK source needed for native concealment contracts')
class ConcealmentRouteSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk=CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT']))/'XComGame/Classes'

    def test_unit_concealment_and_challenge_exception(self):
        unit=(self.sdk/'XComGameState_Unit.uc').read_text(encoding='utf-8-sig')
        for token in ('IsConcealed() const', 'UnitBreaksConcealment(',
                      'GetConcealmentDetectionDistance(', 'XComGameState_ChallengeData',
                      'AbilityRetainsConcealmentVsInteractives'):
            self.assertIn(token,unit)

    def test_path_and_geometry_contracts(self):
        path=(self.sdk/'X2PathSolver.uc').read_text(encoding='utf-8-sig')
        self.assertIn('GetPathPointsFromPath(XComGameState_Unit Unit,',path)
        visibility=(self.sdk/'X2TacticalVisibilityHelpers.uc').read_text(encoding='utf-8-sig')
        self.assertIn('GetAllVisibleObjectsForPlayer(int PlayerStateObjectID',visibility)


if __name__ == '__main__':
    unittest.main()
