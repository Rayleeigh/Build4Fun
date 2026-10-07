"""Execute only generated, workspace-owned Compose deployments on a local Engine."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import uuid

import yaml
from core import Invalid, compose_yaml, read_yaml
from storage import Workspace, atomic_write
from revisions import copy_files, fingerprint
from references import normalize, walk

OWNER = 'io.build4fun.workspace'


class DockerRuntime:
    def __init__(self, projects, definitions, docker='docker', host_workspace=None):
        self.projects, self.definitions, self.docker = projects, definitions, docker
        if host_workspace and not Path(host_workspace).is_absolute():
            raise Invalid('B4F_HOST_WORKSPACE must be an absolute path on the Docker host.')
        self.host_workspace = Path(host_workspace) if host_workspace else None
        self.lock = threading.RLock()

    def run(self, args, cwd, timeout=30, endpoint=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith('COMPOSE_') and k != 'DOCKER_CONTEXT'}
        command = [self.docker] + (['--host', endpoint] if endpoint else []) + args
        try:
            with tempfile.TemporaryFile() as output:
                result = subprocess.run(command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout, check=False)
                length = output.tell()
                output.seek(max(0, length - 262144))
                text = output.read().decode('utf-8', errors='replace')
            if result.returncode:
                raise Invalid(text.strip() or f'Docker exited with code {result.returncode}.')
            return text
        except FileNotFoundError as error:
            raise Invalid('Docker CLI was not found. Install Docker with the Compose plugin and restart Build4Fun.') from error
        except subprocess.TimeoutExpired as error:
            raise Invalid('Docker timed out. The operation may have partially completed; refresh service status before retrying.') from error

    def endpoint(self, workspace):
        endpoint = os.environ.get('DOCKER_HOST') or self.run(['context', 'inspect'] + ([os.environ['DOCKER_CONTEXT']] if os.environ.get('DOCKER_CONTEXT') else []) + ['--format', '{{.Endpoints.docker.Host}}'], workspace.root).strip()
        if not endpoint.startswith('unix://'):
            raise Invalid('This version requires a local Docker Engine with a Unix socket.')
        return endpoint

    def manifest(self, workspace):
        path = workspace.root / 'deployment.json'
        return json.loads(path.read_text()) if path.exists() else None

    def owner(self, workspace):
        path = workspace.root / 'docker-owner'
        if not path.exists():
            atomic_write(path, uuid.uuid4().hex)
        return path.read_text().strip()

    def prepare(self, workspace, project, inputs=None):
        project = normalize(project, self.definitions, strict=True)
        document = read_yaml(compose_yaml(project, self.definitions))
        owner = self.owner(workspace)
        for service in document['services'].values():
            service.setdefault('labels', {})[OWNER] = owner
            for mount in service.get('volumes', []):
                if mount['type'] != 'bind':
                    continue
                # Values were escaped for Compose interpolation; filesystem paths are literal.
                source = mount['source'].replace('$$', '$')
                origin = next((node for node in walk(project) if node['type'] == 'bind-mount' and str(Path(node['values'].get('source', ''))) == str(Path(source))), None)
                try:
                    path = (inputs or workspace).path(source)
                    if not path.exists():
                        raise Invalid(f'Bind mount source does not exist: {source}')
                except Invalid as error:
                    raise Invalid(str(error), code='invalid_mount', block_id=origin['id'] if origin else None, field='source') from error
                if self.host_workspace:
                    path = self.host_workspace / path.relative_to(self.projects.legacy.root)
                elif Path('/.dockerenv').exists():
                    raise Invalid('Set B4F_HOST_WORKSPACE to the absolute workspace path on the Docker host before using bind mounts.')
                mount['source'] = str(path).replace('$', '$$')
        if any(not service.get('networks') for service in document['services'].values()):
            document.setdefault('networks', {}).setdefault('default', {})
        for section in ('networks', 'volumes'):
            for resource in document.get(section, {}).values():
                if not resource.get('external'):
                    resource.setdefault('labels', {})[OWNER] = owner
        return document

    def compose(self, workspace, filename, name, args, endpoint=None, timeout=30):
        return self.run(['compose', '--ansi', 'never', '--env-file', str(workspace.root / 'compose.empty.env'),
                         '--project-directory', str(workspace.files), '-p', name, '-f', str(filename)] + args,
                        workspace.root, timeout, endpoint)

    def check_ownership(self, workspace, document, endpoint):
        name, owner = document['name'], self.owner(workspace)
        ids = self.run(['ps', '-aq', '--filter', f'label=com.docker.compose.project={name}'], workspace.root, endpoint=endpoint).split()
        for identity in ids:
            details = json.loads(self.run(['inspect', identity], workspace.root, endpoint=endpoint))[0]
            if details.get('Config', {}).get('Labels', {}).get(OWNER) != owner:
                raise Invalid(f'Compose project name {name} is already used by containers outside this workspace.')
        for section, kind in (('networks', 'network'), ('volumes', 'volume')):
            names = set(self.run([kind, 'ls', '--format', '{{.Name}}'], workspace.root, endpoint=endpoint).splitlines())
            expected = {resource.get('name', f'{name}_{key}') for key, resource in document.get(section, {}).items() if not resource.get('external')}
            for resource_name in names & expected:
                details = json.loads(self.run([kind, 'inspect', resource_name], workspace.root, endpoint=endpoint))[0]
                if (details.get('Labels') or {}).get(OWNER) != owner:
                    raise Invalid(f'Docker {kind} {resource_name} already exists outside this workspace.')

    def check_ports(self, workspace, document, endpoint):
        requested = []
        for service in document['services'].values():
            for value in service.get('ports', []):
                mapping, _, protocol = value.partition('/')
                host, published, _ = mapping.rsplit(':', 2) if mapping.count(':') > 1 else ('', *mapping.split(':'))
                requested.append((host.strip('[]'), str(published), protocol or 'tcp'))
        if not requested:
            return
        identities = self.run(['ps', '-q'], workspace.root, endpoint=endpoint).split()
        for identity in identities:
            details = json.loads(self.run(['inspect', identity], workspace.root, endpoint=endpoint))[0]
            labels = details.get('Config', {}).get('Labels') or {}
            if labels.get(OWNER) == self.owner(workspace):
                continue
            occupied = []
            for target, bindings in details.get('NetworkSettings', {}).get('Ports', {}).items():
                for binding in bindings or []:
                    occupied.append((binding['HostIp'], binding['HostPort'], target.rsplit('/', 1)[-1]))
            # Desktop may publish ports through its host proxy rather than Engine NAT.
            for key, value in labels.items():
                if key.startswith('desktop.docker.io/ports/') and ':' in value:
                    host, port = value.rsplit(':', 1)
                    occupied.append((host.strip('[]'), port, key.rsplit('/', 1)[-1]))
            for host, port, protocol in requested:
                for other_host, other_port, other_protocol in occupied:
                    overlap = host == other_host or host in ('', '0.0.0.0', '::') or other_host in ('', '0.0.0.0', '::')
                    if port == other_port and protocol == other_protocol and overlap:
                        raise Invalid(f'Host port {port}/{protocol} is already published by another container.', code='port_conflict')

    def execute(self, identity, action, project=None):
        if not self.lock.acquire(blocking=False):
            raise Invalid('Another Docker operation is in progress. Try again shortly.')
        try:
            return self._execute(identity, action, project)
        finally:
            self.lock.release()

    def _execute(self, identity, action, project):
        if action not in ('validate', 'start', 'stop', 'status', 'logs', 'remove'):
            raise Invalid('Unknown Docker action.')
        workspace = self.projects.workspace(identity)
        deployment = self.manifest(workspace)
        atomic_write(workspace.root / 'compose.empty.env', '')
        if action in ('validate', 'start'):
            if project is None:
                path = workspace.project_path
                if not path.exists():
                    raise Invalid('Save the project before starting it.')
                project = read_yaml(path.read_text())
            saved_revision = fingerprint(workspace)
            # Check original sources before copying, including forbidden symlinks.
            document = self.prepare(workspace, project)
            inputs = None
            if action == 'start':
                inputs = Workspace(workspace.root / 'deployment-inputs' / uuid.uuid4().hex)
                copy_files(workspace, inputs)
                document = self.prepare(workspace, project, inputs)
            name = document['name']
            if deployment and deployment['name'] != name:
                raise Invalid('Remove the existing deployment before changing its Compose project name.')
            candidate = workspace.root / 'compose.candidate.yaml'
            atomic_write(candidate, yaml.safe_dump(document, sort_keys=False))
            self.compose(workspace, candidate, name, ['config', '--quiet'])
            if action == 'validate':
                return {'message': 'Docker Compose configuration is valid.'}
            endpoint = deployment['endpoint'] if deployment else self.endpoint(workspace)
            # Reserve names across managed workspaces, including stopped deployments.
            for item in self.projects.listing():
                if item['id'] == identity:
                    continue
                other = self.manifest(self.projects.workspace(item['id']))
                if other and other['name'] == name and other['endpoint'] == endpoint:
                    raise Invalid('This Compose project name is assigned to another managed deployment.')
            self.check_ownership(workspace, document, endpoint)
            self.check_ports(workspace, document, endpoint)
            deployed = workspace.root / 'compose.deployed.yaml'
            atomic_write(deployed, candidate.read_text())
            # Persist before up: failed/partial starts must remain manageable.
            atomic_write(workspace.root / 'deployment.json', json.dumps({'name': name, 'endpoint': endpoint, 'revision': saved_revision, 'inputs': str(inputs.root)}))
            output = self.compose(workspace, deployed, name, ['up', '-d', '--remove-orphans'], endpoint, 180)
            return {'message': 'Start command completed. Refresh status to check service health.', 'output': output}
        if not deployment:
            if action in ('status', 'logs'):
                return {'deployed': False, 'services': [], 'output': ''}
            raise Invalid('This project has no deployment to manage.')
        deployed = workspace.root / 'compose.deployed.yaml'
        document = read_yaml(deployed.read_text())
        self.check_ownership(workspace, document, deployment['endpoint'])
        args = {'stop': ['stop', '--timeout', '10'], 'status': ['ps', '--all', '--format', 'json'],
                'logs': ['logs', '--no-color', '--tail', '200'], 'remove': ['down', '--remove-orphans', '--timeout', '10']}[action]
        output = self.compose(workspace, deployed, deployment['name'], args, deployment['endpoint'], 60)
        if action == 'remove':
            (workspace.root / 'deployment.json').unlink()
            return {'message': 'Deployment removed. Persistent volumes and project files were kept.'}
        if action == 'status':
            try:
                services = json.loads(output) if output.strip().startswith('[') else [json.loads(line) for line in output.splitlines() if line.strip()]
            except json.JSONDecodeError as error:
                raise Invalid('Docker returned unreadable status output.') from error
            return {'deployed': True, 'services': services}
        return {'deployed': True, 'output': output, 'message': 'Containers stopped. Persistent data was kept.' if action == 'stop' else ''}
