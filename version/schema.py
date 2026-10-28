"""schema.py — version 權威 DDL 入口（唯一 schema 來源）

表：
    boolean        yes/no 值表（0 = 否 / 1 = 是）—— version.db 自有
    value          版本值表（版本字串，例如 1.4.0）
    registry       版本註冊表（id | pass_id | value_id | github_id）
    github_action  GitHub 動作字典（commit / push）
    github_status  GitHub 狀態字典（pending / done / failed）
    github_ignore  GitHub 忽略規則（pattern + boolean_id -> boolean.id）
    github         一次 GitHub 操作記錄（session + action + status + registry）

2026-10-27（用戶要求）：version 表 -> rename -> registry
    id | pass_id | value_id | github_id
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

# value：版本值表（2026-10-27 用戶要求 registry.value_id 指過去）
# 版本字串（1.4.0 / v1 ...）存喺呢度 —— value 係所有嘢嘅來源。
# UNIQUE：版本字串唔可以重複（保留舊 version 表嘅 UNIQUE 語意）。
VALUE_DDL = """
CREATE TABLE IF NOT EXISTS value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 版本字串（1.4.0 / v1 ...）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# registry：版本註冊表（2026-10-27 用戶要求：version -> rename -> registry）
#   id | pass_id | value_id | github_id
#     pass_id   = 期望值（expected.id；pass = 期望值，同 question 一致）
#     value_id  = 版本值（value.id；版本字串）
#     github_id = GitHub 操作記錄（github.id）
REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pass_id     INTEGER,            -- 期望值（expected.id）
    value_id    INTEGER,            -- 版本值（value.id）
    github_id   INTEGER,            -- GitHub 操作記錄（github.id）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 舊名 alias（遷移期兼容：2026-10-27 version 表改名做 registry）
VERSION_DDL = REGISTRY_DDL

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
# 2026-10-27：version_id -> registry.id（version 表改名做 registry）
GITHUB_DDL = """
CREATE TABLE IF NOT EXISTS github (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    github_session_id  TEXT    NOT NULL,   -- github session ID
    github_action_id   INTEGER NOT NULL,   -- FK -> github_action.id（commit / push）
    github_status_id   INTEGER NOT NULL,   -- FK -> github_status.id（pending / done / failed）
    version_id         INTEGER,            -- FK -> registry.id（版本註冊）
    is_active          BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ["BOOLEAN_DDL", "VALUE_DDL", "REGISTRY_DDL", "VERSION_DDL",
           "GITHUB_ACTION_DDL", "GITHUB_STATUS_DDL", "GITHUB_IGNORE_DDL",
           "GITHUB_DDL"]