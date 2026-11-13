"""Revealed-ranged current AIGroup focus (stage 1 of #31).

Numeric policy helpers execute actual UnrealScript text. Structural tests
ensure current native target eligibility, safety and mission separation.
These tests do not demonstrate legal in-game reaction shots or victory.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
FOCUS = CLASSES/'APX_RevealedFocus.uc'
CTRL = CLASSES/'APX_Controller.uc'
COMBAT = CLASSES/'APX_CombatPlanner.uc'
MISSION = CLASSES/'APX_MissionPlanner.uc'
INI = ROOT/'AutoplayXCom2/Config/XComAutoplayXCom2.ini'


class RevealedGroupFocusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.focus = FOCUS.read_text(encoding='utf-8-sig')
        cls.ctrl = CTRL.read_text(encoding='utf-8-sig')
        cls.combat = COMBAT.read_text(encoding='utf-8-sig')
        cls.mission = MISSION.read_text(encoding='utf-8-sig')
        cls.can = staticmethod(load_uc_function(FOCUS, 'CanFocus'))
        cls.pod = staticmethod(load_uc_function(FOCUS, 'PodPriority'))
        cls.member = staticmethod(load_uc_function(FOCUS, 'MemberPriority'))
        cls.shot = staticmethod(load_uc_function(FOCUS, 'LegalShotFocusBonus'))
        cls.position = staticmethod(load_uc_function(FOCUS, 'FocusPositionBonus'))

    def test_no_focus_while_hidden_under_timer_or_urgent_rescue(self):
        self.assertTrue(self.can(True,True,False,False,False,4))
        for args in [
            (False,True,False,False,False,4),
            (True,False,False,False,False,4),
            (True,True,True,False,False,4),
            (True,True,False,True,False,4),
            (True,True,False,False,True,4),
            (True,True,False,False,False,1),
        ]:
            with self.subTest(args=args):
                self.assertFalse(self.can(*args))

    def test_previous_pod_can_be_retained_but_nearer_threat_can_replace(self):
        self.assertGreater(self.pod(12,2,True), self.pod(12,2,False))
        self.assertGreater(self.pod(2,2,False), self.pod(25,2,True))
        self.assertLess(self.pod(3,0,True),-9999)
        self.assertLess(self.pod(-1,3,False),-9999)
        self.assertGreater(self.pod(8,2,False),self.pod(8,7,False))

    def test_wounded_visible_enemy_wins_close_primary_selection(self):
        self.assertGreater(self.member(10,0.2),self.member(10,1.0))
        self.assertGreater(self.member(7,1.0),self.member(13,0.1))
        self.assertLess(self.member(-1,1.0),-9999)

    def test_only_native_legal_non_melee_basic_shots_get_bonus(self):
        for args in [(False,True,True,True,0.1),
                     (True,True,False,True,0.1),
                     (True,True,True,False,0.1)]:
            self.assertEqual(self.shot(*args),0)
        self.assertGreater(self.shot(True,True,True,True,0.2),
                           self.shot(True,False,True,True,0.2))
        self.assertGreater(self.shot(True,True,True,True,0.2),
                           self.shot(True,True,True,True,1.0))
        self.assertLessEqual(self.shot(True,True,True,True,0.0),22.0)

    def test_focused_route_bonus_only_for_constructive_advance(self):
        self.assertEqual(self.position(10,10),0)
        self.assertEqual(self.position(10,11),0)
        self.assertEqual(self.position(10,9.8),0)
        self.assertEqual(self.position(-1,0),0)
        self.assertEqual(self.position(10,4),7)
        self.assertGreater(self.position(10,7),0)

    def test_group_selection_bounded_read_only_and_only_player_visible(self):
        choose=function_body(self.focus,'SelectContact')
        for required in (
            "EnableFullIntel", "GetLocalClientPlayerObjectID()",
            "MaxFriendlyStatesPerDecision", "MaxMembersPerDecision",
            "MaxGroupsPerDecision", "MaxSquadSize",
            "GetAllVisibleEnemiesForPlayer(",
            "PlayerVisibleEnemies.Find('ObjectID', Enemy.ObjectID)",
            "m_arrMembers", "SeenIDs.Find(",
            "Friend.IsBleedingOut()", "Friend.IsMeleeOnly()",
            "Group.ObjectID == PreviousGroupID",
            "Enemy.IsAlive()", "Representative.IsEnemyUnit(Enemy)",
            "IsReclaimableControlledSquadmate(",
        ):
            with self.subTest(required=required):
                self.assertIn(required,choose)
        for forbidden in (
            "IsEngaged(", "HasAbsoluteKnowledge(", "CurrentTargetLocation",
            "GetTotalScore(", "ModifyStateObject(", "CreateNewGameState(",
            "SubmitGameState(", "Rand(", "GetActionPoints(", "GetAmmo(",
        ):
            self.assertNotIn(forbidden,self.focus)

    def test_one_group_snapshot_per_decision_with_epoch_and_off_reset(self):
        decision=function_body(self.ctrl,'MakeDecision')
        stop=function_body(self.ctrl,'StopAutoplay')
        self.assertEqual(decision.count("class'APX_RevealedFocus'.static.SelectContact("),1)
        self.assertIn("ResetRangedFocus();",stop)
        for required in ("RangedFocusHistory != `XCOMHISTORY",
                         "RangedFocusStartIndex != FocusStartIndex",
                         "RangedFocusBattleID != FocusBattle.ObjectID",
                         "RangedFocusPlayerID != PlayerRef.ObjectID",
                         "FocusHistoryIndex < RangedFocusLastHistory",
                         "MissionRecorder.Marker(\"revealed_focus\""):
            self.assertIn(required,decision)
        self.assertLess(decision.index("SelectContact("),
                        decision.index("class'APX_CombatPlanner'.static.ChooseAction("))
        self.assertIn('RangedTargetID, bRangedFocusGoal',decision)

    def test_deadlines_plant_and_berserker_focus_not_overridden(self):
        goal=function_body(self.mission,'FindGoal')
        move=function_body(self.mission,'ChooseMove')
        self.assertLess(goal.index("ShouldPrioritizeBerserkerSabotage("),
                        goal.index("if (bRangedFocusGoal && RangedFocusTargetID"))
        self.assertLess(goal.index("if (EvacZone != none && ShouldEvacuate(UnitState))"),
                        goal.index("if (bRangedFocusGoal && RangedFocusTargetID"))
        for required in ("Goal.bImmediateThreats", "!HasBleedingSquadmate(UnitState)",
                         "!HasActiveMissionDeadline()", "!UnitState.IsConcealed()",
                         "!UnitState.IsMeleeOnly()",
                         "VisibleEnemies.Find('ObjectID', RangedFocusTargetID)",
                         "RangedFocusTargetID, bRangedFocusGoal"):
            self.assertIn(required,goal+move)
        self.assertIn('HasBlockingHazard(UnitState, CandidatePath[PathIndex])',move)
        self.assertIn('IsSupportedAdvanceStep(StartSupport,',move)
        self.assertIn('FocusPositionBonus(',move)
        self.assertLess(move.index('PositionScore(UnitState, Tile, GoalTile, bCombatGoal,'),
                        move.index('FocusPositionBonus('))

    def test_native_legal_actions_before_soft_focus_and_no_aoe_bonus(self):
        body=function_body(self.combat,'ChooseAction')
        self.assertIn("Candidate.AvailableCode != 'AA_Success'",body)
        self.assertIn('AdditionalTargetsAreSafe(',body)
        self.assertLess(body.index('HasRequiredMeleePath(UnitState, TargetUnit,'),
                        body.index("class'APX_RevealedFocus'.static.LegalShotFocusBonus("))
        for ability in ("'StandardShot'", "'PistolStandardShot'", "'SniperStandardFire'"):
            self.assertIn(ability,body)
        self.assertIn('CandidateScore > 5.0',body)
        self.assertIn('TargetUnit.ObjectID == RangedFocusTargetID',body)

    def test_opt_out_and_finite_scan_defaults(self):
        ini=INI.read_text()
        for entry in (
            'EnableRevealedGroupFocus=true','MaxGroupsPerDecision=24',
            'MaxMembersPerDecision=128','MaxFriendlyStatesPerDecision=128',
            'MaxSquadSize=12',
        ):
            self.assertIn(entry,ini)


if __name__=='__main__':
    unittest.main()
