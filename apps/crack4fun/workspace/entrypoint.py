"""Initialize Docker volume ownership, then permanently drop controller privileges."""
import os
for path in ['/workspace',*['/controls/'+name for name in ('filesystem','forensics','network-analysis','web-api','portal')]]:
    os.makedirs(path,exist_ok=True);os.chown(path,65532,65532);os.chmod(path,0o700)
os.setgroups([]);os.setgid(65532);os.setuid(65532)
os.execvp('python',['python','apps/crack4fun/workspace/server.py','--workspace','/workspace'])
