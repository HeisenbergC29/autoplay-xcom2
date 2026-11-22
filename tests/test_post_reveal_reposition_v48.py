"""Exercise the same-turn return exception and its evidence in the public report CLI."""

from itertools import product
from pathlib import Path
import unittest

from test_revealed_shooter_tactics_e2e_v45 import LOSS, run_synthetic_bundle
from test_ui_gating import function_body
from uc_math import load_uc_function


CLASSES = Path(__file__).resolve().parents[1] / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
CONTROLLER = CLASSES / "APX_Controller.uc"
REPOSITION = CLASSES / "APX_RepositionPlanner.uc"


class PostRevealReturnTests(unittest.TestCase):
    """A changed concealment state alone must never justify spending an AP on a return."""

    def test_only_revealed_shooter_with_verified_reposition_can_return(self):
        """Execute the actual UC gate for every combination of evidence and concealment."""
        allowed = load_uc_function(CONTROLLER, "IsPostRevealShotReturn")
        for proposal, departed_concealed, now_concealed in product((False, True), repeat=3):
            with self.subTest(proposal=proposal, departed=departed_concealed, current=now_concealed):
                self.assertEqual((proposal, departed_concealed, now_concealed) == (True, True, False),
                                 allowed(proposal, departed_concealed, now_concealed))

    def test_newest_matching_record_consumes_return_on_accepted_move_only(self):
        """Check soldier, direction, turn and commit boundaries of the live visit journal."""
        source = CONTROLLER.read_text()
        main = function_body(source, "MakeDecision")
        commit = function_body(source, "RecordMove")
        gate = function_body(source, "CanUseMove")
        self.assertIn("VisitedPositions.Length = 0;", main[main.index("if (PlayerState.PlayerTurnCount != LastTurn)"):])
        epoch = main[main.index("if (BerserkerFocusHistory !="):main.index("BerserkerFocusHistory = `XCOMHISTORY;")]
        for token in ("BerserkerFocusStartIndex != FocusStartIndex", "BerserkerFocusBattleID != FocusBattle.ObjectID",
                      "BerserkerFocusPlayerID != PlayerRef.ObjectID", "FocusHistoryIndex < BerserkerFocusLastHistory",
                      "VisitedPositions.Length = 0;"):
            self.assertIn(token, epoch)
        ordered = ("bLeftWhileConcealed = BestPath.Length > 1 && BestPath[0] == BestUnit.TileLocation",
                   "&& BestUnit.IsConcealed();", "PC.GameStateMoveUnitSingle(",
                   "if (!bSuccess)", "RecordMove(BestUnit, BestPath, bLeftWhileConcealed);")
        self.assertEqual([main.index(item) for item in ordered], sorted(main.index(item) for item in ordered))
        self.assertIn("return;", main[main.index("if (!bSuccess)"):main.index("RecordMove(")])
        self.assertIn("Entry.UnitID = UnitState.ObjectID;", commit)
        origin, arrival, _ = commit.split("VisitedPositions.AddItem(Entry);")
        self.assertIn("Entry.Tile = Path[0];", origin)
        self.assertIn("Entry.bLeftWhileConcealed = bLeftWhileConcealed;", origin)
        self.assertIn("Entry.Tile = Path[Path.Length - 1];", arrival)
        self.assertIn("Entry.bLeftWhileConcealed = false;", arrival)
        self.assertIn("for (Index = VisitedPositions.Length - 1; Index >= 0; --Index)", gate)
        self.assertIn("VisitedPositions[Index].UnitID == UnitState.ObjectID", gate)
        self.assertIn("VisitedPositions[Index].Tile == Path[Path.Length - 1]", gate)
        self.assertIn("VisitedPositions[Index].bLeftWhileConcealed, UnitState.IsConcealed()", gate)
        self.assertIn('return false;\n            ScanReason = "post_reveal_move_and_shot_candidate";', gate)

    def test_verified_proposal_still_requires_ap_gain_and_safe_path(self):
        """Check quality gates on the sole call site granting the post-reveal exception."""
        source = CONTROLLER.read_text()
        scan = function_body(source, "ChooseCompetitiveReposition")
        grant = "CanUseMove(UnitState, CandidatePath, false, bProposed, ScanReason)"
        self.assertEqual(1, source.count(grant))
        order = ("static.ChooseMove(", "if (bProposed)", "if (Score <= BestScore)", grant)
        self.assertEqual([scan.index(item) for item in order], sorted(scan.index(item) for item in order))
        move_and_shot = load_uc_function(REPOSITION, "MoveAndShotScore")
        # One retained shot, at least +12 percentage points, at least +8 utility, no added exposure.
        self.assertGreater(move_and_shot(35, 50, 45, 60, 10, 8, 4, 2), 35)
        for args in ((35, 50, 45, 60, 10, 8, 4, 1), (35, 50, 45, 55, 10, 8, 4, 2),
                     (35, 42, 45, 60, 10, 8, 4, 2), (35, 50, 45, 60, 10, 11, 4, 2)):
            self.assertLess(move_and_shot(*args), 0)
        planner = function_body(REPOSITION.read_text(), "ChooseMove")
        self.assertLess(planner.index("ForecastBluePathSafe("), planner.index("Path = CandidatePath;"))

    def test_cli_distinguishes_post_reveal_proposal_from_executed_return_and_shot(self):
        """Exercise ZIP ingestion for a return and a later rejected shuffle in the same turn."""
        rows = [
            (0, "start|mission=ChallengeAbductionCemetery|revision=mission-report-v48"),
            (4, "phase|phase=decision|turn=2|active_team=1"),
            (4, "unit|id=8|scope=friendly|concealed=True|x=5|y=3|z=1"),
            (4, "chosen|kind=move|unit=8|x=7|y=4|z=1|move_planner=mission|accepted=True"),
            (4, "result|ability=StandardMove|source=8|source_scope=friendly|history=107"),
            (5, "unit|id=8|scope=friendly|concealed=False|x=7|y=4|z=1|ap=3"),
            (5, "marker|kind=offensive_reposition_scan|details=unit=8 reason=post_reveal_move_and_shot_candidate"),
            (5, "chosen|kind=move|unit=8|x=5|y=3|z=1|move_planner=offensive_reposition|accepted=True"),
            (5, "result|ability=StandardMove|source=8|source_scope=friendly|history=110"),
            (6, "marker|kind=offensive_reposition_scan|details=unit=8 reason=destination_already_visited"),
            (6, "ability|unit=8|ability=StandardShot|code=AA_Success|input=True|targets=1"),
            (6, "chosen|kind=action|unit=8|ability=StandardShot|target=21|accepted=True"),
            (6, "result|ability=StandardShot|source=8|target=21|source_scope=friendly|hit=eHit_Miss|history=111"),
            (7, LOSS),
        ]
        report = run_synthetic_bundle(("same_turn_return", rows))
        self.assertEqual([], report["malformed_records"])
        session, = report["sessions"]
        self.assertEqual((2, 3), (session["moves"], session["accepted_actions"]))
        records = session["records"]
        origin, later = (row for row in records if row["event"] == "unit")
        self.assertTrue(origin["concealed"])
        self.assertFalse(later["concealed"])
        out, back, shot = (row for row in records if row["event"] == "chosen")
        self.assertEqual((origin["id"], origin["x"], origin["y"], origin["z"]),
                         (back["unit"], back["x"], back["y"], back["z"]))
        self.assertEqual((out["unit"], later["x"], later["y"]), (later["id"], out["x"], out["y"]))
        self.assertEqual(("offensive_reposition", back["unit"]), (back["move_planner"], shot["unit"]))
        self.assertEqual(["StandardMove", "StandardMove", "StandardShot"],
                         [r["ability"] for r in records if r["event"] == "result"])
        self.assertEqual(["unit=8 reason=post_reveal_move_and_shot_candidate", "unit=8 reason=destination_already_visited"],
                         [r["details"] for r in records if r["event"] == "marker"])
