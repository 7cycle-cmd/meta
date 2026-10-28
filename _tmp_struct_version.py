import sqlite3

c = sqlite3.connect(r"C:\projects\meta\structure\structure.db")
c.row_factory = sqlite3.Row
print("=== structure_module (version) ===")
for r in c.execute("SELECT * FROM structure_module WHERE value LIKE '%version%'"):
    print(" ", dict(r))
print("=== structure_db_table for version module ===")
for r in c.execute("SELECT * FROM structure_db_table"):
    d = dict(r)
    if "version" in str(d).lower():
        print(" ", d)
print("=== structure_db_field for version tables ===")
for r in c.execute("SELECT * FROM structure_db_field"):
    d = dict(r)
    if "version" in str(d).lower():
        print(" ", d)
c.close()
