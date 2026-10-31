#!/usr/bin/env python3
"""Check class references and configured ability names against a local SDK.

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
        print(f"PASS: {len(mod_files)} mod classes, SDK class references, {ability_count} configured ability names and WOTC markers.")
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
