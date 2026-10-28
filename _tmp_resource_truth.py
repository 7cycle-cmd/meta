# -*- coding: utf-8 -*-
import sqlite3

# 1. resource 喺 source.db 有冇證明
c = sqlite3.connect(r"C:\projects\meta\source\source.db")
c.row_factory = sqlite3.Row
print("--- source_proof resource ---")
rows = c.execute(
    "SELECT sp.id, sp.word, sp.source_id, sp.registered_by,"
    " s.source FROM source_proof sp"
    " LEFT JOIN source s ON s.id = sp.source_id"
    " WHERE LOWER(sp.word) = 'resource'").fetchall()
for r in rows:
    print(dict(r))
if not rows:
    print("(冇 resource 證明)")
c.close()

# 2. resource 喺 terminology.db word_category
c = sqlite3.connect(r"C:\projects\meta\terminology\terminology.db")
c.row_factory = sqlite3.Row
print("--- word_category resource ---")
for r in c.execute(
        "SELECT id, word, spec, has_proof FROM word_category"
        " WHERE LOWER(word) = 'resource'"):
    print(dict(r))
print("--- run resource 最近 ---")
for r in c.execute(
        "SELECT r.id, v.value, r.status_id, f.flow_name"
        " FROM run r JOIN value v ON v.id = r.value_id"
        " LEFT JOIN flow f ON f.id = r.flow_id"
        " WHERE LOWER(v.value) = 'resource' ORDER BY r.id DESC LIMIT 5"):
    print(dict(r))
c.close()

# 3. 而家 _auto_answers source_register 個 hardcode 喺邊
import re
src = open(r"C:\projects\meta\terminology\sql.py", encoding="utf-8").read()
for m in re.finditer(r".*source_id=8.*", src):
    print("HARDCODE:", m.group(0).strip())