"""version module SQLite 存取層。

表：
    boolean        yes/no 值表（0 = 否 / 1 = 是）—— 本 DB 自有
    value          版本值表（版本字串，例如 1.4.0）
    registry       版本註冊表（id | pass_id | value_id | github_id）
    github_action  GitHub 動作字典（commit / push）
    github_status  GitHub 狀態字典（pending / done / failed）
    github_ignore  GitHub 忽略規則（pattern + boolean_id -> boolean.id）
    github         一次 GitHub 操作記錄

2026-10-27（用戶要求）：version 表 -> rename -> registry
"""

import sqlite3

from .schema import (BOOLEAN_DDL, GITHUB_ACTION_DDL, GITHUB_DDL,
                     GITHUB_IGNORE_DDL, GITHUB_STATUS_DDL, REGISTRY_DDL,
                     VALUE_DDL)

DB_PATH = r"C:\projects\meta\version\version.db"
# .gitignore 位置（repo root）
GITIGNORE_PATH = r"C:\projects\meta\.gitignore"

# 預設 boolean 值表（0 = 否 / 1 = 是）—— 本 DB 自己定義
DEFAULT_BOOLEANS = [
    (0, 0, "否（without）"),
    (1, 1, "是（with）"),
]

# 預設 GitHub 動作字典（用戶要求：commit and push）
DEFAULT_GITHUB_ACTIONS = [
    ("commit", "提交（git commit）"),
    ("push", "推送（git push）"),
]

# 預設 GitHub 狀態字典
DEFAULT_GITHUB_STATUSES = [
    ("pending", "待處理"),
    ("done", "完成"),
    ("failed", "失敗"),
]

