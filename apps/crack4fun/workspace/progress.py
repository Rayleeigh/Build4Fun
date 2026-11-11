"""Persistent local session, challenge-specific flags, and idempotent completion."""
import hashlib
import hmac
import json
from pathlib import Path
import re
import secrets
import threading
import time


class Store:
    def __init__(self, directory):
        self.path = Path(directory) / 'session.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        if not self.path.exists():
            self.write({'secret': secrets.token_hex(32), 'session': secrets.token_hex(16), 'active': 'filesystem', 'completed': {}})

    def read(self):
        return json.loads(self.path.read_text())

    def write(self, state):
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w') as stream:
            json.dump(state, stream)
            stream.flush()
            import os
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        temporary.replace(self.path)

    def flag(self, challenge):
        with self.lock:
            digest = hmac.new(bytes.fromhex(self.read()['secret']), challenge.encode(), hashlib.sha256).hexdigest()[:16]
        return '{' + challenge.replace('-', '_') + '_' + digest + '}'

    def public(self):
        with self.lock:
            state = self.read()
            return {**{key: state[key] for key in ('session', 'active', 'completed')}, 'tutorial_seen': state.get('tutorial_seen', False)}

    def finish_tutorial(self):
        with self.lock:
            state = self.read(); state['tutorial_seen'] = True; self.write(state)

    def activate(self, program):
        with self.lock:
            state = self.read(); state['active'] = program; self.write(state)

    def submit(self, challenge, value):
        if not isinstance(value, str) or not re.fullmatch(r'\{[a-z0-9_]+\}', value.strip()):
            raise ValueError('Use a flag enclosed in braces, for example {example_token}.')
        if not hmac.compare_digest(value.strip(), self.flag(challenge)):
            return {'correct': False, 'message': 'That flag does not match this challenge. Check the selected task and try again.'}
        with self.lock:
            state = self.read()
            already = challenge in state['completed']
            state['completed'].setdefault(challenge, int(time.time()))
            self.write(state)
        return {'correct': True, 'already': already, 'message': 'Already completed.' if already else 'Flag accepted. Progress saved.'}

    def clear(self, prefix):
        with self.lock:
            state = self.read()
            state['completed'] = {key: value for key, value in state['completed'].items() if not key.startswith(prefix + '-')}
            self.write(state)
