"""Score-read boundaries from the v27 dump and the stock latent-update API.

These run pure UC scheduling logic and source/API contracts, not a native
concurrency simulation, Windows build or in-game reproduction.
"""
import itertools
import os
from pathlib import Path
import unittest

from test_ui_gating import function_body, braced_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SCORE = CLASSES / 'APX_MissionScore.uc'
HUD = CLASSES / 'APX_UITacticalControl.uc'


class ScoreReadSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = SCORE.read_text()
        cls.hud = HUD.read_text()
        cls.can_query = staticmethod(load_uc_function(SCORE, 'CanQueryScoreHistory'))
        cls.should_refresh = staticmethod(load_uc_function(HUD, 'ShouldRefreshScoreForHUD'))
        cls.contribution = staticmethod(load_uc_function(SCORE, 'ChallengePointContribution'))

    def test_native_rollup_and_none_are_not_counted_twice(self):
        # Native GetTotalScore sums AddedPoints except None/TotalScore.
        rows = [(False, False, 5000), (False, False, 1900),
                (False, True, 6900), (True, False, 123456)]
        self.assertEqual(sum(self.contribution(*row) for row in rows), 6900)

    def test_native_awards_and_penalties_keep_signed_integer_values(self):
        rows = [(False, False, 10000), (False, False, -1000),
                (False, False, -5000), (False, False, 0)]
        self.assertEqual(sum(self.contribution(*row) for row in rows), 4000)
        self.assertEqual(self.contribution(False, False, -21200), -21200)

    def test_challenge_reader_uses_committed_score_states_without_force_rebuild(self):
        read = function_body(self.score, 'ReadChallengePoints')
        self.assertIn("History.IterateByClassType(class'XComGameState_ChallengeScore', Score)", read)
        self.assertIn('Score.ScoringType == CMPT_None', read)
        self.assertIn('Score.ScoringType == CMPT_TotalScore, Score.AddedPoints', read)
        self.assertNotIn('LadderBonus', read)
        self.assertNotIn('GetTotalScore(', self.score)
        self.assertNotIn('GetTotalScoreFromHistory(', self.score)
        self.assertNotIn('UpdateStateObjectCache(', self.score)
        self.assertLess(read.index('!CanReadScoreNow()'), read.index('IterateByClassType('))

    def test_bounded_reader_never_publishes_a_truncated_native_total(self):
        read = function_body(self.score, 'ReadChallengePoints')
        cap = read.index('if (++Inspected > 4096)')
        block = braced_body(read, read.index('{', cap))
        self.assertIn('Points = 0;', block)
        self.assertIn('return false;', block)
        self.assertLess(cap, read.index('Points += ChallengePointContribution('))
        provider = function_body(self.score, 'GetText')
        self.assertIn('if (!ReadChallengePoints(History, CurrentPoints))', provider)
        self.assertLess(provider.index('!ReadChallengePoints('),
                        provider.index('bHasNativePoints = true;'))

    def test_only_a_settled_ruleset_allows_reads(self):
        allowed = [(rules, building, submitting)
                   for rules, building, submitting in itertools.product((False, True), repeat=3)
                   if self.can_query(rules, building, submitting)]
        self.assertEqual(allowed, [(True, False, False)])

    def test_completed_worker_still_waits_for_main_thread_cleanup(self):
        # IsDoingLatentSubmission becomes false before EndLatentUpdate and
        # BuildingLatentGameState=false. The cleanup window must stay closed.
        states = [(True, True), (True, False), (False, False)]
        self.assertEqual([self.can_query(True, building, submitting)
                          for building, submitting in states], [False, False, True])

    def test_runtime_gate_checks_both_public_stock_flags(self):
        gate = function_body(self.score, 'CanReadScoreNow')
        self.assertIn('if (Rules == none)', gate)
        self.assertIn('return false;', gate)
        self.assertIn('CanQueryScoreHistory(true, Rules.BuildingLatentGameState,', gate)
        self.assertIn('Rules.IsDoingLatentSubmission()', gate)

    def test_provider_gate_precedes_history_comparison_and_native_aggregates(self):
        text = function_body(self.score, 'GetText')
        gate = text.index('if (!CanReadScoreNow())')
        self.assertLess(gate, text.index('History = `XCOMHISTORY;'))
        for operation in ('History.GetCurrentHistoryIndex()', 'History.FindStartStateIndex()',
                          'History.GetSingleGameStateObjectForClass(', 'CacheMatches(',
                          'ResetCache()', 'ComparisonCounter.GetObservedScore()',
                          'ReadChallengePoints(', 'Manager.GetMaxChallengeScore()',
                          'Manager.GetChallengeMaxPossibleScoreTable('):
            with self.subTest(operation=operation):
                self.assertLess(gate, text.index(operation))
        self.assertLess(text.index('bHasNativePoints = false;'), gate)
        self.assertLess(text.index('LastNativePoints = 0;'), gate)
        self.assertRegex(text[gate:], r'^if \(!CanReadScoreNow\(\)\)\s+return UnavailableText\(\);')

    def test_deferred_hud_preserves_only_same_history_text_without_refresh(self):
        display = function_body(self.hud, 'GetDisplayedScoreText')
        gate = display.index("if (!class'APX_MissionScore'.static.CanReadScoreNow())")
        deferred = braced_body(display, display.index('{', gate))
        self.assertIn('bScoreReadDeferred = true;', deferred)
        self.assertIn('!bScoreTextValid || History != CachedScoreHistory', deferred)
        self.assertIn('return ScoreCounter.UnavailableText();', deferred)
        self.assertIn('return CachedScoreText;', deferred)
        self.assertNotIn('GetCurrentHistoryIndex', deferred)
        self.assertNotIn('ScoreCounter.GetText()', deferred)
        self.assertNotIn('bScoreTextValid = true', deferred)
        self.assertNotIn('ScoreRefreshRemaining =', deferred)
        self.assertLess(gate, display.index('History.GetCurrentHistoryIndex()'))
        self.assertLess(gate, display.index('ScoreCounter.GetText()'))

    def test_next_safe_poll_keeps_due_or_changed_history_refresh_immediate(self):
        self.assertFalse(self.can_query(True, True, False))
        self.assertTrue(self.can_query(True, False, False))
        self.assertTrue(self.should_refresh(True, True, 0.8))
        self.assertTrue(self.should_refresh(True, False, -2.0))
        self.assertTrue(self.should_refresh(False, False, 0.8))

    def test_deferred_text_cannot_be_recorded_as_new_native_evidence(self):
        status = function_body(self.hud, 'UpdateStatus')
        self.assertIn('if (Controller != none && !bScoreReadDeferred)', status)
        self.assertLess(status.index('!bScoreReadDeferred'),
                        status.index('Controller.RecordDisplayedScore(ScoreText)'))
        native = function_body(self.score, 'ReadNativeMissionPoints')
        self.assertLess(native.index('GetText();'), native.index('return bHasNativePoints;'))
        self.assertIn('bScoreReadDeferred = false;', function_body(self.hud, 'Removed'))

    def test_score_safety_is_independent_of_autoplay_or_enemy_phase(self):
        for text in (function_body(self.score, 'CanReadScoreNow'),
                     function_body(self.score, 'GetText'),
                     function_body(self.hud, 'GetDisplayedScoreText')):
            self.assertNotIn('Controller.IsEnabled()', text)
            self.assertNotIn('eTeam_Alien', text)
            self.assertNotIn('eTeam_XCom', text)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Private SDK contract')