# 預設忽略規則：(pattern, boolean 值 1=是/with, description)
# ⚠️ version.db 本身被 .gitignore 排除（*.db），所以呢個 list 就係
#    重建 .gitignore 嘅**唯一真實來源** —— 加規則一定要同時加落呢度，
#    否則 DB 重建後規則會消失（安全漏洞）。
DEFAULT_GITHUB_IGNORES = [
    # --- 資料庫 / 備份 / 暫存 ---
    ("*.db", 1, "SQLite 資料庫（由 code 重建）"),
    ("*.db-journal", 1, "SQLite journal"),
    ("*.db-wal", 1, "SQLite WAL"),
    ("*.db-shm", 1, "SQLite shared memory"),
    ("*.bak*", 1, "備份檔"),
    ("*_tmp/", 1, "臨時目錄"),
    ("_purge_tmp/", 1, "臨時清理目錄"),
    # --- Python 產物 ---
    ("__pycache__/", 1, "Python bytecode cache"),
    ("*.py[cod]", 1, "Python 編譯檔"),
    ("*.pyo", 1, "Python 優化位元碼"),
    ("*.pyd", 1, "Python DLL"),
    # --- 虛擬環境 ---
    (".venv/", 1, "虛擬環境"),
    ("venv/", 1, "虛擬環境"),
    ("env/", 1, "虛擬環境"),
    # --- 憑證（絕對唔可以上 GitHub）---
    ("secret.env", 1, "憑證檔（token / 密碼）——一定唔可以上"),
    ("secret.txt", 1, "憑證檔（token / 密碼）——一定唔可以上"),
    ("secret.*", 1, "憑證檔（任何 secret.* 變體）"),
    (".env", 1, "環境變數（可能含憑證）"),
    (".env.*", 1, "環境變數變體"),
    ("*.env", 1, "環境變數檔"),
    ("*.pem", 1, "私鑰"),
    ("*.key", 1, "私鑰"),
    ("*.token", 1, "token 檔"),
    ("*_token*", 1, "token 檔"),
    ("*_secret*", 1, "secret 檔"),
]


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(BOOLEAN_DDL)      # yes/no 值表（本 DB 自己）
        self.conn.execute(VALUE_DDL)        # 版本值表（版本字串）
        self._migrate_version_to_registry()  # 舊 version 表 -> registry
        self.conn.execute(REGISTRY_DDL)     # 版本註冊表
        self.conn.execute(GITHUB_ACTION_DDL)
        self.conn.execute(GITHUB_STATUS_DDL)
        self.conn.execute(GITHUB_IGNORE_DDL)
        self.conn.commit()
        self._seed()              # 先填字典（遷移要查 github_status.id）
        self._migrate_github()    # 舊 TEXT status -> FK
        self.conn.execute(GITHUB_DDL)
        self.conn.commit()

    def _migrate_version_to_registry(self):
        """遷移（幂等）：version -> registry（2026-10-27 用戶要求 rename）

        舊 version（id | version）-> value（版本字串）+ registry
        （id | pass_id | value_id | github_id）。
        保留 id（github.version_id 仍然指同一 id，唔使改）。
        """
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='version'"
        ).fetchone()
        if not has_old:
            return  # 已新版（registry）
        has_new = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='registry'"
        ).fetchone()
        if has_new:
            n = self.conn.execute("SELECT COUNT(*) FROM registry").fetchone()[0]
            if n:
                raise ValueError(
                    "registry 表已存在且有資料，唔可以自動合併（需要人手處理）")
            self.conn.execute("DROP TABLE registry")
        # 舊 version 表 -> 暫存，再建新 registry（保 id）
        self.conn.execute("ALTER TABLE version RENAME TO version_old")
        self.conn.execute(REGISTRY_DDL)
        rows = self.conn.execute(
            "SELECT id, version FROM version_old ORDER BY id").fetchall()
        for r in rows:
            vid = self._value_id(r["version"])
            self.conn.execute(
                "INSERT INTO registry (id, value_id) VALUES (?, ?)",
                (r["id"], vid))
        self.conn.execute("DROP TABLE version_old")
        # 重設 sqlite_sequence（保 id 連續，唔跳號）
        self.conn.execute(
            "UPDATE sqlite_sequence SET seq ="
            " (SELECT COALESCE(MAX(id), 0) FROM registry)"
            " WHERE name = 'registry'")
        self.conn.commit()
        print(f"[version] version -> registry（rename，保 {len(rows)} 行）")

    def _migrate_github(self):
        """遷移：舊 github.status（TEXT）-> github_status_id（FK，2026-10-27）

        新表未有 -> 唔郁（GITHUB_DDL 會建）。舊表有 status 欄 -> 重建。
        """
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='github'"
        ).fetchone()
        if not has:
            return
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(github)")}
        if "status" not in cols:
            return  # 已新版（github_status_id）
        # 舊 -> 新：status 字串 -> github_status.id
        self.conn.execute("ALTER TABLE github RENAME TO github_old")
        self.conn.execute(GITHUB_DDL)
        name2id = {r["meta"]: r["id"] for r in self.conn.execute(
            "SELECT id, meta FROM github_status")}
        rows = self.conn.execute(
            "SELECT * FROM github_old").fetchall()
        for r in rows:
            sid = name2id.get(r["status"])
            if sid is None:
                continue  # 唔知嘅 status -> 唔搬（誠實，唔造）
            self.conn.execute(
                "INSERT INTO github (id, github_session_id, github_action_id,"
                " github_status_id, version_id, is_active, created_at,"
                " updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (r["id"], r["github_session_id"], r["github_action_id"],
                 sid, r["version_id"], r["is_active"],
                 r["created_at"], r["updated_at"]))
        self.conn.execute("DROP TABLE github_old")
        self.conn.commit()
        print("[version] github.status -> github_status_id（FK 遷移）")

    def _seed(self):
        """預填 boolean / github_action / github_status / github_ignore

        冪等（WHERE NOT EXISTS），唔燒號。
        """
        for bid, val, desc in DEFAULT_BOOLEANS:
            self.conn.execute(
                "INSERT INTO boolean (id, value, description)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM boolean WHERE value = ?)",
                (bid, val, desc, val))
        for meta, desc in DEFAULT_GITHUB_ACTIONS:
            self.conn.execute(
                "INSERT INTO github_action (meta, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM github_action WHERE meta = ?)",
                (meta, desc, meta))
        for meta, desc in DEFAULT_GITHUB_STATUSES:
            self.conn.execute(
                "INSERT INTO github_status (meta, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM github_status WHERE meta = ?)",
                (meta, desc, meta))
        # boolean 值 -> 本 DB boolean.id
        bid = {r["value"]: r["id"] for r in self.conn.execute(
            "SELECT id, value FROM boolean")}
        for pattern, bval, desc in DEFAULT_GITHUB_IGNORES:
            boolean_id = bid.get(bval)
            if boolean_id is None:
                continue  # boolean 未 ready -> 下次開再 seed
            self.conn.execute(
                "INSERT INTO github_ignore (pattern, boolean_id, description)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM github_ignore WHERE pattern = ?)",
                (pattern, boolean_id, desc, pattern))
        self.conn.commit()

    # ---------------- boolean（yes / no 值表）----------------
    def booleans(self, active_only=True):
        """列出 yes/no 值表（0 = 否 / 1 = 是）"""
        sql = "SELECT * FROM boolean WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def boolean_id(self, value):
        """由值（0 / 1）攞 boolean.id"""
        row = self.conn.execute(
            "SELECT id FROM boolean WHERE value = ?", (value,)).fetchone()
        return row["id"] if row else None

    # ---------------- value（版本值表）----------------
    def _value_id(self, value):
        """由版本字串攞 value.id（唔存在就登記，冪等）"""
        self.conn.execute(
            "INSERT INTO value (value) SELECT ? WHERE NOT EXISTS"
            " (SELECT 1 FROM value WHERE value = ?)", (value, value))
        row = self.conn.execute(
            "SELECT id FROM value WHERE value = ?", (value,)).fetchone()
        return row["id"] if row else None

    def values(self):
        """列出全部版本值（value 表）"""
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM value ORDER BY id")]

    # ---------------- registry（版本註冊表）----------------
    def versions(self):
        """列出註冊版本（registry JOIN value）"""
        return [dict(row) for row in self.conn.execute(
            "SELECT r.id, v.value AS version, r.pass_id, r.value_id,"
            " r.github_id, r.is_active, r.created_at, r.updated_at"
            " FROM registry r"
            " LEFT JOIN value v ON v.id = r.value_id"
            " ORDER BY r.id")]

    def registries(self, active_only=True):
        """列出 registry 原始行（id | pass_id | value_id | github_id）"""
        sql = "SELECT * FROM registry WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_version(self, version):
        """登記一個版本（冪等）—— value 存字串，registry 存註冊行

        返回 registry.id
        """
        vid = self._value_id(version)
        if vid is None:
            return None
        self.conn.execute(
            "INSERT INTO registry (value_id) SELECT ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE value_id = ?)", (vid, vid))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM registry WHERE value_id = ?", (vid,)).fetchone()
        return row["id"] if row else None

    def set_registry_github(self, registry_id, github_id):
        """連結 registry 行 -> github 操作記錄（github.id）"""
        self.conn.execute(
            "UPDATE registry SET github_id = ?,"
            " updated_at = datetime('now', 'localtime') WHERE id = ?",
            (github_id, registry_id))
        self.conn.commit()

    def set_registry_pass(self, registry_id, pass_id):
        """設定 registry 行嘅期望值（pass_id = expected.id）"""
        self.conn.execute(
            "UPDATE registry SET pass_id = ?,"
            " updated_at = datetime('now', 'localtime') WHERE id = ?",
            (pass_id, registry_id))
        self.conn.commit()

    # ---------------- github_action（字典）----------------
    def github_actions(self, active_only=True):
        """列出 GitHub 動作字典（commit / push）"""
        sql = "SELECT * FROM github_action WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def github_action_id(self, meta):
        """由 meta（commit / push）攞 github_action.id"""
        row = self.conn.execute(
            "SELECT id FROM github_action WHERE meta = ?", (meta,)).fetchone()
        return row["id"] if row else None

    # ---------------- github_status（字典）----------------
    def github_statuses(self, active_only=True):
        """列出 GitHub 狀態字典（pending / done / failed）"""
        sql = "SELECT * FROM github_status WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def github_status_id(self, meta):
        """由 meta（pending / done / failed）攞 github_status.id"""
        row = self.conn.execute(
            "SELECT id FROM github_status WHERE meta = ?", (meta,)).fetchone()
        return row["id"] if row else None

    # ---------------- github（操作記錄）----------------
    def githubs(self, active_only=True):
        """列出 GitHub 操作記錄（帶 action / status / version 名）"""
        sql = ("SELECT g.*, a.meta AS action, s.meta AS status,"
               " v.value AS version"
               " FROM github g"
               " LEFT JOIN github_action a ON a.id = g.github_action_id"
               " LEFT JOIN github_status s ON s.id = g.github_status_id"
               " LEFT JOIN registry r ON r.id = g.version_id"
               " LEFT JOIN value v ON v.id = r.value_id"
               " WHERE 1=1")
        if active_only:
            sql += " AND g.is_active = 1"
        sql += " ORDER BY g.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def record_github(self, github_session_id, action, status="pending",
                      version=None):
        """記錄一次 GitHub 操作（session + action + status + version）

        github_session_id = GitHub session ID（必填）
        action            = commit / push（meta 名，唔硬寫 id）
        status            = pending / done / failed（meta 名）
        version           = 版本字串（可選；唔存在就自動登記）
        返回 github.id
        """
        aid = self.github_action_id(action)
        if aid is None:
            raise ValueError(
                f"唔知嘅 github action: {action}"
                f"（可用：{[a['meta'] for a in self.github_actions()]}）")
        sid = self.github_status_id(status)
        if sid is None:
            raise ValueError(
                f"唔知嘅 github status: {status}"
                f"（可用：{[s['meta'] for s in self.github_statuses()]}）")
        vid = self.add_version(version) if version else None
        cur = self.conn.execute(
            "INSERT INTO github"
            " (github_session_id, github_action_id, github_status_id,"
            "  version_id) VALUES (?, ?, ?, ?)",
            (github_session_id, aid, sid, vid))
        gid = cur.lastrowid
        # 反向連結：registry.github_id -> github.id（用戶要求嘅 4 欄之一）
        if vid is not None:
            self.set_registry_github(vid, gid)
        self.conn.commit()
        return gid

    def set_github_status(self, github_id, status):
        """更新操作狀態（pending / done / failed，meta 名）"""
        sid = self.github_status_id(status)
        if sid is None:
            raise ValueError(
                f"唔知嘅 github status: {status}"
                f"（可用：{[s['meta'] for s in self.github_statuses()]}）")
        self.conn.execute(
            "UPDATE github SET github_status_id = ?,"
            " updated_at = datetime('now', 'localtime') WHERE id = ?",
            (sid, github_id))
        self.conn.commit()

    # ---------------- github_ignore（忽略規則）----------------
    def github_ignores(self, active_only=True):
        """列出忽略規則（帶 boolean 值 + 描述，value 由本 DB boolean 查）"""
        sql = ("SELECT i.*, b.value AS boolean_value,"
               " b.description AS boolean_desc,"
               " CASE WHEN b.value = 1 THEN 'with' ELSE 'without' END AS action"
               " FROM github_ignore i"
               " LEFT JOIN boolean b ON b.id = i.boolean_id"
               " WHERE 1=1")
        if active_only:
            sql += " AND i.is_active = 1"
        sql += " ORDER BY i.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def set_github_ignore(self, pattern, value, description=None):
        """設定一條忽略規則（value: 0 = 否 / 1 = 是）

        冪等：已存在就更新 boolean_id / description。
        """
        bid = self.boolean_id(value)
        if bid is None:
            raise ValueError(f"唔知嘅 boolean value: {value}（可用：0 / 1）")
        self.conn.execute(
            "INSERT INTO github_ignore (pattern, boolean_id, description)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM github_ignore WHERE pattern = ?)",
            (pattern, bid, description, pattern))
        self.conn.execute(
            "UPDATE github_ignore SET boolean_id = ?, description = ?"
            " WHERE pattern = ?", (bid, description, pattern))
        self.conn.commit()

    def write_gitignore(self, path=GITIGNORE_PATH):
        """由 github_ignore 表生成 .gitignore（boolean value = 1 先寫）

        表 = 權威；檔案係生成物。用戶要求：有表定義 yes / no。
        """
        lines = [
            "# ============================================================",
            "# .gitignore — 由 version/github_ignore 表權威定義（唔好手改）",
            "# 表：version.db :: github_ignore（pattern + boolean_id -> boolean.id）",
            "#   boolean：0 = 否（唔要）/ 1 = 是（要）",
            "#   還原：python -m version.route gitignore",
            "# ============================================================",
            "",
        ]
        for r in self.github_ignores(active_only=True):
            desc = r.get("description") or ""
            lines.append(f"# ---- {desc} ----" if desc else "")
            lines.append(r["pattern"])
        text = "\n".join(lines) + "\n"
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def close(self):
        self.conn.close()