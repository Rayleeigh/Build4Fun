#!/usr/local/bin/python
"""Keep John's generated state in the learner's home, including on read-only evidence."""
import os
import sys
args=sys.argv[1:]
home=os.environ['HOME']
options=[] if any(arg.startswith('--pot=') for arg in args) else ['--pot='+home+'/.john.pot']
inspection=any(arg.startswith(('--show','--list','--test','--status','--restore','--help')) for arg in args)
if not inspection and not any(arg.startswith('--session') for arg in args):options.append('--session='+home+'/.john-session')
os.execv('/opt/john/john',['/opt/john/john',*options,*args])
