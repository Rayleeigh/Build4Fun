"""Local prototype server. Run with python src/application/server.py."""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import yaml

from core import Invalid, registry, check_structure, compose_preview, read_yaml
from storage import Workspace, atomic_write
from projects import Projects
from docker_runtime import DockerRuntime

BASE = Path(__file__).resolve().parent


def make_handler(workspace, definitions, runtime=None):
    projects = Projects(workspace)
    runtime = runtime or DockerRuntime(projects, definitions, os.environ.get('B4F_DOCKER', 'docker'), os.environ.get('B4F_HOST_WORKSPACE'))
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, data, content_type='application/json'):
            body = json.dumps(data).encode() if content_type == 'application/json' else data
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.dispatch(False)

        def do_POST(self):
            self.dispatch(True)

        def dispatch(self, mutation):
            port = self.server.server_port
            host = self.headers.get('Host', '')
            if host not in (f'localhost:{port}', f'127.0.0.1:{port}'):
                self.respond(403, {'error': 'Use localhost or 127.0.0.1 to access this application.'})
                return
            origin = self.headers.get('Origin')
            if origin and origin != f'http://{host}':
                self.respond(403, {'error': 'Cross-origin access is not allowed.'})
                return
            try:
                route = urlsplit(self.path)
                query = parse_qs(route.query)
                if mutation:
                    if self.headers.get('Content-Type') != 'application/json':
                        raise Invalid('Expected a JSON request.')
                    size = int(self.headers.get('Content-Length', '0'))
                    if size < 1 or size > 2 * 1024 * 1024:
                        raise Invalid('Invalid request size.')
                    data = json.loads(self.rfile.read(size))
                    if not isinstance(data, dict):
                        raise Invalid('Expected a request object.')
                if route.path in ('/api/projects', '/api/projects/rename', '/api/projects/delete'):
                    if mutation and route.path != '/api/projects':
                        data['action'] = route.path.rsplit('/', 1)[-1]
                    if not mutation:
                        self.respond(200, projects.listing())
                    elif data.get('action') == 'rename':
                        self.respond(200, projects.rename(data['id'], data.get('name')))
                    elif data.get('action') == 'delete':
                        with runtime.lock:
                            projects.delete(data['id'])
                        self.respond(200, {'deleted': True})
                    elif data.get('action', 'create') == 'create':
                        self.respond(200, projects.create(data.get('name')))
                    else:
                        raise Invalid('Unknown project action.')
                    return
                current_workspace = projects.workspace(query.get('workspace', ['legacy'])[0])
                project_path = current_workspace.root / 'project.yaml'
                if route.path == '/api/definitions' and not mutation:
                    self.respond(200, definitions)
                elif route.path == '/api/docker' and mutation:
                    self.respond(200, runtime.execute(query.get('workspace', ['legacy'])[0], data.get('action'), data.get('project') if data.get('action') == 'validate' else None))
                elif route.path == '/api/project':
                    if mutation:
                        check_structure(data['project'], definitions)
                        atomic_write(project_path, yaml.safe_dump(data['project'], sort_keys=False))
                        self.respond(200, {'saved': True})
                    else:
                        project = read_yaml(project_path.read_text()) if project_path.exists() else {'id': 'root', 'type': 'harness', 'version': 1, 'values': {}, 'children': []}
                        check_structure(project, definitions)
                        self.respond(200, project)
                elif route.path == '/api/preview' and mutation:
                    self.respond(200, compose_preview(data['project'], definitions))
                elif route.path == '/api/files' and not mutation:
                    self.respond(200, current_workspace.listing())
                elif route.path == '/api/file':
                    if mutation:
                        current_workspace.write(data['path'], data['content'], data.get('create', False))
                        self.respond(200, {'saved': True})
                    else:
                        self.respond(200, {'content': current_workspace.read(query['path'][0])})
                elif route.path == '/api/delete' and mutation:
                    current_workspace.delete(data['path'])
                    self.respond(200, {'deleted': True})
                elif route.path == '/api/folder' and mutation:
                    current_workspace.path(data['path']).mkdir(parents=True, exist_ok=False)
                    self.respond(200, {'created': True})
                elif not mutation and route.path in ('/', '/app.js', '/style.css'):
                    filename = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}[route.path]
                    kind = {'/': 'text/html; charset=utf-8', '/app.js': 'text/javascript; charset=utf-8', '/style.css': 'text/css; charset=utf-8'}[route.path]
                    self.respond(200, (BASE / 'static' / filename).read_bytes(), kind)
                else:
                    self.respond(404, {'error': 'Not found.'})
            except (Invalid, ValueError, KeyError, TypeError, OSError, RecursionError) as error:
                self.respond(400, {'error': str(error)})
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--workspace', default=str(BASE.parents[1] / '.workspace'))
    args = parser.parse_args()
    definitions = registry(BASE.parent / 'templates')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(Workspace(args.workspace), definitions))
    print(f'Build4Fun: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
