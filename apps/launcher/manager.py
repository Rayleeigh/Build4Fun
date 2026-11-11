"""Compose lifecycle management with bounded logs and one job per application."""
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from catalog import APPS

TAG = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}')
REGISTRY = re.compile(r'ghcr\.io/[a-z0-9][a-z0-9._/-]*[a-z0-9]')


def parse_ps(output):
    if not output.strip(): return []
    try: value = json.loads(output)
    except json.JSONDecodeError: value = [json.loads(line) for line in output.splitlines() if line.strip()]
    return value if isinstance(value, list) else [value]


class Manager:
    def __init__(self, root, state_dir, registry=None):
        self.root = Path(root).resolve()
        self.directory = Path(state_dir).resolve(); self.directory.mkdir(parents=True, exist_ok=True)
        self.registry = registry or os.environ.get('FOURFUN_REGISTRY', 'ghcr.io/rayleeigh/build4fun')
        if not REGISTRY.fullmatch(self.registry) or '..' in self.registry: raise ValueError('FOURFUN_REGISTRY must be a GHCR repository path')
        self.lock = threading.RLock(); self.jobs = {}; self.settings = {}
        self.environment = {**os.environ, 'PWD': str(self.root), 'COMPOSE_ANSI': 'never', 'COMPOSE_PROGRESS': 'plain'}
        self.cache = {'docker': 'Checking Docker…', 'apps': []}; self.last_check = 0

    def command(self, app, path=None):
        return ['docker', 'compose', '--project-directory', str(self.root), '-p', app, '-f', str(path or self.root / ('compose.' + app + '.yaml'))]

    def config(self, app):
        result = subprocess.run(self.command(app) + ['config', '--format', 'json'], cwd=self.root, env=self.environment, capture_output=True, text=True, timeout=30)
        if result.returncode: raise ValueError(result.stderr.strip() or 'Could not read Compose configuration')
        return json.loads(result.stdout)

    def registry_config(self, app, tag):
        config = self.config(app)
        for service, suffix in APPS[app]['images'].items():
            item = config['services'][service]; item.pop('build', None)
            item['image'] = self.registry + ('/' + suffix if suffix else '') + ':' + tag
            item['pull_policy'] = 'always'
        return config

    def launch(self, app, action, source='local', tag='latest'):
        if app not in APPS: raise ValueError('Unknown application')
        if action not in ('start', 'stop'): raise ValueError('Choose Start or Stop')
        if source not in ('local', 'registry'): raise ValueError('Choose a local build or GHCR')
        if not isinstance(tag, str) or not TAG.fullmatch(tag): raise ValueError('Invalid image tag')
        with self.lock:
            if self.jobs.get(app, {}).get('running'): raise ValueError('An operation is already running for this application')
            job = {'running': True, 'action': action, 'source': source, 'tag': tag, 'log': '', 'started': time.time(), 'exit_code': None}
            self.jobs[app] = job
        threading.Thread(target=self.run, args=(app, job), daemon=True).start()
        return dict(job)

    def append(self, job, text):
        with self.lock: job['log'] = (job['log'] + text)[-100000:]

    def run_command(self, command, job):
        # A file avoids pipe deadlocks and allows a hard timeout on quiet builds.
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+b') as output, open(output.name, 'rb') as reader:
            process = subprocess.Popen(command, cwd=self.root, env=self.environment, stdout=output, stderr=subprocess.STDOUT)
            position = 0; deadline = time.monotonic() + 2700
            while True:
                done = process.poll() is not None
                reader.seek(position); data = reader.read(); position += len(data)
                if data: self.append(job, data.decode(errors='replace'))
                if done: break
                if time.monotonic() > deadline:
                    process.kill(); process.wait(); raise TimeoutError('Operation exceeded 45 minutes. Inspect Docker before retrying.')
                time.sleep(.2)
            if process.returncode: raise RuntimeError('Docker Compose exited with code ' + str(process.returncode))

    def run(self, app, job):
        try:
            if job['action'] == 'stop':
                self.run_command(self.command(app) + ['stop', '--timeout', '20'], job)
            elif job['source'] == 'local':
                self.append(job, 'Building from the local repository…\n')
                self.run_command(self.command(app) + ['up', '--build', '--pull', 'missing', '-d', '--wait', '--wait-timeout', '180'], job)
            else:
                path = self.directory / (app + '-registry.json')
                path.write_text(json.dumps(self.registry_config(app, job['tag']))); path.chmod(0o600)
                command = self.command(app, path)
                self.append(job, 'Pulling ' + self.registry + ' images (' + job['tag'] + ')…\n')
                self.run_command(command + ['pull'], job)
                self.run_command(command + ['up', '--no-build', '--pull', 'never', '-d', '--wait', '--wait-timeout', '180'], job)
            with self.lock:
                job['exit_code'] = 0
                if job['action'] == 'start': self.settings[app] = {'source': job['source'], 'tag': job['tag']}
            self.append(job, 'Ready.\n' if job['action'] == 'start' else 'Stopped. Saved work is kept.\n')
        except Exception as error:
            self.append(job, str(error) + '\n')
            with self.lock: job['exit_code'] = 1
        finally:
            with self.lock: job['running'] = False; self.last_check = 0

    def refresh(self):
        while True:
            self.inspect()
            time.sleep(3)

    def inspect(self):
        apps = []; docker_error = None
        for app, item in APPS.items():
            entry = {key: item[key] for key in ('title', 'description', 'accent')}; entry['id'] = app
            try:
                # Compose resolves .env port overrides with the same rules used for launching.
                config = self.config(app)
                services = config['services']; frontend = services['app' if app == 'build4fun' else 'workspace']
                entry['port'] = next(int(p['published']) for p in frontend.get('ports', []) if int(p['target']) == item['port'])
                result = subprocess.run(self.command(app) + ['ps', '--all', '--format', 'json'], cwd=self.root, env=self.environment, capture_output=True, text=True, timeout=15)
                if result.returncode: raise ValueError(result.stderr.strip() or 'Docker is unavailable')
                containers = parse_ps(result.stdout)
                entry['containers'] = [{'service': c.get('Service', ''), 'state': c.get('State', ''), 'health': c.get('Health', '')} for c in containers]
                running = [c for c in containers if c.get('State') == 'running']
                unhealthy = any(c.get('Health') == 'unhealthy' for c in containers)
                starting = any(c.get('Health') == 'starting' for c in containers)
                entry['status'] = 'unhealthy' if unhealthy else 'starting' if starting else 'running' if len(running) == len(services) else 'partial' if running else 'stopped'
            except Exception as error:
                entry.update(port=item['port'], status='unavailable', containers=[], error=str(error)); docker_error = str(error)
            apps.append(entry)
        with self.lock: self.cache = {'docker': docker_error, 'apps': apps}; self.last_check = time.time()

    def snapshot(self):
        with self.lock:
            return {**self.cache, 'registry': self.registry, 'jobs': {key: dict(value) for key, value in self.jobs.items()}, 'settings': dict(self.settings)}
