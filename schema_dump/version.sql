-- schema dump: version.db
-- generated : 2026-10-27T16:21:48
-- objects   : 9（table=9）

-- [table] boolean
CREATE TABLE boolean (
    id          INTEGER PRIMARY KEY,          -- 0 = 否 / 1 = 是
    value       INTEGER NOT NULL UNIQUE CHECK (value IN (0, 1)),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] github
CREATE TABLE github (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    github_session_id  TEXT    NOT NULL,   -- github session ID
    github_action_id   INTEGER NOT NULL,   -- FK -> github_action.id（commit / push）
    github_status_id   INTEGER NOT NULL,   -- FK -> github_status.id（pending / done / failed）
    version_id         INTEGER,            -- FK -> version.id
    is_active          BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] github_action
CREATE TABLE github_action (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- commit / push
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] github_ignore
CREATE TABLE github_ignore (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern     TEXT    NOT NULL UNIQUE,   -- *.db / __pycache__/ / *.bak* ...
    boolean_id  INTEGER NOT NULL,          -- FK -> common.db boolean.id（1 = 要/with）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] github_status
CREATE TABLE github_status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- pending / done / failed
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] registry
CREATE TABLE registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pass_id     INTEGER,            -- 期望值（expected.id）
    value_id    INTEGER,            -- 版本值（value.id）
    github_id   INTEGER,            -- GitHub 操作記錄（github.id）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] skill
CREATE TABLE skill (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_key    TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- [table] value
CREATE TABLE value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 版本字串（1.4.0 / v1 ...）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
