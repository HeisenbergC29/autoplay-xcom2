"""Parser checks using a handcrafted table fixture, never an SDK/game binary.

The fixture models table structure only. It is not executable UE3 bytecode and
passing these checks is not compilation or game validation.
"""

import importlib.util
import hashlib
from io import BytesIO
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from zipfile import BadZipFile, ZipFile, ZipInfo, ZIP_STORED


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("compiled_checks", ROOT / "tools/check-compiled-package.py")
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


def i32(*values):
    return struct.pack("<" + "i" * len(values), *values)


def fstring(value):
    data = value.encode("ascii") + b"\0"
    return i32(len(data)) + data


def table_fixture(foreign_package="XComGame", extra_classes=None):
    classes = CHECKS.EXPECTED_CLASSES | (extra_classes or {})
    names = list(dict.fromkeys(["None", "Core", "Engine", foreign_package, "Class", "Package",
                               "Object", "Actor", "UIScreenListener", "UIPanel", "X2DownloadableContentInfo",
                               *classes]))
    name_index = {name: index for index, name in enumerate(names)}
    name_table = b"".join(fstring(name) + struct.pack("<Q", 0) for name in names)
    package_names = ["Core", "Engine", foreign_package]
    imports = [("Core", "Package", 0, name) for name in package_names]
    imports += [("Core", "Class", -1, "Object"), ("Core", "Class", -2, "Actor")]
    imports += [("Core", "Class", -3, name) for name in
                ("UIScreenListener", "UIPanel", "X2DownloadableContentInfo")]
    import_table = b"".join(i32(name_index[cp], 0, name_index[cn], 0, outer, name_index[name], 0)
                            for cp, cn, outer, name in imports)
    export_count = len(classes)
    name_offset = 129
    import_offset = name_offset + len(name_table)
    export_offset = import_offset + len(import_table)
    depends_offset = export_offset + export_count * 68
    header_size = depends_offset + export_count * 4
    supers = {"Object": -4, "Actor": -5, "UIScreenListener": -6,
              "UIPanel": -7, "X2DownloadableContentInfo": -8}
    export_table = b""
    for index, (name, superclass) in enumerate(classes.items()):
        export_table += (i32(0, supers[superclass], 0, name_index[name], 0, 0)
                         + struct.pack("<Q", 0) + i32(1, header_size + index, 0, 0)
                         + bytes(16) + i32(0))
    header = (struct.pack("<II", 0x9E2A83C1, 845 | (120 << 16)) + i32(header_size)
              + fstring("None") + struct.pack("<I", 0x200001)
              + i32(len(names), name_offset, export_count, export_offset,
                    len(imports), import_offset, depends_offset, header_size, 0, 0, 0)
              + bytes(16) + i32(1, export_count, len(names), export_count, 8917, 0, 0, 0, 0, 0, 0))
    assert len(header) == name_offset
    data = header + name_table + import_table + export_table + bytes(export_count * 4) + bytes(export_count)
    return data, {"import_offset": import_offset, "export_offset": export_offset}


def archive_fixture(package, extra=()):
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        for name in sorted(CHECKS.REQUIRED_FILES):
            payload = package if name.endswith(".u") else b"fixture content"
            archive.writestr(name.replace("/", "\\"), payload)
        for name, payload in extra:
            archive.writestr(name, payload)
    return output.getvalue()


class CompiledTableTests(unittest.TestCase):
    def test_require_recorder_cli_distinguishes_new_installer_from_legacy(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'mod.zip'
            command = [sys.executable, str(ROOT / 'tools/check-compiled-package.py'),
                       str(archive), '--require-recorder']
            legacy, _ = table_fixture()
            archive.write_bytes(archive_fixture(legacy))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('predates mission recording', result.stderr)
            current, _ = table_fixture(extra_classes={"APX_MissionRecorder": "Object"})
            archive.write_bytes(archive_fixture(current))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('collector is missing', result.stderr)
            archive.write_bytes(archive_fixture(current, extra=[
                ('AutoplayXCom2/Diagnostics/Collect-MissionRecording.ps1', b'# fixture')]))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_accepts_new_mission_recorder_with_stock_superclass(self):
        data, _ = table_fixture(extra_classes={"APX_MissionRecorder": "Object"})
        report = CHECKS.parse_ue3_package(data)
        self.assertIn("APX_MissionRecorder", report["own_classes"])

    def test_rejects_unknown_additional_class(self):
        data, _ = table_fixture(extra_classes={"UnrelatedClass": "Object"})
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "unexpected mod classes"):
            CHECKS.parse_ue3_package(data)

    def test_parses_handcrafted_stock_roots_and_nine_classes(self):
        data, _ = table_fixture()
        report = CHECKS.parse_ue3_package(data)
        self.assertEqual(set(report["import_roots"]), {"Core", "Engine", "XComGame"})
        self.assertEqual(set(report["own_classes"]), set(CHECKS.EXPECTED_CLASSES))
        self.assertFalse(report["exact_source_revision_verified"])

    def test_rejects_unsupported_version(self):
        data, _ = table_fixture()
        mutated = bytearray(data)
        struct.pack_into("<I", mutated, 4, 844 | (120 << 16))
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "Unsupported UE3 layout"):
            CHECKS.parse_ue3_package(mutated)

    def test_rejects_external_package_root(self):
        data, _ = table_fixture("CommunityHighlander")
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "External package dependency"):
            CHECKS.parse_ue3_package(data)

    def test_rejects_import_ownership_cycle(self):
        data, offsets = table_fixture()
        mutated = bytearray(data)
        struct.pack_into("<i", mutated, offsets["import_offset"] + 3 * 28 + 16, -4)
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "Cycle"):
            CHECKS.parse_ue3_package(mutated)

    def test_rejects_truncated_payload_and_bad_name(self):
        data, offsets = table_fixture()
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "outside the package"):
            CHECKS.parse_ue3_package(data[:-1])
        mutated = bytearray(data)
        struct.pack_into("<i", mutated, offsets["export_offset"] + 12, 999999)
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "FName"):
            CHECKS.parse_ue3_package(mutated)

    def test_rejects_unsupported_export_generation_layout(self):
        data, offsets = table_fixture()
        mutated = bytearray(data)
        struct.pack_into("<i", mutated, offsets["export_offset"] + 44, 1)
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "per-export generation"):
            CHECKS.parse_ue3_package(mutated)


