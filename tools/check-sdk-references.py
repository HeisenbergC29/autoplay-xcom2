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


def invalid_cover_query_arguments(source: str) -> list[tuple[int, int]]:
    """Cover queries require vector variables for both const out inputs.

    WOTC rejects a vector-returning call in either position even though its
    return type matches. Check this known native API, not arbitrary functions.
    """
    tokens = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\x27[^\x27\n]*\x27', re.S)
    masked = tokens.sub(lambda match: re.sub(r'[^\n]', ' ', match[0]), source)
    failures = []
    variable = re.compile(r'\w+(?:\s*\.\s*\w+|\s*\[[^\[\]]+\])*\s*$', re.S)
    for call in re.finditer(r'\bGetCoverTypeForTarget\s*\(', masked, re.I):
        if re.search(r'\bfunction\s+(?:\w+\s+)?$', masked[:call.start()], re.I):
            continue
        start = call.end()
        depth = 0
        argument = 1
        for index in range(start, len(masked)):
            char = masked[index]
            if char in '([':
                depth += 1
            elif char in ')]':
                if depth == 0:
                    break
                depth -= 1
            elif char == ',' and depth == 0:
                if not variable.fullmatch(masked[start:index].strip()):
                    failures.append((masked.count('\n', 0, call.start()) + 1, argument))
                argument += 1
                start = index + 1
                if argument > 2:
                    break
    return failures


def find_sdk_root(path: Path) -> Path:
    for candidate in (path, path / "Development" / "SrcOrig", path / "Development" / "Src"):
        if (candidate / "XComGame" / "Classes").is_dir():
            return candidate
    raise ValueError("Expected SrcOrig/Src, or an SDK directory containing Development/SrcOrig.")


def declared_config_properties(source: str) -> set[str]:
    properties = set()
    for declaration in re.findall(r'\bvar\b([^;]+);', without_comments(source), re.I):
        if re.search(r'\bconfig\b', declaration, re.I):
            name = re.search(r'(\w+)\s*$', declaration)
            if name:
                properties.add(name[1].casefold())
    return properties


def forbidden_config_defaults(source: str, inherited_properties=()) -> list[tuple[int, str]]:
    """WOTC rejects config assignments in defaultproperties, including arrays."""
    properties = declared_config_properties(source) | {name.casefold() for name in inherited_properties}
    text = without_comments(source)
    block = re.search(r'^\s*defaultproperties\s*\{(.*)\}\s*$', text, re.M | re.S | re.I)
    if not block:
        return []
    return [(text.count('\n', 0, block.start(1) + match.start()) + 1, match[1])
            for match in re.finditer(r'^\s*(\w+)(?:\(\d+\))?\s*=', block[1], re.M)
            if match[1].casefold() in properties]


def read_config_entries(path: Path) -> list[tuple[str, str, str]]:
    """Read repeated Unreal INI array entries without collapsing their values."""
    entries = []
    section = ''
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        if not line or line.startswith((';', '#')):
            continue
        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1]
        elif '=' in line:
            name, value = line.split('=', 1)
            entries.append((section, name.strip().lstrip('+.!-'), value.strip().strip('"')))
    return entries


def audit(sdk_root: Path, repo_root: Path) -> list[str]:
    sdk_files = list(sdk_root.rglob("*.uc"))
    mod_files = sorted((repo_root / "AutoplayXCom2" / "Src").rglob("*.uc"))
    if not mod_files:
        raise ValueError("No mod source files found in repository.")
    classes = {file.stem.casefold() for file in sdk_files + mod_files}
    class_paths = {file.stem.casefold(): file for file in sdk_files + mod_files}
    source = {file: without_comments(file.read_text(encoding="utf-8-sig", errors="replace"))
              for file in mod_files}
    failures = []
    for file in mod_files:
        raw_source = file.read_text(encoding="utf-8-sig")
        for line in forbidden_out_booleans(raw_source):
            failures.append(f"{file.name}:{line}: UnrealScript forbids direct out bool parameters; use a result struct.")
        for line in forbidden_bare_stop_calls(raw_source):
            failures.append(f"{file.name}:{line}: bare Stop(...) conflicts with the state statement; use StopAutoplay.")
        for line, argument in invalid_cover_query_arguments(raw_source):
            failures.append(f"{file.name}:{line}: GetCoverTypeForTarget argument {argument} must be a vector variable for const out; assign expressions to locals first.")
        inherited = set()
        parent = re.search(r'\bextends\s+(\w+)', without_comments(raw_source), re.I)
        visited = set()
        while parent and parent[1].casefold() in class_paths and parent[1].casefold() not in visited:
            parent_name = parent[1].casefold()
            visited.add(parent_name)
            parent_source = class_paths[parent_name].read_text(encoding='utf-8-sig', errors='replace')
            inherited.update(declared_config_properties(parent_source))
            parent = re.search(r'\bextends\s+(\w+)', without_comments(parent_source), re.I)
        for line, name in forbidden_config_defaults(raw_source, inherited):
            failures.append(f"{file.name}:{line}: config property {name} must be initialized in INI, not defaultproperties.")
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
    config_path = repo_root / 'AutoplayXCom2/Config/XComAutoplayXCom2.ini'
    for section, key, name in read_config_entries(config_path):
        if section.casefold() == 'autoplayxcom2.apx_combatplanner' and re.fullmatch(
                r'(?:Attack|Heal|Stabilize|Reload|Overwatch|Hunker)Abilities', key, re.I):
            ability_count += 1
            if name.casefold() not in literals:
                failures.append(f"{config_path.name}: configured ability name absent from SDK factories: {name}")
    if ability_count == 0:
        failures.append('No configured combat abilities found in source or INI.')
    for name in ("X2Ability_ReaperAbilitySet", "X2Ability_TemplarAbilitySet", "X2Ability_SkirmisherAbilitySet"):
        if name.casefold() not in classes:
            failures.append(f"WOTC source marker missing: {name}")
    if not failures:
        print(f"PASS: {len(mod_files)} mod classes, SDK class references, {ability_count} configured ability names, WOTC markers and known parameter/Stop/config restrictions.")
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
