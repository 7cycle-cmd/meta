"""schema.py — terminology 權威 DDL 入口

terminology.db 存放分類字典（2026-10-24s 字符定義搬去 character，
語言/格式/組合搬去 programming）：
    industry         行業分類
（2026-10-25：term / data_collect / authority_level / result 表已移除）
（2026-10-25：word_industry 移除，改為通用 evidence 表）
"""

INDUSTRY_DDL = """
CREATE TABLE IF NOT EXISTS industry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,
    description TEXT    NOT NULL DEFAULT '',  -- 唔可以有 NULL（2026-10-25）
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# evidence 表：每次 run 對每個 step/condition 嘅證明（2026-10-25 用戶要求）
# 通用證據表 —— 每個通過嘅判斷（condition）一條證據，附證明來源。
#    value_id     = 提交值（value.id）
#    run_id       = 證明 run（證據鏈，唔可以 fake）
#    condition_id = 通過咗邊個判斷（condition.id）
#    source_id    = 證明來源（source.db source.id；冇來源 = 冇證據可寫）
#    status_id    = 判斷結果（1=PASS 0=FAIL）
# 零 hardcode：任何 flow 嘅任何 step 都可以有證據，唔使改表。
EVIDENCE_DDL = """
CREATE TABLE IF NOT EXISTS evidence (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id     INTEGER NOT NULL,             -- 提交值（value.id）
    run_id       INTEGER NOT NULL,             -- 證明 run
    condition_id INTEGER NOT NULL,             -- 通過嘅判斷（condition.id）
    source_id    INTEGER NOT NULL,             -- 證明來源（source.db source.id）
    status_id    INTEGER NOT NULL,             -- 1=PASS 0=FAIL（boolean.id）
    is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (value_id, run_id, condition_id)
);
"""

# ============ question 表 clone（2026-10-24s：真 clone，兩邊獨立）============
# 用戶要求：test/value/run/flow/step/expected/calculation/answer/question/
# result/seq/status clone 去 terminology.db。新建空表，唔搬 question 資料。
# 用途：terminology 可以有自己嘅驗證鏈/字典，唔影響 question 執行。
# 2026-10-25：test 改名 condition（用戶要求）—— 測試維度 = 判斷條件。

CONDITION_DDL = """
CREATE TABLE IF NOT EXISTS condition (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,   -- 判斷條件名（symbol / english / INT ...）
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

W5H2_DDL = """
CREATE TABLE IF NOT EXISTS "5W2H" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,   -- 提問框架（what / where / when / who / why / how / how much）
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

VALUE_DDL = """
CREATE TABLE IF NOT EXISTS value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id        INTEGER NOT NULL,
    modele_skill_id  INTEGER NOT NULL,
    flow_pass_id    INTEGER NOT NULL,
    UNIQUE (value_id, modele_skill_id, flow_pass_id)
);
"""

RUN_DDL = """
CREATE TABLE IF NOT EXISTS run (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id    INTEGER NOT NULL,        -- 永遠唔可以空（2026-10-25 用戶：all table 無 NULL）
    value_id   INTEGER NOT NULL,        -- 冇提交值 = 指向 value 表 ''（空值行）
    step_id    INTEGER NOT NULL,        -- 全 PASS = 最後一步；FAIL = 停步
    status_id  INTEGER NOT NULL,        -- 1=approved 2=rejected
    answer_id  INTEGER NOT NULL,        -- 最終答案（1=真 2=假），由 status 推
    expected_id INTEGER NOT NULL,       -- 期望值（expected.id，flow 嘅最終期望）
    evidence_id INTEGER,                -- 證據鏈頭（evidence.id；FAIL run = NULL）
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

FLOW_DDL = """
CREATE TABLE IF NOT EXISTS flow (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name  TEXT    NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

STEP_DDL = """
CREATE TABLE IF NOT EXISTS step (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id        INTEGER NOT NULL,
    question_id    INTEGER NOT NULL,       -- 永遠唔可以空（用戶 2026-10-25：never）
    seq_id         INTEGER NOT NULL,
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, seq_id)
);
"""

# flow_branch 表：每次 run 對每個 condition 嘅實際判斷結果（2026-10-25 用戶要求）
# runtime 自動寫入（發生過咩 -> 記錄）。唔係規則！
FLOW_BRANCH_DDL = """
CREATE TABLE IF NOT EXISTS flow_branch (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        INTEGER NOT NULL,          -- 邊次 run（runtime 自動寫）
    value_id      INTEGER NOT NULL,          -- 提交值（value.id）
    condition_id  INTEGER NOT NULL,          -- 用邊個 condition 判斷
    status_id     INTEGER NOT NULL,          -- 實際結果：1=PASS 0=FAIL
    is_active     BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (run_id, condition_id)
);
"""

# next_flow 表：決策規則（2026-10-25 用戶要求）
# 3 鍵（flow + condition + status）-> flow_target_id（目標 flow id）。
# 引擎：跑完 flow -> 寫 flow_branch 行（runtime 判斷）-> 查 next_flow
# (flow, condition, status) -> flow_target_id = 下一條 flow -> 自動跑。
# 零 hardcode：加分支 = 加 next_flow 行。
NEXT_FLOW_DDL = """
CREATE TABLE IF NOT EXISTS next_flow (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id        INTEGER NOT NULL,          -- 邊條 flow 跑完就分叉
    condition_id   INTEGER NOT NULL,          -- 用邊個 condition（= flow_branch.condition_id）
    status_id      INTEGER NOT NULL,          -- 結果 key：1=PASS 0=FAIL（= flow_branch.status_id）
    flow_target_id INTEGER NOT NULL,          -- 目標 flow id（呢個結果 -> 去邊）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, condition_id, status_id)
);
"""

EXPECTED_DDL = """
CREATE TABLE IF NOT EXISTS expected (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id  INTEGER NOT NULL REFERENCES boolean(id),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# operator 表：operator 字典（點比）
# 2026-10-24：calculation 改名 operator（用戶要求，同 question 一致）
OPERATOR_DDL = """
CREATE TABLE IF NOT EXISTS operator (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- operator 名（== / >= / <= / != / > / <）
    expression  TEXT,                      -- 判斷表達式（answer = 答案，pass_value = 期望值）
    description TEXT,                      -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

ANSWER_DDL = """
CREATE TABLE IF NOT EXISTS answer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id  INTEGER NOT NULL REFERENCES boolean(id),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

QUESTION_DDL = """
CREATE TABLE IF NOT EXISTS question (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id   INTEGER NOT NULL,       -- condition.id（判斷條件）
    "5w2h_id"      INTEGER NOT NULL,
    operator_id    INTEGER,
    expected_id    INTEGER,
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (condition_id, "5w2h_id", expected_id)
);
"""

SEQ_DDL = """
CREATE TABLE IF NOT EXISTS seq (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seq         INTEGER NOT NULL UNIQUE,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

BOOLEAN_DDL = """
CREATE TABLE IF NOT EXISTS boolean (
    id          INTEGER PRIMARY KEY,        -- 0 或 1（id = value）
    value       INTEGER NOT NULL UNIQUE
                CHECK (value IN (0, 1)),    -- 只准 0/1（DB 層硬擋）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

STATUS_DDL = """
CREATE TABLE IF NOT EXISTS status (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id INTEGER NOT NULL REFERENCES boolean(id),
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# ============ 詞彙分類（word_category）============
# 2026-10-24s（用戶要求）：每個 word 一行，多欄分類。
# 判斷結果由 question 引擎產生（english / speech / symbol / INT / single_word），
# industry 由 terminology 字典查。word 嚟自 question 收過嘅 value。
WORD_CATEGORY_DDL = """
CREATE TABLE IF NOT EXISTS word_category (
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
"""

__all__ = ["INDUSTRY_DDL", "EVIDENCE_DDL",
           "CONDITION_DDL", "W5H2_DDL", "VALUE_DDL", "RUN_DDL", "FLOW_DDL", "STEP_DDL",
           "FLOW_BRANCH_DDL", "NEXT_FLOW_DDL",
           "EXPECTED_DDL", "OPERATOR_DDL", "ANSWER_DDL", "BOOLEAN_DDL",
           "QUESTION_DDL", "SEQ_DDL", "STATUS_DDL", "REGISTRY_DDL",
           "WORD_CATEGORY_DDL"]