class ArchiveTests(unittest.TestCase):
    def inspect_bytes(self, data):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mod.zip"
            path.write_bytes(data)
            return CHECKS.inspect_zip(path)

    def test_normalizes_windows_archive_and_verifies_required_files(self):
        package, _ = table_fixture()
        report = self.inspect_bytes(archive_fixture(package))
        self.assertIn("AutoplayXCom2/Script/AutoplayXCom2.u", report["files"])

    def test_rejects_unsafe_or_wrong_root_paths(self):
        for name in ("../escape", "AutoplayXCom2\\..\\escape", "/AutoplayXCom2/file",
                     "C:\\AutoplayXCom2\\file", "OtherMod/file", "AutoplayXCom2/Config./file"):
            with self.subTest(name=name), self.assertRaises(CHECKS.InvalidPackage):
                CHECKS.normalized_entry_name(name)

    def test_rejects_unexpected_executable_payload(self):
        package, _ = table_fixture()
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "Unexpected installer payload"):
            self.inspect_bytes(archive_fixture(package, [("AutoplayXCom2/extra.exe", b"fixture")]))

    def test_accepts_and_verifies_build_metadata(self):
        package, _ = table_fixture()
        base = archive_fixture(package)
        with ZipFile(BytesIO(base)) as archive:
            hashes = {name.replace("\\", "/")[len(CHECKS.ROOT) + 1:]:
                      hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
        metadata = {"compiled_package": {"size": len(package), "sha256": hashlib.sha256(package).hexdigest()},
                    "member_sha256": hashes}
        data = archive_fixture(package, [("AutoplayXCom2/BUILD-INFO.json", json.dumps(metadata).encode())])
        self.assertTrue(self.inspect_bytes(data)["build_info_hashes_consistent"])
        metadata["compiled_package"]["sha256"] = "wrong"
        data = archive_fixture(package, [("AutoplayXCom2/BUILD-INFO.json", json.dumps(metadata).encode())])
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "binary hash/size mismatch"):
            self.inspect_bytes(data)

    def test_rejects_case_colliding_entries(self):
        package, _ = table_fixture()
        extra = [("AutoplayXCom2/CONFIG/XComGame.ini", b"different")]
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "Duplicate/case-colliding"):
            self.inspect_bytes(archive_fixture(package, extra))

    def test_rejects_missing_required_file(self):
        output = BytesIO()
        with ZipFile(output, "w") as archive:
            archive.writestr("AutoplayXCom2/INSTALL.pl.md", b"fixture")
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "Missing installation files"):
            self.inspect_bytes(output.getvalue())

    def test_rejects_symbolic_link(self):
        package, _ = table_fixture()
        output = BytesIO(archive_fixture(package))
        with ZipFile(output, "a") as archive:
            info = ZipInfo("AutoplayXCom2/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "../../elsewhere")
        with self.assertRaisesRegex(CHECKS.InvalidPackage, "links"):
            self.inspect_bytes(output.getvalue())

    def test_crc_damage_is_rejected(self):
        package, _ = table_fixture()
        data = bytearray(archive_fixture(package))
        with ZipFile(BytesIO(data)) as archive:
            info = archive.infolist()[0]
            name_length, extra_length = struct.unpack_from("<HH", data, info.header_offset + 26)
            payload = info.header_offset + 30 + name_length + extra_length
        data[payload] ^= 1
        with self.assertRaises((CHECKS.InvalidPackage, BadZipFile)) as caught:
            self.inspect_bytes(data)
        self.assertIn("CRC", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
