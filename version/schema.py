"""schema.py — version 權威 DDL 入口（唯一 schema 來源）

表：
    boolean        yes/no 值表（0 = 否 / 1 = 是）—— version.db 自有
    version        版本字典（version UNIQUE）
    github_action  GitHub 動作字典（commit / push）
    github_status  GitHub 狀態字典（pending / done / failed）
    github_ignore  GitHub 忽略規則（pattern + boolean_id -> boolean.id）
    github         一次 GitHub 操作記錄（session + action + status + version）
"""

# boolean：yes / no 值表（2026-10-27 用戶要求「value table」）
# 慣例同 common / template / terminology.db 一致：
#   id = 值本身（0 = 否 / 1 = 是），唔係 AUTOINCREMENT
BOOLEAN_DDL = """
CREATE TABLE IF NOT EXISTS boolean (
    id          INTEGER PRIMARY KEY,          -- 0 = 否 / 1 = 是
    value       INTEGER NOT NULL UNIQUE CHECK (value IN (0, 1)),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

VERSION_DDL = """
CREATE TABLE IF NOT EXISTS version (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT    NOT NULL UNIQUE
);
"""

# github_action：GitHub 動作字典（2026-10-27 用戶要求）
# 值域 = commit / push
GITHUB_ACTION_DDL = """
CREATE TABLE IF NOT EXISTS github_action (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- commit / push
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# github_status：GitHub 狀態字典（2026-10-27 用戶要求）
# 值域 = pending / done / failed
GITHUB_STATUS_DDL = """
CREATE TABLE IF NOT EXISTS github_status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- pending / done / failed
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# github_ignore：GitHub 忽略規則（2026-10-27 用戶要求）
# 每個 pattern 一條，value 指向 **本 DB boolean**（0 = 否 / 1 = 是）——
# yes/no 由 version.db 自己嘅 boolean 表定義，唔跨 DB。
GITHUB_IGNORE_DDL = """
CREATE TABLE IF NOT EXISTS github_ignore (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern     TEXT    NOT NULL UNIQUE,   -- *.db / __pycache__/ / *.bak* ...
    boolean_id  INTEGER NOT NULL,          -- FK -> boolean.id（0 = 否 / 1 = 是）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# github：一次 GitHub 操作記錄（2026-10-27 用戶要求）
#   id | github session ID | github_action_id | github_status_id | version_id
GITHUB_DDL = """
CREATE TABLE IF NOT EXISTS github (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    github_session_id  TEXT    NOT NULL,   -- github session ID
    github_action_id   INTEGER NOT NULL,   -- FK -> github_action.id（commit / push）
    github_status_id   INTEGER NOT NULL,   -- FK -> github_status.id（pending / done / failed）
    version_id         INTEGER,            -- FK -> version.id
    is_active          BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ["BOOLEAN_DDL", "VERSION_DDL", "GITHUB_ACTION_DDL",
           "GITHUB_STATUS_DDL", "GITHUB_IGNORE_DDL", "GITHUB_DDL"]