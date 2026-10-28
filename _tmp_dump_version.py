import sqlite3

c = sqlite3.connect(r"C:\projects\meta\version\version.db")
c.row_factory = sqlite3.Row
print("=== objects ===")
for r in c.execute("SELECT type, name FROM sqlite_master ORDER BY type, name"):
    print(" ", r["type"], r["name"])
print("=== counts ===")
for r in c.execute("SELECT type, name FROM sqlite_master WHERE type='table' ORDER BY name"):
    n = c.execute(f'SELECT COUNT(*) FROM "{r["name"]}"').fetchone()[0]
    print(f"  {r['name']}: {n}")
print("=== version rows ===")
for r in c.execute("SELECT * FROM version"):
    print(" ", dict(r))
print("=== registry rows ===")
try:
    for r in c.execute("SELECT * FROM registry"):
        print(" ", dict(r))
except Exception as e:
    print("  ERR", e)
print("=== github rows ===")
for r in c.execute("SELECT * FROM github"):
    print(" ", dict(r))
c.close()
