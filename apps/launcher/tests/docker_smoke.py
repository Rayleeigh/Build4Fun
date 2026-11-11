"""Real local-build, stop and optional GHCR pull lifecycle in an isolated project.

Run on a host with Docker: python apps/launcher/tests/docker_smoke.py [--registry]
Never changes the ordinary build4fun project or its workspace.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from manager import Manager
ROOT=Path(__file__).resolve().parents[3]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--registry',action='store_true');args=parser.parse_args()
    project='fourfun-launcher-check-'+uuid.uuid4().hex[:8]
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    with tempfile.TemporaryDirectory() as directory:
        manager=Manager(ROOT,Path(directory)/'state')
        manager.environment.update(B4F_HTTP_PORT=str(port),B4F_HOST_WORKSPACE=directory)
        # Isolate the project's name while exercising the manager's actual command builder.
        original=manager.command
        def command(app,path=None):
            result=original(app,path);result[result.index('-p')+1]=project;return result
        manager.command=command
        try:
            for source in (['local','registry'] if args.registry else ['local']):
                manager.launch('build4fun','start',source)
                while manager.jobs['build4fun']['running']:time.sleep(.25)
                job=manager.jobs['build4fun'];assert job['exit_code']==0,job['log']
                with urlopen(f'http://127.0.0.1:{port}/api/projects') as response:assert json.load(response)==[]
                manager.launch('build4fun','stop',source)
                while manager.jobs['build4fun']['running']:time.sleep(.25)
                assert manager.jobs['build4fun']['exit_code']==0,manager.jobs['build4fun']['log']
                result=subprocess.run(command('build4fun')+['ps','--format','json'],env=manager.environment,capture_output=True,text=True,check=True)
                assert result.stdout.strip() in ('','[]')
                print(source+': real start, HTTP response and stop passed.')
        finally:
            subprocess.run(command('build4fun')+['down','--volumes','--remove-orphans'],env=manager.environment,check=True)


if __name__=='__main__':main()
