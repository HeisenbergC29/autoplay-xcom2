"""Regression checks for a restriction reported by the real WOTC compiler.

These test the preflight scanner, not UnrealScript compilation or gameplay.
"""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sdk_checks", ROOT / "tools/check-sdk-references.py")
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


class OutBooleanRestrictionTests(unittest.TestCase):
    def test_rejects_original_mission_parameter_shapes(self):
        original = (
            "static function ConsiderGoal(out TTile Tile,\n"
            "    out bool bCombatGoal, out bool bFoundGoal) {}\n"
            "static function bool FindGoal(out bool bCombatGoal) {}\n"
        )
        self.assertEqual(CHECKS.forbidden_out_booleans(original), [2, 2, 3])

    def test_accepts_boolean_fields_inside_result_struct(self):
        corrected = (
            "struct MissionGoal { var bool bFound; var bool bCombat; };\n"
            "static function bool FindGoal(out MissionGoal Goal, bool bInput) {}\n"
        )
        self.assertEqual(CHECKS.forbidden_out_booleans(corrected), [])

    def test_ignores_comments_and_literals_and_preserves_line_numbers(self):
        source = (
            "/* out bool\n out bool */\n"
            '// out bool\nvar string Label = "out bool";\n'
            "var name LabelName = 'out bool';\n"
            "function Test(OUT\n BOOL bResult);\n"
        )
        self.assertEqual(CHECKS.forbidden_out_booleans(source), [6])

    def test_current_mod_has_no_prohibited_out_booleans(self):
        for file in (ROOT / "AutoplayXCom2/Src").rglob("*.uc"):
            with self.subTest(file=file.name):
                self.assertEqual(CHECKS.forbidden_out_booleans(file.read_text()), [])


if __name__ == "__main__":
    unittest.main()
