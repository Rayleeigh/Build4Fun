"""Stable block/file references; legacy name references migrate only when unambiguous."""
import copy
import uuid
from pathlib import PurePosixPath


def walk(node):
    yield node
    for child in node.get('children', []):
        yield from walk(child)


def normalize(project, definitions, entries=None, strict=False):
    from core import Invalid
    project = copy.deepcopy(project)
    nodes = list(walk(project))
    by_id = {node['id']: node for node in nodes}
    paths = project.setdefault('fileReferences', {})
    if not isinstance(paths, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in paths.items()):
        raise Invalid('Invalid file reference directory.')
    if entries is not None:
        for entry in entries:
            if entry['path'] not in paths.values():
                # Deterministic migration until the first revision persists this directory.
                identity = uuid.uuid5(uuid.NAMESPACE_URL, project['id'] + '/' + entry['path']).hex
                paths[identity] = entry['path']
    for node in nodes:
        refs = node.setdefault('references', {})
        if not isinstance(refs, dict):
            raise Invalid('Invalid block references.', block_id=node['id'])
        for field in definitions[node['type']].get('inputs', []):
            key = field['key']
            kind = field.get('reference')
            if not kind and not field.get('file'):
                continue
            if kind:
                candidates = [item for item in project.get('children', []) if definitions[item['type']].get('target') == kind]
                if key not in refs:
                    matches = [item for item in candidates if item['values'].get('name') == node['values'].get(key)]
                    if len(matches) == 1:
                        refs[key] = matches[0]['id']
                target = by_id.get(refs.get(key))
                if target and target in candidates:
                    node['values'][key] = target['values'].get('name', '')
                elif key in refs and strict:
                    raise Invalid('The referenced resource was removed. Choose another resource.', code='missing_reference', block_id=node['id'], field=key)
            else:
                value = node['values'].get(key)
                if isinstance(value, str) and value:
                    value = str(PurePosixPath(value))
                    if key not in refs:
                        matches = [identity for identity, path in paths.items() if path == value]
                        if len(matches) == 1:
                            refs[key] = matches[0]
                if refs.get(key) in paths:
                    node['values'][key] = paths[refs[key]]
    return project
