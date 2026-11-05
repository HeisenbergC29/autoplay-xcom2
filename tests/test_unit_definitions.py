"""Audit source facts and their limits without executing proprietary game code.

Small synthetic factories exercise parsing. Optional SDK contracts verify that
all registration calls are represented and observed enemies have definitions.
"""
import importlib.util
import json
import os
from pathlib import Path
import unittest

from test_ui_gating import CHECKS


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'unit_definition_audit', ROOT / 'tools/audit-unit-definitions.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def provider(registrations, factories, name='Fixture'):
    return f'''class {name} extends X2Character config(GameData_CharacterStats);
static function array<X2DataTemplate> CreateTemplates()
{{
    local array<X2DataTemplate> Templates;
    {registrations}
    return Templates;
}}
{factories}
'''


def named_units(catalog):
    return {entry['template_name']: entry for entry in catalog['units']
            if entry['template_name'] is not None}


class UnitDefinitionAuditTests(unittest.TestCase):
    def test_comment_lexer_preserves_strings_offsets_and_newlines(self):
        source = '''// discard me
class Fixture extends X2Character;
"img:///Portrait.Path"; 'Name//Part'; "escaped\\\"//inside";
/* block comment
   more comment */
'''
        clean = AUDIT.strip_comments(source)
        self.assertEqual(len(clean), len(source))
        self.assertEqual(clean.count('\n'), source.count('\n'))
        self.assertIn('"img:///Portrait.Path"', clean)
        self.assertIn("'Name//Part'", clean)
        self.assertIn('"escaped\\\"//inside"', clean)
        self.assertNotIn('discard me', clean)
        self.assertNotIn('block comment', clean)

    def test_literal_and_default_arguments_resolve_distinct_lost_names(self):
        source = provider(
            "Templates.AddItem(Build()); Templates.AddItem(Build('LostHP4', 'Tier2'));",
            '''static function X2CharacterTemplate Build(optional name DataName='Lost', optional name Loadout='Tier1')
{
    local X2CharacterTemplate Unit;
    `CREATE_X2CHARACTER_TEMPLATE(Unit, DataName);
    Unit.DefaultLoadout = Loadout;
    Unit.bIsMeleeOnly = true;
    return Unit;
}''')
        result = AUDIT.audit_sources({'Fixture/Classes/Characters.uc': source})
        units = named_units(result)
        self.assertEqual(set(units), {'Lost', 'LostHP4'})
        self.assertEqual(units['Lost']['loadout']['name'], 'Tier1')
        self.assertEqual(units['LostHP4']['loadout']['name'], 'Tier2')
        self.assertFalse(units['LostHP4']['loadout']['configuration_resolved'])
        self.assertIs(units['Lost']['properties']['bIsMeleeOnly']['value'], True)

    def test_image_uri_does_not_remove_a_speaker_registration(self):
        source = provider(
            '''Templates.AddItem(Speaker('Voice', "img:///Portrait.Path"));
    Templates.AddItem(Speaker('Second', "img:///Another.Path"));''',
            '''static function X2CharacterTemplate Speaker(name DataName, string Portrait)
{
    local X2CharacterTemplate Unit;
    `CREATE_X2CHARACTER_TEMPLATE(Unit, DataName);
    return Unit;
}''')
        result = AUDIT.audit_sources({'Fixture/Classes/Characters.uc': source})
        self.assertEqual(result['coverage']['registration_count'], 2)
        self.assertEqual(set(named_units(result)), {'Voice', 'Second'})

    def test_external_wrapper_inherits_facts_and_applies_later_overrides(self):
        base = provider('', '''static function X2CharacterTemplate Base(name DataName)
{
    local X2CharacterTemplate Unit;
    `CREATE_X2CHARACTER_TEMPLATE(Unit, DataName);
    Unit.bCanTakeCover = true;
    Unit.Abilities.AddItem('Basic');
    Unit.ImmuneTypes.AddItem('Fire');
    return Unit;
}''', 'BaseCharacters')
        wrapper = provider('Templates.AddItem(Build());', '''static function X2CharacterTemplate Build()
{
    local X2CharacterTemplate Unit;
    Unit = class'BaseCharacters'.static.Base('Wrapped');
    Unit.bCanTakeCover = false;
    Unit.Abilities.AddItem('Control');
    return Unit;
}''')
        unit = named_units(AUDIT.audit_sources({
            'Base/Classes/Characters.uc': base, 'Fixture/Classes/Characters.uc': wrapper}))['Wrapped']
        self.assertIs(unit['properties']['bCanTakeCover']['value'], False)
        self.assertEqual({a['name'] for a in unit['abilities']}, {'Basic', 'Control'})
        self.assertIn('Fire', [a['value'] for a in unit['immunities']])
        self.assertGreaterEqual(len(unit['factory_chain']), 2)
        self.assertEqual(unit['registration_source']['file'], 'Fixture/Classes/Characters.uc')
        self.assertGreater(unit['registration_source']['line'], 0)

    def test_void_out_parameter_factory_supplies_the_template_name(self):
        source = provider('Templates.AddItem(Build());', '''static function Fill(out X2CharacterTemplate Unit, name DataName)
{
    `CREATE_X2CHARACTER_TEMPLATE(Unit, DataName);
    Unit.bIsRobotic = true;
}
static function X2CharacterTemplate Build()
{
    local X2CharacterTemplate Unit;
    Fill(Unit, 'Turret');
    Unit.DefaultLoadout = 'Turret_Loadout';
    return Unit;
}''')
        unit = named_units(AUDIT.audit_sources({'Fixture/Classes/Characters.uc': source}))['Turret']
        self.assertIs(unit['properties']['bIsRobotic']['value'], True)
        self.assertEqual(unit['loadout']['name'], 'Turret_Loadout')

    def test_derived_character_macro_resolves_spark_and_wrapped_facts(self):
        source = provider('Templates.AddItem(Build());', """static function RobotTemplate Build()
{
    local RobotTemplate Unit;
    `CREATE_X2TEMPLATE(class'RobotTemplate', Unit, 'Spark');
    Unit.bIsRobotic = true;
    return Unit;
}""")
        result = AUDIT.audit_sources({
            'Fixture/Classes/Characters.uc': source,
            'Fixture/Classes/RobotTemplate.uc': 'class RobotTemplate extends X2CharacterTemplate;',
        })
        self.assertEqual(result['coverage']['factory_count'], 1)
        self.assertEqual(result['coverage']['resolved_registration_count'], 1)
        self.assertIs(named_units(result)['Spark']['properties']['bIsRobotic']['value'], True)

    def test_conditional_and_configuration_facts_do_not_become_certain_numbers(self):
        source = provider('Templates.AddItem(Build());', '''static function X2CharacterTemplate Build()
{
    local X2CharacterTemplate Unit;
    `CREATE_X2CHARACTER_TEMPLATE(Unit, 'UnknownStats');
    if (default.bFeature)
    {
        Unit.bIsRobotic = true;
    }
    Unit.CharacterBaseStats[eStat_HP] = default.UnknownHP;
    Unit.DefaultLoadout = default.UnknownLoadout;
    return Unit;
}''')
        unit = named_units(AUDIT.audit_sources({'Fixture/Classes/Characters.uc': source}))['UnknownStats']
        self.assertNotIn('bIsRobotic', unit['properties'])
        self.assertIn('bIsRobotic', json.dumps(unit['conditional_properties']))
        serialized = json.dumps(unit)
        self.assertIn('UnknownHP', serialized)
        self.assertIn('UnknownLoadout', serialized)
        self.assertIsNone(unit['loadout']['name'])
        self.assertFalse(unit['loadout']['configuration_resolved'])

    def test_unknown_factory_is_reported_and_registration_is_not_dropped(self):
        source = provider("Templates.AddItem(UnavailableFactory('Unknown'));", '')
        result = AUDIT.audit_sources({'Fixture/Classes/Characters.uc': source})
        self.assertEqual(result['coverage']['registration_count'], 1)
        self.assertEqual(result['coverage']['unresolved_registration_count'], 1)
        self.assertEqual(len(result['units']), 1)
        self.assertIsNone(result['units'][0]['template_name'])
        self.assertTrue(result['units'][0]['unresolved'])

    def test_ability_reference_links_to_its_declared_definition(self):
        character = provider('Templates.AddItem(Build());', '''static function X2CharacterTemplate Build()
{
    local X2CharacterTemplate Unit;
    `CREATE_X2CHARACTER_TEMPLATE(Unit, 'KnownAbility');
    Unit.Abilities.AddItem('Control');
    return Unit;
}''')
        ability = '''class AbilityFixture extends X2Ability;
static function X2AbilityTemplate BuildControl()
{
    local X2AbilityTemplate Template;
    `CREATE_X2ABILITY_TEMPLATE(Template, 'Control');
    return Template;
}'''
        sources = {'Fixture/Classes/Characters.uc': character, 'Fixture/Classes/Ability.uc': ability}
        result = AUDIT.audit_sources(sources)
        unit = named_units(result)['KnownAbility']
        definition = unit['abilities'][0]['definition_sources'][0]
        self.assertEqual(definition['file'], 'Fixture/Classes/Ability.uc')
        self.assertGreater(definition['line'], 0)
        self.assertEqual(result, AUDIT.audit_sources(dict(reversed(list(sources.items())))))
        self.assertNotIn('/workspace/', json.dumps(result))

    def test_source_defaults_preserve_literal_values_and_physical_provenance(self):
        source = '''class WeaponFixture extends X2Item config(GameCore);
var name Category;
var bool Enabled;
var int Count;
var float Rate;
var string Label;
var config int Configured;
defaultproperties
{
    // The braces and comment marker are literal string content.
    Category="img:///Category.}"
    Enabled=true
    Count=-2
    Rate=1.25f
    Label="quoted \\\"label\\\"";
    Configured=99
}
'''
        defaults = AUDIT.source_scalar_defaults({'Fixture/Classes/WeaponFixture.uc': source})['weaponfixture']
        self.assertEqual({key: fact['value'] for key, fact in defaults.items()},
                         {'category': 'img:///Category.}', 'enabled': True, 'count': -2,
                          'rate': 1.25, 'label': 'quoted "label"'})
        self.assertEqual(defaults['category']['source'],
                         {'file': 'Fixture/Classes/WeaponFixture.uc', 'line': 11,
                          'class': 'WeaponFixture', 'block': 'defaultproperties'})

    def test_source_defaults_skip_expressions_structs_arrays_and_nested_objects(self):
        source = '''class WeaponFixture extends X2Item;
var name Category;
var int Count;
var int Items[2];
defaultproperties
{
    Category="outer"
    Count=1+2
    Items[0]=4
    Details=(
        Category="struct"
    )
    Begin Object Class=Fixture Name=Nested
        Category="nested"
    End Object
}
'''
        defaults = AUDIT.source_scalar_defaults({'Fixture/Classes/WeaponFixture.uc': source})['weaponfixture']
        self.assertEqual({key: fact['value'] for key, fact in defaults.items()}, {'category': 'outer'})

    def test_weapon_source_default_links_explicit_class_without_guessing_inheritance(self):
        sources = {
            'Fixture/Classes/BaseFixture.uc': '''class BaseFixture extends X2Item;
var name Category;
defaultproperties
{
    Category="base"
}
''',
            'Fixture/Classes/ChildFixture.uc': '''class ChildFixture extends BaseFixture;
static function X2WeaponTemplate Build()
{
    local X2WeaponTemplate Template;
    `CREATE_X2TEMPLATE(class'X2WeaponTemplate', Template, 'ChildWeapon');
    Template.WeaponCat = default.Category;
    Template.WeaponTech = class'BaseFixture'.default.Category;
    return Template;
}
''',
        }
        result = AUDIT.audit_sources(sources)
        weapon = result['weapon_definitions'][0]
        self.assertTrue(weapon['properties']['WeaponCat']['unresolved'])
        self.assertEqual(weapon['source_defaults']['Category']['value'], 'base')
        self.assertEqual(weapon['source_defaults']['Category']['source']['class'], 'BaseFixture')
        only_inherited = sources['Fixture/Classes/ChildFixture.uc'].replace(
            "    Template.WeaponTech = class'BaseFixture'.default.Category;\n", '')
        sources['Fixture/Classes/ChildFixture.uc'] = only_inherited
        self.assertNotIn('source_defaults', AUDIT.audit_sources(sources)['weapon_definitions'][0])

    def test_duplicate_source_class_names_do_not_choose_a_default(self):
        sources = {
            'A/Classes/Fixture.uc': '''class Fixture extends X2Item;
var name Category;
defaultproperties
{
    Category="first"
}
''',
            'B/Classes/Fixture.uc': 'class Fixture extends X2Item;',
        }
        self.assertNotIn('fixture', AUDIT.source_scalar_defaults(sources))


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Unit definition audit contracts need SDK sources')
class UnitDefinitionSDKContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT']))
        cls.catalog = AUDIT.build_catalog(root)
        cls.units = named_units(cls.catalog)

    def test_every_source_registration_is_represented_without_calling_them_all_enemies(self):
        coverage = self.catalog['coverage']
        self.assertEqual(coverage['provider_count'], 5)
        self.assertEqual(coverage['registration_count'], 253)
        self.assertEqual(coverage['factory_count'], 171)
        self.assertEqual(len(self.catalog['units']), 253)
        self.assertEqual(coverage['resolved_registration_count'] + coverage['unresolved_registration_count'], 253)

    def test_all_observed_templates_and_official_expansion_examples_are_present(self):
        required = {'AdvCaptainM1', 'AdvPriestM3', 'AdvTrooperM1', 'BerserkerMP',
                    'Faceless', 'PsiZombie', 'PsiZombieHuman', 'Sectoid', 'Soldier', 'Viper',
                    'BerserkerQueen', 'ArchonKing', 'ViperKing', 'PsiZombieCivilian',
                    'SparkSoldier', 'LostTowersSpark'}
        self.assertFalse(required - self.units.keys())
        spectre = self.units['SpectreM1']
        self.assertIs(spectre['properties']['bIsRobotic']['value'], False)
        self.assertIs(spectre['properties']['bWeakAgainstTechLikeRobot']['value'], True)

    def test_medikit_category_is_already_declared_in_sdk_source_defaults(self):
        weapons = {weapon['name']: weapon for weapon in self.catalog['weapon_definitions']}
        for name in ('Medikit', 'NanoMedikit'):
            with self.subTest(item=name):
                fact = weapons[name]['source_defaults']['MedikitCat']
                self.assertEqual(fact['value'], 'medikit')
                self.assertEqual(fact['source']['file'], 'XComGame/Classes/X2Item_DefaultUtilityItems.uc')
                self.assertEqual(fact['source']['class'], 'X2Item_DefaultUtilityItems')
                self.assertEqual(fact['source']['block'], 'defaultproperties')

    def test_checked_in_metadata_is_reproducible_from_the_same_sdk(self):
        checked_in = json.loads((ROOT / 'data/unit-catalog.json').read_text())
        # Configuration snapshots enrich, rather than overwrite, source facts.
        checked_in.pop('configuration_audit', None)
        for unit in checked_in['units']:
            unit.pop('config_values', None)
        for weapon in checked_in['weapon_definitions']:
            weapon.pop('config_values', None)
        self.assertEqual(checked_in, self.catalog)


if __name__ == '__main__':
    unittest.main()
