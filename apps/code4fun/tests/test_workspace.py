import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'workspace'))
from server import Store, Conflict, validate_files


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store(self.directory.name)

    def test_stage_transitions_preserve_files_and_survive_restart(self):
        original = self.store.read()
        files = {**original['files'], 'index.html': '<h1>My own dashboard</h1>'}
        saved = self.store.save({'files': files, 'stage': 3, 'revision': original['revision']})
        self.assertEqual(saved['files'], files)
        self.assertEqual(Store(self.directory.name).read(), saved)
        self.assertNotEqual(original['revision'], saved['revision'])

    def test_stale_save_and_old_check_cannot_overwrite_new_work(self):
        original = self.store.read()
        self.store.save(original)
        with self.assertRaises(Conflict):
            self.store.save(original)
        self.assertFalse(self.store.complete(original['revision'], 0, [{'passed': True}]))
        self.assertFalse(self.store.read()['completed'])

    def test_snapshots_are_immutable_and_do_not_publish_management_state(self):
        files = self.store.read()['files']
        token = self.store.snapshot(files)
        files['index.html'] = 'changed'
        self.assertNotEqual(self.store.snapshot_file(token, 'index.html'), 'changed')
        self.assertIsNone(self.store.snapshot_file(token, '../project.json'))
        self.assertIsNone(self.store.snapshot_file('unknown', 'index.html'))

    def test_pass_records_history_and_reset_clears_it(self):
        state = self.store.read()
        self.assertTrue(self.store.complete(state['revision'], 0, [{'passed': True}]))
        self.assertIn('0', self.store.read()['completed'])
        self.store.complete(state['revision'], 1, [{'passed': False}])
        self.assertNotIn('1', self.store.read()['completed'])
        reset = self.store.save({'revision': state['revision']}, reset=True)
        self.assertEqual(reset['files'], self.store.starter())
        self.assertFalse(reset['completed'])

    def test_rejects_extra_paths_oversized_files_and_invalid_stages(self):
        state = self.store.read()
        for files in ({'../x': 'bad'}, {**state['files'], 'secret.txt': 'x'}, {**state['files'], 'script.js': 'a' * (128*1024+1)}):
            with self.assertRaises(ValueError):
                validate_files(files)
        for stage in (-1, 6, True, '1'):
            with self.assertRaises(ValueError):
                self.store.save({**state, 'stage': stage})
