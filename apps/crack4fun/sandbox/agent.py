"""Single-program PTY service on a private network; control credentials never reach the browser."""
import base64
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import pty
import secrets
import select
import shutil
import signal
import struct
import subprocess
import termios
import threading
import time
from artifacts import provision

PROGRAM=os.environ.get('CRACK_PROGRAM','filesystem')
TOKEN=Path('/control/token')
MARKER=Path('/state/session')
lock=threading.RLock()
terminals={}


class Terminal:
    def __init__(self):
        self.master,slave=pty.openpty()
        fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',28,100,0,0))
        def child():
            os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0)
            os.setgroups([]);os.setgid(1000);os.setuid(1000)
        self.process=subprocess.Popen(['/bin/bash','--noprofile','--norc','-i'],stdin=slave,stdout=slave,stderr=slave,
            cwd='/home/apprentice',env={'HOME':'/home/apprentice','USER':'apprentice','LOGNAME':'apprentice','PATH':os.environ['PATH'],'TERM':'xterm-256color','LANG':'C.UTF-8','HISTFILE':'/home/apprentice/.session_history','PS1':r'\u@\h:\w\$ '},preexec_fn=child)
        os.close(slave)
        self.output=bytearray();self.offset=0;self.closed=False;self.lock=threading.Lock()
        threading.Thread(target=self.read,daemon=True).start()

    def read(self):
        while not self.closed:
            try:
                if not select.select([self.master],[],[],.25)[0]:continue
                data=os.read(self.master,65536)
                if not data:break
                with self.lock:
                    self.output.extend(data)
                    if len(self.output)>1024*1024:
                        removed=len(self.output)-1024*1024
                        del self.output[:removed];self.offset+=removed
            except OSError:break
        self.closed=True

    def poll(self,cursor):
        with self.lock:
            cursor=max(self.offset,min(cursor,self.offset+len(self.output)))
            return {'output':base64.b64encode(self.output[cursor-self.offset:]).decode(),'cursor':self.offset+len(self.output),'closed':self.closed}

    def close(self):
        self.closed=True
        try:os.killpg(self.process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        try:os.close(self.master)
        except OSError:pass
        try:self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:pass


class Handler(BaseHTTPRequestHandler):
    def reply(self,status,data):
        body=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path=='/health':self.reply(200,{'ready':True})
        else:self.reply(404,{'error':'Not found'})
    def do_POST(self):
        try:
            if not TOKEN.exists() or not secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+TOKEN.read_text().strip()):
                self.reply(403,{'error':'Control authorization required'});return
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=131072:raise ValueError('Invalid request length')
            data=json.loads(self.rfile.read(length))
            with lock:
                if self.path in ('/configure','/reset'):
                    session=data['session']
                    if self.path=='/reset' or not MARKER.exists() or MARKER.read_text()!=session:
                        for terminal in terminals.values():terminal.close()
                        terminals.clear()
                        subprocess.run(['pkill','-KILL','-u','1000'],check=False)
                        # Restore only scenario-owned locations, never host paths or other programs.
                        for folder in ('/work','/home/apprentice'):
                            root=Path(folder)
                            for entry in root.iterdir():
                                if entry.is_dir() and not entry.is_symlink():shutil.rmtree(entry)
                                else:entry.unlink()
                            os.chown(root,1000,1000)
                        provision(PROGRAM,data['flags'],session)
                        MARKER.parent.mkdir(exist_ok=True);MARKER.write_text(session)
                    self.reply(200,{'ready':True});return
                if not MARKER.exists():raise ValueError('Program is still preparing')
                if self.path=='/artifact':
                    names={'forensics':{'01-message.hex','02-recovered.dat','03-workshop-photo.jpg','04-support-bundle.bin','05-account.sha256','06-records.zip','checksums.sha256'},'network-analysis':{'support-session.pcap','topology.txt','capture.sha256'}}
                    name=data.get('file')
                    if name not in names.get(PROGRAM,set()):raise ValueError('Unknown evidence file')
                    raw=(Path('/evidence')/PROGRAM/name).read_bytes()
                    self.reply(200,{'content':base64.b64encode(raw).decode()});return
                if self.path=='/open':
                    if len(terminals)>=4:
                        key=next(iter(terminals));terminals.pop(key).close()
                    identity=secrets.token_urlsafe(24);terminals[identity]=Terminal();self.reply(200,{'terminal':identity});return
                terminal=terminals.get(data.get('terminal'))
                if not terminal: self.reply(404,{'error':'Terminal expired; reconnect.'});return
                if self.path=='/poll':self.reply(200,terminal.poll(int(data.get('cursor',0))))
                elif self.path=='/input':
                    raw=base64.b64decode(data['input'],validate=True)
                    if len(raw)>32768:raise ValueError('Input too large')
                    os.write(terminal.master,raw);self.reply(200,{'ok':True})
                elif self.path=='/resize':
                    rows=max(10,min(100,int(data['rows'])));cols=max(20,min(300,int(data['cols'])))
                    fcntl.ioctl(terminal.master,termios.TIOCSWINSZ,struct.pack('HHHH',rows,cols,0,0));self.reply(200,{'ok':True})
                elif self.path=='/close':terminal.close();terminals.pop(data['terminal'],None);self.reply(200,{'ok':True})
                else:self.reply(404,{'error':'Not found'})
        except (KeyError,ValueError,TypeError,OSError) as error:self.reply(400,{'error':str(error)})
        except Exception:
            import traceback;traceback.print_exc();self.reply(500,{'error':'Program operation failed; inspect service logs.'})


if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',9000),Handler).serve_forever()
