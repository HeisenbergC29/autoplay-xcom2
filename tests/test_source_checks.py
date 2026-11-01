"""Regression checks for restrictions reported by the real WOTC compiler.

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


class BareStopRestrictionTests(unittest.TestCase):
    def test_rejects_calls_reported_by_compiler(self):
        original = (
            'Stop(Reason);\n'
            'if (bEnabled) Stop("User toggle", true);\n'
            'STOP("Escape", true);\n'
        )
        self.assertEqual(CHECKS.forbidden_bare_stop_calls(original), [1, 2, 3])

    def test_accepts_state_statement_qualified_sdk_call_and_renamed_method(self):
        valid = (
            'state Paused { Begin: Stop; }\n'
            'native function Stop();\n'
            'function bool Stop(string Reason) {}\n'
            'Audio.Stop();\n'
            'Audio. /* qualified SDK call */ Stop();\n'
            'function StopAutoplay(string Reason) {}\n'
            'StopAutoplay("Escape", true);\n'
            'Controller.StopAutoplay("HUD removed");\n'
        )
        self.assertEqual(CHECKS.forbidden_bare_stop_calls(valid), [])

    def test_ignores_comments_and_literals(self):
        source = (
            '// Stop(Reason);\n'
            '/* Stop("Escape"); */\n'
            'var string Text = "Stop(Reason)";\n'
            "var name Key = 'Stop()';\n"
        )
        self.assertEqual(CHECKS.forbidden_bare_stop_calls(source), [])

    def test_controller_and_ui_share_renamed_stop_contract(self):
        classes = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
        controller = (classes / 'APX_Controller.uc').read_text()
        ui = (classes / 'APX_UITacticalControl.uc').read_text()
        self.assertIn('function StopAutoplay(', controller)
        self.assertIn('Controller.StopAutoplay(', ui)
        for file in classes.glob('*.uc'):
            with self.subTest(file=file.name):
                self.assertEqual(CHECKS.forbidden_bare_stop_calls(file.read_text()), [])


class CoverQueryOutArgumentTests(unittest.TestCase):
    def test_rejects_nested_vector_return_reported_by_compiler(self):
        source = (
            'Cover = `XWORLD.GetCoverTypeForTarget(\n'
            '    `XWORLD.GetPositionFromTileCoordinates(Ally.TileLocation), EnemyLocation, Angle);'
        )
        self.assertEqual(CHECKS.invalid_cover_query_arguments(source), [(1, 1)])

    def test_rejects_second_vector_expression_too(self):
        self.assertEqual(CHECKS.invalid_cover_query_arguments(
            'World.GetCoverTypeForTarget(Source + Offset, TargetLocation(), Angle);'),
            [(1, 1), (1, 2)])

    def test_accepts_locals_members_and_array_elements(self):
        self.assertEqual(CHECKS.invalid_cover_query_arguments(
            'World.GetCoverTypeForTarget(SourceLocation, EnemyLocation, Angle);\n'
            'World.GetCoverTypeForTarget(Info.Location, Locations[Index + 1], Angle);'), [])

    def test_ignores_comments_strings_and_native_declaration(self):
        self.assertEqual(CHECKS.invalid_cover_query_arguments(
            '// World.GetCoverTypeForTarget(Position(), EnemyLocation, Angle);\n'
            'var string Text = "GetCoverTypeForTarget(Position(), Target, Angle)";\n'
            'static native final function ECoverType GetCoverTypeForTarget('
            'const out Vector ShooterLocation, const out Vector TargetLocation, out float Angle);'), [])

    def test_current_mod_has_no_invalid_cover_query_inputs(self):
        for file in (ROOT / 'AutoplayXCom2/Src').rglob('*.uc'):
            with self.subTest(file=file.name):
                self.assertEqual(CHECKS.invalid_cover_query_arguments(file.read_text()), [])


if __name__ == "__main__":
    unittest.main()
