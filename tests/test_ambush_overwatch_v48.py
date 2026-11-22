"""#111 regression of confirmed squad waits, personal Overwatch lanes and evidence.

Numeric tests execute real UnrealScript helpers through uc_math. Source contracts
and a synthetic record-to-report E2E do NOT replace Windows compilation or WOTC.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body
from test_revealed_shooter_tactics_e2e_v45 import run_synthetic_bundle

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
AMBUSH = SRC / "APX_PatrolAmbushPlanner.uc"
CONTROLLER = SRC / "APX_Controller.uc"
CONTACT = SRC / "APX_ContactEnvelope.uc"
COMBAT = SRC / "APX_CombatPlanner.uc"
ROUTE = SRC / "APX_RouteTempo.uc"
MISSION = SRC / "APX_MissionPlanner.uc"


class ConfirmedPatrolWaitTests(unittest.TestCase):
    """The same patrol has one finite counter shared across all squad members."""

    @classmethod
    def setUpClass(cls):
        """Load numeric policy from the production UnrealScript source."""
        cls.count = staticmethod(load_uc_function(AMBUSH, "CountConfirmedWait"))
        cls.wait = staticmethod(load_uc_function(AMBUSH, "CanWaitWindow"))

    def test_first_second_and_third_confirmed_wait_close_the_window(self):
        """A request alone is not a completed turn; a fourth wait is prohibited."""
        count = 0
        for turn in (8, 9, 10):
            self.assertTrue(self.wait(True, False, True, False, 1, 0, count, 3))
            self.assertEqual(count, self.count(count, -1, turn))
            count = self.count(count, turn, turn)
        self.assertEqual(3, count)
        self.assertFalse(self.wait(True, False, True, False, 1, 0, count, 3))
        self.assertEqual(3, self.count(count, 11, 11))

    def test_unstaged_and_unconfirmed_turns_do_not_open_or_advance_wait(self):
        """No artificial wait without an accepted setup move or native OW."""
        self.assertFalse(self.wait(True, False, False, False, 0, 0, 0, 3))
        self.assertTrue(self.wait(True, False, False, True, 0, 1, 0, 3))
        self.assertEqual(1, self.count(1, 12, 13))
        self.assertEqual(1, self.count(1, -1, 12))
        self.assertFalse(self.wait(True, True, True, False, 1, 0, 1, 3))
        self.assertFalse(self.wait(True, False, True, False, 1, 0, -1, 3))

    def test_waypoint_and_a_b_a_do_not_renew_patrol_budget(self):
        """A/B/A restores A's total and last-counted turn by native patrol ID."""
        ambush = AMBUSH.read_text()
        refresh = function_body(ambush, "Refresh")
        select = function_body(ambush, "SelectWaitBudget")
        confirm = function_body(ambush, "NoteWaitConfirmed")
        start = refresh.index("if (GroupID != Group.ObjectID)")
        waypoint = refresh.index("else if (CurrentWaypoint != Waypoint)", start)
        limit = refresh.index("if (bExpired || ConfirmedWaits >=", waypoint)
        self.assertIn("SelectWaitBudget(GroupID);", refresh[start:waypoint])
        self.assertIn("Waypoint = CurrentWaypoint;", refresh[waypoint:limit])
        for reset in ("SelectWaitBudget(", "StartTurn =", "ConfirmedWaits =", "PreparedMoves =", "OrderedReactions ="):
            self.assertNotIn(reset, refresh[waypoint:limit])
        self.assertIn("Index = WaitHistory.Find('PatrolID', NewGroupID);", select)
        fresh, returning = select.split("else")
        self.assertIn("if (Index == INDEX_NONE)", fresh)
        self.assertIn("ConfirmedWaits = 0;", fresh)
        self.assertIn("ConfirmedWaits = WaitHistory[Index].Waits;", returning)
        self.assertIn("LastCountedWaitTurn = WaitHistory[Index].LastWaitTurn;", returning)
        for step in ("Budget.PatrolID = GroupID;", "Budget.Waits = ConfirmedWaits;",
                     "Budget.LastWaitTurn = RequestedTurn;", "Index = WaitHistory.Find('PatrolID', GroupID);",
                     "WaitHistory.AddItem(Budget);", "WaitHistory[Index] = Budget;"):
            self.assertIn(step, confirm)
        self.assertNotIn("WaitHistory.Length = 0;", refresh + select + confirm)

    def test_explicit_wait_requires_committed_native_evidence(self):
        """An interrupted initiative can clear a stock ticket without counting a patrol wait."""
        controller = CONTROLLER.read_text()
        ambush = AMBUSH.read_text()
        decision = function_body(controller, "MakeDecision")
        poll = function_body(controller, "PollEndTurnRequest")
        confirm = function_body(controller, "ConfirmEndTurnRequest")
        note = function_body(ambush, "NoteWaitConfirmed")
        marker = decision.index('MissionRecorder.Marker("patrol_ambush_wait"')
        request = decision.index("PatrolAmbushPlanner.NoteWaitRequested(", marker)
        self.assertLess(request, decision.index("RequestEndTurn(PC);", request))
        self.assertIn('ConfirmEndTurnRequest("skip_turn_history", EndTurnHistoryCursor, true);', poll)
        self.assertIn('ConfirmEndTurnRequest("player_or_turn_transition", EndIndex);', poll)
        self.assertIn("bCommittedSkip", confirm)
        self.assertLess(confirm.index("FindWaitRosterHistory(EvidenceHistory) != INDEX_NONE"),
                        confirm.index("PatrolAmbushPlanner.NoteWaitConfirmed("))
        self.assertIn("EndTurnRequestHistory, Evidence);", confirm)
        self.assertIn("if (PendingWaitTurn < 0 || PendingWaitTurn != RequestedTurn)", note)
        self.assertIn("PendingWaitTurn = INDEX_NONE;", note)
        self.assertIn('Recorder.Marker("patrol_ambush_wait_confirmed"', note)
        self.assertIn("Recorder.RecordPatrolWindow(GroupID, RequestedTurn, RosterHistory, 'wait');", note)
        requested = function_body(ambush, "NoteWaitRequested")
        self.assertIn("Turn > LastCountedWaitTurn", requested)
        self.assertIn("LastCountedWaitTurn = RequestedTurn;", note)

    def test_automatic_exhaustion_counts_once_after_accepted_reserve(self):
        """A stock AP handoff can occur without a ticket; use advancement of the local turn."""
        ambush = AMBUSH.read_text()
        completed = load_uc_function(AMBUSH, "IsPendingTurnComplete")
        for pending, previous, current, valid in (
                (8, 8, 8, False), (8, 8, 9, True), (-1, 8, 9, False),
                (8, 9, 10, False), (8, 8, 7, False), (8, 8, 12, True)):
            self.assertEqual(valid, completed(pending, previous, current))
        refresh = function_body(ambush, "Refresh")
        self.assertLess(refresh.index("if (bNewEpoch)"), refresh.index("else if (IsPendingTurnComplete("))
        self.assertLess(refresh.index('FindWaitRosterHistory(HistoryIndex), "next_local_turn"'),
                        refresh.index("LastTurn = Turn;"))
        submit = function_body(ambush, "NoteSubmitted")
        self.assertIn("else if (bArmedOverwatch && HasActiveStaging())", submit)
        self.assertIn("if (Phase != 'contact')", submit)
        self.assertNotIn("NoteWaitRequested", submit.split("else if (bMove)")[1].split("else if (bArmedOverwatch")[0])
        decision = function_body(CONTROLLER.read_text(), "MakeDecision")
        self.assertLess(decision.index("if (!bSuccess)"), decision.index("PatrolAmbushPlanner.NoteSubmitted("))
        roster = function_body(ambush, "FindWaitRosterHistory")
        for guard in ("PendingWaitTurn < 0", "LastHistory + 256", "eGameRule_PlayerTurnEnd",
                      "Rule.PlayerRef.ObjectID == OwnedPlayerID", "return Index - 1;"):
            self.assertIn(guard, roster)
        self.assertTrue(roster.strip().endswith("return INDEX_NONE;"))

    def test_contact_only_manual_off_and_epoch_boundaries(self):
        """A contact can permit an immediate opener; missing movement and old epochs cannot fund a wait."""
        ambush = AMBUSH.read_text()
        refresh = function_body(ambush, "Refresh")
        self.assertIn("Phase = 'contact';", refresh)
        self.assertIn("PendingWaitTurn = INDEX_NONE;", refresh.split("if (!bSnapshotComplete")[1].split("GroupID > 0")[0])
        can_wait = function_body(ambush, "CanWaitForContact")
        self.assertIn("Phase == 'setup', Phase == 'armed'", can_wait)
        self.assertNotIn("'contact'", can_wait)
        for guard in ("OwnedHistory != `XCOMHISTORY", "OwnedStartIndex != StartIndex",
                      "OwnedBattleID != Battle.ObjectID", "OwnedPlayerID != Scout.GetAssociatedPlayerID()",
                      "HistoryIndex < LastHistory", "Turn < LastTurn"):
            self.assertIn(guard, refresh)
        self.assertIn("PatrolAmbushPlanner.Reset();", function_body(CONTROLLER.read_text(), "StopAutoplay"))
        reset = function_body(ambush, "Reset")
        for clear in ("ConfirmedWaits = 0;", "PendingWaitTurn = INDEX_NONE;",
                      "LastCountedWaitTurn = INDEX_NONE;", "WaitHistory.Length = 0;"):
            self.assertIn(clear, reset)


