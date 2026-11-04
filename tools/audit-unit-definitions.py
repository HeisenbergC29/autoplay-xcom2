#!/usr/bin/env python3
"""Audit character factories in an installed WOTC SDK without executing it.

This is a source index, not an UnrealScript interpreter or a dump of effective
game stats. It follows explicit character-factory calls and literal/default
parameters; conditional declarations and unresolved configuration stay marked.
Only derived identifiers, values and source locations are written to JSON.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re


FUNCTION = re.compile(r'\bfunction\s+(?:(?P<return>[\w<>]+)\s+)?(?P<name>\w+)\s*\(', re.I)
CALL = re.compile(r"(?:(?:class\s*'(?P<class>\w+)'\s*\.\s*static\s*\.)|(?<![\w.]))(?P<name>\w+)\s*\(", re.I)
PROPERTY = re.compile(r'\b\w+\.(?P<field>b\w+|DefaultLoadout|RequiredLoadout|CharacterGroupName|strBehaviorTree|strScamperBT|UnitSize|UnitHeight|CharacterBaseStats\s*\[\s*\w+\s*\])\s*=\s*(?P<value>[^;]+);', re.I)
ARRAY = re.compile(r'\b\w+\.(?P<field>Abilities|ImmuneTypes)\s*(?:\.\s*(?P<operation>AddItem|RemoveItem)\s*\(|\.\s*(?P<clear>Length)\s*=\s*0\s*;)', re.I)
WEAPON_PROPERTIES = re.compile(r'\b\w+\.(?P<field>WeaponCat|WeaponTech|BaseDamage|RangeAccuracy|iRange|iRadius|iClipSize|iTypicalActionCost|Aim|CritChance|InfiniteAmmo)\s*=\s*(?P<value>[^;]+);', re.I)


def strip_comments(text: str) -> str:
    """Preserve offsets, newlines and quoted text, including img:/// strings."""
    out = list(text)
    index, quote = 0, None
    while index < len(text):
        char = text[index]
        if quote:
            if char == '\\':
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in "\"'":
            quote = char
            index += 1
            continue
        end = None
        if text.startswith('//', index):
            end = text.find('\n', index)
            end = len(text) if end < 0 else end
        elif text.startswith('/*', index):
            ending = text.find('*/', index + 2)
            end = len(text) if ending < 0 else ending + 2
        if end is not None:
            for position in range(index, end):
                if out[position] not in '\r\n':
                    out[position] = ' '
            index = end
        else:
            index += 1
    return ''.join(out)


def syntax_mask(text: str) -> str:
    """Blank literals as well as comments for structural delimiter searches."""
    clean = strip_comments(text)
    out = list(clean)
    index = 0
    while index < len(clean):
        if clean[index] not in "\"'":
            index += 1
            continue
        quote = clean[index]
        out[index] = ' '
        index += 1
        while index < len(clean):
            char = clean[index]
            if char not in '\r\n':
                out[index] = ' '
            index += 1
            if char == '\\' and index < len(clean):
                out[index] = ' '
                index += 1
            elif char == quote:
                break
    return ''.join(out)


def matching(mask: str, start: int, opening='(', closing=')') -> int:
    depth = 0
    for index in range(start, len(mask)):
        depth += (mask[index] == opening) - (mask[index] == closing)
        if depth == 0:
            return index
    raise ValueError('Unclosed source delimiter.')


def split_args(text: str) -> list[str]:
    mask = syntax_mask(text)
    parts, start, depth = [], 0, 0
    for index, char in enumerate(mask):
        depth += char in '([{'
        depth -= char in ')]}'
        if char == ',' and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    if text[start:].strip():
        parts.append(text[start:].strip())
    return parts


def source_at(function: dict, position=0) -> dict:
    return {'file': function['file'],
            'line': function['body_line'] + function['body'][:position].count('\n'),
            'function': function['name']}


