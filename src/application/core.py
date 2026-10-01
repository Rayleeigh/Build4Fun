"""Load YAML block definitions and assemble a Compose document."""
from pathlib import Path
import copy
import re
import yaml


class Invalid(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise Invalid('YAML keys must be unique strings.')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def read_yaml(text):
    try:
        return yaml.load(text, Loader=UniqueLoader)
    except yaml.YAMLError as error:
        raise Invalid(str(error)) from error


def registry(directory):
    definitions = {}
    for path in sorted(Path(directory).glob('*.yaml')):
        d = read_yaml(path.read_text())
        if not isinstance(d, dict) or not isinstance(d.get('id'), str):
            raise Invalid(f'{path.name}: missing block ID.')
        if d['id'] in definitions or d.get('version') != 1:
            raise Invalid(f'{path.name}: duplicate ID or unsupported version.')
        if d.get('op') not in ('root', 'group', 'named', 'set', 'append'):
            raise Invalid(f'{path.name}: unsupported assembly operation.')
        if not isinstance(d.get('label'), str) or not isinstance(d.get('children', []), list):
            raise Invalid(f'{path.name}: invalid label or children.')
        if d['op'] != 'root' and not isinstance(d.get('target'), str):
            raise Invalid(f'{path.name}: missing assembly target.')
        keys = set()
        for field in d.get('inputs', []):
            key = field.get('key')
            if not isinstance(key, str) or key in keys:
                raise Invalid(f'{path.name}: invalid or duplicate input key.')
            keys.add(key)
            if field.get('type') not in ('text', 'integer', 'choice', 'boolean'):
                raise Invalid(f'{path.name}: unsupported input type.')
            if field['type'] == 'choice' and not field.get('choices'):
                raise Invalid(f'{path.name}: missing choices.')
        if d['op'] == 'named' and d.get('key') not in keys:
            raise Invalid(f'{path.name}: unknown naming input.')
        def check_template(value):
            if isinstance(value, dict):
                if set(value) == {'input'}:
                    if value['input'] not in keys:
                        raise Invalid(f'{path.name}: unknown template input.')
                else:
                    for child in value.values():
                        check_template(child)
            elif isinstance(value, list):
                for child in value:
                    check_template(child)
        check_template(d.get('template', {}))
        definitions[d['id']] = d
    for d in definitions.values():
        if any(child not in definitions for child in d.get('children', [])):
            raise Invalid(f'{d["id"]}: unknown child type.')
    if 'harness' not in definitions:
        raise Invalid('Missing harness definition.')
    return definitions


def check_structure(project, definitions):
    seen = set()
    def visit(node, parent=None, depth=0):
        if depth > 12 or not isinstance(node, dict):
            raise Invalid('Invalid block hierarchy.')
        kind = node.get('type')
        if not isinstance(kind, str):
            raise Invalid('Missing block type.')
        d = definitions.get(kind)
        if not d or node.get('version') != d['version']:
            raise Invalid(f'Unknown block definition or version: {kind}')
        ident = node.get('id')
        if not isinstance(ident, str) or ident in seen:
            raise Invalid('Each block must have a unique ID.')
        seen.add(ident)
        if len(seen) > 1000:
            raise Invalid('Project exceeds 1000 blocks.')
        if parent is None and kind != 'harness':
            raise Invalid('The project must start with a harness.')
        if parent and kind not in parent.get('children', []):
            raise Invalid(f'{kind} cannot be placed inside {parent["id"]}.')
        if not isinstance(node.get('values', {}), dict) or not isinstance(node.get('children', []), list):
            raise Invalid('Invalid block values or children.')
        counts = {}
        for child in node.get('children', []):
            visit(child, d, depth + 1)
            k = child['type']
            counts[k] = counts.get(k, 0) + 1
            if definitions[k].get('single') and counts[k] > 1:
                raise Invalid(f'Only one {definitions[k]["label"]} is allowed here.')
    visit(project)


def compile_project(project, definitions):
    check_structure(project, definitions)
    references = []

    def assemble(node):
        d = definitions[node['type']]
        values = {}
        def fail(message):
            raise Invalid(f'{d["label"]} [{node["id"]}]: {message}')
        for f in d.get('inputs', []):
            value = node.get('values', {}).get(f['key'], '')
            if f['type'] == 'boolean':
                if not isinstance(value, bool):
                    fail(f'{f["label"]} must be true or false.')
            elif f['type'] == 'integer':
                if isinstance(value, bool) or not re.fullmatch(r'\d+', str(value)):
                    fail(f'{f["label"]} must be a whole number.')
                value = int(value)
                if not f.get('min', 0) <= value <= f.get('max', 65535):
                    fail(f'{f["label"]} is outside the allowed range.')
            else:
                if not isinstance(value, str) or (not value and not f.get('allowEmpty')):
                    fail(f'{f["label"]} is required.')
                if f.get('pattern') and not re.fullmatch(f['pattern'], value):
                    fail(f'{f["label"]} has an invalid format.')
                if f['type'] == 'choice' and value not in f['choices']:
                    fail(f'Choose a valid {f["label"]}.')
            values[f['key']] = value
        for f in d.get('inputs', []):
            if f.get('reference'):
                references.append((f['reference'], values[f['key']], node['id']))
        def render(value):
            if isinstance(value, dict):
                if set(value) == {'input'}:
                    return values[value['input']]
                return {k: render(v) for k, v in value.items()}
            if isinstance(value, list):
                return [render(v) for v in value]
            return copy.deepcopy(value)
        result = render(d.get('template', {}))
        for child in node.get('children', []):
            cd = definitions[child['type']]
            item = assemble(child)
            target = cd['target']
            if cd['op'] == 'group':
                for key, value in item.items():
                    if key in result:
                        fail(f'Duplicate setting: {key}')
                    result[key] = value
            elif cd['op'] == 'named':
                dest = result.setdefault(target, {})
                key = child['values'][cd['key']]
                if key in dest:
                    fail(f'Duplicate {target} name: {key}')
                dest[key] = item
            elif cd['op'] == 'append':
                result.setdefault(target, []).append(item)
            else:
                if target in result:
                    fail(f'Duplicate setting: {target}')
                result[target] = item
        return result

    result = assemble(project)
    if not result.get('name') or not result.get('services'):
        raise Invalid('Add a Project name block and at least one Service.')
    for kind, name, block_id in references:
        if name not in result.get(kind, {}):
            raise Invalid(f'Block [{block_id}]: unknown {kind} reference: {name}')
    for name, service in result['services'].items():
        if not service.get('image'):
            raise Invalid(f'Service {name}: add an Image block.')
        mounts = service.get('volumes', [])
        targets = [m['target'] for m in mounts]
        if len(targets) != len(set(targets)):
            raise Invalid(f'Service {name}: duplicate mount destination.')
        ports = service.get('ports', [])
        for port in ports:
            port['published'] = str(port['published'])
        for mount in mounts:
            if mount['type'] == 'bind':
                source = Path(mount['source'])
                if source.is_absolute() or '..' in source.parts or not source.parts:
                    raise Invalid(f'Service {name}: bind source must be a project-relative path.')
                mount['source'] = './' + source.as_posix()
    return result


def compose_yaml(project, definitions):
    # Dollar signs entered as values are literal, not Compose interpolation.
    def literal(value):
        if isinstance(value, str):
            return value.replace('$', '$$')
        if isinstance(value, list):
            return [literal(v) for v in value]
        if isinstance(value, dict):
            return {k: literal(v) for k, v in value.items()}
        return value
    return yaml.safe_dump(literal(compile_project(project, definitions)), sort_keys=False)
