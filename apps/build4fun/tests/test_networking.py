import copy
import unittest
from pathlib import Path

from test_core import block, example
from core import Invalid, compile_project, compose_yaml, compose_preview, registry, read_yaml


class NetworkingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.definitions = registry(Path(__file__).resolve().parents[1] / 'templates')

    def managed_project(self):
        project = example()
        project['children'][-1] = block('network', {'name': 'lab', 'subnet': '172.25.0.0/24', 'gateway': '172.25.0.1'})
        attachment = project['children'][1]['children'][4]['children'][0]
        attachment['values']['ipv4Address'] = '172.25.0.10'
        return project

    def test_optional_protocol_omits_suffix_and_quotes_short_port(self):
        for value in ('', None):
            project = example()
            project['children'][1]['children'][1]['children'][0]['values']['protocol'] = value
            text = compose_yaml(project, self.definitions)
            self.assertIn('- "1053:53"', text)
            self.assertNotIn('protocol:', text)
            self.assertEqual(read_yaml(text)['services']['dns']['ports'], ['1053:53'])

    def test_missing_optional_fields_support_existing_saved_blocks(self):
        project = example()
        project['children'][1]['children'][1]['children'][0]['values'].pop('protocol')
        result = compile_project(project, self.definitions)
        self.assertEqual(result['services']['dns']['ports'], ['1053:53'])
        self.assertEqual(result['services']['dns']['networks']['lab'], {})

    def test_explicit_protocol_and_host_ip(self):
        for host, expected in [('127.0.0.1', '127.0.0.1:1053:53/udp'), ('::1', '[::1]:1053:53/udp')]:
            project = example()
            port = project['children'][1]['children'][1]['children'][0]
            port['values']['hostIp'] = host
            result = compile_project(project, self.definitions)
            self.assertEqual(result['services']['dns']['ports'], [expected])
        port['values']['hostIp'] = 'not-an-ip'
        with self.assertRaisesRegex(Invalid, 'Host IP'):
            compile_project(project, self.definitions)

    def test_top_level_and_service_order_do_not_follow_block_creation(self):
        project = self.managed_project()
        project['children'].append(block('named-volume', {'name': 'data'}))
        original = compose_yaml(project, self.definitions)
        project['children'].reverse()
        service = next(n for n in project['children'] if n['type'] == 'service')
        service['children'].reverse()
        result = compile_project(project, self.definitions)
        self.assertEqual(list(result), ['name', 'services', 'networks', 'volumes'])
        self.assertEqual(list(result['services']['dns']), ['image', 'ports', 'environment', 'volumes', 'networks'])
        self.assertEqual(compose_yaml(project, self.definitions), original)
        mapped = compose_preview(project, self.definitions)
        name = next(n for n in project['children'] if n['type'] == 'project-name')
        self.assertEqual(mapped['blocks'][name['id']], {'start': 1, 'end': 1})

    def test_managed_network_ipam_and_static_ip(self):
        result = compile_project(self.managed_project(), self.definitions)
        self.assertEqual(result['networks']['lab'], {'ipam': {'config': [{'subnet': '172.25.0.0/24', 'gateway': '172.25.0.1'}]}})
        self.assertEqual(result['services']['dns']['networks']['lab'], {'ipv4_address': '172.25.0.10'})

    def test_plain_project_network_has_no_empty_ipam(self):
        project = example()
        project['children'][-1] = block('network', {'name': 'lab'})
        self.assertEqual(compile_project(project, self.definitions)['networks']['lab'], {})

    def test_invalid_static_ips_are_rejected(self):
        for address in ('172.26.0.10', '172.25.0.0', '172.25.0.255', '172.25.0.1', 'bad'):
            project = self.managed_project()
            project['children'][1]['children'][4]['children'][0]['values']['ipv4Address'] = address
            with self.subTest(address=address), self.assertRaises(Invalid):
                compile_project(project, self.definitions)

    def test_missing_subnet_and_bad_gateway_are_rejected(self):
        for values in ({'name': 'lab'}, {'name': 'lab', 'gateway': '172.25.0.1'}, {'name': 'lab', 'subnet': '172.25.0.0/24', 'gateway': '172.26.0.1'}):
            project = self.managed_project()
            project['children'][-1]['values'] = values
            with self.subTest(values=values), self.assertRaises(Invalid):
                compile_project(project, self.definitions)

    def test_external_network_keeps_ipam_out_of_compose(self):
        project = example()
        project['children'][1]['children'][4]['children'][0]['values']['ipv4Address'] = '172.25.0.10'
        result = compile_project(project, self.definitions)
        self.assertEqual(result['networks']['lab'], {'external': True, 'name': 'existing-lab'})
        self.assertEqual(result['services']['dns']['networks']['lab']['ipv4_address'], '172.25.0.10')

    def test_duplicate_static_address_on_same_network_is_rejected(self):
        project = self.managed_project()
        service = copy.deepcopy(project['children'][1])
        def assign_ids(node):
            node['id'] += '-copy'
            for child in node['children']:
                assign_ids(child)
        assign_ids(service)
        service['values']['name'] = 'other'
        project['children'].append(service)
        with self.assertRaisesRegex(Invalid, 'duplicate static IP'):
            compile_project(project, self.definitions)


if __name__ == '__main__':
    unittest.main()