class OverwatchPersonalOpportunityTests(unittest.TestCase):
    """An ally seeing an enemy is not sufficient to score a personal reaction highly."""

    @classmethod
    def setUpClass(cls):
        """Load the same numeric score used by the live combat planner."""
        cls.score = staticmethod(load_uc_function(COMBAT, "ScoreOverwatchDefense"))

    def test_unreachable_squad_contact_falls_below_useful_movement(self):
        """A remembered or teammate-only contact must not get the old 17 points."""
        self.assertEqual(2.0, self.score(False, False, 1.0, 0.0, 0))
        self.assertEqual(5.0, self.score(False, False, 1.0, 0.0, 0, True))
        self.assertEqual(17.0, self.score(True, False, 1.0, 0.0, 0, True))
        self.assertEqual(22.0, self.score(True, True, 1.0, 0.0, 0, True))
        self.assertLess(self.score(False, False, 1, 0, 0, True),
                        self.score(True, False, 1, 0, 0))

    def test_bounded_personal_los_and_native_guard_not_weakened(self):
        """Use the reaction target checks while preserving the native submission guard."""
        combat = COMBAT.read_text()
        lane = function_body(combat, "HasPlausibleLocalReactionLane")
        score = function_body(combat, "ScoreSelfAction")
        self.assertIn("SquadVisibleEnemies.Length > 64", lane)
        self.assertIn("IsVisibleHostile(", lane)
        self.assertIn("IsCurrentReactionTarget(Template, Shot, Soldier, Enemy)", lane)
        self.assertNotIn("GetNextDestination(", lane)
        self.assertNotIn("SubmitGameState(", lane)
        self.assertIn("HasPlausibleLocalReactionLane(UnitState, Ability, VisibleEnemies)", score)
        self.assertIn("GuardOverwatchForKnownAlly(", score)
        self.assertIn("!bSquadOverwatchSafe", score)


