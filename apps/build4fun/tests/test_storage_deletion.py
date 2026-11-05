"""Deletion stays inside the workspace and never follows symbolic links."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'application'))
from core import Invalid
from storage import Workspace


class DeletionTests(unittest.TestCase):
    def test_file_and_recursive_folder_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(directory)
            workspace.write('config/nested/example.conf', 'arbitrary invalid configuration')
            workspace.write('keep.txt', 'keep')
            workspace.delete('config/nested/example.conf')
            self.assertTrue(workspace.path('config/nested').is_dir())
            workspace.write('config/nested/another.conf', 'unchanged')
            workspace.delete('config')
            self.assertEqual(workspace.listing(), [{'path': 'keep.txt', 'directory': False}])
            with self.assertRaises(FileNotFoundError):
                workspace.delete('missing')

    def test_paths_and_symlinks_cannot_delete_outside_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / 'workspace')
            outside = Path(directory) / 'outside.txt'
            outside.write_text('keep')
            workspace.path('link').symlink_to(outside)
            for path in ('', '.', '..', '../outside.txt', str(outside), 'link'):
                with self.subTest(path=path), self.assertRaises(Invalid):
                    workspace.delete(path)
            workspace.path('folder').mkdir()
            workspace.path('folder/link').symlink_to(outside)
            workspace.delete('folder')
            self.assertEqual(outside.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
