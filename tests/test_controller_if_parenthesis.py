"""Regression: the v32 Windows compiler rejected a missing closing 'if' paren.

Source-level guard only; a successful Python test does NOT prove WOTC make.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_Controller.uc"


class NativeCombatDecisionSyntaxTests(unittest.TestCase):
    def test_choose_action_if_condition_closes_before_open_brace(self):
        source = CONTROLLER.read_text(encoding="utf-8-sig")
        anchor = "if (class'APX_CombatPlanner'.static.ChooseAction("
        self.assertEqual(source.count(anchor), 1)
        start = source.index(anchor)
        end = source.index("\n        {", start)
        condition = source[start:end]
        self.assertIn("(bRangedFocusGoal ? RangedTargetID : 0)", condition)
        # Three closures: ternary subexpression, ChooseAction(...), if (...).
        self.assertTrue(condition.rstrip().endswith(")))"))
        depth = 0
        for char in condition[condition.index("("):]:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                self.assertGreaterEqual(depth, 0, "premature closing parenthesis")
        self.assertEqual(depth, 0, "unclosed if-condition: WOTC MakeCommandlet fails")


if __name__ == "__main__":
    unittest.main()
