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

    def test_saved_compose_outputs_and_identical_file_paths_are_isolated(self):
        from test_core import block, registry, TEMPLATES
        with tempfile.TemporaryDirectory() as root:
            projects = Projects(Workspace(root))
            definitions = registry(TEMPLATES)
            ids = [projects.create(name)['id'] for name in ('First', 'Second')]
            for identity, image in zip(ids, ('nginx:alpine', 'busybox:latest')):
                workspace = projects.workspace(identity)
                document = read_yaml((workspace.root / 'project.yaml').read_text())
                document['children'].append(block('service', {'name': 'same-service'}, block('image', {'image': image}),
                    block('mounts', {}, block('bind-mount', {'source': 'same.conf', 'target': '/etc/app.conf', 'readOnly': True}))))
                workspace.write('same.conf', image)
                result = projects.save(identity, document, definitions)
                self.assertTrue(result['composeGenerated'])
                compose = read_yaml((workspace.root / 'compose.yaml').read_text())
                self.assertEqual(compose['services']['same-service']['image'], image)
                self.assertEqual(compose['services']['same-service']['volumes'][0]['source'], './files/same.conf')
            projects.delete(ids[0])
            remaining = projects.workspace(ids[1])
            self.assertEqual(remaining.read('same.conf'), 'busybox:latest')
            self.assertTrue((remaining.root / 'compose.yaml').exists())

    def test_incomplete_save_removes_stale_output_but_preserves_deployment(self):
        from test_core import block, registry, TEMPLATES
        import json
        with tempfile.TemporaryDirectory() as root:
            projects = Projects(Workspace(root))
            identity = projects.create('Example')['id']
            workspace = projects.workspace(identity)
            document = read_yaml((workspace.root / 'project.yaml').read_text())
            document['children'].append(block('service', {'name': 'worker'}, block('image', {'image': 'busybox'})))
            projects.save(identity, document, registry(TEMPLATES))
            (workspace.root / 'deployment.json').write_text(json.dumps({'name': 'example', 'endpoint': 'unix:///test'}))
            (workspace.root / 'compose.deployed.yaml').write_text('deployed snapshot')
            document['children'][-1]['children'][0]['values']['image'] = ''
            result = projects.save(identity, document, registry(TEMPLATES))
            self.assertFalse(result['composeGenerated'])
            self.assertFalse((workspace.root / 'compose.yaml').exists())
            self.assertEqual((workspace.root / 'compose.deployed.yaml').read_text(), 'deployed snapshot')
            document['children'][0]['values']['name'] = 'renamed'
            with self.assertRaisesRegex(Invalid, 'existing deployment'):
                projects.save(identity, document, registry(TEMPLATES))

    def test_duplicate_compose_name_is_rejected_without_overwriting(self):
        from test_core import registry, TEMPLATES
        with tempfile.TemporaryDirectory() as root:
            projects = Projects(Workspace(root))
            projects.create('First')
            second = projects.create('Second')['id']
            path = projects.workspace(second).root / 'project.yaml'
            original = path.read_text()
            document = read_yaml(original)
            document['children'][0]['values']['name'] = 'first'
            with self.assertRaisesRegex(Invalid, 'already assigned'):
                projects.save(second, document, registry(TEMPLATES))
            self.assertEqual(path.read_text(), original)
