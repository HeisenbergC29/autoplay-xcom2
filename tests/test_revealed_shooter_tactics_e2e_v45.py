"""#104: CLI-level multi-decision ranged tactic report fixture (synthetic data).

This E2E checks APXREC input ZIP -> public analyzer -> output decision/score
provenance; it DOES NOT execute native UnrealScript or XCOM 2.
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


def encode_session(session_id, rows):
    """Encode a complete ordered synthetic APXREC session for the CLI."""
    return "\n".join(
        f"AutoplayXCom2: APXREC|v=1|session={session_id}|seq={seq}"
        f"|decision={decision}|event={payload}"
        for seq, (decision, payload) in enumerate(rows, 1)
    )


def run_synthetic_bundle(*streams):
    """Execute actual report CLI against ZIP with isolated synthetic runs."""
    with tempfile.TemporaryDirectory() as temporary:
        bundle = Path(temporary) / "input.zip"
        result = Path(temporary) / "report.json"
        with zipfile.ZipFile(bundle, "w") as archive:
            for name, text in streams:
                archive.writestr(name, text)
        subprocess.run([sys.executable, str(ANALYZER), str(bundle),
                        "--json", str(result)], cwd=temporary,
                       text=True, capture_output=True, check=True)
        return json.loads(result.read_text(encoding="utf-8"))


class RangedDecisionReportEndToEnd(unittest.TestCase):
    """Validate ordered chosen actions, forecasts, manual intervention and result."""

    def test_good_direct_shot_beats_hypothetical_flank_and_ow(self):
        """An 82% live shot has a confirmed roll; projected flank is not an action."""
        rows = [
            (0, "start|mission=ChallengeAbductionGasStation|revision=mission-report-v45"),
            (1, "phase|phase=decision|turn=1"),
            (1, "marker|kind=offensive_reposition_scan|details=unit=8"
             " reason=no_material_projected_shot supported_native_shots=1"
             " material_previews=0 safe_native_paths=0 future_native_shot=unverified"),
            (1, "candidate|kind=combat|unit=8|ability=StandardShot|target=21"
             "|score=55.0800|chance=82"),
            (1, "chosen|kind=action|unit=8|ability=StandardShot|target=21"
             "|score=55.0800|chance=82|accepted=True"),
            (2, "result|ability=StandardShot|source=8|source_scope=friendly"
             "|target=21|hit=eHit_Success|chance=82|history=91"),
            (2, "game_score|source=challenge_runtime|mission_points_known=True"
             "|mission_final=True|mission_points=120|history=99"),
            (2, "end|outcome=win|history=100|history_pending=0"),
        ]
        data = run_synthetic_bundle(("Logs/Launch.log", encode_session("direct", rows)))
        self.assertEqual([], data["malformed_records"])
        run = next(x for x in data["sessions"] if x["session"] == "direct")
        self.assertEqual(1, run["accepted_actions"])
        self.assertEqual(0, run["moves"])
        self.assertEqual({"StandardShot": 1}, run["abilities"])
        self.assertEqual("pass", run["attempt_verdict"]["status"])
        markers = [x for x in run["records"]
                   if x.get("event") == "marker" and x.get("kind")
                   == "offensive_reposition_scan"]
        self.assertEqual(1, len(markers))
        self.assertIn("no_material_projected_shot", markers[0]["details"])

    def test_weak_shot_safe_native_blue_then_fresh_shot_and_unknown_e2e(self):
        """A candidate move alone cannot guarantee future native shot or outcome."""
        rows = [
            (0, "start|mission=ChallengeAbductionGasStation|revision=mission-report-v45"),
            (4, "phase|phase=decision|turn=2"),
            (4, "marker|kind=offensive_reposition_scan|details=unit=8"
             " reason=safe_move_and_shot_candidate supported_native_shots=1"
             " material_previews=1 safe_native_paths=1 future_native_shot=unverified"),
            (4, "candidate|kind=move|unit=8|score=41|path_tiles=6|x=11|y=19|z=1"
             "|offensive_forecast=True|forecast_target=21|native_chance_now=35"
             "|native_chance_after=70"),
            (4, "chosen|kind=move|unit=8|score=41|path_tiles=6|x=11|y=19|z=1"
             "|accepted=True|offensive_forecast=True|forecast_target=21"),
            (5, "result|ability=StandardMove|source=8|source_scope=friendly|history=131"),
            (5, "ability|unit=8|ability=StandardShot|code=AA_Success|targets=1"),
            (5, "chosen|kind=action|unit=8|ability=StandardShot|target=21"
             "|score=44|chance=64|accepted=True"),
            (6, "result|ability=StandardShot|source=8|target=21"
             "|source_scope=friendly|hit=eHit_Miss|chance=64|history=132"),
            (6, "end|outcome=loss|history=136|history_pending=0"),
        ]
        data = run_synthetic_bundle(("Logs/Launch.log", encode_session("move_then_shot", rows)))
        self.assertEqual([], data["malformed_records"])
        run = next(x for x in data["sessions"] if x["session"] == "move_then_shot")
        self.assertEqual(2, run["accepted_actions"])
        self.assertEqual(1, run["moves"])
        self.assertEqual({"StandardShot": 1}, run["abilities"])
        self.assertEqual("fail", run["attempt_verdict"]["status"])
        self.assertFalse(run["mission_points"]["confirmed"])
        sequence = [(x["decision"], x["event"], x.get("ability", x.get("kind")))
                    for x in run["records"]
                    if x["event"] == "chosen"
                    or (x["event"] == "ability" and x.get("code") == "AA_Success")]
        self.assertEqual([(4, "chosen", "move"), (5, "ability", "StandardShot"),
                          (5, "chosen", "StandardShot")], sequence)
        # The measured current native shot after the move is 64%, not the
        # pre-move optimistic 70% estimate. Neither value implies a hit.
        self.assertTrue(any(x.get("hit") == "eHit_Miss" for x in run["records"]))

    def test_no_current_shot_or_unsafe_path_cannot_be_faked_as_a_chosen_move(self):
        """A scout with zero native shot candidates contributes only diagnostics."""
        rows = [
            (0, "start|mission=ChallengeAbductionGasStation|revision=mission-report-v45"),
            (3, "phase|phase=decision|turn=2"),
            (3, "marker|kind=offensive_reposition_scan|details=unit=8"
             " reason=no_supported_current_shot supported_native_shots=0"
             " safe_native_paths=0"),
            (4, "marker|kind=offensive_reposition_scan|details=unit=9"
             " reason=unsafe_or_unverified_blue_path supported_native_shots=2"
             " material_previews=3 safe_native_paths=0"),
            (4, "chosen|kind=action|unit=9|ability=overwatch|target=9"
             "|score=2|accepted=True"),
            (5, "result|ability=overwatch|source=9|target=9"
             "|source_scope=friendly|history=145"),
            (5, "end|outcome=loss|history=170|history_pending=0"),
        ]
        data = run_synthetic_bundle(("Logs/Launch.log", encode_session("blocked", rows)))
        self.assertEqual([], data["malformed_records"])
        run = next(x for x in data["sessions"] if x["session"] == "blocked")
        self.assertEqual(1, run["accepted_actions"])
        self.assertEqual(0, run["moves"])
        self.assertEqual("fail", run["attempt_verdict"]["status"])
        self.assertEqual(2, len([x for x in run["records"]
                                  if x.get("kind") == "offensive_reposition_scan"]))


if __name__ == "__main__":
    unittest.main()
