"""Reproduce the published derived catalog from the private SDK/config inputs."""
import importlib.util
import json
import os
from pathlib import Path
import unittest

from test_unit_definitions import AUDIT


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ('APX_SDK_SOURCE_ROOT', 'APX_GAME_CONFIG_ROOT', 'APX_SDK_CONFIG_ROOT')


@unittest.skipUnless(all(os.environ.get(name) for name in INPUTS),
                     'Configured catalog contracts need the supplied SDK and both config snapshots')
class ConfiguredCatalogContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('apx_unit_config_contract', ROOT / 'tools/unit_config.py')
        configuration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(configuration)
        source_catalog = AUDIT.build_catalog(Path(os.environ['APX_SDK_SOURCE_ROOT']))
        cls.catalog = configuration.enrich_catalog(
            source_catalog, Path(os.environ['APX_GAME_CONFIG_ROOT']),
            Path(os.environ['APX_SDK_CONFIG_ROOT']))

    def test_checked_in_configuration_facts_are_reproducible(self):
        published = json.loads((ROOT / 'data/unit-catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(self.catalog, published)

    def test_derived_catalog_does_not_expose_private_absolute_paths(self):
        serialized = json.dumps(self.catalog)
        for private_path in ('/workspace/', '/tmp/', 'sediment://'):
            self.assertNotIn(private_path, serialized)

    def test_partial_legend_overrides_preserve_base_stats_and_explicit_zero(self):
        units = {unit['template_name']: unit for unit in self.catalog['units']}
        expected = {'AdvTrooperM1': (4, 65, 12), 'AdvCaptainM1': (7, 75, 12),
                    'Sectoid': (10, 75, 12), 'PsiZombie': (8, 75, 15),
                    'Faceless': (12, 75, 14), 'Viper': (10, 75, 15)}
        for name, values in expected.items():
            with self.subTest(unit=name):
                stats = units[name]['config_values']['stats']
                legend = stats['difficulty']['3']['values']
                self.assertEqual(tuple(legend[key] for key in
                                       ('eStat_HP', 'eStat_Offense', 'eStat_Mobility')), values)
                self.assertEqual(legend['eStat_Defense'], 0)
                self.assertFalse(stats['effective_values_complete'])
        missing = units['ViperKing']['config_values']['stats']
        self.assertEqual(missing['status'], 'not_present')
        self.assertNotIn('eStat_HP', missing['difficulty']['3']['values'])

    def test_zombie_uses_equipped_melee_damage_instead_of_similar_unused_symbol(self):
        zombie = next(unit for unit in self.catalog['units'] if unit['template_name'] == 'PsiZombie')
        items = zombie['config_values']['loadout']['items']
        self.assertEqual([item['item'] for item in items], ['PsiZombie_MeleeAttack'])
        weapon = next(weapon for weapon in self.catalog['weapon_definitions']
                      if weapon['name'] == items[0]['item'])
        fact = weapon['config_values']['resolved_properties']['BaseDamage']
        self.assertEqual((fact['value']['Damage'], fact['value']['Spread'], fact['value']['PlusOne']),
                         (4, 1, 0))
        self.assertEqual(fact['source']['key'], 'PsiZombie_MeleeAttack_BaseDamage')

    def test_sdk_files_corroborate_defaults_without_becoming_game_overrides(self):
        audit = self.catalog['configuration_audit']
        self.assertEqual(audit['primary_dataset'], 'game_defaults')
        self.assertEqual(len(audit['default_files']), 7)
        self.assertTrue(all(item['identical'] for item in audit['default_files']))
        self.assertFalse(audit['generated_configuration']['used_as_overrides'])


if __name__ == '__main__':
    unittest.main()
