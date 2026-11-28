"""#127: execute real recorder lifecycle branches on explicit SDK test doubles.

The restricted translator is test-only; the history/score APIs are mocked.
ZIP tests run the real analyzer but do not simulate native WOTC gameplay.
"""
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

from test_live_unit_stats import translate_body
from test_ui_gating import function_body
from test_revealed_shooter_tactics_e2e_v45 import run_synthetic_bundle
from test_game_scoring import SCORING

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionRecorder.uc").read_text(
    encoding="utf-8-sig")
STATE = ("bStarted,bFinished,bLimitReported,bRecordingEpochInvalid,Sequence,"
         "RecordedHistory,LastObservedMissionHistory,bEndPending,LastEndHistory,HistoryCursor")


def uc_concat(expression):
    """Preserve the actual UC field order while converting scalar types to text."""
    return "Join(" + ",".join(expression.split("$")) + ")"


def compile_lifecycle(environment):
    """Execute the actual four production methods with a small syntax adapter."""
    namespace = dict(environment)
    specs = (
        ("Emit", "EventName,Fields,bTerminal=False"),
        ("RecordingEpochMatches", "bSameHistory,StartStateIndex,CurrentStartStateIndex,"
                                  "MinimumHistory,CurrentHistory,BattleID,CurrentBattleID"),
        ("IsRecordingMission", "bAllowTerminal=False"),
        ("Finish", "Reason"),
    )
    for name, args in specs:
        body = function_body(SOURCE, name)
        body = body.replace("++Sequence", "Sequence += 1")
        body = body.replace("class'XComGameState_BattleData'", "'XComGameState_BattleData'")
        body = body.replace('BattleData.bLocalPlayerWon ? "win" : "loss"',
                            '("win" if BattleData.bLocalPlayerWon else "loss")')
        body = re.sub(r"\x60log\((.*?),\s*true,\s*'AutoplayXCom2'\);",
                      lambda m: "Log(" + uc_concat(m[1]) + ");", body, flags=re.S)
        body = re.sub(r'Emit\("([^"]+)",\s*(.*?)(,\s*true)?\);',
                      lambda m: 'Emit("' + m[1] + '",' + uc_concat(m[2])
                      + (m[3] or "") + ");", body, flags=re.S)
        code = f"def {name}({args}):\n    global {STATE}\n" + translate_body(body)
        exec(compile(code, f"APX_MissionRecorder.uc:{name}", "exec"), namespace)
    return namespace


class History:
    """Fixture with mutable native epoch, cursor and winner evidence."""

    def __init__(self):
        """Install one battle with no authoritative winner yet."""
        self.start = 2
        self.index = 10
        self.battle = SimpleNamespace(
            ObjectID=8, MapData=SimpleNamespace(ActiveMission=SimpleNamespace(sType="Test")),
            VictoriousPlayer=SimpleNamespace(ObjectID=0), bLocalPlayerWon=False)

    def FindStartStateIndex(self):
        """Return the fixture's current epoch boundary."""
        return self.start

    def GetCurrentHistoryIndex(self):
        """Return the current history index."""
        return self.index

    def GetSingleGameStateObjectForClass(self, cls, allow_none):
        """Resolve only the requested battle-data object."""
        if cls != "XComGameState_BattleData" or not allow_none:
            raise AssertionError("Unexpected history read")
        return self.battle


