"""Native plant geometry and phase contracts; not a Windows compiler/game test."""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
KNOWLEDGE = CLASSES / 'APX_PlantInteractionKnowledge.uc'
MISSION = CLASSES / 'APX_MissionPlanner.uc'


class NativePlantGoalContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = KNOWLEDGE.read_text()
        cls.mission = MISSION.read_text()
        cls.finite = staticmethod(load_uc_function(KNOWLEDGE, 'FiniteCoordinate'))
        cls.used = staticmethod(load_uc_function(KNOWLEDGE, 'HasConsumedPlantInteraction'))
        cls.eligible = staticmethod(load_uc_function(KNOWLEDGE, 'PlantObjectStateEligible'))
        cls.anchor = staticmethod(load_uc_function(KNOWLEDGE, 'InteractionAnchorCoordinate'))
        cls.probe_z = staticmethod(load_uc_function(KNOWLEDGE, 'PlantQueryProbeZ'))

    def test_finite_geometry_accepts_origin_but_not_nan_or_infinity(self):
        for value in (0, -100, 100):
            self.assertTrue(self.finite(value))
        for value in (float('nan'), float('inf'), -float('inf'), 1e30):
            self.assertFalse(self.finite(value))

    def test_unused_or_preset_disabled_object_is_not_evidence_of_a_plant(self):
        self.assertFalse(self.used(0, 0, 0))
        self.assertFalse(self.used(1, 1, 1))
        self.assertFalse(self.used(1, 0, 2))
        self.assertFalse(self.used(1, 0, -1))
        self.assertTrue(self.used(1, 0, 1))
        self.assertTrue(self.used(2, 1, 2))

    def test_only_usable_object_state_is_a_geometry_candidate(self):
        self.assertTrue(self.eligible(True, False, False, False, 0, 1))
        self.assertTrue(self.eligible(True, False, False, False, 3, -1))
        for arguments in ((False, False, False, False, 0, 1),
                          (True, True, False, False, 0, 1),
                          (True, False, True, False, 0, 1),
                          (True, False, False, True, 0, 1),
                          (True, False, False, False, 0, 0),
                          (True, False, False, False, 1, 1)):
            with self.subTest(arguments=arguments):
                self.assertFalse(self.eligible(*arguments))

    def test_large_unit_anchor_is_reverse_of_actual_occupied_offset(self):
        current = (10, 20, 1)
        point = (30, 40, 1)
        offsets = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0))
        anchors = set()
        for offset in offsets:
            occupied = tuple(a + b for a, b in zip(current, offset))
            candidate = tuple(self.anchor(p, o, c) for p, o, c in zip(point, occupied, current))
            anchors.add(candidate)
            self.assertIn(point, {tuple(a + b for a, b in zip(candidate, d)) for d in offsets})
        self.assertEqual(anchors, {(30, 40, 1), (29, 40, 1), (30, 39, 1), (29, 39, 1)})
        find = function_body(self.source, 'FindInteractionGoalResult')
        self.assertIn('InteractionAnchorCoordinate(QueryTile.X, OccupiedTile.X, UnitState.TileLocation.X)', find)
        self.assertIn('UnitState.GetVisibilityForLocation(Candidate, FutureFootprint)', find)
        self.assertIn('ContainsTile(FutureFootprint, QueryTile)', find)

    def test_three_tile_footprint_preserves_every_possible_occupied_offset(self):
        # A larger footprint is not limited to the four 2x2 Berserker cases.
        current = (10, 20, 1)
        point = (30, 40, 1)
        offsets = {(x, y, 0) for x in range(3) for y in range(3)}
        anchors = set()
        for offset in offsets:
            occupied = tuple(c + d for c, d in zip(current, offset))
            candidate = tuple(self.anchor(p, o, c) for p, o, c in zip(point, occupied, current))
            anchors.add(candidate)
            self.assertIn(point, {tuple(c + d for c, d in zip(candidate, cell)) for cell in offsets})
        self.assertEqual(len(anchors), 9)
        self.assertIn((28, 38, 1), anchors)

    def test_hidden_interactors_require_full_intel_before_visualizer_discovery(self):
        find = function_body(self.source, 'FindInteractionGoalResult')
        gate = find.index("if (!class'APX_FullIntel'.default.EnableFullIntel")
        query = find.index('CanXComSquadSeeTarget(ObjectState.ObjectID)', gate)
        self.assertLess(gate, query)
        self.assertLess(query, find.index('ObjectState.GetVisualizer()'))

    def test_vertical_anchor_uses_native_verified_query_level_not_socket_level(self):
        # A socket 64 world units above a query center can satisfy stock's
        # 90-unit height. Model the native-confirmed query at Z1, socket at Z2.
        # The native call, not this numerical fixture, decides actual legality.
        point_tile_z = 2
        verified_query_z = 1
        self.assertEqual([self.probe_z(point_tile_z, index) for index in range(5)],
                         [2, 1, 3, 0, 4])
        self.assertIn(verified_query_z,
                      [self.probe_z(point_tile_z, index) for index in range(5)])
        current_anchor_z = occupied_z = 1
        self.assertEqual(self.anchor(verified_query_z, occupied_z, current_anchor_z), 1)
        self.assertEqual(self.anchor(point_tile_z, occupied_z, current_anchor_z), 2)
        find = function_body(self.source, 'FindInteractionGoalResult')
        proof = find.index('NativePlantPointOnTile(ObjectState, Visualizer, QueryTile, RemainingQueries)')
        anchor = find.index('Candidate.Z = InteractionAnchorCoordinate(QueryTile.Z,')
        self.assertLess(proof, anchor)
        self.assertIn('ContainsTile(FutureFootprint, QueryTile)', find)
        self.assertIn('Probe < 5 && RemainingQueries > 0 && AnchorsChecked < 64', find)

    def test_cached_point_needs_live_native_actor_and_point_location_bounds(self):
        point = function_body(self.source, 'NativePlantPointOnTile')
        self.assertIn('GetPositionFromTileCoordinates(QueryTile)', point)
        self.assertIn('GetInteractionPoints(Position, 8.0, 90.0, Points)', point)
        self.assertIn('Point.InteractiveActor == Visualizer', point)
        self.assertIn('ObjectState.IsLocationValidForInteraction(Point.Location)', point)
        self.assertNotIn('IsLocationValidForInteraction(Position)', point)
        find = function_body(self.source, 'FindInteractionGoalResult')
        self.assertIn("Visualizer.InteractionAbilityTemplateName != 'Interact_PlantBomb'", find)
        self.assertIn('Visualizer.ObjectID != ObjectState.ObjectID', find)
        self.assertIn('ObjectState.CanInteractNormally(UnitState)', find)
        self.assertIn('Ability.OwnerStateObject.ObjectID != UnitState.ObjectID', find)
        self.assertLess(find.index('NativePlantPointOnTile('), find.index('Candidates.AddItem(Candidate)'))
        for forbidden in ('ModifyStateObject(', 'CreateNewGameState(', 'SubmitGameState(',
                          'ActivateAbility(', 'CompleteObjective(', 'SetRemainingTurns('):
            self.assertNotIn(forbidden, self.source)
        self.assertIsNone(re.search(r'UnitState\.TileLocation\s*=', self.source))

    def test_inspection_and_native_query_caps_are_before_expensive_operations(self):
        find = function_body(self.source, 'FindInteractionGoalResult')
        self.assertLess(find.index('++ObjectsChecked > 128'), find.index('ObjectState.GetVisualizer()'))
        self.assertLess(find.index('++PointsChecked > 32'), find.index('Point.Location.X'))
        self.assertIn('RemainingQueries = 32;', find)
        self.assertIn('AnchorsChecked < 64', find)
        self.assertLess(find.index('++AnchorsChecked'), find.index('GetVisibilityForLocation(Candidate'))
        self.assertIn('while (PathChecks < 4', find)
        self.assertLess(find.index('++PathChecks'), find.index("class'X2PathSolver'.static.BuildPath"))
        self.assertIn('FullPath[FullPath.Length - 1] == Candidate', find)
        point = function_body(self.source, 'NativePlantPointOnTile')
        self.assertLess(point.index('--RemainingQueries'), point.index('GetInteractionPoints('))
        self.assertLess(point.index('Points.Length > 32'), point.index('foreach Points('))

    def test_exact_native_phase_not_marker_distance_controls_plant_and_sweep(self):
        phase = function_body(self.source, 'NativePlantObjectivePhase')
        self.assertIn('MapData.ActiveMission.sType != "SabotageTransmitter"', phase)
        self.assertIn("ObjectiveName == 'PlantBomb'", phase)
        self.assertIn('.bCompleted ? 1 : 0', phase)
        self.assertIn('Min(64,', phase)
        self.assertIn('return -1;', phase)
        goal = function_body(self.mission, 'FindGoal')
        self.assertIn('PlantObjectivePhase == 1', goal)
        self.assertIn('bCompletedStrategyObjective = PlantObjectivePhase == 1;', goal)
        self.assertNotIn('TileDistance(UnitState.TileLocation, SabotageGoalTile) > 1.5', goal)
        sweep = goal.split('if (bBerserkerSweep)', 1)[1].split("IterateByClassType(class'XComGameState_InteractiveObject'", 1)[0]
        self.assertIn('foreach VisibleEnemies(EnemyRef)', sweep)
        self.assertIn('return Goal.bFound;', sweep)

    def test_consumed_object_suppresses_marker_but_does_not_invent_completion(self):
        goal = function_body(self.mission, 'FindGoal')
        consumed = goal.split('if (SabotageGoalSource == "plant_interaction_already_used")', 1)[1].split('}', 1)[0]
        self.assertIn('bSkipUnverifiedPlantMarker = true;', consumed)
        self.assertNotIn('bBerserkerSweep = true;', consumed)
        self.assertIn('if (!Goal.bFound && !bSkipUnverifiedPlantMarker)', goal)

    def test_unverified_marker_never_replaces_native_point_or_consumed_object(self):
        find = function_body(self.mission, 'FindBerserkerSabotageGoal')
        self.assertIn("class'APX_PlantInteractionKnowledge'.static.FindInteractionGoal", find)
        self.assertLess(find.index('if (NativeGoalStatus > 0)'), find.index('MapData.ObjectiveLocation'))
        self.assertLess(find.index('if (NativeGoalStatus < 0)'), find.index('MapData.ObjectiveLocation'))
        self.assertIn('GoalSource = "mission_marker_unverified:" $ NativeGoalReason;', find)
        self.assertNotIn('GetRequiresObjectiveGlint()', find)

    def test_compiler_boundary_keeps_custom_result_inside_knowledge_class(self):
        # Regression from the native make error: adding the knowledge class to
        # MissionPlanner.DependsOn made SDK dependency validation abort before
        # function analysis. Use stock/scalar outputs, as ChoosePreparation does.
        header = self.mission.split(';', 1)[0]
        self.assertNotIn('APX_PlantInteractionKnowledge', header)
        self.assertNotIn('PlantGoalResult', self.mission)
        self.assertIn('static function int FindInteractionGoal(XComGameState_Unit UnitState,\n'
                      '    out TTile GoalTile, out string GoalReason)', self.source)
        api = function_body(self.source, 'FindInteractionGoal')
        self.assertIn('FindInteractionGoalResult(UnitState, Result);', api)
        self.assertIn('GoalTile = Result.Tile;', api)
        self.assertIn('GoalReason = Result.Reason;', api)
        self.assertRegex(api, r'if \(Result.bFound\)\s+return 1;')
        self.assertRegex(api, r'if \(Result.bConsumedObject\)\s+return -1;')
        self.assertLess(api.index('if (Result.bFound)'), api.index('if (Result.bConsumedObject)'))
        self.assertTrue(api.rstrip().endswith('return 0;'))


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Private SDK contract')
class NativePlantSDKContracts(unittest.TestCase):
    def test_future_geometry_matches_stock_interaction_condition(self):
        root = Path(os.environ['APX_SDK_SOURCE_ROOT']) / 'XComGame/Classes'
        unit = (root / 'XComGameState_Unit.uc').read_text()
        world = (root / 'XComWorldData.uc').read_text()
        actor = (root / 'XComInteractiveLevelActor.uc').read_text()
        condition = (root / 'X2Condition_UnitInteractions.uc').read_text()
        interactive = (root / 'XComGameState_InteractiveObject.uc').read_text()
        self.assertIn('GetVisibilityForLocation(const out TTile FromLocation, out array<TTile> VisibilityTiles) const', unit)
        self.assertIn('out array<XComInteractPoint> InteractPoints)', world)
        self.assertIn('var transient init array<XComInteractPoint> InteractPoints;', actor)
        self.assertIn('World.GetInteractionPoints(UnitLocation, 8.0f, 90.0f, InteractionPoints)', condition)
        self.assertIn('IsInteractionLocationRestrictedByObject(InteractionPoints[Index].Location', condition)
        self.assertIn('ObjectState.CanInteractNormally(Unit)', condition)
        self.assertIn('( InteractionBoundingBox.IsValid == 0 ) || IsPointInBox(TestLocation, InteractionBoundingBox)', interactive)