def functions_from_source(text: str, filename: str) -> list[dict]:
    clean, mask = strip_comments(text), syntax_mask(text)
    class_match = re.search(r'\bclass\s+(\w+)\s+extends\s+(\w+)', mask, re.I)
    if not class_match:
        return []
    config = re.search(r'\bconfig\s*\(\s*(\w+)\s*\)', mask[:mask.find(';') + 1], re.I)
    functions = []
    position = 0
    while (match := FUNCTION.search(mask, position)):
        close = matching(mask, match.end() - 1)
        opening = close + 1
        while opening < len(mask) and mask[opening].isspace():
            opening += 1
        if opening >= len(mask) or mask[opening] != '{':
            position = close + 1
            continue
        end = matching(mask, opening, '{', '}')
        parameters = []
        for argument in split_args(clean[match.end():close]):
            declaration, _, default = argument.partition('=')
            words = declaration.split()
            if not words:
                continue
            parameters.append({'name': words[-1], 'default': default.strip() or None,
                               'optional': any(word.lower() == 'optional' for word in words),
                               'type': words[-2] if len(words) > 1 else '',
                               'out': any(word.lower() == 'out' for word in words)})
        functions.append({'name': match['name'], 'return': match['return'] or '',
                          'class': class_match[1], 'parent': class_match[2],
                          'config': config[1] if config else None,
                          'file': filename, 'line': clean[:match.start()].count('\n') + 1,
                          'body_line': clean[:opening + 1].count('\n') + 1,
                          'parameters': parameters, 'body': clean[opening + 1:end]})
        position = end + 1
    return functions


def literal(expression: str, environment: dict):
    expression = expression.strip()
    if not expression:
        return None
    pieces = split_operator(expression, '$')
    if len(pieces) > 1:
        values = [literal(piece, environment) for piece in pieces]
        return ''.join(str(value) for value in values) if all(value is not None for value in values) else None
    if expression.lower() in environment:
        return environment[expression.lower()]
    if re.fullmatch(r"'[^']*'|\"[^\"]*\"", expression):
        return expression[1:-1]
    if expression.lower() in {'true', 'false'}:
        return expression.lower() == 'true'
    if re.fullmatch(r'-?\d+', expression):
        return int(expression)
    if re.fullmatch(r'-?\d+\.\d+f?', expression, re.I):
        return float(expression.rstrip('fF'))
    cast = re.fullmatch(r'(?:name|string|int|float|bool)\s*\((.*)\)', expression, re.I | re.S)
    if cast:
        return literal(cast[1], environment)
    return None


def split_operator(text: str, operator: str) -> list[str]:
    mask, parts, depth, start = syntax_mask(text), [], 0, 0
    for index, char in enumerate(mask):
        depth += char in '([{'
        depth -= char in ')]}'
        if char == operator and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return parts


def value_fact(expression: str, environment: dict, function: dict, position: int) -> dict:
    value = literal(expression, environment)
    fact = {'value': value, 'source': source_at(function, position)}
    if value is None:
        fact['unresolved'] = True
        # Retain only a short reference/expression, never a function body.
        fact['reference'] = re.sub(r'\s+', ' ', expression.strip())[:180]
    return fact


def is_conditional(body: str, position: int) -> bool:
    before = syntax_mask(body[:position])
    if before.count('{') > before.count('}'):
        return True
    boundary = max(before.rfind(';'), before.rfind('{'), before.rfind('}'))
    return bool(re.search(r'\b(?:if|else|for|foreach|while|switch)\b', before[boundary + 1:]))


def calls_in(body: str):
    """Return source positions and balanced arguments for explicit calls."""
    clean, mask = strip_comments(body), syntax_mask(body)
    for match in CALL.finditer(clean):
        # Opening parenthesis must be code, not text inside a literal.
        if mask[match.end() - 1] != '(':
            continue
        close = matching(mask, match.end() - 1)
        yield match.start(), match['class'], match['name'], split_args(clean[match.end():close])


