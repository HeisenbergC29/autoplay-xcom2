"""Resolve bounded, source-linked facts from supplied WOTC Default INIs.

This is a configuration snapshot audit, not Unreal's native configuration
loader. It deliberately does not overlay SDK-generated XCom*.ini caches, load
mods/DLC, execute hooks, or invent values for missing sections.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import re


FAMILIES = (
    'GameData_CharacterStats', 'GameData_WeaponData', 'GameData_SoldierSkills',
    'GameData', 'GameCore', 'AI', 'WeaponTuning',
)


def strip_inline_comment(text: str) -> str:
    quote, index = None, 0
    while index < len(text):
        char = text[index]
        if quote:
            if char == '\\':
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in '\"\'':
            quote = char
        elif char == ';':
            return text[:index]
        index += 1
    return text


def split_top(text: str, delimiter=',') -> list[str]:
    """Split outside quotes and balanced (), [] and {} delimiters."""
    parts, quote, depth, start, index = [], None, 0, 0, 0
    while index < len(text):
        char = text[index]
        if quote:
            if char == '\\':
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in '\"\'':
            quote = char
        elif char in '([{':
            depth += 1
        elif char in ')]}':
            depth -= 1
        elif char == delimiter and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
        index += 1
    parts.append(text[start:].strip())
    return parts


def parse_value(text: str):
    """Parse literal INI scalars/structs/arrays; leave symbols as strings."""
    text = text.strip()
    if len(text) >= 2 and text[0] in '\"\'' and text[-1] == text[0]:
        # INI strings are not Python expressions. Only decode escaped quotes.
        return text[1:-1].replace('\\' + text[0], text[0])
    if text.lower() in ('true', 'false'):
        return text.lower() == 'true'
    if re.fullmatch(r'[+-]?\d+', text):
        return int(text)
    if re.fullmatch(r'[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[fF]?', text):
        return float(text.rstrip('fF'))
    if text.startswith('(') and text.endswith(')'):
        parts = split_top(text[1:-1])
        if parts == ['']:
            return []
        pairs = [split_top(part, '=') for part in parts]
        if all(len(pair) == 2 for pair in pairs):
            # Preserve repeated struct fields instead of silently discarding one.
            result = {}
            duplicates = set()
            for key, raw in pairs:
                value = parse_value(raw)
                if key in result:
                    if key not in duplicates:
                        result[key] = [result[key]]
                        duplicates.add(key)
                    result[key].append(value)
                else:
                    result[key] = value
            return result
        return [parse_value(part) for part in parts]
    return text


class IniDocument:
    """Ordered entries with Unreal array operators and physical line numbers.

    Bare duplicate keys remain duplicate entries. Callers choose scalar-last or
    array-first semantics according to the property's native declaration.
    """
    def __init__(self, text: str, filename: str, dataset='game_defaults'):
        self.filename = filename
        self.dataset = dataset
        self.sections = {}
        section, pending, first_line = None, '', 0
        logical = []
        for line_number, physical in enumerate(text.splitlines(), 1):
            line = strip_inline_comment(physical).strip()
            if not pending and (not line or line.startswith('//')):
                continue
            if not pending:
                first_line = line_number
            continued = line.endswith('\\')
            if continued:
                line = line.rstrip('\\').rstrip()
            pending += (' ' if pending else '') + line
            if not continued:
                logical.append((first_line, pending))
                pending = ''
        if pending:
            logical.append((first_line, pending))
        for line_number, line in logical:
            if line.startswith('[') and line.endswith(']'):
                section = line[1:-1].strip()
                self.sections.setdefault(section, [])
            elif section is not None and '=' in line:
                key, raw = line.split('=', 1)
                key = key.strip()
                operation = key[0] if key and key[0] in '+.-!' else ''
                if operation:
                    key = key[1:].strip()
                self.sections[section].append({
                    'key': key, 'operation': operation,
                    'value': parse_value(raw), 'line': line_number,
                })

    @classmethod
    def read(cls, path: Path, dataset='game_defaults'):
        data = path.read_bytes()
        if data.startswith((b'\xff\xfe', b'\xfe\xff')):
            text = data.decode('utf-16')
        else:
            try:
                text = data.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = data.decode('cp1252')
        return cls(text, path.name, dataset)

    def section_name(self, requested: str):
        return next((name for name in self.sections if name.casefold() == requested.casefold()), None)

    def entries(self, section: str, key: str | None = None) -> list[dict]:
        actual = self.section_name(section)
        result = []
        for entry in self.sections.get(actual, []):
            if key is not None and entry['key'].casefold() != key.casefold():
                continue
            same_key = lambda item: item['key'].casefold() == entry['key'].casefold()
            same_value = lambda item: same_key(item) and item['value'] == entry['value']
            operation = entry['operation']
            if operation == '!':
                result = [item for item in result if not same_key(item)]
            elif operation == '-':
                result = [item for item in result if not same_value(item)]
            elif operation != '+' or not any(same_value(item) for item in result):
                result.append(entry)
        return result

    def source(self, section: str, entry: dict) -> dict:
        return {'dataset': self.dataset, 'file': self.filename,
                'section': self.section_name(section) or section,
                'key': entry['key'], 'line': entry['line']}

    def fact(self, section: str, entry: dict) -> dict:
        return {'value': deepcopy(entry['value']), 'source': self.source(section, entry)}


def _config_dir(path: Path) -> Path:
    path = Path(path)
    if not path.is_dir():
        raise ValueError(f'Configuration directory does not exist: {path}')
    return path / 'Config' if (path / 'Config').is_dir() else path


def _documents(directory: Path) -> dict[str, IniDocument]:
    # The two supplied archives have root Defaults. Nested SDK localization or
    # DLC directories have no declared load order and must not be merged here.
    return {family: IniDocument.read(directory / f'Default{family}.ini')
            for family in FAMILIES if (directory / f'Default{family}.ini').is_file()}


def _stats(unit: dict, document: IniDocument | None) -> dict:
    name = unit.get('template_name')
    if not name:
        return {'status': 'not_declared', 'base': {}, 'difficulty': {},
                'randomized_base_stats': [], 'effective_values_complete': False}
    section = f'{name} X2CharacterTemplate'
    if document is None:
        return {'status': 'not_present', 'base': {}, 'difficulty': {},
                'randomized_base_stats': [], 'effective_values_complete': False}

    def values(section_name):
        result = {}
        for entry in document.entries(section_name):
            match = re.fullmatch(r'CharacterBaseStats\[(\w+)\]', entry['key'], re.I)
            if match:
                result[match[1]] = document.fact(section_name, entry)
        return result

    base = values(section)
    difficulties = {}
    any_difficulty = False
    for difficulty in range(4):
        variant = f'{name}_Diff_{difficulty} X2CharacterTemplate'
        present = document.section_name(variant) is not None
        any_difficulty |= present
        overrides = values(variant)
        merged = {key: fact['value'] for key, fact in base.items()}
        merged.update({key: fact['value'] for key, fact in overrides.items()})
        difficulties[str(difficulty)] = {
            'section_present': present, 'overrides': overrides, 'values': merged,
        }
    randomized = [document.fact(section, entry)
                  for entry in document.entries(section, 'RandomizedBaseStats')]
    status = ('present' if document.section_name(section) else
              'partial' if any_difficulty else 'not_present')
    return {'status': status, 'base': base, 'difficulty': difficulties,
            'randomized_base_stats': randomized, 'effective_values_complete': False}


def _loadout(unit: dict, document: IniDocument | None) -> dict:
    declaration = unit.get('loadout', {})
    name = declaration.get('name')
    if name is None:
        return {'status': 'not_declared'}
    if name == '':
        return {'status': 'explicit_empty', 'name': name, 'items': []}
    result = {'status': 'not_present', 'name': name}
    if document is None:
        return result
    section = 'XComGame.X2ItemTemplateManager'
    matches = [entry for entry in document.entries(section, 'Loadouts')
               if isinstance(entry['value'], dict)
               and str(entry['value'].get('LoadoutName', '')).casefold() == str(name).casefold()]
    if not matches:
        return result
    # XComGameState_Unit.ApplyInventoryLoadout breaks after the FIRST match.
    selected = matches[0]
    items = []
    for key, value in selected['value'].items():
        index = re.fullmatch(r'Items\[(\d+)\]', key, re.I)
        if index and isinstance(value, dict):
            items.append({'index': int(index[1]), 'item': value.get('Item'),
                          'attributes': deepcopy(value),
                          'source': document.source(section, selected)})
    items.sort(key=lambda item: item['index'])
    result.update({'status': 'present', 'items': items,
                   'matching_definitions': len(matches), 'selection': 'first_matching_definition',
                   'source': document.source(section, selected)})
    return result


def _ai(unit: dict, document: IniDocument | None) -> dict:
    properties = unit.get('properties', {})
    explicit = properties.get('strBehaviorTree', {}).get('value')
    group = properties.get('CharacterGroupName', {}).get('value')
    name = explicit or (str(group) + '::CharacterRoot' if group else None)
    result = {'status': 'not_present', 'root_name': name,
              'name_basis': 'source_property' if explicit else 'character_group_convention'}
    if not name or document is None:
        return result
    section = 'XComGame.X2AIBTBehaviorTree'
    matches = [entry for entry in document.entries(section, 'Behaviors')
               if isinstance(entry['value'], dict)
               and str(entry['value'].get('BehaviorName', '')).casefold() == name.casefold()]
    if matches:
        selected = matches[0]
        value = selected['value']
        result.update({'status': 'present' if explicit else 'indexed_by_convention',
                       'node_type': value.get('NodeType'),
                       'children': {key: val for key, val in value.items()
                                    if re.fullmatch(r'Child\[\d+\]', key, re.I)},
                       'matching_definitions': len(matches),
                       'source': document.source(section, selected)})
    return result


def _weapon(weapon: dict, documents: dict[str, IniDocument]) -> dict:
    document = documents.get(weapon.get('config'))
    resolved, unresolved = {}, {}
    for field, declaration in weapon.get('properties', {}).items():
        reference = declaration.get('reference')
        if not reference:
            continue
        match = re.fullmatch(r"(?:(?:class\s*'(?P<class>\w+)'\s*\.)?)default\.(?P<symbol>\w+)", reference, re.I)
        if not match:
            unresolved[field] = reference
            continue
        owner = match['class'] or Path(declaration.get('source', weapon['source'])['file']).stem
        # An explicitly qualified reference can name an ability class configured
        # in SoldierSkills rather than the weapon's own config family. Search
        # only the selected Default snapshots, and never guess among duplicates.
        candidates = [(candidate, section)
                      for candidate in (documents.values() if match['class'] else
                                        [document] if document is not None else [])
                      for section in candidate.sections
                      if section.rsplit('.', 1)[-1].casefold() == owner.casefold()]
        if len(candidates) != 1:
            unresolved[field] = reference
            continue
        target_document, section = candidates[0]
        entries = target_document.entries(section, match['symbol'])
        if entries:
            resolved[field] = target_document.fact(section, entries[-1])
        else:
            indexed = []
            for entry in target_document.entries(section):
                index = re.fullmatch(re.escape(match['symbol']) + r'\[(\d+)\]', entry['key'], re.I)
                if index:
                    indexed.append({'index': int(index[1]), **target_document.fact(section, entry)})
            if indexed:
                # Explicit indexes only: absent indexes are unknown, not zero.
                by_index = {entry['index']: entry for entry in indexed}
                resolved[field] = {'indexed_values': [by_index[index] for index in sorted(by_index)]}
            else:
                unresolved[field] = reference
    return {'resolved_properties': resolved, 'unresolved_references': unresolved,
            'effective_values_complete': False}


def _file_record(path: Path) -> dict:
    if not path.is_file():
        return {'present': False}
    data = path.read_bytes()
    return {'present': True, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def enrich_catalog(catalog: dict, game_config: Path, sdk_config: Path | None = None) -> dict:
    """Return a deep copy enriched with the supplied game Defaults snapshot."""
    game_dir = _config_dir(game_config)
    sdk_dir = _config_dir(sdk_config) if sdk_config is not None else None
    documents = _documents(game_dir)
    result = deepcopy(catalog)
    file_records = []
    for family in FAMILIES:
        name = f'Default{family}.ini'
        game = _file_record(game_dir / name)
        record = {'file': name, 'game': game}
        if sdk_dir is not None:
            sdk = _file_record(sdk_dir / name)
            record['sdk'] = sdk
            record['identical'] = (game['sha256'] == sdk['sha256']
                                   if game['present'] and sdk['present'] else None)
        file_records.append(record)
    for unit in result.get('units', []):
        unit['config_values'] = {
            'stats': _stats(unit, documents.get('GameData_CharacterStats')),
            'loadout': _loadout(unit, documents.get('GameData')),
            'ai_root': _ai(unit, documents.get('AI')),
        }
    for weapon in result.get('weapon_definitions', []):
        weapon['config_values'] = _weapon(weapon, documents)
    generated = {'used_as_overrides': False}
    if sdk_dir is not None:
        sdk_names = {path.name for path in sdk_dir.glob('XCom*.ini') if path.is_file()}
        game_names = {path.name for path in game_dir.glob('XCom*.ini') if path.is_file()}
        common = sorted(sdk_names & game_names)
        generated.update({'sdk_files': len(sdk_names), 'game_files': len(game_names),
                          'common_files': len(common),
                          'different_common_files': sum((sdk_dir / name).read_bytes() !=
                                                        (game_dir / name).read_bytes()
                                                        for name in common)})
    result['configuration_audit'] = {
        'format_version': 1, 'primary_dataset': 'game_defaults',
        'default_files': file_records, 'generated_configuration': generated,
        'coverage': {
            'units_with_base_stats_section': sum(unit['config_values']['stats']['status'] == 'present'
                                                 for unit in result.get('units', [])),
            'units_with_resolved_loadout': sum(unit['config_values']['loadout']['status'] == 'present'
                                               for unit in result.get('units', [])),
            'units_with_explicit_ai_root': sum(unit['config_values']['ai_root']['status'] == 'present'
                                               for unit in result.get('units', [])),
            'units_with_ai_root_index': sum(unit['config_values']['ai_root']['status'] in
                                           ('present', 'indexed_by_convention')
                                           for unit in result.get('units', [])),
            'weapon_properties_resolved': sum(len(weapon['config_values']['resolved_properties'])
                                               for weapon in result.get('weapon_definitions', [])),
            'weapon_references_unresolved': sum(len(weapon['config_values']['unresolved_references'])
                                                for weapon in result.get('weapon_definitions', [])),
        },
        'limitations': [
            'Values are from the supplied game Default INIs, not the effective runtime/mod/DLC load order.',
            'SDK Defaults corroborate files only; SDK-generated XCom INIs never override game values.',
            'Difficulty values inherit known base entries and apply explicit partial difficulty overrides.',
            'Missing sections, keys and array indexes are unknown; explicit zero remains zero.',
            'Native class defaults, randomized values, source assignments and hooks may change runtime stats.',
            'Legacy or unsupported enum keys are retained as config declarations, not certified native stat slots.',
            'AI root children are an index, not an execution trace or prediction of private enemy intent.',
        ],
    }
    return result
