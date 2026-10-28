-- schema dump: structure.db
-- generated : 2026-10-27T16:21:48
-- objects   : 18（table=18）

-- [table] db_field_check
CREATE TABLE "db_field_check" (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                structure_db_table_id  INTEGER NOT NULL,
                structure_db_field_id  INTEGER NOT NULL,
                total                  INTEGER NOT NULL DEFAULT 0,
                json                   TEXT,
                UNIQUE (structure_db_field_id)
            );

-- [table] db_field_format
CREATE TABLE db_field_format (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    format      TEXT    NOT NULL UNIQUE,   -- 原子格式 token（primary_key / unique / ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] db_field_property
CREATE TABLE db_field_property (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    db_field_type_id   INTEGER NOT NULL,  -- db_field_type.id（型別）
    db_field_format_id INTEGER NOT NULL,  -- db_field_format.id（性質 token）
    UNIQUE (db_field_type_id, db_field_format_id)
);

-- [table] db_field_setting
CREATE TABLE db_field_setting (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    db_field_unique_id   INTEGER NOT NULL,  -- db_field_unique.id（欄位名）
    db_field_property_id INTEGER NOT NULL,  -- db_field_property.id（型別×性質）
    is_active            BOOLEAN NOT NULL DEFAULT 1,
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (db_field_unique_id, db_field_property_id)
);

-- [table] db_field_type
CREATE TABLE db_field_type (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    meta                TEXT    NOT NULL UNIQUE,   -- 型別名：INTEGER / TEXT / ...
    description         TEXT    NOT NULL,          -- 型別描述（人讀）
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, default_value BOOLEAN NOT NULL DEFAULT 0 CHECK (default_value IN (0,1)));

-- [table] db_field_unique
CREATE TABLE db_field_unique (
    id          INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    value       TEXT    NOT NULL UNIQUE   -- 欄位名（id / meta_key / is_active ...）
);

-- [table] db_table_setting
CREATE TABLE "db_table_setting" (
                        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                        meta_key            TEXT    NOT NULL,
                        seq_id         INTEGER,
                        is_active           BOOLEAN NOT NULL DEFAULT 1,
                        created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                        updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')), db_field_type_id INTEGER,
                        UNIQUE (meta_key)
                    );

-- [table] db_table_setting_new
CREATE TABLE db_table_setting_new (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_key            TEXT    NOT NULL UNIQUE,
                db_field_setting_id INTEGER NOT NULL,
                position_id         INTEGER,
                is_active           BOOLEAN NOT NULL DEFAULT 1,
                created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] default_value
CREATE TABLE default_value (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    db_field_type_id  INTEGER NOT NULL,          -- db_field_type.id（型別）
    value             TEXT    NOT NULL,          -- 預設值（0 / NOW / [] ...）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (db_field_type_id)
);

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- [table] structure_db_field
CREATE TABLE structure_db_field (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_db_table_id INTEGER NOT NULL, -- structure_db_table.id（邊張表）
    field_name           TEXT    NOT NULL,  -- 真欄位名（id / question_id ...）
    description          TEXT    NOT NULL DEFAULT '', -- 欄位用途（唔可以 NULL）
    is_active            BOOLEAN NOT NULL DEFAULT 1,
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')), db_field_unique_id INTEGER, db_field_check_id INTEGER,
    UNIQUE (structure_db_table_id, field_name)
);

-- [table] structure_db_table
CREATE TABLE structure_db_table (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id  INTEGER NOT NULL,          -- taxonomy.tree.id（1 = channel）
    module_id   INTEGER NOT NULL,          -- taxonomy.taxonomy.id（tree = module）
    table_name  TEXT    NOT NULL,          -- 真表名（question / run / registry ...）
    description TEXT    NOT NULL DEFAULT '', -- 表用途（唔可以 NULL，2026-10-26）
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (channel_id, module_id, table_name)
);

-- [table] structure_module
CREATE TABLE structure_module (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type_id INTEGER NOT NULL,   -- structure_type.id（package / db / file）
    root_id           INTEGER NOT NULL,   -- structure_root.id（上游身份）
    module_id         INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    value             TEXT    NOT NULL,   -- 地址值（api_module / api_module.db）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')), location TEXT,
    UNIQUE (structure_type_id, root_id, module_id, value)
);

-- [table] structure_root
CREATE TABLE structure_root (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type_id INTEGER NOT NULL,   -- structure_type.id（root）
    value             TEXT    NOT NULL,   -- 地址值（C:\projects\meta）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')), location TEXT,
    UNIQUE (structure_type_id, value)
);

-- [table] structure_skill
CREATE TABLE structure_skill (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type_id   INTEGER NOT NULL,   -- structure_type.id（package）
    structure_module_id INTEGER NOT NULL,   -- structure_module.id（上游）
    skill_id            INTEGER NOT NULL,   -- taxonomy.taxonomy.id（skill 身份）
    value               TEXT    NOT NULL,   -- skill 名（build_columns ...）
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')), location TEXT,
    UNIQUE (structure_type_id, structure_module_id, skill_id, value)
);

-- [table] structure_taxonomy
CREATE TABLE structure_taxonomy (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id           INTEGER NOT NULL,   -- taxonomy.tree.id（channel / module / skill）
    structure_type_id INTEGER NOT NULL,   -- structure_type.id（package / file / db_table / db_field / db）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id, structure_type_id)
);

-- [table] structure_type
CREATE TABLE structure_type (
    id          INTEGER PRIMARY KEY,       -- 固定 id（1=package 2=file 3=db_table 4=db_field）
    meta        TEXT    NOT NULL UNIQUE,   -- package / file / db_table / db_field
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] value
CREATE TABLE value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT    NOT NULL,           -- check（CHECK 約束）
    formula     TEXT    NOT NULL,           -- 模板（placeholder 執行時填）
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
