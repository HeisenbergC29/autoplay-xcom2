"""No speculated melee/contact: bounded current native AA-ready opportunity.

These tests exercise the actual UC policy helper and source contracts.
They cannot prove WOTC compilation or a changed action sequence in game.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT/'AutoplayXCom2/Src/AutoplayXCom2/Classes'
FOCUS = CLASSES/'APX_BerserkerFocus.uc'
CTRL = CLASSES/'APX_Controller.uc'
COMBAT = CLASSES/'APX_CombatPlanner.uc'
MISSION = CLASSES/'APX_MissionPlanner.uc'

class NativeOpeningOpportunityContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.focus = FOCUS.read_text(encoding='utf-8-sig')
        cls.ctrl = CTRL.read_text(encoding='utf-8-sig')
        cls.combat = COMBAT.read_text(encoding='utf-8-sig')
        cls.mission = MISSION.read_text(encoding='utf-8-sig')
        cls.native = staticmethod(load_uc_function(FOCUS,'CanPreferNativeOpeningStrike'))
        cls.old = staticmethod(load_uc_function(FOCUS,'ShouldUseContactGoal'))

    def test_real_native_strike_is_exception_to_distance_only(self):
        self.assertTrue(self.native(True,False,4,1,5,4,2,True,False))
        self.assertTrue(self.native(True,False,4,2,3,4,2,True,False))
        # Existing speculative movement remains prohibited at 18.42 tiles.
        self.assertFalse(self.old(True,False,4,1,18.42,5,2,4,18))
        self.assertTrue(self.old(True,False,4,1,17.5,5,2,4,18))

    def test_unknown_or_tight_native_timer_never_spends_early_attack_budget(self):
        for x in [
            (False,False,4,1,5,4,2,True,False),
            (True,True,4,1,5,4,2,True,False),
            (True,False,-1,1,5,4,2,True,False),
            (True,False,3,1,5,4,2,True,False),
            (True,False,4,0,5,4,2,True,False),
            (True,False,4,3,5,4,2,True,False),
            (True,False,4,1,2,4,2,True,False),
            (True,False,4,1,5,4,2,False,False),
            (True,False,4,1,5,4,2,True,True),
        ]:
            with self.subTest(x=x):
                self.assertFalse(self.native(*x))

    def test_only_real_current_owned_visible_safe_melee_actions_qualify(self):
        readiness = function_body(self.focus, 'FindNativeOpeningStrike')
        for required in (
            "GetGameRulesCache_Unit(Friend.GetReference(), Cache)",
            "Candidate.AvailableCode != 'AA_Success'",
            "Candidate.bInputTriggered",
            "Candidate.bFreeAim",
            "Ability.OwnerStateObject.ObjectID != Friend.ObjectID",
            "Ability.GetMyTemplateName() != 'DevastatingPunchMP'",
            "Candidate.AvailableTargets(NativeTarget)",
            "NativeTarget.PrimaryTarget.ObjectID != FocusTargetID",
            "GetAllVisibleEnemiesForPlayer(",
            "VisibleEnemies.Find('ObjectID', FocusTargetID)",
            "IsVisibleHostile(",
            "AdditionalTargetsAreSafe(",
            "HasRequiredMeleePath(",
            "ScoreAttack(",
            "Value > 5.0",
            "Friend.GetMyTemplateName() != 'BerserkerMP'",
            "Friend.IsEnemyUnit(TargetUnit)",
            "IsReclaimableControlledSquadmate(",
            "Friend.GetCurrentStat(eStat_HP)",
            "MaxUnitStatesPerDecision",
            "ActionsVisited > 96",
            "TargetsVisited > 24",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readiness)
        for bad in ("ModifyStateObject(", "CreateNewGameState(",
                    "SubmitGameState(", "IsEngaged(", "HasAbsoluteKnowledge(",
                    "CurrentActionPoints", "Rand(", "GetTotalScore("):
            self.assertNotIn(bad, readiness)

    def test_no_new_contact_route_or_relay_suppression(self):
        decide=function_body(self.ctrl,'MakeDecision')
        choose=function_body(self.combat,'ChooseAction')
        self.assertIn('NativeOpeningStrikesThisTurn = 0;',decide)
        self.assertIn('BerserkerFocusHistory != `XCOMHISTORY',decide)
        self.assertIn('FocusHistoryIndex < BerserkerFocusLastHistory',decide)
        self.assertLess(decide.index('FocusHistoryIndex < BerserkerFocusLastHistory'),
                        decide.index('NativeOpeningStrikesThisTurn = 0;',
                                     decide.index('BerserkerFocusHistory != `XCOMHISTORY')))
        self.assertIn('NativeOpeningStrikesThisTurn >= 1',decide)
        self.assertIn('!bFocusedGoal && FocusPlantPhase == 0',decide)
        self.assertIn("static.CanPreferNativeOpeningStrike(",decide)
        self.assertIn("static.FindNativeOpeningStrike(",decide)
        self.assertIn('"native_strike_ready=" $ string(bNativeStrikeOnly)',decide)
        self.assertIn('UnitState.ObjectID == NativeStrikeAttackerID',decide)
        self.assertIn('++NativeOpeningStrikesThisTurn;',decide)
        self.assertIn("ChosenTargetID == FocusTargetID && Ability != none",decide)
        self.assertIn("Ability.GetMyTemplateName() == 'DevastatingPunchMP'",decide)
        self.assertIn('bNativeBerserkerStrikeOnly',choose)
        self.assertIn('bBerserkerOpeningContact || bNativeBerserkerStrikeOnly',choose)
        self.assertIn('ContactRelayScore(',choose)
        self.assertIn('if (bBerserkerOpeningContact',choose)
        self.assertIn('CandidateScore, true);',choose)
        self.assertNotIn('if (bNativeBerserkerStrikeOnly',choose)
        self.assertNotIn('bNativeBerserkerStrikeOnly',self.mission)
        self.assertIn('BerserkerFocusTargetID, bBerserkerFocusGoal',self.mission)

    def test_berserker_mission_and_legacy_safety_unchanged(self):
        self.assertIn("FocusBattle.MapData.ActiveMission.sType == \"SabotageTransmitter\"",
                      self.ctrl)
        self.assertIn('ReadActiveTimerTurns()',self.ctrl)
        self.assertIn('NativePlantObjectivePhase(FocusBattle)',self.ctrl)
        self.assertIn('bNativeStrikeOnly && BestUnit != none',self.ctrl)
        self.assertIn('bFocusedGoal && FocusPlantPhase != 1',self.ctrl)
        self.assertIn('StopAutoplay("HUD removed")', (CLASSES/'APX_UITacticalControl.uc').read_text())

if __name__ == '__main__':
    unittest.main()
