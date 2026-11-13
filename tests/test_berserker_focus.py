"""Mission-scoped Blood Killer focus, timer slack and native-legal attack contracts.

Pure policies execute the actual numeric UnrealScript helper bodies via
uc_math. Source contracts check surrounding game-state safety boundaries.
Neither test mode compiles WOTC UC or validates native combat outcomes.
"""
from pathlib import Path
import os
import unittest

from uc_math import load_uc_function
from test_ui_gating import CHECKS, function_body

ROOT=Path(__file__).resolve().parents[1]
CLASSES=ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes'
FOCUS=CLASSES/'APX_BerserkerFocus.uc'
CONTROLLER=CLASSES/'APX_Controller.uc'
MISSION=CLASSES/'APX_MissionPlanner.uc'
COMBAT=CLASSES/'APX_CombatPlanner.uc'
INI=ROOT/'AutoplayXCom2/Config/XComAutoplayXCom2.ini'


class BloodKillerFocusContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.focus=FOCUS.read_text()
        cls.control=CONTROLLER.read_text()
        cls.mission=MISSION.read_text()
        cls.combat=COMBAT.read_text()
        cls.group=staticmethod(load_uc_function(FOCUS,'GroupPriority'))
        cls.phase=staticmethod(load_uc_function(FOCUS,'ShouldUseContactGoal'))
        cls.attack=staticmethod(load_uc_function(FOCUS,'FocusAttackBonus'))
        cls.relay=staticmethod(load_uc_function(FOCUS,'ContactRelayScore'))

    def test_opening_is_bounded_by_native_timer_turn_and_distance(self):
        self.assertTrue(self.phase(True,False,6,1,9,5,2,4,18))
        self.assertTrue(self.phase(True,False,4,2,18,3,2,4,18))
        # Once the deadline gets close, retain the already working X4/relay.
        for args in [
            (False,False,6,1,9,5,2,4,18),
            (True,False,-1,1,9,5,2,4,18),
            (True,False,3,1,9,5,2,4,18),
            (True,False,6,3,9,5,2,4,18),
            (True,False,6,1,19,5,2,4,18),
            (True,False,6,1,9,2,2,4,18),
            (True,False,6,0,9,5,2,4,18),
        ]:
            with self.subTest(args=args):
                self.assertFalse(self.phase(*args))

    def test_native_sweep_reuses_contact_even_after_timer_runs_out(self):
        self.assertTrue(self.phase(True,True,-1,14,33,2,2,4,18))
        self.assertFalse(self.phase(True,True,4,14,33,0,2,4,18))
        self.assertFalse(self.phase(False,True,5,2,8,5,2,4,18))

    def test_inactive_contact_cannot_outscore_the_urgent_objective_with_sweep_bonus(self):
        # Regression: the selected group ID survives in diagnostics while the
        # objective phase is active. It must not authorize a +16 sweep bonus.
        decide=function_body(self.control,'MakeDecision')
        self.assertIn('(bFocusedGoal ? FocusTargetID : 0), bOpeningContact',decide)
        active=self.phase(True,False,3,3,9,5,2,4,18)
        self.assertFalse(active)
        self.assertEqual(self.attack(active,False,1.0,1.0),0)

    def test_retained_group_and_nearer_threat_can_both_win(self):
        self.assertGreater(self.group(12,3,True),self.group(12,3,False))
        self.assertGreater(self.group(4,3,False),self.group(22,3,True))
        self.assertGreater(self.group(8,2,False),self.group(8,6,False))
        self.assertLess(self.group(-1,2,False),-9999)
        self.assertLess(self.group(2,0,False),-9999)

    def test_legal_melee_focus_is_soft_and_not_a_sacrifice_order(self):
        self.assertEqual(self.attack(False,True,1.0,0.1),0)
        self.assertEqual(self.attack(True,True,0.3,0.1),0)
        self.assertEqual(self.attack(True,False,0.5,0.1),0)
        self.assertGreater(self.attack(True,True,1.0,0.2),
                           self.attack(True,False,1.0,0.2))
        self.assertGreater(self.attack(True,True,1.0,0.2),
                           self.attack(True,True,1.0,1.0))
        self.assertLessEqual(self.attack(True,True,1.0,0),48)
        self.assertLessEqual(self.attack(True,False,1.0,0),26)

    def test_originally_local_berserker_never_becomes_shared_enemy_contact(self):
        # Run the actual UnrealScript policy, not a Python reimplementation.
        exclude = load_uc_function(FOCUS, 'ExcludeFormerLocalBerserker')
        self.assertTrue(exclude(True, True, True))
        self.assertTrue(exclude(True, False, False))
        self.assertFalse(exclude(True, True, False))
        self.assertFalse(exclude(False, True, True))
        self.assertFalse(exclude(False, False, False))

    def test_original_owner_filter_is_only_read_only_berserker_pod_selection(self):
        guard = function_body(self.focus, 'WasOriginallyLocalBerserker')
        select = function_body(self.focus, 'SelectSquadContact')
        self.assertIn("UnitState.GetMyTemplateName() != 'BerserkerMP'", guard)
        self.assertIn('GetGameStateForObjectID(UnitState.ObjectID,, StartIndex)', guard)
        self.assertNotIn('GetOriginalGameStateRevision(UnitState.ObjectID)', guard)
        self.assertIn('OriginalUnit.GetTeam() == eTeam_XCom', guard)
        self.assertIn('OriginalUnit.GetAssociatedPlayerID() == PlayerID', guard)
        self.assertIn("OriginalUnit.GetMyTemplateName() == 'BerserkerMP'", guard)
        self.assertIn('ExcludeFormerLocalBerserker(true, bKnown, bLocal)', guard)
        self.assertIn('WasOriginallyLocalBerserker(Enemy, PlayerID)', select)
        self.assertLess(select.index('WasOriginallyLocalBerserker(Enemy, PlayerID)'),
                        select.index('++Members;'))
        # Uncertain original ownership only drops a focus goal, never an
        # otherwise native-legal punch on a truly hostile unit.
        self.assertNotIn('WasOriginallyLocalBerserker(', self.combat)
        self.assertNotIn('WasOriginallyLocalBerserker(', self.mission)
        for bad in ('ModifyStateObject(', 'CreateNewGameState(',
                    'SubmitGameState(', 'IsEngaged(', 'GetTotalScore('):
            self.assertNotIn(bad, guard)

    def test_start_owner_lookup_rejects_missing_or_non_tactical_start(self):
        guard = function_body(self.focus, 'WasOriginallyLocalBerserker')
        # Regression: -1 is the native current-state sentinel, so an absent
        # start cannot silently become evidence that a former ally was hostile.
        self.assertRegex(guard, r'if \(StartIndex < 0\)\s*return true;')
        self.assertRegex(guard, r'if \(StartState == none\)\s*return true;')
        self.assertRegex(guard, r'if \(StartContext == none \|\| StartContext.GameRuleType != eGameRule_TacticalGameStart\)\s*return true;')
        read = guard.index('GetGameStateForObjectID(UnitState.ObjectID,, StartIndex)')
        self.assertLess(guard.index('StartIndex < 0'), read)
        self.assertLess(guard.index('StartState == none'), read)
        self.assertLess(guard.index('StartContext.GameRuleType != eGameRule_TacticalGameStart'), read)
        self.assertIn('OriginalUnit.GetAssociatedPlayerID() > 0', guard)

    def test_relay_is_always_legal_if_stock_cache_says_so(self):
        self.assertEqual(self.relay(105,False),105)
        self.assertEqual(self.relay(105,True),26)
        self.assertEqual(self.relay(12,True),12)
        self.assertEqual(self.relay(-10000,True),-10000)
        self.assertEqual(self.relay(0,True),0)

    def test_restricted_active_group_snapshot_and_real_timer_not_enemy_intent(self):
        select=function_body(self.focus,'SelectSquadContact')
        for phrase in ("EnableBerserkerGroupFocus","EnableFullIntel",
                       "Friend.GetMyTemplateName() != 'BerserkerMP'",
                       "GetAssociatedPlayerID()", "m_arrMembers", 
                       "MaxGroupsPerDecision","MaxMemberRefsPerDecision",
                       "MaxFriendlyUnitsPerDecision","GroupPriority(",
                       "Enemy.IsAlive()", "Enemy.IsIncapacitated()",
                       "Representative.IsEnemyUnit(Enemy)",
                       "Group.ObjectID == PreviousGroupID"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase,select)
        timer=function_body(self.focus,'ReadActiveTimerTurns')
        for phrase in ("XComGameState_UITimer","TimerState.TimerValue",
                       "TimerState.ShouldShow", "TimerState.IsSuspended()"):
            self.assertIn(phrase,timer)
        for prohibited in ("IsEngaged(", "HasAbsoluteKnowledge(", "RollFor",
                           "Rand(", ".CurrentActionPoints", ".Ammo",
                           ".CurrentTargetLocation", "ModifyStateObject(",
                           "CreateNewGameState(", "SubmitGameState("):
            self.assertNotIn(prohibited,self.focus)

    def test_squad_focus_is_scope_reset_and_observed_once_per_decision(self):
        decide=function_body(self.control,'MakeDecision')
        stop=function_body(self.control,'StopAutoplay')
        self.assertIn("ResetBerserkerFocus();",stop)
        self.assertIn('BerserkerFocusHistory != `XCOMHISTORY',decide)
        self.assertIn('BerserkerFocusStartIndex != FocusStartIndex',decide)
        self.assertIn('BerserkerFocusBattleID != FocusBattle.ObjectID',decide)
        self.assertIn('FocusHistoryIndex < BerserkerFocusLastHistory',decide)
        self.assertEqual(decide.count('SelectSquadContact('),1)
        self.assertIn('MissionRecorder.Marker("berserker_focus",',decide)
        self.assertLess(decide.index("SelectSquadContact("),
                        decide.index("class'APX_CombatPlanner'.static.ChooseAction("))
        self.assertLess(decide.index("class'APX_CombatPlanner'.static.ChooseAction("),
                        decide.index("class'APX_MissionPlanner'.static.ChooseMove("))
        self.assertIn('(bFocusedGoal ? FocusTargetID : 0), bOpeningContact',decide)
        self.assertIn('FocusTargetID, bFocusedGoal',decide)

    def test_all_inspected_units_count_and_partial_centroid_is_rejected(self):
        select=function_body(self.focus,'SelectSquadContact')
        scan=select[select.index("IterateByClassType(class'XComGameState_Unit'"):
                    select.index('CenterX /=')]
        self.assertRegex(scan,r'if \(\+\+UnitsChecked > Clamp\(default.MaxUnitStatesPerDecision, 16, 256\)\)\s*return false;')
        self.assertLess(scan.index('++UnitsChecked'),scan.index('if (Friend == none'))
        self.assertRegex(scan,r'if \(LivingFriendlies >= Clamp\(default.MaxFriendlyUnitsPerDecision, 1, 16\)\)\s*return false;')
        self.assertNotIn('break;',scan)

    def test_objective_and_native_sweep_have_scoped_contact_exception(self):
        goal=function_body(self.mission,'FindGoal')
        move=function_body(self.mission,'ChooseMove')
        self.assertIn('bBerserkerSweep || bBerserkerFocusGoal',goal)
        self.assertIn("BattleData.MapData.ActiveMission.sType == \"SabotageTransmitter\"",goal)
        self.assertIn("UnitState.GetMyTemplateName() == 'BerserkerMP'",goal)
        self.assertIn('VisibleEnemies.Find(\'ObjectID\', BerserkerFocusTargetID)',goal)
        self.assertLess(goal.index('if (EvacZone != none && ShouldEvacuate(UnitState))'),
                        goal.index('bBerserkerSweep || bBerserkerFocusGoal'))
        self.assertIn('FindBerserkerSabotageGoal(UnitState, BattleData,',goal)
        self.assertLess(goal.index('bBerserkerSweep || bBerserkerFocusGoal'),
                        goal.index('Goal.bBerserkerSabotageGoal = true;'))
        self.assertIn('BerserkerFocusTargetID, bBerserkerFocusGoal',move)
        # All the original path hazards, last-AP and scoring gates stay.
        self.assertIn('HasBlockingHazard(UnitState, CandidatePath[PathIndex])',move)
        self.assertIn('if (!Goal.bImmediateThreats && !bRoutineRoute)',move)
        self.assertIn('bSabotageRush = Goal.bBerserkerSabotageGoal',move)

    def test_native_attack_safety_precedes_any_focus_bonus(self):
        choose=function_body(self.combat,'ChooseAction')
        self.assertLess(choose.index('HasRequiredMeleePath(UnitState, TargetUnit,'),
                        choose.index('FocusAttackBonus('))
        self.assertIn("Candidate.AvailableCode != 'AA_Success'",choose)
        self.assertIn('AdditionalTargetsAreSafe(',choose)
        self.assertIn('ScoreObjectiveAttack(UnitState, Ability,',choose)
        self.assertLess(choose.index('ScoreObjectiveAttack(UnitState, Ability,'),
                        choose.index('ContactRelayScore('))
        self.assertIn('IsTransmitterRelay(ObjectiveTarget)',choose)

    def test_opt_out_and_static_limits_are_documented(self):
        ini=INI.read_text()
        for setting in ('EnableBerserkerGroupFocus=true',
                        'OpeningContactTurns=2',
                        'MinimumContactTimerTurns=4',
                        'MaximumOpeningContactDistance=18.0',
                        'MaxGroupsPerDecision=24',
                        'MaxMemberRefsPerDecision=128',
                        'MaxFriendlyUnitsPerDecision=12',
                        'MaxUnitStatesPerDecision=128'):
            self.assertIn(setting,ini)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'Private WOTC SDK required for native type contracts')
