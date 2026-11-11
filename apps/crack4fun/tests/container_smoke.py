"""Exercise real artifacts, PTY, cracking tools, browser UI, and network boundaries."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import uuid

ROOT=Path(__file__).resolve().parents[3]
FLAG=re.compile(r'\{[a-z0-9_]+\}')


def free_port():
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--keep',action='store_true');args=parser.parse_args()
    port,portal_port=free_port(),free_port()
    while port==portal_port:portal_port=free_port()
    env={**os.environ,'CRACK_HTTP_PORT':str(port),'CRACK_PORTAL_PORT':str(portal_port)}
    command=['docker','compose','-f',str(ROOT/'compose.crack4fun.yaml'),'-p','crack4fun-check-'+uuid.uuid4().hex[:8]]
    origin=f'http://127.0.0.1:{port}'
    def compose(*parts,**kwargs):return subprocess.run(command+list(parts),cwd=ROOT,env=env,**kwargs)
    def inside(service,cmd,user='1000'):
        result=compose('exec','-T','--user',user,service,'bash','-lec',cmd,capture_output=True,text=True,timeout=90)
        if result.returncode:raise AssertionError((service,cmd,result.stderr,result.stdout))
        return result.stdout
    def api(path,data=None):
        req=Request(origin+'/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Origin':origin,'Content-Type':'application/json'})
        with urlopen(req,timeout=70) as response:return json.load(response)
    def submit(program,flag):
        prefix=flag[1:].split('_')[0];number=flag[1:].split('_')[1]
        result=api('submit',{'program':program,'challenge':prefix+'-'+number,'flag':flag});assert result['correct'],result
    try:
        compose('up','--build','-d','--wait','--wait-timeout','180',check=True)
        for attempt in range(60):
            state=api('state')
            if all(state['ready'].values()):break
            time.sleep(.5)
        else:raise AssertionError(state['errors'])
        assert len(state['programs'])==4
        try:
            urlopen(Request(origin+'/api/state',headers={'Host':'untrusted.example'}))
            raise AssertionError('Untrusted Host accepted')
        except HTTPError as error:assert error.code==403
        try:
            urlopen(Request(origin+'/api/submit',data=b'{}',headers={'Origin':'http://untrusted.example'}))
            raise AssertionError('Cross-origin write accepted')
        except HTTPError as error:assert error.code==403
        with urlopen(origin+'/api/download?program=network-analysis&file=support-session.pcap') as response:
            assert response.read(4) in (b'\xd4\xc3\xb2\xa1',b'\xa1\xb2\xc3\xd4')
        try:
            urlopen(origin+'/api/download?program=forensics&file=../../control/token')
            raise AssertionError('Arbitrary file download accepted')
        except HTTPError as error:assert error.code==400

        # No answer catalog crosses the public API.
        assert not FLAG.search(json.dumps(state))
        # Filesystem: actual permissions, hidden evidence, and password elevation.
        source=inside('filesystem','cat /home/apprentice/documents/.maintenance-note /var/log/portal/maintenance.log /home/apprentice/documents/inventory.txt')
        for flag in FLAG.findall(source):submit('filesystem',flag)
        denial=compose('exec','-T','--user','1000','filesystem','cat','/root/flag.txt',capture_output=True,text=True)
        assert denial.returncode!=0
        history=inside('filesystem','cat /home/apprentice/.bash_history')
        password=re.search(r'ROOT_PASSWORD="([^"]+)"',history)[1]
        terminal=api('terminal',{'program':'filesystem','action':'open'})['terminal'];cursor=0;output=''
        def send(text):api('terminal',{'program':'filesystem','action':'input','terminal':terminal,'input':base64.b64encode(text.encode()).decode()})
        def until(text,timeout=10):
            nonlocal cursor,output
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                result=api('terminal',{'program':'filesystem','action':'poll','terminal':terminal,'cursor':cursor});cursor=result['cursor'];output+=base64.b64decode(result['output']).decode(errors='replace')
                if text in output:return
                time.sleep(.1)
            raise AssertionError('Terminal did not produce '+text+': '+output[-300:])
        until('$');send('su -\r');until('Password:');send(password+'\r');time.sleep(.3);send('cat /root/flag.txt\r');until('{fs_03_')
        submit('filesystem',next(f for f in FLAG.findall(output) if f.startswith('{fs_03_')))
        # Root cannot reach another program or the controller's management listener.
        inside('filesystem',"python -c \"import socket; s=socket.socket();s.settimeout(1);assert s.connect_ex(('workspace',8100))!=0\"",user='0')
        isolated=compose('exec','-T','filesystem','curl','--connect-timeout','1','-fsS','http://forensics:9000/health',capture_output=True)
        assert isolated.returncode!=0
        denied=compose('exec','-T','--user','1000','forensics','cat','/control/token',capture_output=True)
        assert denied.returncode!=0
        # Actual evidence tools, not mocked solve responses.
        evidence=inside('forensics','xxd -r /evidence/forensics/01-message.hex; strings /evidence/forensics/02-recovered.dat; exiftool /evidence/forensics/03-workshop-photo.jpg')
        for flag in FLAG.findall(evidence):submit('forensics',flag)
        embedded=inside('forensics','dd if=/evidence/forensics/04-support-bundle.bin of=/work/support.zip bs=1 skip=128 status=none && unzip -oq /work/support.zip -d /work/support && cat /work/support/support-note.txt')
        submit('forensics',FLAG.search(embedded)[0])
        started=time.monotonic()
        inside('forensics','john --format=raw-sha256 --wordlist=/wordlists/rockyou.txt /evidence/forensics/05-account.sha256')
        elapsed=time.monotonic()-started
        recovered=inside('forensics','john --show --format=raw-sha256 /evidence/forensics/05-account.sha256')
        password=next(line.split(':')[1] for line in recovered.splitlines() if line.startswith('?:'))
        # Pass the synthetic password without shell interpolation.
        result=compose('exec','-T','--user','1000','forensics','unzip','-oq','-P',password,'/evidence/forensics/06-records.zip','-d','/work/records',capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        final=inside('forensics','cat /work/records/recovery-note.txt; python -c \'import csv,base64; print(next(base64.b64decode(r["payload_base64"]).decode() for r in csv.DictReader(open("/work/records/records.csv")) if r["record_id"]=="417"))\'')
        for flag in FLAG.findall(final):submit('forensics',flag)
        print(f'Real CPU-only John recovery completed in {elapsed:.2f}s.')
        # tshark reconstructs the split HTTP objects in the prepared capture.
        network=inside('network','mkdir -p /work/exported && tshark -r /evidence/network-analysis/support-session.pcap --export-objects http,/work/exported >/dev/null && cat /work/exported/*; tshark -r /evidence/network-analysis/support-session.pcap -Y http -V')
        for flag in set(FLAG.findall(network)):submit('network-analysis',flag)
        # Real portal requests, including the intentionally documented header/body contracts.
        web=inside('web-terminal',"curl -fsS http://portal:8080/; curl -fsS -H 'X-Archive-Key: workshop-handover' 'http://portal:8080/api/archive?department=training'; curl -fsS -H 'Content-Type: application/json' -d '{\"parcel\":\"training-kit\",\"action\":\"release\"}' http://portal:8080/api/dispatch")
        for flag in set(FLAG.findall(web)):submit('web-api',flag)
        state=api('state');assert len(state['completed'])==17,state['completed']
        first=FLAG.search(source)[0];assert api('submit',{'program':'filesystem','challenge':'fs-01','flag':first})['already']
        # Restore changes evidence/work only, keeping flags and completed progress stable.
        inside('forensics','echo scratch >/work/scratch')
        api('restore',{'program':'forensics','confirm':True})
        assert not inside('forensics','test -e /work/scratch && echo exists || true')
        assert len(api('state')['completed'])==17
        compose('restart','workspace',check=True)
        for _ in range(40):
            try:state=api('state');break
            except OSError:time.sleep(.25)
        assert len(state['completed'])==17
        # Browser uses the real PTY through the controller, and progress survives reload.
        from playwright.sync_api import sync_playwright,expect
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            started=time.monotonic()
            page.goto(origin);expect(page.locator('#program-title')).to_have_text('Filesystem');expect(page.locator('#progress-count')).to_have_text('4/4')
            page.wait_for_function('()=>document.querySelector("#connection").textContent==="Connected"')
            page.wait_for_function('''()=>{const b=terminals.get(active)?.term.buffer.active;return b&&Array.from({length:b.length},(_,i)=>b.getLine(i)?.translateToString()||'').join('').includes('apprentice@')}''')
            print(f'Warm stack browser-to-shell prompt: {time.monotonic()-started:.2f}s.')
            expect(page.locator('#tour')).to_be_visible()
            expect(page.locator('#tour-title')).to_have_text('Learn to follow the clues.')
            page.locator('#tour-next').click();expect(page.locator('#tour-code')).to_have_text('{example_training_flag}')
            page.locator('#tour-back').click();expect(page.locator('#tour-count')).to_have_text('1 of 11')
            page.keyboard.press('Tab');assert page.evaluate('document.activeElement.closest("#tour") !== null')
            page.locator('#tour-skip').click();expect(page.locator('#tour')).not_to_be_visible()
            page.reload();expect(page.locator('#program-title')).to_have_text('Filesystem');expect(page.locator('#tour')).not_to_be_visible()
            page.locator('#tutorial').click()
            for step in range(11):
                expect(page.locator('#tour-count')).to_have_text(f'{step+1} of 11')
                if step>=4:expect(page.locator('#tour-spotlight')).to_be_visible()
                page.locator('#tour-next').click()
            expect(page.locator('#tour')).not_to_be_visible()
            assert api('state')['tutorial_seen']
            page.wait_for_function('()=>document.querySelector("#connection").textContent==="Connected"')
            page.locator('.xterm-helper-textarea').fill('')
            page.locator('.xterm-helper-textarea').press('i');page.keyboard.type('d');page.keyboard.press('Enter')
            page.wait_for_function('''()=>{const buffer=terminals.get(active)?.term.buffer.active;return buffer&&Array.from({length:buffer.length},(_,i)=>buffer.getLine(i)?.translateToString()||'').join('\\n').includes('uid=1000')}''')
            page.get_by_role('button',name='Web/API',exact=False).first.click();expect(page.locator('#program-title')).to_have_text('Web/API')
            page.locator('#portal-view').click();page.frame_locator('#portal').get_by_role('heading',name='Welcome to the workshop.').wait_for()
            page.screenshot(path='/tmp/crack4fun-desktop.png',full_page=True)
            page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.locator('.mission').bounding_box()['width']>300
            assert page.locator('.lab').bounding_box()['width']>300
            page.emulate_media(reduced_motion='reduce')
            page.locator('#tutorial').click()
            for step in range(11):
                expect(page.locator('#tour-count')).to_have_text(f'{step+1} of 11')
                box=page.locator('#tour-card').bounding_box()
                assert box['x']>=0 and box['x']+box['width']<=391
                assert box['y']>=0 and box['y']+box['height']<=845
                if step==4:
                    expect(page.locator('.sidebar')).to_be_visible()
                    page.screenshot(path='/tmp/crack4fun-tutorial-mobile.png')
                page.locator('#tour-next').click()
            expect(page.locator('#tour')).not_to_be_visible()
            page.locator('#tutorial').click();page.keyboard.press('Escape');expect(page.locator('#tour')).not_to_be_visible()
            page.screenshot(path='/tmp/crack4fun-mobile.png',full_page=True)
            assert not errors,errors;browser.close()
        print('All 17 flags, actual tool solve paths, PTY root exercise, boundaries, reset, persistence, and browser checks passed.')
    except Exception:
        compose('logs','--tail','60')
        raise
    finally:
        if not args.keep:compose('down','--volumes','--remove-orphans',check=True)


if __name__=='__main__':main()
