#!/usr/bin/env python3
"""Audit installed Legacy ladder scoring *configuration*, without copying INIs.

This is a DATA audit only. The native award routines (kill origin, disabled
status, restart and bonuses) are not present in the public UnrealScript bodies;
a matching rate table is NOT proof of identical or complete earned points.
No raw SDK/INI content or absolute host paths are written to the report.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

SCORING_KEYS = {
    "DefaultEnemyScoring": ("CharacterTemplateName",),
    "DefaultEnemyScoringTable": ("CharacterTemplateName",),
    "DefaultObjectiveScoring": ("MissionType", "TextPoolIndex", "GroupID", "LineIndex"),
    "DefaultObjectiveScoringTable": ("MissionType", "TextPoolIndex", "GroupID", "LineIndex"),
    "DefaultMissionScoring": ("MissionType",),
    "DefaultMissionScoringTable": ("MissionType",),
    "DefaultSoldierScoring": (),
    "RestartScorePenalty": (),
}
PROPERTY_NAMES = {key.casefold(): key for key in SCORING_KEYS}
CONFIG_PROPERTY = re.compile(r"^\s*([^\w\s]*)\s*(\w+)\b(.*)$")
SCORING_PROPERTY = re.compile(r"Default(?:Enemy|Objective|Mission|Soldier)Scoring", re.I)
ASSIGNMENT = re.compile(r"^\s*=\s*(.*?)\s*$")
FIELD = re.compile(r'\s*(\w+)\s*=\s*(?:"([^"\\]*)"|(-?\d+))\s*')
ENEMY_FIELDS = ("StartingPoints", "MinPoints", "DecreasePerTurn", "TurnOffset",
                "SpawnedPoints", "ReinforcementPoints", "DisabledPoints", "MinDisabledPoints")
OBJECTIVE_FIELDS = ("StartingPoints", "MinPoints", "DecreasePerTurn", "TurnOffset")
SOLDIER_FIELDS = ("UninjuredBonus", "WoundedBonus", "RescuedCivilianBonus")
NAME_FIELDS = {"CharacterTemplateName", "MissionType"}
FIELD_NAMES = {key.casefold(): key for key in
               (*NAME_FIELDS, "TextPoolIndex", "GroupID", "LineIndex",
                *ENEMY_FIELDS, *OBJECTIVE_FIELDS, *SOLDIER_FIELDS)}
REQUIRED_DEFAULTS = ("DefaultEnemyScoring", "DefaultObjectiveScoring",
                     "DefaultMissionScoring", "DefaultSoldierScoring")


def scoring_fields(kind):
    return (ENEMY_FIELDS if kind.startswith("DefaultEnemy") else
            OBJECTIVE_FIELDS if kind.startswith(("DefaultObjective", "DefaultMission")) else
            SOLDIER_FIELDS)


def scoring_identity(kind, entry):
    """These identity strings are stock SDK name fields, not FString values."""
    result = []
    for field in SCORING_KEYS[kind]:
        value = entry[field]
        expected = str if field in NAME_FIELDS else int
        if type(value) is not expected:
            raise ValueError(f"invalid scoring identity type for {field}")
        result.append(value.casefold() if field in NAME_FIELDS else value)
    return tuple(result)


def normalized_entry(entry):
    return {key: value.casefold() if key in NAME_FIELDS else value
            for key, value in entry.items()}


def parse_tuple(rhs, kind, location):
    """Parse the whole supported tuple; unmatched text is never discarded."""
    if not rhs.startswith("(") or not rhs.endswith(")"):
        raise ValueError(f"{location}: malformed scoring tuple")
    body, position, values = rhs[1:-1], 0, {}
    allowed = set(SCORING_KEYS[kind]) | set(scoring_fields(kind))
    while position < len(body):
        match = FIELD.match(body, position)
        if not match:
            raise ValueError(f"{location}: unsupported scoring syntax")
        raw_key, quoted, numeric = match.groups()
        key = FIELD_NAMES.get(raw_key.casefold())
        if key not in allowed:
            raise ValueError(f"{location}: unsupported scoring field {raw_key}")
        if key in values:
            raise ValueError(f"{location}: repeated field {key}")
        values[key] = quoted if quoted is not None else int(numeric)
        position = match.end()
        if position == len(body):
            break
        if body[position] != "," or not body[position + 1:].strip():
            raise ValueError(f"{location}: malformed scoring separator")
        position += 1
    if any(key not in values for key in SCORING_KEYS[kind]):
        raise ValueError(f"{location}: missing scoring identity")
    try:
        scoring_identity(kind, values)
    except ValueError as exc:
        raise ValueError(f"{location}: {exc}") from exc
    if any(key not in values or type(values[key]) is not int
           for key in scoring_fields(kind)):
        raise ValueError(f"{location}: incomplete scoring values")
    return values


def read_config(path):
    """Return (source digest, records) only from the LadderProgress section."""
    raw = Path(path).read_bytes()
    source = {"filename": Path(path).name, "sha256": hashlib.sha256(raw).hexdigest()}
    text = raw.decode("utf-8-sig")
    in_ladder = False
    records = []
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_ladder = stripped.casefold() == "[xcomgame.xcomgamestate_ladderprogress]"
            continue
        if not in_ladder or not stripped or stripped.startswith((";", "//")):
            continue
        match = CONFIG_PROPERTY.match(line)
        if not match:
            continue
        operation, raw_kind, assignment = match.groups()
        kind = PROPERTY_NAMES.get(raw_kind.casefold())
        location = f"{source['filename']}:{number}"
        if kind is None:
            if SCORING_PROPERTY.match(raw_kind):
                raise ValueError(f"{location}: unsupported scoring property {raw_kind}")
            continue
        # Array clearing/removal/force-append semantics are outside this narrow
        # auditor. Refuse them instead of reporting a stale, apparently valid table.
        if operation == "-":
            raise ValueError(f"{location}: removal cannot be safely resolved")
        if operation not in ("", "+") or (operation and not kind.endswith("Table")):
            raise ValueError(f"{location}: unsupported scoring operator {operation}")
        value_match = ASSIGNMENT.fullmatch(assignment)
        if not value_match:
            raise ValueError(f"{location}: malformed scoring assignment")
        rhs = value_match[1]
        if kind == "RestartScorePenalty":
            if not re.fullmatch(r"-?\d+", rhs):
                raise ValueError(f"{location}: invalid penalty")
            value = int(rhs)
            records.append((operation, kind, {"Value": value}, number))
            continue
        values = parse_tuple(rhs, kind, location)
        records.append((operation, kind, values, number))
    return source, records


def load_rules(paths):
    """Reject ambiguous duplicates rather than assuming native INI precedence."""
    categories = {"enemy": {}, "objective": {}, "mission": {}}
    defaults = {}
    sources = []
    for path in paths:
        origin, records = read_config(path)
        sources.append(origin)
        for operation, kind, entry, line in records:
            category = ("enemy" if kind.startswith("DefaultEnemy") else
                        "objective" if kind.startswith("DefaultObjective") else
                        "mission" if kind.startswith("DefaultMission") else None)
            if category is None or kind == "RestartScorePenalty" or not kind.endswith("Table"):
                if kind in defaults and normalized_entry(defaults[kind]) != normalized_entry(entry):
                    raise ValueError(f"{origin['filename']}:{line}: conflicting {kind} default")
                defaults[kind] = entry
                continue
            identity = scoring_identity(kind, entry)
            if (identity in categories[category]
                    and normalized_entry(categories[category][identity]) != normalized_entry(entry)):
                raise ValueError(f"{origin['filename']}:{line}: ambiguous {kind} override {identity}")
            categories[category][identity] = entry
    missing = [key for key in REQUIRED_DEFAULTS if key not in defaults]
    if missing:
        raise ValueError("missing required scoring defaults: " + ", ".join(missing))
    return {"sources": sources, "defaults": defaults, "categories": categories}


def decayed(record, turn):
    """Explicit v2 convention for diagnostic comparison, NOT proven native C++."""
    if type(turn) is not int or turn < 0:
        raise ValueError("native turn unknown")
    if any(type(record.get(key)) is not int for key in OBJECTIVE_FIELDS):
        raise ValueError("incomplete scoring values")
    return max(record["MinPoints"],
               record["StartingPoints"] - max(0, turn - record["TurnOffset"])
               * record["DecreasePerTurn"])


def previous_v2_decayed(record, turn):
    """The historic JSON uses snake_case, unlike native INI's PascalCase."""
    if type(turn) is not int or turn < 0:
        raise ValueError("native turn unknown")
    if any(type(record.get(key)) is not int for key in
           ("min_points", "starting_points", "turn_offset", "decrease_per_turn")):
        raise ValueError("incomplete comparison scoring values")
    return max(record["min_points"],
               record["starting_points"] - max(0, turn - record["turn_offset"])
               * record["decrease_per_turn"])


