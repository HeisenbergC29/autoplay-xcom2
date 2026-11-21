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

    def test_waypoint_changes_do_not_rearm_the_same_group(self):
        """Only a changed native group can reset the wait budget and episode."""
        refresh = function_body(AMBUSH.read_text(), "Refresh")
        start = refresh.index("if (GroupID != Group.ObjectID)")
        waypoint = refresh.index("else if (CurrentWaypoint != Waypoint)", start)
        limit = refresh.index("if (bExpired || ConfirmedWaits >=", waypoint)
        self.assertIn("ConfirmedWaits = 0;", refresh[start:waypoint])
        self.assertIn("PendingWaitTurn = INDEX_NONE;", refresh[start:waypoint])
        self.assertNotIn("ConfirmedWaits = 0;", refresh[waypoint:limit])
        self.assertNotIn("StartTurn = Turn;", refresh[waypoint:limit])
        self.assertIn("Waypoint = CurrentWaypoint;", refresh[waypoint:limit])
        self.assertIn("ConfirmedWaits", refresh[limit:])

    def test_native_ticket_completion_and_manual_off_are_wired(self):
        """One confirmed SkipTurn or player transition increments only a marked wait."""
        controller = CONTROLLER.read_text()
        ambush = AMBUSH.read_text()
        decision = function_body(controller, "MakeDecision")
        confirm = function_body(controller, "ConfirmEndTurnRequest")
        note = function_body(ambush, "NoteWaitConfirmed")
        reset = function_body(ambush, "Reset")
        marker = decision.index('MissionRecorder.Marker("patrol_ambush_wait"')
        requested = decision.index("PatrolAmbushPlanner.NoteWaitRequested(", marker)
        dispatch = decision.index("RequestEndTurn(PC);", requested)
        self.assertLess(marker, requested)
        self.assertLess(requested, dispatch)
        self.assertIn("PatrolAmbushPlanner.NoteWaitConfirmed(EndTurnPlayerTurn)", confirm)
        self.assertIn('MissionRecorder.Marker("patrol_ambush_wait_confirmed"', confirm)
        self.assertIn("if (PendingWaitTurn < 0 || PendingWaitTurn != RequestedTurn)", note)
        self.assertIn("PendingWaitTurn = INDEX_NONE;", note)
        self.assertIn("PatrolAmbushPlanner.Reset();",
                      function_body(controller, "StopAutoplay"))
        self.assertIn("ConfirmedWaits = 0;", reset)
        self.assertIn("PendingWaitTurn = INDEX_NONE;", reset)


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
        """Personal geometric LOS is a hint, not a guarantee of future fire."""
        combat = COMBAT.read_text()
        lane = function_body(combat, "HasPlausibleLocalReactionLane")
        score = function_body(combat, "ScoreSelfAction")
        self.assertIn("SquadVisibleEnemies.Length > 64", lane)
        self.assertIn("IsVisibleHostile(", lane)
        self.assertIn("CanSeeTileToTile(Soldier.TileLocation, Enemy.TileLocation", lane)
        self.assertIn("Visibility.DefaultTargetDist <= SightSq", lane)
        self.assertNotIn("GetNextDestination(", lane)
        self.assertNotIn("SubmitGameState(", lane)
        self.assertIn("HasPlausibleLocalReactionLane(UnitState, VisibleEnemies)", score)
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
