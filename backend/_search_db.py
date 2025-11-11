from pathlib import Path
rows = []
for path in Path("organizations").rglob("test.db"):
    rows.append(path)
if rows:
    for r in rows:
        print("found", r)
else:
    print("no clones")
