"""Generate a single program's evidence. Called only by the root bootstrap service."""
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


def write(path, text, mode=0o444):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text); path.chmod(mode)


def filesystem(flags, session):
    home = Path('/home/apprentice')
    password = 'maintenance-' + hashlib.sha256(session.encode()).hexdigest()[:10]
    subprocess.run(['chpasswd'], input='root:' + password + '\n', text=True, check=True)
    write(home/'README.txt', 'Apprentice Portal handover\n\nStart with pwd and ls -la. Your documents include a hidden maintenance note.\nRead notes/handover.txt for the next task. Flags use {token} syntax.\nThe planted .bash_history is evidence, separate from your ongoing history.\n')
    write(home/'.bash_history', 'cd /var/log/portal\nexport ROOT_PASSWORD="'+password+'"\nsu -\n')
    write(home/'notes/handover.txt', 'Find the HANDOVER_ACCEPTED event in /var/log/portal/maintenance.log.\nThe previous administrator also left a shell history file in this home directory.\n')
    write(home/'documents/.maintenance-note', 'Hidden does not mean protected.\n'+flags['fs-01']+'\n')
    write('/var/log/portal/maintenance.log', '09:00 SERVICE_STARTED\n09:10 HANDOVER_ACCEPTED '+flags['fs-02']+'\n09:20 CHECKS_FINISHED\n')
    write('/root/flag.txt', flags['fs-03']+'\n', 0o600)
    write('/root/closure-note.txt', 'Complete the handover by locating inventory record TRAIN-417 in /home/apprentice/documents/inventory.txt.\n', 0o600)
    write(home/'documents/inventory.txt', 'TRAIN-102 keyboard\nTRAIN-417 training-kit '+flags['fs-04']+'\nTRAIN-830 monitor\n')
    Path('/root').chmod(0o700)
    for path in home.rglob('*'):
        if path.is_file(): os.chown(path, 1000, 1000)


def forensics(flags, destination):
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=True)
    message = b'Apprentice incident evidence\n' + flags['fo-01'].encode() + b'\nNext: identify 02-recovered.dat\n'
    dump = subprocess.run(['xxd', '-g', '1'], input=message, capture_output=True, check=True).stdout
    (destination/'01-message.hex').write_bytes(dump)
    info=PngInfo(); info.add_text('Comment', flags['fo-02']+' Next: inspect the workshop photograph metadata.')
    Image.new('RGB',(48,48),(190,200,210)).save(destination/'02-recovered.dat',format='PNG',pnginfo=info)
    Image.new('RGB',(48,48),(210,200,190)).save(destination/'03-workshop-photo.jpg',format='JPEG')
    subprocess.run(['exiftool','-overwrite_original','-Comment='+flags['fo-03']+' Inspect the support bundle next.',str(destination/'03-workshop-photo.jpg')],check=True,capture_output=True)
    embedded=io.BytesIO()
    with zipfile.ZipFile(embedded,'w',compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('support-note.txt',flags['fo-04']+'\nNext: recover the fictional account password from 05-account.sha256 using the supplied RockYou wordlist. It unlocks 06-records.zip.\n')
    header=b'SUPPORT EXPORT\nZIP starts at byte offset 128.\n'
    (destination/'04-support-bundle.bin').write_bytes(header.ljust(128,b'\0')+embedded.getvalue())
    # Choose a real, early member without changing or truncating the supplied wordlist.
    wordlist=Path('/wordlists/rockyou.txt')
    candidates=[]
    with wordlist.open('rb') as stream:
        for _ in range(128):
            word=stream.readline().rstrip(b'\r\n')
            if 6<=len(word)<=14 and word.isascii() and word.isalnum(): candidates.append(word.decode())
    if not candidates: raise ValueError('RockYou is unavailable or has no usable early entries.')
    password=candidates[int(hashlib.sha256(flags['fo-05'].encode()).hexdigest()[:4],16)%len(candidates)]
    write(destination/'05-account.sha256',hashlib.sha256(password.encode()).hexdigest()+'\n')
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary)
        write(root/'recovery-note.txt',flags['fo-05']+'\nCorrelate the dispatch restart at 10:42 in events.log with records.csv. Decode the matching Base64 payload.\n')
        write(root/'events.log','10:40 backup complete record=103\n10:42 dispatch restarted record=417\n10:44 inventory checked record=830\n')
        with (root/'records.csv').open('w') as output:
            writer=csv.writer(output);writer.writerow(['record_id','payload_base64'])
            for identity,text in [('103','routine backup'),('417',flags['fo-06']),('830','inventory checked')]:
                writer.writerow([identity,base64.b64encode(text.encode()).decode()])
        archive=destination/'06-records.zip'
        if archive.exists(): archive.unlink()
        subprocess.run(['zip','-q','-P',password,str(archive.resolve()),'recovery-note.txt','events.log','records.csv'],cwd=root,check=True)
    write(destination/'README.txt','Incident evidence\n\nStart with 01-message.hex, then follow the numbered files. Work in /work.\nTools: xxd, file, strings, exiftool, binwalk, dd, unzip, john.\nThe account uses a deliberately weak unsalted SHA-256 password hash.\nRockYou is available at /wordlists/rockyou.txt. No GPU is required.\nOriginal evidence is read-only.\n')
    checksums=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(destination.iterdir()) if p.is_file())
    write(destination/'checksums.sha256',checksums)


