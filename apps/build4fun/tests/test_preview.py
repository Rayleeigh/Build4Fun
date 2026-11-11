"""Source-map checks for the educational Compose preview."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'application'))
from core import compose_preview, registry, read_yaml


class PreviewTests(unittest.TestCase):
    def test_ranges_correspond_to_nested_configuration(self):
        root = Path(__file__).resolve().parents[1]
        project = read_yaml((root / 'tests/fixtures/homelab/project.yaml').read_text())
        result = compose_preview(project, registry(root / 'templates'))
        lines = result['yaml'].splitlines()
        service = project['children'][1]
        image, ports, env, mounts, networks = service['children']
        def excerpt(node):
            r = result['blocks'][node['id']]
            return '\n'.join(lines[r['start'] - 1:r['end']])
        self.assertIn('nginx:latest', excerpt(image))
        self.assertNotIn('ports:', excerpt(image))
        self.assertIn('8080', excerpt(ports['children'][0]))
        self.assertNotIn('NGINX_HOST', excerpt(ports['children'][0]))
        self.assertIn('NGINX_PORT', excerpt(env['children'][1]))
        self.assertNotIn('NGINX_HOST', excerpt(env['children'][1]))
        self.assertIn('/usr/share/nginx/html', excerpt(mounts['children'][0]))
        self.assertIn('frontend', excerpt(networks['children'][0]))
        self.assertIn('nginx:', excerpt(service))
        self.assertNotIn('name: homelab', excerpt(service))
        self.assertEqual(excerpt(project), result['yaml'].rstrip())


if __name__ == '__main__':
    unittest.main()
