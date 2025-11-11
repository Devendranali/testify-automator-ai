import os
from pathlib import Path
backend_root = Path('.').resolve()
org_root = backend_root / 'organizations'
print('backend_root', backend_root)
print('org exists', org_root.exists())
found = []
if org_root.exists():
    for sub in org_root.rglob('generated_runs'):
        src = sub / 'src'
        if src.exists():
            found.append(src)
print('found src dirs', len(found))
for path in found:
    print(' -', path)