def rate_for_enemy(rules, template):
    key = scoring_identity("DefaultEnemyScoringTable", {"CharacterTemplateName": template})
    return rules["categories"]["enemy"].get(key, rules["defaults"]["DefaultEnemyScoring"])


def rate_for_objective(rules, mission, text_pool, group, line):
    key = scoring_identity("DefaultObjectiveScoringTable", {
        "MissionType": mission, "TextPoolIndex": text_pool, "GroupID": group, "LineIndex": line})
    return rules["categories"]["objective"].get(key, rules["defaults"]["DefaultObjectiveScoring"])


def audit(rules, previous=None):
    """Only derived counts, representative witnesses and hashes: no raw INIs."""
    counts = {key: len(value) for key, value in rules["categories"].items()}
    report = {"kind": "legacy_rate_configuration_audit",
              "is_official_game_score": False,
              "native_award_parity_proven": False,
              "event_coverage_proven": False,
              "sources": rules["sources"],
              "counts": counts,
              "profile_v2_unmodified": True,
              "gaps": [
                  "native AddKillMail/AddObjectiveScore bodies not available in SDK UC",
                  "spawn/reinforcement/disabled classification not established",
                  "restart and bonuses not reconstructed",
                  "history observation may miss objective and civilian events after reload",
                  "legacy rate table alone does not prove total score parity"
              ]}
    witnesses = {}
    for name in ("AdvTrooperM1", "AdvPriestM3", "Muton"):
        witnesses[name] = decayed(rate_for_enemy(rules, name), 10)
    witnesses["ChallengeTerrorBar:0:1:0"] = decayed(
        rate_for_objective(rules, "ChallengeTerrorBar", 0, 1, 0), 10)
    report["sample_rate_turn10"] = witnesses
    if previous is not None:
        default = previous["enemy_default"]
        old = previous.get("enemies", {})
        report["previous_profile"] = previous["profile_id"]
        report["comparison_differences_at_turn10"] = {}
        for name in ("AdvTrooperM1", "AdvPriestM3", "Muton"):
            before = previous_v2_decayed(old.get(name, default), 10)
            after = witnesses[name]
            report["comparison_differences_at_turn10"][name] = {
                "previous": before, "configured": after, "difference": after - before
            }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True,
                        help="Owned game Config/DefaultLadder.ini (read-only)")
    parser.add_argument("--overlay", type=Path, action="append", default=[],
                        help="Optional DLC's Config/XComLadder.ini (read-only)")
    parser.add_argument("--comparison", type=Path,
                        help="Optional tools/legacy-score-rules.json to compare v2")
    parser.add_argument("--output", type=Path, help="Private output file (no raw INI)")
    args = parser.parse_args(argv)
    rules = load_rules([args.base, *args.overlay])
    previous = json.loads(args.comparison.read_text(encoding="utf-8")) if args.comparison else None
    result = audit(rules, previous)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.exists():
            parser.error("refusing to overwrite existing audit report")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
