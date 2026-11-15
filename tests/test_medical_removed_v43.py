"""Removed patients cannot become useful merely through a removable status.

The scorer is loaded from the actual UnrealScript. This checks selection
policy, not WOTC native target-cache execution or a gameplay scenario.
"""
from pathlib import Path
import unittest

from uc_math import load_uc_function
from test_ui_gating import function_body

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"


class RemovedMedicalPatientPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = staticmethod(load_uc_function(SRC / "APX_MedicalApproach.uc",
                                                 "ScoreUsefulHealing"))

    def test_removed_poisoned_patient_keeps_hard_veto_at_any_health_score(self):
        for base in (-10000, 20, 140):
            for poisoned in (False, True):
                with self.subTest(base=base, poisoned=poisoned):
                    self.assertLess(self.score(base, True, poisoned, False, True), -1000)

    def test_live_full_health_detox_and_existing_healing_remain_useful(self):
        self.assertEqual(self.score(-10000, True, True, False, False), 170)
        self.assertEqual(self.score(-10000, True, False, False, False), 105)
        self.assertEqual(self.score(140, False, False, False, False), 140)
        self.assertEqual(self.score(140, True, True, False), 195)
        self.assertLess(self.score(-10000, False, True, False, False), -1000)
        self.assertLess(self.score(140, True, True, True, False), -1000)

    def test_native_chooser_passes_actual_removed_state_into_promotion(self):
        choose = function_body((SRC / "APX_CombatPlanner.uc").read_text(encoding="utf-8-sig"),
                               "ChooseAction")
        self.assertIn("TargetUnit.bRemoved || TargetUnit.bRemovedFromPlay", choose)


if __name__ == "__main__":
    unittest.main()
