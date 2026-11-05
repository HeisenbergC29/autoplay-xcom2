"""The live partial score uses the frozen report profile and public observations.

Numeric cases execute the real UC helpers. Native visibility/history/event
contracts protect the observational boundary; the Windows game is still needed.
"""
import json
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, braced_body, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_ComparisonScore.uc'


class LiveComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text()
        cls.profile = json.loads((ROOT / 'tools/legacy-score-rules.json').read_text())
        cls.enemy = staticmethod(load_uc_function(SOURCE, 'EnemyPoints'))
        cls.soldier = staticmethod(load_uc_function(SOURCE, 'SoldierPoints'))
        cls.objective = staticmethod(load_uc_function(SOURCE, 'CompletedObjectivePoints'))

    def test_runtime_profile_id_matches_the_default_report_profile(self):
        body = function_body(self.source, 'GetProfileID')
        match = re.fullmatch(r'\s*return "([^"]+)";\s*', body)
        self.assertIsNotNone(match)
        self.assertEqual(match[1], self.profile['profile_id'])

    def test_enemy_points_match_frozen_profile_across_turn_decay_boundaries(self):
        for template in (*self.profile['enemies'], 'AdvTrooperM1', 'UnobservedModEnemy'):
            rule = self.profile['enemies'].get(template, self.profile['enemy_default'])
            for turn in (0, 1, 2, 3, 5, 6, 20):
                with self.subTest(template=template, turn=turn):
                    expected = max(rule['min_points'], rule['starting_points']
                                   - max(0, turn - rule['turn_offset']) * rule['decrease_per_turn'])
                    self.assertEqual(self.enemy(template, turn), expected)
        self.assertEqual(self.enemy('Sectoid', -1), 0)

    def test_objectives_and_soldier_penalties_match_the_report_profile(self):
        rule = self.profile['objective']
        for turn in (0, 1, 2, 5, 6, 20):
            self.assertEqual(self.objective(turn), max(rule['min_points'], rule['starting_points']
                             - max(0, turn - rule['turn_offset']) * rule['decrease_per_turn']))
        self.assertEqual(self.objective(-1), 0)
        self.assertEqual(self.profile['profile_id'], 'wotc_legacy_observed_v2')
        self.assertFalse(self.profile['initial_soldier_allowance'])
        soldier = self.profile['soldier']
        for wounded in (False, True):
            for lost in (False, True):
                expected = (-wounded * soldier['uninjured_bonus']
                            - lost * soldier['survival_bonus'])
                self.assertEqual(self.soldier(True, wounded, lost), expected)
                self.assertEqual(self.soldier(False, wounded, lost), 0)

    def test_prior_report_recomputes_to_negative_18800_without_initial_allowances(self):
        # Four eligible soldiers, all injured, three confirmed deaths, two
        # ordinary/default troopers killed after their minimum-point boundary.
        observed = 3 * self.soldier(True, True, True) + self.soldier(True, True, False)
        observed += self.enemy('AdvTrooperM1', 7) + self.enemy('AdvTrooperM1', 12)
        self.assertEqual(observed, -18800)
        self.assertEqual(4 * self.soldier(True, False, False), 0)

    def test_soldier_injury_death_and_eligibility_only_use_owned_native_metrics(self):
        observe = function_body(self.source, 'ObserveUnit')
        for contract in ("UnitState.GetPreviousTeam() == eTeam_XCom", '!UnitState.bMissionProvided',
                         "!UnitState.GetUnitValue('NewSpawnedUnit', SpawnedValue)",
                         'UnitState.HighestHP > UnitState.LowestHP',
                         "UnitState.GetUnitValue('LadderKilledScored', KilledValue)",
                         'Units[Index].bLost || !UnitState.IsAlive()'):
            self.assertIn(contract, observe)
        owned_start = observe.index('if (bFriendly)')
        owned = braced_body(observe, observe.index('{', owned_start))
        self.assertIn('UnitState.HighestHP > UnitState.LowestHP', owned)
        self.assertNotIn('GetMaxStat', observe)
        self.assertNotIn('IsIncapacitated()', observe)
        self.assertNotIn('IsBleedingOut()', observe)
        # Loss flags are idempotent; collecting a snapshot repeatedly cannot
        # charge each wound/death more than once.
        self.assertNotIn('Score -=', observe)
        self.assertNotIn('Score +=', observe)

    def test_first_observed_affiliation_survives_both_mind_control_directions(self):
        index = function_body(self.source, 'UnitIndex')
        self.assertLess(index.index('if (Index != INDEX_NONE)'),
                        index.index('Entry.bOriginalFriendly = bFriendly'))
        self.assertIn('return Index', index)
        observe = function_body(self.source, 'ObserveUnit')
        self.assertIn('if (Units[Index].bOriginalFriendly)', observe)
        self.assertIn('if (!bFriendly && UnitState.IsAlive())', observe)
        self.assertNotIn('bOriginalFriendly =', observe)
        self.assertIn('!Units[Index].bEliminated', observe)
        self.assertIn('!UnitState.IsAlive() && Units[Index].bSeenAliveEnemy', observe)

    def test_owner_is_local_player_not_the_current_action_side(self):
        ensure = function_body(self.source, 'EnsureMission')
        self.assertIn('PC = XComTacticalController(World.GetALocalPlayerController())', ensure)
        self.assertIn('PC == none || PC.m_XGPlayer == none', ensure)
        self.assertIn('PlayerID = PC.m_XGPlayer.ObjectID', ensure)
        self.assertNotIn('GetCachedUnitActionPlayerRef', self.source)
        self.assertIn("class'XComGameState_LadderProgress'", ensure)
        self.assertIn("class'XComGameState_ChallengeData'", ensure)

    def test_history_is_chronological_bounded_and_uses_that_frames_visibility(self):
        ensure = function_body(self.source, 'EnsureMission')
        self.assertIn('HistoryCursor = CurrentStart - 1', ensure)
        self.assertIn('StartingBattle.MapData.ActiveMission.sType != BattleData.MapData.ActiveMission.sType', ensure)
        score = function_body(self.source, 'GetObservedScore')
        self.assertIn('HistoryCursor + 256', score)
        self.assertIn('++HistoryCursor', score)
        self.assertIn('ObserveFrame(HistoryCursor)', score)
        frame = function_body(self.source, 'ObserveFrame')
        self.assertIn('OwnerPlayerID, VisibleNow, HistoryIndex', frame)
        self.assertIn('OwnerPlayerID, VisibleBefore, HistoryIndex - 1', frame)
        self.assertIn('UnitRef.ObjectID, eReturnType_Reference, HistoryIndex', frame)
        self.assertIn('foreach VisibleNow(UnitRef)', frame)
        self.assertNotIn('foreach Units(', frame)
        # Changed hidden state objects expose ownership metadata only. Full
        # enemy snapshots are fetched through the actual visible references.
        own = frame.index("foreach Frame.IterateByClassType(class'XComGameState_Unit'")
        own_body = braced_body(frame, frame.index('{', own))
        self.assertIn('UnitState.GetAssociatedPlayerID() == OwnerPlayerID', own_body)
        self.assertIn('ObserveUnit(UnitState, true, HistoryIndex)', own_body)
        self.assertNotIn('ObserveUnit(UnitState, false', own_body)

    def test_lethal_target_reads_need_ownership_visibility_or_own_visible_before_action(self):
        target = function_body(self.source, 'ObserveResultTarget')
        self.assertIn("VisibleNow.Find('ObjectID', UnitID) == INDEX_NONE", target)
        self.assertIn("(!bOwnAction || VisibleBefore.Find('ObjectID', UnitID) == INDEX_NONE)", target)
        self.assertLess(target.index('return;', target.index('if (!bOwnTarget')),
                        target.index('ObservedHistory.GetGameStateForObjectID('))
        self.assertIn('if (bOwnAction && HistoryIndex > StartIndex', target)
        frame = function_body(self.source, 'ObserveFrame')
        self.assertIn('Context.InterruptionStatus == eInterruptionStatus_Interrupt', frame)
        self.assertIn('foreach Context.InputContext.MultiTargets(UnitRef)', frame)
        self.assertNotIn('AdditionalTargets', frame)

    def test_callbacks_only_count_public_completed_goals_and_owned_rescues(self):
        goal = function_body(self.source, 'OnObjectiveCompleted')
        for contract in ('HasCurrentMission()', 'GameState.HistoryIndex < StartIndex',
                         'SeqAct_DisplayMissionObjective(EventSource)',
                         'XComGameState_ObjectivesList(EventData)',
                         '!Info.ShowCompleted || !Info.ShowCheckBox || Info.HideInTactical',
                         'CompletedObjectives.Find(ObjectiveID) == INDEX_NONE && Turn >= 0',
                         'CompletedObjectivePoints(Turn)'):
            self.assertIn(contract, goal)
        rescue = function_body(self.source, 'OnCivilianRescued')
        self.assertIn('Rescuer.GetAssociatedPlayerID() == OwnerPlayerID', rescue)
        self.assertIn('RescuedCivilianIDs.Find(Civilian.ObjectID) == INDEX_NONE', rescue)
        self.assertNotIn('Civilian.TileLocation', rescue)
        self.assertNotIn('Civilian.GetCurrentStat', rescue)
        self.assertIn("RescuedCivilianIDs.Length * 1000", function_body(self.source, 'GetObservedScore'))
        self.assertEqual(self.profile['civilian']['rescued_bonus'], 1000)

    def test_callbacks_cleanup_and_identity_guards_are_independent_of_f8(self):
        register = function_body(self.source, 'RegisterEvents')
        cleanup = function_body(self.source, 'Cleanup')
        for event in ('MissionObjectiveMarkedCompleted', 'CivilianRescued'):
            self.assertIn("'" + event + "'", register)
            self.assertIn("'" + event + "'", cleanup)
        self.assertIn('bInitialized = false', cleanup)
        self.assertIn('Units.Length = 0', cleanup)
        current = function_body(self.source, 'HasCurrentMission')
        for guard in ('`XCOMHISTORY != ObservedHistory', 'FindStartStateIndex() != StartIndex',
                      'GetCurrentHistoryIndex() < LastHistoryIndex', 'BattleData.ObjectID == BattleID',
                      'BattleData.MapData.ActiveMission.sType == MissionType'):
            self.assertIn(guard, current)
        for forbidden in ('APX_Controller', 'IsEnabled()', 'Toggle()', 'EnableMissionRecording'):
            self.assertNotIn(forbidden, self.source)

    def test_observer_never_changes_rules_states_rng_or_native_scoring(self):
        source = CHECKS.without_comments(self.source)
        forbidden = r'\b(?:AddKillMail|AddTacticalGameEnd|AddMissionObjectiveComplete|AddIndividualMissionObjectiveComplete|AddCivilianRescued|ModifyStateObject|CreateNewGameState|CreateStateObject|SubmitGameState|SetCurrentStat|SetUnitFloatValue|ActivateAbility_ReturnContext|SetCurrentHistoryIndex|Rand|FRand)\s*\('
        self.assertIsNone(re.search(forbidden, source))
        self.assertNotIn('GetEnemyScoring', source)
        self.assertNotIn('bLocalPlayerWon =', source)
        self.assertIn('return bInitialized', function_body(self.source, 'IsReady'))


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Live comparison contracts need SDK sources')
class LiveComparisonSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_native_history_visibility_and_public_events_match_the_sdk(self):
        visibility = (self.sdk / 'X2TacticalVisibilityHelpers.uc').read_text(encoding='utf-8-sig')
        self.assertIsNotNone(re.search(r'GetAllVisibleEnemiesForPlayer\(int PlayerStateObjectID,\s*out array<StateObjectReference> VisibleUnits,\s*int HistoryIndex = -1', visibility))
        history = (self.sdk / 'XComGameStateHistory.uc').read_text(encoding='utf-8-sig')
        self.assertIn('native final function int FindStartStateIndex();', history)
        unit = (self.sdk / 'XComGameState_Unit.uc').read_text(encoding='utf-8-sig')
        self.assertRegex(unit, r'var\(\) int\s+LowestHP;')
        self.assertRegex(unit, r'var\(\) int\s+HighestHP;')
        recorder = (ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionRecorder.uc').read_text()
        self.assertIn("'MissionObjectiveMarkedCompleted'", recorder)
        self.assertIn("'CivilianRescued'", recorder)
        self.assertIn('SeqAct_DisplayMissionObjective(EventSource)', recorder)
        self.assertIn('Rescuer = XComGameState_Unit(EventData)', recorder)


if __name__ == '__main__':
    unittest.main()
