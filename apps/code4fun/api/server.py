"""Prepared teaching API. Only Linux cgroup v2 measurements are called container metrics."""
import argparse
import getpass
import json
from pathlib import Path
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

FIELDS = {
    '/api/username/': {'username': 'string: API process user'},
    '/api/hostname/': {'hostname': 'string: container hostname'},
    '/api/ip': {'addresses': 'array of non-loopback IP addresses resolved for the container hostname'},
    '/api/metrics': {
        'cpu_percent': 'number or null: percent of effective CPU capacity used since previous sample (first sample null)',
        'memory_used_bytes': 'integer or null: cgroup memory.current, includes cache',
        'memory_limit_bytes': 'integer or null: cgroup memory.max; unlimited is null',
        'uptime_seconds': 'number: API process uptime in seconds',
    },
}


class Measurements:
    def __init__(self, cgroup='/sys/fs/cgroup'):
        self.root = Path(cgroup)
        self.started = time.monotonic()
        self.previous = None
        self.lock = threading.Lock()

    def read(self, name):
        try:
            return (self.root / name).read_text().strip()
        except OSError:
            return None

    def integer(self, name):
        try:
            return int(self.read(name))
        except (TypeError, ValueError):
            return None

    def metrics(self):
        # Never substitute host-wide /proc metrics when container accounting is unavailable.
        with self.lock:
            now = time.monotonic()
            cpu = None
            try:
                stats = dict(line.split() for line in (self.read('cpu.stat') or '').splitlines())
                usage = int(stats['usage_usec'])
                quota, period = (self.read('cpu.max') or '').split()
                cpuset = self.read('cpuset.cpus.effective')
                if not cpuset:
                    raise ValueError('Unknown effective CPU set')
                capacity = sum(int(part.split('-')[-1]) - int(part.split('-')[0]) + 1 for part in cpuset.split(','))
                if quota != 'max':
                    capacity = min(capacity, int(quota) / int(period))
                if self.previous and capacity > 0:
                    elapsed = now - self.previous[0]
                    if elapsed > 0:
                        cpu = round(max(0, min(100, (usage - self.previous[1]) / 1e6 / elapsed / capacity * 100)), 2)
                self.previous = (now, usage)
            except (ValueError, KeyError, ZeroDivisionError):
                self.previous = None
            return {
                'cpu_percent': cpu,
                'memory_used_bytes': self.integer('memory.current'),
                'memory_limit_bytes': self.integer('memory.max'),
                'uptime_seconds': round(now - self.started, 2),
            }


def addresses():
    try:
        import ipaddress
        return sorted({row[4][0] for row in socket.getaddrinfo(socket.gethostname(), None)
                       if not ipaddress.ip_address(row[4][0]).is_loopback
                       and not ipaddress.ip_address(row[4][0]).is_unspecified})
    except OSError:
        return []


def handler(measurements):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path.rstrip('/')
            if path == '/api/info':
                data = {
                    'name': 'Code4Fun teaching API', 'version': 1,
                    'scope': 'API container environment, not the apprentice computer',
                    'endpoints': {'/api/info': {'description': 'This API contract'}, **FIELDS},
                    'metrics': {
                        'source': 'Linux cgroup v2; unsupported measurements are null',
                        'unlimited_memory': 'memory_limit_bytes is null',
                        'cpu_sampling': 'Delta between requests; first sample is null. Normalized to effective cpuset and CPU quota.',
                        'availability': {name: measurements.read(name) is not None for name in
                                         ('cpu.stat', 'cpu.max', 'cpuset.cpus.effective', 'memory.current', 'memory.max')},
                        'recommended_refresh_seconds': 5,
                    },
                    'trailing_slashes': 'Accepted on every endpoint',
                    'errors': {'error': 'Human-readable message; non-2xx HTTP status'},
                }
            elif path == '/api/username':
                data = {'username': getpass.getuser()}
            elif path == '/api/hostname':
                data = {'hostname': socket.gethostname()}
            elif path == '/api/ip':
                data = {'addresses': addresses()}
            elif path == '/api/metrics':
                data = measurements.metrics()
            else:
                self.reply(404, {'error': 'Endpoint not found. See /api/info.'})
                return
            self.reply(200, data)

        def do_POST(self):
            self.reply(405, {'error': 'Use GET for this read-only API.'})

        def reply(self, status, data):
            body = json.dumps(data, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)
    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8092)
    args = parser.parse_args()
    ThreadingHTTPServer((args.bind, args.port), handler(Measurements())).serve_forever()
