-- schema dump: common.db
-- generated : 2026-10-27T15:47:40
-- objects   : 13（table=13）

-- [table] action
CREATE TABLE action (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 動作名（DROP / create / read ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] boolean
CREATE TABLE boolean (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       INTEGER NOT NULL UNIQUE CHECK (value IN (0,1)),  -- 只有 0 / 1
    description TEXT,                       -- 人讀描述（0 = 否 / 1 = 是）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] migration_activity
CREATE TABLE migration_activity (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_id     INTEGER,                    -- 父 migration（一次遷移任務；可選）
    resource_id      INTEGER NOT NULL,           -- resource.db registry.id（邊個資源）
    resource_type_id INTEGER,                    -- registry.type_id（資源類型快照）
    action_id        INTEGER NOT NULL,           -- common.db action.id（動作）
    status_id        INTEGER NOT NULL,           -- common.db status.id（狀態）
    is_active        BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] registry
CREATE TABLE registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT, meta TEXT NOT NULL UNIQUE, description TEXT, is_active BOOLEAN NOT NULL CHECK (is_active IN (0,1)) DEFAULT 1, created_at TEXT DEFAULT (datetime('now', 'localtime')), updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- [table] resource_action
CREATE TABLE resource_action (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ontology_id INTEGER,                    -- ontology.db ontology.id（可選：邊個 ontology）
    filling_id  INTEGER,                    -- code_gen.db filling.id（可選：邊個 filling）
    resource_id INTEGER NOT NULL,           -- resource.db registry.id（邊個資源）
    action_id   INTEGER NOT NULL,           -- common.db action.id（正確動作）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (resource_id, action_id, ontology_id, filling_id)
);

-- [table] resource_status
CREATE TABLE resource_status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ontology_id INTEGER,                    -- ontology.db ontology.id（可選：邊個 ontology）
    filling_id  INTEGER,                    -- code_gen.db filling.id（可選：邊個 filling）
    resource_id INTEGER NOT NULL,           -- resource.db registry.id（邊個資源）
    status_id   INTEGER NOT NULL,           -- common.db status.id（正確狀態）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (resource_id, status_id, ontology_id, filling_id)
);

-- [table] role
CREATE TABLE role (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 角色名（api / worker / migration / sweep ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] seq
CREATE TABLE seq (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 位置名（1 / 2 / 3 ...）
    value       INTEGER,                   -- 正規數值（10-100；2026-10-25 用戶要求）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] skill
CREATE TABLE skill (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_key    TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1
                            CHECK (is_active IN (0,1)),
                created_at  TEXT NOT NULL
                            DEFAULT (datetime('now', 'localtime'))
            );

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- [table] status
CREATE TABLE status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 狀態名（active / dead / pending ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] sweep_activity
CREATE TABLE sweep_activity (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sweep_id    INTEGER,
                resource_id INTEGER NOT NULL,
                type_id     INTEGER NOT NULL,
                action_id   INTEGER NOT NULL,
                is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] token
CREATE TABLE token (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id    TEXT    NOT NULL UNIQUE,   -- token 文字識別（module.file）
    module_id   INTEGER NOT NULL,          -- taxonomy.taxonomy.id（tree=module）
    file_id     INTEGER,                   -- structure_module file 行 id（可選）
    role_id     INTEGER NOT NULL,          -- common.db role.id（api / worker ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
