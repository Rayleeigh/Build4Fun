"""Trusted local Crack4Fun controller. No Docker socket and no learner shell in this service."""
import argparse
import base64
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import threading
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit,parse_qs
from urllib.request import Request,urlopen
from programs import catalog,PROGRAMS
from progress import Store

STATIC=Path(__file__).parent/'static'


class Runtime:
    def __init__(self,store,control_root='/controls',hosts=None):
        self.store=store;self.controls=Path(control_root);self.controls.mkdir(parents=True,exist_ok=True)
        self.hosts=hosts or {p:os.environ.get('CRACK_'+p.upper().replace('-','_')+'_URL','http://'+{'filesystem':'filesystem','forensics':'forensics','network-analysis':'network','web-api':'web-terminal'}[p]+':9000') for p in PROGRAMS}
        self.hosts['portal']=os.environ.get('CRACK_PORTAL_CONTROL_URL','http://portal:9000')
        self.tokens={}
        self.ready={p:False for p in PROGRAMS};self.errors={};self.locks={p:threading.Lock() for p in PROGRAMS}
        for name in (*PROGRAMS,'portal'):
            root=self.controls/name;root.mkdir(exist_ok=True)
            path=root/'token'
            try:
                fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                with os.fdopen(fd,'w') as output:output.write(secrets.token_urlsafe(32))
            except FileExistsError:pass
            fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(fd) as source:self.tokens[name]=source.read().strip()

    def call(self,name,path,data,timeout=8):
        token=self.tokens[name]
        request=Request(self.hosts[name]+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        try:
            with urlopen(request,timeout=timeout) as response:return json.load(response)
        except HTTPError as error:
            try:message=json.load(error).get('error','Program request failed')
            except Exception:message='Program request failed'
            raise ValueError(message) from error
        except (URLError,TimeoutError,OSError) as error:raise ValueError('Program service unavailable. Check the stack and reconnect.') from error

    def configure(self,program,reset=False):
        with self.locks[program]:
            try:
                item=next(p for p in catalog() if p['id']==program)
                data={'session':self.store.public()['session'],'flags':{c['id']:self.store.flag(c['id']) for c in item['challenges']}}
                self.call(program,'/reset' if reset else '/configure',data,timeout=60)
                if program=='web-api':self.call('portal','/reset' if reset else '/configure',data)
                self.ready[program]=True;self.errors.pop(program,None)
            except Exception as error:self.ready[program]=False;self.errors[program]=str(error);raise

    def start(self):
        def prepare(program):
            try:self.configure(program)
            except Exception:pass
        for program in PROGRAMS:threading.Thread(target=prepare,args=(program,),daemon=True).start()


def make_handler(store,runtime,public_port=8100,portal_port=8101):
    class Handler(BaseHTTPRequestHandler):
        def reply(self,status,data,kind='application/json'):
            raw=data if isinstance(data,bytes) else json.dumps(data).encode()
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',f"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-src http://localhost:{portal_port} http://127.0.0.1:{portal_port}; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers();self.wfile.write(raw)
        def allowed(self,mutation=False):
            ports=(self.server.server_port,public_port)
            host=self.headers.get('Host','')
            if host not in {f'{name}:{port}' for name in ('localhost','127.0.0.1') for port in ports}:
                self.reply(403,{'error':'Open Crack4Fun using localhost and its published port.'});return False
            if mutation and self.headers.get('Origin')!='http://'+host:
                self.reply(403,{'error':'Same-origin requests are required.'});return False
            return True
        def do_GET(self):
            if not self.allowed():return
            path=urlsplit(self.path).path
            if path=='/api/state':
                self.reply(200,{**store.public(),'programs':catalog(),'ready':runtime.ready,'errors':runtime.errors,'portal_port':portal_port})
            elif path=='/api/download':
                try:
                    query=parse_qs(urlsplit(self.path).query)
                    program=query.get('program',[''])[0];name=query.get('file',[''])[0]
                    if program not in ('forensics','network-analysis'):raise ValueError('Choose an evidence program')
                    result=runtime.call(program,'/artifact',{'file':name})
                    self.reply(200,base64.b64decode(result['content']),'application/octet-stream')
                except (ValueError,KeyError):self.reply(400,{'error':'Evidence file unavailable or unknown.'})
            elif path in ('/','/app.js','/style.css','/vendor/xterm.js','/vendor/xterm.css'):
                name='index.html' if path=='/' else path[1:]
                kind='text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
                self.reply(200,(STATIC/name).read_bytes(),kind+'; charset=utf-8')
            else:self.reply(404,{'error':'Not found'})
        def do_POST(self):
            if not self.allowed(True):return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=65536:raise ValueError('Invalid request size')
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict):raise ValueError('Expected a JSON object')
                program=data.get('program',store.public()['active'])
                if program not in PROGRAMS:raise ValueError('Unknown program')
                path=urlsplit(self.path).path
                if path=='/api/activate':store.activate(program);self.reply(200,store.public())
                elif path=='/api/tutorial':store.finish_tutorial();self.reply(200,store.public())
                elif path=='/api/submit':
                    valid={c['id'] for p in catalog() if p['id']==program for c in p['challenges']}
                    if data.get('challenge') not in valid:raise ValueError('Choose a challenge from this program')
                    self.reply(200,{**store.submit(data['challenge'],data.get('flag')),'state':store.public()})
                elif path=='/api/restore':
                    if data.get('confirm') is not True:raise ValueError('Confirm restoring scenario files')
                    runtime.configure(program,reset=True);self.reply(200,{'message':'Scenario files restored. Progress was kept.'})
                elif path=='/api/clear-progress':
                    if data.get('confirm') is not True:raise ValueError('Confirm clearing progress')
                    item=next(p for p in catalog() if p['id']==program);store.clear(item['prefix']);self.reply(200,store.public())
                elif path=='/api/prepare':runtime.configure(program);self.reply(200,{'ready':True})
                elif path=='/api/terminal':
                    if not runtime.ready[program]:raise ValueError('Program is still preparing. Use Prepare / Retry.')
                    action=data.get('action')
                    if action not in ('open','poll','input','resize','close'):raise ValueError('Unknown terminal action')
                    self.reply(200,runtime.call(program,'/'+action,data))
                else:self.reply(404,{'error':'Not found'})
            except (ValueError,KeyError,TypeError) as error:self.reply(400,{'error':str(error)})
            except Exception:
                import traceback;traceback.print_exc();self.reply(500,{'error':'Operation failed. Inspect workspace logs.'})
    return Handler


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8100);parser.add_argument('--bind',default='127.0.0.1');parser.add_argument('--workspace',default='.workspace/crack4fun');args=parser.parse_args()
    # Bind only the UI network address: learner networks cannot reach the controller API.
    bind=socket.gethostbyname(os.environ['CRACK_UI_HOST']) if os.environ.get('CRACK_UI_HOST') else args.bind
    store=Store(args.workspace);runtime=Runtime(store,os.environ.get('CRACK_CONTROLS','/controls'));runtime.start()
    ThreadingHTTPServer((bind,args.port),make_handler(store,runtime,int(os.environ.get('CRACK_HTTP_PORT',8100)),int(os.environ.get('CRACK_PORTAL_PORT',8101)))).serve_forever()
