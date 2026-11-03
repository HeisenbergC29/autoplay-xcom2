"""Public game-score observations remain read-only and separate from AI utility.

These contract checks use the provided SDK. They validate event payloads and
native field declarations; the Windows compiler and game remain required.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, braced_body, function_body


ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionRecorder.uc'


class RecorderScoringContracts(unittest.TestCase):
    def test_observer_never_awards_points_or_changes_game_state(self):
        source = CHECKS.without_comments(RECORDER.read_text())
        forbidden = r'\b(?:AddKillMail|AddMissionObjectiveComplete|AddIndividualMissionObjectiveComplete|AddTacticalGameEnd|AddCivilianRescued|ModifyStateObject|CreateNewGameState|SubmitGameState|SetUnitFloatValue|SetControllingPlayer|Rand|FRand)\s*\('
        self.assertIsNone(re.search(forbidden, source))

    def test_native_total_is_phase_labeled_and_stays_in_the_recorded_rung(self):
        score = function_body(RECORDER.read_text(), 'RecordGameScore')
        self.assertIn("class'XComGameState_LadderProgress'", score)
        for field in ('source=legacy_runtime', 'ladder_index=', 'ladder_rung=',
                      'cumulative_score=', 'phase=', 'history='):
            self.assertIn(field, score)
        self.assertIn('Ladder.LadderIndex != RecordedLadderIndex', score)
        self.assertIn('Ladder.LadderRung != RecordedLadderRung', score)
        self.assertIn('Fields == LastGameScore && Phase != "start" && Phase != "finish"', score)
        self.assertIn('RecordGameScore(Phase)', function_body(RECORDER.read_text(), 'Observe'))
        self.assertNotIn('MaxScore', score)

    def test_score_deltas_are_not_lost_in_the_ability_only_history_filter(self):
        source = RECORDER.read_text()
        results = function_body(source, 'RecordResults')
        delta = function_body(source, 'RecordScoreDeltas')
        self.assertLess(results.index('RecordScoreDeltas(HistoryState)'),
                        results.index('Context = XComGameStateContext_Ability('))
        self.assertIn("HistoryState.IterateByClassType(class'XComGameState_ChallengeScore'", delta)
        self.assertIn('ScoreKey = HistoryState.HistoryIndex $ ":" $ ScoreState.ObjectID', delta)
        self.assertIn('RecordedScoreKeys.Find(ScoreKey)', delta)
        self.assertIn('RecordedScoreKeys.AddItem(ScoreKey)', delta)
        for field in ('scoring_type=', 'added_points=', 'ladder_bonus=', 'score_id=', 'turn='):
            self.assertIn(field, delta)
        self.assertNotIn('IterateByClassType(class\'XComGameState_Unit\'', delta)

    def test_result_turn_uses_each_historical_frame_instead_of_current_phase(self):
        results = function_body(RECORDER.read_text(), 'RecordResults')
        primary = results[results.index('Emit("result",'):results.index('for (TargetIndex =')]
        secondary = results[results.index('Emit("result_target",'):]
        for fields in (primary, secondary):
            self.assertIn('"|turn=" $ TurnAtHistory(HistoryCursor)', fields)
        turn = function_body(RECORDER.read_text(), 'TurnAtHistory')
        self.assertIn('OwnerPlayerID, eReturnType_Reference, HistoryIndex', turn)
        self.assertIn('PlayerState != none ? PlayerState.PlayerTurnCount : -1', turn)

    def test_runtime_configuration_requires_the_same_live_legacy_rung(self):
        source = RECORDER.read_text()
        manager = function_body(source, 'RuntimeScoreManager')
        for contract in ('!bHasLadderScore || !IsRecordingMission()',
                         'Manager = `CHALLENGEMODE_MGR', 'Manager == none',
                         'Ladder.LadderIndex != RecordedLadderIndex',
                         'Ladder.LadderRung != RecordedLadderRung'):
            self.assertIn(contract, manager)
        for name in ('RecordBaseScoreRules', 'RecordVisibleEnemyScoreRule', 'RecordObjectiveScoreRule'):
            rule = function_body(source, name)
            self.assertIn('Manager = RuntimeScoreManager()', rule)
            self.assertLess(rule.index('if (Manager == none)'), rule.index('Manager.Get'))
        base = function_body(source, 'RecordBaseScoreRules')
        for contract in ('Manager.GetSoldierScoring(Soldier)', 'Manager.GetTimeScoring(TimeRule)',
                         'Soldier.UninjuredBonus', 'Soldier.WoundedBonus',
                         'Soldier.RescuedCivilianBonus', 'TimeRule.PointsPerInterval',
                         'TimeRule.IntervalInSeconds'):
            self.assertIn(contract, base)

    def test_enemy_and_objective_rules_only_follow_public_observations(self):
        source = RECORDER.read_text()
        observe = function_body(source, 'Observe')
        visible = observe[observe.index('foreach VisibleEnemies(EnemyRef)'):]
        self.assertIn('RecordVisibleEnemyScoreRule(UnitState)', visible)
        self.assertNotIn('RecordVisibleEnemyScoreRule', observe[:observe.index('foreach VisibleEnemies(EnemyRef)')])
        enemy = function_body(source, 'RecordVisibleEnemyScoreRule')
        self.assertIn('Manager.GetEnemyScoring(Enemy, string(UnitState.GetMyTemplateName()))', enemy)
        for field in ('starting_points=', 'min_points=', 'decrease_per_turn=', 'turn_offset=',
                      'spawned_points=', 'reinforcement_points=', 'disabled_points=', 'min_disabled_points='):
            self.assertIn(field, enemy)
        self.assertNotIn('IterateByClassType', enemy)
        completed = function_body(source, 'OnObjectiveCompleted')
        self.assertLess(completed.index('if (!bFound)'), completed.index('RecordObjectiveScoreRule('))
        objective = function_body(source, 'RecordObjectiveScoreRule')
        self.assertIn('Manager.GetObjectiveScoring(Objective, RecordedMissionType, DisplayAction.TextPoolIndex,\n'
                      '        DisplayAction.GroupID, DisplayAction.LineIndex)', objective)
        for field in ('objective_id=', 'text_pool_index=', 'group_id=', 'line_index='):
            self.assertIn(field, objective)

    def test_configuration_dedup_preserves_changed_rules_and_f8_is_not_full_coverage(self):
        source = RECORDER.read_text()
        rule = function_body(source, 'EmitScoreRule')
        self.assertIn('RecordedScoreRules.Find(Fields)', rule)
        self.assertIn('RecordedScoreRules.AddItem(Fields)', rule)
        self.assertIn('Emit("score_rule", "|source=legacy_runtime" $ Fields', rule)
        self.assertLess(rule.index('RecordedScoreRules.AddItem(Fields)'), rule.index('"|history="'))
        start = function_body(source, 'Start')
        self.assertIn('Emit("scoring_coverage", "|complete=false|reason=recording_begins_at_f8"', start)
        self.assertNotIn('complete=true', source)

    def test_wound_and_native_eligibility_metrics_are_added_only_to_owned_snapshots(self):
        unit = function_body(RECORDER.read_text(), 'RecordUnit')
        owned = unit.index('if (bFriendly)', unit.index('Fields ='))
        metrics = braced_body(unit, unit.index('{', owned))
        for gate in ('GetPreviousTeam() == eTeam_XCom', '!UnitState.bMissionProvided',
                     "GetUnitValue('NewSpawnedUnit'", "GetUnitValue('LadderKilledScored'"):
            self.assertIn(gate, metrics)
        for field in ('unconscious=', 'bleeding_turns_remaining=', 'score_eligible=', 'highest_hp=', 'lowest_hp=',
                      'ladder_killed_scored='):
            self.assertIn(field, metrics)
            self.assertNotIn(field, unit[:owned])

    def test_target_damage_observations_distinguish_death_from_zero_hp(self):
        health = function_body(RECORDER.read_text(), 'TargetHealthFields')
        for field, predicate in (('target_alive_after=', 'AfterUnit.IsAlive()'),
                                 ('target_incapacitated_after=', 'AfterUnit.IsIncapacitated()'),
                                 ('target_bleeding_out_after=', 'AfterUnit.IsBleedingOut()')):
            self.assertIn(field, health)
            self.assertIn(predicate, health)
        self.assertLess(health.index('if (BeforeUnit == none || AfterUnit == none)'),
                        health.index('AfterUnit.IsAlive()'))

    def test_objective_completion_requires_the_public_completed_checkbox(self):
        objective = function_body(RECORDER.read_text(), 'OnObjectiveCompleted')
        for contract in ('SeqAct_DisplayMissionObjective(EventSource)',
                         'XComGameState_ObjectivesList(EventData)',
                         'Info.MissionType == RecordedMissionType',
                         'Info.ShowCompleted && Info.ShowCheckBox && !Info.HideInTactical',
                         'CompletedObjectiveIDs.Find(ObjectiveID)',
                         'CompletedObjectiveIDs.AddItem(ObjectiveID)',
                         'Safe(ObjectiveName)', 'TurnAtHistory(HistoryIndex)'):
            self.assertIn(contract, objective)
        self.assertIn('objective_completed', objective)
        self.assertNotIn('added_points=', objective)

    def test_event_observers_are_registered_once_and_released_when_session_finishes(self):
        source = RECORDER.read_text()
        start = function_body(source, 'Start')
        register = function_body(source, 'RegisterScoreObservers')
        unregister = function_body(source, 'UnregisterScoreObservers')
        finish = function_body(source, 'Finish')
        self.assertEqual(start.count('RegisterScoreObservers()'), 1)
        self.assertIn('Listener = self;', register)
        self.assertIn('ELD_OnStateSubmitted', register)
        for event in ('MissionObjectiveMarkedCompleted', 'CivilianRescued'):
            self.assertIn("'" + event + "'", register)
            self.assertIn("'" + event + "'", unregister)
        self.assertLess(finish.index('UnregisterScoreObservers()'),
                        finish.index('bFinished = true;'))

    def test_civilian_rescue_checks_own_rescuer_and_redacts_unknown_identity(self):
        rescue = function_body(RECORDER.read_text(), 'OnCivilianRescued')
        self.assertIn('Rescuer = XComGameState_Unit(EventData)', rescue)
        self.assertIn('Civilian = XComGameState_Unit(EventSource)', rescue)
        self.assertIn('Rescuer.GetAssociatedPlayerID() != OwnerPlayerID', rescue)
        self.assertIn('OwnerPlayerID, VisibleObjects, , GameState.HistoryIndex', rescue)
        self.assertIn("VisibleObjects.Find('ObjectID', Civilian.ObjectID)", rescue)
        self.assertLess(rescue.index("VisibleObjects.Find('ObjectID'"),
                        rescue.index('CivilianID = Civilian.ObjectID'))
        self.assertNotIn('TileLocation', rescue)
        self.assertNotIn('GetCurrentStat', rescue)
        self.assertIn('RescuedCivilianIDs.Find(Civilian.ObjectID)', rescue)

    def test_loot_has_an_explicit_handler_and_new_revision(self):
        source = RECORDER.read_text()
        self.assertIn("if (AbilityName == 'Loot')\n        return \"loot\";",
                      function_body(source, 'AbilityHandler'))
        self.assertIn('revision=mission-report-v9', function_body(source, 'Start'))


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Scoring observer contracts need SDK sources')
class RecorderScoringSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classes = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_native_point_fields_and_soldier_qualification_match_observations(self):
        ladder = (self.classes / 'XComGameState_LadderProgress.uc').read_text(encoding='utf-8-sig')
        for name in ('LadderIndex', 'LadderRung', 'CumulativeScore'):
            self.assertRegex(ladder, r'var\s+int\s+' + name + r'\s*;')
        damage = function_body(ladder, 'OnUnitDamage')
        for field in ('GetPreviousTeam()', 'bMissionProvided', 'bIsCosmetic',
                      'NewSpawnedUnit', 'PreviousState.HighestHP > PreviousState.LowestHP'):
            self.assertIn(field, damage)
        score = (self.classes / 'XComGameState_ChallengeScore.uc').read_text(encoding='utf-8-sig')
        for name in ('AddedPoints', 'LadderBonus'):
            self.assertRegex(score, r'var\s+int\s+' + name + r'\s*;')
        unit = (self.classes / 'XComGameState_Unit.uc').read_text(encoding='utf-8-sig')
        self.assertRegex(unit, r'var\(\)\s+int\s+HighestHP\s*;')
        self.assertRegex(unit, r'var\(\)\s+int\s+LowestHP\s*;')
        self.assertRegex(unit, r'function\s+int\s+GetBleedingOutTurnsRemaining\s*\(\s*\)')

    def test_native_configuration_getters_and_struct_fields_match_runtime_observations(self):
        manager = (self.classes / 'XComChallengeModeManager.uc').read_text(encoding='utf-8-sig')
        for getter, declaration in (
                ('GetSoldierScoring', r'out ChallengeSoldierScoring SoldierScoring'),
                ('GetTimeScoring', r'out ChallengeTimeScoring TimeScoring'),
                ('GetEnemyScoring', r'out ChallengeEnemyScoring EnemyScoring, string CharacterTemplateName'),
                ('GetObjectiveScoring', r'out ChallengeObjectiveScoring ObjectiveScoring, string MissionType = "", int TextPoolIndex = -1, int GroupID = -1, int LineIndex = -1')):
            self.assertIn('final native function ' + getter + '(' + declaration, manager)
        data = (self.classes / 'X2ChallengeModeDataStructures.uc').read_text(encoding='utf-8-sig')
        for name in ('StartingPoints', 'MinPoints', 'DecreasePerTurn', 'TurnOffset',
                     'SpawnedPoints', 'ReinforcementPoints', 'DisabledPoints', 'MinDisabledPoints',
                     'UninjuredBonus', 'WoundedBonus', 'RescuedCivilianBonus',
                     'PointsPerInterval', 'IntervalInSeconds'):
            self.assertRegex(data, r'var\s+int\s+' + name + r'\s*;')

    def test_native_event_payloads_and_registration_signatures_match(self):
        objective = (self.classes / 'SeqAct_DisplayMissionObjective.uc').read_text(encoding='utf-8-sig')
        self.assertIn("TriggerEvent('MissionObjectiveMarkedCompleted', ObjectiveList, self, NewGameState)", objective)
        ai = (self.classes / 'X2AIBTDefaultActions.uc').read_text(encoding='utf-8-sig')
        self.assertIn("TriggerEvent('CivilianRescued', NewRescuerUnit, UnitState, NewGameState2)", ai)
        manager = (self.classes / 'X2EventManager.uc').read_text(encoding='utf-8-sig')
        self.assertIn('RegisterForEvent( ref Object SourceObj,', manager)
        self.assertIn('UnRegisterFromEvent( const ref Object SourceObj,', manager)
        visibility = (self.classes / 'X2TacticalVisibilityHelpers.uc').read_text(encoding='utf-8-sig')
        self.assertRegex(visibility, r'GetAllVisibleObjectsForPlayer\(int PlayerStateObjectID,\s*'
                         r'out array<StateObjectReference> VisibleUnits,\s*'
                         r'optional array<X2Condition> RequiredConditions,\s*int HistoryIndex = -1,')


if __name__ == '__main__':
    unittest.main()
