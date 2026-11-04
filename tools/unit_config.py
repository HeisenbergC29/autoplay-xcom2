"""Resolve bounded, source-linked facts from supplied WOTC Default INIs.

This is a configuration snapshot audit, not Unreal's native configuration
loader. It composes explicitly supplied game DLC snapshots, but does not overlay
SDK-generated caches, discover a native load order, execute hooks, or invent
values for missing sections.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import re
from types import MappingProxyType


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
        self._entry_cache = None
        self._section_names = None
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
        if self._section_names is not None:
            return self._section_names.get(requested.casefold())
        return next((name for name in self.sections if name.casefold() == requested.casefold()), None)

    def freeze(self):
        """Freeze section topology and cache reads after composition is complete."""
        self._section_names = {name.casefold(): name for name in self.sections}
        self.sections = MappingProxyType({name: tuple(entries) for name, entries in self.sections.items()})
        self._entry_cache = {}
        return self

    def entries(self, section: str, key: str | None = None) -> list[dict]:
        cache_key = (section.casefold(), key.casefold() if key is not None else None)
        if self._entry_cache is not None and cache_key in self._entry_cache:
            return list(self._entry_cache[cache_key])
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
        if self._entry_cache is not None:
            self._entry_cache[cache_key] = tuple(result)
        return result

    def source(self, section: str, entry: dict) -> dict:
        if '_source' in entry:
            return deepcopy(entry['_source'])
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


def _dlc_documents(directory: Path, label: str) -> dict[str, IniDocument]:
    """Read only the explicitly identified game DLC's seven supported families."""
    documents = {}
    for family in FAMILIES:
        paths = [directory / f'{prefix}{family}.ini' for prefix in ('XCom', 'Default')]
        present = [path for path in paths if path.is_file()]
        if len(present) > 1:
            raise ValueError(f'Ambiguous DLC configuration family: {label}/{family}')
        if present:
            document = IniDocument.read(present[0], f'game_dlc:{label}')
            document.filename = f'{label}/Config/{present[0].name}'
            documents[family] = document
    return documents


def _compose_documents(base: dict[str, IniDocument],
                       layers: list[dict[str, IniDocument]]) -> dict[str, IniDocument]:
    """Replay raw entries in caller-declared order, retaining every origin.

    Operations must be applied after composing: pre-filtering each document
    would lose DLC removals and clears aimed at an earlier document.
    """
    result = {}
    for family in FAMILIES:
        components = [layer[family] for layer in [base, *layers] if family in layer]
        if not components:
            continue
        composite = IniDocument('', f'composed:{family}')
        for document in components:
            for section, entries in document.sections.items():
                actual = composite.section_name(section) or section
                target = composite.sections.setdefault(actual, [])
                for entry in entries:
                    copied = deepcopy(entry)
                    copied['_source'] = document.source(section, entry)
                    target.append(copied)
        result[family] = composite.freeze()
    return result


def _scalar_conflicts(document: IniDocument, section: str, entries: list[dict]) -> list[dict]:
    """Do not choose between conflicting scalar values from separate DLCs."""
    last_by_layer = {}
    for entry in entries:
        source = document.source(section, entry)
        if source['dataset'].startswith('game_dlc:'):
            last_by_layer[source['dataset']] = entry
    selected = list(last_by_layer.values())
    if len(selected) > 1 and any(entry['value'] != selected[0]['value'] for entry in selected[1:]):
        return [document.fact(section, entry) for entry in selected]
    return []


def _character_section(document: IniDocument, name: str) -> tuple[str | None, list[str]]:
    candidates = [section for section in document.sections
                  if len(section.split()) == 2
                  and section.split()[0].casefold() == name.casefold()
                  and 'charactertemplate' in section.split()[1].casefold()]
    return (candidates[0], []) if len(candidates) == 1 else (None, candidates)


