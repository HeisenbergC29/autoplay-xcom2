"""Native HUD mission-score boundaries, without simulating the native engine.

Execute the small UC arithmetic/identity/baseline helpers. SDK contracts prove
which native read APIs back the display; Windows/game validation is separate.
"""
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

from test_ui_gating import CHECKS, braced_body, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionScore.uc'


def battle(identity=10, mission='ChallengeAbductionCemetery'):
    return SimpleNamespace(ObjectID=identity, MapData=SimpleNamespace(
        ActiveMission=SimpleNamespace(sType=mission)))


def ladder(identity=20, index=1, rung=2, points=16000):
    return SimpleNamespace(ObjectID=identity, LadderIndex=index,
                           LadderRung=rung, CumulativeScore=points)


class MissionScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text()
        cls.points = staticmethod(load_uc_function(SOURCE, 'MissionPoints'))
        cls.matches = staticmethod(load_uc_function(SOURCE, 'CacheMatches'))
        cls.baseline = staticmethod(load_uc_function(SOURCE, 'ReadLadderBaseline'))

    def setUp(self):
        self.history = object()
        self.matches.__globals__.update(
            none=None, CachedHistory=self.history, CachedStartIndex=50,
            CachedBattleID=10, CachedMissionType='ChallengeAbductionCemetery',
            CachedLadderID=20, CachedLadderIndex=1, CachedLadderRung=2,
            CachedChallengeID=0, LastHistoryIndex=100)

    def test_mission_points_exclude_previous_rungs_and_allow_penalties(self):
        self.assertEqual(self.points(16000, 16000), 0)
        self.assertEqual(self.points(19500, 16000), 3500)
        self.assertEqual(self.points(15000, 16000), -1000)
        self.assertEqual(self.points(11000, 16000), -5000)

    def test_display_keeps_native_integer_values_without_clamping_or_percentages(self):
        body = function_body(self.source, 'FormatPoints')
        expression = re.fullmatch(r'\s*return\s+(.+);\s*', body, re.S)[1]
        expression = expression.replace('$', '+').replace('string(', 'str(')
        for current, maximum, expected in ((0, 30000, '0/30000'),
                                            (12500, 64000, '12500/64000'),
                                            (-1000, 64000, '-1000/64000'),
                                            (65000, 64000, '65000/64000')):
            self.assertEqual(eval(expression, {'str': str, 'CurrentPoints': current,
                                               'MaximumPoints': maximum}), expected)

    def test_unknown_maximum_preserves_the_known_current_score(self):
        text = CHECKS.without_comments(function_body(self.source, 'GetText'))
        expression = re.search(r'if\s*\(MaximumPoints <= 0\)\s*return\s+([^;]+);', text)[1]
        expression = expression.replace('$', '+').replace('string(', 'str(')
        for current, unavailable, expected in ((1200, '—', '1200/—'),
                                               (0, '—', '0/—'),
                                               (-1000, '—', '-1000/—'),
                                               (1200, '--', '1200/--')):
            with self.subTest(current=current, unavailable=unavailable):
                self.assertEqual(eval(expression, {'str': str, 'CurrentPoints': current,
                                                  'UnavailableText': lambda: unavailable}), expected)
        # A missing maximum must be retried, rather than cached as zero.
        self.assertLess(text.index('return string(CurrentPoints) $ "/" $ UnavailableText()'),
                        text.index('CachedMaximum = MaximumPoints'))

    def test_unscored_mission_has_marked_comparison_without_native_getters(self):
        text = function_body(self.source, 'GetText')
        mode_guard = text.index('if (Ladder == none && ChallengeData == none)')
        unscored = braced_body(text, text.index('{', mode_guard))
        self.assertIn("ComparisonCounter = new(self) class'APX_ComparisonScore'", unscored)
        self.assertIn('ComparisonCounter.GetObservedScore()', unscored)
        self.assertIn('if (!ComparisonCounter.IsReady())', unscored)
        self.assertIn('return UnavailableText()', unscored)
        self.assertIn('return "~" $ string(ComparisonPoints) $ "/" $ UnavailableText()', unscored)
        self.assertNotIn('Manager.', unscored)
        self.assertNotIn('ResetCache()', unscored)
        self.assertLess(mode_guard, text.index('Manager = `CHALLENGEMODE_MGR'))
        self.assertRegex(text, r'if \(!bHasBaseline && !ReadLadderBaseline\(History, BattleData, Ladder\)\)\s*return UnavailableText\(\);')

    def test_comparison_lifetime_ends_on_mission_reset_and_hud_removal(self):
        cleanup = function_body(self.source, 'Cleanup')
        self.assertIn('ComparisonCounter.Cleanup()', cleanup)
        self.assertIn('ComparisonCounter = none', cleanup)
        self.assertIn('Cleanup()', function_body(self.source, 'ResetCache'))
        hud = (SOURCE.parent / 'APX_UITacticalControl.uc').read_text()
        self.assertIn('ScoreCounter.Cleanup()', function_body(hud, 'Removed'))
        self.matches.__globals__.update(CachedLadderID=0, CachedChallengeID=0)
        self.assertTrue(self.matches(self.history, 50, battle(), None, None, 100))
        self.assertFalse(self.matches(self.history, 50, battle(), ladder(), None, 100))

    def test_unchanged_mission_retains_cached_maximum_across_actions(self):
        self.assertTrue(self.matches(self.history, 50, battle(), ladder(), None, 100))
        self.assertTrue(self.matches(self.history, 50, battle(), ladder(points=19000), None, 300))

    def test_history_replacement_rewind_mission_and_rung_changes_invalidate_cache(self):
        cases = (
            (object(), 50, battle(), ladder(), None, 100),
            (self.history, 60, battle(), ladder(), None, 100),
            (self.history, 50, battle(identity=11), ladder(), None, 100),
            (self.history, 50, battle(mission='OtherMission'), ladder(), None, 100),
            (self.history, 50, battle(), ladder(identity=21), None, 100),
            (self.history, 50, battle(), ladder(index=2), None, 100),
            (self.history, 50, battle(), ladder(rung=3), None, 100),
            (self.history, 50, battle(), ladder(), None, 99),
            (self.history, 50, battle(), None, None, 100),
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                self.assertFalse(self.matches(*arguments))

    def test_challenge_identity_cannot_reuse_a_legacy_maximum(self):
        challenge = SimpleNamespace(ObjectID=30)
        self.assertFalse(self.matches(self.history, 50, battle(), None, challenge, 100))
        self.matches.__globals__.update(CachedLadderID=0, CachedChallengeID=30)
        self.assertTrue(self.matches(self.history, 50, battle(), None, challenge, 100))
        self.assertFalse(self.matches(self.history, 50, battle(), None,
                                      SimpleNamespace(ObjectID=31), 100))

    def read_baseline(self, starting_battle, starting_ladder):
        calls = []

        def get_object(identity, return_type, history_index):
            calls.append((identity, return_type, history_index))
            return {10: starting_battle, 20: starting_ladder}[identity]

        self.baseline.__globals__.update(
            none=None, eReturnType_Reference='reference', CachedStartIndex=50,
            CachedMissionType='ChallengeAbductionCemetery',
            XComGameState_BattleData=lambda value: value,
            XComGameState_LadderProgress=lambda value: value)
        result = self.baseline(SimpleNamespace(GetGameStateForObjectID=get_object),
                               battle(), ladder(points=19500))
        return result, calls

    def test_mid_mission_baseline_reads_the_original_tactical_history(self):
        valid, calls = self.read_baseline(battle(), ladder(points=16000))
        self.assertTrue(valid)
        self.assertEqual(calls, [(10, 'reference', 50), (20, 'reference', 50)])
        self.assertIn('CachedBaseline = StartingLadder.CumulativeScore',
                      function_body(self.source, 'ReadLadderBaseline'))

    def test_missing_or_different_start_state_never_fabricates_a_baseline(self):
        for initial_battle, initial_ladder in (
                (None, ladder()), (battle(), None),
                (battle(identity=11), ladder()),
                (battle(mission='OtherMission'), ladder()),
                (battle(), ladder(identity=21)),
                (battle(), ladder(index=2)), (battle(), ladder(rung=1))):
            with self.subTest(battle=initial_battle, ladder=initial_ladder):
                self.assertFalse(self.read_baseline(initial_battle, initial_ladder)[0])

    def test_native_apis_require_a_scored_mode_and_valid_baseline(self):
        text = function_body(self.source, 'GetText')
        mode_guard = text.index('if (Ladder == none && ChallengeData == none)')
        self.assertLess(mode_guard, text.index('Manager = `CHALLENGEMODE_MGR'))
        self.assertLess(text.index('!ReadLadderBaseline(History, BattleData, Ladder)'),
                        text.index('MissionPoints(Ladder.CumulativeScore, CachedBaseline)'))
        self.assertIn('StartIndex = History.FindStartStateIndex()', text)
        self.assertIn('MaximumPoints = Manager.GetChallengeMaxPossibleScoreTable(ScoreTable)', text)
        self.assertIn('CurrentPoints = Manager.GetTotalScore()', text)
        self.assertIn('MaximumPoints = Manager.GetMaxChallengeScore()', text)
        self.assertIn('if (MaximumPoints <= 0)', text)
        self.assertIn('return FormatPoints(CurrentPoints, CachedMaximum)', text)

    def test_maximum_is_only_read_until_valid_and_not_reduced_by_scoring_events(self):
        text = function_body(self.source, 'GetText')
        self.assertEqual(text.count('if (!bHasMaximum)'), 3)
        self.assertIn('CachedMaximum = MaximumPoints', text)
        self.assertIn('bHasMaximum = true', text)
        self.assertIn('bHasMaximum = false', function_body(self.source, 'ResetCache'))
        self.assertIn('HistoryIndex < LastHistoryIndex', function_body(self.source, 'CacheMatches'))
        self.assertNotIn('CachedMaximum -=', self.source)
        self.assertNotIn('CachedMaximum +=', self.source)

    def test_missing_state_uses_localized_unavailable_with_ascii_fallback(self):
        unavailable = function_body(self.source, 'UnavailableText')
        self.assertIn('Len(UnavailableLabel) > 0', unavailable)
        self.assertIn('return UnavailableLabel', unavailable)
        self.assertIn('return "--"', unavailable)
        self.assertIn('var localized string UnavailableLabel', self.source)

    def test_display_never_mutates_history_awards_points_or_inspects_hidden_units(self):
        source = CHECKS.without_comments(self.source)
        forbidden = r'\b(?:AddKillMail|AddTacticalGameEnd|AddMissionObjectiveComplete|AddIndividualMissionObjectiveComplete|AddCivilianRescued|ModifyStateObject|CreateNewGameState|CreateStateObject|SubmitGameState|SetCurrentHistoryIndex|Init|Rand|FRand)\s*\('
        self.assertIsNone(re.search(forbidden, source))
        self.assertNotIn("class'XComGameState_Unit'", source)
        self.assertNotIn('IterateByClassType', source)
        self.assertNotIn('GetEnemyScoring', source)
        self.assertNotIn('APX_CombatPlanner', source)
        self.assertNotIn('APX_Controller', source)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Native score contracts need SDK sources')
class MissionScoreSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_legacy_dialog_and_challenge_summary_use_the_same_native_getters(self):
        dialog = function_body((self.sdk / 'UILadderModeScoringDialog.uc').read_text(encoding='utf-8-sig'), 'OnInit')
        self.assertIn('maxscore = ChallengeModeManager.GetChallengeMaxPossibleScoreTable(ScoreTable)', dialog)
        summary = (self.sdk / 'UIChallengePostScreen.uc').read_text(encoding='utf-8-sig')
        self.assertIn('ChallengeScore = ChallengeModeManager.GetTotalScore()', summary)
        self.assertIn('MaxChallengeScore = ChallengeModeManager.GetMaxChallengeScore()', summary)
        manager = (self.sdk / 'XComChallengeModeManager.uc').read_text(encoding='utf-8-sig')
        for signature in ('final native function int GetTotalScore();',
                          'final native function int GetMaxChallengeScore(optional int ChallengeIdx = -1);',
                          'final native function int GetChallengeMaxPossibleScoreTable(out array<ScoreTableEntry> ScoreTable, optional int ChallengeIdx = -1);'):
            self.assertIn(signature, manager)

    def test_history_start_lookup_and_ladder_carry_are_real_sdk_contracts(self):
        history = (self.sdk / 'XComGameStateHistory.uc').read_text(encoding='utf-8-sig')
        self.assertIn('native final function int FindStartStateIndex();', history)
        self.assertIn('optional int HistoryIndex=-1', history)
        self.assertIn('native final function XComGameState_BaseObject GetGameStateForObjectID(', history)
        ladder_source = (self.sdk / 'XComGameState_LadderProgress.uc').read_text(encoding='utf-8-sig')
        self.assertIn('NextMissionLadder.CumulativeScore = LadderData.CumulativeScore', ladder_source)
        self.assertIn('LadderData.CumulativeScore -= SoldierScoring.UninjuredBonus', ladder_source)


if __name__ == '__main__':
    unittest.main()
