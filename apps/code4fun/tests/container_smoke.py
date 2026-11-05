"""Build and exercise an isolated Code4Fun stack, cleaning up only its own volume."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
import uuid

ROOT = Path(__file__).resolve().parents[3]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    first = free_port()
    second = free_port()
    while first == second:
        second = free_port()
    env = {**os.environ, 'C4F_HTTP_PORT': str(first), 'C4F_PREVIEW_PORT': str(second)}
    command = ['docker', 'compose', '-f', str(ROOT / 'compose.code4fun.yaml'), '-p', 'code4fun-check-' + uuid.uuid4().hex[:10]]
    origin = f'http://127.0.0.1:{first}'
    preview = f'http://127.0.0.1:{second}'

    def http(base, path, data=None):
        request = Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                          headers={'Origin': base, 'Content-Type': 'application/json'})
        with urlopen(request, timeout=70) as response:
            return json.load(response)

    try:
        subprocess.run(command + ['up', '--build', '-d', '--wait', '--wait-timeout', '120'], cwd=ROOT, env=env, check=True)
        assert http(preview, '/api/hostname/')['hostname'] == 'code4fun-api'
        assert http(preview, '/api/username/')['username'] == 'code4fun'
        metrics = http(preview, '/api/metrics')
        assert metrics['memory_limit_bytes'] == 128 * 1024 * 1024, metrics
        assert metrics['memory_used_bytes'] > 0, metrics
        time.sleep(.1)
        assert http(preview, '/api/metrics')['cpu_percent'] is not None
        state = http(origin, '/code4fun/api/project')
        state['files']['index.html'] = '<h1>Docker dashboard</h1><p>Saved inside the volume.</p><section id="server-info"><h2>Server</h2></section>'
        result = http(origin, '/code4fun/api/check', state)
        assert all(item['passed'] for item in result['results']), result
        # The complete dashboard exercises Chromium, timers, and all final-stage cases in the image.
        state = result['state']
        state['files'] = {name: (ROOT / 'apps' / 'code4fun' / 'tests' / 'fixtures' / name).read_text() for name in state['files']}
        state['stage'] = 5
        result = http(origin, '/code4fun/api/check', state)
        assert all(item['passed'] for item in result['results']), result
        subprocess.run(command + ['restart', 'workspace'], cwd=ROOT, env=env, check=True)
        for attempt in range(40):
            try:
                state = http(origin, '/code4fun/api/project')
                assert '0' in state['completed'] and '5' in state['completed']
                break
            except (URLError, ConnectionError):
                time.sleep(.25)
        else:
            raise AssertionError('Workspace did not restart')
        print('Code4Fun container API, cgroup metrics, browser checks, and persistence passed.')
    except Exception:
        subprocess.run(command + ['logs', '--tail', '100'], cwd=ROOT, env=env)
        raise
    finally:
        subprocess.run(command + ['down', '--volumes', '--remove-orphans'], cwd=ROOT, env=env, check=True)


if __name__ == '__main__':
    main()
