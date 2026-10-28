"""sql.py — migration.db 存取層（遷移審計日誌）

概念（2026-10-28 用戶設計，已修正）：
    migration ≠ api（api 係對外介面）
    sync 係 migration 一種（type 字典：schema/seed/sync/cutover/other）
    呢張表 = 每個 module 改過邊張表邊行嘅完整記錄
    type 表 value 幫助識別類型（唔使淨靠 id）
"""

import sqlite3

from .schema import MIGRATION_LOG_DDL, TYPE_DDL  # noqa: F401（逐個 symbol）

DB_PATH = r"C:\projects\meta\migration\migration.db"

# type 字典（migration 類型，冪等 seed；WHERE NOT EXISTS 唔燒號）
DEFAULT_TYPES = [
    ("schema", "建表 / 改表（DDL 變更）"),
    ("seed", "字典 / 預設資料初始化"),
    ("sync", "數據同步（外部拉取 / 掃描登記）"),
    ("cutover", "搬遷 / 重建（損害性）"),
    ("other", "其他"),
]


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(TYPE_DDL)
        self.conn.execute(MIGRATION_LOG_DDL)
        self._seed_types()
        self._migrate_type_id()
        self.conn.commit()

    def _seed_types(self):
        """type 字典 seed（冪等：WHERE NOT EXISTS，唔燒 AUTOINCREMENT 號）"""
        for value, desc in DEFAULT_TYPES:
            self.conn.execute(
                "INSERT INTO type (value, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM type WHERE value = ?)",
                (value, desc, value))

    def _migrate_type_id(self):
        """遷移（幂等）：migration_log.api_id -> type_id（2026-10-28 用戶修正）

        舊版有 api_id / migration_type 文字欄 -> 轉 type_id 指 type 表。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('migration_log')")}
        if "type_id" in cols:
            # 有 type_id 再補 migration_type 文字（fill 舊資料）
            if "migration_type" in cols:
                rows = self.conn.execute(
                    "SELECT id, migration_type FROM migration_log"
                    " WHERE type_id IS NULL").fetchall()
                for r in rows:
                    tid = self.type_id(r["migration_type"] or "other")
                    self.conn.execute(
                        "UPDATE migration_log SET type_id = ? WHERE id = ?",
                        (tid, r["id"]))
                self.conn.commit()
            return
        if "api_id" not in cols:
            return
        # 舊版：api_id + migration_type 文字 -> rebuild 做 type_id
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM migration_log ORDER BY id")]
        self.conn.execute("DROP TABLE migration_log")
        self.conn.execute(MIGRATION_LOG_DDL)
        for r in rows:
            tid = self.type_id(r.get("migration_type") or "other")
            self.conn.execute(
                "INSERT INTO migration_log"
                " (id, run_id, type_id, taxonomy_id, structure_db_table,"
                "  description, row_id, is_active, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r["id"], r.get("run_id"), tid, r.get("taxonomy_id"),
                 r.get("structure_db_table"), r.get("description"),
                 r.get("row_id", 0), r.get("is_active", 1),
                 r.get("created_at")))
        self.conn.commit()
        print("[migration] api_id -> type_id 遷移完成")

    # ---------- type 字典 ----------
    def types(self, active_only=True):
        sql = "SELECT * FROM type"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def type_id(self, value):
        """type.id by value（schema/seed/sync/cutover/other）"""
        r = self.conn.execute(
            "SELECT id FROM type WHERE value = ?", (value,)).fetchone()
        return r["id"] if r else None

    def type_value(self, type_id):
        """type.value by id"""
        r = self.conn.execute(
            "SELECT value FROM type WHERE id = ?", (type_id,)).fetchone()
        return r["value"] if r else None

    # ---------- 記錄 ----------
    def record(self, module_name, table=None, migration_type="schema",
               description=None, run_id=None, api_id=None, row_id=0):
        """記錄一次 migration（冪等：同 run + module + table + type + desc 唔重複）

        module_name    = taxonomy.registry.meta（邊個 module）
        table          = 改邊張表（db_table 名）
        migration_type = type value（schema / seed / sync / cutover / other）
        run_id         = run.id（有先）
        api_id         = 保留參數（api 觸發來源，記錄用；type_id 唔係 api_id）
        row_id         = 改邊行（0 = 全表）
        """
        # taxonomy_id 反查（零 hardcode）
        taxonomy_id = self._taxonomy_id(module_name)
        tid = self.type_id(migration_type) or self.type_id("other")
        if table:
            self.conn.execute(
                "INSERT INTO migration_log"
                " (run_id, type_id, taxonomy_id, structure_db_table,"
                "  description, row_id)"
                " SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM migration_log WHERE run_id IS ?"
                "  AND taxonomy_id IS ? AND structure_db_table IS ?"
                "  AND type_id = ? AND description IS ?)",
                (run_id, tid, taxonomy_id, table,
                 description, row_id,
                 run_id, taxonomy_id, table, tid, description))
        else:
            self.conn.execute(
                "INSERT INTO migration_log"
                " (run_id, type_id, taxonomy_id, structure_db_table,"
                "  description, row_id)"
                " SELECT ?, ?, ?, NULL, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM migration_log WHERE run_id IS ?"
                "  AND taxonomy_id IS ? AND structure_db_table IS NULL"
                "  AND type_id = ? AND description IS ?)",
                (run_id, tid, taxonomy_id,
                 description, row_id,
                 run_id, taxonomy_id, tid, description))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM migration_log WHERE run_id IS ?"
            " AND taxonomy_id IS ? AND structure_db_table IS ?"
            " AND type_id = ? AND description IS ?",
            (run_id, taxonomy_id, table, tid, description)).fetchone()
        return r["id"] if r else None

    def _taxonomy_id(self, module_name):
        """taxonomy.registry.id by meta（零 hardcode，搵唔到 -> None）"""
        try:
            import sqlite3 as _sq
            c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            try:
                c.row_factory = _sq.Row
                r = c.execute(
                    "SELECT id FROM registry WHERE meta = ?"
                    " AND tree_id = 2 AND is_active = 1",
                    (module_name,)).fetchone()
                return r["id"] if r else None
            finally:
                c.close()
        except Exception:
            return None

    # ---------- 查詢 ----------
    def logs(self, module_name=None, migration_type=None, limit=100):
        """列出 migration 記錄（可按 module / type 篩選）

        type 用 value 篩選（type 表），返回補 type_value + module_name。
        """
        args = []
        where = []
        if module_name:
            tid = self._taxonomy_id(module_name)
            where.append("ml.taxonomy_id = ?")
            args.append(tid)
        if migration_type:
            tid = self.type_id(migration_type)
            where.append("ml.type_id = ?")
            args.append(tid)
        sql = ("SELECT ml.*, t.value AS type_value"
               " FROM migration_log ml"
               " LEFT JOIN type t ON t.id = ml.type_id")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ml.id DESC LIMIT ?"
        args.append(limit)
        rows = [dict(r) for r in self.conn.execute(sql, args)]
        # 補 module 名（跨 DB，SQL JOIN 唔到）
        mods = self._module_names()
        for r in rows:
            r["module_name"] = mods.get(r.get("taxonomy_id"))
        return rows

    def _module_names(self):
        """taxonomy_id -> meta map"""
        try:
            import sqlite3 as _sq
            c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            try:
                c.row_factory = _sq.Row
                return {r["id"]: r["meta"] for r in c.execute(
                    "SELECT id, meta FROM registry WHERE tree_id = 2"
                    " AND is_active = 1")}
            finally:
                c.close()
        except Exception:
            return {}

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM migration_log").fetchone()[0]

    def by_module(self):
        """按 module + type 統計（type_value 補名）"""
        rows = [dict(r) for r in self.conn.execute(
            "SELECT ml.taxonomy_id, t.value AS type_value, COUNT(*) AS n"
            " FROM migration_log ml"
            " LEFT JOIN type t ON t.id = ml.type_id"
            " GROUP BY ml.taxonomy_id, t.value ORDER BY n DESC")]
        mods = self._module_names()
        for r in rows:
            r["module_name"] = mods.get(r.get("taxonomy_id"))
        return rows

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
