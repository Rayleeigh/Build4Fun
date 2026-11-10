"""Local Code4Fun workspace and separate-origin preview server."""
import argparse
from collections import OrderedDict
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
STATIC = Path(__file__).parent / 'static'
LESSONS = ROOT / 'challenges' / 'code'
FILES = ('index.html', 'style.css', 'script.js')
MAX_BODY = 512 * 1024

# Exact original starter, used only to upgrade untouched workspaces and empty drafts.
LEGACY_STARTER = {
    'index.html': '<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>My Server Dashboard</title>\n  <link rel="stylesheet" href="style.css">\n  <script src="script.js" defer></script>\n</head>\n<body>\n  <!-- Build your dashboard here. Start with stage 1. -->\n</body>\n</html>\n',
    'style.css': '/* Your dashboard styles. */\n',
    'script.js': '// Your dashboard interactions. API requests use relative paths, e.g. /api/hostname/.\n',
}

# The second starter fixed nesting but still had no visible body content.
PREVIEWLESS_STARTERS = [LEGACY_STARTER, {
    **LEGACY_STARTER,
    'index.html': '\n'.join('  ' + line if 2 <= index <= 11 else line
                            for index, line in enumerate(LEGACY_STARTER['index.html'].splitlines())) + '\n',
}]


def validate_files(files):
    if not isinstance(files, dict) or set(files) != set(FILES):
        raise ValueError('The project must contain index.html, style.css, and script.js.')
    if any(not isinstance(v, str) or len(v.encode()) > 128 * 1024 for v in files.values()):
        raise ValueError('Each file must be text and at most 128 KiB.')
    return dict(files)


class Conflict(Exception):
    pass


class Store:
    def __init__(self, directory):
        self.path = Path(directory) / 'project.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.snapshots = OrderedDict()
        self.check_lock = threading.Lock()
        if not self.path.exists():
            self.write({'files': self.starter(), 'stage': 0, 'completed': {}, 'revision': secrets.token_hex(16)})
        else:
            state = self.read()
            if state.get('stage') == 0 and not state.get('completed') and state.get('files') in PREVIEWLESS_STARTERS:
                state.update(files=self.starter(), revision=secrets.token_hex(16))
                self.write(state)


    def starter(self):
        return {name: (LESSONS / 'starter' / name).read_text() for name in FILES}

    def read(self):
        return json.loads(self.path.read_text())

    def write(self, state):
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w') as stream:
            json.dump(state, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.path)

    def save(self, data, reset=False):
        files = self.starter() if reset else validate_files(data.get('files'))
        stage = 0 if reset else data.get('stage')
        if type(stage) is not int or not 0 <= stage < 6:
            raise ValueError('Choose a stage between 1 and 6.')
        with self.lock:
            state = self.read()
            if data.get('revision') != state['revision']:
                raise Conflict('A newer save exists. Download your files, then reload before saving again.')
            state.update(files=files, stage=stage, revision=secrets.token_hex(16))
            if reset:
                state['completed'] = {}
            self.write(state)
            return state

    def finish_tutorial(self):
        with self.lock:
            state = self.read()
            state['tutorial_seen'] = True
            self.write(state)
        return {'tutorial_seen': True}

    def snapshot(self, files):
        files = validate_files(files)
        with self.lock:
            token = secrets.token_urlsafe(24)
            self.snapshots[token] = (time.monotonic(), files)
            while len(self.snapshots) > 32:
                self.snapshots.popitem(last=False)
            return token

    def snapshot_file(self, token, name):
        with self.lock:
            item = self.snapshots.get(token)
            if item and time.monotonic() - item[0] < 3600:
                return item[1].get(name)
        return None

    def complete(self, revision, stage, results):
        with self.lock:
            state = self.read()
            if state['revision'] != revision:
                return False
            if all(result['passed'] for result in results):
                digest = hashlib.sha256(json.dumps(state['files'], sort_keys=True).encode()).hexdigest()
                state['completed'][str(stage)] = {'checked_at': int(time.time()), 'files_hash': digest}
                self.write(state)
            return True


def run_checks(url, stage):
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).with_name('checks.py')), url, str(stage)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        output, errors = process.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        return [{'label': 'Complete checks within 60 seconds', 'passed': False,
                 'message': 'Check for infinite loops or blocking code, then try again.'}]
    if process.returncode:
        raise RuntimeError('Browser checks could not start or finish: ' + errors[-500:])
    return json.loads(output)


