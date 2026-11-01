"""Execute the numeric subset used by pure UnrealScript planning helpers.

This deliberately small adapter loads function bodies from the real .uc files;
scenario tests exercise those bodies rather than a second scoring implementation.
It is not an UnrealScript parser, compiler, or replacement for in-game tests.
"""
from pathlib import Path
import re


def load_uc_function(path: Path, name: str):
    source = re.sub(r'//[^\n]*|/\*.*?\*/', '', path.read_text(), flags=re.S)
    match = re.search(r'\bfunction\s+(?:float|int|bool)\s+' + re.escape(name) + r'\s*\((.*?)\)\s*\{', source, re.S)
    if not match:
        raise ValueError(f'Numeric helper not found: {name}')
    parameters = [part.strip().split()[-1] for part in match[1].split(',') if part.strip()]
    start = match.end()
    depth = 1
    end = start
    while depth:
        if source[end] == '{':
            depth += 1
        elif source[end] == '}':
            depth -= 1
        end += 1
    body = re.sub(r'\blocal\b[^;]*;', '', source[start:end - 1])
    tokens = [token.strip() for token in re.split(r'([{};])', body) if token.strip() and token != ';']

    def expression(text):
        text = ' '.join(text.split())
        text = re.sub(r'\btrue\b', 'True', text, flags=re.I)
        text = re.sub(r'\bfalse\b', 'False', text, flags=re.I)
        text = text.replace('&&', ' and ').replace('||', ' or ')
        return re.sub(r'!(?!=)', 'not ', text)

    lines = [f'def {name}({", ".join(parameters)}):']
    indent = 1
    single_indent = False
    for token in tokens:
        if token == '{':
            continue
        if token == '}':
            indent -= 1
            continue
        if token.startswith('else if'):
            raise ValueError('Use independent early-return conditions in numeric helpers')
        elif token.startswith('if'):
            # Tests keep a condition and its body on separate lines. A same-line
            # single statement is also accepted by separating at the final ')'.
            condition = re.match(r'if\s*\((.*)\)\s*$', token.splitlines()[0])
            if not condition:
                raise ValueError(f'Unsupported condition in {name}: {token}')
            lines.append('    ' * indent + 'if ' + expression(condition[1]) + ':')
            indent += 1
            remainder = '\n'.join(token.splitlines()[1:]).strip()
            if remainder:
                lines.append('    ' * indent + expression(remainder))
                indent -= 1
            else:
                single_indent = False
        elif token == 'else':
            lines.append('    ' * indent + 'else:')
            indent += 1
        else:
            lines.append('    ' * indent + expression(token))
            if single_indent:
                indent -= 1
                single_indent = False
    namespace = {
        'FMin': min, 'FMax': max, 'Min': min, 'Max': max, 'Abs': abs,
        'FClamp': lambda value, low, high: min(high, max(low, value)),
        'Clamp': lambda value, low, high: min(high, max(low, value)),
        'float': float, 'int': int,
    }
    for called in set(re.findall(r'\b(\w+)\s*\(', body)) - set(namespace) - {'if'}:
        if re.search(r'\bfunction\s+(?:float|int|bool)\s+' + re.escape(called) + r'\s*\(', source):
            namespace[called] = load_uc_function(path, called)
    exec('\n'.join(lines), namespace)
    return namespace[name]