class BloodKillerFocusSDKContracts(unittest.TestCase):
    def test_public_group_member_and_native_timer_fields_exist(self):
        sdk=CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT']))/'XComGame/Classes'
        timer=(sdk/'XComGameState_UITimer.uc').read_text(encoding='utf-8-sig')
        group=(sdk/'XComGameState_AIGroup.uc').read_text(encoding='utf-8-sig')
        unit=(sdk/'XComGameState_Unit.uc').read_text(encoding='utf-8-sig')
        history=(sdk/'XComGameStateHistory.uc').read_text(encoding='utf-8-sig')
        context=(sdk/'XComGameStateContext_TacticalGameRule.uc').read_text(encoding='utf-8-sig')
        self.assertIn('var int TimerValue;',timer)
        self.assertIn('var bool IsTimer;',timer)
        self.assertIn('function bool IsSuspended(',timer)
        self.assertIn('m_arrMembers',group)
        self.assertIn('GetAssociatedPlayerID(',unit)
        self.assertIn('native final function int FindStartStateIndex();',history)
        self.assertIn('native final function XComGameState GetGameStateFromHistory(',history)
        self.assertIn('GetGameStateForObjectID(int ObjectID, optional EGameStateReturnType DesiredReturnType=eReturnType_Reference, optional int HistoryIndex=-1)',history)
        self.assertIn('eGameRule_TacticalGameStart',context)


if __name__=='__main__':
    unittest.main()
