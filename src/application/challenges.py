"""Discover Markdown lessons and evaluate declarative checks without executing code."""
import re
from pathlib import Path
from core import Invalid, compile_project, read_yaml

DOCS = Path(__file__).resolve().parents[2] / 'docs' / 'challenges'
MISSING = object()


def validate_rule(rule):
    if not isinstance(rule, dict):
        raise ValueError('Each condition must be a mapping.')
    keys = set(rule)
    if 'mount' in rule:
        mount = rule['mount']
        if keys != {'mount'} or not isinstance(mount, dict) or set(mount) != {'service', 'type', 'source', 'target', 'read_only'}:
            raise ValueError('Mount conditions require service, type, source, target, read_only.')
        if not all(isinstance(mount[k], str) and mount[k] for k in ('service', 'type', 'source', 'target')) or not isinstance(mount['read_only'], bool):
            raise ValueError('Invalid mount condition values.')
    elif 'file' in rule:
        if keys != {'file', 'contains'} or not isinstance(rule['file'], str) or not isinstance(rule['contains'], str):
            raise ValueError('File conditions require a file path and contains text.')
        path = Path(rule['file'])
        if path.is_absolute() or '..' in path.parts or not path.parts:
            raise ValueError('File conditions must use project-relative paths.')
    else:
        operators = keys - {'path'}
        if len(operators) != 1 or not operators <= {'equals', 'contains', 'exists', 'empty'}:
            raise ValueError('Use path with one of equals, contains, exists, empty.')
        if not isinstance(rule.get('path'), list) or not rule['path'] or not all(isinstance(p, str) and p for p in rule['path']):
            raise ValueError('Condition paths must be nonempty lists of mapping keys.')
        for key in ('exists', 'empty'):
            if key in rule and not isinstance(rule[key], bool):
                raise ValueError(f'{key} must be boolean.')


def load_catalog(directory=None):
    catalog = []
    for path in sorted(Path(directory or DOCS).glob('*.md')):
        text = path.read_text()
        if path.name == 'README.md':
            continue
        try:
            match = re.fullmatch(r'---\n(.*?)\n---\n(.*)', text, re.S)
            if not match:
                raise ValueError('Start the lesson with YAML front matter containing checks.')
            metadata, body = read_yaml(match[1]), match[2]
            title = re.search(r'^# (\d+)\. (.+)$', body, re.M)
            level = re.search(r'^Level: (.+)$', body, re.M)
            if not title or not level:
                raise ValueError('Expected # <number>. <title> and Level: <level>.')
            intro, *parts = re.split(r'^## (Build|Explain|Try it)\s*$', body, flags=re.M)
            sections = dict(zip(parts[::2], parts[1::2]))
            if set(sections) != {'Build', 'Explain', 'Try it'}:
                raise ValueError('Expected Build, Explain, and Try it sections.')
            goal = intro.split(level.group(0), 1)[1].strip()
            steps = re.findall(r'^\d+\. (.+)$', sections['Build'], re.M)
            checks = metadata.get('checks') if isinstance(metadata, dict) else None
            if not goal or not steps or not sections['Explain'].strip() or not sections['Try it'].strip() or not isinstance(checks, list) or not checks:
                raise ValueError('Lesson content and at least one automatic check are required.')
            for check in checks:
                if not isinstance(check, dict) or set(check) != {'label', 'all'} or not isinstance(check['label'], str) or not check['label'].strip() or not isinstance(check['all'], list) or not check['all']:
                    raise ValueError('Each check requires a label and a nonempty all list.')
                for rule in check['all']:
                    validate_rule(rule)
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', path.stem):
                raise ValueError('Use lowercase letters, numbers, and hyphens in lesson filenames.')
            catalog.append({'id': path.stem, 'order': int(title[1]), 'title': title[2], 'level': level[1],
                            'goal': goal, 'steps': steps, 'question': sections['Explain'].strip(),
                            'experiment': sections['Try it'].strip(), 'checks': [c['label'] for c in checks],
                            'rules': [c['all'] for c in checks]})
        except (Invalid, ValueError, TypeError, KeyError) as exc:
            raise Invalid(f'Challenge {path.name}: {exc}') from exc
    return sorted(catalog, key=lambda c: (c['order'], c['id']))


def matches(rule, compose, workspace):
    if 'file' in rule:
        try:
            return rule['contains'] in workspace.read(rule['file'])
        except (Invalid, OSError):
            return False
    if 'mount' in rule:
        expected = rule['mount']
        service = compose.get('services', {}).get(expected['service'], {})
        return any(all(mount.get(k, False if k == 'read_only' else None) == v
                       for k, v in expected.items() if k != 'service')
                   for mount in service.get('volumes', []))
    value = compose
    for key in rule['path']:
        value = value.get(key, MISSING) if isinstance(value, dict) else MISSING
    if 'exists' in rule:
        return (value is not MISSING) == rule['exists']
    if 'empty' in rule:
        return (value is MISSING or not value) == rule['empty']
    if value is MISSING:
        return False
    if 'equals' in rule:
        return value == rule['equals']
    return isinstance(value, (dict, list, str)) and rule['contains'] in value


def evaluate(compose, workspace, catalog=None):
    return {c['id']: [all(matches(rule, compose, workspace) for rule in rules) for rules in c['rules']]
            for c in (load_catalog() if catalog is None else catalog)}


def progress(projects, definitions):
    catalog = load_catalog()
    results = []
    for item in projects.listing():
        workspace = projects.workspace(item['id'])
        error = None
        try:
            compose = compile_project(read_yaml(workspace.project_path.read_text()), definitions)
            checks = evaluate(compose, workspace, catalog)
        except (Invalid, OSError, ValueError, TypeError, KeyError) as exc:
            error = str(exc)
            checks = {}
        results.append({**item, 'error': error, 'checks': checks})
    return {'challenges': catalog, 'projects': results}
