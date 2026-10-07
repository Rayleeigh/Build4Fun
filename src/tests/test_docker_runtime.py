import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_core import block, registry, TEMPLATES, Invalid, read_yaml
from storage import Workspace, atomic_write
from projects import Projects
from docker_runtime import DockerRuntime, OWNER
import yaml


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projects = Projects(Workspace(self.temp.name))
        self.project = self.projects.create('Test runtime')
        self.workspace = self.projects.workspace(self.project['id'])
        self.runtime = DockerRuntime(self.projects, registry(TEMPLATES))
        self.document = read_yaml((self.workspace.root / 'project.yaml').read_text())
        self.document['children'].append(block('service', {'name': 'worker'}, block('image', {'image': 'busybox:latest'})))
        atomic_write(self.workspace.root / 'project.yaml', yaml.safe_dump(self.document))
        self.calls = []

    def fake(self, args, cwd, timeout=30, endpoint=None):
        self.calls.append((args, endpoint))
        if args[:2] == ['context', 'inspect']:
            return 'unix:///test.sock\n'
        if '--format' in args and 'json' in args:
            return json.dumps({'Service': 'worker', 'State': 'running', 'Name': 'test-runtime-worker-1'})
        return ''

    def test_lifecycle_snapshot_name_lock_and_delete_guard(self):
        with patch.object(self.runtime, 'run', side_effect=self.fake):
            self.runtime.execute(self.project['id'], 'start')
            self.assertTrue((self.workspace.root / 'deployment.json').exists())
            with self.assertRaises(Invalid):
                self.projects.delete(self.project['id'])
            self.document['children'][0]['values']['name'] = 'changed'
            with self.assertRaisesRegex(Invalid, 'Remove the existing deployment'):
                self.runtime.execute(self.project['id'], 'validate', self.document)
            result = self.runtime.execute(self.project['id'], 'status')
            self.assertEqual(result['services'][0]['State'], 'running')
            self.runtime.execute(self.project['id'], 'stop')
            self.runtime.execute(self.project['id'], 'logs')
            self.runtime.execute(self.project['id'], 'remove')
            self.assertFalse((self.workspace.root / 'deployment.json').exists())
            self.assertTrue(all('--volumes' not in args and '-v' not in args for args, _ in self.calls))
            self.assertTrue(any(args[-3:] == ['stop', '--timeout', '10'] for args, _ in self.calls))
            self.assertTrue(all(endpoint == 'unix:///test.sock' for args, endpoint in self.calls if 'stop' in args))

    def test_validation_does_not_deploy_and_uses_explicit_paths(self):
        with patch.object(self.runtime, 'run', side_effect=self.fake):
            self.runtime.execute(self.project['id'], 'validate', self.document)
        self.assertFalse((self.workspace.root / 'deployment.json').exists())
        args = self.calls[-1][0]
        self.assertEqual(args[-2:], ['config', '--quiet'])
        self.assertIn('--env-file', args)
        self.assertIn(str(self.workspace.files), args)

    def test_bind_mount_mapping_missing_file_symlink_and_raw_contents(self):
        service = self.document['children'][-1]
        service['children'].append(block('mounts', {}, block('bind-mount', {'source': 'config/app.conf', 'target': '/etc/app.conf', 'readOnly': True})))
        with self.assertRaisesRegex(Invalid, 'does not exist'):
            self.runtime.prepare(self.workspace, self.document)
        self.workspace.write('config/app.conf', 'INVALID CONFIGURATION')
        self.runtime.host_workspace = Path('/host/workspace')
        prepared = self.runtime.prepare(self.workspace, self.document)
        source = prepared['services']['worker']['volumes'][0]['source']
        self.assertEqual(source, '/host/workspace/projects/'+self.project['id']+'/files/config/app.conf')
        self.assertEqual(self.workspace.read('config/app.conf'), 'INVALID CONFIGURATION')
        self.workspace.path('config/app.conf').unlink()
        self.workspace.path('config/app.conf').symlink_to('/etc/hosts')
        with self.assertRaises(Invalid):
            self.runtime.prepare(self.workspace, self.document)

    def test_foreign_containers_block_start(self):
        def foreign(args, cwd, timeout=30, endpoint=None):
            if args[0] == 'ps':
                return 'foreign-id'
            if args[0] == 'inspect':
                return '[{"Config":{"Labels":{}}}]'
            return self.fake(args, cwd, timeout, endpoint)
        with patch.object(self.runtime, 'run', side_effect=foreign), self.assertRaisesRegex(Invalid, 'outside this workspace'):
            self.runtime.execute(self.project['id'], 'start')
        self.assertFalse((self.workspace.root / 'deployment.json').exists())

    def test_partial_start_retains_manifest(self):
        def fail(args, cwd, timeout=30, endpoint=None):
            if 'up' in args:
                raise Invalid('image not found')
            return self.fake(args, cwd, timeout, endpoint)
        with patch.object(self.runtime, 'run', side_effect=fail), self.assertRaisesRegex(Invalid, 'image not found'):
            self.runtime.execute(self.project['id'], 'start')
        self.assertTrue((self.workspace.root / 'deployment.json').exists())

    def test_missing_cli_and_timeout_are_actionable(self):
        with patch('docker_runtime.subprocess.run', side_effect=FileNotFoundError()), self.assertRaisesRegex(Invalid, 'Docker CLI was not found'):
            self.runtime.run(['compose', 'version'], self.workspace.root)
        with patch('docker_runtime.subprocess.run', side_effect=subprocess.TimeoutExpired('docker', 30)), self.assertRaisesRegex(Invalid, 'partially completed'):
            self.runtime.run(['compose', 'version'], self.workspace.root)

    def test_foreign_volume_is_not_adopted_and_external_network_is_not_owned(self):
        self.document['children'].append(block('named-volume', {'name': 'data'}))
        self.document['children'].append(block('external-network', {'name': 'outside', 'externalName': 'existing'}))
        prepared = self.runtime.prepare(self.workspace, self.document)
        self.assertNotIn('labels', prepared['networks']['outside'])
        def foreign(args, cwd, timeout=30, endpoint=None):
            if args[:2] == ['volume', 'ls']:
                return 'test-runtime_data\n'
            if args[:2] == ['volume', 'inspect']:
                return '[{"Labels":null}]'
            return self.fake(args, cwd, timeout, endpoint)
        with patch.object(self.runtime, 'run', side_effect=foreign), self.assertRaisesRegex(Invalid, 'outside this workspace'):
            self.runtime.check_ownership(self.workspace, prepared, 'unix:///test.sock')

    def test_deployed_name_reserved_for_other_workspace(self):
        other = self.projects.create('Other')
        other_workspace = self.projects.workspace(other['id'])
        atomic_write(other_workspace.root / 'deployment.json', json.dumps({'name': 'test-runtime', 'endpoint': 'unix:///test.sock'}))
        with patch.object(self.runtime, 'run', side_effect=self.fake), self.assertRaisesRegex(Invalid, 'another managed deployment'):
            self.runtime.execute(self.project['id'], 'start')
        self.assertFalse((self.workspace.root / 'deployment.json').exists())

    def test_two_deployments_use_separate_snapshots_and_control_arguments(self):
        other = self.projects.create('Other')
        other_workspace = self.projects.workspace(other['id'])
        document = read_yaml((other_workspace.root / 'project.yaml').read_text())
        document['children'].append(block('service', {'name': 'worker'}, block('image', {'image': 'nginx:alpine'})))
        self.projects.save(other['id'], document, self.runtime.definitions)
        with patch.object(self.runtime, 'run', side_effect=self.fake):
            self.runtime.execute(self.project['id'], 'start')
            self.runtime.execute(other['id'], 'start')
            self.runtime.execute(self.project['id'], 'stop')
            stop_args = self.calls[-1][0]
            self.assertEqual(stop_args[stop_args.index('-p') + 1], 'test-runtime')
            self.assertEqual(stop_args[stop_args.index('-f') + 1], str(self.workspace.root / 'compose.deployed.yaml'))
            self.runtime.execute(self.project['id'], 'remove')
        self.assertIsNotNone(self.runtime.manifest(other_workspace))
        snapshot = read_yaml((other_workspace.root / 'compose.deployed.yaml').read_text())
        self.assertEqual(snapshot['services']['worker']['image'], 'nginx:alpine')
        self.assertNotEqual(self.runtime.owner(self.workspace), self.runtime.owner(other_workspace))
