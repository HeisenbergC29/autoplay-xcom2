"""Regressions for the real report's vanished-contact/partial-reload sequence."""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body


CLASSES = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
CONTROLLER = CLASSES / 'APX_Controller.uc'
COMBAT = CLASSES / 'APX_CombatPlanner.uc'


class RecentContactTests(unittest.TestCase):
    def test_confirmed_own_kills_clear_contact_memory_using_historical_visible_result(self):
        source = CONTROLLER.read_text()
        prune = function_body(source, 'PruneObservedDefeats')
        self.assertIn('SourceUnit.GetAssociatedPlayerID() != PlayerID', prune)
        self.assertIn("VisibleBefore.Find('ObjectID', TargetRef.ObjectID) == INDEX_NONE", prune)
        self.assertIn('PlayerID, VisibleBefore, ContactHistoryCursor - 1', prune)
        self.assertIn('TargetRef.ObjectID, eReturnType_Reference, ContactHistoryCursor)', prune)
        self.assertIn('BeforeUnit.IsAlive() && !AfterUnit.IsAlive()', prune)
        self.assertIn('RecentContacts.Remove(ContactIndex, 1)', prune)
        self.assertIn('ContactHistoryCursor + 512', prune)
        decision = function_body(source, 'MakeDecision')
        self.assertLess(decision.index('PruneObservedDefeats('),
                        decision.index('bContactSearch = !bVisibleThreats'))

    def test_surviving_contact_remains_relevant_next_turn_but_expires(self):
        fresh = load_uc_function(CONTROLLER, 'IsContactFresh')
        self.assertTrue(fresh(3, 2, 2))  # Report: turn 2 survivor, turn 3 no sight.
        self.assertTrue(fresh(4, 2, 2))
        self.assertFalse(fresh(5, 2, 2))
        self.assertFalse(fresh(1, 2, 2))  # A rewound history cannot retain a future contact.

    def test_nearly_full_magazine_does_not_displace_guard_after_contact_loss(self):
        reload_score = load_uc_function(COMBAT, 'ScorePartialReload')
        overwatch = load_uc_function(COMBAT, 'ScoreOverwatchDefense')
        self.assertLess(reload_score(False, True), overwatch(True, False, 1.0, 0.0, 0))
        self.assertEqual(reload_score(False, False), 12.0)
        self.assertEqual(reload_score(True, False), 3.0)

    def test_empty_weapon_reloads_before_investigation_then_can_guard(self):
        reload_score = load_uc_function(COMBAT, 'ScoreEmptyReload')
        self.assertGreater(reload_score(False, True), 20.0)  # Contact search priority.
        self.assertGreater(reload_score(False, True), 17.0)  # Reaction-shot priority.
        self.assertEqual(reload_score(True, False), 35.0)
        self.assertEqual(reload_score(False, False), 18.0)

    def test_contact_locations_are_only_updated_from_visible_references(self):
        source = CONTROLLER.read_text()
        update = function_body(source, 'RefreshContacts')
        self.assertLess(update.index('foreach VisibleEnemies(EnemyRef)'),
                        update.index('RecentContacts[Index].LastSeenTile = Enemy.TileLocation;'))
        search = function_body(source, 'ChooseContactSearchMove')
        self.assertIn('RecentContacts[Index].LastSeenTile', search)
        self.assertNotIn('GetGameStateForObjectID', search)
        self.assertIn('RecentContacts.Length >= 128', update)

    def test_recent_contact_mode_blocks_ordinary_exploration_and_preserves_response(self):
        source = CONTROLLER.read_text()
        decision = function_body(source, 'MakeDecision')
        self.assertIn('bCombatThreats = bVisibleThreats || bContactSearch;', decision)
        self.assertIn("if (bContactSearch && !class'APX_MissionPlanner'.static.ShouldEvacuate(UnitState))", decision)
        self.assertIn('ChooseContactSearchMove(UnitState, CandidatePath, Score)', decision)
        self.assertIn('ExplorationPlanner != none && !bCombatThreats', decision)
        search = function_body(source, 'ChooseContactSearchMove')
        self.assertIn('UnitState.NumActionPoints() < 2', search)
        self.assertIn('FClamp(ContactSearchDistance, 1.0, 6.0)', search)
        self.assertIn('Path[Index].Z > UnitState.TileLocation.Z + 1', search)

    def test_grenade_rejection_summary_is_recorded_after_failed_scans_too(self):
        decision = function_body(CONTROLLER.read_text(), 'MakeDecision')
        scan = decision.index('bGrenadeCandidate = AreaPlanner.ChooseAction(')
        summary = decision.index('AreaPlanner.GetDiagnosticSummary()')
        accepted_branch = decision.index('if (bGrenadeCandidate')
        self.assertLess(scan, summary)
        self.assertLess(summary, accepted_branch)


if __name__ == '__main__':
    unittest.main()
