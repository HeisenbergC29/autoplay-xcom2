"""Lexical guard for logical operators in ungrouped UE3 ternary conditions.

The native WOTC compiler rejected an ``&&``/integer-ternary combination that
portable numeric tests did not parse. Require explicit grouping of the full
condition. This narrow preflight is not an UnrealScript parser or compiler.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "AutoplayXCom2" / "Src"
TOKENS = re.compile(r"&&|\|\||==|!=|>=|<=|\+=|-=|\*=|/=|[()\[\]{};,?:=]")


def mask_noncode(source):
    """Replace comments and literals with spaces, retaining source positions."""
    result = list(source)
    state = "code"
    i = 0
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if state == "code":
            if ch == "/" and nxt in ("/", "*"):
                state = "line" if nxt == "/" else "block"
                result[i:i + 2] = "  "
                i += 2
                continue
            if ch in ('"', "'"):
                state = ch
                result[i] = " "
        elif state == "line":
            if ch == "\n":
                state = "code"
            else:
                result[i] = " "
        elif state == "block":
            if ch == "*" and nxt == "/":
                result[i:i + 2] = "  "
                i += 2
                state = "code"
                continue
            if ch != "\n":
                result[i] = " "
        else:
            if ch == "\\" and nxt:
                result[i] = " "
                if nxt != "\n":
                    result[i + 1] = " "
                i += 2
                continue
            if ch == state:
                state = "code"
            if ch != "\n":
                result[i] = " "
        i += 1
    return "".join(result)


def check_ternary_conditions(source):
    """Return (line, diagnostic) for logical operators at the '?' depth.

    Parentheses isolate complete conditions, while commas/assignments and
    statement/branch boundaries prevent unrelated expressions leaking through.
    Delimiter balance is checked separately by the existing source preflight.
    """
    code = mask_noncode(source)
    logical_at_depth = [None]
    failures = []
    line = 1
    previous_end = 0
    for match in TOKENS.finditer(code):
        line += code.count("\n", previous_end, match.start())
        previous_end = match.end()
        token = match.group()
        if token in ("(", "[", "{"):
            logical_at_depth.append(None)
        elif token in (")", "]", "}"):
            if len(logical_at_depth) > 1:
                logical_at_depth.pop()
            if token == "}":
                logical_at_depth[-1] = None
        elif token in ("&&", "||"):
            logical_at_depth[-1] = logical_at_depth[-1] or (token, line)
        elif token == "?":
            if logical_at_depth[-1] is not None:
                operator, operator_line = logical_at_depth[-1]
                failures.append((line, "parenthesize the full ternary condition "
                                 f"containing {operator} from line {operator_line}"))
            logical_at_depth[-1] = None
        elif token in (";", ",", ":", "=", "+=", "-=", "*=", "/="):
            logical_at_depth[-1] = None
    return failures


class UnrealScriptTernaryPreflight(unittest.TestCase):
    def test_all_mod_sources_group_logical_ternary_conditions(self):
        files = sorted(SOURCES.rglob("*.uc")) + sorted(SOURCES.rglob("*.uci"))
        self.assertGreaterEqual(len(files), 30)
        failures = []
        for path in files:
            for line, diagnostic in check_ternary_conditions(path.read_text(encoding="utf-8-sig")):
                failures.append(f"{path.relative_to(ROOT)}:{line}: {diagnostic}")
        self.assertEqual([], failures, "\n".join(failures))

    def test_all_three_original_movement_failures_are_detected(self):
        cases = (
            "iFirstBlueClear = bSingleBlue && ContactStatus == 0\n"
            "    && bTempoCurrentPathSafe ? 1 : 0;",
            "iAcceptedRoutine = bInspectContact && !bUsedLocalFallback ? 1 : 0;",
            "iFirstBlueClear = iAcceptedRoutine > 0 && bSingleBlue && bBestBlueFullyClear ? 1 : 0;",
        )
        for source in cases:
            with self.subTest(source=source):
                self.assertEqual(1, len(check_ternary_conditions(source)))

    def test_full_condition_grouping_and_simple_conditions_are_valid(self):
        source = (
            "a = (bSingleBlue && ContactStatus == 0 && bTempoCurrentPathSafe) ? 1 : 0;\n"
            "b = (bInspectContact && !bUsedLocalFallback) ? 1 : 0;\n"
            "c = (iAcceptedRoutine > 0 && bSingleBlue && bBestBlueFullyClear) ? 1 : 0;\n"
            "d = Ready ? 1 : 0; e = Count > 0 ? Count : 0;\n"
            "f = (Ready || (Other && Enabled)) ? 1 : 0;"
        )
        self.assertEqual([], check_ternary_conditions(source))

    def test_or_and_partial_grouping_are_not_mistaken_for_full_grouping(self):
        for source in ("x = a || b ? 1 : 0;", "x = a && (b || c) ? 1 : 0;"):
            with self.subTest(source=source):
                self.assertEqual(1, len(check_ternary_conditions(source)))

    def test_expression_boundaries_and_nested_ternaries_do_not_leak(self):
        source = (
            "x = a && b; y = c ? 1 : 0;\n"
            "Call(a && b, c ? 1 : 0);\n"
            "x = a && (b ? c : d);\n"
            "x = a ? b && c : d || e;\n"
            "if (a && b) { x = c ? 1 : 0; }"
        )
        self.assertEqual([], check_ternary_conditions(source))
        self.assertEqual(1, len(check_ternary_conditions("x = a ? b && c ? 1 : 0 : 0;")))

    def test_comments_literals_and_escaped_quotes_are_ignored(self):
        source = (
            "// bad = a && b ? 1 : 0;\n"
            "/* bad = a || b\n ? 1 : 0; */\n"
            'Label = "a && b ? 1 : 0; \\\"escaped\\\"";\n'
            "Named = 'a || b ? 1 : 0';\n"
            "Value = Ready ? 1 : 0;"
        )
        self.assertEqual([], check_ternary_conditions(source))
        self.assertEqual(5, mask_noncode(source).count("\n"))


if __name__ == "__main__":
    unittest.main()