class AmbushEvidenceEndToEnd(unittest.TestCase):
    """A synthetic log is useful for report provenance, not proof of native shots."""

    def test_group_zero_and_arm_shot_distinction_survive_cli(self):
        """Even a visible AI group cannot be called a verified patrol or full salvo."""
        rows = [
            (0, "start|mission=ChallengeAbductionCemetery|revision=mission-report-v48"),
            (1, "marker|kind=contact_snapshot|details=complete=True"
             " reason=current_known_contacts detectors=5 interactives=0"
             " patrol_selection=no_listed_eligible_patrol groups=3 not_listed=3"),
            (1, "marker|kind=patrol_ambush_state|details=phase=None"
             " group=0 reason=patrol_evidence_unknown selection=no_listed_eligible_patrol"
             " completed_waits=0 horizon=variants_unknown"),
            (1, "chosen|kind=action|unit=8|ability=overwatch|accepted=True"),
            (2, "result|ability=overwatch|source=8|source_scope=friendly"),
            (3, "result|ability=OverwatchShot|source=8|source_scope=friendly"
             "|target=99|hit=eHit_Miss"),
            (4, "chosen|kind=action|unit=9|ability=overwatch|accepted=True"),
            (5, "end|reason=tactical_game_ended|outcome=loss|history=99"
             "|history_pending=0"),
        ]
        data = run_synthetic_bundle(("ambush_unknown", rows))
        self.assertEqual([], data["malformed_records"])
        session, = data["sessions"]
        self.assertEqual(2, session["overwatch_observations"]["accepted_autoplay_orders"])
        self.assertEqual(1, session["overwatch_observations"]["observed_friendly_arm_results"])
        self.assertEqual(1, session["overwatch_observations"]["observed_friendly_shot_results"])
        self.assertEqual({"eHit_Miss": 1},
                         session["overwatch_observations"]["friendly_shot_outcomes"])
        details = [r.get("details", "") for r in session["records"]
                   if r["event"] == "marker"]
        self.assertTrue(any("group=0" in x for x in details))
        self.assertFalse(any("verified_stored_patrol" in x for x in details))

    def test_useful_later_turn_return_remains_penalized_not_forbidden(self):
        """A safe later-turn return can still be worth the soft memory charge."""
        memory = load_uc_function(ROUTE, "SoftVisitPenalty")
        route = load_uc_function(MISSION, "ScoreOrdinaryRouteCandidate")
        cost = memory(11, 3, 3, True, False, 28, 12)
        self.assertGreaterEqual(cost, 0.0)
        self.assertLess(cost, 28.0)
        self.assertGreater(route(70.0 - cost), 0.0)
        self.assertEqual(8.0, route(-40.0, True))


if __name__ == "__main__":
    unittest.main()
