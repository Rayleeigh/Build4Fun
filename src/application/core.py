"""Load YAML block definitions and assemble a Compose document."""
from pathlib import Path
import copy
import ipaddress
import re
import yaml
from references import normalize


class Invalid(ValueError):
    def __init__(self, message, code='invalid_configuration', block_id=None, field=None):
        super().__init__(message)
        self.issue = {'code': code, 'blockId': block_id, 'field': field, 'message': message}


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
    project = normalize(project, definitions, strict=True)
    references = []
    missing = object()

    def assemble(node):
        d = definitions[node['type']]
        values = {}
        current_field = None
        def fail(message):
            raise Invalid(message, block_id=node['id'], field=current_field)
        for f in d.get('inputs', []):
            current_field = f['key']
            value = node.get('values', {}).get(f['key'], '')
            if f.get('optional') and value in ('', None):
                values[f['key']] = missing
                continue
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
            if f.get('format'):
                try:
                    if f['format'] == 'ipv4':
                        ipaddress.IPv4Address(value)
                    elif f['format'] == 'ipv4-network':
                        ipaddress.IPv4Network(value)
                    elif f['format'] == 'ip':
                        ipaddress.ip_address(value)
                except ValueError:
                    fail(f'{f["label"]} must be a valid {f["format"]}.')
            values[f['key']] = value
        for f in d.get('inputs', []):
            if f.get('reference'):
                references.append((f['reference'], values[f['key']], node['id']))
        def render(value):
            if isinstance(value, dict):
                if set(value) == {'input'}:
                    return values[value['input']]
                rendered = {k: render(v) for k, v in value.items()}
                rendered = {k: v for k, v in rendered.items() if v is not missing}
                return missing if value and not rendered else rendered
            if isinstance(value, list):
                rendered = [render(v) for v in value]
                rendered = [v for v in rendered if v is not missing]
                return missing if value and not rendered else rendered
            return copy.deepcopy(value)
        result = render(d.get('template', {}))
        if result is missing:
            result = {}
        current_field = None
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
            raise Invalid(f'unknown {kind} reference: {name}', code='missing_reference', block_id=block_id)
    for name, service in result['services'].items():
        if not service.get('image'):
            raise Invalid(f'Service {name}: add an Image block.')
        mounts = service.get('volumes', [])
        targets = [m['target'] for m in mounts]
        if len(targets) != len(set(targets)):
            raise Invalid(f'Service {name}: duplicate mount destination.')
        ports = service.get('ports', [])
        service['ports'] = [short_port(port) for port in ports] if 'ports' in service else []
        if not ports:
            service.pop('ports', None)
        for mount in mounts:
            if mount['type'] == 'bind':
                source = Path(mount['source'])
                if source.is_absolute() or '..' in source.parts or not source.parts:
                    raise Invalid(f'Service {name}: bind source must be a project-relative path.')
                mount['source'] = './' + source.as_posix()
    validate_networks(result, project)
    for name, service in result['services'].items():
        result['services'][name] = ordered(service, ('image', 'build', 'command', 'restart', 'ports', 'environment', 'volumes', 'networks'))
    for section in ('services', 'networks', 'volumes', 'configs', 'secrets'):
        if section in result:
            result[section] = dict(sorted(result[section].items()))
    return ordered(result, ('name', 'services', 'networks', 'volumes', 'configs', 'secrets'))


def ordered(value, preferred):
    return {key: value[key] for key in list(preferred) + sorted(set(value) - set(preferred)) if key in value}


def short_port(port):
    host = port.get('host_ip', '')
    if ':' in host:
        host = f'[{host}]'
    prefix = f'{host}:' if host else ''
    protocol = f'/{port["protocol"]}' if port.get('protocol') else ''
    return f'{prefix}{port["published"]}:{port["target"]}{protocol}'