def _stats(unit: dict, document: IniDocument | None) -> dict:
    name = unit.get('template_name')
    if not name:
        return {'status': 'not_declared', 'base': {}, 'difficulty': {},
                'randomized_base_stats': [], 'effective_values_complete': False}
    if document is None:
        return {'status': 'not_present', 'base': {}, 'difficulty': {},
                'randomized_base_stats': [], 'effective_values_complete': False}

    def values(section_name):
        result, conflicts = {}, {}
        if section_name is None:
            return result, conflicts
        entries_by_stat = {}
        for entry in document.entries(section_name):
            match = re.fullmatch(r'CharacterBaseStats\[(\w+)\]', entry['key'], re.I)
            if match:
                entries_by_stat.setdefault(match[1], []).append(entry)
        for stat, entries in entries_by_stat.items():
            conflict = _scalar_conflicts(document, section_name, entries)
            if conflict:
                conflicts[stat] = conflict
            else:
                result[stat] = document.fact(section_name, entries[-1])
        return result, conflicts

    section, ambiguous = _character_section(document, name)
    base, base_conflicts = values(section)
    difficulties, variant_conflicts, ambiguous_variants = {}, {}, {}
    any_difficulty = False
    for difficulty in range(4):
        variant, variant_ambiguous = _character_section(document, f'{name}_Diff_{difficulty}')
        present = variant is not None
        any_difficulty |= present
        overrides, conflicts = values(variant)
        merged = {key: fact['value'] for key, fact in base.items()}
        merged.update({key: fact['value'] for key, fact in overrides.items()})
        # A conflicting override cannot safely fall back to the base value.
        for key in conflicts:
            merged.pop(key, None)
        # An ambiguous subclass variant may override known base fields too.
        # Keep inherited fields only when none of its candidates mentions them.
        for candidate in variant_ambiguous:
            candidate_values, candidate_conflicts = values(candidate)
            for key in candidate_values.keys() | candidate_conflicts.keys():
                merged.pop(key, None)
        difficulties[str(difficulty)] = {
            'section_present': present, 'overrides': overrides, 'values': merged,
        }
        if conflicts:
            variant_conflicts[str(difficulty)] = conflicts
        if variant_ambiguous:
            ambiguous_variants[str(difficulty)] = variant_ambiguous
    randomized = ([document.fact(section, entry)
                   for entry in document.entries(section, 'RandomizedBaseStats')]
                  if section is not None else [])
    status = ('ambiguous' if ambiguous else 'present' if section is not None else
              'partial' if any_difficulty else 'not_present')
    result = {'status': status, 'base': base, 'difficulty': difficulties,
              'randomized_base_stats': randomized, 'effective_values_complete': False}
    if base_conflicts or variant_conflicts:
        result['conflicting_fields'] = {'base': base_conflicts, 'difficulty': variant_conflicts}
    if ambiguous or ambiguous_variants:
        result['ambiguous_sections'] = {'base': ambiguous, 'difficulty': ambiguous_variants}
    return result


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
    resolved, unresolved, conflicts = {}, {}, {}
    for field, declaration in weapon.get('properties', {}).items():
        reference = declaration.get('reference')
        if not reference:
            continue
        match = re.fullmatch(r"(?:(?:class\s*'(?P<class>\w+)'\s*\.)?)default\.(?P<symbol>\w+)", reference, re.I)
        if not match:
            unresolved[field] = reference
            continue
        owner = match['class'] or Path(declaration.get('source', weapon['source'])['file']).stem
        candidates = [(candidate, section)
                      for candidate in (documents.values() if match['class'] else
                                        [document] if document is not None else [])
                      for section in candidate.sections
                      if section.rsplit('.', 1)[-1].casefold() == owner.casefold()]
        if len(candidates) == 1:
            target_document, section = candidates[0]
            entries = target_document.entries(section, match['symbol'])
            conflict = _scalar_conflicts(target_document, section, entries)
            if conflict:
                conflicts[field] = conflict
            elif entries:
                resolved[field] = target_document.fact(section, entries[-1])
            else:
                indexed = {}
                for entry in target_document.entries(section):
                    index = re.fullmatch(re.escape(match['symbol']) + r'\[(\d+)\]', entry['key'], re.I)
                    if index:
                        indexed.setdefault(int(index[1]), []).append(entry)
                bad_indexes = {index: _scalar_conflicts(target_document, section, rows)
                               for index, rows in indexed.items()}
                bad_indexes = {str(index): rows for index, rows in bad_indexes.items() if rows}
                if bad_indexes:
                    conflicts[field] = {'indexed_values': bad_indexes}
                elif indexed:
                    # Explicit indexes only: absent indexes are unknown, not zero.
                    resolved[field] = {'indexed_values': [
                        {'index': index, **target_document.fact(section, indexed[index][-1])}
                        for index in sorted(indexed)]}
        if field in resolved:
            continue
        # The source index supplies only direct literal non-config defaults;
        # these are separate from INI facts and never resolve an INI conflict.
        source_default = weapon.get('source_defaults', {}).get(match['symbol'])
        if (field not in conflicts and len(candidates) <= 1 and source_default is not None
                and source_default.get('source', {}).get('class', '').casefold() == owner.casefold()):
            fact = deepcopy(source_default)
            fact['source']['dataset'] = 'sdk_source_defaults'
            resolved[field] = fact
        else:
            unresolved[field] = reference
    result = {'resolved_properties': resolved, 'unresolved_references': unresolved,
              'effective_values_complete': False}
    if conflicts:
        result['conflicting_properties'] = conflicts
    return result


