#!/usr/bin/env python3
"""Check class references, ability names and known compiler restrictions.

This is a source-reference audit, NOT an UnrealScript compiler or game test.
SDK sources stay on the local machine and are never copied to the repository.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


def without_comments(source: str) -> str:
    token = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\x27[^\x27\n]*\x27', re.S)
    return token.sub(lambda match: "" if match[0].startswith(("//", "/*")) else match[0], source)


def forbidden_out_booleans(source: str) -> list[int]:
    """Return lines containing the compiler-prohibited direct out bool type.

    Mask comments and literals without changing positions. Boolean fields in an
    out struct are legal, as are ordinary boolean inputs and function results.
    """
    tokens = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\x27[^\x27\n]*\x27', re.S)
    masked = tokens.sub(lambda match: re.sub(r'[^\n]', ' ', match[0]), source)
    return [masked.count("\n", 0, match.start()) + 1
            for match in re.finditer(r'\bout\s+(?:const\s+)?bool\b', masked, re.I)]


def forbidden_bare_stop_calls(source: str) -> list[int]:
    """Bare Stop(...) is parsed as the state Stop statement, not a call.

    A proper Stop; state statement and qualified SDK calls such as Audio.Stop()
    remain valid. Our controller uses StopAutoplay to avoid the ambiguity.
    """
    tokens = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\x27[^\x27\n]*\x27', re.S)
    masked = tokens.sub(lambda match: re.sub(r'[^\n]', ' ', match[0]), source)
    failures = []
    for match in re.finditer(r'\bstop\s*\(', masked, re.I):
        prefix = masked[:match.start()].rstrip()
        if prefix.endswith('.'):
            continue
        # SDK-native Stop declarations and explicit object.Stop() calls are
        # legal. It is the statement-position call that the compiler rejects.
        if re.search(r'\b(?:function|event|delegate)\s+(?:array\s*<\s*\w+\s*>\s+|\w+\s+)?$',
                     masked[:match.start()], re.I):
            continue
        failures.append(masked.count("\n", 0, match.start()) + 1)
    return failures


def find_sdk_root(path: Path) -> Path:
    for candidate in (path, path / "Development" / "SrcOrig", path / "Development" / "Src"):
        if (candidate / "XComGame" / "Classes").is_dir():
            return candidate
    raise ValueError("Expected SrcOrig/Src, or an SDK directory containing Development/SrcOrig.")


def audit(sdk_root: Path, repo_root: Path) -> list[str]:
    sdk_files = list(sdk_root.rglob("*.uc"))
    mod_files = sorted((repo_root / "AutoplayXCom2" / "Src").rglob("*.uc"))
    if not mod_files:
        raise ValueError("No mod source files found in repository.")
    classes = {file.stem.casefold() for file in sdk_files + mod_files}
    source = {file: without_comments(file.read_text(encoding="utf-8-sig", errors="replace"))
              for file in mod_files}
    failures = []
    for file in mod_files:
        raw_source = file.read_text(encoding="utf-8-sig")
        for line in forbidden_out_booleans(raw_source):
            failures.append(f"{file.name}:{line}: UnrealScript forbids direct out bool parameters; use a result struct.")
        for line in forbidden_bare_stop_calls(raw_source):
            failures.append(f"{file.name}:{line}: bare Stop(...) conflicts with the state statement; use StopAutoplay.")
    for file, contents in source.items():
        for name in sorted(set(re.findall(r"\bclass\s*'([A-Za-z_]\w*)'", contents, re.I))):
            if name.casefold() not in classes:
                failures.append(f"{file.name}: SDK/local class not found: {name}")

    # Ability factories use literal template names. This checks literal presence
    # in the SDK's ability source, not whether a soldier has it in a given save.
    literals = set()
    for file in sdk_files:
        if file.stem.startswith("X2Ability"):
            text = without_comments(file.read_text(encoding="utf-8-sig", errors="replace"))
            literals.update(name.casefold() for name in re.findall(r'''["']([A-Za-z_]\w*)["']''', text))
    ability_count = 0
    for file, contents in source.items():
        for name in re.findall(r'\b(?:Attack|Heal|Stabilize|Reload|Overwatch|Hunker)Abilities\(\d+\)\s*=\s*"([A-Za-z_]\w*)"', contents):
            ability_count += 1
            if name.casefold() not in literals:
                failures.append(f"{file.name}: configured ability name absent from SDK factories: {name}")
    for name in ("X2Ability_ReaperAbilitySet", "X2Ability_TemplarAbilitySet", "X2Ability_SkirmisherAbilitySet"):
        if name.casefold() not in classes:
            failures.append(f"WOTC source marker missing: {name}")
    if not failures:
        print(f"PASS: {len(mod_files)} mod classes, SDK class references, {ability_count} configured ability names, WOTC markers and known parameter/Stop restrictions.")
        print("Not checked by this tool: member signatures, compilation, native behavior or in-game mission completion.")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True, help="SDK root or extracted SrcOrig directory")
    args = parser.parse_args()
    try:
        failures = audit(find_sdk_root(args.sdk.resolve()), Path(__file__).resolve().parents[1])
    except (ValueError, OSError) as error:
        parser.error(str(error))
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
