-- schema dump: question.db
-- generated : 2026-10-27T15:47:40
-- objects   : 30（table=30）

-- [table] 5W2H
CREATE TABLE "5W2H" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,   -- 提問框架（what / where / when / who / why / how / how much）
    is_active  BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] answer
CREATE TABLE answer (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                boolean_id  INTEGER NOT NULL REFERENCES boolean(id),
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] api
CREATE TABLE api (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    api         TEXT    NOT NULL,           -- API 路徑（例如 /run /english）
    api_type_id INTEGER NOT NULL,           -- api_type.id（GET / POST）
    flow_id     INTEGER,                    -- flow.id（呢條 API 屬於邊條 flow）
    value_id    INTEGER,                    -- value.id（呢條 API 消耗邊種 value）
    description TEXT,                       -- 描述
    status_id   INTEGER,                    -- status.id（1=active 2=deprecated）
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (api, api_type_id)
);

-- [table] api_type
CREATE TABLE api_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- GET / POST / PUT / DELETE
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] boolean
CREATE TABLE boolean (
                id          INTEGER PRIMARY KEY,
                value       INTEGER NOT NULL UNIQUE
                            CHECK (value IN (0, 1)),
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] code_condition
CREATE TABLE code_condition (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- file / def / class / async def / main
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] code_flow
CREATE TABLE code_flow (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name   TEXT    NOT NULL UNIQUE,   -- 檔案名（sql.py / api_server.py ...）
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] code_registry
CREATE TABLE code_registry (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code_type_id INTEGER NOT NULL,           -- code_type.id（邊類）
    condition_id INTEGER NOT NULL,           -- code_condition.id（file/def/class）
    meta         TEXT    NOT NULL,           -- 用途名（sql / run_flow...）
    description  TEXT,                       -- 描述
    filename     TEXT    NOT NULL,           -- 檔名（sql.py）
    mapping_line INTEGER,                    -- 對應行（真實行號）
    is_active    BOOLEAN NOT NULL DEFAULT 1,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (meta, filename, mapping_line)
);

-- [table] code_step
CREATE TABLE code_step (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    code_flow_id     INTEGER NOT NULL,      -- code_flow.id（邊條 flow）
    code_registry_id INTEGER NOT NULL,      -- code_registry.id（執行邊個函數）
    seq_id           INTEGER NOT NULL,      -- seq.id（第幾步）
    is_active        BOOLEAN NOT NULL DEFAULT 1,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (code_flow_id, seq_id)
);

-- [table] code_type
CREATE TABLE code_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- preflight / schema / mission ...
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] expected
CREATE TABLE expected (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                boolean_id  INTEGER NOT NULL REFERENCES boolean(id),
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            , pass_value TEXT);

-- [table] flow
CREATE TABLE "flow" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name  TEXT    NOT NULL UNIQUE,   -- 驗證鏈名（5w2h / spec ...）
    is_active  BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] operator
CREATE TABLE "operator" (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 計算條件名（is_true / is_not_empty / == / >= / <= / != / > / <）
    description TEXT,                      -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, expression TEXT);

-- [table] question
CREATE TABLE question (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id        INTEGER NOT NULL,
                "5w2h_id"      INTEGER NOT NULL,
                operator_id INTEGER,
                expected_id    INTEGER,
                is_active      BOOLEAN NOT NULL DEFAULT 1,
                created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                UNIQUE (test_id, "5w2h_id", expected_id)
            );

-- [table] question_text
CREATE TABLE question_text (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id     INTEGER NOT NULL,           -- test.id（symbol / english / INT...）
    w5w2h_id    INTEGER NOT NULL,           -- "5W2H".id（what / where...）
    text        TEXT    NOT NULL,           -- 問題文字
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (test_id, w5w2h_id)
);

-- [table] registry
CREATE TABLE registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT, meta TEXT NOT NULL UNIQUE, description TEXT, is_active BOOLEAN NOT NULL CHECK (is_active IN (0,1)) DEFAULT 1, created_at TEXT DEFAULT (datetime('now', 'localtime')), updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- [table] result
CREATE TABLE result (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER NOT NULL,    -- run.id（邊次執行）
    question_id  INTEGER NOT NULL,    -- question.id（邊個問題）
    answer_id    INTEGER,             -- answer.id（1=真/有，0=假/冇）
    status_id    INTEGER,             -- status.id（1=approved 2=rejected 3=NA）
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (run_id, question_id)
);

-- [table] run
CREATE TABLE "run" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id    INTEGER NOT NULL,   -- question_flow.id（邊條驗證鏈）
    value_id   INTEGER,            -- value.id（提交去檢查嘅值）
    step_id    INTEGER,            -- question_step.id（停喺邊步）
    status_id  INTEGER,            -- status.id（1=approved 2=rejected 3=NA）
    is_active  BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] seq
CREATE TABLE seq (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seq         INTEGER NOT NULL UNIQUE,  -- 序號（1, 2, 3... 10）
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] shortcut
CREATE TABLE shortcut (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    api_url     TEXT    NOT NULL UNIQUE,  -- API 路徑（例如 /run/english-word /english）
    shortcut    TEXT    NOT NULL,         -- flow 名（例如 english word）
    is_active   BOOLEAN NOT NULL DEFAULT 1,
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

-- [table] status
CREATE TABLE status (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                boolean_id INTEGER NOT NULL REFERENCES boolean(id),
                is_active  BOOLEAN NOT NULL DEFAULT 1,
                created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] step
CREATE TABLE step (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id        INTEGER NOT NULL,   -- flow.id（邊條驗證鏈）
    question_id    INTEGER NOT NULL,   -- question.id（問邊個問題）
    seq_id         INTEGER NOT NULL,   -- seq.id（第幾步：1, 2, 3...）
    is_active      BOOLEAN NOT NULL DEFAULT 1,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, seq_id)
);

-- [table] taxonomy
CREATE TABLE "taxonomy" (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id     INTEGER NOT NULL,   -- taxonomy tree.id（=2 module 大類）
    flow_id INTEGER NOT NULL,   -- question.id（邊個問題）
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id, flow_id)
);

-- [table] test
CREATE TABLE "test" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,   -- 盲測維度名（speech / word / spec ...）
    is_active  BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] unique_defne
CREATE TABLE unique_defne (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    value           TEXT    NOT NULL UNIQUE,  -- 'value_id=value_id'（配對字串）
    left_value_id   INTEGER NOT NULL,         -- value_defne.id（左邊）
    right_value_id  INTEGER NOT NULL,         -- value_defne.id（右邊）
    description     TEXT,                     -- 描述
    is_active       BOOLEAN NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (left_value_id, right_value_id)
);

-- [table] value
CREATE TABLE value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT,                      -- 提交去檢查嘅值（例如 "Anthropic spec"）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] value_defne
CREATE TABLE value_defne (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 實際值（xxx）
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] w5w2h_text
CREATE TABLE w5w2h_text (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    w5w2h_id    INTEGER NOT NULL,           -- "5W2H".id（what / where...）
    text        TEXT    NOT NULL,           -- 問法（係咩？）
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (w5w2h_id)
);
