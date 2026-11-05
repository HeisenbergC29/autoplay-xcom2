"""Configuration regression checks prompted by the real 59-warning build.

INI data must initialize config properties; these are not engine/gameplay tests.
"""

from collections import Counter
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('sdk_config_checks', ROOT / 'tools/check-sdk-references.py')
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


class ConfigDefaultsTests(unittest.TestCase):
    def test_flags_scalar_array_and_inherited_config_assignments(self):
        original = (
            'var config int MinimumTargets;\n'
            'var config array<name> AttackAbilities;\n'
            'defaultproperties\n{\n'
            '    MinimumTargets=2\n'
            '    AttackAbilities(0)="StandardShot"\n'
            '    DLCIdentifier="AutoplayXCom2"\n'
            '    bHidden=true\n}\n'
        )
        flagged = CHECKS.forbidden_config_defaults(original, {'DLCIdentifier'})
        self.assertEqual([name for _, name in flagged],
                         ['MinimumTargets', 'AttackAbilities', 'DLCIdentifier'])

    def test_every_declared_config_property_has_ini_values(self):
        ini = ROOT / 'AutoplayXCom2/Config/XComAutoplayXCom2.ini'
        entries = CHECKS.read_config_entries(ini)
        configured = {(section.casefold(), key.casefold()) for section, key, _ in entries}
        for file in (ROOT / 'AutoplayXCom2/Src').rglob('*.uc'):
            for name in CHECKS.declared_config_properties(file.read_text()):
                with self.subTest(file=file.name, property=name):
                    self.assertIn((f'autoplayxcom2.{file.stem}'.casefold(), name), configured)

    def test_combat_lists_survive_migration_and_keep_core_actions(self):
        entries = CHECKS.read_config_entries(ROOT / 'AutoplayXCom2/Config/XComAutoplayXCom2.ini')
        combat = [(key, value) for section, key, value in entries
                  if section == 'AutoplayXCom2.APX_CombatPlanner' and key.endswith('Abilities')]
        self.assertEqual(Counter(key for key, _ in combat), {
            'AttackAbilities': 18, 'HealAbilities': 4, 'StabilizeAbilities': 2,
            'ReloadAbilities': 1, 'OverwatchAbilities': 4, 'HunkerAbilities': 1,
            'SupportAbilities': 1})
        self.assertEqual(len(combat), len(set(combat)))
        self.assertTrue({('AttackAbilities', 'StandardShot'), ('AttackAbilities', 'Rend'),
                         ('AttackAbilities', 'DevastatingPunch'),
                         ('AttackAbilities', 'DevastatingPunchMP'),
                         ('HealAbilities', 'GremlinHeal'), ('ReloadAbilities', 'Reload'),
                         ('OverwatchAbilities', 'Overwatch'),
                         ('SupportAbilities', 'AidProtocol')} <= set(combat))

    def test_dlc_identifier_uses_inherited_game_config(self):
        entries = CHECKS.read_config_entries(ROOT / 'AutoplayXCom2/Config/XComGame.ini')
        self.assertIn(('AutoplayXCom2.X2DownloadableContentInfo_AutoplayXCom2',
                       'DLCIdentifier', 'AutoplayXCom2'), entries)

    def test_mod_has_no_rejected_config_initializers(self):
        for file in (ROOT / 'AutoplayXCom2/Src').rglob('*.uc'):
            with self.subTest(file=file.name):
                self.assertEqual(CHECKS.forbidden_config_defaults(
                    file.read_text(), {'DLCIdentifier'}), [])


if __name__ == '__main__':
    unittest.main()
