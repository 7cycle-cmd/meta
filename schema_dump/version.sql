-- schema dump: version.db
-- generated : 2026-10-27T15:47:40
-- objects   : 8（table=8）

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

-- [table] version
CREATE TABLE version (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT    NOT NULL UNIQUE
);
