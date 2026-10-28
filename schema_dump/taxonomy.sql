-- schema dump: taxonomy.db
-- generated : 2026-10-27T16:21:48
-- objects   : 5（table=5）

-- [table] physical_path
CREATE TABLE physical_path (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id     INTEGER NOT NULL,          -- taxonomy.tree.id（channel / module / skill）
    module      TEXT    NOT NULL,           -- module 名（system_setting；channel 層 = root）
    entity_id   INTEGER,                    -- 該層實體身份（module=package.id / skill=taxonomy.id；channel=NULL）
    full_path   TEXT    NOT NULL,           -- 完整實體路徑
    path_json   TEXT    NOT NULL,           -- 路徑鏈 JSON（root -> module -> <層實體>）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id, module, entity_id)
);

-- [table] registry
CREATE TABLE registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id     INTEGER NOT NULL,          -- FK -> tree.id（channel / module / skill）
    meta        TEXT    NOT NULL,          -- 分類項目名（codegen / fill_value / cli ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id, meta)
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

-- [table] tree
CREATE TABLE "tree" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_key   TEXT    NOT NULL UNIQUE,   -- 定義 key（channel / module / skill）
    is_active  BOOLEAN NOT NULL DEFAULT 0 CHECK (is_active IN (0,1)),
    seq        INTEGER NOT NULL,          -- 排序序號（1,2,3...）
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
