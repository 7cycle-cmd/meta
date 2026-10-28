"""sql.py — common.db 存取層（中央字典）

表：
    action   動作字典（DROP / KEEP / create / read ...）
    status   狀態字典（active / legacy / dead ...）

第一次啟動自動 seed（由舊 DB 合併嘅完整清單）。

用法：
    from common.sql import SqlStore
    s = SqlStore()
    s.action_id("DROP")
    s.status_id("active")
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\common\common.db"

# 預設動作字典（seed，冪等）—— 由 3 個舊 action 表合併歸納
DEFAULT_ACTIONS = [
    # 寫入動作（activity_log 用 —— guard trigger 記錄 INSERT/UPDATE/DELETE）
    "INSERT", "UPDATE", "DELETE",
    # 清理動作（sweep.db）
    "DROP", "KEEP", "RENAME", "REPLACE", "MERGE", "UPGRADE", "REBUILD",
    # 資料庫動作（step.db）
    "design", "head", "whole", "update_delete", "seed",
    "create", "read", "update", "delete", "generate", "verify", "report",
    "list", "register", "scan", "analyze", "sync", "observe", "monitor",
    "import", "export", "backup", "restore", "trace", "log", "clean",
    # 能力動作（由 skill 表達）
    "link", "run", "unlink",
]

# 預設狀態字典（seed，冪等）—— 由舊 status 表合併
DEFAULT_STATUS = [
    # sweep 狀態
    "empty", "dead", "legacy", "active",
    # 任務狀態
    "planned", "in_progress", "done", "blocked",
    # 回饋狀態（na.db）
    "pending", "resolved",
    # 問題狀態（question.db）
    "approved", "rejected", "NA",
]

# 預設角色字典（seed，冪等）—— guard 寫入證明用
# 2026-10-23：角色 = 業務身份（跨 module），唔好 fallback 做 module 名。
#    api        對外接口（module/api.py）
#    worker     執行任務（flow/worker.py）
#    migration  遷移
#    sweep      清理
#    repair     修復
#    seed       種子/初始化
#    system     系統層（bootstrap / scaffold）
DEFAULT_ROLES = [
    "api", "worker", "migration", "sweep", "repair", "seed", "system",
]


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(COMMON_DDL)
        self.conn.commit()
        self._migrate_position_to_seq()
        self._migrate_drop_rest_api_type()
        self._seed()

    def _migrate_drop_rest_api_type(self):
        """遷移（幂等）：drop 舊 rest_api_type 表（2026-10-27 用戶要求）

        READ 中心 = monitor（rest_api_READ）
        WRITE 中心 = tool（rest_api_WRITE）
        common 唔再需要 rest_api_type 中央字典。
        """
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='rest_api_type'").fetchone()
        if has:
            self.conn.execute("DROP TABLE rest_api_type")
            self.conn.commit()
            print("[common] drop 舊表 rest_api_type")

    def _migrate_position_to_seq(self):
        """遷移（幂等）：position 表 -> seq 表（2026-10-27 用戶要求）

        舊表 position 存在 -> 資料搬去 seq（保 id / meta / value）。
        搬完 drop position。
        """
        has_pos = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='position'").fetchone()
        if not has_pos:
            return
        has_seq = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='seq'").fetchone()
        if has_seq:
            # seq 已有 -> 搬資料（OR IGNORE）
            self.conn.execute(
                "INSERT OR IGNORE INTO seq (id, meta, value, is_active,"
                " created_at, updated_at)"
                " SELECT id, meta, value, is_active, created_at, updated_at"
                " FROM position")
            self.conn.commit()
        self.conn.execute("DROP TABLE IF EXISTS position")
        self.conn.commit()

    def _seed(self):
        """預填字典（冪等：INSERT OR IGNORE）"""
        for meta in DEFAULT_ACTIONS:
            self.conn.execute(
                "INSERT OR IGNORE INTO action (meta) VALUES (?)", (meta,))
        for meta in DEFAULT_STATUS:
            self.conn.execute(
                "INSERT OR IGNORE INTO status (meta) VALUES (?)", (meta,))
        for meta in DEFAULT_ROLES:
            self.conn.execute(
                "INSERT OR IGNORE INTO role (meta) VALUES (?)", (meta,))
        self._seed_seqs()
        self._seed_booleans()
        self.conn.commit()

    # ---------- token（2026-10-26 用戶設計，取代 guard._guard） ----------
    def add_token(self, token_id, module_id, role_id, file_id=None):
        """登記一個寫入 token（冪等）

        token_id  = token 文字識別（例如 'terminology.api'）
        module_id = taxonomy.taxonomy.id（tree=module）
        role_id   = common.db role.id（api / worker / seed ...）
        file_id   = structure_module file 行 id（可選）
        """
        self.conn.execute(
            "INSERT INTO token (token_id, module_id, file_id, role_id)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM token WHERE token_id = ?)",
            (token_id, module_id, file_id, role_id, token_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM token WHERE token_id = ?",
            (token_id,)).fetchone()
        return r["id"] if r else None

    def token_id_of(self, token_id, active_only=True):
        """攞 token 行 id（唔存在返回 None）"""
        sql = "SELECT id FROM token WHERE token_id = ?"
        if active_only:
            sql += " AND is_active = 1"
        r = self.conn.execute(sql, (token_id,)).fetchone()
        return r["id"] if r else None

    def valid_token(self, token_id, active_only=True):
        """驗證 token 有冇效（存在 + active）"""
        return self.token_id_of(token_id, active_only) is not None

    def tokens(self, active_only=True):
        """列出全部 token（JOIN module + role 名）"""
        sql = """SELECT t.id, t.token_id, t.module_id, t.file_id,
                        t.role_id, r.meta AS role, t.is_active,
                        t.created_at, t.updated_at
                 FROM token t
                 LEFT JOIN role r ON r.id = t.role_id"""
        if active_only:
            sql += " WHERE t.is_active = 1"
        sql += " ORDER BY t.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def _seed_booleans(self):
        """預填 boolean 字典：value 只有 0 / 1（2026-10-25 用戶要求新增）

        boolean_id = common.db boolean.id（db_field_check.boolean_id
        引用）——純值字典（0 = 否 / 1 = 是），唔係欄位名。
        """
        for val, desc in ((0, "否（without）"), (1, "是（with）")):
            self.conn.execute(
                "INSERT OR IGNORE INTO boolean (value, description)"
                " VALUES (?, ?)", (val, desc))
            self.conn.execute(
                "UPDATE boolean SET description = ? WHERE value = ?"
                " AND description IS NULL", (desc, val))
        self.conn.commit()

    def _seed_seqs(self):
        """預填 seq 字典：meta 1-100 + value（2026-10-25 用戶要求 10-100）

        冪等：已有嘅 row 補 value，冇嘅 row 新加。
        舊表（冇 value 欄）-> 加欄。
        """
        # 1. 加 value 欄（舊 DB）
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('seq')")]
        if "value" not in cols:
            self.conn.execute(
                "ALTER TABLE seq ADD COLUMN value INTEGER")
            self.conn.commit()
        # 2. 補 value：全部現有 row（meta 數字 -> value）
        self.conn.execute(
            "UPDATE seq SET value = CAST(meta AS INTEGER)"
            " WHERE value IS NULL AND meta GLOB '[0-9]*'")
        # 3. seed 1-100（10-100 用戶要求 + 1-9 已存在）
        for i in range(1, 101):
            self.conn.execute(
                "INSERT OR IGNORE INTO seq (meta, value)"
                " VALUES (?, ?)", (str(i), i))
            self.conn.execute(
                "UPDATE seq SET value = ? WHERE meta = ?"
                " AND value IS NULL", (i, str(i)))
        self.conn.commit()

    # ---------- action ----------
    def actions(self, active_only=True):
        sql = "SELECT * FROM action WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def action(self, meta):
        r = self.conn.execute(
            "SELECT * FROM action WHERE meta = ?", (meta,)).fetchone()
        return dict(r) if r else None

    def action_id(self, meta):
        """由名攞 id（唔存在返回 None）"""
        r = self.conn.execute(
            "SELECT id FROM action WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def add_action(self, meta):
        """登記一個動作（冪等）"""
        self.conn.execute(
            "INSERT OR IGNORE INTO action (meta) VALUES (?)", (meta,))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM action WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    # ---------- status ----------
    def statuses(self, active_only=True):
        sql = "SELECT * FROM status WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def status(self, meta):
        r = self.conn.execute(
            "SELECT * FROM status WHERE meta = ?", (meta,)).fetchone()
        return dict(r) if r else None

    def status_id(self, meta):
        """由名攞 id（唔存在返回 None）"""
        r = self.conn.execute(
            "SELECT id FROM status WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def add_status(self, meta):
        """登記一個狀態（冪等）"""
        self.conn.execute(
            "INSERT OR IGNORE INTO status (meta) VALUES (?)", (meta,))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM status WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    # ---------- role（角色字典：guard 寫入證明用） ----------
    def roles(self, active_only=True):
        sql = "SELECT * FROM role WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def role(self, meta):
        r = self.conn.execute(
            "SELECT * FROM role WHERE meta = ?", (meta,)).fetchone()
        return dict(r) if r else None

    def role_id(self, meta):
        """由名攞 id（唔存在返回 None）"""
        r = self.conn.execute(
            "SELECT id FROM role WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def add_role(self, meta):
        """登記一個角色（冪等）"""
        self.conn.execute(
            "INSERT OR IGNORE INTO role (meta) VALUES (?)", (meta,))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM role WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    # ---------- seq（位置字典：跨 module 共用；2026-10-27 position -> seq） ----------
    def seqs(self, active_only=True):
        sql = "SELECT * FROM seq WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY value, id"
        return [dict(r) for r in self.conn.execute(sql)]

    def seq(self, meta):
        r = self.conn.execute(
            "SELECT * FROM seq WHERE meta = ?", (meta,)).fetchone()
        return dict(r) if r else None

    def seq_by_value(self, value):
        """由數值攞 seq（例如 10 -> 第 10 位）"""
        r = self.conn.execute(
            "SELECT * FROM seq WHERE value = ?", (value,)).fetchone()
        return dict(r) if r else None

    def seq_id(self, meta):
        """由位置名攞 id（例如 "1" -> 1）；唔存在自動登記（冪等）"""
        r = self.conn.execute(
            "SELECT id FROM seq WHERE meta = ?", (meta,)).fetchone()
        if r:
            return r["id"]
        self.conn.execute(
            "INSERT OR IGNORE INTO seq (meta, value) VALUES (?, ?)",
            (meta, int(meta) if str(meta).isdigit() else None))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM seq WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def add_seq(self, meta, value=None):
        """登記一個位置（冪等）"""
        self.conn.execute(
            "INSERT OR IGNORE INTO seq (meta, value) VALUES (?, ?)",
            (meta, value))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM seq WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    # ---------- position（兼容 alias；2026-10-27 之後位置表叫 seq） ----------
    def positions(self, active_only=True):
        return self.seqs(active_only)

    def position(self, meta):
        return self.seq(meta)

    def position_by_value(self, value):
        return self.seq_by_value(value)

    def position_id(self, meta):
        return self.seq_id(meta)

    def add_position(self, meta, value=None):
        return self.add_seq(meta, value)

    # ---------- boolean（布林字典：value 只有 0 / 1） ----------
    def booleans(self, active_only=True):
        """列出布林字典（boolean：value 0 / 1）"""
        sql = "SELECT * FROM boolean WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY value"
        return [dict(r) for r in self.conn.execute(sql)]

    def boolean_by_value(self, value):
        """由值攞 boolean（0 / 1）"""
        r = self.conn.execute(
            "SELECT * FROM boolean WHERE value = ?", (value,)).fetchone()
        return dict(r) if r else None

    def boolean_id(self, value):
        """由值攞 id（0/1；唔存在返回 None）"""
        r = self.conn.execute(
            "SELECT id FROM boolean WHERE value = ?", (value,)).fetchone()
        return r["id"] if r else None

    # ---------- resource_action（資源 × 正確動作選項） ----------
    def resource_actions(self, resource_id=None, ontology_id=None,
                         filling_id=None, active_only=True):
        """列出資源嘅正確動作選項（可按 resource / ontology / filling 篩選）"""
        sql = ("SELECT ra.*, a.meta AS action_meta"
               " FROM resource_action ra"
               " JOIN action a ON a.id = ra.action_id WHERE 1=1")
        args = []
        if active_only:
            sql += " AND ra.is_active = 1"
        if resource_id is not None:
            sql += " AND ra.resource_id = ?"
            args.append(resource_id)
        if ontology_id is not None:
            sql += " AND ra.ontology_id = ?"
            args.append(ontology_id)
        if filling_id is not None:
            sql += " AND ra.filling_id = ?"
            args.append(filling_id)
        sql += " ORDER BY ra.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def set_resource_action(self, resource_id, action_id, ontology_id=None,
                            filling_id=None):
        """設定一個資源嘅正確動作（冪等 upsert）"""
        self.conn.execute(
            "INSERT INTO resource_action"
            " (ontology_id, filling_id, resource_id, action_id)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(resource_id, action_id, ontology_id, filling_id)"
            " DO UPDATE SET is_active = 1,"
            " updated_at = datetime('now', 'localtime')",
            (ontology_id, filling_id, resource_id, action_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM resource_action"
            " WHERE resource_id = ? AND action_id = ?"
            " AND ontology_id IS ? AND filling_id IS ?",
            (resource_id, action_id, ontology_id, filling_id)).fetchone()
        return r["id"] if r else None

    def clear_resource_actions(self, resource_id):
        """清走一個資源嘅動作選項（soft delete）"""
        self.conn.execute(
            "UPDATE resource_action SET is_active = 0,"
            " updated_at = datetime('now', 'localtime')"
            " WHERE resource_id = ?", (resource_id,))
        self.conn.commit()

    # ---------- resource_status（資源 × 正確狀態選項） ----------
    def resource_statuses(self, resource_id=None, ontology_id=None,
                          filling_id=None, active_only=True):
        """列出資源嘅正確狀態選項（可按 resource / ontology / filling 篩選）"""
        sql = ("SELECT rs.*, s.meta AS status_meta"
               " FROM resource_status rs"
               " JOIN status s ON s.id = rs.status_id WHERE 1=1")
        args = []
        if active_only:
            sql += " AND rs.is_active = 1"
        if resource_id is not None:
            sql += " AND rs.resource_id = ?"
            args.append(resource_id)
        if ontology_id is not None:
            sql += " AND rs.ontology_id = ?"
            args.append(ontology_id)
        if filling_id is not None:
            sql += " AND rs.filling_id = ?"
            args.append(filling_id)
        sql += " ORDER BY rs.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def set_resource_status(self, resource_id, status_id, ontology_id=None,
                            filling_id=None):
        """設定一個資源嘅正確狀態（冪等 upsert）"""
        self.conn.execute(
            "INSERT INTO resource_status"
            " (ontology_id, filling_id, resource_id, status_id)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(resource_id, status_id, ontology_id, filling_id)"
            " DO UPDATE SET is_active = 1,"
            " updated_at = datetime('now', 'localtime')",
            (ontology_id, filling_id, resource_id, status_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM resource_status"
            " WHERE resource_id = ? AND status_id = ?"
            " AND ontology_id IS ? AND filling_id IS ?",
            (resource_id, status_id, ontology_id, filling_id)).fetchone()
        return r["id"] if r else None

    def clear_resource_statuses(self, resource_id):
        """清走一個資源嘅狀態選項（soft delete）"""
        self.conn.execute(
            "UPDATE resource_status SET is_active = 0,"
            " updated_at = datetime('now', 'localtime')"
            " WHERE resource_id = ?", (resource_id,))
        self.conn.commit()

    # ---------- sweep_activity（資源清理活動記錄，中央） ----------
    def sweep_activities(self, resource_id=None, action_id=None, type_id=None,
                         sweep_id=None, limit=100, active_only=True):
        """列出清理活動（可按 resource / action / type / sweep_id 篩選）"""
        sql = ("SELECT sw.*, a.meta AS action_meta, s.meta AS type_meta"
               " FROM sweep_activity sw"
               " JOIN action a ON a.id = sw.action_id"
               " JOIN status s ON s.id = sw.type_id WHERE 1=1")
        args = []
        if active_only:
            sql += " AND sw.is_active = 1"
        if resource_id is not None:
            sql += " AND sw.resource_id = ?"
            args.append(resource_id)
        if action_id is not None:
            sql += " AND sw.action_id = ?"
            args.append(action_id)
        if type_id is not None:
            sql += " AND sw.type_id = ?"
            args.append(type_id)
        if sweep_id is not None:
            sql += " AND sw.sweep_id = ?"
            args.append(sweep_id)
        sql += " ORDER BY sw.id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def insert_sweep_activity(self, resource_id, type_id, action_id,
                              sweep_id=None):
        """記錄一次清理活動（DROP 咗 / KEEP / RENAME...）

        sweep_id = 父 sweep（一次清理任務；可選）
        """
        cur = self.conn.execute(
            "INSERT INTO sweep_activity"
            " (sweep_id, resource_id, type_id, action_id)"
            " VALUES (?, ?, ?, ?)",
            (sweep_id, resource_id, type_id, action_id))
        self.conn.commit()
        return cur.lastrowid

    def sweep_activity_count(self, active_only=True):
        sql = "SELECT COUNT(*) c FROM sweep_activity"
        if active_only:
            sql += " WHERE is_active = 1"
        return self.conn.execute(sql).fetchone()["c"]

    # ---------- migration_activity（資源遷移活動記錄，中央） ----------
    def migration_activities(self, resource_id=None, action_id=None,
                             status_id=None, migration_id=None,
                             limit=100, active_only=True):
        """列出遷移活動（可按 resource / action / status / migration 篩選）"""
        sql = ("SELECT ma.*, a.meta AS action_meta, s.meta AS status_meta"
               " FROM migration_activity ma"
               " JOIN action a ON a.id = ma.action_id"
               " JOIN status s ON s.id = ma.status_id WHERE 1=1")
        args = []
        if active_only:
            sql += " AND ma.is_active = 1"
        if resource_id is not None:
            sql += " AND ma.resource_id = ?"
            args.append(resource_id)
        if action_id is not None:
            sql += " AND ma.action_id = ?"
            args.append(action_id)
        if status_id is not None:
            sql += " AND ma.status_id = ?"
            args.append(status_id)
        if migration_id is not None:
            sql += " AND ma.migration_id = ?"
            args.append(migration_id)
        sql += " ORDER BY ma.id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def insert_migration_activity(self, resource_id, action_id, status_id,
                                  resource_type_id=None, migration_id=None):
        """記錄一次遷移活動（proof migration 真係做咗）

        resource_id      = registry.id（被遷移資源）
        resource_type_id = registry.type_id（資源類型快照）
        action_id        = common.action.id（ALTER / CREATE / DROP...）
        status_id        = common.status.id（done / active...）
        migration_id     = 父 migration（可選）
        """
        cur = self.conn.execute(
            "INSERT INTO migration_activity"
            " (migration_id, resource_id, resource_type_id, action_id, status_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (migration_id, resource_id, resource_type_id, action_id, status_id))
        self.conn.commit()
        return cur.lastrowid

    def migration_activity_count(self, active_only=True):
        sql = "SELECT COUNT(*) c FROM migration_activity"
        if active_only:
            sql += " WHERE is_active = 1"
        return self.conn.execute(sql).fetchone()["c"]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
