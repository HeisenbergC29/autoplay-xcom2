"""Fail-fast lexical preflight for UnrealScript delimiters.

The Windows WOTC compiler remains authoritative. This light source check
catches a common, otherwise CI-invisible syntax mistake (an unclosed if)
without treating punctuation in comments or quoted literals as code.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "AutoplayXCom2" / "Src"
OPEN = "([{"
CLOSE = ")]}"
MATCH = dict(zip(CLOSE, OPEN))


def check_delimiters(text):
    """Return actionable (line, message) for unmatched code delimiters."""
    stack = []
    failures = []
    state = "code"
    line = 1
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if ch == "\n":
            line += 1
        if state == "line_comment":
            if ch == "\n":
                state = "code"
            i += 1
            continue
        if state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "code"
                i += 2
            else:
                i += 1
            continue
        if state in ("string", "name"):
            delim = '"' if state == "string" else "'"
            # UnrealScript uses backslash-escaped characters in strings.
            if ch == "\\" and nxt:
                i += 2
            elif ch == delim:
                state = "code"
                i += 1
            else:
                i += 1
            continue
        if ch == "/" and nxt == "/":
            state = "line_comment"
            i += 2
            continue
        if ch == "/" and nxt == "*":
            state = "block_comment"
            i += 2
            continue
        if ch == '"':
            state = "string"
            i += 1
            continue
        if ch == "'":
            state = "name"
            i += 1
            continue
        if ch in OPEN:
            stack.append((ch, line))
        elif ch in CLOSE:
            if not stack or stack[-1][0] != MATCH[ch]:
                failures.append((line, f"unexpected {ch}, expected closure for {stack[-1] if stack else 'nothing'}"))
            else:
                stack.pop()
        i += 1
    for delim, opening_line in stack:
        failures.append((opening_line, f"unclosed {delim}"))
    if state in ("block_comment", "string", "name"):
        failures.append((line, f"unterminated {state}"))
    return failures


class UnrealScriptDelimiterPreflight(unittest.TestCase):
    def test_all_project_sources_have_balanced_code_delimiters(self):
        source_files = sorted(SOURCES.rglob("*.uc")) + sorted(SOURCES.rglob("*.uci"))
        self.assertGreaterEqual(len(source_files), 20)
        problems = []
        for path in source_files:
            for line, problem in check_delimiters(path.read_text(encoding="utf-8-sig")):
                problems.append(f"{path.relative_to(ROOT)}:{line}: {problem}")
        self.assertEqual([], problems, "\n".join(problems))

    def test_missing_if_closer_is_reported_not_silently_skipped(self):
        sample = "if (Foo((1 + 2))\n{ Action(); }"
        self.assertIn((1, "unclosed ("), check_delimiters(sample))

    def test_quotes_and_comments_do_not_create_fake_errors(self):
        sample = (
            "// ) } ]\n"
            "/* ( { [ */\n"
            'local string Label; Label = "text with } ] ) and \\\"quote\\\"";\n'
            "if (Find('Name') > 0) { Log(Label); }\n"
        )
        self.assertEqual([], check_delimiters(sample))


if __name__ == "__main__":
    unittest.main()
