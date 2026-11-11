"""Regression coverage for atomic saves, conflicting tabs and recovery."""
import tempfile
import unittest
from unittest.mock import patch

from test_core import registry, TEMPLATES, block
from storage import Workspace
from projects import Projects
from revisions import Revisions, Conflict
from docker_runtime import DockerRuntime
from core import read_yaml


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projects = Projects(Workspace(self.temp.name))
        self.identity = self.projects.create('Revision test')['id']
        self.workspace = self.projects.workspace(self.identity)
        self.revisions = Revisions(self.projects, registry(TEMPLATES))

    def test_failed_file_write_does_not_publish_partial_save(self):
        before = self.revisions.read(self.identity)
        with self.assertRaises(Exception):
            self.revisions.commit(self.identity, before['revision'], edits={'first.conf': 'saved?', '../outside': 'no'})
        self.assertEqual(self.revisions.read(self.identity), before)
        self.assertFalse(self.workspace.path('first.conf').exists())

    def test_stale_tab_cannot_overwrite_saved_files(self):
        before = self.revisions.read(self.identity)
        saved = self.revisions.commit(self.identity, before['revision'], edits={'app.conf': 'first tab'})
        with self.assertRaises(Conflict):
            self.revisions.commit(self.identity, before['revision'], edits={'app.conf': 'second tab'})
        self.assertEqual(self.workspace.read('app.conf'), 'first tab')
        self.assertEqual(self.revisions.read(self.identity)['revision'], saved['revision'])

    def test_restore_replaces_files_and_keeps_history(self):
        before = self.revisions.read(self.identity)
        saved = self.revisions.commit(self.identity, before['revision'], edits={'app.conf': 'old'})
        revision = self.workspace.data_root.name
        newer = self.revisions.commit(self.identity, saved['revision'], edits={'app.conf': 'new', 'extra.conf': 'new'})
        self.revisions.restore(self.identity, newer['revision'], revision)
        self.assertEqual(self.workspace.read('app.conf'), 'old')
        self.assertFalse(self.workspace.path('extra.conf').exists())
        self.assertIn(revision, self.revisions.history(self.identity))

    def test_restore_detects_external_edit_before_publish(self):
        before = self.revisions.read(self.identity)
        saved = self.revisions.commit(self.identity, before['revision'])
        revision = self.workspace.data_root.name
        save = self.projects.save
        def changed(*args, **kwargs):
            result = save(*args, **kwargs)
            self.workspace.write('external.conf', 'external change')
            return result
        with patch.object(self.projects, 'save', side_effect=changed), self.assertRaises(Conflict):
            self.revisions.restore(self.identity, saved['revision'], revision)
        self.assertEqual(self.workspace.data_root.name, revision)

    def test_start_uses_saved_model_and_isolates_config_files(self):
        before = self.revisions.read(self.identity)
        project = before['project']
        project['children'].append(block('service', {'name': 'worker'}, block('image', {'image': 'busybox:latest'}), block('mounts', {}, block('bind-mount', {'source': 'app.conf', 'target': '/app.conf', 'readOnly': True}))))
        saved = self.revisions.commit(self.identity, before['revision'], project, {'app.conf': 'original'})
        runtime = DockerRuntime(self.projects, self.revisions.definitions)
        def run(args, *a, **kw):
            return 'unix:///test.sock' if args[:2] == ['context', 'inspect'] else ''
        with patch.object(runtime, 'run', side_effect=run):
            runtime.execute(self.identity, 'start')
        deployed = read_yaml((self.workspace.root / 'compose.deployed.yaml').read_text())
        from pathlib import Path
        mounted = Path(deployed['services']['worker']['volumes'][0]['source'])
        self.revisions.commit(self.identity, saved['revision'], edits={'app.conf': 'new'})
        self.assertEqual(mounted.read_text(), 'original')
        self.assertEqual(runtime.manifest(self.workspace)['revision'], saved['revision'])
        self.assertEqual(self.workspace.read('app.conf'), 'new')

    def test_export_keeps_relative_paths_and_raw_configuration(self):
        import io
        import zipfile
        from export import project_bundle
        before = self.revisions.read(self.identity)
        project = before['project']
        project['children'].append(block('service', {'name': 'worker'}, block('image', {'image': 'busybox:latest'}), block('mounts', {}, block('bind-mount', {'source': 'app.conf', 'target': '/app.conf', 'readOnly': True}))))
        self.revisions.commit(self.identity, before['revision'], project, {'app.conf': 'not valid config'})
        with zipfile.ZipFile(io.BytesIO(project_bundle(self.workspace))) as archive:
            document = read_yaml(archive.read('compose.yaml').decode())
            self.assertEqual(document['services']['worker']['volumes'][0]['source'], './files/app.conf')
            self.assertEqual(archive.read('files/app.conf'), b'not valid config')
            self.assertIn('README.txt', archive.namelist())
            self.assertNotIn('deployment.json', archive.namelist())

    def test_file_rename_keeps_identity_and_updates_mount(self):
        before = self.revisions.read(self.identity)
        project = before['project']
        mount = block('bind-mount', {'source': 'config/app.conf', 'target': '/app.conf', 'readOnly': True})
        project['children'].append(block('service', {'name': 'worker'}, block('image', {'image': 'busybox:latest'}), block('mounts', {}, mount)))
        saved = self.revisions.commit(self.identity, before['revision'], project, {'config/app.conf': 'arbitrary text'})
        from references import walk
        saved_mount = next(n for n in walk(saved['project']) if n['id'] == mount['id'])
        identity = saved_mount['references']['source']
        renamed = self.revisions.commit(self.identity, saved['revision'], operation={'kind': 'rename', 'path': 'config', 'destination': 'settings'})
        self.assertEqual(renamed['project']['fileReferences'][identity], 'settings/app.conf')
        changed = next(n for n in walk(renamed['project']) if n['id'] == mount['id'])
        self.assertEqual(changed['values']['source'], 'settings/app.conf')
        self.assertEqual(changed['references']['source'], identity)
        self.assertEqual(self.workspace.read('settings/app.conf'), 'arbitrary text')

    def test_resource_rename_keeps_identity_and_deletion_is_reported(self):
        from core import compile_project, Invalid
        before = self.revisions.read(self.identity)
        project = before['project']
        project['children'].append(block('named-volume', {'name': 'data'}))
        project['children'].append(block('service', {'name': 'worker'}, block('image', {'image': 'busybox:latest'}), block('mounts', {}, block('volume-mount', {'source': 'data', 'target': '/data', 'readOnly': False}))))
        saved = self.revisions.commit(self.identity, before['revision'], project)
        project = saved['project']
        project['children'][1]['values']['name'] = 'renamed'
        document = compile_project(project, self.revisions.definitions)
        self.assertEqual(document['services']['worker']['volumes'][0]['source'], 'renamed')
        project['children'].pop(1)
        with self.assertRaises(Invalid) as caught:
            compile_project(project, self.revisions.definitions)
        self.assertEqual(caught.exception.issue['code'], 'missing_reference')
        self.assertIsNotNone(caught.exception.issue['blockId'])
