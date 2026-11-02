#!/usr/bin/env python3
"""Inspect this mod's installer ZIP and supported WOTC UE3 package tables.

Does not execute UnrealScript, validate native gameplay, or attest a Steam build.
Only the little-endian UE3 845/licensee-120 layout emitted by the supplied SDK
is supported. No game/SDK files are bundled with this tool.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys
from zipfile import BadZipFile, ZipFile


ROOT = "AutoplayXCom2"
ALLOWED_PACKAGES = {"Core", "Engine", "XComGame"}
EXPECTED_CLASSES = {
    "APX_AreaAttackPlanner": "Object",
    "APX_CombatPlanner": "Object",
    "APX_Controller": "Actor",
    "APX_EvacPlanner": "Object",
    "APX_ExplorationPlanner": "Object",
    "APX_MissionPlanner": "Object",
    "APX_ScreenListener": "UIScreenListener",
    "APX_UITacticalControl": "UIPanel",
    "X2DownloadableContentInfo_AutoplayXCom2": "X2DownloadableContentInfo",
}
OPTIONAL_CLASSES = {"APX_MissionRecorder": "Object", "APX_SquadPlanner": "Object"}
REQUIRED_FILES = {
    f"{ROOT}/AutoplayXCom2.XComMod",
    f"{ROOT}/INSTALL.pl.md",
    f"{ROOT}/Config/XComEngine.ini",
    f"{ROOT}/Config/XComGame.ini",
    f"{ROOT}/Config/XComAutoplayXCom2.ini",
    f"{ROOT}/Localization/AutoplayXCom2.int",
    f"{ROOT}/Localization/AutoplayXCom2.pol",
    f"{ROOT}/Script/AutoplayXCom2.u",
}
MAX_BINARY_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
OPTIONAL_FILES = {f"{ROOT}/.apx-build-owned", f"{ROOT}/BUILD-INFO.json",
                  f"{ROOT}/Diagnostics/Collect-MissionRecording.ps1"}


class InvalidPackage(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidPackage(message)


class Reader:
    def __init__(self, data: bytes, position: int = 0):
        self.data = data
        self.position = position

    def take(self, size: int) -> bytes:
        require(size >= 0 and self.position + size <= len(self.data), "Truncated package data.")
        result = self.data[self.position:self.position + size]
        self.position += size
        return result

    def i32(self) -> int:
        return struct.unpack("<i", self.take(4))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.take(8))[0]

    def fstring(self) -> str:
        count = self.i32()
        require(abs(count) <= MAX_BINARY_BYTES // 2, "Invalid FString length.")
        if count == 0:
            return ""
        raw = self.take(count if count > 0 else -2 * count)
        if count > 0:
            require(raw.endswith(b"\0"), "Unterminated ANSI FString.")
            return raw[:-1].decode("latin-1")
        require(raw.endswith(b"\0\0"), "Unterminated UTF-16 FString.")
        try:
            return raw[:-2].decode("utf-16le")
        except UnicodeDecodeError as error:
            raise InvalidPackage("Invalid UTF-16 FString.") from error


def normalized_entry_name(name: str) -> str:
    """Windows Compress-Archive emits backslashes; never extract ZIP entries."""
    value = name.replace("\\", "/")
    require(value and "\0" not in value and ":" not in value, "Invalid archive entry path.")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts, "Unsafe archive entry path.")
    require(path.parts and path.parts[0] == ROOT, f"Archive must have one {ROOT}/ root.")
    require(all(not part.endswith((".", " ")) for part in path.parts), "Ambiguous Windows archive path.")
    return str(path)


def parse_ue3_package(data: bytes) -> dict:
    require(0 < len(data) <= MAX_BINARY_BYTES, "Compiled package is empty or too large.")
    reader = Reader(data)
    require(reader.u32() == 0x9E2A83C1, "Not a little-endian UE3 package.")
    version_word = reader.u32()
    version, licensee = version_word & 0xFFFF, version_word >> 16
    require((version, licensee) == (845, 120),
            f"Unsupported UE3 layout: version {version}, licensee {licensee}.")
    header_size = reader.i32()
    folder = reader.fstring()
    package_flags = reader.u32()
    name_count, name_offset = reader.i32(), reader.i32()
    export_count, export_offset = reader.i32(), reader.i32()
    import_count, import_offset = reader.i32(), reader.i32()
    depends_offset = reader.i32()
    guid_offset, import_guids, export_guids = reader.i32(), reader.i32(), reader.i32()
    thumbnail_offset = reader.i32()
    reader.take(16)  # Package GUID.
    require(reader.i32() == 1, "Unsupported generation table layout.")
    generation_exports, generation_names, generation_net = reader.i32(), reader.i32(), reader.i32()
    engine_version, cooker_version = reader.i32(), reader.i32()
    compression_flags, compressed_chunks = reader.u32(), reader.i32()
    reader.u32()  # Package source identifier.
    extra_packages, texture_allocations = reader.i32(), reader.i32()

    require(compression_flags == 0 and compressed_chunks == 0, "Compressed UE3 layout is unsupported.")
    require(import_guids == export_guids == thumbnail_offset == extra_packages == texture_allocations == 0,
            "Unsupported optional package-header tables.")
    require(all(0 < n <= 200000 for n in (name_count, import_count, export_count)), "Invalid table counts.")
    require((generation_exports, generation_names) == (export_count, name_count)
            and 0 <= generation_net <= export_count, "Invalid generation record.")
    require(reader.position <= name_offset <= import_offset <= export_offset <= depends_offset <= header_size <= len(data),
            "Invalid package table offsets.")
    require(0 <= guid_offset <= header_size, "Invalid GUID table offset.")
    require(import_offset + import_count * 28 == export_offset,
            "Unsupported or damaged 28-byte import table.")
    require(export_offset + export_count * 68 == depends_offset,
            "Unsupported or damaged 68-byte export table.")

    reader.position = name_offset
    names = []
    for _ in range(name_count):
        names.append(reader.fstring())
        reader.u64()  # Name flags.
        require(reader.position <= import_offset, "Name table overlaps import table.")
    require(reader.position == import_offset, "Unsupported name table layout.")

    def fname(index: int, number: int) -> str:
        require(0 <= index < len(names) and number >= 0, "Invalid FName index/number.")
        return names[index] + (f"_{number - 1}" if number else "")

    imports = []
    reader.position = import_offset
    for index in range(import_count):
        class_package = fname(reader.i32(), reader.i32())
        class_name = fname(reader.i32(), reader.i32())
        outer = reader.i32()
        name = fname(reader.i32(), reader.i32())
        require(class_package in ALLOWED_PACKAGES, f"External class package dependency: {class_package}.")
        imports.append({"index": -index - 1, "name": name, "outer": outer,
                        "class_name": class_name, "class_package": class_package})

    exports = []
    reader.position = export_offset
    for index in range(export_count):
        class_index, super_index, outer = reader.i32(), reader.i32(), reader.i32()
        name = fname(reader.i32(), reader.i32())
        archetype = reader.i32()
        reader.u64()  # Object flags.
        size, offset = reader.i32(), reader.i32()
        reader.u32()  # Export flags.
        require(reader.i32() == 0, "Unsupported per-export generation records.")
        reader.take(16)  # Export package GUID.
        reader.u32()  # Export package flags.
        require(size >= 0 and 0 <= offset <= len(data) and offset + size <= len(data),
                "Export payload is outside the package.")
        require(not size or offset >= header_size, "Export payload overlaps package tables.")
        exports.append({"index": index + 1, "name": name, "outer": outer,
                        "class_index": class_index, "super_index": super_index,
                        "archetype": archetype, "size": size, "offset": offset})

    def object_for(index: int) -> dict:
        require(index != 0 and -import_count <= index <= export_count, "Invalid object index.")
        return imports[-index - 1] if index < 0 else exports[index - 1]

    for obj in imports + exports:
        for field in ("outer", "class_index", "super_index", "archetype"):
            if obj.get(field):
                object_for(obj[field])

    def root_for(obj: dict) -> str:
        visited = set()
        while obj["outer"]:
            require(obj["outer"] not in visited, "Cycle in object ownership chain.")
            visited.add(obj["outer"])
            obj = object_for(obj["outer"])
        return obj["name"]

    roots = Counter(root_for(obj) for obj in imports)
    require(set(roots) <= ALLOWED_PACKAGES, f"External package dependency: {sorted(set(roots) - ALLOWED_PACKAGES)}.")
    own_classes = [obj for obj in exports if obj["class_index"] == 0]
    class_names = {obj["name"] for obj in own_classes}
    known_classes = EXPECTED_CLASSES | OPTIONAL_CLASSES
    require(set(EXPECTED_CLASSES) <= class_names <= set(known_classes)
            and len(own_classes) == len(class_names),
            "Compiled package has missing, duplicate or unexpected mod classes.")
    for obj in own_classes:
        require(obj["super_index"] != 0 and object_for(obj["super_index"])["name"] == known_classes[obj["name"]],
                f"Unexpected superclass for {obj['name']}.")
    payloads = sorted((obj["offset"], obj["offset"] + obj["size"]) for obj in exports if obj["size"])
    require(all(a[1] <= b[0] for a, b in zip(payloads, payloads[1:])), "Overlapping export payloads.")

    embedded = []
    for obj in exports:
        if obj["class_index"] >= 0 or object_for(obj["class_index"])["name"] != "TextBuffer":
            continue
        require(obj["outer"] > 0, "Invalid embedded source owner.")
        text = Reader(data[obj["offset"]:obj["offset"] + obj["size"]])
        require(text.i32() == -1, "Unsupported TextBuffer network index.")
        require(fname(text.i32(), text.i32()) == "None", "Unsupported TextBuffer properties.")
        text.i32()  # Cursor position.
        text.i32()  # Top line.
        source = text.fstring()
        require(text.position == len(text.data), "Unsupported TextBuffer payload layout.")
        embedded.append({"class": object_for(obj["outer"])["name"],
                         "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                         "has_stop_autoplay": bool(re.search(r"\bStopAutoplay\s*\(", source)),
                         "has_mission_goal": bool(re.search(r"\bstruct\s+MissionGoal\b", source))})

    return {
        "binary_bytes": len(data), "binary_sha256": hashlib.sha256(data).hexdigest(),
        "header": {"file_version": version, "licensee_version": licensee,
                   "engine_version": engine_version, "cooker_version": cooker_version,
                   "package_flags": package_flags, "folder": folder},
        "tables": {"names": name_count, "imports": import_count, "exports": export_count},
        "import_roots": dict(sorted(roots.items())),
        "imported_classes": sorted(obj["name"] for obj in imports if obj["class_name"] == "Class"),
        "own_classes": sorted(obj["name"] for obj in own_classes),
        "embedded_source": embedded,
        "exact_source_revision_verified": False,
        "scope": "ZIP/package table inspection only; no game execution, native API behavior, or Steam-version compatibility test. Embedded source is macro-expanded and excludes defaultproperties.",
    }


def inspect_zip(path: Path) -> dict:
    require(path.stat().st_size <= MAX_ARCHIVE_BYTES, "Installer archive is too large.")
    with ZipFile(path) as archive:
        infos = archive.infolist()
        require(0 < len(infos) <= 128, "Invalid archive entry count.")
        require(sum(info.file_size for info in infos) <= MAX_ARCHIVE_BYTES, "Expanded archive is too large.")
        entries = {}
        seen = set()
        for info in infos:
            name = normalized_entry_name(info.filename)
            require(name.casefold() not in seen, "Duplicate/case-colliding archive entry.")
            seen.add(name.casefold())
            mode = (info.external_attr >> 16) & 0xFFFF
            require(not stat.S_ISLNK(mode), "Archive links are not supported.")
            require(not info.flag_bits & 1, "Encrypted archives are unsupported.")
            if not info.is_dir() and not info.filename.endswith(("/", "\\")):
                require(info.file_size <= MAX_BINARY_BYTES, "Archive entry is too large.")
                require(name in REQUIRED_FILES | OPTIONAL_FILES or name.lower().endswith(".md"),
                        f"Unexpected installer payload: {name}.")
                entries[name] = info
        require(REQUIRED_FILES <= set(entries), f"Missing installation files: {sorted(REQUIRED_FILES - set(entries))}.")
        require(archive.testzip() is None, "ZIP CRC verification failed.")
        data = archive.read(entries[f"{ROOT}/Script/AutoplayXCom2.u"])
        report = parse_ue3_package(data)
        report["archive_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        report["files"] = {name: info.file_size for name, info in sorted(entries.items())}
        info_name = f"{ROOT}/BUILD-INFO.json"
        report["build_info_present"] = info_name in entries
        if info_name in entries:
            try:
                build_info = json.loads(archive.read(entries[info_name]).decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise InvalidPackage("Invalid BUILD-INFO.json.") from error
            require(isinstance(build_info, dict), "BUILD-INFO must be a JSON object.")
            compiled = build_info.get("compiled_package", {})
            require(isinstance(compiled, dict) and compiled.get("sha256") == report["binary_sha256"]
                    and compiled.get("size") == report["binary_bytes"], "BUILD-INFO binary hash/size mismatch.")
            hashes = build_info.get("member_sha256")
            require(isinstance(hashes, dict), "BUILD-INFO must contain member hashes.")
            expected = {name[len(ROOT) + 1:] for name in entries if name != info_name}
            require(set(hashes) == expected, "BUILD-INFO member list mismatch.")
            for name, expected_hash in hashes.items():
                normalized = normalized_entry_name(f"{ROOT}/{name}")
                digest = hashlib.sha256(archive.read(entries[normalized])).hexdigest()
                require(digest == expected_hash, f"BUILD-INFO member hash mismatch: {name}.")
            report["build_info_hashes_consistent"] = True
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--json", type=Path, help="Optional path for the inspection report")
    parser.add_argument("--require-recorder", action="store_true", help="Require the new mission-recording class; rejects older packages")
    args = parser.parse_args()
    try:
        report = inspect_zip(args.archive)
        if args.require_recorder:
            require("APX_MissionRecorder" in report["own_classes"], "Package predates mission recording; rebuild current sources.")
            require(f"{ROOT}/Diagnostics/Collect-MissionRecording.ps1" in report["files"], "Mission report collector is missing from the installation package.")
        if args.json:
            args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("PASS: installer paths/CRC, supported UE3 tables, stock package roots and expected mod classes.")
        print("Dependencies:", ", ".join(report["import_roots"]))
        print("Binary SHA-256:", report["binary_sha256"])
        print(report["scope"])
        return 0
    except (InvalidPackage, BadZipFile, OSError, RuntimeError, struct.error) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
