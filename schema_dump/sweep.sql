-- schema dump: sweep.db
-- generated : 2026-10-27T15:47:40
-- objects   : 12（table=12）

-- [table] action
CREATE TABLE action (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- DROP / KEEP / RENAME / ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] evidence
CREATE TABLE evidence (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id   INTEGER NOT NULL,          -- FK -> target.id
    collected_at TEXT   NOT NULL DEFAULT (datetime('now', 'localtime')),
    detail      TEXT,                       -- 收集到嘅證據（例如 0 行 / NULL 值）
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, proof_run_id INTEGER, verify_run_id INTEGER);

-- [table] mission
CREATE TABLE mission (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id   INTEGER NOT NULL,          -- FK -> target.id
    action_id   INTEGER NOT NULL,          -- FK -> action.id（DROP / KEEP）
    flow_id     INTEGER,                   -- flow.db flow.id（邊個 flow 執行）
    step_id     INTEGER,                   -- code_gen.db step.id（邊個 step 執行）
    task_id     INTEGER,                   -- task.db task.id（邊個 task 觸發）
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (target_id, action_id)
);

-- [table] mission_log
CREATE TABLE mission_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id  INTEGER NOT NULL,          -- FK -> mission.id
    run_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    status      TEXT    NOT NULL,          -- success / failed / skipped
    detail      TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] mission_run
CREATE TABLE mission_run (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id     INTEGER NOT NULL,       -- FK -> mission.id
    status_id      INTEGER,                -- common.db status.id（pass/fail/NA）
    schema_run_id  INTEGER,                -- schema.db schema_run.id（授權）
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] physical_type
CREATE TABLE physical_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- package / folder / coding / ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] proof
CREATE TABLE proof (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id INTEGER NOT NULL,          -- FK -> evidence.id
    mission_id  INTEGER,                    -- FK -> mission.id（邊個任務用咗呢個證明）
    proof       TEXT,                       -- 證明內容
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
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
                is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- [table] status
CREATE TABLE status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- empty / dead / legacy / active / ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] target
CREATE TABLE target (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id       TEXT    NOT NULL,   -- 資源識別（例如 taxonomy.db.module）
    identity_id       TEXT,                -- 身份（taxonomy_id + resource_id）
    status_id         INTEGER,             -- FK -> status.id（empty / dead / legacy）
    resource_type_id  INTEGER,             -- FK -> resource_type.id（db_table / db_field / ...）
    physical_type_id  INTEGER,             -- FK -> physical_type.id（package / folder / coding）
    is_active         BOOLEAN NOT NULL DEFAULT 1,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')), source_version_id INTEGER, target_version_id INTEGER, plan_action TEXT, plan_status TEXT NOT NULL DEFAULT 'none',
    UNIQUE (resource_id)
);
