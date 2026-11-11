"""Loopback-only local launcher; Docker access is restricted to fixed Compose apps."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
from urllib.parse import urlsplit
from manager import Manager

STATIC = Path(__file__).parent / 'static'


def handler(manager, port):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, data, kind='application/json'):
            raw = data if isinstance(data, bytes) else json.dumps(data).encode()
            self.send_response(status)
            for key, value in {'Content-Type': kind, 'Content-Length': str(len(raw)), 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'", 'Referrer-Policy': 'no-referrer'}.items(): self.send_header(key, value)
            self.end_headers(); self.wfile.write(raw)

        def allowed(self, write=False):
            if self.headers.get('Host') not in (f'localhost:{port}', f'127.0.0.1:{port}'):
                self.reply(403, {'error': 'Use the local launcher address'}); return False
            if write and self.headers.get('Origin') not in (f'http://localhost:{port}', f'http://127.0.0.1:{port}'):
                self.reply(403, {'error': 'Use the launcher to manage applications'}); return False
            return True

        def do_GET(self):
            if not self.allowed(): return
            path = urlsplit(self.path).path
            if path == '/api/state': self.reply(200, manager.snapshot())
            elif path in ('/', '/app.js', '/style.css'):
                name = 'index.html' if path == '/' else path[1:]
                kind = 'text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
                self.reply(200, (STATIC / name).read_bytes(), kind + '; charset=utf-8')
            else: self.reply(404, {'error': 'Not found'})

        def do_POST(self):
            if not self.allowed(True): return
            if urlsplit(self.path).path != '/api/action': self.reply(404, {'error': 'Not found'}); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096: raise ValueError('Invalid request size')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict): raise ValueError('Expected a JSON object')
                job = manager.launch(data.get('app'), data.get('action'), data.get('source', 'local'), data.get('tag', 'latest'))
                self.reply(202, job)
            except (ValueError, TypeError) as error: self.reply(400, {'error': str(error)})
    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--bind', default='127.0.0.1'); parser.add_argument('--port', type=int, default=8070); args = parser.parse_args()
    manager = Manager(os.environ.get('LAUNCHER_REPOSITORY') or str(Path(__file__).resolve().parents[2]), os.environ.get('LAUNCHER_STATE', '.workspace/launcher'))
    threading.Thread(target=manager.refresh, daemon=True).start()
    ThreadingHTTPServer((args.bind, args.port), handler(manager, int(os.environ.get('LAUNCHER_HTTP_PORT', args.port)))).serve_forever()
