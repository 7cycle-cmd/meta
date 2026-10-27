-- schema dump: template.db
-- generated : 2026-10-27T15:47:40
-- objects   : 21（table=21）

-- [table] 5W2H
CREATE TABLE "5W2H" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] answer
CREATE TABLE answer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id  INTEGER NOT NULL
                REFERENCES boolean(id),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] boolean
CREATE TABLE boolean (
    id          INTEGER PRIMARY KEY,
    value       INTEGER NOT NULL UNIQUE
                CHECK (value IN (0, 1)),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] condition
CREATE TABLE condition (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] decorator
CREATE TABLE decorator (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,  -- 裝飾器名（@formula_def 用）
    formula_full    TEXT    NOT NULL,         -- 完整公式（<table> = placeholder）
    language_id     INTEGER NOT NULL DEFAULT 1,  -- language.id（SQL=1）
    table_meta      TEXT,                     -- 真表名（seq / structure_db_field ...）
    field_meta      TEXT,                     -- 欄位名（id / package_id ...）
    operator_meta   TEXT,                     -- operator.meta（== / >= ...）
    preflight_value TEXT,                     -- 條件值（"module_id" 等）
    db_file         TEXT,                     -- 執行 DB（template.db / structure.db）
    cuter_split     BOOLEAN NOT NULL DEFAULT 1 CHECK (cuter_split IN (0,1)),
    is_active       BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] evidence
CREATE TABLE evidence (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    formula_id   INTEGER NOT NULL,   -- formula.id
    table_name   TEXT,               -- 被證明嘅表
    field_name   TEXT,               -- 被證明嘅欄位
    value        TEXT,               -- 比較值（SSOT 真值）
    expected     TEXT,               -- 期望值
    actual       TEXT,               -- 實際值（執行）
    is_match     BOOLEAN NOT NULL DEFAULT 0 CHECK (is_match IN (0,1)),
    evidence     TEXT,               -- raw 證據（JSON）
    is_active    BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] expected
CREATE TABLE expected (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id  INTEGER NOT NULL
                REFERENCES boolean(id),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] flow
CREATE TABLE flow (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name  TEXT    NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] formula
CREATE TABLE formula (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full        TEXT    NOT NULL,   -- 完整公式（xxx=<select * from ...>）
    package_id  INTEGER,            -- taxonomy.taxonomy.id（出處 package）
    file_id     INTEGER,            -- structure_module.id（出處 file 層）
    line        INTEGER,            -- 出處行號
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, db_file TEXT);

-- [table] formula_cuter
CREATE TABLE formula_cuter (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    formula_id   INTEGER NOT NULL,   -- formula.id
    seq_id  INTEGER NOT NULL,   -- 次序（1 開始）
    value        TEXT    NOT NULL, python_ast_id INTEGER, source_id INTEGER,   -- token（select / * / from / SPACE ...）
    UNIQUE (formula_id, seq_id)
);

-- [table] operator
CREATE TABLE operator (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- operator 名（== / >= / <= ...）
    expression  TEXT,                      -- 判斷表達式
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] preflight_condition
CREATE TABLE preflight_condition (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    formula_id             INTEGER NOT NULL,  -- formula.id
    structure_db_field_id  INTEGER NOT NULL,  -- structure.db structure_db_field.id
    operator_id            INTEGER,           -- calculation.id
    preflight_id           INTEGER,           -- preflight 值（id）
    is_active              BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (formula_id, structure_db_field_id, preflight_id)
);

-- [table] preflight_table
CREATE TABLE preflight_table (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    formula_id            INTEGER NOT NULL,  -- formula.id
    structure_db_table_id INTEGER NOT NULL,  -- structure.db structure_db_table.id
    is_active             BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at            TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (formula_id, structure_db_table_id)
);

-- [table] proof
CREATE TABLE proof (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id  INTEGER NOT NULL,   -- language.id（SQL / Python ...）
    formula_id   INTEGER NOT NULL,   -- formula.id
    is_active    BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (language_id, formula_id)
);

-- [table] question
CREATE TABLE question (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id        INTEGER NOT NULL,   -- test.id
    "5w2h_id"      INTEGER NOT NULL,   -- "5W2H".id
    operator_id    INTEGER,            -- calculation.id（用邊個 operator）
    expected_id    INTEGER,            -- expected.id
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (condition_id, "5w2h_id", expected_id)
);

-- [table] run
CREATE TABLE run (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id    INTEGER NOT NULL,   -- flow.id
    value_id   INTEGER,            -- value.id
    step_id    INTEGER,            -- step.id
    status_id  INTEGER,            -- status.id
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] seq
CREATE TABLE seq (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seq         INTEGER NOT NULL UNIQUE,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- [table] status
CREATE TABLE status (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id INTEGER NOT NULL
                REFERENCES boolean(id),
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] step
CREATE TABLE step (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id        INTEGER NOT NULL,   -- flow.id
    question_id    INTEGER NOT NULL,   -- question.id
    seq_id         INTEGER NOT NULL,   -- seq.id（第幾步）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
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
