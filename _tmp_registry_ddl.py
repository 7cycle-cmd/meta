import glob
import os
import sqlite3

root = r"C:\projects\meta"
for db in sorted(glob.glob(os.path.join(root, "*", "*.db"))):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = c.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='registry'"
        ).fetchone()
        if not row:
            continue
        n = c.execute("SELECT COUNT(*) FROM registry").fetchone()[0]
        print(f"--- {os.path.basename(db)}  (rows={n})")
        print("   ", " ".join(row[0].split()))
    finally:
        c.close()
