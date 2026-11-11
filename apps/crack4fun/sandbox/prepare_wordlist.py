"""Build-time provisioning of an unchanged, pinned RockYou wordlist."""
import hashlib,json,shutil,tarfile,tempfile
from pathlib import Path
from urllib.request import urlopen
revision='64b41f2156e1ae3edb592535c1b4b4dd0d6fe26a'
url=f'https://raw.githubusercontent.com/danielmiessler/SecLists/{revision}/Passwords/Leaked-Databases/rockyou.txt.tar.gz'
root=Path('/wordlists');root.mkdir(exist_ok=True)
with tempfile.NamedTemporaryFile() as temporary:
    with urlopen(url,timeout=120) as response:shutil.copyfileobj(response,temporary)
    temporary.flush()
    with tarfile.open(temporary.name) as archive:
        member=next(m for m in archive.getmembers() if Path(m.name).name=='rockyou.txt' and m.isfile())
        with archive.extractfile(member) as source,(root/'rockyou.txt').open('wb') as output:shutil.copyfileobj(source,output)
path=root/'rockyou.txt'
with path.open('rb') as stream:lines=sum(1 for _ in stream)
if lines<10_000_000:raise ValueError('Unexpectedly small RockYou file')
(root/'provenance.json').write_text(json.dumps({'source':url,'revision':revision,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'lines':lines,'encoding':'original bytes; mixed legacy text, not rewritten'},indent=2))
path.chmod(0o444)