def make_handler(store, preview=False, preview_port=8091, api_url='http://127.0.0.1:8092'):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body, content_type='application/json; charset=utf-8'):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            if preview:
                self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'; frame-src 'none'; object-src 'none'")
            else:
                self.send_header('X-Frame-Options', 'DENY')
                self.send_header('Content-Security-Policy', f"default-src 'self'; frame-src http://127.0.0.1:{preview_port} http://localhost:{preview_port}; object-src 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self, mutation=False):
            # A separate preview origin must never obtain management privileges.
            host = self.headers.get('Host', '')
            ports = (self.server.server_port, getattr(self.server, 'public_port', self.server.server_port))
            valid = host in {f'{name}:{port}' for name in ('localhost', '127.0.0.1') for port in ports}
            if not valid:
                self.reply(403, {'error': 'Use the localhost URL with the configured port.'})
                return False
            origin = self.headers.get('Origin')
            if mutation and origin != 'http://' + host:
                self.reply(403, {'error': 'A same-origin request is required.'})
                return False
            return True

        def do_GET(self):
            if not self.allowed():
                return
            path = urlsplit(self.path).path
            if preview:
                if path.startswith('/api/'):
                    if path.rstrip('/') not in ('/api/info', '/api/username', '/api/hostname', '/api/ip', '/api/metrics'):
                        self.reply(404, {'error': 'Unknown API endpoint.'})
                        return
                    try:
                        with urlopen(Request(api_url.rstrip('/') + path, headers={'Accept': 'application/json'}), timeout=4) as response:
                            self.reply(response.status, response.read(128 * 1024))
                    except HTTPError as error:
                        self.reply(error.code, {'error': 'The API returned an error.'})
                    except (URLError, TimeoutError, OSError):
                        self.reply(502, {'error': 'The prepared API is unavailable. Check the API service.'})
                    return
                parts = path.strip('/').split('/')
                if len(parts) == 3 and parts[0] == 'preview' and parts[2] in FILES:
                    body = store.snapshot_file(parts[1], parts[2])
                    if body is not None:
                        mime = {'index.html': 'text/html', 'style.css': 'text/css', 'script.js': 'text/javascript'}[parts[2]]
                        self.reply(200, body.encode(), mime + '; charset=utf-8')
                        return
                self.reply(404, {'error': 'Preview expired or not found. Run your project again.'})
                return
            if path == '/code4fun/api/project':
                with store.lock:
                    state = store.read()
                untouched = state.get('stage') == 0 and not state.get('completed') and state['files'] == store.starter()
                self.reply(200, {**state, 'stages': json.loads((LESSONS / 'stages.json').read_text()),
                                 'preview_port': preview_port, 'obsolete_starters': PREVIEWLESS_STARTERS if untouched else []})
            elif path == '/code4fun/api/reference':
                try:
                    with urlopen(api_url.rstrip('/') + '/api/info', timeout=4) as response:
                        self.reply(200, response.read(128 * 1024))
                except (URLError, TimeoutError, OSError):
                    self.reply(502, {'error': 'The API reference is unavailable. Check the API service and try again.'})
            elif path in ('/', '/app.js', '/style.css'):
                name = 'index.html' if path == '/' else path[1:]
                self.reply(200, (STATIC / name).read_bytes(), {'index.html': 'text/html', 'app.js': 'text/javascript', 'style.css': 'text/css'}[name] + '; charset=utf-8')
            else:
                self.reply(404, {'error': 'Not found.'})

        def do_POST(self):
            if not self.allowed(mutation=True):
                return
            if preview:
                self.reply(405, {'error': 'The preview is read-only.'})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BODY:
                    self.reply(413, {'error': 'Request is empty or too large.'})
                    return
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Expected a JSON object.')
                path = urlsplit(self.path).path
                if path == '/code4fun/api/tutorial':
                    self.reply(200, store.finish_tutorial())
                elif path in ('/code4fun/api/save', '/code4fun/api/reset'):
                    self.reply(200, store.save(data, reset=path.endswith('/reset')))
                elif path == '/code4fun/api/run':
                    token = store.snapshot(data.get('files'))
                    self.reply(200, {'path': f'/preview/{token}/index.html'})
                elif path == '/code4fun/api/check':
                    if not store.check_lock.acquire(blocking=False):
                        self.reply(409, {'error': 'Another check is running. Try again shortly.'})
                        return
                    try:
                        state = store.save(data)
                        token = store.snapshot(state['files'])
                        try:
                            results = run_checks(f'http://127.0.0.1:{self.server.preview_internal_port}/preview/{token}/index.html', state['stage'])
                        except RuntimeError as error:
                            self.log_error('%s', error)
                            results = [{'label': 'Browser checks unavailable', 'passed': False,
                                        'message': 'Your files were saved. Install Chromium as described in the Code4Fun guide, or inspect workspace logs.'}]
                        current = store.complete(state['revision'], state['stage'], results)
                        with store.lock:
                            latest = store.read()
                        self.reply(200, {'state': latest, 'results': results, 'current': current, 'checked_revision': state['revision']})
                    finally:
                        store.check_lock.release()
                else:
                    self.reply(404, {'error': 'Not found.'})
            except Conflict as error:
                self.reply(409, {'error': str(error)})
            except (ValueError, TypeError) as error:
                self.reply(400, {'error': str(error)})
            except Exception:
                self.log_error('Workspace operation failed')
                self.reply(500, {'error': 'Operation failed. If checking, verify Chromium is installed; your saved work is preserved.'})
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8090)
    parser.add_argument('--preview-port', type=int, default=8091)
    parser.add_argument('--public-preview-port', type=int, default=int(os.environ.get('C4F_PREVIEW_PORT', '8091')))
    parser.add_argument('--workspace', default='.workspace/code4fun')
    parser.add_argument('--api-url', default=os.environ.get('C4F_API_URL', 'http://127.0.0.1:8092'))
    args = parser.parse_args()
    store = Store(args.workspace)
    preview = ThreadingHTTPServer((args.bind, args.preview_port), make_handler(store, True, args.public_preview_port, args.api_url))
    server = ThreadingHTTPServer((args.bind, args.port), make_handler(store, False, args.public_preview_port, args.api_url))
    # Public port can differ from the container listening port. Validate both explicitly.
    for instance, public in ((server, int(os.environ.get('C4F_HTTP_PORT', args.port))), (preview, args.public_preview_port)):
        instance.public_port = public
    server.preview_internal_port = args.preview_port
    threading.Thread(target=preview.serve_forever, daemon=True).start()
    print(f'Code4Fun: http://localhost:{args.port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
