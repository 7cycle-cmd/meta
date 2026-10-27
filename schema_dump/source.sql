-- schema dump: source.db
-- generated : 2026-10-27T15:47:40
-- objects   : 22（table=22）

-- [table] INT
CREATE TABLE "INT" (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 整數字符（0-9）
    description TEXT,                       -- 描述
    source_id   INTEGER,                    -- source.id（證明來源：IEEE 754）
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] api
CREATE TABLE api (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    api         TEXT    NOT NULL,           -- API 路徑（例如 /sources）
    api_type_id INTEGER NOT NULL,           -- api_type.id（GET / POST）
    flow_id     INTEGER,                    -- flow.id（呢條 API 屬於邊條 flow）
    value_id    INTEGER,                    -- value.id（呢條 API 消耗邊種 value）
    description TEXT,                       -- 描述
    status_id   INTEGER,                    -- status.id（1=active 2=deprecated）
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (api, api_type_id)
);

-- [table] api_type
CREATE TABLE api_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- GET / POST / PUT / DELETE
    description TEXT,                       -- 描述
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] authority_level
CREATE TABLE authority_level (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            meta        TEXT    NOT NULL UNIQUE,
            level       INTEGER NOT NULL UNIQUE,
            description TEXT,
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

-- [table] data_format
CREATE TABLE data_format (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 格式名（json / xml / csv / yaml ...）
    description TEXT,                       -- 描述
    source_id   INTEGER,                    -- source.id（證明來源）
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, char_format TEXT NOT NULL DEFAULT 'lowercase' CHECK (char_format IN ('lowercase','uppercase','both')));

-- [table] english
CREATE TABLE english (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lowercase   TEXT    NOT NULL UNIQUE,   -- 細階字母（a-z，26 行）
    uppercase   TEXT,                      -- 對應大階（A-Z）
    description TEXT,                       -- 描述
    source_id   INTEGER,                    -- source.id（證明來源：OED）
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] flow
CREATE TABLE flow (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name  TEXT    NOT NULL UNIQUE,   -- 驗證鏈名（source / charsets / languages ...）
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] industry
CREATE TABLE industry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 行業名（例如 information technology）
    description TEXT,                       -- 行業說明
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] programming_language
CREATE TABLE "programming_language" (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 語言名（python / javascript / java / c ...）
    description TEXT,                       -- 描述
    source_id   INTEGER,                    -- source.id（證明來源）
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, char_format TEXT NOT NULL DEFAULT 'lowercase' CHECK (char_format IN ('lowercase','uppercase','both')));

-- [table] provider
CREATE TABLE "provider" (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            meta               TEXT    NOT NULL UNIQUE,
            authority_level_id INTEGER,
            description        TEXT,
            is_active          INTEGER NOT NULL DEFAULT 1,
            created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        , official_url TEXT, industry_id INTEGER);

-- [table] result
CREATE TABLE result (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER NOT NULL,    -- run.id（邊次執行）
    step_id      INTEGER NOT NULL,    -- step.id（驗證邊步）
    source_id    INTEGER NOT NULL,    -- source.id（驗證邊個來源）
    has_provider INTEGER NOT NULL DEFAULT 0,  -- provider 存在（0/1）
    has_url      INTEGER NOT NULL DEFAULT 0,  -- official_url 非空（0/1）
    status_id    INTEGER,             -- status.id（1=approved 2=rejected 3=NA）
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (run_id, step_id)
);

-- [table] run
CREATE TABLE run (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id    INTEGER NOT NULL,   -- flow.id（邊條驗證鏈）
    step_id    INTEGER,            -- step.id（停喺邊步）
    status_id  INTEGER,            -- status.id（1=approved 2=rejected 3=NA）
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] seq
CREATE TABLE seq (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seq         INTEGER NOT NULL UNIQUE,  -- 序號（1, 2, 3... 10）
    is_active   INTEGER NOT NULL DEFAULT 1,
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

-- [table] source
CREATE TABLE "source" (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT    NOT NULL UNIQUE,
            provider_id INTEGER,
            description TEXT,
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

-- [table] source_proof
CREATE TABLE "source_proof" (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT    NOT NULL UNIQUE,   -- 詞（mcp / definition...）
    source_id   INTEGER,                   -- source.id（證明來源）
    proof       TEXT,                      -- proof 文字（'Provider: Topic'）
    description TEXT,                       -- 描述
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, registered_by TEXT, run_id INTEGER);

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- [table] status
CREATE TABLE status (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    status     TEXT    NOT NULL UNIQUE,   -- approved / rejected / NA
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] step
CREATE TABLE step (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id        INTEGER NOT NULL,   -- flow.id（邊條驗證鏈）
    source_id      INTEGER NOT NULL,   -- source.id（檢查邊個來源）
    seq_id         INTEGER NOT NULL,   -- seq.id（第幾步：1, 2, 3...）
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, seq_id)
);

-- [table] symbol
CREATE TABLE symbol (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 單個符號字符（/ . , ; ' [ ] ...）
    description TEXT,                       -- 描述
    source_id   INTEGER,                    -- source.id（證明來源：ISO/IEC 9075）
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] type_symbol
CREATE TABLE type_symbol (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_type  TEXT    NOT NULL,           -- 'language' | 'data_format'
    owner_id    INTEGER NOT NULL,           -- programming_language.id | data_format.id
    value       TEXT    NOT NULL,           -- 允許嘅符號字符
    description TEXT,                       -- 描述
    source_id   INTEGER,                    -- source.id（證明來源）
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (owner_type, owner_id, value),
    CHECK (owner_type IN ('language', 'data_format'))
);

-- [table] value
CREATE TABLE value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT,                      -- 值（source / provider / industry...）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
