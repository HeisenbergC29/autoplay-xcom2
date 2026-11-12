"""Current stored waypoint exception, with bounded position-only membership.

Numeric tests execute helpers from the UC source. The native world/player
contracts still require Windows compilation and game observation.
"""
import os
from pathlib import Path
import unittest
from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SOURCE = CLASSES / 'APX_PatrolKnowledge.uc'
RECORDER = CLASSES / 'APX_MissionRecorder.uc'


class PatrolKnowledgeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding='utf-8-sig')
        cls.recorder = RECORDER.read_text(encoding='utf-8-sig')
        cls.eligible = staticmethod(load_uc_function(SOURCE, 'EligiblePatrolMember'))
        cls.usable = staticmethod(load_uc_function(SOURCE, 'UsableStoredWaypoint'))
        cls.consume = staticmethod(load_uc_function(SOURCE, 'ConsumeMemberReference'))

    def test_members_must_be_living_active_hostile_and_valid(self):
        ordinary = [True, False, False, False, False, True, True]
        self.assertTrue(self.eligible(*ordinary))
        for index in range(len(ordinary)):
            invalid = ordinary.copy()
            invalid[index] = not invalid[index]
            with self.subTest(index=index):
                self.assertFalse(self.eligible(*invalid))

    def test_zero_is_a_valid_coordinate_when_its_tile_is_in_world(self):
        self.assertTrue(self.usable(0.0, 0.0, 0.0, True))
        self.assertTrue(self.usable(-10.0, 40.0, 0.0, True))
        self.assertFalse(self.usable(0.0, 0.0, 0.0, False))
        for bad in (float('nan'), float('inf'), -float('inf'), 100000001.0):
            for index in range(3):
                coords = [1.0, 2.0, 3.0]
                coords[index] = bad
                with self.subTest(bad=bad, index=index):
                    self.assertFalse(self.usable(*coords, True))
        reader = function_body(self.source, 'GetCurrentPatrolWaypoint')
        self.assertNotIn('VSizeSq(Target)', reader)
        self.assertLess(reader.index('FiniteWaypointCoordinate(Target.X)'),
                        reader.index('GetTileCoordinatesFromPosition(Target)'))
        self.assertIn('!`XWORLD.IsTileOutOfRange(Waypoint)', reader)

    def test_budget_is_shared_across_groups_and_consumed_before_every_lookup(self):
        remaining = 128
        consumed_by_group = []
        for references in (80, 80, 80):
            before = remaining
            for _ in range(references):
                if remaining <= 0:
                    break
                remaining = self.consume(remaining)
            consumed_by_group.append(before - remaining)
        self.assertEqual(consumed_by_group, [80, 48, 0])
        self.assertEqual(self.consume(0), 0)
        self.assertEqual(self.consume(-1), 0)
        reader = function_body(self.source, 'GetCurrentPatrolWaypoint')
        scan = function_body(self.recorder, 'RecordCurrentPatrolWaypoints')
        self.assertLess(reader.index('if (RemainingMemberChecks <= 0)'),
                        reader.index('ConsumeMemberReference(RemainingMemberChecks)'))
        self.assertLess(reader.index('ConsumeMemberReference(RemainingMemberChecks)'),
                        reader.index('SeenMembers.Find('))
        self.assertLess(reader.index('SeenMembers.Find('),
                        reader.index('GetGameStateForObjectID(Ref.ObjectID)'))
        self.assertEqual(scan.count('RemainingMemberChecks = MemberBudget;'), 1)
        self.assertLess(scan.index('RemainingMemberChecks = MemberBudget;'),
                        scan.index('foreach `XCOMHISTORY.IterateByClassType('))
        call = scan.split('.static.GetCurrentPatrolWaypoint(', 1)[1].split(';', 1)[0]
        self.assertIn('RemainingMemberChecks)', call)
        self.assertIn('|| RemainingMemberChecks <= 0)', scan)
        self.assertIn('member_refs_checked=', scan)
        self.assertIn('member_budget_exhausted=', scan)

    def test_midpoint_and_count_use_only_the_same_verified_hostile_members(self):
        reader = function_body(self.source, 'GetCurrentPatrolWaypoint')
        scan = function_body(self.recorder, 'RecordCurrentPatrolWaypoints')
        for token in ('EligiblePatrolMember(Member.IsAlive(), Member.IsIncapacitated()',
                      'Member.bRemovedFromPlay', 'Member.IsCivilian()',
                      'Member.GetMyTemplate().bIsCosmetic',
                      "class'XGPlayerNativeBase'.static.AreEnemyTeams(",
                      'LocalPlayer.GetTeam(), Member.GetTeam()',
                      '!`XWORLD.IsTileOutOfRange(Member.TileLocation)',
                      'SeenMembers.AddItem(Ref.ObjectID)'):
            self.assertIn(token, reader)
        self.assertLess(reader.index('EligiblePatrolMember('), reader.index('++HostileMembers;'))
        self.assertLess(reader.index('++HostileMembers;'),
                        reader.index('Midpoint += `XWORLD.GetPositionFromTileCoordinates(Member.TileLocation);'))
        self.assertIn('Midpoint /= float(HostileMembers);', reader)
        self.assertIn('if (HostileMembers <= 0)', reader)
        self.assertIn('"|members=" $ HostileMembers', scan)
        self.assertNotIn('GetGroupMidpoint(', scan)
        self.assertNotIn('m_arrMembers.Length', scan)

    def test_full_intel_and_local_xcom_gate_both_reader_and_recorder(self):
        reader = function_body(self.source, 'GetCurrentPatrolWaypoint')
        scan = function_body(self.recorder, 'RecordCurrentPatrolWaypoints')
        observe = function_body(self.recorder, 'Observe')
        for body in (reader, scan):
            self.assertIn("!class'APX_FullIntel'.default.EnableFullIntel", body)
            self.assertIn('GetLocalClientPlayerObjectID()', body)
            self.assertIn('LocalPlayer.GetTeam() != eTeam_XCom', body)
            self.assertLess(body.index("!class'APX_FullIntel'.default.EnableFullIntel"),
                            body.index('Group.CurrentTargetLocation') if body is reader else
                            body.index('foreach `XCOMHISTORY.IterateByClassType('))
        self.assertIn("if (class'APX_FullIntel'.default.EnableFullIntel", observe)
        self.assertIn('&& PlayerState.PlayerTurnCount != LastPatrolObservationTurn', observe)
        self.assertIn('LastPatrolObservationTurn = -1;', function_body(self.recorder, 'Start'))

    def test_no_additional_private_enemy_state_or_future_decision_is_inspected(self):
        scan = function_body(self.recorder, 'RecordCurrentPatrolWaypoints')
        for body in (self.source, scan):
            for forbidden in ('IsEngaged(', 'HasAbsoluteKnowledge(', 'GetCurrentStat(',
                              'GetAIUnitDataID(', 'bPendingScamper', 'bProcessedScamper',
                              'bObjective', 'bInterceptObjectiveLocation',
                              'TurnCountForLastDestination', 'GetGroupMidpoint(',
                              'SYNC_RAND', 'GetNextDestination(', 'ShouldMoveToIntercept(',
                              'CreateNewGameState(', 'ModifyStateObject(', 'SubmitGameState('):
                with self.subTest(forbidden=forbidden):
                    self.assertNotIn(forbidden, body)
        self.assertIn('Group.CurrentTargetLocation', self.source)
        self.assertIn('is_stored_current_target=true|target_usage=unknown', scan)
        self.assertIn('next_waypoint_unknown=true', scan)
        self.assertIn('future_route=unknown', scan)

    def test_group_and_member_limits_are_configured_separately(self):
        ini = (ROOT / 'AutoplayXCom2/Config/XComAutoplayXCom2.ini').read_text()
        scan = function_body(self.recorder, 'RecordCurrentPatrolWaypoints')
        self.assertIn('MaxGroupsPerObservation=32', ini)
        self.assertIn('MaxMemberReferencesPerObservation=128', ini)
        self.assertIn("Clamp(class'APX_PatrolKnowledge'.default.MaxGroupsPerObservation, 1, 48)", scan)
        self.assertIn("Clamp(class'APX_PatrolKnowledge'.default.MaxMemberReferencesPerObservation, 1, 256)", scan)
        self.assertLess(scan.index('if (Seen >='), scan.index('++Seen;'))
        self.assertLess(scan.index('++Seen;'), scan.index('.static.GetCurrentPatrolWaypoint('))


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Private SDK sources unavailable')
class PatrolSDKContracts(unittest.TestCase):
    def test_reader_uses_real_public_state_fields_and_native_hostility_api(self):
        sdk = Path(os.environ['APX_SDK_SOURCE_ROOT']) / 'XComGame/Classes'
        group = (sdk / 'XComGameState_AIGroup.uc').read_text(encoding='utf-8-sig')
        player = (sdk / 'XComGameState_Player.uc').read_text(encoding='utf-8-sig')
        native = (sdk / 'XGPlayerNativeBase.uc').read_text(encoding='utf-8-sig')
        self.assertIn('var Vector', group)
        self.assertIn('CurrentTargetLocation;', group)
        self.assertIn('var privatewrite array<StateObjectReference> m_arrMembers;', group)
        self.assertIn('simulated function ETeam GetTeam()', player)
        self.assertIn('static final native function bool AreEnemyTeams( eTeam TeamOne, eTeam TeamTwo );', native)
