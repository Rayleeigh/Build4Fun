import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from manager import Manager, parse_ps
from catalog import APPS
from server import handler
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.manager = Manager(self.temp.name, Path(self.temp.name)/'state')

    def test_registry_removes_builds_and_maps_every_service(self):
        for app, target in APPS.items():
            config = {'services': {service: {'build': {'context': '/repo'}, 'environment': {'KEEP': 'yes'}, 'volumes': ['work:/workspace']} for service in target['images']}}
            with patch.object(self.manager, 'config', return_value=config): result = self.manager.registry_config(app, 'v1.2.3')
            for service, suffix in target['images'].items():
                item = result['services'][service]
                self.assertNotIn('build', item)
                self.assertEqual(item['image'], 'ghcr.io/rayleeigh/build4fun'+('/'+suffix if suffix else '')+':v1.2.3')
                self.assertEqual(item['environment'], {'KEEP': 'yes'})
                self.assertEqual(item['volumes'], ['work:/workspace'])

    def test_actions_reject_paths_commands_invalid_tags_and_conflicts(self):
        for args in [('other','start'),('build4fun','rm'),('build4fun','start','shell'),('build4fun','start','registry','x;touch /tmp/bad')]:
            with self.assertRaises(ValueError): self.manager.launch(*args)
        self.manager.jobs['build4fun'] = {'running': True}
        with self.assertRaises(ValueError): self.manager.launch('build4fun','start')

    def test_registry_and_local_use_distinct_commands(self):
        for source in ('local','registry'):
            job={'source':source,'action':'start','tag':'latest','log':'','running':True}
            with patch.object(self.manager,'run_command') as command, patch.object(self.manager,'registry_config',return_value={'services':{}}):
                self.manager.run('code4fun',job)
            calls=[call.args[0] for call in command.call_args_list]
            self.assertEqual(job['exit_code'],0)
            if source=='local': self.assertIn('--build',calls[0]);self.assertEqual(len(calls),1)
            else:
                self.assertEqual(calls[0][-1],'pull');self.assertIn('--no-build',calls[1])
                self.assertEqual(len(calls),2)

    def test_stop_preserves_volumes_and_records_failures(self):
        job={'source':'local','action':'stop','log':'','running':True}
        with patch.object(self.manager,'run_command',side_effect=RuntimeError('failure')) as command:self.manager.run('crack4fun',job)
        self.assertIn('stop',command.call_args.args[0]);self.assertNotIn('down',command.call_args.args[0]);self.assertNotIn('--volumes',command.call_args.args[0])
        self.assertEqual(job['exit_code'],1);self.assertFalse(job['running']);self.assertIn('failure',job['log'])

    def test_compose_ps_formats(self):
        self.assertEqual(parse_ps(''),[])
        self.assertEqual(parse_ps('[{"State":"running"}]'),[{'State':'running'}])
        self.assertEqual(len(parse_ps('{"State":"running"}\n{"State":"exited"}')),2)

    def test_http_restricts_cross_origin_and_host(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.manager,0));port=server.server_port
        server.RequestHandlerClass=handler(self.manager,port)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base=f'http://127.0.0.1:{port}'
        with urlopen(base+'/api/state') as response:self.assertEqual(response.status,200)
        for request in [Request(base+'/api/state',headers={'Host':'evil.example'}),Request(base+'/api/action',data=b'{}',headers={'Origin':'http://evil.example'})]:
            with self.assertRaises(HTTPError) as error:urlopen(request)
            self.assertEqual(error.exception.code,403)
        with self.assertRaises(HTTPError) as error:urlopen(Request(base+'/api/action',data=b'{"app":"wrong","action":"start"}',headers={'Origin':base}))
        self.assertEqual(error.exception.code,400)


if __name__=='__main__':unittest.main()
