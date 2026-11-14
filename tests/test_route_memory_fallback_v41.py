"""Necessary ordinary returns remain useful after soft memory costs.

Numeric tests execute real UC helpers. Source checks bind that policy to the
local route branch; they are not a native execution of ChooseMove or a mission.
"""
from pathlib import Path
from types import SimpleNamespace
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
MISSION = SRC / "APX_MissionPlanner.uc"


class NecessaryMemoryReturnPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = staticmethod(load_uc_function(MISSION, "ScoreOrdinaryRouteCandidate"))
        cls.memory = staticmethod(load_uc_function(SRC / "APX_RouteTempo.uc", "SoftVisitPenalty"))
        cls.urgent = staticmethod(load_uc_function(SRC / "APX_ConcealmentPlanner.uc", "ConcealmentIsUrgent"))
        contact = load_uc_function(SRC / "APX_ContactEnvelope.uc", "PathStatusPenalty")
        contact.__globals__["default"] = SimpleNamespace(CautionRoutePenalty=24, UnknownRoutePenalty=8)
        cls.contact = staticmethod(contact)

    def test_revealed_no_cover_necessary_return_survives_combined_costs(self):
        # A local gain over MinimumPositionGain=4 can fall below the action
        # threshold after Unknown contact and a previous-turn return penalty.
        # Revealed no-cover units skip both old cover/stealth threshold checks.
        self.assertTrue(self.urgent(False, False, False, False, False))
        penalty = self.memory(8, 7, 3, True, False, 28, 12)
        self.assertEqual(penalty, 21)
        gain = 5.5 - self.contact(-1) - penalty
        self.assertEqual(self.score(gain), -3.5)
        self.assertEqual(self.score(gain, True), 8)

    def test_useful_safe_alternative_beats_only_return_without_changing_baseline(self):
        necessary_return = self.score(5.5 - 8 - 21, True)
        self.assertGreater(self.score(5.5), necessary_return)
        # No-memory revealed/no-cover behavior remains unchanged.
        self.assertEqual(self.score(5.5 - 8), 17.5)
        self.assertEqual(self.score(200), 80)

    def test_all_soft_costs_rank_returns_before_the_score_floor(self):
        clear = self.score(5.5 - 21)
        unknown = self.score(5.5 - 21 - self.contact(-1))
        explosive = self.score(5.5 - 21 - self.contact(-1) - 30)
        self.assertGreater(clear, unknown)
        self.assertGreater(unknown, explosive)
        self.assertEqual(self.score(5.5 - 21, True), 8)
        self.assertEqual(self.score(5.5 - 21 - 8 - 30, True), 8)

    def test_real_local_branch_keeps_costs_and_cannot_resurrect_second_blue(self):
        choose = function_body(MISSION.read_text(encoding="utf-8-sig"), "ChooseMove")
        local = choose[choose.index("if (bSafe)"):]
        capture = local.index("if (!bSecondBlue && MemoryPenalty > 0.0)")
        threshold = local.index("if (MemoryPenalty > 0.0 && CandidateScore <= BestScore)")
        self.assertLess(local.index("CandidateScore -= MemoryPenalty"), capture)
        self.assertLess(local.index("CandidateScore -= CoverRisk"), capture)
        self.assertLess(local.index("RouteConcealmentPenalty("), capture)
        self.assertLess(capture, threshold)
        self.assertIn("MemoryCandidateScore > MemoryFallbackRank", local)
        self.assertIn("MemoryFallbackPath = CandidatePath", local)
        self.assertIn("CandidateScore - CurrentScore, true", local)
        self.assertIn("if (MemoryPenalty <= 0.0 && CandidateScore <= BestScore)", local)
        self.assertIn("Score = ScoreOrdinaryRouteCandidate(BestScore - CurrentScore)", local)


if __name__ == "__main__":
    unittest.main()
