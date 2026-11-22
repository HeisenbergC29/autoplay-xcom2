"""Regression for #116: timer-aware X4 movement versus remembered contact.

Numeric tests execute the actual UnrealScript numeric helpers. The synthetic
log pipeline is an E2E of reporting, NOT a Windows WOTC gameplay simulation.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body
from test_revealed_shooter_tactics_e2e_v45 import run_synthetic_bundle

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
CONTROLLER = CLASSES / "APX_Controller.uc"
MISSION = CLASSES / "APX_MissionPlanner.uc"


class TimedObjectiveNumericTests(unittest.TestCase):
    """Compare legal choices without manufacturing native actions or AP."""

    @classmethod
    def setUpClass(cls):
        """Load both numeric policies from current production UC code."""
        cls.eligible = staticmethod(load_uc_function(CONTROLLER, "ShouldCompareTimedObjective"))
        cls.score = staticmethod(load_uc_function(MISSION, "ScoreTimedBerserkerLastAP"))

    def test_clock_and_native_mission_bound_the_extra_candidate(self):
        """A stale timer, finished X4, non-berserker, or nonmission cannot enable it."""
        self.assertTrue(self.eligible(True, True, 4, True))
        self.assertTrue(self.eligible(True, True, 1, True))
        for params in [(False, True, 2, True), (True, False, 2, True),
                       (True, True, 0, True), (True, True, -1, True),
                       (True, True, 5, True), (True, True, 2, False)]:
            with self.subTest(params=params):
                self.assertFalse(self.eligible(*params))

    def test_safe_progress_can_outscore_contact_without_forcing_movement(self):
        """A verified, zero-extra-risk native prefix beats contact score 20."""
        self.assertEqual(45.0, self.score(3.0, 3, 0.0, True))
        self.assertEqual(36.0, self.score(1.0, 4, 2.0, True))
        self.assertGreater(self.score(3.0, 3, 0.0, True), 20.0)
        self.assertGreater(self.score(3.0, 3, 0.0, True), 2.0)
        self.assertLess(self.score(3.0, 3, 0.0, True), 70.0)

    def test_end_turn_or_native_attack_still_win_when_move_is_unsafe(self):
        """Unknown concealment, no progress, extra risk or expired clock fails."""
        for args in [(0.0, 3, 0.0, True), (1.0, 3, 0.0, False),
                     (3.0, 3, 8.01, True), (3.0, 0, 0.0, True),
                     (3.0, 5, 0.0, True)]:
            with self.subTest(args=args):
                self.assertLess(self.score(*args), -9999.0)
        self.assertLess(self.score(1.0, 3, 8.0, True),
                        self.score(3.0, 3, 0.0, True))


class TimedObjectiveSourceContracts(unittest.TestCase):
    """Source gate tests restrict last-AP movement to a safe native context."""

    @classmethod
    def setUpClass(cls):
        """Read actual controller and mission source for precise contracts."""
        cls.controller = CONTROLLER.read_text(encoding="utf-8-sig")
        cls.mission = MISSION.read_text(encoding="utf-8-sig")

    def test_one_ap_uses_current_native_path_and_checks_every_step(self):
        """No fabricated reachability, enemy intent, points or speculative shot."""
        body = function_body(self.mission, "ChooseTimedBerserkerLastAP")
        for name in ('BerserkerMP', '"SabotageTransmitter"', 'NumActionPoints() != 1',
                     'NativePlantObjectivePhase(Battle) != 0',
                     'ReadActiveTimerTurns()', 'FindBerserkerSabotageGoal(',
                     'ChooseRoutePrefix(', 'Path[0] != Soldier.TileLocation',
                     'Path.Length > 32', 'Progress < 1.0', 'InspectPathRisk(',
                     'RemainingTempoCoverChecks < Path.Length - 1',
                     'RiskAtTile(', 'ExposureRisk(', 'HasBlockingHazard(',
                     'ScoreTimedBerserkerLastAP(', 'Path.Length = 0;'):
            self.assertIn(name, body)
        for forbidden in ('CreateNewGameState(', 'Rand(', 'SYNC_RAND(',
                          'SubmitGameState(', 'ActivateAbility_ReturnContext('):
            self.assertNotIn(forbidden, body)

    def test_contact_and_mission_compete_under_timer_without_altering_combat(self):
        """Both candidates go through common Trace/CanUseMove and >BestScore."""
        body = function_body(self.controller, "MakeDecision")
        current = body.index('ChooseContactSearchMove(')
        timed = body.index('ShouldCompareTimedObjective(', current)
        mission = body.index("ChooseTimedBerserkerLastAP(", timed)
        last = body.index("TraceCandidateMove(UnitState, CandidatePath, Score)", mission)
        self.assertLess(current, timed)
        self.assertLess(timed, mission)
        self.assertLess(mission, last)
        self.assertIn("Score > BestScore && CanUseMove(UnitState, CandidatePath", body)
        self.assertIn('MissionRecorder.Marker("timed_objective_comparison"', body)
        self.assertIn("if (!bHavePlan)", body)
        self.assertIn("RequestEndTurn(PC);", body)
        self.assertIn("class'APX_CombatPlanner'.static.ChooseAction(", body)
        self.assertIn('BestMovePlanner = UnitState.NumActionPoints() == 1', body)

    def test_fresh_timer_and_no_postplant_run(self):
        """Installed clock, native plant phase and own Berserker are checked."""
        body = function_body(self.controller, "MakeDecision")
        self.assertIn("TimedNativeTimer = class'APX_BerserkerFocus'.static.ReadActiveTimerTurns();", body)
        self.assertIn("NativePlantObjectivePhase(", body)
        self.assertIn("bContactSearch || UnitState.NumActionPoints() == 1", body)
        self.assertIn("UnitState.GetMyTemplateName() == 'BerserkerMP'", body)


class TimedObjectiveLogEndToEnd(unittest.TestCase):
    """Check the public ZIP CLI contract for all three first-turn comparisons."""

    def test_mission_candidates_compete_and_rejected_move_does_not_count(self):
        """Synthetic records retain unused AP and explicit nonmovement decisions."""
        rows = [
            (0, "start|mission=SabotageTransmitter|revision=mission-report-v50"),
            (1, "unit|id=23|scope=friendly|ap=1|x=9|y=5|z=1"),
            (1, "marker|kind=timed_objective_comparison|details=unit=23"
             " turn=1 timer=4 ap=1 recent_contact=False found=True"
             " reason=timed_x4_native_one_ap candidate_score=45 best_before=20"),
            (1, "chosen|kind=move|unit=23|score=45|path_tiles=4|x=11|y=5"
             "|z=1|ap_before=1|accepted=True|move_planner=timed_last_ap_objective"),
            (2, "unit|id=24|scope=friendly|ap=1|x=7|y=9|z=1"),
            (2, "marker|kind=timed_objective_comparison|details=unit=24"
             " turn=2 timer=3 ap=1 recent_contact=True found=False"
             " reason=unsafe_native_path candidate_score=-10000 best_before=2"),
            (3, "unit|id=25|scope=friendly|ap=1|x=8|y=9|z=1"),
            (3, "marker|kind=timed_objective_comparison|details=unit=25"
             " turn=3 timer=2 ap=1 recent_contact=True found=True"
             " reason=timed_x4_native_one_ap candidate_score=42 best_before=90"),
            (3, "chosen|kind=action|unit=25|ability=DevastatingPunchMP|target=474"
             "|score=90|accepted=True"),
            (4, "end|reason=tactical_game_ended|outcome=loss|history=91|history_pending=0"),
        ]
        data = run_synthetic_bundle(("last_ap", rows))
        self.assertEqual([], data["malformed_records"])
        session, = data["sessions"]
        moves = [x for x in session["records"] if x["event"] == "chosen"
                 and x.get("kind") == "move"]
        self.assertEqual(1, len(moves))
        self.assertEqual(23, moves[0]["unit"])
        self.assertEqual(1, moves[0]["ap_before"])
        action = [x for x in session["records"] if x["event"] == "chosen"
                  and x.get("kind") == "action"]
        self.assertEqual(1, len(action))
        self.assertEqual("DevastatingPunchMP", action[0]["ability"])
        markers = [x.get("details", "") for x in session["records"]
                   if x["event"] == "marker"]
        self.assertTrue(any("unsafe_native_path" in m for m in markers))
        self.assertTrue(any("recent_contact=True" in m for m in markers))


if __name__ == "__main__":
    unittest.main()
