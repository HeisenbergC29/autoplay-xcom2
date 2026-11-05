"""Confirm the stock end-turn request from history rather than its false return.

Pure helpers execute their actual UC bodies. SDK contracts explain why the
return is not an acknowledgement; asynchronous native behavior needs game tests.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body
from uc_math import load_uc_function


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_Controller.uc'


class EndTurnSubmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CONTROLLER.read_text()
        cls.matches = staticmethod(load_uc_function(CONTROLLER, 'IsMatchingEndTurnEvidence'))
        cls.transition = staticmethod(load_uc_function(CONTROLLER, 'HasEndTurnTransition'))
        cls.expired = staticmethod(load_uc_function(CONTROLLER, 'EndTurnWaitExpired'))

    def test_only_new_skip_turn_for_the_requested_positive_player_is_evidence(self):
        self.assertTrue(self.matches(True, 2, 2))
        for args in ((False, 2, 2), (True, 2, 3), (True, 0, 0), (True, -1, -1)):
            with self.subTest(args=args):
                self.assertFalse(self.matches(*args))

    def test_actual_player_or_own_turn_transition_is_evidence_but_rewind_is_not(self):
        self.assertTrue(self.transition(2, 7, 3, 7))
        self.assertTrue(self.transition(2, 7, 2, 8))
        for args in ((2, 7, 2, 7), (2, 7, 0, 7), (2, 7, 3, 6),
                     (0, 7, 3, 8), (2, -1, 3, 0)):
            with self.subTest(args=args):
                self.assertFalse(self.transition(*args))

    def test_an_unconfirmed_request_has_a_finite_active_wait_budget(self):
        for value in (0, 0.01, 4.99):
            self.assertFalse(self.expired(value))
        for value in (5, 6, 1000):
            self.assertTrue(self.expired(value))
        poll = function_body(self.source, 'PollEndTurnRequest')
        self.assertIn('EndTurnWaitSeconds += FMax(0.0, DeltaTime)', poll)
        self.assertIn('EndTurnWaitExpired(EndTurnWaitSeconds)', poll)
        self.assertIn('End turn was not confirmed by game history', poll)

    def test_native_return_is_diagnostic_and_does_not_decide_rejection(self):
        request = function_body(self.source, 'RequestEndTurn')
        self.assertIn('bNativeReturn = PC.PerformEndTurn(ePlayerEndTurnType_PlayerInput)', request)
        self.assertIn('"native_return=" $ string(bNativeReturn)', request)
        self.assertNotRegex(request, r'if\s*\([^)]*bNativeReturn')
        self.assertIn('PollEndTurnRequest(0.0)', request)
        decision = function_body(self.source, 'MakeDecision')
        self.assertIn('RequestEndTurn(PC)', decision)
        self.assertNotIn('PerformEndTurn(', decision)
        self.assertNotIn('Engine rejected end turn', decision)

    def test_request_snapshots_local_player_turn_battle_and_history_before_native_call(self):
        request = function_body(self.source, 'RequestEndTurn')
        submit = request.index('PC.PerformEndTurn(')
        for field in ('EndTurnHistory = `XCOMHISTORY', 'EndTurnPlayerID = CurrentPlayer.ObjectID',
                      'EndTurnPlayerTurn = PlayerState.PlayerTurnCount',
                      'EndTurnBattleID = BattleData.ObjectID',
                      'EndTurnStartStateIndex = EndTurnHistory.FindStartStateIndex()',
                      'EndTurnRequestHistory = EndTurnHistory.GetCurrentHistoryIndex()',
                      'EndTurnHistoryCursor = EndTurnRequestHistory', 'bEndTurnPending = true'):
            self.assertLess(request.index(field), submit)
        for guard in ('CurrentPlayer.ObjectID != PC.m_XGPlayer.ObjectID',
                      'CurrentPlayer.ObjectID != `TACTICALRULES.GetLocalClientPlayerObjectID()',
                      'bEndTurnPending || bEndTurnRequested'):
            self.assertIn(guard, request)

    def test_history_confirmation_is_incremental_bounded_and_requires_matching_skip_turn(self):
        poll = function_body(self.source, 'PollEndTurnRequest')
        self.assertIn('EndTurnHistoryCursor + 256', poll)
        self.assertIn('bEndTurnRequested && !EndTurnTicketIsCurrent()', poll)
        self.assertIn('while (EndTurnHistoryCursor < ScanEnd)', poll)
        self.assertIn('++EndTurnHistoryCursor', poll)
        self.assertIn('GetGameStateFromHistory(EndTurnHistoryCursor)', poll)
        self.assertIn('XComGameStateContext_TacticalGameRule(Frame.GetContext())', poll)
        self.assertIn('RuleContext.GameRuleType == eGameRule_SkipTurn', poll)
        self.assertIn('EndTurnPlayerID, RuleContext.PlayerRef.ObjectID', poll)
        self.assertNotIn('SubmitGameState', poll)
        self.assertNotIn('PerformEndTurn(', poll)
        current = function_body(self.source, 'EndTurnTicketIsCurrent')
        for guard in ('EndTurnHistory != `XCOMHISTORY',
                      'FindStartStateIndex() != EndTurnStartStateIndex',
                      'GetCurrentHistoryIndex() < EndTurnRequestHistory',
                      'BattleData.ObjectID == EndTurnBattleID'):
            self.assertIn(guard, current)

    def test_pending_confirmation_runs_before_hud_and_game_rules_waits_but_not_while_paused(self):
        tick = function_body(self.source, 'Tick')
        poll = tick.index('PollEndTurnRequest(DeltaTime)')
        self.assertLess(tick.index('if (!bEnabled)'), poll)
        self.assertLess(tick.index('WorldInfo.Pauser != none'), poll)
        self.assertLess(poll, tick.index('UIBlockReason = GetUIBlockReason('))
        self.assertLess(poll, tick.index("IsInState('TurnPhase_UnitActions')"))

    def test_pending_and_confirmed_tickets_block_duplicates_even_after_same_turn_toggle(self):
        decision = function_body(self.source, 'MakeDecision')
        reset = decision[decision.index('if (PlayerState.PlayerTurnCount != LastTurn)'):
                         decision.index('if (bEndTurnPending || bEndTurnRequested)')]
        self.assertIn('!EndTurnTicketIsCurrent()', reset)
        self.assertIn('EndTurnPlayerID != PlayerRef.ObjectID', reset)
        self.assertIn('EndTurnPlayerTurn != PlayerState.PlayerTurnCount', reset)
        self.assertIn('ResetEndTurnRequest()', reset)
        self.assertNotIn('bEndTurnRequested = false', reset)
        confirmed = function_body(self.source, 'ConfirmEndTurnRequest')
        self.assertIn('bEndTurnPending = false', confirmed)
        self.assertIn('bEndTurnRequested = true', confirmed)
        self.assertIn('"end_turn_confirmed"', confirmed)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'End-turn contracts need SDK sources')
class EndTurnSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'

    def test_stock_end_turn_submits_skip_turn_but_returns_false(self):
        player = (self.sdk / 'XGPlayer.uc').read_text(encoding='utf-8-sig')
        end = function_body(player, 'EndTurn')
        self.assertIn('EndTurnContext.GameRuleType = eGameRule_SkipTurn', end)
        self.assertIn('EndTurnContext.PlayerRef = TacticalRules.GetCachedUnitActionPlayerRef()', end)
        self.assertIn('SubmitGameStateContext(EndTurnContext)', end)
        self.assertRegex(end, r'return false;\s*$')
        self.assertNotIn('return true', end)
        controller = (self.sdk / 'XComTacticalController.uc').read_text(encoding='utf-8-sig')
        internal = function_body(controller, 'InternalPerformEndTurn')
        self.assertIn('bEndTurnResult = m_XGPlayer.EndTurn(eEndTurnType)', internal)
        self.assertIn('return bEndTurnResult', internal)

    def test_history_context_and_public_player_read_apis_exist(self):
        rule = (self.sdk / 'XComGameStateContext_TacticalGameRule.uc').read_text(encoding='utf-8-sig')
        self.assertIn('eGameRule_SkipTurn', rule)
        self.assertTrue(re.search(r'var\s+GameRuleStateChange\s+GameRuleType;', rule),
                        'SDK tactical context exposes GameRuleType')
        self.assertTrue(re.search(r'var\s+StateObjectReference\s+PlayerRef;', rule),
                        'SDK tactical context exposes PlayerRef')
        rules = (self.sdk / 'X2TacticalGameRuleset.uc').read_text(encoding='utf-8-sig')
        self.assertIn('simulated native function int GetLocalClientPlayerObjectID()', rules)
        self.assertIn('function StateObjectReference GetCachedUnitActionPlayerRef()', rules)


if __name__ == '__main__':
    unittest.main()
