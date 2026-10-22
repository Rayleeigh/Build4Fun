"""Smoke-test a built image without exposing a port or mounting the Docker socket."""
import argparse
import os
import shutil
import subprocess

CHECK = '''
import json, os, sys, tempfile, threading, urllib.request, urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, '/app/src/application')
from server import make_handler
from storage import Workspace
from core import registry
with tempfile.TemporaryDirectory() as directory:
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(Workspace(directory), registry(Path('/app/src/templates'))))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = 'http://127.0.0.1:' + str(server.server_port)
        assert urllib.request.urlopen(base).status == 200
        assert json.load(urllib.request.urlopen(base + '/api/projects')) == []
        assert 'service' in json.load(urllib.request.urlopen(base + '/api/definitions'))
        # Docker can publish a different host port from the server's internal port.
        os.environ['B4F_PUBLIC_PORT'] = '18081'
        request = urllib.request.Request(base + '/api/projects', headers={
            'Host': 'localhost:18081', 'Origin': 'http://localhost:18081'})
        assert json.load(urllib.request.urlopen(request)) == []
        for headers in ({'Host': 'untrusted.example:18081'},
                        {'Host': 'localhost:18081', 'Origin': 'https://untrusted.example'}):
            try:
                urllib.request.urlopen(urllib.request.Request(base, headers=headers))
                raise AssertionError('Untrusted host or origin was accepted')
            except urllib.error.HTTPError as error:
                assert error.code == 403

    finally:
        server.shutdown()
        server.server_close()
print('Container HTTP startup and empty landing passed.')
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', default='build4fun-local-check')
    args = parser.parse_args()
    docker = os.environ.get('B4F_DOCKER', shutil.which('docker') or os.path.expanduser('~/.docker/bin/docker'))
    for command in (['docker', 'compose', 'version'], ['python', '-c', CHECK]):
        subprocess.run([docker, 'run', '--rm', args.image] + command, check=True, timeout=60)


if __name__ == '__main__':
    main()
