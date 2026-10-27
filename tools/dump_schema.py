"""dump_schema.py — 自動 dump 所有 module DB 嘅表結構做 .sql（GitHub backup）

用法：
    python tools/dump_schema.py [base_dir]

掃描 base_dir 下所有 *.db（skip *.bak* / 內部表），
每個 DB 寫一個 schema_dump/<db_name>.sql（CREATE TABLE / VIEW / TRIGGER / INDEX）。
schema_dump/ 入 repo -> GitHub 有齊所有表結構 backup + diff + history。

GitHub Actions 每次 push 自動跑（.github/workflows/schema-dump.yml）。
本地想即時 dump 都得：python tools/dump_schema.py
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def dump_db(db_path: Path, out_dir: Path) -> int:
    """dump 一個 db -> out_dir/<name>.sql；返回對象數（0 = 冇嘢可 dump）"""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error as e:
        print(f"  [skip] {db_path.name}: {e}")
        return 0
    try:
        rows = conn.execute(
            "SELECT type, name, sql FROM sqlite_master"
            " WHERE sql IS NOT NULL"
            " ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'view' THEN 1"
            "  WHEN 'trigger' THEN 2 ELSE 3 END, name").fetchall()
    finally:
        conn.close()
    if not rows:
        return 0
    n_tables = sum(1 for r in rows if r[0] == "table")
    lines = [
        f"-- schema dump: {db_path.name}",
        f"-- generated : {datetime.now().isoformat(timespec='seconds')}",
        f"-- objects   : {len(rows)}（table={n_tables}）",
        "",
    ]
    for _type, name, sql in rows:
        lines.append(f"-- [{_type}] {name}")
        lines.append(sql.rstrip() + ";")
        lines.append("")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{db_path.stem}.sql").write_text(
        "\n".join(lines), encoding="utf-8")
    return len(rows)


def main(base: str) -> int:
    base = Path(base)
    out = base / "schema_dump"
    total_dbs = 0
    total_objs = 0
    print(f"掃描 {base} ...")
    # 遞歸掃描所有子資料夾（每個 module 一個 .db），skip .git / __pycache__
    for db in sorted(base.rglob("*.db")):
        if ".bak" in db.name:
            continue
        if any(part in (".git", "__pycache__", ".venv", "venv", "env")
               for part in db.parts):
            continue
        n = dump_db(db, out)
        if n:
            total_dbs += 1
            total_objs += n
            print(f"  {db.relative_to(base)}: {n} 個對象")
    print(f"完成：{total_dbs} 個 DB，{total_objs} 個表/視圖/觸發器"
          f" -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else r"C:\projects\meta"))