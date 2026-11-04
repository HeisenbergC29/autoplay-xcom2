"""Configuration semantics using small, original fixtures (no bundled INIs)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('unit_config', ROOT / 'tools' / 'unit_config.py')
CONFIG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONFIG)


class IniParsingTests(unittest.TestCase):
    def document(self, text):
        return CONFIG.IniDocument(text, 'DefaultFixture.ini')

    def test_duplicate_bare_keys_preserve_order_and_sources(self):
        doc = self.document('[S]\nLoadouts=(LoadoutName="A",Items[0]=(Item="first"))\n'
                            'Loadouts=(LoadoutName="A",Items[0]=(Item="second"))\n')
        entries = doc.entries('s', 'loadouts')
        self.assertEqual([entry['value']['Items[0]']['Item'] for entry in entries], ['first', 'second'])
        self.assertEqual([entry['line'] for entry in entries], [2, 3])

    def test_array_operators_and_bare_duplicates(self):
        doc = self.document('[S]\n+Values=A\n+Values=A\n.Values=A\nValues=B\n'
                            '-Values=A\n+Values=C\n.Other=kept\n!Values=ClearArray\n+Values=D\n')
        self.assertEqual([entry['value'] for entry in doc.entries('S', 'Values')], ['D'])
        self.assertEqual([entry['value'] for entry in doc.entries('S', 'Other')], ['kept'])

    def test_add_unique_append_and_remove_are_distinct(self):
        doc = self.document('[S]\n+V=(A=1,B="x")\n+V=(A=1,B="x")\n.V=(A=1,B="x")\nV=2\n')
        self.assertEqual([entry['value'] for entry in doc.entries('S', 'V')],
                         [{'A': 1, 'B': 'x'}, {'A': 1, 'B': 'x'}, 2])

    def test_semicolon_inside_quoted_string_is_not_comment(self):
        doc = self.document('[S]\nValue=(Name="a;b",Number=0) ; comment\n')
        self.assertEqual(doc.entries('S')[0]['value'], {'Name': 'a;b', 'Number': 0})

    def test_multiline_double_backslashes_retain_first_physical_line(self):
        text = ('[S]\n; preamble\nBehaviors=(BehaviorName="Root", \\\\\n'
                ' Child[0]=First, \\\\\n Child[1]=Second) ; end\n')
        doc = self.document(text)
        entry = doc.entries('S')[0]
        self.assertEqual(entry['line'], 3)
        self.assertEqual(entry['value'], {'BehaviorName': 'Root', 'Child[0]': 'First', 'Child[1]': 'Second'})

    def test_nested_struct_array_quotes_and_numbers(self):
        parsed = CONFIG.parse_value('(Damage=4,Spread=1,PlusOne=0,Enabled=true,Radius=3.75,'
                                    'Items=("a,b",(Inner=-2)),Name="x=y;z")')
        self.assertEqual(parsed, {'Damage': 4, 'Spread': 1, 'PlusOne': 0, 'Enabled': True,
                                  'Radius': 3.75, 'Items': ['a,b', {'Inner': -2}], 'Name': 'x=y;z'})

    def test_repeated_struct_fields_are_not_discarded(self):
        self.assertEqual(CONFIG.parse_value('(Value=1,Value=2)'), {'Value': [1, 2]})

    def test_literal_parser_never_evaluates_code(self):
        self.assertEqual(CONFIG.parse_value('__import__("os").getcwd()'), '__import__("os").getcwd()')
        self.assertEqual(CONFIG.parse_value('SomeSymbol'), 'SomeSymbol')

    def test_read_windows_utf16_ini_with_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'DefaultFixture.ini'
            path.write_bytes('[S]\nValue="żółw"\n'.encode('utf-16'))
            doc = CONFIG.IniDocument.read(path)
        self.assertEqual(doc.entries('S', 'Value')[0]['value'], 'żółw')


class ConfigurationEnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.game = self.directory / 'game'
        self.sdk = self.directory / 'sdk'
        self.game.mkdir()
        self.sdk.mkdir()
        self.catalog = {
            'kind': 'fixture',
            'units': [{'template_name': 'Enemy', 'properties': {'CharacterGroupName': {'value': 'EnemyGroup'}},
                       'loadout': {'name': 'Enemy_Loadout'}}],
            'weapon_definitions': [{
                'name': 'Enemy_WPN', 'config': 'GameData_WeaponData',
                'source': {'file': 'XComGame/Classes/X2Item_Fixture.uc', 'line': 1},
                'properties': {
                    'BaseDamage': {'value': None, 'reference': 'default.DAMAGE'},
                    'iClipSize': {'value': None, 'reference': "class'X2Item_Base'.default.CLIP"},
                    'RangeAccuracy': {'value': None, 'reference': 'default.RANGE'},
                    'Aim': {'value': 0},
                },
            }],
        }

    def write(self, family, text, directory=None, generated=False):
        prefix = 'XCom' if generated else 'Default'
        (directory or self.game).joinpath(f'{prefix}{family}.ini').write_text(text, encoding='utf-8')

    def enrich(self, sdk=False):
        return CONFIG.enrich_catalog(self.catalog, self.game, self.sdk if sdk else None)

    def test_partial_difficulty_inherits_base_and_keeps_zero_distinct_from_missing(self):
        self.write('GameData_CharacterStats', '[Enemy X2CharacterTemplate]\n'
                   'CharacterBaseStats[eStat_HP]=4\nCharacterBaseStats[eStat_Defense]=0\n'
                   'CharacterBaseStats[eStat_Mobility]=12\n'
                   'RandomizedBaseStats=(StatType=eStat_Will,StatAmount=10,RandStatAmount=5)\n'
                   '[Enemy_Diff_3 X2CharacterTemplate]\nCharacterBaseStats[eStat_HP]=7\n')
        stats = self.enrich()['units'][0]['config_values']['stats']
        self.assertEqual(stats['base']['eStat_HP']['value'], 4)
        self.assertEqual(stats['difficulty']['3']['values'],
                         {'eStat_HP': 7, 'eStat_Defense': 0, 'eStat_Mobility': 12})
        self.assertEqual(set(stats['difficulty']['3']['overrides']), {'eStat_HP'})
        self.assertNotIn('eStat_ArmorMitigation', stats['difficulty']['3']['values'])
        self.assertFalse(stats['effective_values_complete'])
        self.assertEqual(stats['randomized_base_stats'][0]['value']['RandStatAmount'], 5)
        self.assertEqual(stats['difficulty']['3']['overrides']['eStat_HP']['source']['line'], 7)

    def test_missing_dlc_section_is_unknown_not_a_zero_stat_or_empty_loadout(self):
        result = self.enrich()['units'][0]['config_values']
        self.assertEqual(result['stats']['status'], 'not_present')
        self.assertEqual(result['stats']['base'], {})
        self.assertEqual(result['loadout']['status'], 'not_present')
        self.assertNotIn('items', result['loadout'])

    def test_difficulty_section_without_base_is_partial(self):
        self.write('GameData_CharacterStats', '[Enemy_Diff_2 X2CharacterTemplate]\nCharacterBaseStats[eStat_HP]=8\n')
        stats = self.enrich()['units'][0]['config_values']['stats']
        self.assertEqual(stats['status'], 'partial')
        self.assertEqual(stats['difficulty']['2']['values'], {'eStat_HP': 8})
        self.assertEqual(stats['difficulty']['0']['values'], {})

    def test_first_remaining_loadout_match_and_ordered_items(self):
        self.write('GameData', '[XComGame.X2ItemTemplateManager]\n'
                   'Loadouts=(LoadoutName="Enemy_Loadout",Items[1]=(Item="grenade"),Items[0]=(Item="rifle"))\n'
                   'Loadouts=(LoadoutName="Enemy_Loadout",Items[0]=(Item="wrong"))\n')
        loadout = self.enrich()['units'][0]['config_values']['loadout']
        self.assertEqual([item['item'] for item in loadout['items']], ['rifle', 'grenade'])
        self.assertEqual(loadout['matching_definitions'], 2)
        self.assertEqual(loadout['selection'], 'first_matching_definition')
        self.assertEqual(loadout['source']['line'], 2)

    def test_absent_declared_and_explicit_empty_loadouts_are_distinct(self):
        self.catalog['units'].extend([
            {'template_name': 'NoDeclaration', 'properties': {}},
            {'template_name': 'Empty', 'properties': {}, 'loadout': {'name': ''}},
        ])
        units = self.enrich()['units']
        self.assertEqual([unit['config_values']['loadout']['status'] for unit in units],
                         ['not_present', 'not_declared', 'explicit_empty'])

    def test_weapon_default_and_cross_class_references_struct_and_indexed_array(self):
        self.write('GameData_WeaponData', '[XComGame.X2Item_Fixture]\n'
                   'DAMAGE=(Damage=4,Spread=1,PlusOne=0)\nRANGE[0]=0\nRANGE[2]=-5\n'
                   '[XComGame.X2Item_Base]\nCLIP=3\n')
        weapon = self.enrich()['weapon_definitions'][0]['config_values']
        resolved = weapon['resolved_properties']
        self.assertEqual(resolved['BaseDamage']['value'], {'Damage': 4, 'Spread': 1, 'PlusOne': 0})
        self.assertEqual(resolved['iClipSize']['value'], 3)
        self.assertEqual([(x['index'], x['value']) for x in resolved['RangeAccuracy']['indexed_values']], [(0, 0), (2, -5)])
        self.assertNotIn('Aim', resolved)  # literal source value remains in original properties
        self.assertFalse(weapon['unresolved_references'])

    def test_unsupported_reference_and_missing_symbols_stay_unresolved(self):
        self.catalog['weapon_definitions'][0]['properties']['iRange'] = {'reference': 'default.RANGE + 1'}
        self.write('GameData_WeaponData', '[XComGame.X2Item_Fixture]\nOTHER=2\n')
        config = self.enrich()['weapon_definitions'][0]['config_values']
        self.assertEqual(config['unresolved_references']['iRange'], 'default.RANGE + 1')
        self.assertIn('BaseDamage', config['unresolved_references'])

    def test_explicit_cross_family_class_reference_requires_unique_section(self):
        self.catalog['weapon_definitions'][0]['properties']['iRange'] = {
            'reference': "class'X2Ability_Fixture'.default.MELEE_RANGE"}
        self.write('GameData_SoldierSkills', '[XComGame.X2Ability_Fixture]\nMELEE_RANGE=3\n')
        resolved = self.enrich()['weapon_definitions'][0]['config_values']['resolved_properties']
        self.assertEqual(resolved['iRange']['value'], 3)
        self.assertEqual(resolved['iRange']['source']['file'], 'DefaultGameData_SoldierSkills.ini')
        self.assertEqual(resolved['iRange']['source']['section'], 'XComGame.X2Ability_Fixture')

    def test_ambiguous_cross_family_class_reference_remains_unresolved(self):
        self.catalog['weapon_definitions'][0]['properties']['iRange'] = {
            'reference': "class'X2Ability_Fixture'.default.MELEE_RANGE"}
        self.write('GameData_SoldierSkills', '[XComGame.X2Ability_Fixture]\nMELEE_RANGE=3\n')
        self.write('GameCore', '[XComGame.X2Ability_Fixture]\nMELEE_RANGE=9\n')
        weapon = self.enrich()['weapon_definitions'][0]['config_values']
        self.assertNotIn('iRange', weapon['resolved_properties'])
        self.assertEqual(weapon['unresolved_references']['iRange'],
                         "class'X2Ability_Fixture'.default.MELEE_RANGE")

    def test_unqualified_reference_does_not_search_other_config_family(self):
        self.write('GameData_SoldierSkills', '[XComGame.X2Item_Fixture]\nDAMAGE=(Damage=9)\n')
        weapon = self.enrich()['weapon_definitions'][0]['config_values']
        self.assertNotIn('BaseDamage', weapon['resolved_properties'])
        self.assertEqual(weapon['unresolved_references']['BaseDamage'], 'default.DAMAGE')

    def test_sdk_defaults_and_generated_files_never_override_game(self):
        self.write('GameData_CharacterStats', '[Enemy X2CharacterTemplate]\nCharacterBaseStats[eStat_HP]=4\n')
        self.write('GameData_CharacterStats', '[Enemy X2CharacterTemplate]\nCharacterBaseStats[eStat_HP]=99\n', self.sdk)
        self.write('GameData_CharacterStats', '[Enemy X2CharacterTemplate]\nCharacterBaseStats[eStat_HP]=88\n', self.sdk, True)
        result = self.enrich(sdk=True)
        self.assertEqual(result['units'][0]['config_values']['stats']['base']['eStat_HP']['value'], 4)
        file_audit = result['configuration_audit']['default_files'][0]
        self.assertFalse(file_audit['identical'])
        self.assertEqual(result['configuration_audit']['generated_configuration']['sdk_files'], 1)
        self.assertFalse(result['configuration_audit']['generated_configuration']['used_as_overrides'])

    def test_ai_convention_is_separate_from_explicit_root(self):
        self.write('AI', '[XComGame.X2AIBTBehaviorTree]\n'
                   'Behaviors=(BehaviorName="EnemyGroup::CharacterRoot",NodeType=Selector,Child[0]=TryMove)\n'
                   'Behaviors=(BehaviorName=ExplicitRoot,NodeType=Sequence,Child[0]=TryShot)\n')
        self.catalog['units'].append({'template_name': 'Other', 'properties': {'strBehaviorTree': {'value': 'ExplicitRoot'}}})
        inferred, explicit = [unit['config_values']['ai_root'] for unit in self.enrich()['units']]
        self.assertEqual(inferred['status'], 'indexed_by_convention')
        self.assertEqual(inferred['children'], {'Child[0]': 'TryMove'})
        self.assertEqual(explicit['status'], 'present')
        self.assertEqual(explicit['node_type'], 'Sequence')

    def test_enrichment_does_not_mutate_source_catalog_or_expose_private_path(self):
        before = json.dumps(self.catalog, sort_keys=True)
        result = self.enrich(sdk=True)
        self.assertEqual(json.dumps(self.catalog, sort_keys=True), before)
        serialized = json.dumps(result)
        self.assertNotIn(str(self.directory), serialized)
        self.assertNotIn('raw_text', serialized)


if __name__ == '__main__':
    unittest.main()
