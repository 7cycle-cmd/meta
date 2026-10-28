-- schema dump: terminology.db
-- generated : 2026-10-27T16:21:48
-- objects   : 21（table=21）

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

-- [table] boolean
CREATE TABLE boolean (
                id          INTEGER PRIMARY KEY,
                value       INTEGER NOT NULL UNIQUE
                            CHECK (value IN (0, 1)),
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] condition
CREATE TABLE "condition" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,   -- 測試維度名（symbol / english / INT ...）
    is_active  BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] evidence
CREATE TABLE evidence (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id     INTEGER NOT NULL,             -- 提交值（value.id）
    run_id       INTEGER NOT NULL,             -- 證明 run
    condition_id INTEGER NOT NULL,             -- 通過嘅判斷（condition.id）
    source_id    INTEGER NOT NULL,             -- 證明來源（source.db source.id）
    status_id    INTEGER NOT NULL,             -- 1=PASS 0=FAIL（boolean.id）
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (value_id, run_id, condition_id)
);

-- [table] expected
CREATE TABLE expected (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                boolean_id  INTEGER NOT NULL REFERENCES boolean(id),
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] flow
CREATE TABLE flow (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name  TEXT    NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] flow_branch
CREATE TABLE flow_branch (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        INTEGER NOT NULL,          -- 邊次 run（runtime 自動寫）
    value_id      INTEGER NOT NULL,          -- 提交值（value.id）
    condition_id  INTEGER NOT NULL,          -- 用邊個 condition 判斷
    status_id     INTEGER NOT NULL,          -- 實際結果：1=PASS 0=FAIL
    is_active     BOOLEAN NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (run_id, condition_id)
);

-- [table] industry
CREATE TABLE industry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,
    description TEXT    NOT NULL DEFAULT '',  -- 唔可以有 NULL（2026-10-25）
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] next_flow
CREATE TABLE next_flow (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id        INTEGER NOT NULL,          -- 邊條 flow 跑完就分叉
    condition_id   INTEGER NOT NULL,          -- 用邊個 condition（= flow_branch.condition_id）
    status_id      INTEGER NOT NULL,          -- 結果 key：1=PASS 0=FAIL（= flow_branch.status_id）
    flow_target_id INTEGER NOT NULL,          -- 目標 flow id（呢個結果 -> 去邊）
    is_active      BOOLEAN NOT NULL DEFAULT 1,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, condition_id, status_id)
);

-- [table] operator
CREATE TABLE "operator" (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,
    expression  TEXT,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] question
CREATE TABLE question (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id   INTEGER NOT NULL,       -- condition.id（判斷條件）
    "5w2h_id"      INTEGER NOT NULL,
    operator_id    INTEGER,
    expected_id    INTEGER,
    is_active      BOOLEAN NOT NULL DEFAULT 1,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (condition_id, "5w2h_id", expected_id)
);

-- [table] registry
CREATE TABLE registry (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id        INTEGER NOT NULL,
    modele_skill_id  INTEGER NOT NULL,
    flow_pass_id    INTEGER NOT NULL,
    UNIQUE (value_id, modele_skill_id, flow_pass_id)
);

-- [table] run
CREATE TABLE run (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id    INTEGER NOT NULL,        -- 永遠唔可以空（2026-10-25 用戶：all table 無 NULL）
    value_id   INTEGER NOT NULL,        -- 冇提交值 = 指向 value 表 ''（空值行）
    step_id    INTEGER NOT NULL,        -- 全 PASS = 最後一步；FAIL = 停步
    status_id  INTEGER NOT NULL,        -- 1=approved 2=rejected
    answer_id  INTEGER NOT NULL,        -- 最終答案（1=真 2=假），由 status 推
    expected_id INTEGER NOT NULL,       -- 期望值（expected.id，flow 嘅最終期望）
    is_active  BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, evidence_id INTEGER);

-- [table] seq
CREATE TABLE seq (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seq         INTEGER NOT NULL UNIQUE,
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
    flow_id        INTEGER NOT NULL,
    question_id    INTEGER NOT NULL,       -- 永遠唔可以空（用戶 2026-10-25：never）
    seq_id         INTEGER NOT NULL,
    is_active      BOOLEAN NOT NULL DEFAULT 1,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, seq_id)
);

-- [table] value
CREATE TABLE value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] word_category
CREATE TABLE word_category (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT    NOT NULL UNIQUE,  -- 詞
    english     INTEGER NOT NULL DEFAULT 0,  -- word 全部由英文字母組成（letter 表）
    speech      INTEGER NOT NULL DEFAULT 0,  -- word 係英文單詞（is_english）
    symbol      INTEGER NOT NULL DEFAULT 0,  -- word 有冇符號
    INT         INTEGER NOT NULL DEFAULT 0,  -- word 全部係數字
    single_word INTEGER NOT NULL DEFAULT 0,  -- 單一詞（冇 _ 冇空格）
    industry    INTEGER NOT NULL DEFAULT 0,  -- 屬行業字典
    spec        INTEGER NOT NULL DEFAULT 0,  -- 屬 spec 字典
    has_proof   INTEGER NOT NULL DEFAULT 0,  -- 有 source 證明
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
