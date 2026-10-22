import copy
from pathlib import Path
import tempfile
import unittest
from test_core import block, registry, TEMPLATES, read_yaml
from storage import Workspace
from projects import Projects
from challenges import evaluate, progress, DOCS, load_catalog
from core import Invalid


class ChallengeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Workspace(self.temp.name)
        self.compose = {
            'services': {
                'web': {'image': 'nginx:alpine', 'ports': ['127.0.0.1:8081:80/tcp'],
                        'networks': {'backend': {}},
                        'volumes': [{'type': 'bind', 'source': './index.html', 'target': '/usr/share/nginx/html/index.html', 'read_only': True}]},
                'cache': {'image': 'redis:7-alpine', 'environment': {'APP_MODE': 'training'},
                          'networks': {'backend': {}},
                          'volumes': [{'type': 'volume', 'source': 'cache-data', 'target': '/data'}]}},
            'volumes': {'cache-data': {}}, 'networks': {'backend': {}}}
        self.workspace.write('index.html', '<h1>Build4Fun apprentice</h1>')

    def test_all_solutions_and_empty_project(self):
        checks = evaluate(self.compose, self.workspace)
        self.assertTrue(all(all(values) for values in checks.values()))
        self.assertEqual(set(checks), {c['id'] for c in load_catalog()})
        self.assertFalse(any(all(values) for values in evaluate({}, self.workspace).values()))

    def test_near_misses_fail(self):
        cases = [
            ('publish-web', lambda c: c['services']['web'].update(ports=['8081:80/tcp'])),
            ('publish-web', lambda c: c['services']['web'].update(ports=['127.0.0.1:8081:80/udp'])),
            ('environment', lambda c: c['services']['cache']['environment'].update(APP_MODE='production')),
            ('persistent-cache', lambda c: c['services']['cache']['volumes'][0].update(read_only=True)),
            ('persistent-cache', lambda c: c.update(volumes={})),
            ('custom-page', lambda c: c['services']['web']['volumes'][0].update(read_only=False)),
            ('private-network', lambda c: c['services']['cache'].update(ports=['6379:6379'])),
            ('private-network', lambda c: c['services']['cache'].update(networks={})),
        ]
        for challenge, mutate in cases:
            with self.subTest(challenge=challenge):
                compose = copy.deepcopy(self.compose); mutate(compose)
                self.assertFalse(all(evaluate(compose, self.workspace)[challenge]))
        self.workspace.delete('index.html')
        self.assertFalse(all(evaluate(self.compose, self.workspace)['custom-page']))

    def test_saved_projects_are_rechecked_and_incomplete_projects_isolated(self):
        projects = Projects(self.workspace)
        good = projects.create('Working')['id']
        bad = projects.create('Incomplete')['id']
        definitions = registry(TEMPLATES)
        workspace = projects.workspace(good)
        document = read_yaml(workspace.project_path.read_text())
        document['children'].append(block('service', {'name': 'web'}, block('image', {'image': 'nginx:alpine'}),
            block('ports', {}, block('port', {'published': '8081', 'target': '80', 'hostIp': '127.0.0.1', 'protocol': 'tcp'})),
            block('mounts', {}, block('bind-mount', {'source': 'index.html', 'target': '/usr/share/nginx/html/index.html', 'readOnly': True}))))
        workspace.write('index.html', '<h1>Build4Fun apprentice</h1>')
        projects.save(good, document, definitions)
        bad_path = projects.workspace(bad).project_path
        original_bad = bad_path.read_text()
        bad_path.write_text('broken: [')
        result = progress(projects, definitions)
        working = next(p for p in result['projects'] if p['id'] == good)
        self.assertTrue(all(working['checks']['publish-web']))
        self.assertTrue(all(working['checks']['custom-page']))
        self.assertTrue(next(p for p in result['projects'] if p['id'] == bad)['error'])
        bad_path.write_text(original_bad)
        document['children'][-1]['children'][0]['values']['image'] = 'httpd:alpine'
        projects.save(good, document, definitions)
        working = next(p for p in progress(projects, definitions)['projects'] if p['id'] == good)
        self.assertFalse(all(working['checks']['first-service']))

    def test_markdown_discovery_editing_and_custom_check(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'new-lesson.md'
            lesson = """---
checks:
  - label: Custom image
    all:
      - path: [services, worker, image]
        equals: busybox:latest
---
# 07. New lesson

Level: Beginner

Create a worker.

## Build

1. Add the worker.

## Explain

What is an image?

## Try it

Inspect its logs.
"""
            path.write_text(lesson)
            catalog = load_catalog(directory)
            self.assertEqual(catalog[0]['title'], 'New lesson')
            self.assertEqual(catalog[0]['steps'], ['Add the worker.'])
            self.assertTrue(evaluate({'services': {'worker': {'image': 'busybox:latest'}}}, self.workspace, catalog)['new-lesson'][0])
            self.assertFalse(evaluate({}, self.workspace, catalog)['new-lesson'][0])
            path.write_text(lesson.replace('New lesson', 'Edited lesson'))
            self.assertEqual(load_catalog(directory)[0]['title'], 'Edited lesson')
            path.unlink()
            self.assertEqual(load_catalog(directory), [])
            path.write_text(lesson.replace('equals:', 'unknown:'))
            with self.assertRaisesRegex(Invalid, 'new-lesson.md'):
                load_catalog(directory)

    def test_rejects_unsafe_file_rules_and_empty_checks(self):
        from challenges import validate_rule
        for rule in ({'file': '../secret', 'contains': 'x'}, {'path': ['services'], 'empty': 'false'}, {'execute': 'anything'}):
            with self.subTest(rule=rule), self.assertRaises(ValueError):
                validate_rule(rule)