def network(flags, destination):
    from scapy.all import Ether, IP, TCP, UDP, DNS, DNSQR, DNSRR, Raw, wrpcap
    root=Path(destination);root.mkdir(parents=True,exist_ok=True)
    client,server,dns='192.0.2.10','198.51.100.20','192.0.2.53'
    packets=[Ether(src='02:00:00:00:00:10',dst='02:00:00:00:00:53')/IP(src=client,dst=dns)/UDP(sport=53000,dport=53)/DNS(id=17,qd=DNSQR(qname='portal.training.test')),
             Ether(src='02:00:00:00:00:53',dst='02:00:00:00:00:10')/IP(src=dns,dst=client)/UDP(sport=53,dport=53000)/DNS(id=17,qr=1,qd=DNSQR(qname='portal.training.test'),an=DNSRR(rrname='portal.training.test',rdata=server))]
    exchanges=[('/',('Welcome to the support session. '+flags['net-01']+'\nNext: inspect response headers on /status.\n').encode(),[]),
               ('/status',b'Download /reports/handover.txt\n',[('X-Training-Flag',flags['net-02'])]),
               ('/reports/handover.txt',(flags['net-03']+'\nHandover complete.\n').encode(),[])]
    for index,(path,body,headers) in enumerate(exchanges):
        sport=41000+index
        request=f'GET {path} HTTP/1.1\r\nHost: portal.training.test\r\nConnection: close\r\n\r\n'.encode()
        response=('HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: '+str(len(body))+'\r\n'+''.join(k+': '+v+'\r\n' for k,v in headers)+'Connection: close\r\n\r\n').encode()+body
        def packet(reverse=False,**kwargs):
            return Ether(src='02:00:00:00:00:20' if reverse else '02:00:00:00:00:10',dst='02:00:00:00:00:10' if reverse else '02:00:00:00:00:20')/IP(src=server if reverse else client,dst=client if reverse else server)/TCP(sport=80 if reverse else sport,dport=sport if reverse else 80,**kwargs)
        packets.extend([packet(flags='S',seq=100),packet(True,flags='SA',seq=500,ack=101),packet(flags='A',seq=101,ack=501),
                        packet(flags='PA',seq=101,ack=501)/Raw(request),packet(True,flags='A',seq=501,ack=101+len(request))])
        # Deliberately split the transferred object to exercise actual stream reassembly.
        split=min(len(response)-1,len(response)//2)
        packets.extend([packet(True,flags='PA',seq=501,ack=101+len(request))/Raw(response[:split]),
                        packet(True,flags='PA',seq=501+split,ack=101+len(request))/Raw(response[split:]),
                        packet(flags='A',seq=101+len(request),ack=501+len(response)),
                        packet(True,flags='FA',seq=501+len(response),ack=101+len(request)),
                        packet(flags='FA',seq=101+len(request),ack=502+len(response)),
                        packet(True,flags='A',seq=502+len(response),ack=102+len(request))])
    for index,p in enumerate(packets):p.time=1700000000+index*.1
    capture=root/'support-session.pcap';wrpcap(str(capture),packets)
    write(root/'topology.txt','Support laptop: 192.0.2.10\nDNS: 192.0.2.53\nFind portal.training.test using the DNS exchange.\nThis synthetic capture uses deliberately plaintext HTTP, not decrypted HTTPS.\n')
    write(root/'README.txt','Recorded support incident\n\nAnalyze support-session.pcap with tshark -r. Start with DNS, then follow HTTP.\nWork in /work. Use --export-objects http,/work/exported to reconstruct HTTP objects.\nNo live interception or network capture is required.\n')
    write(root/'capture.sha256',hashlib.sha256(capture.read_bytes()).hexdigest()+'  support-session.pcap\n')


def provision(program, flags, session):
    if program=='filesystem':filesystem(flags,session)
    elif program in ('forensics','network-analysis'):
        root=Path('/evidence')/program
        if root.exists():shutil.rmtree(root)
        (forensics if program=='forensics' else network)(flags,root)
        for p in root.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
        root.chmod(0o555)
    else:
        write('/home/apprentice/README.txt','Apprentice Portal\n\nUse curl http://portal:8080/ to inspect the website.\nGET /api/info describes the API. The browser preview is available in Crack4Fun.\nWork in /work and keep notes as you follow the clues.\n')
