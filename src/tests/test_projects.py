import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'application'))
from core import Invalid, read_yaml
from storage import Workspace
from projects import Projects


class ProjectTests(unittest.TestCase):
    def test_projects_are_separate_and_persistent(self):
        with tempfile.TemporaryDirectory() as root:
            legacy = Workspace(root)
            legacy.write('keep.conf', 'legacy')
            projects = Projects(legacy)
            first = projects.create('Project 1')
            second = projects.create('Project 2')
            a, b = projects.workspace(first['id']), projects.workspace(second['id'])
            a.write('test.conf', 'first')
            b.write('test.conf', 'second')
            a.delete('test.conf')
            self.assertEqual(b.read('test.conf'), 'second')
            self.assertEqual(legacy.read('keep.conf'), 'legacy')
            self.assertEqual(len(Projects(legacy).listing()), 2)
            document = read_yaml((a.root / 'project.yaml').read_text())
            self.assertEqual(document['children'][0]['values']['name'], 'project-1')
            self.assertEqual(len(document['children']), 1)
            with self.assertRaises(Invalid):
                projects.create('project 1')
            with self.assertRaises(Invalid):
                projects.workspace('../files')
            with self.assertRaises(Invalid):
                projects.workspace('a' * 32)

    def test_normalized_name_collisions_get_unique_compose_names(self):
        with tempfile.TemporaryDirectory() as root:
            projects = Projects(Workspace(root))
            projects.create('Project 1')
            other = projects.create('Project-1')
            document = read_yaml((projects.workspace(other['id']).root / 'project.yaml').read_text())
            self.assertEqual(document['children'][0]['values']['name'], 'project-1-2')

    def test_rename_and_delete_preserve_other_projects_and_compose_name(self):
        with tempfile.TemporaryDirectory() as root:
            legacy = Workspace(root)
            (legacy.root / 'project.yaml').write_text('type: harness\nchildren: []\n')
            legacy.write('old.conf', 'old')
            projects = Projects(legacy)
            first = projects.create('First')
            second = projects.create('Second')
            workspace = projects.workspace(first['id'])
            original = (workspace.root / 'project.yaml').read_text()
            workspace.write('nested/example.conf', 'keep')
            projects.rename(first['id'], 'Renamed')
            self.assertEqual((workspace.root / 'project.yaml').read_text(), original)
            self.assertEqual(workspace.read('nested/example.conf'), 'keep')
            with self.assertRaises(Invalid):
                projects.rename(first['id'], 'Second')
            projects.rename('legacy', 'Original')
            projects.delete('legacy')
            self.assertEqual(len(projects.listing()), 2)
            self.assertEqual(workspace.read('nested/example.conf'), 'keep')
            projects.delete(first['id'])
            self.assertFalse(workspace.root.exists())
            self.assertEqual(projects.listing(), [second])
