"""Read-only native failure and transmitter-target discovery contracts.

Source checks do not replace a Windows WOTC SDK compile or gameplay. A
'destructible candidate' is not presumed to be a power relay until verified.
"""
from pathlib import Path
import unittest
from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionRecorder.uc'


class CriticalObjectiveRelayContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=FILE.read_text(encoding='utf-8-sig')

    def test_failed_event_is_observed_from_native_ui_not_invented(self):
        registration=function_body(self.source,'RegisterScoreObservers')
        cleanup=function_body(self.source,'UnregisterScoreObservers')
        failed=function_body(self.source,'OnObjectiveFailed')
        self.assertIn("'MissionObjectiveMarkedFailed'", registration)
        self.assertIn("'MissionObjectiveMarkedFailed'", cleanup)
        self.assertIn('XComGameState_ObjectivesList(EventData)',failed)
        self.assertIn('SeqAct_DisplayMissionObjective(EventSource)',failed)
        self.assertIn('Info.ShowFailed && Info.ShowCheckBox && !Info.HideInTactical',failed)
        self.assertIn('FailedObjectiveIDs.Find(ObjectiveID)',failed)
        self.assertIn('FailedObjectiveIDs.AddItem(ObjectiveID)',failed)
        self.assertIn('Emit("objective_failed"',failed)
        # A displayed failed checkbox contains no required/optional flag.
        self.assertIn('|critical=false|criticality=unknown|',failed)
        self.assertNotIn('|critical=true|',failed)
        challenge=function_body(self.source,'OnChallengeObjectiveFailed')
        self.assertIn('challenge_native_event',challenge)
        self.assertIn('|critical=true',challenge)
        self.assertIn('OnChallengeObjectiveFailed, ELD_Immediate, 1000',registration)
        self.assertIn('return ELR_NoInterrupt;',challenge)
        self.assertNotIn('ELR_InterruptEvent',challenge)
        self.assertNotIn('GameState == none',challenge)
        self.assertIn('FailedObjectiveIDs.Find(ObjectiveID)',challenge)
        self.assertIn('Emit("objective_failed"',challenge)
        self.assertIn("'ChallengeObjectiveFailed'",registration)
        self.assertIn("'ChallengeObjectiveFailed'",cleanup)
        for forbidden in ('FailBattle(', 'SubmitGameState(', 'ModifyStateObject('):
            self.assertNotIn(forbidden,failed)
            self.assertNotIn(forbidden,challenge)

    def test_relay_scan_is_scoped_and_one_per_real_player_turn(self):
        observe=function_body(self.source,'Observe')
        scan=function_body(self.source,'RecordSabotageRelayCandidates')
        self.assertIn('RecordedMissionType == "SabotageTransmitter"',observe)
        self.assertIn('PlayerState.PlayerTurnCount != LastRelayScanTurn',observe)
        self.assertIn('RecordSabotageRelayCandidates(LastRelayScanTurn)',observe)
        self.assertIn('LastRelayScanTurn = -1;', function_body(self.source,'Start'))
        self.assertIn('RecordedMissionType != "SabotageTransmitter"',scan)
        self.assertIn('classification=unverified',scan)
        self.assertIn('type=unverified_destructible',scan)

    def test_native_attack_targets_and_relay_candidates_are_not_guessed(self):
        scan=function_body(self.source,'RecordSabotageRelayCandidates')
        for part in ("IterateByClassType(class'XComGameState_Destructible'",
                     'TargetObject.Health <= 0',
                     'TargetObject.bRemoved',
                     'Soldier.bRemovedFromPlay',
                     'TargetObject.IsTargetable(eTeam_XCom)',
                     'IsTileOutOfRange(TargetObject.TileLocation)',
                     'GetGameRulesCache_Unit(Soldier.GetReference(), UnitCache)',
                     "default.AttackAbilities.Find(",
                     'Action.AvailableTargets',
                     'Action.AvailableCode',
                     'Emit("relay_action_target"',
                     '"|native_available=" $ (Action.AvailableCode == \'AA_Success\')',
                     'Ability.OwnerStateObject.ObjectID != Soldier.ObjectID',
                     'class\'Helpers\'.static.IsObjectiveTarget(TargetObject.ObjectID)',
                     'Soldier.TargetIsEnemy(TargetObject.ObjectID)'):
            self.assertIn(part,scan)
        for bound in ('ObjectsChecked > 256', 'Shown >= 20', 'UnitsScanned > 256', 'UnitsChecked >= 8',
                      'ActionsChecked >= 128', 'TargetsChecked >= 192'):
            self.assertIn(bound,scan)
        for forbidden in ('CreateNewGameState(', 'SubmitGameState(', 'ModifyStateObject(',
                          'ActivateAbility(', 'CompleteObjective(', 'SetRemainingTurns('):
            self.assertNotIn(forbidden,scan)


    def test_failure_observers_and_relay_scan_stay_in_original_mission_epoch(self):
        match = load_uc_function(FILE, 'RecordingEpochMatches')
        self.assertTrue(match(True, 2, 2, 50, 50, 91, 91))
        self.assertTrue(match(True, 2, 2, 50, 80, 91, 91))
        # Same mission type is insufficient after world replacement, new start
        # state, history rewind or a different battle in the same world.
        for args in ((False, 2, 2, 50, 80, 91, 91),
                     (True, 2, 3, 50, 80, 91, 91),
                     (True, 2, 2, 50, 49, 91, 91),
                     (True, 2, 2, 5000, 3000, 91, 91),
                     (True, 2, 2, 50, 80, 91, 92),
                     (True, 2, 2, 50, 80, 0, 0)):
            with self.subTest(args=args):
                self.assertFalse(match(*args))
        guard = function_body(self.source, 'IsRecordingMission')
        for token in ('RecordingEpochMatches(RecordedHistory == `XCOMHISTORY,',
                      'RecordedStartStateIndex, `XCOMHISTORY.FindStartStateIndex()',
                      'Max(RecordingStartHistory, LastObservedMissionHistory), CurrentHistory',
                      'RecordedBattleID, BattleData.ObjectID',
                      'BattleData.MapData.ActiveMission.sType != RecordedMissionType',
                      'bRecordingEpochInvalid = true;',
                      'LastObservedMissionHistory = CurrentHistory;'):
            self.assertIn(token,guard)
        start = function_body(self.source, 'Start')
        for token in ('RecordedHistory = `XCOMHISTORY;',
                      'RecordedStartStateIndex = RecordedHistory.FindStartStateIndex();',
                      'RecordingStartHistory = HistoryCursor;',
                      'LastObservedMissionHistory = HistoryCursor;',
                      'RecordedBattleID = BattleData.ObjectID;'):
            self.assertIn(token,start)
        self.assertIn('bRecordingEpochInvalid', guard.split('BattleData =', 1)[0])
        self.assertNotIn('bRecordingEpochInvalid = false', guard)
        self.assertNotIn('LastObservedMissionHistory =', guard.split('return false;', 2)[0])
        for name in ('Observe','OnObjectiveFailed','OnChallengeObjectiveFailed','RecordSabotageRelayCandidates'):
            self.assertIn('!IsRecordingMission()', function_body(self.source,name))
        hud = function_body(self.source, 'RecordHUDScore')
        self.assertLess(hud.index('!IsRecordingMission()'), hud.index('LastHUDScore ='))
        finish = function_body(self.source, 'Finish')
        lost = finish.split('if (!IsRecordingMission())',1)[1].split('if (`XCOMHISTORY != none)',1)[0]
        self.assertIn('Emit("recording_context_lost"',lost)
        self.assertIn('UnregisterScoreObservers();',lost)
        self.assertIn('bFinished = true;',lost)
        self.assertNotIn('Emit("end"',lost)
        self.assertNotIn('BattleData =',lost)


    def test_scanned_unit_cap_precedes_filters_and_archetype_is_real(self):
        scan = function_body(self.source,'RecordSabotageRelayCandidates')
        unit_loop = scan.split("IterateByClassType(class'XComGameState_Unit'",1)[1]
        self.assertLess(unit_loop.index('++UnitsScanned > 256'),
                        unit_loop.index('Soldier == none'))
        self.assertLess(unit_loop.index('++UnitsScanned > 256'),
                        unit_loop.index('++UnitsChecked'))
        self.assertIn('Visualizer.ObjectID != TargetObject.ObjectID',scan)
        self.assertIn('Visualizer.bDeleteMe',scan)
        self.assertIn('Safe(string(Visualizer.Class))',scan)
        self.assertIn('Safe(PathName(Visualizer.ObjectArchetype))',scan)
        self.assertIn('|actor_class=unknown|archetype=unknown',scan)
        self.assertIn('"|units_scanned=" $ Min(UnitsScanned, 256)',scan)


if __name__=='__main__':
    unittest.main()
