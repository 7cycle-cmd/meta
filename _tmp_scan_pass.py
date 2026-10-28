import glob
import os
import sqlite3

root = r"C:\projects\meta"
for db in sorted(glob.glob(os.path.join(root, "*", "*.db"))):
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except Exception as e:
        print("OPEN ERR", db, e)
        continue
    try:
        tabs = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        hits = []
        for t in tabs:
            if "pass" in t.lower():
                hits.append(("TABLE", t))
            try:
                cols = [r[1] for r in c.execute(f'PRAGMA table_info("{t}")')]
            except Exception:
                continue
            for col in cols:
                if "pass" in col.lower():
                    hits.append(("COL", f"{t}.{col}"))
        if hits:
            print(f"--- {os.path.basename(db)}")
            for k, v in hits:
                print(f"    {k}: {v}")
    finally:
        c.close()