class TerminalLifecycleTests(unittest.TestCase):
    """Exercise emission, context checks, pending winner and idempotent close."""

    def setUp(self):
        """Build a live recorder with a deliberately small configured cap."""
        self.history = History()
        self.logs = []
        self.cleanup = 0
        self.uc = compile_lifecycle(dict(
            bStarted=True, bFinished=False, bLimitReported=False,
            bRecordingEpochInvalid=False, bEndPending=False, LastEndHistory=0,
            Sequence=0, MaxRecords=1, Decision=1, SessionID="test",
            HistoryCursor=10, RecordingStartHistory=10, LastObservedMissionHistory=10,
            RecordedHistory=self.history, XCOMHISTORY=self.history,
            RecordedStartStateIndex=2, RecordedBattleID=8, RecordedMissionType="Test",
            Clamp=lambda value, lo, hi: max(lo, min(hi, value)), Max=max,
            Safe=lambda value: value, XComGameState_BattleData=lambda x: x,
            Join=lambda *parts: "".join(map(str, parts)), Log=self.logs.append,
            Observe=self.observe, RecordGameScore=self.score, UnregisterScoreObservers=self.close,
        ))

    def observe(self, phase):
        """Mock detail collection; no native frames are fabricated after the cap."""
        if self.uc["IsRecordingMission"]():
            self.uc["Emit"]("phase", "|phase=" + phase)
            if not self.uc["bLimitReported"]:
                self.uc["HistoryCursor"] = self.history.index

    def score(self, phase):
        """Stand in for guarded ordinary score observation, never reserve a score slot."""
        if self.uc["IsRecordingMission"]():
            self.uc["Emit"]("game_score", "|phase=" + phase)

    def close(self):
        """Count native observer cleanup without invoking the engine."""
        self.cleanup += 1

    def cap(self):
        """Exercise the real lower clamp and the one-time limit notification."""
        for _ in range(120):
            self.uc["Emit"]("unit", "|id=1")
        self.assertEqual(101, len(self.logs))
        self.assertTrue(self.uc["bLimitReported"])
        self.assertEqual(1, sum("|event=limit|" in row for row in self.logs))

    def test_limit_reserves_only_terminal_and_close_is_idempotent(self):
        """Low configured limit still clamps to 100; no later detail passes."""
        self.cap()
        self.uc["Emit"]("game_score", "|mission_final=True", True)
        self.uc["Emit"]("unit", "|id=2")
        self.history.index = 50
        self.history.battle.VictoriousPlayer.ObjectID = 5
        self.history.battle.bLocalPlayerWon = True
        self.uc["Finish"]("tactical_game_ended")
        self.uc["Finish"]("tactical_game_ended")
        self.uc["Emit"]("end", "", True)
        self.assertEqual(102, len(self.logs))
        self.assertIn("|seq=102|event=end|", self.logs[-1])
        self.assertIn("|outcome=win|history=10|history_pending=40|details_truncated=True", self.logs[-1])
        self.assertEqual(1, self.cleanup)

    def test_wait_for_committed_winner_even_after_cap(self):
        """No default false winner or repeated ending records at the cap."""
        self.cap()
        self.history.index = 11
        for _ in range(5):
            self.uc["Finish"]("tactical_game_ended")
        self.assertEqual(101, len(self.logs))
        self.assertFalse(self.uc["bFinished"])
        self.assertEqual(0, self.cleanup)
        self.history.battle.VictoriousPlayer.ObjectID = 7
        self.uc["Finish"]("tactical_game_ended")
        self.assertIn("|outcome=loss|", self.logs[-1])
        self.assertEqual(1, self.cleanup)

    def test_changed_epoch_or_rewind_never_borrows_later_winner(self):
        """Validation remains live after cap, even with no detail record."""
        for mutation in ("history", "start", "battle", "mission", "rewind", "missing"):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.cap()
                self.history.index = 30
                self.assertFalse(self.uc["IsRecordingMission"]())
                self.assertTrue(self.uc["IsRecordingMission"](True))
                if mutation == "history":
                    self.uc["XCOMHISTORY"] = History()
                elif mutation == "start":
                    self.history.start += 1
                elif mutation == "battle":
                    self.history.battle.ObjectID += 1
                elif mutation == "mission":
                    self.history.battle.MapData.ActiveMission.sType = "Other"
                elif mutation == "rewind":
                    self.history.index = 29
                else:
                    self.history.battle = None
                if self.history.battle is not None:
                    self.history.battle.VictoriousPlayer.ObjectID = 5
                    self.history.battle.bLocalPlayerWon = True
                self.uc["Finish"]("tactical_game_ended")
                self.uc["Finish"]("controller_destroyed")
                self.assertEqual(102, len(self.logs))
                self.assertIn("|event=recording_context_lost|", self.logs[-1])
                self.assertNotIn("|outcome=", self.logs[-1])
                self.assertEqual(1, self.cleanup)

    def test_native_epoch_predicate(self):
        """The production identity/start/history/battle conditions are unchanged."""
        f = self.uc["RecordingEpochMatches"]
        self.assertTrue(f(True, 2, 2, 10, 11, 8, 8))
        for args in ((False, 2, 2, 10, 11, 8, 8), (True, 2, 3, 10, 11, 8, 8),
                     (True, 2, 2, 10, 9, 8, 8), (True, 2, 2, 10, 11, 8, 9)):
            self.assertFalse(f(*args))

    def test_uncapped_end_and_destroyed_unknown(self):
        """An ordinary finish retains details; destroy cannot invent a winner."""
        self.history.index = 12
        self.uc["Finish"]("controller_destroyed")
        self.assertIn("|outcome=unknown|history=12|history_pending=0|details_truncated=False", self.logs[-1])
        self.assertEqual(1, self.cleanup)

    def test_source_cursor_and_score_gates(self):
        """Partially emitted last frame remains pending; scoring stays detail-only."""
        body = function_body(SOURCE, "RecordResults")
        self.assertIn("if (bLimitReported)\n        return;", body)
        self.assertIn("if (bLimitReported)\n        --HistoryCursor;", body)
        score = function_body(SOURCE, "RecordGameScore")
        self.assertIn("!IsRecordingMission()", score)
        self.assertIn("&& !bLimitReported", score)
        self.assertIn("HistoryCursor == ", score)
        finish = function_body(SOURCE, "Finish")
        self.assertIn("Max(0, ", finish)
        self.assertIn('Emit("end",', finish)
        self.assertIn('details_truncated=', finish)


