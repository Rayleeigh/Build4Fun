import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'workspace'))
from server import Store, Conflict, validate_files, LEGACY_STARTER, PREVIEWLESS_STARTERS


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store(self.directory.name)

    def test_untouched_original_starter_upgrades_once_and_preserves_preferences(self):
        state = self.store.read()
        state.update(files=dict(LEGACY_STARTER), tutorial_seen=True)
        self.store.write(state)
        upgraded = Store(self.directory.name).read()
        self.assertEqual(upgraded['files'], self.store.starter())
        self.assertIn('\n  <head>\n    <meta', upgraded['files']['index.html'])
        self.assertNotEqual(upgraded['revision'], state['revision'])
        self.assertTrue(upgraded['tutorial_seen'])
        self.assertEqual(Store(self.directory.name).read(), upgraded)

    def test_both_empty_starters_upgrade_to_visible_content(self):
        for files in PREVIEWLESS_STARTERS:
            state = {**self.store.read(), 'files': files, 'stage': 0, 'completed': {}}
            self.store.write(state)
            updated = Store(self.directory.name).read()
            self.assertIn('id="starter-message"', updated['files']['index.html'])
            self.assertEqual(updated['files'], self.store.starter())

    def test_starter_upgrade_preserves_edits_and_progress(self):
        for field, value in [('files', {**LEGACY_STARTER, 'style.css': 'body { color: red; }'}),
                             ('stage', 1), ('completed', {'0': {'checked_at': 123}})]:
            state = {**self.store.read(), 'files': dict(LEGACY_STARTER), 'stage': 0, 'completed': {}, field: value}
            self.store.write(state)
            self.assertEqual(Store(self.directory.name).read(), state)

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

    def test_tutorial_preference_survives_restart_save_and_reset_without_changing_revision(self):
        original = self.store.read()
        self.store.finish_tutorial()
        updated = Store(self.directory.name).read()
        self.assertTrue(updated['tutorial_seen'])
        self.assertEqual(updated['revision'], original['revision'])
        self.assertEqual(updated['files'], original['files'])
        saved = self.store.save(original)
        self.assertTrue(saved['tutorial_seen'])
        reset = self.store.save({'revision': saved['revision']}, reset=True)
        self.assertTrue(reset['tutorial_seen'])

    def test_rejects_extra_paths_oversized_files_and_invalid_stages(self):
        state = self.store.read()
        for files in ({'../x': 'bad'}, {**state['files'], 'secret.txt': 'x'}, {**state['files'], 'script.js': 'a' * (128*1024+1)}):
            with self.assertRaises(ValueError):
                validate_files(files)
        for stage in (-1, 6, True, '1'):
            with self.assertRaises(ValueError):
                self.store.save({**state, 'stage': stage})
