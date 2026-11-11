"""Deliberately inspectable teaching portal. Control routes use a different listener."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import html
import json
import os
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit,parse_qs

STATE=Path('/state/portal.json')
lock=threading.RLock()


def reply(handler,status,body,kind='application/json'):
    raw=body if isinstance(body,bytes) else json.dumps(body).encode()
    handler.send_response(status);handler.send_header('Content-Type',kind);handler.send_header('Content-Length',str(len(raw)));handler.send_header('Cache-Control','no-store');handler.send_header('X-Content-Type-Options','nosniff');handler.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'");handler.end_headers();handler.wfile.write(raw)


class Control(BaseHTTPRequestHandler):
    def do_GET(self):reply(self,200,{'ready':True}) if self.path=='/health' else reply(self,404,{'error':'Not found'})
    def do_POST(self):
        try:
            token=Path('/control/token')
            if not token.exists() or not secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+token.read_text().strip()):reply(self,403,{'error':'Forbidden'});return
            if self.path not in ('/configure','/reset'):reply(self,404,{'error':'Not found'});return
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<16384:raise ValueError('Invalid request size')
            data=json.loads(self.rfile.read(length))
            with lock:
                if self.path=='/reset' or not STATE.exists() or json.loads(STATE.read_text())['session']!=data['session']:
                    STATE.parent.mkdir(exist_ok=True);STATE.write_text(json.dumps(data));STATE.chmod(0o600)
            reply(self,200,{'ready':True})
        except (ValueError,KeyError):reply(self,400,{'error':'Invalid configuration'})


class Portal(BaseHTTPRequestHandler):
    def state(self):
        if not STATE.exists():reply(self,503,{'error':'The program is preparing. Try again shortly.'});return None
        return json.loads(STATE.read_text())
    def do_GET(self):
        data=self.state()
        if not data:return
        flags=data['flags'];path=urlsplit(self.path).path
        if path=='/':
            body=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Apprentice Portal</title><link rel="stylesheet" href="/styles.css"><script src="/app.js" defer></script></head><body><header>Apprentice Portal <span>Internal training service</span></header><main><h1>Welcome to the workshop.</h1><p>Our archive and dispatch tools help prepare your training kit.</p><!-- Maintenance handover: {flags['web-01']} Find the notice that the stylesheet hides. --><aside id="maintenance-notice">{flags['web-02']} Next: inspect app.js and the API description.</aside><section><h2>Service information</h2><p id="service">Loading…</p><a href="/api/info">API description</a></section></main></body></html>'''
            reply(self,200,body.encode(),'text/html; charset=utf-8')
        elif path=='/styles.css':
            reply(self,200,b'body{margin:0;background:#f5f5f7;color:#1d1d1f;font:16px/1.7 system-ui,sans-serif}header{padding:20px 32px;background:white;border-bottom:1px solid #ddd}header span{float:right;color:#777;font-size:12px}main{max-width:720px;margin:70px auto;padding:24px}h1{font-size:38px;letter-spacing:-1px}section{background:white;padding:24px;border-radius:12px;margin-top:30px}a{color:#990000}#maintenance-notice{display:none}', 'text/css')
        elif path=='/app.js':
            reply(self,200,b'''// Archive client configuration. This is an intentionally inspectable training app.
const archiveHeader = {"X-Archive-Key": "workshop-handover"};
fetch('/api/info').then(response => response.json()).then(info => {
  document.querySelector('#service').textContent = info.name;
});''','text/javascript')
        elif path=='/api/info':reply(self,200,{'name':'Apprentice Portal API','endpoints':{'GET /api/archive':{'query':{'department':'training'},'header':'Use the archive header configured in app.js'},'POST /api/dispatch':{'content_type':'application/json','required_fields':['parcel','action'],'supported_values':'Read the training archive record.'}}})
        elif path=='/api/archive':
            if self.headers.get('X-Archive-Key')!='workshop-handover':reply(self,403,{'error':'Supply the archive header from app.js.'})
            elif parse_qs(urlsplit(self.path).query).get('department')!=['training']:reply(self,400,{'error':'Select the training department.'})
            else:reply(self,200,{'flag':flags['web-03'],'next':'POST /api/dispatch','parcel':'training-kit','action':'release'})
        else:reply(self,404,{'error':'Not found'})
    def do_POST(self):
        data=self.state()
        if not data:return
        if urlsplit(self.path).path!='/api/dispatch':reply(self,404,{'error':'Not found'});return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=4096:raise ValueError('Body too large or empty')
            if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':reply(self,415,{'error':'Use application/json'});return
            body=json.loads(self.rfile.read(length))
            if body!={'parcel':'training-kit','action':'release'}:reply(self,400,{'error':'Use the parcel and action in the training archive record.'});return
            reply(self,200,{'flag':data['flags']['web-04'],'message':'Training kit released. Handover complete.'})
        except (ValueError,TypeError):reply(self,400,{'error':'Send a valid JSON object.'})


if __name__=='__main__':
    control=ThreadingHTTPServer(('0.0.0.0',9000),Control)
    threading.Thread(target=control.serve_forever,daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0',8080),Portal).serve_forever()