def validate_networks(config, project=None):
    from references import walk
    children = (project or {}).get('children', [])
    resources = {node['values'].get('name'): node for node in children if node['type'] in ('network', 'external-network')}
    services = {node['values'].get('name'): node for node in children if node['type'] == 'service'}
    def network_error(message, name, field):
        raise Invalid(message, code='invalid_network', block_id=resources.get(name, {}).get('id'), field=field)
    def address_error(message, service, network):
        node = next((node for node in walk(services.get(service, {})) if node.get('type') == 'network-attachment' and node.get('values', {}).get('network') == network), {})
        raise Invalid(message, code='invalid_address', block_id=node.get('id'), field='ipv4Address')
    subnets = {}
    for name, network in config.get('networks', {}).items():
        for entry in network.get('ipam', {}).get('config', []):
            if not entry.get('subnet'):
                network_error(f'Network {name}: a subnet is required when a gateway is set.', name, 'subnet')
            subnet = ipaddress.IPv4Network(entry['subnet'])
            subnets[name] = subnet
            if entry.get('gateway'):
                address = ipaddress.IPv4Address(entry['gateway'])
                if address not in subnet or address in (subnet.network_address, subnet.broadcast_address):
                    network_error(f'Network {name}: gateway must be a usable address inside the subnet.', name, 'gateway')
    assigned = set()
    for name, service in config['services'].items():
        for network_name, attachment in service.get('networks', {}).items():
            value = attachment.get('ipv4_address')
            if not value:
                continue
            network = config['networks'][network_name]
            address = ipaddress.IPv4Address(value)
            identity = (network.get('name', network_name), str(address))
            if identity in assigned:
                address_error(f'Service {name}: duplicate static IP {value} on network {network_name}.', name, network_name)
            assigned.add(identity)
            if network.get('external'):
                continue  # Its subnet belongs to the existing Docker network.
            subnet = subnets.get(network_name)
            if not subnet:
                address_error(f'Service {name}: define a subnet for network {network_name} before assigning a static IP.', name, network_name)
            if address not in subnet or address in (subnet.network_address, subnet.broadcast_address):
                address_error(f'Service {name}: static IP {value} must be a usable address inside {subnet}.', name, network_name)
            gateways = [e.get('gateway') for e in network.get('ipam', {}).get('config', [])]
            if value in gateways:
                address_error(f'Service {name}: static IP cannot equal the network gateway.', name, network_name)


class QuotedPort(str):
    pass


class ComposeDumper(yaml.SafeDumper):
    pass


ComposeDumper.add_representer(QuotedPort, lambda dumper, value: dumper.represent_scalar('tag:yaml.org,2002:str', value, style='"'))


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
    result = literal(compile_project(project, definitions))
    for service in result['services'].values():
        if 'ports' in service:
            service['ports'] = [QuotedPort(port) for port in service['ports']]
    return yaml.dump(result, Dumper=ComposeDumper, sort_keys=False)


def compose_preview(project, definitions):
    """Return generated YAML and exact line ranges for its originating blocks."""
    text = compose_yaml(project, definitions)
    document = yaml.compose(text, Loader=yaml.SafeLoader)
    paths = {}

    def index(node, path=(), key_line=None):
        start = node.start_mark.line + 1 if key_line is None else key_line
        end = node.end_mark.line + (1 if node.end_mark.column else 0)
        paths[path] = {'start': start, 'end': max(start, end)}
        if isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                index(value, path + (key.value,), key.start_mark.line + 1)
        elif isinstance(node, yaml.SequenceNode):
            for i, value in enumerate(node.value):
                index(value, path + (i,))

    index(document)
    blocks = {project['id']: paths[()]}

    def locate(parent, base=()):
        counts = {}
        for child in parent.get('children', []):
            definition = definitions[child['type']]
            target = definition['target']
            operation = definition['op']
            if operation == 'group':
                path = base + (target,)
                child_base = base
            elif operation == 'named':
                path = base + (target, child['values'][definition['key']])
                child_base = path
            elif operation == 'append':
                position = counts.get(target, 0)
                counts[target] = position + 1
                path = base + (target, position)
                child_base = path
            else:
                path = base + (target,)
                child_base = path
            if path in paths:
                blocks[child['id']] = paths[path]
            locate(child, child_base)

    locate(project)
    return {'yaml': text, 'blocks': blocks}
