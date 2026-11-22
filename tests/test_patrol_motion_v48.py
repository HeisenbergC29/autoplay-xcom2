"""Validate the selected patrol's stored movement against the native registry and history."""

import os
from pathlib import Path
import unittest

from test_ui_gating import function_body
from uc_math import load_uc_function


CLASSES = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
PATROL = CLASSES / 'APX_PatrolKnowledge.uc'
CONTACT = CLASSES / 'APX_ContactEnvelope.uc'


class PatrolMotionTests(unittest.TestCase):
    """Exercise actual UC tile comparison and the native-object contracts around it."""

    def test_displacement_requires_both_observed_endpoints_and_net_movement(self):
        """A partial, reversed, hypothetical or stationary route supplies no completed segment."""
        matches = load_uc_function(PATROL, 'MatchesDisplacement')
        start, middle, end = (0, 0, 0), (2, 2, 0), (4, 1, 1)
        self.assertTrue(matches(start, end, start, end))
        for actual, path_start, path_end in (
            (middle, start, end), (end, middle, end), (end, end, start),
            (start, start, end), (start, start, start),
        ):
            with self.subTest(actual=actual, path_start=path_start, path_end=path_end):
                self.assertFalse(matches(start, actual, path_start, path_end))

    def test_missing_data_is_distinct_from_observed_zero_displacement(self):
        """Classify a missing cache or invalid tile before comparing the valid observed tiles."""
        body = function_body(PATROL.read_text(), 'LeaderMotionEvidence')
        tokens = ('Patrol == none || Leader == none || `XWORLD == none',
                  'IsTileOutOfRange(Leader.TurnStartLocation)', 'IsTileOutOfRange(Leader.TileLocation)',
                  'return "patrol_motion_unobserved"', 'Leader.TurnStartLocation == Leader.TileLocation',
                  'return "patrol_no_net_displacement"', 'PathLength >= 2 && MatchesDisplacement(',
                  'Patrol.m_arrGroupPath[0], Patrol.m_arrGroupPath[PathLength - 1]',
                  'return "completed_leader_segment"')
        offsets = [body.index(token) for token in tokens]
        self.assertEqual(offsets, sorted(offsets))
        self.assertTrue(body.rstrip().endswith('return "patrol_motion_unobserved";'))

    def test_only_one_bounded_owner_registry_entry_can_certify_the_history_roster(self):
        """Reject stale/missing owner, leader, oversized or mismatched rosters, and ambiguity."""
        source = PATROL.read_text()
        roster = function_body(source, 'MatchesPatrolRoster')
        for token in ('Patrol == none || Group == none', 'Group.m_arrMembers.Length < 1',
                      'Group.m_arrMembers.Length > 24', 'Patrol.m_arrUnitIDs.Length != Group.m_arrMembers.Length',
                      'Patrol.m_arrUnitIDs[Index] <= 0', 'Patrol.m_arrUnitIDs[Index] != Group.m_arrMembers[Index].ObjectID'):
            self.assertIn(token, roster)
        registry = function_body(source, 'RegisteredLeaderPatrol')
        for token in ('Group.m_arrMembers[0].ObjectID != Leader.ObjectID', 'Leader.GroupMembershipID != Group.ObjectID',
                      'Leader.ControllingPlayer.ObjectID != Owner.ObjectID', 'AIActor.ObjectID != Owner.ObjectID',
                      'AIActor.m_kNav == none', 'AIActor.m_kNav.m_kPlayer != AIActor',
                      'AIActor.m_kNav.m_arrPatrolGroups.Length > 48', 'foreach AIActor.m_kNav.m_arrPatrolGroups(Patrol)',
                      'Patrol.m_kPlayer != AIActor', 'Patrol.m_arrUnitIDs[0] != Leader.ObjectID',
                      'Match != none || !MatchesPatrolRoster(Patrol, Group)', 'return Match;'):
            self.assertIn(token, registry)
        for mutating in ('RefreshGameState(', 'GetGroupInfo(', 'RefreshGroups(', 'UpdatePatrolGroup(', 'BuildPathToTile('):
            self.assertNotIn(mutating, source)

    def test_selection_requires_fresh_waypoint_and_movement_even_with_a_listed_group(self):
        """Check selection through the source entry point and distinct diagnostics for skipped groups."""
        evidence = function_body(PATROL.read_text(), 'StoredPatrolEvidence')
        for token in ("!class'APX_FullIntel'.default.EnableFullIntel", 'AIData.m_iPlayerObjectID == AIPlayer.ObjectID',
                      "AIData.PatrolGroupList.Find('ObjectID', Group.ObjectID)", 'RegisteredLeaderPatrol(Group, Leader, AIPlayer)',
                      'if (!bListed && Patrol == none)', 'Motion = LeaderMotionEvidence(Patrol, Leader);',
                      'StoredWaypointAge(AIData.StatsData.TurnCount,', 'GetCurrentPatrolWaypoint(', 'patrol_waypoint_reached'):
            self.assertIn(token, evidence)
        self.assertLess(evidence.index('if (Motion != "completed_leader_segment")'),
                        evidence.index('Reason = bListed ? "stored_list_completed_segment" : "navigator_completed_segment"'))
        snapshot = function_body(CONTACT.read_text(), 'BuildSnapshot')
        for reason, counter in (('patrol_no_net_displacement', 'AtTurnStart'), ('patrol_motion_unobserved', 'UnobservedMotion')):
            self.assertRegex(snapshot, rf'if \(PatrolReason == "{reason}"\)\s*\{{\s*\+\+{counter};\s*continue;')
        self.assertIn('PatrolDistanceSq < BestPatrolDistanceSq', snapshot)
        self.assertIn('"verified_stored_patrol source=" $ SelectedEvidence', snapshot)
        self.assertIn('"at_turn_start_tile=" $ AtTurnStart', snapshot)

    @unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'private WOTC SDK unavailable')
    def test_sdk_registration_ownership_segment_and_turn_origin(self):
        """Check SDK writers for the data read by the mod, including the registry's use of living members."""
        sdk = Path(os.environ['APX_SDK_SOURCE_ROOT']) / 'XComGame/Classes'
        navigator = (sdk / 'XGAIPlayerNavigator.uc').read_text(encoding='utf-8-sig')
        refresh = function_body(navigator, 'RefreshGroups')
        self.assertIn('kGroup.GetLivingMembers(arrObjIDs)', refresh)
        self.assertIn('UpdatePatrolGroup(arrObjIDs', refresh)
        self.assertIn('m_arrPatrolGroups.AddItem(kGroup)', navigator)
        group = (sdk / 'XGAIGroup.uc').read_text(encoding='utf-8-sig')
        self.assertIn('m_arrUnitIDs = arrObjIDs;', group)
        self.assertIn('History.GetVisualizer(LeadUnit.ControllingPlayer.ObjectID)', group)
        actor = (sdk / 'XGAIPatrolGroup.uc').read_text(encoding='utf-8-sig')
        self.assertIn('m_arrGroupPath.Length = 0;', function_body(actor, 'InitTurn'))
        self.assertIn('InputData.MovementTiles = m_arrGroupPath;', actor)
        unit = (sdk / 'XComGameState_Unit.uc').read_text(encoding='utf-8-sig')
        self.assertIn('TurnStartLocation = TileLocation;', function_body(unit, 'SetupActionsForBeginTurn'))
        data = (sdk / 'XComGameState_AIPlayerData.uc').read_text(encoding='utf-8-sig')
        rebuild = function_body(data, 'UpdateGroupData')
        self.assertIn('PatrolGroupList.Length = 0;', rebuild)
        self.assertNotIn('PatrolGroupList.AddItem', rebuild)
