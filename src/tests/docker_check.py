"""Read-only Docker integration check; creates no images, containers, or networks.
Run: .venv/bin/python src/tests/docker_check.py
"""
import tempfile
from pathlib import Path
from test_core import block, registry, TEMPLATES, read_yaml
from projects import Projects
from storage import Workspace
from docker_runtime import DockerRuntime


def main():
    with tempfile.TemporaryDirectory(prefix='build4fun-docker-check-') as directory:
        projects = Projects(Workspace(directory))
        metadata = projects.create('build4fun-check-' + Path(directory).name.rsplit('-', 1)[-1])
        workspace = projects.workspace(metadata['id'])
        project = read_yaml((workspace.root / 'project.yaml').read_text())
        project['children'].append(block('service', {'name': 'worker'}, block('image', {'image': 'busybox:latest'}),
                                         block('environment', {}, block('variable', {'key': 'EXAMPLE', 'value': '$LITERAL'}))))
        runtime = DockerRuntime(projects, registry(TEMPLATES))
        print(runtime.execute(metadata['id'], 'validate', project)['message'])
        runtime.check_ownership(workspace, runtime.prepare(workspace, project), runtime.endpoint(workspace))
        assert not (workspace.root / 'deployment.json').exists()
        print('Read-only Engine checks passed. No Docker resources were created.')


if __name__ == '__main__':
    main()
