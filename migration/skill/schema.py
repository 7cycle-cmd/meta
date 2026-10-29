"""skill.py — migration 技能層（migrate_schema 7 個真 action，2026-10-29 用戶要求）

用戶：「move to module : package : migration > package : skill > schema.py」
migrate_schema flow 嘅 7 個 action（inspect_table / check_column / add_column /
backfill_column / verify_column / verify_rowcount / report）由 sql.py 搬嚟
呢度 —— 技能層（skill）負責「點做」，sql.py 只留審計記錄 + 其他 migrate_*。

2026-10-29（用戶再要求）：migration/schema.py 刪除 —— DDL（TYPE_DDL /
MIGRATION_LOG_DDL）都搬埋入呢度，migration 只有一個 schema.py（呢個）。

每個 function 都係真 SQL（PRAGMA / ALTER / COUNT），零 hardcode：
    module_name = taxonomy.registry.meta（邊個 module；決定 db 檔）
    table       = 張表名
    column      = 欄位名

用法：
    from migration.skill import SchemaSkill
    s = SchemaSkill()
    s.inspect_table("source", "api")
    s.check_column("source", "api", "proven")
    s.add_column("source", "api", "proven", "INTEGER")
    s.close()
"""

import os
import sqlite3

META = r"C:\projects\meta"

# ============ DDL（由 migration/schema.py 搬入，2026-10-29 用戶要求）============
# type 字典：migration 類型（2026-10-28 用戶設計）
# value 幫助識別（唔使淨靠 id）
TYPE_DDL = """
CREATE TABLE IF NOT EXISTS type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,  -- schema / seed / sync / cutover / other
    description TEXT,                      -- 描述
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# migration_log：遷移審計日誌（2026-10-28 用戶設計）
# type_id -> type.id（migration 類型：schema/seed/sync/cutover/other）
# flow_id  -> terminology.flow.id（行邊條 migration flow，2026-10-28 用戶要求；
#             flow/step 已全部喺 terminology.db，呢度由 run_id 反查）
# step_id  -> terminology.step.id（停喺邊步；全 pass = 最後一步）
MIGRATION_LOG_DDL = """
CREATE TABLE IF NOT EXISTS migration_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id             INTEGER,            -- terminology run.id（驗證鏈執行）
    value_id           INTEGER,            -- value.db value.id（提交值，2026-10-28）
    type_id            INTEGER,            -- type.id（migration type 字典）
    taxonomy_id        INTEGER,            -- taxonomy.registry.id（邊個 module）
    structure_db_table TEXT,               -- 改邊張表（db_table 名）
    description        TEXT,               -- 描述
    row_id             INTEGER NOT NULL DEFAULT 0,  -- 改邊行（0 = 全表）
    flow_id            INTEGER,            -- terminology.flow.id（migration flow）
    step_id            INTEGER,            -- terminology.step.id（停喺邊步）
    is_active          INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# flow_registry：migration 技能檔案登記（2026-10-29 用戶要求）