def definition_indexes(functions: list[dict]) -> tuple[dict, list]:
    abilities, weapons = {}, []
    for function in functions:
        for position, _, called, arguments in calls_in(function['body']):
            if called.upper() == 'CREATE_X2ABILITY_TEMPLATE' and len(arguments) >= 2:
                name = literal(arguments[1], {})
                if isinstance(name, str):
                    abilities.setdefault(name.casefold(), []).append(source_at(function, position))
            if called.upper() != 'CREATE_X2TEMPLATE' or len(arguments) < 3:
                continue
            if not re.fullmatch(r"class\s*'X2WeaponTemplate'", arguments[0], re.I):
                continue
            name = literal(arguments[2], {})
            if not isinstance(name, str):
                continue
            properties, conditional = {}, []
            for match in WEAPON_PROPERTIES.finditer(function['body']):
                fact = value_fact(match['value'], {}, function, match.start())
                if is_conditional(function['body'], match.start()):
                    conditional.append({'property': match['field'], **fact})
                else:
                    properties[match['field']] = fact
            names = []
            for match in re.finditer(r'\b\w+\.Abilities\.AddItem\s*\(', function['body'], re.I):
                close = matching(syntax_mask(function['body']), match.end() - 1)
                ability = literal(function['body'][match.end():close], {})
                if isinstance(ability, str):
                    names.append(ability)
            weapons.append({'name': name, 'source': source_at(function, position),
                            'properties': properties, 'conditional_properties': conditional,
                            'ability_references': sorted(set(names)), 'config': function['config'],
                            'effective_numeric_values_complete': False})
    return abilities, sorted(weapons, key=lambda row: (row['name'].casefold(), row['source']['file'], row['source']['line']))


