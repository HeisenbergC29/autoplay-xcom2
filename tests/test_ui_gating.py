"""Source-contract regressions for the real stock-HUD autoplay pause bug.

These checks do not execute UnrealScript. Set APX_SDK_SOURCE_ROOT to a local
SrcOrig directory to also check the stock UI construction that triggered it.
The SDK itself is not redistributed with these tests.
"""

import importlib.util
import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SPEC = importlib.util.spec_from_file_location('sdk_ui_checks', ROOT / 'tools/check-sdk-references.py')
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


def function_body(source, name):
    """Extract one real function body while ignoring braces in strings/comments."""
    clean = CHECKS.without_comments(source)
    match = re.search(r'\b(?:function|event)\s+(?:\w+\s+)?' + re.escape(name)
                      + r'\s*\([^)]*\)\s*\{', clean, re.I)
    if match is None:
        raise AssertionError(f'Missing function/event {name}')
    return braced_body(clean, match.end() - 1)


def braced_body(source, opening_index):
    """Return the body of a block whose opening brace is already located."""
    masked = re.sub(r'"(?:\\.|[^"\\])*"|\x27[^\x27\n]*\x27',
                    lambda token: ' ' * len(token[0]), source)
    depth = 1
    for index in range(opening_index + 1, len(masked)):
        if masked[index] == '{':
            depth += 1
        elif masked[index] == '}':
            depth -= 1
            if depth == 0:
                return source[opening_index + 1:index]
    raise AssertionError('Unterminated braced block')


class TacticalUIGatingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controller = (CLASSES / 'APX_Controller.uc').read_text(encoding='utf-8-sig')

    def test_does_not_require_hud_to_be_the_top_screen(self):
        # Normal WOTC creates mission and turn overlays above UITacticalHUD.
        self.assertIsNone(re.search(r'UITacticalHUD\s*\([^;\n]*GetCurrentScreen\s*\(',
                                    CHECKS.without_comments(self.controller)),
                          'Stock passive overlays can be above UITacticalHUD')
        gate = function_body(self.controller, 'GetUIBlockReason')
        self.assertIn('.GetTacticalHUD(', gate)
        self.assertIn('.Screens', gate)

    def test_stock_overlays_have_explicit_allowlist(self):
        passive = function_body(self.controller, 'IsPassiveTacticalOverlay')
        screen_casts = set(re.findall(r'\b(UI\w+)\s*\(\s*Screen\s*\)', passive))
        self.assertEqual(screen_casts, {
            'UITurnOverlay', 'UISpecialMissionHUD', 'UIChallengeModeHUD',
            'UIUnitFlagManager', 'UIEnemyArrowContainer', 'UITooltipMgr',
            'UIEventNotices',
        })
        # An arbitrary input-transparent screen is not sufficient evidence that
        # it is safe to issue gameplay orders beneath it.
        self.assertNotIn('eInputState_None', passive)

    def test_real_menu_and_manual_input_guards_remain(self):
        gate = function_body(self.controller, 'GetUIBlockReason')
        for required in ('PC.IsBusy(', '.IsInputBlocked', '.GetTargetingMethod(',
                         '.ShowingDialog(', '.ConsumesInput('):
            with self.subTest(guard=required):
                self.assertIn(required, gate)
        self.assertRegex(gate, r"return\s+'Menu'\s*;")
        self.assertIn('IsPassiveTacticalOverlay(', gate)

    def test_stack_traversal_stops_at_the_actual_hud(self):
        gate = function_body(self.controller, 'GetUIBlockReason')
        hud_check = re.search(r'if\s*\(\s*Screen\s*==\s*HUD\s*\)\s*\{', gate)
        self.assertIsNotNone(hud_check, 'Use the HUD instance from the presentation layer')
        hud_branch = braced_body(gate, hud_check.end() - 1)
        self.assertRegex(hud_branch, r"return\s+''\s*;")
        self.assertIn('HUD.GetTargetingMethod(', hud_branch)
        self.assertLess(hud_check.start(), gate.index('IsPassiveTacticalOverlay('))
        # A stale presentation-layer HUD that is absent from the stack must not
        # authorize orders after the entire loop has been exhausted.
        self.assertRegex(gate.rstrip(), r"return\s+'HUD'\s*;\s*$")

    def test_ui_block_reason_stops_the_tick_before_any_order(self):
        tick = function_body(self.controller, 'Tick')
        blocked = re.search(r"if\s*\(\s*UIBlockReason\s*!=\s*''\s*\)\s*\{", tick)
        self.assertIsNotNone(blocked)
        blocked_branch = braced_body(tick, blocked.end() - 1)
        self.assertRegex(blocked_branch.rstrip(), r'return\s*;\s*$')
        self.assertNotIn('MakeDecision(', blocked_branch)
        self.assertLess(blocked.end(), tick.index('MakeDecision('))

    def test_pause_and_owned_hack_handling_precede_normal_ui_gate(self):
        tick = function_body(self.controller, 'Tick')
        gate_position = tick.index('GetUIBlockReason(')
        self.assertLess(tick.index('WorldInfo.Pauser'), gate_position)
        self.assertLess(tick.index('HandleOwnedHack('), gate_position)

    def test_all_controller_statuses_have_both_translations(self):
        statuses = set(re.findall(r'\bvar\s+localized\s+string\s+(Status\w+)\s*;',
                                  CHECKS.without_comments(self.controller)))
        self.assertTrue(statuses)
        for language in ('int', 'pol'):
            entries = CHECKS.read_config_entries(
                ROOT / f'AutoplayXCom2/Localization/AutoplayXCom2.{language}')
            localized = {key: value for section, key, value in entries
                         if section == 'APX_Controller'}
            with self.subTest(language=language):
                self.assertEqual(statuses, set(localized))
                self.assertTrue(all(localized.values()))


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'),
                     'Set APX_SDK_SOURCE_ROOT to check the original stock SDK UI layout')
class StockSDKHUDLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk_classes = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT'])) / 'XComGame/Classes'
        cls.presentation = (cls.sdk_classes / 'XComPresentationLayer.uc').read_text(
            encoding='utf-8-sig', errors='replace')

    def test_stock_builds_passive_screens_above_the_tactical_hud(self):
        setup = function_body(self.presentation, 'InitUIScreensComplete')
        self.assertLess(setup.index('UIAbilityHUD();'), setup.index('UITurnOverlay();'))
        self.assertLess(setup.index('UITurnOverlay();'),
                        setup.index('InitializeSpecialMissionUI();'))
        for function, screen in (('UIAbilityHUD', 'm_kTacticalHUD'),
                                 ('UITurnOverlay', 'm_kTurnOverlay')):
            self.assertRegex(function_body(self.presentation, function),
                             r'ScreenStack\.Push\(\s*' + screen + r'\s*\)')
        self.assertIn("class'UISpecialMissionHUD'",
                      function_body(self.presentation, 'InitializeSpecialMissionUI'))

    def test_stock_clear_to_hud_keeps_turn_overlay_at_top(self):
        self.assertIn("PopUntilClass(class'UITurnOverlay'",
                      function_body(self.presentation, 'ClearUIToHUD'))

    def test_ladder_overlay_inherits_the_allowed_challenge_overlay(self):
        ladder = (self.sdk_classes / 'UILadderModeHUD.uc').read_text(
            encoding='utf-8-sig', errors='replace')
        self.assertRegex(CHECKS.without_comments(ladder),
                         r'class\s+UILadderModeHUD\s+extends\s+UIChallengeModeHUD\s*;')


if __name__ == '__main__':
    unittest.main()
