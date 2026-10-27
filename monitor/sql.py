"""sql.py — monitor.db 存取層（全站當前計數快照）"""

import os
import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\monitor\monitor.db"
STRUCTURE_DB = r"C:\projects\meta\structure\structure.db"
TAXONOMY_DB = r"C:\projects\meta\taxonomy\taxonomy.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(CURRENT_STRUCTURE_DDL + CURRENT_TAXONOMY_DDL)
        self.conn.commit()

    # ---------- current_structure（structure.db 各實體類型行數） ----------
    def _real_structure_totals(self):
        """掃 structure.db：structure_type_id -> 真實行數"""
        out = {}
        try:
            src = sqlite3.connect(f"file:{STRUCTURE_DB}?mode=ro", uri=True)
            src.row_factory = sqlite3.Row
            try:
                # structure_type 字典
                types = [r["id"] for r in src.execute(
                    "SELECT id FROM structure_type WHERE is_active = 1")]
                # 各層表：structure_type_id 對應行數
                for tid in types:
                    meta = src.execute(
                        "SELECT meta FROM structure_type WHERE id = ?",
                        (tid,)).fetchone()["meta"]
                    tbl = {
                        "package": "structure_module",
                        "file": "structure_module",
                        "db": "structure_module",
                        "root": "structure_root",
                        "db_table": "structure_db_table",
                        "db_field": "structure_db_field",
                    }.get(meta)
                    if not tbl:
                        n = 0
                    elif meta == "package":
                        n = src.execute(
                            "SELECT COUNT(*) c FROM structure_module"
                            " WHERE structure_type_id = 1").fetchone()["c"]
                    elif meta == "file":
                        n = src.execute(
                            "SELECT COUNT(*) c FROM structure_module"
                            " WHERE structure_type_id = 2").fetchone()["c"]
                    elif meta == "db":
                        n = src.execute(
                            "SELECT COUNT(*) c FROM structure_module"
                            " WHERE structure_type_id = 5").fetchone()["c"]
                    else:
                        n = src.execute(
                            f"SELECT COUNT(*) c FROM [{tbl}]").fetchone()["c"]
                    out[tid] = n
            finally:
                src.close()
        except Exception as e:
            print(f"[monitor] structure 掃描失敗: {e}")
        return out

    def refresh_structure(self):
        """更新 current_structure（冪等：upsert）"""
        real = self._real_structure_totals()
        n = 0
        for tid, total in real.items():
            cur = self.conn.execute(
                "INSERT INTO current_structure (structure_type_id, total)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM current_structure WHERE structure_type_id = ?)",
                (tid, total, tid))
            n += cur.rowcount
            self.conn.execute(
                "UPDATE current_structure SET total = ?,"
                " updated_at = datetime('now', 'localtime')"
                " WHERE structure_type_id = ? AND total != ?",
                (total, tid, total))
        self.conn.commit()
        return n, len(real)

    def current_structure(self, active_only=True):
        """列出快照（JOIN structure.db structure_type 名）"""
        rows = []
        for r in self.conn.execute(
                "SELECT * FROM current_structure WHERE 1=1"
                + (" AND is_active = 1" if active_only else "")
                + " ORDER BY structure_type_id"):
            d = dict(r)
            try:
                src = sqlite3.connect(f"file:{STRUCTURE_DB}?mode=ro", uri=True)
                src.row_factory = sqlite3.Row
                try:
                    m = src.execute(
                        "SELECT meta FROM structure_type WHERE id = ?",
                        (d["structure_type_id"],)).fetchone()
                    d["structure_type"] = m["meta"] if m else None
                finally:
                    src.close()
            except Exception:
                d["structure_type"] = None
            rows.append(d)
        return rows

    # ---------- current_taxonomy（taxonomy.db 各樹層行數） ----------
    def _real_taxonomy_totals(self):
        """掃 taxonomy.db：tree_id -> 真實行數（registry 表，2026-10-27 rename）"""
        out = {}
        try:
            src = sqlite3.connect(f"file:{TAXONOMY_DB}?mode=ro", uri=True)
            src.row_factory = sqlite3.Row
            try:
                for r in src.execute("SELECT id FROM tree WHERE is_active = 1"):
                    out[r["id"]] = src.execute(
                        "SELECT COUNT(*) c FROM registry WHERE tree_id = ?"
                        " AND is_active = 1", (r["id"],)).fetchone()["c"]
            finally:
                src.close()
        except Exception as e:
            print(f"[monitor] taxonomy 掃描失敗: {e}")
        return out

    def refresh_taxonomy(self):
        """更新 current_taxonomy（冪等：upsert）"""
        real = self._real_taxonomy_totals()
        n = 0
        for tid, total in real.items():
            cur = self.conn.execute(
                "INSERT INTO current_taxonomy (tree_id, total)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM current_taxonomy WHERE tree_id = ?)",
                (tid, total, tid))
            n += cur.rowcount
            self.conn.execute(
                "UPDATE current_taxonomy SET total = ?,"
                " updated_at = datetime('now', 'localtime')"
                " WHERE tree_id = ? AND total != ?",
                (total, tid, total))
        self.conn.commit()
        return n, len(real)

    def current_taxonomy(self, active_only=True):
        """列出快照（JOIN taxonomy.db tree 名）"""
        rows = []
        for r in self.conn.execute(
                "SELECT * FROM current_taxonomy WHERE 1=1"
                + (" AND is_active = 1" if active_only else "")
                + " ORDER BY tree_id"):
            d = dict(r)
            try:
                src = sqlite3.connect(f"file:{TAXONOMY_DB}?mode=ro", uri=True)
                src.row_factory = sqlite3.Row
                try:
                    m = src.execute(
                        "SELECT meta_key FROM tree WHERE id = ?",
                        (d["tree_id"],)).fetchone()
                    d["tree"] = m["meta_key"] if m else None
                finally:
                    src.close()
            except Exception:
                d["tree"] = None
            rows.append(d)
        return rows

    def refresh(self):
        """一次過 refresh 兩張表"""
        n1, t1 = self.refresh_structure()
        n2, t2 = self.refresh_taxonomy()
        return {"structure": (n1, t1), "taxonomy": (n2, t2)}

    def close(self):
        self.conn.close()
