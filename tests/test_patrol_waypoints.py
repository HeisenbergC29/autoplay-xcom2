"""Stock patrol waypoint knowledge: current targets, not future RNG.

All source checks are read-only. A Windows SDK build and a real WOTC A/B
are required before using these waypoints for staging a firefight.
"""
from pathlib import Path
import unittest
from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT=Path(__file__).resolve().parents[1]
CLASSES=ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SOURCE=CLASSES/'APX_PatrolKnowledge.uc'
RECORDER=CLASSES/'APX_MissionRecorder.uc'


class PatrolKnowledgeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SOURCE.read_text(encoding='utf-8-sig')
        cls.recorder=RECORDER.read_text(encoding='utf-8-sig')
        cls.policy=staticmethod(load_uc_function(
            SOURCE,'IsReadOnlyPatrolCandidate'))
        cls.near=staticmethod(load_uc_function(
            SOURCE,'IsNearCurrentWaypoint'))

    def test_only_unengaged_active_patrols_are_candidates(self):
        self.assertTrue(self.policy(False,False,False,False,3))
        for args in (
            (True,False,False,False,3),
            (False,True,False,False,3),
            (False,False,True,False,3),
            (False,False,False,True,3),
            (False,False,False,False,0)
        ):
            with self.subTest(args=args):
                self.assertFalse(self.policy(*args))

    def test_native_waypoint_is_current_bounded_valid_tile(self):
        body=function_body(self.source,'GetCurrentPatrolWaypoint')
        for token in ('Group.IsEngaged()', 'Group.bPendingScamper',
                      'Group.bObjective', 'Group.bInterceptObjectiveLocation',
                      'Group.m_arrMembers.Length',
                      'Group.CurrentTargetLocation',
                      'GetTileCoordinatesFromPosition(Target)',
                      'IsTileOutOfRange(Waypoint)'):
            self.assertIn(token,body)
        self.assertNotIn('SYNC_RAND',self.source)
        self.assertNotIn('GetNextDestination(',self.source)
        self.assertNotIn('ModifyStateObject(',self.source)
        self.assertNotIn('SubmitGameState(',self.source)

    def test_waypoint_nearness_is_not_a_claim_of_precise_future_path(self):
        # No fixed random patrol route is inferred: only relative geometry.
        body=function_body(self.source,'IsNearCurrentWaypoint')
        self.assertIn('Abs(Current.X - Destination.X)',body)
        self.assertIn('Abs(Current.Y - Destination.Y)',body)
        self.assertIn('Abs(Current.Z - Destination.Z)',body)

    def test_reporter_records_only_current_target_once_per_turn(self):
        scan=function_body(self.recorder,'RecordCurrentPatrolWaypoints')
        observe=function_body(self.recorder,'Observe')
        start=function_body(self.recorder,'Start')
        for token in ('MaxGroupsPerObservation', 'GetCurrentPatrolWaypoint(',
                      'Group.GetGroupMidpoint()', 'Group.TurnCountForLastDestination',
                      'Emit("patrol_group"', 'next_waypoint_unknown=true',
                      'future_route=unknown', 'groups_checked='):
            self.assertIn(token,scan)
        self.assertIn('PlayerState.PlayerTurnCount != LastPatrolObservationTurn',observe)
        self.assertIn('RecordCurrentPatrolWaypoints(LastPatrolObservationTurn)',observe)
        self.assertIn('LastPatrolObservationTurn = -1;',start)
        self.assertNotIn('CreateNewGameState(',scan)
        self.assertNotIn('ModifyStateObject(',scan)

    def test_group_sampling_has_configurable_sane_limit(self):
        ini=(ROOT/'AutoplayXCom2/Config/XComAutoplayXCom2.ini').read_text()
        self.assertIn('[AutoplayXCom2.APX_PatrolKnowledge]',ini)
        self.assertIn('MaxGroupsPerObservation=32',ini)
        self.assertIn("Clamp(class'APX_PatrolKnowledge'.default.MaxGroupsPerObservation, 1, 48)",
                      function_body(self.recorder,'RecordCurrentPatrolWaypoints'))


if __name__=='__main__':
    unittest.main()
