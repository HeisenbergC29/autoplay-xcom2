"""Regression for ability results lost when ownership changes in that frame.

Numeric policies execute their actual UC bodies. Native history/visibility
boundaries are source contracts, not a substitute for Windows/game testing.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body


ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_MissionRecorder.uc'


class RecorderOwnershipContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RECORDER.read_text()
        cls.relevant = staticmethod(load_uc_function(RECORDER, 'ResultInvolvesLocalUnit'))
        cls.previous = staticmethod(load_uc_function(RECORDER, 'ResultPreviousHistoryIndex'))

    def test_transferred_targets_and_sources_keep_the_native_result(self):
        # Successful enemy mind control: neither source nor target is owned
        # after the frame, but the target was ours before that same frame.
        self.assertTrue(self.relevant(False, False, True))
        # A source can also stop being ours during its ability's result.
        self.assertTrue(self.relevant(False, True, False))
        self.assertTrue(self.relevant(True, False, False))
        self.assertFalse(self.relevant(False, False, False))

    def test_previous_frame_cannot_alias_current_or_cross_the_mission_start(self):
        for result, start in ((-1, 0), (0, 0), (1, -1), (5, 5), (4, 5)):
            with self.subTest(result=result, start=start):
                self.assertEqual(self.previous(result, start), -1)
        self.assertEqual(self.previous(6, 5), 5)
        self.assertEqual(self.previous(100, 0), 99)

    def test_primary_and_secondary_target_redaction_share_ownership_transition(self):
        results = function_body(self.source, 'RecordResults')
        across = function_body(self.source, 'IsOwnUnitAcrossResult')
        self.assertIn('IsOwnUnitAt(ObjectID, ResultHistoryIndex)', across)
        self.assertIn('IsOwnUnitAt(ObjectID, BeforeHistoryIndex)', across)
        previous = across.index('IsOwnUnitAt(ObjectID, BeforeHistoryIndex)')
        for guard in ('BeforeHistoryIndex >= 0',
                      'BeforeHistoryIndex >= RecordedStartStateIndex',
                      'BeforeHistoryIndex < ResultHistoryIndex'):
            self.assertLess(across.index(guard), previous)
        self.assertIn('bPrimaryOwnTarget = IsOwnUnitAcrossResult(TargetID, HistoryCursor, BeforeHistoryIndex)', results)
        self.assertIn('bOwnTarget = bPrimaryOwnTarget', results)
        relevance = results.index('if (!ResultInvolvesLocalUnit(')
        self.assertIn('TargetRef.ObjectID, HistoryCursor, BeforeHistoryIndex', results[:relevance])
        self.assertIn('if (!bPrimaryOwnTarget', results[relevance:])
        secondary = results[results.index('for (TargetIndex ='):]
        self.assertIn('!IsOwnUnitAcrossResult(TargetID, HistoryCursor, BeforeHistoryIndex)', secondary)

    def test_source_scope_still_describes_post_action_observation(self):
        results = function_body(self.source, 'RecordResults')
        self.assertIn('ResultPreviousHistoryIndex(HistoryCursor, RecordedStartStateIndex)', results)
        self.assertIn('if (!bOwnAction && BeforeHistoryIndex >= 0)', results)
        self.assertIn('bOwnActionBefore = IsOwnUnitAt(SourceID, BeforeHistoryIndex)', results)
        scope = results[results.index('bSourceVisible ='):results.index('AbilityName =')]
        self.assertIn('if (bOwnAction)', scope)
        self.assertNotIn('bOwnActionBefore', scope)
        self.assertIn('SourceID = 0;', results)
        self.assertIn('string(Context.ResultContext.HitResult)', results)
        self.assertIn('Context.ResultContext.MultiTargetHitResults[TargetIndex]', results)


if __name__ == '__main__':
    unittest.main()