def audit_sources(sources: dict[str, str]) -> dict:
    """Build derived metadata. Relative source names are supplied by caller."""
    functions = [function for filename, text in sorted(sources.items())
                 for function in functions_from_source(text, filename)]
    parents = {}
    for text in sources.values():
        header = re.search(r'\bclass\s+(\w+)\s+extends\s+(\w+)', syntax_mask(text), re.I)
        if header:
            parents[header[1].casefold()] = header[2].casefold()

    def is_character_template(type_name: str) -> bool:
        type_name, seen = type_name.casefold(), set()
        while type_name and type_name not in seen:
            if type_name == 'x2charactertemplate':
                return True
            seen.add(type_name)
            type_name = parents.get(type_name, '')
        return False

    providers = {function['class'] for function in functions
                 if function['parent'].casefold() == 'x2character' and function['name'].casefold() == 'createtemplates'}
    factories = {(function['class'].casefold(), function['name'].casefold()): function
                 for function in functions if function['class'] in providers}
    ability_definitions, weapon_definitions = definition_indexes(functions)

    def resolve(function: dict, arguments: list[str], inherited_environment: dict,
                result: dict, stack: tuple, inherited_conditional=False):
        identity = (function['class'].casefold(), function['name'].casefold())
        if identity in stack or len(stack) >= 20:
            result['unresolved'].append({'reason': 'recursive_factory', 'source': source_at(function)})
            return
        environment = {}
        for index, parameter in enumerate(function['parameters']):
            expression = arguments[index] if index < len(arguments) else parameter['default']
            if expression is None and parameter['optional']:
                expression = {'name': "''", 'string': '""', 'bool': 'false', 'int': '0', 'float': '0.0'}.get(parameter['type'].lower(), '')
            environment[parameter['name'].lower()] = literal(expression or '', inherited_environment)
        result['factory_chain'].append({'file': function['file'], 'line': function['line'], 'function': function['name']})
        body, events = function['body'], []
        for position, class_name, called, args in calls_in(body):
            if called.upper() == 'CREATE_X2CHARACTER_TEMPLATE' and len(args) >= 2:
                events.append((position, 'name', args[1]))
                continue
            if called.upper() == 'CREATE_X2TEMPLATE' and len(args) >= 3:
                template_type = re.fullmatch(r"class\s*'(?P<name>\w+)'", args[0], re.I)
                if template_type and is_character_template(template_type['name']):
                    events.append((position, 'name', args[2]))
                continue
            child = factories.get(((class_name or function['class']).casefold(), called.casefold()))
            if child and (is_character_template(child['return'])
                          or any(is_character_template(parameter['type']) for parameter in child['parameters'])):
                events.append((position, 'call', (child, args)))
        for match in PROPERTY.finditer(body):
            events.append((match.start(), 'property', match))
        for match in ARRAY.finditer(body):
            args = []
            if match['operation']:
                close = matching(syntax_mask(body), match.end() - 1)
                args = split_args(body[match.end():close])
            events.append((match.start(), 'array', (match, args)))
        for position, kind, event in sorted(events, key=lambda value: value[0]):
            conditional = inherited_conditional or is_conditional(body, position)
            if kind == 'call':
                resolve(event[0], event[1], environment, result, stack + (identity,), conditional)
            elif kind == 'name':
                name = literal(event, environment)
                if isinstance(name, str) and name:
                    result['template_names'].add(name)
                else:
                    result['unresolved'].append({'reason': 'template_name', **value_fact(event, environment, function, position)})
            elif kind == 'property':
                field = re.sub(r'\s+', '', event['field'])
                fact = value_fact(event['value'], environment, function, position)
                if conditional:
                    result['conditional_properties'].append({'property': field, **fact})
                else:
                    result['properties'][field] = fact
            else:
                match, args = event
                field = 'abilities' if match['field'].lower() == 'abilities' else 'immunities'
                if match['clear']:
                    if not conditional:
                        result[field].clear()
                    else:
                        result['unresolved'].append({'reason': 'conditional_array_clear', 'field': field, 'source': source_at(function, position)})
                    continue
                expression = args[0] if args else ''
                fact = value_fact(expression, environment, function, position)
                if conditional:
                    fact['conditional'] = True
                if match['operation'].lower() == 'removeitem' and not conditional:
                    result[field] = [entry for entry in result[field] if entry['value'] != fact['value']]
                else:
                    result[field].append(fact)

    units, provider_rows = [], []
    for function in functions:
        if function['class'] not in providers or function['name'].casefold() != 'createtemplates':
            continue
        registrations = 0
        for match in re.finditer(r'\bTemplates\.AddItem\s*\(', function['body'], re.I):
            close = matching(syntax_mask(function['body']), match.end() - 1)
            expression = function['body'][match.end():close].strip()
            calls = list(calls_in(expression))
            result = {'template_names': set(), 'factory_chain': [], 'properties': {},
                      'conditional_properties': [], 'abilities': [], 'immunities': [], 'unresolved': []}
            called = calls[0] if calls else None
            child = factories.get((((called[1] or function['class']).casefold()), called[2].casefold())) if called else None
            if child:
                resolve(child, called[3], {}, result, ())
            else:
                result['unresolved'].append({'reason': 'registration_factory', 'reference': expression[:180]})
            names = sorted(result.pop('template_names'), key=str.casefold)
            result.update({'template_name': names[0] if len(names) == 1 else None,
                           'possible_template_names': names if len(names) != 1 else [],
                           'provider': function['class'], 'registration_source': source_at(function, match.start()),
                           'factory': called[2] if called else None})
            if not names:
                result['unresolved'].append({'reason': 'no_resolved_template_name'})
            normalized_abilities = []
            for fact in result['abilities']:
                fact = deepcopy(fact)
                fact['name'] = fact.pop('value')
                fact['definition_sources'] = ability_definitions.get(str(fact['name']).casefold(), [])
                if not fact['definition_sources']:
                    fact['definition_unresolved'] = True
                normalized_abilities.append(fact)
            result['abilities'] = normalized_abilities
            loadout = result['properties'].get('DefaultLoadout')
            result['loadout'] = {'name': loadout['value'] if loadout else None,
                                 'configuration_resolved': False,
                                 'config': 'GameData / X2ItemTemplateManager.Loadouts'}
            if loadout:
                result['loadout']['source'] = loadout['source']
            result['stat_configuration'] = {'config': 'GameData_CharacterStats',
                                             'template_section': result['template_name'],
                                             'numeric_values_complete': False,
                                             'randomized_stats_may_override': True}
            units.append(result)
            registrations += 1
        provider_rows.append({'class': function['class'], 'file': function['file'], 'registrations': registrations})
    units.sort(key=lambda row: ((row['template_name'] or '').casefold(), row['registration_source']['file'], row['registration_source']['line']))
    resolved = sum(row['template_name'] is not None for row in units)
    return {'format_version': 1, 'kind': 'sdk_source_definition_audit',
            'coverage': {'provider_count': len(providers), 'registration_count': len(units),
                         'factory_count': sum(is_character_template(function['return']) for function in functions if function['class'] in providers),
                         'resolved_registration_count': resolved,
                         'unique_template_count': len({row['template_name'].casefold() for row in units if row['template_name']}),
                         'unresolved_registration_count': len(units) - resolved},
            'providers': sorted(provider_rows, key=lambda row: row['file']),
            'units': units, 'weapon_definitions': weapon_definitions,
            'source_files': [{'file': filename, 'normalized_utf8_sha256': hashlib.sha256(text.replace('\r\n', '\n').encode()).hexdigest()} for filename, text in sorted(sources.items())],
            'limitations': [
                'Registration counts include soldiers, civilians, speakers, multiplayer and aliases; they are not enemy counts.',
                'Conditional source declarations are possible facts, not guaranteed effective template values.',
                'Difficulty variants, randomized stats, DLC/mod hooks and native changes are not executed.',
                'Config-backed stats, damage, loadout contents and AI behavior trees remain unresolved; explicit source overrides are listed separately.',
                'Only literal ability/weapon definition names are indexed; empty definition_sources do not prove that an ability is missing.',
                'The catalog is source metadata, not live hidden enemy state and not an input that reveals hidden contacts to the tactical planner.',
            ]}


