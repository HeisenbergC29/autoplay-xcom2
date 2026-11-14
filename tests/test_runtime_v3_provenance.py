"""Regression: live v3 HUD provenance is distinct from archived offline v2.

These tests use the real Python analyzer with synthetic APXREC sessions.
No native WOTC gameplay or proof of parity is asserted.
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


SCORING = load_tool("scoring_v3_tests", "tools/game_scoring.py")
LOG = load_tool("log_v3_tests", "tools/analyze-mission-log.py")
PROFILE = "wotc_legacy_config_observed_v3_partial"
RATE_SOURCE = "installed_ladder_config"


def event(seq, kind, **fields):
    return {"event": kind, "seq": seq, "session": "s", **fields}


def hud(seq=3, display="~1234/--", **changes):
    values = dict(comparison_profile=PROFILE, comparison_status="partial",
                  rate_source=RATE_SOURCE, native_parity_proven=False,
                  event_coverage_proven=False, display=display)
    values.update(changes)
    return event(seq, "hud_score", **values)


def mission(*extra, score=None):
    records = [
        event(1, "start", mission="SabotageCC", history=10),
        event(2, "phase", turn=1),
        *extra,
    ]
    if score is not None:
        records.append(event(19, "game_score", source="challenge_runtime",
                             mission_points_known=True, mission_final=True,
                             mission_points=score, phase="finish", history=50))
    records.append(event(20, "end", history=50, history_pending=0, outcome="win"))
    return records


def logline(record):
    return ("[0003.11] AutoplayXCom2: APXREC|v=1|session=s"
            + "".join("|%s=%s" % (key, str(value).lower() if isinstance(value, bool) else value)
                      for key, value in record.items() if key != "session"))


class ObservedV3Provenance(unittest.TestCase):
    def test_exact_v3_runtime_hud_is_observation_not_final_score(self):
        records = mission(hud(display="~-4900/—"))
        result = SCORING.score_session(records)
        v3 = result["runtime_observed_v3"]
        self.assertEqual(v3["profile_id"], PROFILE)
        self.assertEqual(v3["status"], "partial")
        self.assertEqual(v3["rate_source"], RATE_SOURCE)
        self.assertEqual(v3["observed_subtotal"], -4900)
        self.assertFalse(v3["native_parity_proven"])
        self.assertFalse(v3["event_coverage_proven"])
        self.assertFalse(v3["is_official_game_score"])
        self.assertIsNone(v3["total"])
        self.assertEqual(result["comparison"]["profile_id"], "wotc_legacy_observed_v2")
        self.assertIn("native_rule_parity", v3["missing_evidence"])
        self.assertIn("complete_event_coverage", v3["missing_evidence"])
        self.assertIn("final_mission_score", v3["missing_evidence"])

    def test_positive_observed_v3_does_not_turn_native_win_into_pass(self):
        records = mission(hud(display="~7100/--"))
        verdict = SCORING.assess_attempt(records, "win", SCORING.score_session(records))
        self.assertEqual(verdict["status"], "unknown")
        self.assertEqual(verdict["reason"], "mission_score_incomplete")
        self.assertEqual(verdict["score_source"], "mod_observed_v3")
        self.assertEqual(verdict["score_profile"], PROFILE)
        self.assertEqual(verdict["observed_score"], 7100)
        self.assertIsNone(verdict["score"])
        self.assertFalse(verdict["score_complete"])

    def test_native_final_mission_score_still_precedes_v3(self):
        records = mission(hud(display="~7100/--"), score=6200)
        verdict = SCORING.assess_attempt(records, "win", SCORING.score_session(records))
        self.assertEqual(verdict["status"], "pass")
        self.assertEqual(verdict["score"], 6200)
        self.assertEqual(verdict["score_source"], "native_mission_points")
        self.assertEqual(verdict["score_status"], "final_native_observation")

    def test_conflicting_or_missing_v3_attribution_fails_closed(self):
        bad = (
            {"rate_source": "sdk_structure_default"},
            {"rate_source": None},
            {"comparison_status": "complete"},
            {"native_parity_proven": True},
            {"event_coverage_proven": True},
            {"native_parity_proven": None},
            {"display": "7100/--"},
            {"display": "~invalid/--"},
            {"display": "~100"},
        )
        for changed in bad:
            with self.subTest(changed=changed):
                records = mission(hud(**changed))
                result = SCORING.score_session(records)
                v3 = result["runtime_observed_v3"]
                self.assertIsNone(v3["observed_subtotal"])
                self.assertIsNone(v3["total"])
                self.assertEqual(v3["status"], "partial")
                verdict = SCORING.assess_attempt(records, "win", result)
                self.assertIsNone(verdict["score"])
                self.assertEqual(verdict["status"], "unknown")

    def test_all_snapshots_must_have_a_consistent_provenance(self):
        observations = mission(hud(seq=3, display="~100/--"),
                               hud(seq=4, display="~200/--"))
        v3 = SCORING.score_session(observations)["runtime_observed_v3"]
        self.assertEqual(v3["observed_subtotal"], 200)
        self.assertEqual(v3["last_seq"], 4)
        self.assertEqual(v3["observations"], 2)
        observations = mission(hud(seq=3, display="~100/--"),
                               hud(seq=4, display="~200/--", rate_source="other"))
        v3 = SCORING.score_session(observations)["runtime_observed_v3"]
        self.assertIsNone(v3["observed_subtotal"])
        self.assertIn("incomplete_runtime_v3_observations", v3["missing_evidence"])

    def test_unknown_profile_cannot_be_cast_to_v3(self):
        records = mission(hud(comparison_profile="unverified_score_profile"))
        result = SCORING.score_session(records)
        self.assertEqual(result["runtime_observed_v3"]["status"], "not_recorded")
        self.assertEqual(result["comparison"]["profile_id"], "wotc_legacy_observed_v2")

    def test_negative_zero_and_unicode_missing_maximum_are_valid_observations(self):
        for display, value in (("~-10/--", -10), ("~0/—", 0), ("~250/--", 250)):
            with self.subTest(display=display):
                v3 = SCORING.score_session(mission(hud(display=display)))["runtime_observed_v3"]
                self.assertEqual(v3["observed_subtotal"], value)

    def test_human_report_exposes_provenance_and_keeps_v2_separate(self):
        records = mission(hud(display="~1234/--"))
        lines = [logline(r) for r in records]
        report = LOG.analyze_logs([("Launch.log", "\n".join(lines))])
        summary = LOG.human_summary(report)
        self.assertIn("Runtime observed v3", summary)
        self.assertIn("rate_source=installed_ladder_config", summary)
        self.assertIn("native_parity_proven=False", summary)
        self.assertIn("not an official final mission score", summary)
        self.assertIn("Comparison (wotc_legacy_observed_v2)", summary)
        verdict = report["sessions"][0]["attempt_verdict"]
        self.assertEqual(verdict["score_source"], "mod_observed_v3")
        self.assertEqual(verdict["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