class TerminalReportTests(unittest.TestCase):
    """Exercise the actual ZIP CLI and conservative score source interpretation."""

    def test_limit_and_explicit_truncation_are_independent_evidence(self):
        """Historical limit and new terminal marker both prevent final scoring."""
        for records in ([{"event": "limit"}],
                        [{"event": "end", "details_truncated": True}],
                        [{"event": "recording_context_lost", "details_truncated": True}]):
            self.assertTrue(SCORING.has_truncated_details(records))
        self.assertFalse(SCORING.has_truncated_details(
            [{"event": "end", "details_truncated": False}]))

    def test_zip_mixed_capped_and_complete_sessions(self):
        """Win is recorded, not certified PASS; loss and healthy sessions stay separate."""
        start = (0, "start|mission=Test|revision=mission-report-v52|history=10")
        total = (1, "score_delta|source=game_runtime|scoring_type=CMPT_TotalScore"
                    "|added_points=700|score_id=9|history=11")
        score = (2, "game_score|source=legacy_runtime|ladder_index=1|ladder_rung=1"
                    "|cumulative_score=700|mission_points_known=True|mission_points=700"
                    "|mission_final=True|phase=finish|history=12")
        limit = (3, "limit|max_records=100")
        capped = (4, "end|reason=tactical_game_ended|outcome=win|history=12"
                     "|history_pending=0|details_truncated=True")
        complete = (4, "end|reason=tactical_game_ended|outcome=win|history=12"
                       "|history_pending=0|details_truncated=False")
        loss = (4, "end|reason=tactical_game_ended|outcome=loss|history=12"
                   "|history_pending=20|details_truncated=True")
        stale = (4, "recording_context_lost|reason=history_or_mission_changed"
                    "|history=12|details_truncated=True")
        report = run_synthetic_bundle(
            ("capped_legacy", [start, score, limit, capped]),
            ("capped_rollup", [start, total, limit, capped]),
            ("flag_only", [start, score, capped]),
            ("healthy", [start, score, complete]),
            ("loss", [start, total, limit, loss]),
            ("stale", [start, limit, stale]),
            ("old_truncated", [start, limit]),
        )
        self.assertEqual([], report["malformed_records"])
        sessions = {s["session"]: s for s in report["sessions"]}
        for name in ("capped_legacy", "capped_rollup", "flag_only"):
            session = sessions[name]
            self.assertEqual("win", session["outcome"])
            self.assertTrue(session["details_truncated"])
            self.assertFalse(session["attempt_verdict"]["score_complete"])
            self.assertEqual("unknown", session["attempt_verdict"]["status"])
            self.assertTrue(any("details are incomplete" in w for w in session["warnings"]))
        self.assertEqual("pass", sessions["healthy"]["attempt_verdict"]["status"])
        self.assertFalse(sessions["healthy"]["details_truncated"])
        self.assertEqual("fail", sessions["loss"]["attempt_verdict"]["status"])
        self.assertEqual("unknown", sessions["stale"]["outcome"])
        self.assertEqual("unknown", sessions["old_truncated"]["outcome"])
        self.assertTrue(any("context was lost" in w for w in sessions["stale"]["warnings"]))


if __name__ == "__main__":
    unittest.main()