class ScoreReadSafetySDKTests(unittest.TestCase):
    def test_native_score_fields_and_rollup_enum_are_stock(self):
        root = Path(os.environ['APX_SDK_SOURCE_ROOT']) / 'XComGame/Classes'
        score = (root / 'XComGameState_ChallengeScore.uc').read_text()
        self.assertIn('var ChallengeModePointType ScoringType;', score)
        self.assertIn('var int AddedPoints;', score)
        types = (root / 'X2ChallengeModeDataStructures.uc').read_text()
        self.assertIn('CMPT_TotalScore', types)
        self.assertIn('CMPT_None', types)

    def test_guards_cover_worker_and_cleanup_boundary_in_stock_tick(self):
        path = Path(os.environ['APX_SDK_SOURCE_ROOT']) / 'XComGame/Classes/X2GameRuleset.uc'
        source = path.read_text(encoding='utf-8-sig', errors='replace')
        self.assertIn('var privatewrite bool BuildingLatentGameState;', source)
        self.assertIn('native function bool IsDoingLatentSubmission();', source)
        tick = function_body(source, 'Tick')
        self.assertIn('if( ! IsDoingLatentSubmission() )', tick)
        self.assertLess(tick.index('`XCOMHISTORY.EndLatentUpdate();'),
                        tick.index('BuildingLatentGameState = false;'))
