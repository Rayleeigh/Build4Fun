import copy
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'application'))
from core import Invalid, registry, compile_project, compose_yaml, read_yaml, check_structure
from storage import Workspace

TEMPLATES = Path(__file__).resolve().parents[1] / 'templates'


def block(kind, values=None, *children):
    return {'id': str(uuid.uuid4()), 'type': kind, 'version': 1, 'values': values or {}, 'children': list(children)}


def example():
    return block('harness', {},
                 block('project-name', {'name': 'dns-lab'}),
                 block('service', {'name': 'dns'},
                       block('image', {'image': 'example/dns:1'}),
                       block('ports', {},
                             block('port', {'published': '1053', 'target': '53', 'protocol': 'udp'})),
                       block('environment', {}, block('variable', {'key': 'VALUE', 'value': 'false: $HOME'})),
                       block('mounts', {}, block('bind-mount', {'source': 'config/dnsmasq.conf', 'target': '/etc/dnsmasq.conf', 'readOnly': True})),
                       block('network-configuration', {}, block('network-attachment', {'network': 'lab'}))),
                 block('external-network', {'name': 'lab', 'externalName': 'existing-lab'}))


class AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.definitions = registry(TEMPLATES)

    def test_nested_configuration(self):
        project = example()
        before = copy.deepcopy(project)
        result = compile_project(project, self.definitions)
        self.assertEqual(project, before)
        service = result['services']['dns']
        self.assertEqual(service['ports'], ['1053:53/udp'])
        self.assertEqual(service['environment']['VALUE'], 'false: $HOME')
        self.assertEqual(service['volumes'][0]['source'], './config/dnsmasq.conf')
        self.assertTrue(service['volumes'][0]['read_only'])
        self.assertEqual(service['networks'], {'lab': {}})
        self.assertEqual(result['networks']['lab'], {'external': True, 'name': 'existing-lab'})

    def test_serialization_preserves_literal_dollars_and_strings(self):
        result = read_yaml(compose_yaml(example(), self.definitions))
        self.assertEqual(result['services']['dns']['environment']['VALUE'], 'false: $$HOME')
        self.assertEqual(result['services']['dns']['ports'][0], '1053:53/udp')

    def test_unknown_reference(self):
        project = example()
        project['children'].pop()
        with self.assertRaisesRegex(Invalid, 'unknown networks reference'):
            compile_project(project, self.definitions)

    def test_duplicate_environment_key(self):
        project = example()
        env = project['children'][1]['children'][2]
        env['children'].append(block('variable', {'key': 'VALUE', 'value': 'different'}))
        with self.assertRaisesRegex(Invalid, 'Duplicate environment name'):
            compile_project(project, self.definitions)

    def test_rejects_invalid_nesting_and_duplicate_single_block(self):
        project = example()
        project['children'].append(block('image', {'image': 'anything'}))
        with self.assertRaisesRegex(Invalid, 'cannot be placed'):
            check_structure(project, self.definitions)
        project = example()
        project['children'].append(block('project-name', {'name': 'duplicate'}))
        with self.assertRaisesRegex(Invalid, 'Only one'):
            check_structure(project, self.definitions)

    def test_bad_port_and_duplicate_service(self):
        project = example()
        project['children'][1]['children'][1]['children'][0]['values']['published'] = '70000'
        with self.assertRaisesRegex(Invalid, 'outside the allowed range'):
            compile_project(project, self.definitions)
        project = example()
        project['children'].append(block('service', {'name': 'dns'}, block('image', {'image': 'other'})))
        with self.assertRaisesRegex(Invalid, 'Duplicate services name'):
            compile_project(project, self.definitions)

    def test_incomplete_project_can_be_saved_but_not_compiled(self):
        project = block('harness', {}, block('service'))
        check_structure(project, self.definitions)
        with self.assertRaises(Invalid):
            compile_project(project, self.definitions)

    def test_yaml_duplicate_keys_and_unsafe_tags(self):
        for text in ('name: one\nname: two', '!!python/object:builtins.object {}'):
            with self.subTest(text=text), self.assertRaises(Invalid):
                read_yaml(text)

    def test_block_versions_are_checked(self):
        project = example()
        project['version'] = 2
        with self.assertRaisesRegex(Invalid, 'version'):
            check_structure(project, self.definitions)

    def test_bind_source_cannot_escape(self):
        project = example()
        project['children'][1]['children'][3]['children'][0]['values']['source'] = '../outside'
        with self.assertRaisesRegex(Invalid, 'project-relative'):
            compile_project(project, self.definitions)

    def test_new_scalar_block_requires_only_a_definition(self):
        definitions = copy.deepcopy(self.definitions)
        definitions['restart'] = {'id': 'restart', 'version': 1, 'label': 'Restart', 'op': 'set', 'target': 'restart', 'inputs': [{'key': 'value', 'label': 'Policy', 'type': 'text'}], 'template': {'input': 'value'}}
        definitions['service']['children'].append('restart')
        project = example()
        project['children'][1]['children'].append(block('restart', {'value': 'unless-stopped'}))
        self.assertEqual(compile_project(project, definitions)['services']['dns']['restart'], 'unless-stopped')


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Workspace(Path(self.temporary.name) / 'workspace')

    def test_arbitrary_config_text_round_trips_unchanged(self):
        text = 'invalid yaml: [\ninvalid dnsmasq directive\n'
        self.workspace.write('config/service.yaml', text, create=True)
        self.assertEqual(self.workspace.read('config/service.yaml'), text)
        self.assertIn({'path': 'config/service.yaml', 'directory': False}, self.workspace.listing())

    def test_rejects_traversal_absolute_paths_and_symlinks(self):
        for path in ('../outside', '/tmp/outside', '.', ''):
            with self.subTest(path=path), self.assertRaises(Invalid):
                self.workspace.path(path)
        outside = Path(self.temporary.name) / 'outside'
        outside.mkdir()
        (self.workspace.files / 'link').symlink_to(outside)
        with self.assertRaises(Invalid):
            self.workspace.write('link/file', 'contents')

    def test_create_never_overwrites_existing_file(self):
        self.workspace.write('a.conf', 'original', create=True)
        with self.assertRaises(Invalid):
            self.workspace.write('a.conf', 'replacement', create=True)
        self.assertEqual(self.workspace.read('a.conf'), 'original')


if __name__ == '__main__':
    unittest.main()
