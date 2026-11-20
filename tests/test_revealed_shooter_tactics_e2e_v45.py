"""Exercise the public ZIP → JSON CLI with synthetic ranged-combat APXREC data.

Wire fields mirror APX_MissionRecorder. Records describe supplied observations.
These tests run the analyzer; native planning and hit rolls require WOTC.
"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "analyze-mission-log.py"
START = "start|mission=ChallengeAbductionGasStation|revision=mission-report-v45"
MOVE = ("kind=move|unit=8|score=41|path_tiles=6|x=11|y=19|z=1|ap_before=2"
        "|offensive_forecast=True|forecast_target=21|native_chance_now=35"
        "|projected_chance=70|forecast_model=bounded_geometry")
FINAL_SCORE = ("game_score|source=legacy_runtime|ladder_index=1|ladder_rung=1"
               "|cumulative_score=120|mission_points_known=True|mission_final=True"
               "|mission_points=120|phase=finish|history=100")
WIN = "end|reason=tactical_game_ended|outcome=win|history=100|history_pending=0"
LOSS = "end|reason=tactical_game_ended|outcome=loss|history=136|history_pending=0"


def encode_session(session_id, rows):
    """Encode ordered APXREC records, including sessions that stop mid-decision."""
    lines = []
    for seq, (decision, payload) in enumerate(rows, 1):
        event, _, fields = payload.partition("|")
        header = (f"AutoplayXCom2: APXREC|v=1|session={session_id}|seq={seq}"
                  f"|event={event}|decision={decision}")
        lines.append(header + ("|" + fields if fields else ""))
    return "\n".join(lines)


def run_synthetic_bundle(*sessions):
    """Write separate synthetic Launch logs and run the public CLI over the ZIP."""
    with tempfile.TemporaryDirectory() as temporary:
        bundle = Path(temporary) / "input.zip"
        result = Path(temporary) / "report.json"
        with zipfile.ZipFile(bundle, "w") as archive:
            for index, (session_id, rows) in enumerate(sessions):
                name = "Launch.log" if index == 0 else f"Launch-backup-{index}.log"
                archive.writestr(f"Logs/{name}", encode_session(session_id, rows))
        subprocess.run([sys.executable, str(ANALYZER), str(bundle), "--json", str(result)],
                       cwd=temporary, text=True, capture_output=True, check=True)
        return json.loads(result.read_text(encoding="utf-8"))


class RangedDecisionReportEndToEnd(unittest.TestCase):
    """Track what was projected, submitted, resolved or left unobserved."""

    def test_immediate_shot_result_and_terminal_native_score(self):
        """A confirmed shot and a matching final score yield a positive mission verdict."""
        rows = [
            (0, START),
            (1, "phase|phase=decision|turn=1|active_team=1"),
            (1, "marker|kind=offensive_reposition_scan|details=unit=8"
             " reason=no_material_projected_shot supported_native_shots=1"
             " material_previews=0 safe_native_paths=0 future_native_shot=unverified"),
            (1, "candidate|kind=combat|unit=8|ability=StandardShot|target=21"
             "|score=55.0800|chance=82"),
            (1, "chosen|kind=action|unit=8|ability=StandardShot|target=21"
             "|score=55.0800|chance=82|accepted=True"),
            (1, "result|ability=StandardShot|source=8|source_scope=friendly"
             "|target=21|hit=eHit_Success|chance=82|history=91"),
            (2, FINAL_SCORE),
            (2, WIN),
        ]
        # A second run records the same win but only an earlier score snapshot.
        partial_rows = rows[:-2] + [
            (2, "game_score|source=legacy_runtime|ladder_index=1|ladder_rung=1"
             "|cumulative_score=120|mission_points_known=True|mission_final=False"
             "|mission_points=120|phase=observe|history=99"),
            (2, WIN),
        ]
        data = run_synthetic_bundle(("direct", rows), ("win_partial_score", partial_rows))
        self.assertEqual([], data["malformed_records"])
        runs = {entry["session"]: entry for entry in data["sessions"]}
        run = runs["direct"]
        partial = runs["win_partial_score"]
        self.assertEqual(("win", "unknown", "mission_score_incomplete"),
                         (partial["outcome"], partial["attempt_verdict"]["status"],
                          partial["attempt_verdict"]["reason"]))
        self.assertEqual((120, False), (partial["mission_points"]["value"],
                                        partial["mission_points"]["confirmed"]))
        self.assertEqual(1, run["accepted_actions"])
        self.assertEqual(0, run["moves"])
        self.assertEqual({"StandardShot": 1}, run["abilities"])
        self.assertEqual({"eHit_Success": 1}, run["hit_results_by_source"]["friendly"])
        self.assertEqual(("pass", 120, True), (run["attempt_verdict"]["status"],
                         run["mission_points"]["value"], run["mission_points"]["confirmed"]))
        marker, = (row for row in run["records"] if row["event"] == "marker")
        self.assertIn("future_native_shot=unverified", marker["details"])

    def test_blue_move_then_fresh_shot_at_measured_chance(self):
        """Read both AP snapshots, the new native availability and the later miss."""
        rows = [
            (0, START),
            (4, "phase|phase=decision|turn=2|active_team=1"),
            (4, "unit|id=8|scope=friendly|ap=2|x=5|y=19|z=1"),
            (4, "marker|kind=offensive_reposition_scan|details=unit=8"
             " reason=safe_move_and_shot_candidate supported_native_shots=1"
             " material_previews=1 safe_native_paths=1 future_native_shot=unverified"),
            (4, "candidate|" + MOVE),
            (4, "chosen|" + MOVE + "|move_planner=offensive_reposition|accepted=True"),
            (4, "result|ability=StandardMove|source=8|source_scope=friendly|target=0"
             "|hit=eHit_Success|chance=0|history=131"),
            (5, "decision"),
            (5, "unit|id=8|scope=friendly|ap=1|x=11|y=19|z=1"),
            (5, "ability|unit=8|ability=StandardShot|code=AA_Success|input=True|targets=1"),
            (5, "chosen|kind=action|unit=8|ability=StandardShot|target=21"
             "|score=44|chance=64|accepted=True"),
            (5, "result|ability=StandardShot|source=8|target=21|source_scope=friendly"
             "|hit=eHit_Miss|chance=64|history=132"),
            (6, LOSS),
        ]
        data = run_synthetic_bundle(("move_then_shot", rows))
        self.assertEqual([], data["malformed_records"])
        run, = data["sessions"]
        self.assertEqual((2, 1, {"StandardShot": 1}),
                         (run["accepted_actions"], run["moves"], run["abilities"]))
        records = run["records"]
        move, shot = [row for row in records if row["event"] == "chosen"]
        before, after = [row for row in records if row["event"] == "unit"]
        self.assertEqual((8, 8, 2, 2, 1), (move["unit"], before["id"], move["ap_before"],
                                           before["ap"], after["ap"]))
        self.assertEqual((move["unit"], move["x"], move["y"], move["z"]),
                         (after["id"], after["x"], after["y"], after["z"]))
        availability, = (row for row in records if row["event"] == "ability")
        self.assertEqual(("AA_Success", "StandardShot", after["id"], 1),
                         (availability["code"], availability["ability"],
                          availability["unit"], availability["targets"]))
        move_result, roll = [row for row in records if row["event"] == "result"]
        self.assertEqual(("StandardMove", move["unit"]), (move_result["ability"], move_result["source"]))
        self.assertEqual(("StandardShot", 8, 21, "eHit_Miss"),
                         (roll["ability"], roll["source"], roll["target"], roll["hit"]))
        order = [move, move_result, after, availability, shot, roll]
        self.assertEqual([row["seq"] for row in order], sorted(row["seq"] for row in order))
        self.assertEqual(("offensive_reposition", 21, 21, 8),
                         (move["move_planner"], move["forecast_target"], shot["target"], shot["unit"]))
        self.assertEqual((35, 70, 64, 64), (move["native_chance_now"], move["projected_chance"],
                                           shot["chance"], roll["chance"]))
        self.assertEqual("fail", run["attempt_verdict"]["status"])
        self.assertFalse(run["mission_points"]["confirmed"])

    def test_arming_overwatch_does_not_count_a_reaction_shot(self):
        """Neither rejected movement nor the Overwatch stance supplies a shot roll."""
        rows = [
            (0, START),
            (3, "marker|kind=offensive_reposition_scan|details=unit=8"
             " reason=no_supported_current_shot supported_native_shots=0 safe_native_paths=0"),
            (4, "marker|kind=offensive_reposition_scan|details=unit=9"
             " reason=unsafe_or_unverified_blue_path supported_native_shots=2"
             " material_previews=3 safe_native_paths=0"),
            (4, "chosen|kind=action|unit=9|ability=overwatch|target=9|score=2|accepted=True"),
            (4, "result|ability=overwatch|source=9|target=9|source_scope=friendly"
             "|hit=eHit_Success|chance=0|history=130"),
            (5, LOSS),
        ]
        data = run_synthetic_bundle(("blocked", rows))
        self.assertEqual([], data["malformed_records"])
        run, = data["sessions"]
        self.assertEqual((1, 0, {"overwatch": 1}),
                         (run["accepted_actions"], run["moves"], run["action_families"]))
        self.assertEqual(["overwatch"], [row["ability"] for row in run["records"]
                                        if row["event"] == "result"])
        self.assertEqual(2, run["events"]["marker"])
        self.assertEqual("fail", run["attempt_verdict"]["status"])

    def test_manual_shot_and_truncated_autoplay_are_distinct_runs(self):
        """A manual result is not an autoplay choice; a partial move predicts no roll."""
        assisted = [
            (0, START),
            (4, "chosen|" + MOVE + "|move_planner=mission|accepted=True"),
            (4, "result|ability=StandardMove|source=8|source_scope=friendly|target=0"
             "|hit=eHit_Success|chance=0|history=91"),
            (4, "phase|phase=manual|turn=2|active_team=1"),
            (4, "result|ability=StandardShot|source=8|source_scope=friendly|target=21"
             "|hit=eHit_Success|chance=63|history=92"),
            (4, FINAL_SCORE),
            (4, WIN),
        ]
        truncated = [
            (0, START),
            (4, "chosen|" + MOVE + "|move_planner=mission|accepted=True"),
        ]
        data = run_synthetic_bundle(("assisted", assisted), ("truncated", truncated))
        self.assertEqual([], data["malformed_records"])
        runs = {run["session"]: run for run in data["sessions"]}
        self.assertEqual({"assisted", "truncated"}, set(runs))
        manual = runs["assisted"]
        self.assertEqual((1, 1, {}), (manual["accepted_actions"], manual["moves"], manual["abilities"]))
        phase, = (row for row in manual["records"] if row["event"] == "phase")
        shot, = (row for row in manual["records"] if row.get("ability") == "StandardShot")
        self.assertEqual(("manual", "result"), (phase["phase"], shot["event"]))
        self.assertLess(phase["seq"], shot["seq"])
        # The positive verdict rates the mission outcome and score; attribution
        # of this non-autoplay shot comes from the separate event sequence.
        self.assertEqual("pass", manual["attempt_verdict"]["status"])

        partial = runs["truncated"]
        choice, = (row for row in partial["records"] if row["event"] == "chosen")
        self.assertEqual((True, "mission"), (choice["offensive_forecast"], choice["move_planner"]))
        self.assertEqual((1, {}, 0), (partial["moves"], partial["abilities"],
                                      partial["events"].get("result", 0)))
        self.assertEqual(("unknown", "mission_outcome_unknown"),
                         (partial["attempt_verdict"]["status"], partial["attempt_verdict"]["reason"]))
        self.assertFalse(partial["mission_points"]["confirmed"])
        self.assertTrue(any("No end record" in warning for warning in partial["warnings"]))


if __name__ == "__main__":
    unittest.main()
