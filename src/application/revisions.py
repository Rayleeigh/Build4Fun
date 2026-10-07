"""Atomic project revisions. CURRENT is the only commit point."""
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from core import Invalid, read_yaml
from storage import Workspace, atomic_write
from references import normalize


class Conflict(Invalid):
    def __init__(self):
        super().__init__('This project changed in another tab or on disk. Your drafts are intact. Reload the saved project before retrying.', code='revision_conflict')


def fingerprint(workspace):
    digest = hashlib.sha256()
    if workspace.project_path.exists():
        digest.update(workspace.project_path.read_bytes())
    for entry in workspace.listing():
        digest.update(json.dumps(entry, sort_keys=True).encode())
        if not entry['directory']:
            digest.update(workspace.path(entry['path']).read_bytes())
    return digest.hexdigest()


def copy_files(source, target):
    for entry in source.listing():
        path = source.path(entry['path'])
        destination = target.files / entry['path']
        if entry['directory']:
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)


class Revisions:
    def __init__(self, projects, definitions):
        self.projects, self.definitions = projects, definitions

    def read(self, identity):
        workspace = self.projects.workspace(identity)
        project = read_yaml(workspace.project_path.read_text())
        return {'project': normalize(project, self.definitions, workspace.listing()), 'files': workspace.listing(), 'revision': fingerprint(workspace)}

    def commit(self, identity, expected, project=None, edits=None, operation=None):
        workspace = self.projects.workspace(identity)
        if not isinstance(expected, str) or expected != fingerprint(workspace):
            raise Conflict()
        base = workspace.data_root
        root = workspace.root / 'revisions'
        root.mkdir(exist_ok=True)
        # Preserve the original pre-revision workspace as a recoverable baseline.
        if not (workspace.root / 'CURRENT').exists():
            baseline = root / uuid.uuid4().hex
            baseline_workspace = Workspace(baseline)
            copy_files(workspace, baseline_workspace)
            atomic_write(baseline / 'project.yaml', workspace.project_path.read_text())
        revision = uuid.uuid4().hex
        stage = Workspace(root / revision)
        committed = False
        try:
            copy_files(workspace, stage)
            atomic_write(stage.project_path, workspace.project_path.read_text())
            model = project if project is not None else read_yaml(stage.project_path.read_text())
            model = normalize(model, self.definitions, stage.listing())
            for path, content in (edits or {}).items():
                stage.write(path, content)
            if operation:
                kind = operation['kind']
                path = operation['path']
                if kind == 'create':
                    stage.write(path, operation.get('content', ''), create=True)
                elif kind == 'folder':
                    stage.path(path).mkdir(parents=True, exist_ok=False)
                elif kind == 'delete':
                    stage.delete(path)
                elif kind == 'rename':
                    source, destination = stage.path(path), stage.path(operation['destination'])
                    if destination.exists() or source == destination or source in destination.parents:
                        raise Invalid('Choose a new, unused destination outside the folder being moved.')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    source.rename(destination)
                    for file_id, value in model.get('fileReferences', {}).items():
                        if value == path or value.startswith(path + '/'):
                            model['fileReferences'][file_id] = operation['destination'] + value[len(path):]
                    def update(node):
                        if node['type'] == 'bind-mount':
                            value = node['values'].get('source', '').removeprefix('./')
                            if value == path or value.startswith(path + '/'):
                                node['values']['source'] = operation['destination'] + value[len(path):]
                        for child in node.get('children', []):
                            update(child)
                    update(model)
                else:
                    raise Invalid('Unknown file operation.')
            model = normalize(model, self.definitions, stage.listing())
            result = self.projects.save(identity, model, self.definitions, target=stage)
            atomic_write(stage.root / 'revision.json', json.dumps({'parent': base.name if base.parent == root else None}))
            # Detect out-of-process modifications during staging too.
            if fingerprint(workspace) != expected:
                raise Conflict()
            atomic_write(workspace.root / 'CURRENT', revision)
            committed = True
            result.update(self.read(identity))
            return result
        except Exception:
            if not committed:
                shutil.rmtree(stage.root)
            raise

    def history(self, identity):
        workspace = self.projects.workspace(identity)
        root = workspace.root / 'revisions'
        return [p.name for p in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True) if p.is_dir() and not p.is_symlink() and (p / 'project.yaml').exists()] if root.exists() else []

    def restore(self, identity, expected, revision):
        workspace = self.projects.workspace(identity)
        if revision not in self.history(identity):
            raise Invalid('Unknown saved revision.')
        source = Workspace(workspace.root / 'revisions' / revision)
        if fingerprint(workspace) != expected:
            raise Conflict()
        # Make recovery a new commit; never rewrite the historical revision.
        current = workspace.root / 'CURRENT'
        model = read_yaml(source.project_path.read_text())
        target_id = uuid.uuid4().hex
        stage = Workspace(workspace.root / 'revisions' / target_id)
        try:
            copy_files(source, stage)
            self.projects.save(identity, model, self.definitions, target=stage)
            atomic_write(stage.root / 'revision.json', json.dumps({'restoredFrom': revision}))
            if fingerprint(workspace) != expected:
                raise Conflict()
            atomic_write(current, target_id)
        except Exception:
            shutil.rmtree(stage.root)
            raise
        return self.read(identity)
