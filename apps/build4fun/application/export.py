"""Portable saved projects, without deployment-specific host paths or metadata."""
import io
import zipfile

from core import Invalid


def project_bundle(workspace):
    compose = workspace.data_root / 'compose.yaml'
    if not compose.is_file():
        raise Invalid('Save a valid Compose configuration before exporting the project.')
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.write(compose, 'compose.yaml')
        archive.write(workspace.project_path, 'project.yaml')
        for entry in workspace.listing():
            name = 'files/' + entry['path']
            if entry['directory']:
                archive.writestr(name + '/', '')
            else:
                archive.write(workspace.path(entry['path']), name)
        archive.writestr('README.txt', 'Build4Fun project export\n\nExtract the entire archive into one directory.\nInstall Docker Engine and the Docker Compose plugin.\nFrom this directory run:\n  docker compose config --quiet\n  docker compose up -d\n  docker compose logs\n  docker compose stop\n\nBind mounts use files/ beside compose.yaml. External networks must already exist.\nNamed-volume contents and images are not included. Service configuration files\nare copied as written, without checking their contents.\nproject.yaml contains the Build4Fun block model.\n')
    return output.getvalue()
