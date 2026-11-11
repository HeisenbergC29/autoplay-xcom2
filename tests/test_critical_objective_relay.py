"""Read-only native failure and transmitter-target discovery contracts.

Source checks do not replace a Windows WOTC SDK compile or gameplay. A
'destructible candidate' is not presumed to be a power relay until verified.
"""
from pathlib import Path
import unittest
from test_ui_gating import function_body

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
        self.assertIn('Info.ShowFailed && !Info.HideInTactical',failed)
        self.assertIn('FailedObjectiveIDs.Find(ObjectiveID)',failed)
        self.assertIn('FailedObjectiveIDs.AddItem(ObjectiveID)',failed)
        self.assertIn('Emit("objective_failed"',failed)
        self.assertIn('|critical=true|',failed)
        challenge=function_body(self.source,'OnChallengeObjectiveFailed')
        self.assertIn('challenge_native_event',challenge)
        self.assertIn('FailedObjectiveIDs.Find(ObjectiveID)',challenge)
        self.assertIn('Emit("objective_failed"',challenge)
        self.assertIn("'ChallengeObjectiveFailed'",registration)
        self.assertIn("'ChallengeObjectiveFailed'",cleanup)
        for forbidden in ('FailBattle(', 'SubmitGameState(', 'ModifyStateObject('):
            self.assertNotIn(forbidden,failed)

    def test_relay_scan_is_scoped_and_one_per_real_player_turn(self):
        observe=function_body(self.source,'Observe')
        scan=function_body(self.source,'RecordSabotageRelayCandidates')
        self.assertIn('RecordedMissionType == "SabotageTransmitter"',observe)
        self.assertIn('PlayerState.PlayerTurnCount != LastRelayScanTurn',observe)
        self.assertIn('RecordSabotageRelayCandidates(LastRelayScanTurn)',observe)
        self.assertIn('RecordedMissionType != "SabotageTransmitter"',scan)
        self.assertIn('classification=unverified',scan)
        self.assertIn('type=unverified_destructible',scan)

    def test_native_attack_targets_and_relay_candidates_are_not_guessed(self):
        scan=function_body(self.source,'RecordSabotageRelayCandidates')
        for part in ("IterateByClassType(class'XComGameState_Destructible'",
                     'TargetObject.Health <= 0',
                     'TargetObject.IsTargetable(eTeam_XCom)',
                     'IsTileOutOfRange(TargetObject.TileLocation)',
                     'GetGameRulesCache_Unit(Soldier.GetReference(), UnitCache)',
                     "default.AttackAbilities.Find(",
                     'Action.AvailableTargets',
                     'Action.AvailableCode',
                     'Ability.OwnerStateObject.ObjectID != Soldier.ObjectID',
                     'class\'Helpers\'.static.IsObjectiveTarget(TargetObject.ObjectID)',
                     'Soldier.TargetIsEnemy(TargetObject.ObjectID)'):
            self.assertIn(part,scan)
        for bound in ('ObjectsChecked > 256', 'Shown >= 20', 'UnitsChecked >= 8',
                      'ActionsChecked >= 128', 'TargetsChecked >= 192'):
            self.assertIn(bound,scan)
        for forbidden in ('CreateNewGameState(', 'SubmitGameState(', 'ModifyStateObject(',
                          'ActivateAbility(', 'CompleteObjective(', 'SetRemainingTurns('):
            self.assertNotIn(forbidden,scan)


if __name__=='__main__':
    unittest.main()
