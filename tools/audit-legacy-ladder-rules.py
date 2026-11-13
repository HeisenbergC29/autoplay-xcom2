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
CONFIG_LINE = re.compile(r"^\s*([+.-]?)(Default(?:Enemy|Objective|Mission|Soldier)Scoring(?:Table)?|RestartScorePenalty)\s*=\s*(.*?)\s*$")
FIELD = re.compile(r'(\w+)\s*=\s*(?:"([^"]*)"|(-?\d+))')
ENEMY_FIELDS = ("StartingPoints", "MinPoints", "DecreasePerTurn", "TurnOffset",
                "SpawnedPoints", "ReinforcementPoints", "DisabledPoints", "MinDisabledPoints")
OBJECTIVE_FIELDS = ("StartingPoints", "MinPoints", "DecreasePerTurn", "TurnOffset")
SOLDIER_FIELDS = ("UninjuredBonus", "WoundedBonus", "RescuedCivilianBonus")


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
        match = CONFIG_LINE.match(line)
        if not match:
            continue
        operation, kind, rhs = match.groups()
        if kind == "RestartScorePenalty":
            try:
                value = int(rhs)
            except ValueError as exc:
                raise ValueError(f"{source['filename']}:{number}: invalid penalty") from exc
            records.append((operation, kind, {"Value": value}, number))
            continue
        if not rhs.startswith("(") or not rhs.endswith(")"):
            raise ValueError(f"{source['filename']}:{number}: malformed scoring tuple")
        values = {}
        for entry in FIELD.finditer(rhs[1:-1]):
            key, quoted, numeric = entry.groups()
            if key in values:
                raise ValueError(f"{source['filename']}:{number}: repeated field {key}")
            values[key] = quoted if quoted is not None else int(numeric)
        required = SCORING_KEYS[kind]
        if any(key not in values for key in required):
            raise ValueError(f"{source['filename']}:{number}: missing scoring identity")
        fields = (ENEMY_FIELDS if kind.startswith("DefaultEnemy") else
                  OBJECTIVE_FIELDS if kind.startswith(("DefaultObjective", "DefaultMission")) else
                  SOLDIER_FIELDS)
        if any(key not in values or not isinstance(values[key], int) for key in fields):
            raise ValueError(f"{source['filename']}:{number}: incomplete scoring values")
        if not all(ch in (",", " ", "\t") for ch in FIELD.sub("", rhs[1:-1])):
            raise ValueError(f"{source['filename']}:{number}: unsupported scoring syntax")
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
            if operation == "-":
                raise ValueError(f"{origin['filename']}:{line}: removal cannot be safely resolved")
            category = ("enemy" if kind.startswith("DefaultEnemy") else
                        "objective" if kind.startswith("DefaultObjective") else
                        "mission" if kind.startswith("DefaultMission") else None)
            if category is None or kind == "RestartScorePenalty" or not kind.endswith("Table"):
                if kind in defaults and defaults[kind] != entry:
                    raise ValueError(f"{origin['filename']}:{line}: conflicting {kind} default")
                defaults[kind] = entry
                continue
            identity_fields = SCORING_KEYS[kind]
            identity = tuple(entry[key] for key in identity_fields)
            if identity in categories[category] and categories[category][identity] != entry:
                raise ValueError(f"{origin['filename']}:{line}: ambiguous {kind} override {identity}")
            categories[category][identity] = entry
    return {"sources": sources, "defaults": defaults, "categories": categories}


def decayed(record, turn):
    """Explicit v2 convention for diagnostic comparison, NOT proven native C++."""
    if turn < 0:
        raise ValueError("native turn unknown")
    return max(record["MinPoints"],
               record["StartingPoints"] - max(0, turn - record["TurnOffset"])
               * record["DecreasePerTurn"])


def previous_v2_decayed(record, turn):
    """The historic JSON uses snake_case, unlike native INI's PascalCase."""
    return max(record["min_points"],
               record["starting_points"] - max(0, turn - record["turn_offset"])
               * record["decrease_per_turn"])


def rate_for_enemy(rules, template):
    return rules["categories"]["enemy"].get((template,), rules["defaults"]["DefaultEnemyScoring"])


def rate_for_objective(rules, mission, text_pool, group, line):
    key = (mission, text_pool, group, line)
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
