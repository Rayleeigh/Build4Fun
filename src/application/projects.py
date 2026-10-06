"""Project catalog with stable IDs and independent file workspaces."""
import json
import re
import uuid
import shutil
import yaml

from core import Invalid, read_yaml
from storage import Workspace, atomic_write


class Projects:
    def __init__(self, workspace):
        self.legacy = workspace
        self.root = workspace.root / 'projects'

    def workspace(self, identity):
        if identity == 'legacy':
            return self.legacy
        if not re.fullmatch(r'[0-9a-f]{32}', identity):
            raise Invalid('Unknown project.')
        path = self.root / identity
        if self.root.is_symlink() or path.is_symlink() or not (path / 'metadata.json').is_file():
            raise Invalid('Unknown project.')
        return Workspace(path)

    def listing(self):
        result = []
        project = self.legacy.root / 'project.yaml'
        if project.exists():
            data = read_yaml(project.read_text())
            name = next((n['values'].get('name') for n in data.get('children', []) if n['type'] == 'project-name'), None)
            metadata = self.legacy.root / 'metadata.json'
            result.append(json.loads(metadata.read_text()) if metadata.exists() else {'id': 'legacy', 'name': name or 'Existing project'})
        if self.root.exists() and not self.root.is_symlink():
            for path in sorted(self.root.iterdir()):
                if re.fullmatch(r'[0-9a-f]{32}', path.name) and not path.is_symlink() and (path / 'metadata.json').is_file():
                    result.append(json.loads((path / 'metadata.json').read_text()))
        return result

    def create(self, name):
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            raise Invalid('Enter a project name between 1 and 80 characters.')
        name = name.strip()
        existing = self.listing()
        if any(p['name'].casefold() == name.casefold() for p in existing):
            raise Invalid('A project with that name already exists.')
        slug = re.sub(r'[^a-z0-9_-]+', '-', name.lower()).strip('-_') or 'project'
        used = set()
        for item in existing:
            document = self.workspace(item['id']).root / 'project.yaml'
            if document.exists():
                used.update(n['values'].get('name') for n in read_yaml(document.read_text()).get('children', []) if n['type'] == 'project-name')
        base, suffix = slug, 2
        while slug in used:
            slug = f'{base}-{suffix}'
            suffix += 1
        identity = uuid.uuid4().hex
        if self.root.is_symlink():
            raise Invalid('The project directory must not be a symbolic link.')
        workspace = Workspace(self.root / identity)
        project = {'id': uuid.uuid4().hex, 'type': 'harness', 'version': 1, 'values': {}, 'children': [
            {'id': uuid.uuid4().hex, 'type': 'project-name', 'version': 1, 'values': {'name': slug}, 'children': []}
        ]}
        metadata = {'id': identity, 'name': name}
        atomic_write(workspace.root / 'project.yaml', yaml.safe_dump(project, sort_keys=False))
        atomic_write(workspace.root / 'metadata.json', json.dumps(metadata))
        return metadata

    def rename(self, identity, name):
        workspace = self.workspace(identity)
        if not any(p['id'] == identity for p in self.listing()):
            raise Invalid('Unknown project.')
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            raise Invalid('Enter a project name between 1 and 80 characters.')
        name = name.strip()
        if any(p['id'] != identity and p['name'].casefold() == name.casefold() for p in self.listing()):
            raise Invalid('A project with that name already exists.')
        metadata = {'id': identity, 'name': name}
        atomic_write(workspace.root / 'metadata.json', json.dumps(metadata))
        return metadata

    def delete(self, identity):
        workspace = self.workspace(identity)
        if (workspace.root / 'deployment.json').exists():
            raise Invalid('Remove this project’s deployment from Environment controls before deleting its files.')
        if identity == 'legacy':
            # The legacy root also contains all newer projects; never remove it.
            if workspace.files.is_symlink():
                raise Invalid('Symbolic links are not supported in the workspace.')
            shutil.rmtree(workspace.files)
            workspace.files.mkdir()
            for name in ('project.yaml', 'metadata.json'):
                (workspace.root / name).unlink(missing_ok=True)
        else:
            shutil.rmtree(workspace.root)
