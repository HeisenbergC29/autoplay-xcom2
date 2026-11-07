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

    def test_native_detector_geometry_obeys_sight_and_detection_radius(self):
        self.assertFalse(self.detected(False, 9, 10, 5, True))
        self.assertFalse(self.detected(True, 101, 10, 5, True))
        self.assertFalse(self.detected(True, 26, 10, 5, False))
        self.assertTrue(self.detected(True, 25, 10, 5, False))
        self.assertTrue(self.detected(True, 80, 10, 5, True))

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
        self.assertIn('PathRisksRevealing(',s)
        self.assertIn('XComGameState_ChallengeData',s)
        self.assertIn('bIgnoreInteractiveDetectors',s)
        self.assertIn("!class'APX_FullIntel'.default.EnableFullIntel",s)
        for t in ('bConcealmentUrgent', 'Goal.bBerserkerSabotageGoal',
                  'HasActiveMissionDeadline()', 'HasBleedingSquadmate(UnitState)',
                  'RiskyRoute = Path', 'Path = RiskyRoute',
                  'ChooseRoutePrefix(', 'BuildPathToTile(',
                  'HasBlockingHazard(', 'ConcealmentChecks <= 6'):
            with self.subTest(token=t):
                self.assertIn(t,m)
        for t in ('PathRisksRevealing(', 'ConcealmentChecks <= 6',
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
