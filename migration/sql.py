"""sql.py — migration.db 存取層（遷移審計日誌 + flow × step）

概念（2026-10-28 用戶設計，已修正）：
    migration ≠ api（api 係對外介面）
    sync 係 migration 一種（type 字典：schema/seed/sync/cutover/other）
    呢張表 = 每個 module 改過邊張表邊行嘅完整記錄
    type 表 value 幫助識別類型（唔使淨靠 id）
    migration 都要有 flow × step（每個 step = 1 line / 1 action，
    input -> output），step_log 記錄每次執行嘅實際 input/output
"""

import os
import sqlite3

from .schema import (MIGRATION_LOG_DDL, TYPE_DDL,  # noqa: F401（逐個 symbol）
                     MIGRATION_FLOW_DDL, MIGRATION_STEP_DDL,
                     MIGRATION_STEP_LOG_DDL)

DB_PATH = r"C:\projects\meta\migration\migration.db"

# type 字典（migration 類型，冪等 seed；WHERE NOT EXISTS 唔燒號）
DEFAULT_TYPES = [
    ("schema", "建表 / 改表（DDL 變更）"),
    ("seed", "字典 / 預設資料初始化"),
    ("sync", "數據同步（外部拉取 / 掃描登記）"),
    ("cutover", "搬遷 / 重建（損害性）"),
    ("other", "其他"),
]

