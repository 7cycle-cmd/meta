-- schema dump: definition.db
-- generated : 2026-10-27T16:21:48
-- objects   : 10（table=10）

-- [table] code_condition
CREATE TABLE code_condition (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id  INTEGER NOT NULL,          -- subject.id（邊個 subject）
    operator_id INTEGER NOT NULL,          -- operator.id（必須 / 唔可以 / 至少一次）
    expected_id INTEGER NOT NULL,          -- expected_def.id（期望咩）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (subject_id, operator_id, expected_id)
);

-- [table] db_field_required
CREATE TABLE db_field_required (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    table_definition_id INTEGER NOT NULL,   -- structure.db table_definition.id
    db_field_id         INTEGER NOT NULL,   -- structure.db db_field.id
    is_active           BOOLEAN NOT NULL DEFAULT 1,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')), seq_id INTEGER,
    UNIQUE (table_definition_id, db_field_id)
);

-- [table] db_table_required
CREATE TABLE db_table_required (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    table_definition_id INTEGER NOT NULL,   -- structure.db table_definition.id
    is_active           BOOLEAN NOT NULL DEFAULT 1,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')), seq_id INTEGER,
    UNIQUE (table_definition_id)
);

-- [table] expected_def
CREATE TABLE expected_def (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 期望值（例如 /health 一定要有 route）
    resource_id INTEGER,                   -- resource.db registry.id（source of truth）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] operator
CREATE TABLE operator (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 必須 / 唔可以 / 至少一次
    resource_id INTEGER,                   -- resource.db registry.id（source of truth）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] rule
CREATE TABLE rule (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type   TEXT    NOT NULL UNIQUE,
    check_method TEXT   NOT NULL,
    pattern     TEXT,
    description TEXT,
    enabled     BOOLEAN NOT NULL DEFAULT 1 CHECK (enabled IN (0,1)),
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

-- [table] structure_required
CREATE TABLE structure_required (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id          INTEGER NOT NULL,     -- taxonomy.tree.id（channel / module / skill）
    structure_type_id INTEGER NOT NULL,    -- structure_type.id（package / file / db_table / db_field）
    is_active        BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id, structure_type_id)
);

-- [table] subject
CREATE TABLE subject (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 主體名（例如 api.py 嘅 do_GET）
    resource_id INTEGER,                   -- resource.db registry.id（source of truth）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
