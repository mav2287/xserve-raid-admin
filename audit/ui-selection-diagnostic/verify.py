"""Verify archived boundary pilot bytes without Java, network or real profiles."""
from pathlib import Path
import hashlib
import json
import re

root = Path(__file__).resolve().parent
receipt = json.loads((root / 'boundary-receipt.json').read_text())
for name, expected in receipt['archived_sha256'].items():
    assert Path(name).name == name, 'Unexpected archive path'
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
text = (root / 'boundaries-original.stdout').read_text()
assert [int(n) for n in re.findall(r'^STEP (\d+) ', text, re.M)] == list(range(1, 61))
assert 'SCENARIOS count=60 tick_ms=1000;' in text
assert 'transitions=60;' in text
assert 'stale_generations_at_tick=0' in text
assert 'java_guard_prohibited_operations=0' in text
assert receipt['steps'] == 60 and receipt['intended_timer_ms'] == 1000
print('PASS archived boundary diagnostic: hashes and 60 steps; no full-app or hardware qualification')