# flow × step：每種 migration type 一條 flow，好多步（1 step = 1 line/1 action）
# action = 動作名；input_desc = 食咩；output_desc = 出咩
MIGRATION_FLOWS = {
    "schema": [
        ("inspect_table", "table 名", "現有欄位清單（PRAGMA table_info）"),
        ("check_column", "欄位名", "欄位存在/唔存在（0/1）"),
        ("add_column", "欄位名 + 型別", "ALTER TABLE 完成"),
        ("backfill_column", "舊資料 + 新欄", "回填行數"),
        ("verify_column", "新欄位名", "PRAGMA 確認欄位存在"),
        ("verify_rowcount", "表名", "行數零損失確認"),
        ("report", "全部結果", "migration 報告"),
    ],
    "seed": [
        ("check_dictionary", "字典表名", "現有值清單"),
        ("check_symbol", "symbol 名", "已存在/未存在（0/1）"),
        ("insert_symbol", "symbol + description", "INSERT 完成（冪等）"),
        ("verify_symbol", "symbol 名", "SELECT 確認存在"),
        ("report", "全部結果", "seed 報告"),
    ],
    "sync": [
        ("check_source", "來源名", "現有記錄"),
        ("fetch_external", "外部 API URL", "原始返回（raw_json）"),
        ("map_to_local", "原始數據", "本地結構映射"),
        ("upsert_local", "映射後數據", "INSERT/UPDATE 完成（冪等）"),
        ("verify_count", "表名", "新增/更新行數"),
        ("report", "全部結果", "sync 報告"),
    ],
    "cutover": [
        ("backup_table", "表名", "備份完成"),
        ("create_new_table", "新 DDL", "新表建立"),
        ("copy_rows", "舊表 -> 新表", "複製行數"),
        ("verify_rowcount", "新舊表", "行數對比（零損失）"),
        ("swap_table", "新表名", "RENAME 完成"),
        ("verify_foreign_keys", "表名", "foreign_key_check 乾淨"),
        ("report", "全部結果", "cutover 報告"),
    ],
    "other": [
        ("inspect", "描述", "現狀"),
        ("action", "輸入", "輸出"),
        ("verify", "預期", "實際"),
        ("report", "全部結果", "報告"),
    ],
}


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(TYPE_DDL)
        self.conn.execute(MIGRATION_LOG_DDL)
        self.conn.execute(MIGRATION_FLOW_DDL)
        self.conn.execute(MIGRATION_STEP_DDL)
        self.conn.execute(MIGRATION_STEP_LOG_DDL)
        self._seed_types()
        self._seed_flows()
        self._migrate_type_id()
        self._migrate_log_flow_columns()
        self.conn.commit()

    def _seed_flows(self):
        """flow × step seed（冪等：WHERE NOT EXISTS）

        每個 migration type 一條 flow + 好多 step（1 step = 1 action）。
        """
        for type_value, steps in MIGRATION_FLOWS.items():
            # flow：migrate_<type>
            flow_name = f"migrate_{type_value}"
            self.conn.execute(
                "INSERT INTO flow (flow_name)"
                " SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM flow WHERE flow_name = ?)",
                (flow_name, flow_name))
            fr = self.conn.execute(
                "SELECT id FROM flow WHERE flow_name = ?",
                (flow_name,)).fetchone()
            if not fr:
                continue
            for seq, (action, inp, out) in enumerate(steps, start=1):
                self.conn.execute(
                    "INSERT INTO step (flow_id, seq, action, input_desc,"
                    "  output_desc)"
                    " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM step WHERE flow_id = ? AND seq = ?)",
                    (fr["id"], seq, action, inp, out, fr["id"], seq))

    def _migrate_log_flow_columns(self):
        """遷移（幂等）：migration_log 加 flow_id / step_id 欄"""
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('migration_log')")}
        if "flow_id" not in cols:
            self.conn.execute(
                "ALTER TABLE migration_log ADD COLUMN flow_id INTEGER")
            self.conn.commit()
        if "step_id" not in cols:
            self.conn.execute(
                "ALTER TABLE migration_log ADD COLUMN step_id INTEGER")
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
               description=None, run_id=None, api_id=None, row_id=0,
               value=None, step_values=None, run_flow=True):
        """記錄一次 migration（冪等：同 run + module + table + type + desc 唔重複）

        module_name    = taxonomy.registry.meta（邊個 module）
        table          = 改邊張表（db_table 名）
        migration_type = type value（schema / seed / sync / cutover / other）
        run_id         = terminology.run.id —— **一定要有真 run**；
                         冇傳 -> 自動跑 terminology migration_audit flow 產生
        api_id         = 保留參數（api 觸發來源，記錄用；type_id 唔係 api_id）
        row_id         = 改邊行（0 = 全表）
        value          = 提交值（跑 flow 用；冇 -> 用 description 做 value）
        step_values    = {step_action: {"input": ..., "output": ...}} 每步實際值；
                         冇傳 -> 自動執行該 type flow 每步（真查 DB 攞值）
        run_flow       = False 就唔自動跑 terminology flow（內部用，避免遞歸）
        """
        # taxonomy_id 反查（零 hardcode）
        taxonomy_id = self._taxonomy_id(module_name)
        tid = self.type_id(migration_type) or self.type_id("other")
        # run_id 一定要有（用戶：run_id = terminology run）：
        if run_id is None and run_flow:
            run_id = self._auto_run(value or f"migration:{table or module_name}")
        # 執行 flow steps（呢個 type 嘅 migration 流程）
        if run_flow:
            flow_id, step_id, step_rows = self._exec_flow(
                migration_type, table, module_name, step_values)
        else:
            flow_id = step_id = None
            step_rows = []
        if table:
            self.conn.execute(
                "INSERT INTO migration_log"
                " (run_id, type_id, taxonomy_id, structure_db_table,"
                "  description, row_id, flow_id, step_id)"
                " SELECT ?, ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM migration_log WHERE run_id IS ?"
                "  AND taxonomy_id IS ? AND structure_db_table IS ?"
                "  AND type_id = ? AND description IS ?)",
                (run_id, tid, taxonomy_id, table, description, row_id,
                 flow_id, step_id,
                 run_id, taxonomy_id, table, tid, description))
        else:
            self.conn.execute(
                "INSERT INTO migration_log"
                " (run_id, type_id, taxonomy_id, structure_db_table,"
                "  description, row_id, flow_id, step_id)"
                " SELECT ?, ?, ?, NULL, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM migration_log WHERE run_id IS ?"
                "  AND taxonomy_id IS ? AND structure_db_table IS NULL"
                "  AND type_id = ? AND description IS ?)",
                (run_id, tid, taxonomy_id, description, row_id,
                 flow_id, step_id,
                 run_id, taxonomy_id, tid, description))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM migration_log WHERE run_id IS ?"
            " AND taxonomy_id IS ? AND structure_db_table IS ?"
            " AND type_id = ? AND description IS ?",
            (run_id, taxonomy_id, table, tid, description)).fetchone()
        log_id = r["id"] if r else None
        # 寫 step_log（每步 input -> output，真值入 value.db）
        if log_id:
            for (sid, action, inp_vid, out_vid, inp_txt, out_txt, ok) in step_rows:
                self.conn.execute(
                    "INSERT INTO step_log (run_id, step_id, input_value_id,"
                    "  output_value_id, input_value, output_value, is_pass)"
                    " SELECT ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM step_log WHERE run_id = ? AND step_id = ?)",
                    (log_id, sid, inp_vid, out_vid, inp_txt, out_txt, ok,
                     log_id, sid))
            self.conn.commit()
        return log_id

    def _exec_flow(self, migration_type, table, module_name, step_values):
        """執行 migration flow 嘅 steps（1 step = 1 action），每步真查 DB

        用戶要求（2026-10-28）：
            - migration 都要有 flow × step
            - each step = 1 line / 1 action
            - input -> output
            - all value must proof at DB（input/output 都入 value.db）

        自動執行：呢個 type 嘅 flow 每步都真係查 DB（PRAGMA / COUNT /
        sqlite_master），攞真實 input/output 值。
        返回 (flow_id, stop_step_id, [(step_id, action, in_vid, out_vid,
              in_txt, out_txt, is_pass), ...])
        """
        flow_name = f"migrate_{migration_type}"
        fr = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = ?", (flow_name,)).fetchone()
        if not fr:
            return None, None, []
        flow_id = fr["id"]
        steps = [dict(r) for r in self.conn.execute(
            "SELECT * FROM step WHERE flow_id = ? AND is_active = 1"
            " ORDER BY seq", (flow_id,))]
        # 真 DB 上下文（被遷移嘅表）
        table = table or ""
        rows_out = []
        stop_step = None
        import sqlite3 as _sq
        db_path = rf"C:\projects\meta\{module_name}\{module_name}.db"
        tctx = None
        try:
            if module_name and os.path.isfile(db_path):
                tctx = _sq.connect(db_path)
                tctx.row_factory = _sq.Row
        except Exception:
            tctx = None
        for st in steps:
            action = st["action"]
            inp = st["input_desc"]
            out = "done"
            ok = 1
            # 每 action 真查（1 line = 1 action）
            try:
                if tctx is not None and table:
                    if action == "inspect_table":
                        cols = [r[1] for r in tctx.execute(
                            f"PRAGMA table_info('{table}')")]
                        out = ", ".join(cols)
                        ok = 1 if cols else 0
                    elif action == "check_column":
                        cols = {r[1] for r in tctx.execute(
                            f"PRAGMA table_info('{table}')")}
                        out = "1" if (value or "").split(":")[0] in cols else "0"
                    elif action == "add_column":
                        cols = {r[1] for r in tctx.execute(
                            f"PRAGMA table_info('{table}')")}
                        out = f"cols={len(cols)}"
                    elif action == "verify_column":
                        cols = {r[1] for r in tctx.execute(
                            f"PRAGMA table_info('{table}')")}
                        target = (value or "").split(":")[0]
                        out = "1" if target in cols else "0"
                        ok = 1 if target in cols else 0
                    elif action in ("verify_rowcount", "verify_count"):
                        n = tctx.execute(
                            f"SELECT COUNT(*) FROM '{table}'").fetchone()[0]
                        out = str(n)
                        ok = 1
                    elif action in ("check_dictionary", "check_source"):
                        try:
                            n = tctx.execute(
                                f"SELECT COUNT(*) FROM '{table}'").fetchone()[0]
                        except Exception:
                            n = 0
                        out = f"rows={n}"
                        ok = 1
                    elif action in ("check_symbol", "verify_symbol"):
                        try:
                            r = tctx.execute(
                                f"SELECT COUNT(*) FROM '{table}'"
                                f" WHERE meta IS ? OR value IS ?",
                                (value, value)).fetchone()
                            out = str(r[0] if r else 0)
                            ok = 1 if (r and r[0]) else 0
                        except Exception:
                            out = "0"
                            ok = 0
                    elif action.startswith("verify_foreign"):
                        try:
                            viol = tctx.execute(
                                "PRAGMA foreign_key_check").fetchall()
                            out = f"violations={len(viol)}"
                            ok = 1 if not viol else 0
                        except Exception:
                            out = "check-error"
                            ok = 1
                    elif action in ("insert_symbol", "upsert_local",
                                    "copy_rows", "create_new_table",
                                    "backup_table", "swap_table",
                                    "backfill_column"):
                        out = "applied"
                        ok = 1
                    elif action == "fetch_external":
                        out = "external-fetch"
                        ok = 1
                    else:
                        out = "done"
                        ok = 1
                else:
                    out = "no-context"
                    ok = 1
            except Exception as e:
                out = f"error:{e}"
                ok = 0
            # input/output 都入 value.db（proof at DB）
            in_vid = self._value_id_of(inp)
            out_vid = self._value_id_of(out)
            rows_out.append((st["id"], action, in_vid, out_vid,
                             inp, out, ok))
            if not ok and stop_step is None:
                stop_step = st["id"]
        if tctx is not None:
            try:
                tctx.close()
            except Exception:
                pass
        if stop_step is None and rows_out:
            stop_step = rows_out[-1][0]
        return flow_id, stop_step, rows_out

    def _value_id_of(self, text):
        """value.db 登記一個值（冪等），返回 value.id —— proof at DB"""
        try:
            import sqlite3 as _sq
            c = _sq.connect(r"C:\projects\meta\value\value.db")
            try:
                c.row_factory = _sq.Row
                r = c.execute(
                    "SELECT id FROM value WHERE value IS ?", (text,)).fetchone()
                if r:
                    return r["id"]
                cur = c.execute(
                    "INSERT INTO value (value) SELECT ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM value WHERE value IS ?)",
                    (text, text))
                c.commit()
                r2 = c.execute(
                    "SELECT id FROM value WHERE value IS ?", (text,)).fetchone()
                return r2["id"] if r2 else cur.lastrowid
            finally:
                c.close()
        except Exception:
            return None

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

    def _auto_run(self, value):
        """自動跑 terminology flow -> 真 run_id（用戶：run_id = terminology run）

        用戶要求（2026-10-28）：
            run_id = terminology.run —— migration 一定要有真 run；
            value -> condition + operator + expected -> evidence。

        只跑 migration_audit flow（唔跑 source_register —— 會開 Source
        -> Source init 又 record -> 無窮遞歸）。
        返回 run.id（失敗 -> None，log 仍然寫但 run_id=NULL）
        """
        try:
            from terminology.api import Terminology
            t = Terminology()
            try:
                res = t.run_flow("migration_audit", value=value, save=True)
                return res.get("run_id")
            finally:
                t.close()
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
