import glob
import os
import sqlite3

root = r"C:\projects\meta"
for db in sorted(glob.glob(os.path.join(root, "*", "*.db"))):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        tabs = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        print(f"{os.path.basename(db):<24} {', '.join(tabs)}")
    finally:
        c.close()
