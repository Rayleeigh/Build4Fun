"""Opt-in real lifecycle test. Creates and removes only a uniquely named test project."""
import argparse
import os
import shutil
import socket
import tempfile
import time
import uuid
from urllib.request import build_opener, ProxyHandler

from test_core import block, registry, TEMPLATES
from core import Invalid
from projects import Projects
from storage import Workspace
from revisions import Revisions
from docker_runtime import DockerRuntime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Allow pulling nginx and creating isolated Docker resources.')
    args = parser.parse_args()
    if not args.run:
        parser.error('Pass --run to explicitly enable Docker resource creation.')
    with tempfile.TemporaryDirectory(prefix='build4fun-lifecycle-') as directory:
        projects = Projects(Workspace(directory))
        identity = projects.create('b4f-test-' + uuid.uuid4().hex[:12])['id']
        workspace = projects.workspace(identity)
        definitions = registry(TEMPLATES)
        revisions = Revisions(projects, definitions)
        runtime = DockerRuntime(projects, definitions, os.environ.get('B4F_DOCKER', shutil.which('docker') or os.path.expanduser('~/.docker/bin/docker')))
        saved = revisions.read(identity)
        project = saved['project']
        with socket.socket() as available:
            available.bind(('127.0.0.1', 0))
            port = available.getsockname()[1]
        image = block('image', {'image': 'nginx:alpine'})
        mapping = block('port', {'published': port, 'target': 80, 'protocol': '', 'hostIp': '127.0.0.1'})
        project['children'].append(block('service', {'name': 'web'}, image, block('ports', {}, mapping),
            block('mounts', {}, block('volume-mount', {'source': 'data', 'target': '/data', 'readOnly': False}), block('bind-mount', {'source': 'site', 'target': '/usr/share/nginx/html', 'readOnly': True}))))
        project['children'].append(block('named-volume', {'name': 'data'}))
        volume_name = project['children'][0]['values']['name'] + '_data'
        volume_created = False
        saved = revisions.commit(identity, saved['revision'], project, {'site/index.html': 'Build4Fun original revision'})
        assert revisions.read(identity)['project'] == saved['project']
        opener = build_opener(ProxyHandler({}))
        def page():
            deadline = time.monotonic() + 30
            while True:
                try:
                    return opener.open(f'http://127.0.0.1:{port}', timeout=2).read().decode()
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(.2)
        try:
            runtime.execute(identity, 'validate')
            runtime.execute(identity, 'start')
            assert page() == 'Build4Fun original revision'
            volume_created = True
            runtime.compose(workspace, workspace.root / 'compose.deployed.yaml', project['children'][0]['values']['name'], ['exec', '-T', 'web', 'sh', '-c', 'printf retained > /data/marker'], runtime.endpoint(workspace))
            assert any(item['State'] == 'running' for item in runtime.execute(identity, 'status')['services'])
            runtime.execute(identity, 'logs')
            saved = revisions.commit(identity, saved['revision'], edits={'site/index.html': 'Build4Fun newer revision'})
            assert page() == 'Build4Fun original revision', 'Saved edits leaked into the deployed mount'
            runtime.execute(identity, 'stop')
            assert all(item['State'] != 'running' for item in runtime.execute(identity, 'status')['services'])
            runtime.execute(identity, 'start')
            assert page() == 'Build4Fun newer revision'
            assert runtime.compose(workspace, workspace.root / 'compose.deployed.yaml', project['children'][0]['values']['name'], ['exec', '-T', 'web', 'cat', '/data/marker'], runtime.endpoint(workspace)) == 'retained'
            runtime.execute(identity, 'remove')
            image['values']['image'] = 'nginx:build4fun-intentionally-missing-image'
            saved = revisions.commit(identity, saved['revision'], project)
            try:
                runtime.execute(identity, 'start')
            except Invalid as error:
                assert str(error)
            else:
                raise AssertionError('Missing image unexpectedly started')
            runtime.execute(identity, 'remove')
            image['values']['image'] = 'nginx:alpine'
            blocker_name = 'b4f-port-test-' + uuid.uuid4().hex[:12]
            endpoint = runtime.endpoint(workspace)
            blocker = runtime.run(['run', '-d', '--name', blocker_name, '-p', '127.0.0.1::80', 'nginx:alpine'], workspace.root, endpoint=endpoint).strip()
            try:
                published = runtime.run(['port', blocker, '80/tcp'], workspace.root, endpoint=endpoint).strip()
                mapping['values']['published'] = int(published.rsplit(':', 1)[1])
                saved = revisions.commit(identity, saved['revision'], project)
                try:
                    runtime.execute(identity, 'start')
                except Invalid as error:
                    assert str(error)
                else:
                    raise AssertionError('Occupied port unexpectedly started: ' + str(runtime.execute(identity, 'status')))
            finally:
                runtime.run(['rm', '-f', blocker], workspace.root, endpoint=endpoint)
        finally:
            if runtime.manifest(workspace):
                runtime.execute(identity, 'remove')
            if volume_created:
                runtime.run(['volume', 'rm', volume_name], workspace.root, endpoint=runtime.endpoint(workspace))
        print('Real Docker lifecycle, saved revision isolation, missing image and occupied port checks passed.')


if __name__ == '__main__':
    main()
