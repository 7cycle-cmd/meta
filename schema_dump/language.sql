-- schema dump: language.db
-- generated : 2026-10-27T15:47:40
-- objects   : 5（table=5）

-- [table] display_text
CREATE TABLE display_text (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 文字 key（例如 module_name / greeting）
    description TEXT,                       -- 用途描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] language
CREATE TABLE language (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 語言代碼（zh / en / ja ...）
    description TEXT,                       -- 語言名（中文 / 英文 ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] registry
CREATE TABLE registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT, meta TEXT NOT NULL UNIQUE, description TEXT, is_active BOOLEAN NOT NULL CHECK (is_active IN (0,1)) DEFAULT 1, created_at TEXT DEFAULT (datetime('now', 'localtime')), updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- [table] skill
CREATE TABLE skill (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_key    TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1
                            CHECK (is_active IN (0,1)),
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);
