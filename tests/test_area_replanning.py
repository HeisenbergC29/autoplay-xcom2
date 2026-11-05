"""A failed grenade preview rejects that plan, without dispatch or global OFF."""
from pathlib import Path
import unittest

from test_ui_gating import function_body, braced_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_Controller.uc'


class AreaReplanningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CONTROLLER.read_text()
        cls.retry = staticmethod(load_uc_function(CONTROLLER, 'MayRetryAreaPlan'))

    def test_same_rejected_state_never_retries_and_rewind_is_not_progress(self):
        for rejected in (0, 100, 2500):
            self.assertFalse(self.retry(rejected, rejected, 1))
            self.assertFalse(self.retry(rejected - 1, rejected, 1))

    def test_changed_state_may_retry_with_a_strict_per_ability_turn_budget(self):
        self.assertTrue(self.retry(101, 100, 1))
        self.assertTrue(self.retry(102, 101, 2))
        self.assertFalse(self.retry(103, 102, 3))
        self.assertFalse(self.retry(10000, 102, 128))

    def test_reported_invalid_70_point_grenade_leaves_35_point_reload_available(self):
        choices = [('grenade', 70), ('reload', 35)]
        allowed = [choice for choice in choices
                   if choice[0] != 'grenade' or self.retry(1500, 1500, 1)]
        self.assertEqual(max(allowed, key=lambda item: item[1]), ('reload', 35))
        decision = function_body(self.source, 'MakeDecision')
        self.assertIn('bGrenadeCandidate && CanUseAreaPlan(UnitState, Candidate)', decision)

    def test_cache_resets_only_on_native_scope_change_and_survives_manual_toggle(self):
        scope = function_body(self.source, 'RefreshAreaRejectionScope')
        for check in ('AreaRejectionHistory != `XCOMHISTORY',
                      'AreaRejectionPlayerID != PlayerID', 'AreaRejectionTurn != PlayerTurn',
                      'CurrentHistory < AreaRejectionLastHistory'):
            self.assertIn(check, scope)
        self.assertIn('RejectedAreaPlans.Length = 0', scope)
        self.assertNotIn('RejectedAreaPlans', function_body(self.source, 'Toggle'))
        decision = function_body(self.source, 'MakeDecision')
        self.assertLess(decision.index('RefreshAreaRejectionScope('),
                        decision.index('PlayerState.PlayerTurnCount != LastTurn'))

    def test_cache_saturation_cannot_evict_a_rejection_and_enable_an_infinite_retry(self):
        remember = function_body(self.source, 'RememberRejectedAreaPlan')
        self.assertIn('RejectedAreaPlans.Length >= 128', remember)
        self.assertIn('bAreaRejectionSaturated = true', remember)
        self.assertNotIn('RejectedAreaPlans.Remove(', remember)
        self.assertIn('bAreaRejectionSaturated', function_body(self.source, 'CanUseAreaPlan'))

    def test_revalidation_failure_records_reason_and_returns_before_activation_without_stopping(self):
        decision = function_body(self.source, 'MakeDecision')
        start = decision.index('if (bArea && !AreaPlanner.PrepareForActivation(')
        rejected = braced_body(decision, decision.index('{', start))
        for operation in ('RememberRejectedAreaPlan(', 'area_revalidation_rejected',
                          'GetPreparationDiagnostic()', 'UntilDecision =', 'return;'):
            self.assertIn(operation, rejected)
        for forbidden in ('StopAutoplay(', 'StopWithStatus(', 'ActivateAbility_ReturnContext(',
                          'RecordAction(', '++ActionsThisTurn'):
            self.assertNotIn(forbidden, rejected)
        self.assertLess(start, decision.index('ActivateAbility_ReturnContext('))

    def test_timeout_keeps_end_turn_ticket_and_waits_until_history_has_been_scanned(self):
        poll = function_body(self.source, 'PollEndTurnRequest')
        start = poll.index('if (EndTurnWaitExpired(')
        self.assertIn('EndTurnHistoryCursor >= EndIndex', poll[start:])
        timeout = braced_body(poll, poll.index('{', start))
        self.assertNotIn('ResetEndTurnRequest(', timeout)
        self.assertIn('StopWithStatus(', timeout)


if __name__ == '__main__':
    unittest.main()