# id | filename | total_line
#   1 | audit | 4 | sync | 5 | cutover | 6 | other
# total_line = 檔案真實行數（AST 掃，零 hardcode）
FLOW_REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS flow_registry (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    filename   TEXT    NOT NULL UNIQUE,   -- skill 檔名（audit/schema/seed/sync/cutover/other）
    total_line INTEGER NOT NULL DEFAULT 0, -- 檔案真實行數（AST 掃）
    is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# step_registry：每個 skill 檔案嘅 function/step 登記（2026-10-29 用戶要求）
# id | flow_registry_id | function_name | formula_id | flow_id | line_number
#   flow_registry_id -> flow_registry.id（邊個 skill 檔案 = subject）
#   function_name    = function 真實名（AST 掃 = action）
#   formula_id       -> template.formula.id（AST 掃描時登記，2026-10-29 用戶要求）
#   flow_id          -> template.flow.id（flow 真 id，由 flow_name 真查 = object）
#   line_number      = function 真實行號（AST 掃，零 hardcode）
#
# 2026-10-29 實查修正（用戶指出）：
#   1. formula_id 指向 template.formula（全部係 `xxx=<select ...>` 字串模板，
#      method 欄位只有 GET），migration skill 嘅 function 喺 formula 表
#      冇對應記錄 -> formula_id 永遠 NULL，冇意義。改為 flow_id
#      （template.flow.id，由 flow_name 真查，零 hardcode）。
#   2. 全部 function 都係 step（包括 __init__ / close / helper），
#      唔可以淨係登記 public function。加 function_name 欄位
#      （AST 掃真實 function 名，零 hardcode）。
#   3. 用戶：「why not register at ast too to have formula_id」——
#      AST 掃描時同時喺 formula 表登記（full = function 名，
#      package_id = taxonomy.registry.id，line = 真實行號），
#      formula_id 就有真值（唔再係 NULL）。
STEP_REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS step_registry (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_registry_id INTEGER NOT NULL,     -- flow_registry.id（邊個 skill 檔案 = subject）
    function_name    TEXT    NOT NULL,     -- function 真實名（AST 掃 = action）
    formula_id       INTEGER,              -- template.formula.id（AST 掃描時登記）
    flow_id          INTEGER,              -- template.flow.id（flow 真 id = object）
    line_number      INTEGER NOT NULL DEFAULT 0,  -- function 真實行號（AST 掃）
    is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ["TYPE_DDL", "MIGRATION_LOG_DDL", "FLOW_REGISTRY_DDL",
           "STEP_REGISTRY_DDL", "SchemaSkill"]


class SchemaSkill:
    """migrate_schema 技能：7 個真 action（表話事，零 hardcode）"""

    def __init__(self, db_path=None):
        self.conn = sqlite3.connect(
            db_path or os.path.join(META, "migration", "migration.db"))
        self.conn.row_factory = sqlite3.Row

    # ---------- helpers ----------
    def _target_db(self, module_name):
        """module 名 -> (db 路徑, 資料夾名)；default = migration.db"""
        if not module_name:
            return os.path.join(META, "migration", "migration.db")
        p = os.path.join(META, module_name, f"{module_name}.db")
        return (p, module_name) if os.path.isfile(p) else (
            os.path.join(META, "migration", "migration.db"), "migration")

    def _count_of(self, dbp, table, where=None, args=()):
        """真查 count（dbp+table 唔存在 -> 0）"""
        try:
            c = sqlite3.connect(dbp)
            try:
                q = f"SELECT COUNT(*) c FROM '{table}'"
                if where:
                    q += f" WHERE {where}"
                return c.execute(q, args).fetchone()[0]
            finally:
                c.close()
        except Exception:
            return 0

    def _taxonomy_id(self, module_name):
        """taxonomy.registry.id by meta（零 hardcode，搵唔到 -> None）"""
        try:
            c = sqlite3.connect(os.path.join(META, "taxonomy",
                                             "taxonomy.db"))
            try:
                c.row_factory = sqlite3.Row
                r = c.execute(
                    "SELECT id FROM registry WHERE tree_id = 2"
                    " AND meta = ? AND is_active = 1",
                    (module_name,)).fetchone()
                return r["id"] if r else None
            finally:
                c.close()
        except Exception:
            return None

    # ---------- migrate_schema 7 個真 action ----------
    def inspect_table(self, module_name, table):
        """真實 inspect：PRAGMA table_info 攞欄位清單 + column_count"""
        dbp, _ = self._target_db(module_name)
        cols = []
        try:
            c = sqlite3.connect(dbp)
            try:
                cols = [dict(zip(("name", "type", "notnull", "dflt", "pk"), r))
                        for r in c.execute(f"PRAGMA table_info('{table}')")]
            finally:
                c.close()
        except Exception:
            cols = []
        return {"table": table, "db_file": dbp,
                "columns": [x["name"] for x in cols],
                "column_count": len(cols), "exists": bool(cols)}

    def check_column(self, module_name, table, column):
        """真實檢查：column 存唔存在（PRAGMA table_info 權威，唔 hardcode）"""
        db_file = None
        exists = False
        if module_name and table and column:
            p = os.path.join(META, module_name, f"{module_name}.db")
            if os.path.isfile(p):
                db_file = p
                try:
                    c = sqlite3.connect(p)
                    try:
                        cols = {r[1] for r in c.execute(
                            f"PRAGMA table_info('{table}')").fetchall()}
                        exists = column in cols
                    finally:
                        c.close()
                except Exception:
                    exists = False
        return {"exists": exists, "db_file": db_file,
                "table": table, "column": column}

    def add_column(self, module_name, table, column, column_type="TEXT"):
        """真實加欄位（ALTER TABLE ADD COLUMN；冪等，唔 hardcode）

        流程：真查有冇欄位 -> 有 = already；冇 = ALTER + 真查確認。
        """
        db_file = None
        exists = False
        added = False
        already = False
        err = None
        if module_name and table and column:
            p = os.path.join(META, module_name, f"{module_name}.db")
            if os.path.isfile(p):
                db_file = p
                try:
                    c = sqlite3.connect(p)
                    try:
                        cols = {r[1] for r in c.execute(
                            f"PRAGMA table_info('{table}')").fetchall()}
                        exists = column in cols
                        if exists:
                            already = True
                        else:
                            c.execute(
                                f"ALTER TABLE '{table}' ADD COLUMN"
                                f" '{column}' {column_type}")
                            c.commit()
                            cols2 = {r[1] for r in c.execute(
                                f"PRAGMA table_info('{table}')").fetchall()}
                            exists = column in cols2
                            added = exists
                    finally:
                        c.close()
                except Exception as e:
                    err = str(e)
        return {"added": added, "already": already, "exists": exists,
                "db_file": db_file, "table": table, "column": column,
                "column_type": column_type, "error": err}

    def backfill_column(self, module_name, table, column):
        """真實回填：count 有值嘅 row 數（冇欄 -> 0）"""
        dbp, _ = self._target_db(module_name)
        n = self._count_of(
            dbp, table, f"\"{column}\" IS NOT NULL AND \"{column}\" != ''")
        return {"table": table, "column": column, "backfilled": n,
                "db_file": dbp}

    def verify_column(self, module_name, table, column):
        """真實 verify：PRAGMA 確認欄位存在"""
        r = self.check_column(module_name, table, column)
        return {"verified": r["exists"], "table": table,
                "column": column, "db_file": r["db_file"]}

    def verify_rowcount(self, module_name, table):
        """真實 verify rowcount：count(*)"""
        dbp, _ = self._target_db(module_name)
        return {"table": table, "rowcount": self._count_of(dbp, table),
                "db_file": dbp}

    def report(self, module_name, table=None):
        """真實 report：migration_log 統計（module 過濾）"""
        where = []
        args = []
        if module_name:
            tid = self._taxonomy_id(module_name)
            if tid:
                where.append("ml.taxonomy_id = ?")
                args.append(tid)
        if table:
            where.append("ml.structure_db_table = ?")
            args.append(table)
        w = (" WHERE " + " AND ".join(where)) if where else ""
        rows = [dict(r) for r in self.conn.execute(
            f"SELECT ml.id, ml.type_id, t.value AS type_value,"
            f" ml.structure_db_table, ml.description, ml.row_id,"
            f" ml.created_at FROM migration_log ml"
            f" LEFT JOIN type t ON t.id = ml.type_id{w}"
            f" ORDER BY ml.id DESC LIMIT 50", args)]
        return {"rows": rows, "count": len(rows)}

    def close(self):
        self.conn.close()
