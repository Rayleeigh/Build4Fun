"""Public program catalog; expected answers never belong here."""
import json
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[3] / 'challenges' / 'crack'
PROGRAMS = ('filesystem', 'forensics', 'network-analysis', 'web-api')


def catalog():
    result = []
    for program in PROGRAMS:
        document = json.loads((CONTENT / program / 'program.json').read_text())
        assert document['id'] == program
        assert all(c['id'].startswith(document['prefix'] + '-') for c in document['challenges'])
        result.append(document)
    return result
