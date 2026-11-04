"""Reproduce the published derived catalog from the private SDK/config inputs."""
import importlib.util
import json
import os
from pathlib import Path
import unittest

from test_unit_definitions import AUDIT


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ('APX_SDK_SOURCE_ROOT', 'APX_GAME_CONFIG_ROOT', 'APX_SDK_CONFIG_ROOT', 'APX_GAME_DLC_ROOT')
DLC_ORDER = ('DLC_1', 'DLC_2', 'DLC_3', 'TLE', 'XCom_DLC_Day0')


@unittest.skipUnless(all(os.environ.get(name) for name in INPUTS),
                     'Configured catalog contracts need SDK, base config snapshots and game DLC folders')
class ConfiguredCatalogContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('apx_unit_config_contract', ROOT / 'tools/unit_config.py')
        configuration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(configuration)
        cls.configuration = configuration
        source_catalog = AUDIT.build_catalog(Path(os.environ['APX_SDK_SOURCE_ROOT']))
        cls.catalog = configuration.enrich_catalog(
            source_catalog, Path(os.environ['APX_GAME_CONFIG_ROOT']),
            Path(os.environ['APX_SDK_CONFIG_ROOT']),
            game_dlc={name: Path(os.environ['APX_GAME_DLC_ROOT']) / name for name in DLC_ORDER})

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

    def test_ruler_spark_and_legacy_stats_come_from_their_own_dlc_sections(self):
        units = {unit['template_name']: unit for unit in self.catalog['units']}
        expected = {'ViperKing': (69, 75, 14, 3), 'BerserkerQueen': (100, 75, 14, 4),
                    'ArchonKing': (120, 75, 14, 5), 'SparkSoldier': (10, 70, 12, 1),
                    'LostTowersSpark': (10, 65, 12, 1), 'Sectopod_Markov': (100, 65, 16, 7),
                    'FeralMEC_M1': (4, 65, 14, 3), 'ViperNeonate': (2, 60, 17, 0),
                    'PsiZombieCivilian': (4, 75, 12, 0), 'NeonateChryssalid': (4, 75, 12, 0)}
        for name, values in expected.items():
            with self.subTest(unit=name):
                stats = units[name]['config_values']['stats']
                self.assertEqual(stats['status'], 'present')
                legend = stats['difficulty']['3']['values']
                self.assertEqual(tuple(legend[key] for key in
                                       ('eStat_HP', 'eStat_Offense', 'eStat_Mobility', 'eStat_ArmorMitigation')),
                                 values)
                self.assertFalse(stats['effective_values_complete'])

    def test_only_two_proxy_weapon_symbols_remain_unknown_without_inventing_m1_damage(self):
        unresolved = {reference for weapon in self.catalog['weapon_definitions']
                      for reference in weapon['config_values']['unresolved_references'].values()}
        self.assertEqual(unresolved, {'default.FERALMEC_M2_PROXY_WPN_BASEDAMAGE',
                                     'default.FERALMEC_M3_PROXY_WPN_BASEDAMAGE'})
        weapons = {weapon['name']: weapon for weapon in self.catalog['weapon_definitions']}
        for name in ('Medikit', 'NanoMedikit'):
            category = weapons[name]['config_values']['resolved_properties']['WeaponCat']
            self.assertEqual(category['value'], 'medikit')
            self.assertTrue(category['source']['file'].endswith('X2Item_DefaultUtilityItems.uc'))

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

    def test_dlc_provenance_records_all_five_game_archives_without_claiming_native_order(self):
        dlc = self.catalog['configuration_audit']['dlc_configuration']
        self.assertEqual(dlc['source'], 'game_installation')
        self.assertEqual(dlc['input_order'], list(DLC_ORDER))
        self.assertFalse(dlc['native_load_order_verified'])
        self.assertEqual(sum(dataset['ini_file_count'] for dataset in dlc['datasets']), 79)
        self.assertEqual(sum(file['bytes'] for dataset in dlc['datasets'] for file in dataset['files']), 796252)

    def test_actual_ai_removals_replace_earlier_nodes_and_keep_the_dlc3_origin(self):
        config = self.configuration
        base = config._documents(Path(os.environ['APX_GAME_CONFIG_ROOT']))
        layers = [config._dlc_documents(config._config_dir(Path(os.environ['APX_GAME_DLC_ROOT']) / name), name)
                  for name in DLC_ORDER]
        section = 'XComGame.X2AIBTBehaviorTree'
        replaced = {entry['value']['BehaviorName']
                    for layer in layers if 'AI' in layer
                    for entry in layer['AI'].sections.get(section, [])
                    if entry['key'] == 'Behaviors' and entry['operation'] == '-'
                    and isinstance(entry['value'], dict) and 'BehaviorName' in entry['value']}
        self.assertEqual(len(replaced), 13)
        ai = config._compose_documents(base, layers)['AI']
        remaining = ai.entries(section, 'Behaviors')
        for name in replaced:
            with self.subTest(behavior=name):
                matches = [entry for entry in remaining if isinstance(entry['value'], dict)
                           and entry['value'].get('BehaviorName') == name]
                self.assertEqual(len(matches), 1)
        for name in ('SetTargetStack-KingBind', 'ArchonKing::CustomMeleeTargetScore',
                     'IsAbilityReady-IcarusDropGrab', 'SetTargetStack-IcarusDropGrab'):
            entry = next(entry for entry in remaining if isinstance(entry['value'], dict)
                         and entry['value'].get('BehaviorName') == name)
            self.assertEqual(ai.source(section, entry)['dataset'], 'game_dlc:DLC_3')


if __name__ == '__main__':
    unittest.main()
