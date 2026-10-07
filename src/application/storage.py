"""Workspace-scoped persistence; file contents are deliberately not validated."""
from pathlib import Path
import os
import shutil
import tempfile
import re

from core import Invalid


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.files.mkdir(parents=True, exist_ok=True)

    @property
    def data_root(self):
        pointer = self.root / 'CURRENT'
        if not pointer.exists():
            return self.root
        revision = pointer.read_text().strip()
        if not re.fullmatch(r'[0-9a-f]{32}', revision):
            raise Invalid('Invalid saved revision pointer.')
        path = self.root / 'revisions' / revision
        if path.is_symlink() or not path.is_dir():
            raise Invalid('Saved revision is missing.')
        return path

    @property
    def files(self):
        return self.data_root / 'files'

    @property
    def project_path(self):
        return self.data_root / 'project.yaml'

    def path(self, name):
        if not isinstance(name, str) or not name or '\x00' in name:
            raise Invalid('Enter a project-relative path.')
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise Invalid('The path must stay inside the project workspace.')
        candidate = self.files / relative
        current = self.files
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise Invalid('Symbolic links are not supported in the workspace.')
        resolved = candidate.resolve()
        if resolved == self.files or self.files not in resolved.parents:
            raise Invalid('The path must stay inside the project workspace.')
        return resolved

    def listing(self):
        result = []
        for directory, dirs, files in os.walk(self.files, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
            for name in dirs + sorted(files):
                p = Path(directory) / name
                if not p.is_symlink():
                    result.append({'path': p.relative_to(self.files).as_posix(), 'directory': p.is_dir()})
        return result

    def read(self, name):
        path = self.path(name)
        if path.stat().st_size > 1024 * 1024:
            raise Invalid('This editor supports text files up to 1 MiB.')
        return path.read_text(encoding='utf-8')

    def delete(self, name):
        path = self.path(name)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    def write(self, name, content, create=False):
        if not isinstance(content, str) or len(content.encode('utf-8')) > 1024 * 1024:
            raise Invalid('This editor supports text files up to 1 MiB.')
        path = self.path(name)
        if create and path.exists():
            raise Invalid('A file or folder already exists at that path.')
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, content)


def atomic_write(path, content):
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix='.save-')
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