def sdk_source_root(path: Path) -> Path:
    for candidate in (path / 'Development/SrcOrig', path / 'SrcOrig', path,
                      path / 'Development/Src', path / 'Src'):
        if (candidate / 'XComGame/Classes/X2CharacterTemplate.uc').is_file():
            return candidate
    raise ValueError('SDK path must contain XComGame/Classes/X2CharacterTemplate.uc (SrcOrig preferred).')


def build_catalog(sdk: Path) -> dict:
    root = sdk_source_root(sdk)
    sources = {}
    for path in sorted(root.rglob('*.uc')):
        if path.name.startswith(('X2Character', 'X2Ability', 'X2Item')) or 'CharacterTemplate' in path.stem:
            data = path.read_bytes()
            try:
                text = data.decode('utf-8-sig')
            except UnicodeDecodeError:
                # Some original SDK files use the Windows source-code page.
                # Preserve those characters instead of silently replacing them.
                text = data.decode('cp1252')
            sources[path.relative_to(root).as_posix()] = text
    return audit_sources(sources)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', required=True, type=Path)
    parser.add_argument('--json', required=True, type=Path, help='New output file; existing files are preserved.')
    args = parser.parse_args()
    if args.json.exists():
        parser.error('Output already exists; choose a new path to preserve the previous audit.')
    result = build_catalog(args.sdk)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    coverage = result['coverage']
    print(f"Audited {coverage['registration_count']} registrations in {coverage['provider_count']} providers; "
          f"{coverage['resolved_registration_count']} resolved names, {coverage['unique_template_count']} unique names.")
    print('Configuration and native/runtime overrides remain explicitly unresolved; no SDK source is bundled.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
