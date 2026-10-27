-- schema dump: ast.db
-- generated : 2026-10-27T15:47:40
-- objects   : 6（table=6）

-- [table] analyze_module
CREATE TABLE analyze_module (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_module_id INTEGER NOT NULL,   -- structure_module.id
    function_id         INTEGER NOT NULL,   -- function.id
    db_field_check_id   INTEGER,            -- db_field_check.id（可選）
    is_active           BOOLEAN NOT NULL DEFAULT 1,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_module_id, function_id)
);

-- [table] analyze_root
CREATE TABLE analyze_root (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_root_id   INTEGER NOT NULL,   -- structure_root.id
    function_id         INTEGER NOT NULL,   -- function.id
    db_field_check_id   INTEGER,            -- db_field_check.id（可選）
    is_active           BOOLEAN NOT NULL DEFAULT 1,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_root_id, function_id)
);

-- [table] analyze_skill
CREATE TABLE analyze_skill (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_skill_id  INTEGER NOT NULL,   -- structure_skill.id
    function_id         INTEGER NOT NULL,   -- function.id
    db_field_check_id   INTEGER,            -- db_field_check.id（可選）
    is_active           BOOLEAN NOT NULL DEFAULT 1,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_skill_id, function_id)
);

-- [table] function
CREATE TABLE function (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    function                  TEXT    NOT NULL UNIQUE,  -- 函數名
    class_id                  INTEGER,                  -- function_class.id（可選）
    programming_language_id   INTEGER NOT NULL,         -- programming_language.id（python=1）
    is_active                 BOOLEAN NOT NULL DEFAULT 1,
    created_at                TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at                TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] function_class
CREATE TABLE function_class (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- class 名
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);