def _file_record(path: Path) -> dict:
    if not path.is_file():
        return {'present': False}
    data = path.read_bytes()
    return {'present': True, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def enrich_catalog(catalog: dict, game_config: Path, sdk_config: Path | None = None,
                   game_dlc: dict[str, Path] | None = None) -> dict:
    """Enrich a copy using game Defaults and caller-ordered game DLC snapshots."""
    game_dir = _config_dir(game_config)
    sdk_dir = _config_dir(sdk_config) if sdk_config is not None else None
    documents = _documents(game_dir)
    dlc_records, dlc_layers = [], []
    for label, supplied_path in (game_dlc or {}).items():
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', label):
            raise ValueError('DLC labels must be simple names, not paths.')
        directory = _config_dir(supplied_path)
        layer = _dlc_documents(directory, label)
        dlc_layers.append(layer)
        used_names = {document.filename.rsplit('/', 1)[-1] for document in layer.values()}
        files = [{'file': f'{label}/Config/{path.name}',
                  'used_by_catalog': path.name in used_names, **_file_record(path)}
                 for path in sorted(directory.iterdir(), key=lambda path: path.name.casefold())
                 if path.is_file() and path.suffix.casefold() == '.ini']
        dlc_records.append({'name': label, 'dataset': f'game_dlc:{label}',
                            'files': files, 'ini_file_count': len(files),
                            'used_ini_file_count': sum(file['used_by_catalog'] for file in files)})
    if dlc_layers:
        documents = _compose_documents(documents, dlc_layers)
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
        'format_version': 2 if dlc_records else 1, 'primary_dataset': 'game_defaults',
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
    if dlc_records:
        audit = result['configuration_audit']
        audit['dlc_configuration'] = {
            'source': 'game_installation', 'input_order': list(game_dlc),
            'native_load_order_verified': False, 'datasets': dlc_records,
            'array_operations': 'replayed_across_documents_before_selection',
            'scalar_conflict_policy': 'different_values_from_multiple_dlc_layers_remain_unresolved',
        }
        audit['limitations'][0] = ('Values compose supplied game Defaults and explicitly identified game DLC INIs; '
                                   'they are not certified effective native/runtime values.')
        audit['limitations'].extend([
            'DLC documents use caller-declared input order; actual native DLC enumeration and hooks are not executed.',
            'Conflicting scalar values from separate DLC layers remain unresolved instead of guessing a winning layer.',
        ])
        audit['coverage']['weapon_properties_from_source_defaults'] = sum(
            fact.get('source', {}).get('dataset') == 'sdk_source_defaults'
            for weapon in result.get('weapon_definitions', [])
            for fact in weapon['config_values']['resolved_properties'].values())
        audit['coverage']['weapon_properties_from_configuration'] = (
            audit['coverage']['weapon_properties_resolved']
            - audit['coverage']['weapon_properties_from_source_defaults'])
    return result
