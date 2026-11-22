"""Check native snapshot boundaries, reserve evidence and group identity for v48 patrol windows."""

import os
from pathlib import Path
import unittest

from test_ui_gating import CHECKS, CLASSES, function_body
from uc_math import load_uc_function


RECORDER = CLASSES / 'APX_MissionRecorder.uc'
SOURCE = RECORDER.read_text()
CONTROLLER = (CLASSES / 'APX_Controller.uc').read_text()
AMBUSH = (CLASSES / 'APX_PatrolAmbushPlanner.uc').read_text()


class PatrolRecorderTests(unittest.TestCase):
    """Check the stock actions that can supply evidence for a whole-squad salvo."""

    def test_consecutive_reserve_cost_classification(self):
        """Execute the actual classifier for single costs, refunds and concurrent changes."""
        classify = load_uc_function(RECORDER, 'ClassifyReserveChange')
        for counts, expected in [
            ((2, 1, 1, 1), 1), ((1, 1, 2, 1), 2), ((0, 0, 0, 0), 0),
            ((1, 1, 1, 1), 0), ((0, 1, 0, 0), 0), ((2, 0, 0, 0), 0),
            ((1, 0, 1, 0), 0), ((1, 0, 0, 1), 0),
        ]:
            with self.subTest(counts=counts):
                self.assertEqual(classify(*counts), expected)

    def test_paid_reserve_requires_friendly_states_on_either_side(self):
        """Pistol can spend one of two reserve types; both observations must belong to the owner."""
        body = function_body(SOURCE, 'ShotReserveSpent')
        for expression in ('BeforeUnit == none || AfterUnit == none',
                           'BeforeUnit.GetAssociatedPlayerID() != OwnerPlayerID',
                           'AfterUnit.GetAssociatedPlayerID() != OwnerPlayerID',
                           'SourceID, eReturnType_Reference, BeforeIndex',
                           'SourceID, eReturnType_Reference, ResultIndex',
                           "AbilityName == 'PistolOverwatchShot'",
                           'default.OverwatchReserveActionPoint', 'default.PistolOverwatchReserveActionPoint',
                           'BeforeUnit.NumReserveActionPoints', 'AfterUnit.NumReserveActionPoints',
                           'default.ReturnFireActionPoint', 'ClassifyReserveChange(',
                           'return "spent"', 'return "other"', 'return "unknown"'):
            self.assertIn(expression, body)

    def test_field_emission_follows_resolved_friendly_reaction_and_redacted_target(self):
        """No disallowed, interrupted or unobservable shot can acquire positive evidence."""
        body = function_body(SOURCE, 'PatrolReactionFields')
        for term in ('!bOwnAction', '!class\'APX_FullIntel\'.default.EnableFullIntel',
                     "AbilityName == 'OverwatchShot'", "AbilityName == 'PistolOverwatchShot'",
                     "AbilityName == 'LongWatchShot'", 'BeforeIndex + 1 != ResultIndex',
                     'RecordedHistory.GetGameStateFromHistory(BeforeIndex) == none',
                     'BeforeIndex < RecordedStartStateIndex', 'target_group=0|ow_reserve=unknown',
                     'ReactionGroupField(TargetID, BeforeIndex, ResultIndex)',
                     'ShotReserveSpent(AbilityName, SourceID, BeforeIndex, ResultIndex)'):
            self.assertIn(term, body)
        results = function_body(SOURCE, 'RecordResults')
        reactions = results.index('PatrolReactionFields(bOwnAction')
        for term in ('BeforeActionEnemies.Find', 'TargetID = 0;',
                     'Context.InterruptionStatus == eInterruptionStatus_Interrupt', 'Emit("result",'):
            self.assertLess(results.index(term), reactions)
        self.assertIn('continue;', results[results.index('Emit("interrupted",'):results.index('Emit("result",')])
        self.assertEqual(1, results.count('PatrolReactionFields('))

    def test_historical_roster_retains_complete_empty_and_truncation(self):
        """Count available rifle and pistol reserves from the boundary snapshot, with bounded traversal."""
        body = function_body(SOURCE, 'CollectPatrolReserves')
        for term in ('eReturnType_Reference, false, HistoryIndex', '++Checked > 256',
                     'Soldier.GetAssociatedPlayerID() != OwnerPlayerID', 'Soldier.GetTeam() != eTeam_XCom',
                     'Soldier.bRemovedFromPlay', '!Soldier.IsAlive()', 'OverwatchReserveActionPoint',
                     'PistolOverwatchReserveActionPoint', 'string(Soldier.ObjectID)'):
            self.assertIn(term, body)
        self.assertNotIn('ReturnFireActionPoint', body)
        window = function_body(SOURCE, 'RecordPatrolWindow')
        for term in ('!IsRecordingMission()', 'HistoryIndex >= RecordingStartHistory',
                     'HistoryIndex <= RecordedHistory.GetCurrentHistoryIndex()',
                     'RecordedHistory.GetGameStateFromHistory(HistoryIndex) != none',
                     'TurnAtHistory(HistoryIndex) == Turn', 'bComplete = CollectPatrolReserves(',
                     'Armed = "none"', '"|complete=" $ string(bComplete)'):
            self.assertIn(term, window)

    def test_target_membership_and_final_casualty_require_observable_death(self):
        """Group links must be reciprocal before impact and newly added or surviving members veto extinction."""
        field = function_body(SOURCE, 'ReactionGroupField')
        for term in ('TargetID <= 0', 'Target.GetAssociatedPlayerID() == OwnerPlayerID',
                     'Target.GroupMembershipID, eReturnType_Reference, BeforeIndex', 'Group.bRemoved',
                     'Group.m_arrMembers.Length > 24', "Group.m_arrMembers.Find('ObjectID', TargetID)",
                     'Target.IsAlive() && AfterTarget != none && AfterTarget.IsDead()',
                     'IsPatrolEliminated(Group, ResultIndex)', '"|patrol_targets_remaining=0"'):
            self.assertIn(term, field)
        extinct = function_body(SOURCE, 'IsPatrolEliminated')
        for term in ('BeforeGroup.ObjectID, eReturnType_Reference, ResultIndex',
                     'AfterGroup == none || AfterGroup.m_arrMembers.Length > 24',
                     "BeforeGroup.m_arrMembers.Find('ObjectID', Ref.ObjectID) == INDEX_NONE",
                     'foreach BeforeGroup.m_arrMembers(Ref)',
                     'Ref.ObjectID, eReturnType_Reference, ResultIndex', 'Member == none || !Member.IsDead()'):
            self.assertIn(term, extinct)

    def test_direct_opener_extinction_explains_unused_reserves(self):
        """An ordinary friendly kill can end the opportunity without earning reaction or reserve credit."""
        fields = function_body(SOURCE, 'PatrolReactionFields')
        no_reaction = fields.index('if (!bStockReaction)')
        extinction = fields.index('return ReactionGroupField(TargetID, BeforeIndex, ResultIndex, true)')
        self.assertLess(no_reaction, extinction)
        self.assertLess(extinction, fields.index('ShotReserveSpent('))
        group = function_body(SOURCE, 'ReactionGroupField')
        guard = group.index('bOnlyElimination && (AfterTarget == none || !AfterTarget.IsDead())')
        roster = group.index('Group = XComGameState_AIGroup(')
        self.assertLess(guard, roster)
        self.assertIn('if (bOnlyElimination)', group[group.index('IsPatrolEliminated('):])

    def test_accepted_arms_openers_and_confirmed_waits_supply_boundaries(self):
        """Read the pre-dispatch frame, then emit a window only after success or a confirmed wait."""
        decision = function_body(CONTROLLER, 'MakeDecision')
        steps = ['PatrolOrderHistory =', 'ActivateAbility_ReturnContext(', 'if (!bSuccess)',
                 'MissionRecorder.RecordPatrolArm(', 'MissionRecorder.RecordPatrolWindow(']
        indices = [decision.index(term) for term in steps]
        self.assertEqual(indices, sorted(indices))
        arm = function_body(SOURCE, 'RecordPatrolArm')
        for term in ('GroupID <= 0', 'SourceID <= 0', 'Turn < 0', '!IsRecordingMission()',
                     'Emit("patrol_arm",', '"|history=" $ HistoryIndex'):
            self.assertIn(term, arm)
        confirmation = function_body(AMBUSH, 'NoteWaitConfirmed')
        self.assertIn("Recorder.RecordPatrolWindow(GroupID, RequestedTurn, RosterHistory, 'wait')", confirmation)

    def test_draining_and_manual_stop_use_native_history(self):
        """A recorder tick may observe results later than the action; keep its turn and missing ranges."""
        observe = function_body(SOURCE, 'Observe')
        self.assertLess(observe.index('RecordResults();'), observe.index('RecordPatrolDrain();'))
        drain = function_body(SOURCE, 'RecordPatrolDrain')
        for term in ('TurnAtHistory(HistoryCursor)', 'DrainedTurn <= LastPatrolWindowTurn',
                     'Emit("patrol_drain",', 'LastPatrolWindowTurn = INDEX_NONE'):
            self.assertIn(term, drain)
        markers = function_body(SOURCE, 'Marker')
        self.assertIn('Kind == "autoplay_stop" && IsRecordingMission()', markers)
        self.assertIn('TurnAtHistory(CurrentHistory)', markers)
        results = function_body(SOURCE, 'RecordResults')
        self.assertIn('GapStart = HistoryCursor;', results)
        self.assertIn('"|last=" $ (HistoryCursor - 1)', results)
        self.assertIn('"|last=" $ HistoryCursor', results)

    @unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Requires stock WOTC SDK sources')
    def test_sdk_stock_costs_match_reserve_observations(self):
        """Check the SDK pistol's dual reserve costs and the actual array read by the stock counter."""
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        pistol = function_body((sdk / 'X2Ability_DefaultAbilitySet.uc').read_text(encoding='cp1252'),
                               'PistolOverwatchShotHelper')
        for name in ('PistolOverwatchReserveActionPoint', 'ReturnFireActionPoint'):
            self.assertIn("ReserveActionPointCost.AllowedTypes.AddItem(class'X2CharacterTemplateManager'.default."
                          + name + ')', pistol)
        unit = (sdk / 'XComGameState_Unit.uc').read_text(encoding='cp1252')
        self.assertIn('InternalNumActionPoints(ReserveActionPoints, Type)',
                      function_body(unit, 'NumReserveActionPoints'))
