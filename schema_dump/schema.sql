-- schema dump: schema.db
-- generated : 2026-10-27T16:21:48
-- objects   : 5（table=5）

-- [table] registry
CREATE TABLE registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT, meta TEXT NOT NULL UNIQUE, description TEXT, is_active BOOLEAN NOT NULL CHECK (is_active IN (0,1)) DEFAULT 1, created_at TEXT DEFAULT (datetime('now', 'localtime')), updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- [table] schema_check
CREATE TABLE schema_check (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL,          -- task.db task.id（邊個 task 要檢查）
    check_name  TEXT    NOT NULL,          -- 檢查名（api_exists / value_active ...）
    check_type  TEXT    NOT NULL,          -- 檢查類型（api_exists / value_active / value_broken / value_missing）
    passed      INTEGER NOT NULL,          -- 1 = 通過，0 = 失敗
    detail      TEXT,                      -- 詳細（例如 10/10 api 存在）
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] schema_run
CREATE TABLE schema_run (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL,          -- task.db task.id
    total       INTEGER NOT NULL,          -- 總檢查數
    passed      INTEGER NOT NULL,          -- 通過數
    failed      INTEGER NOT NULL,          -- 失敗數
    status      TEXT    NOT NULL,          -- ready / not_ready
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
