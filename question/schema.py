"""schema.py — question 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：TEST_DDL, W5H2_DDL, EXPECTED_DDL, QUESTION_DDL, QUESTION_FLOW_DDL, QUESTION_STEP_DDL, QUESTION_FLOW_RUN_DDL, STATUS_DDL, QUESTION_ANSWER_DDL
（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

TEST_DDL = """
CREATE TABLE IF NOT EXISTS test (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,   -- 測試維度名（symbol / english / INT ...）
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

# expected 表：期望值字典（只存「比幾多」）
# 2026-10-23c：移除 meta / expression（用戶要求）——
#   operator（點比）→ calculation 表；expected 只負責「期望值 pass_value」
#   原本 expected.meta 係判斷條件名、expression 係判斷表達式，
#   兩者已搬去 calculation（meta + expression）。
# 2026-10-24t：pass_value -> boolean_id（指 boolean 表：1=真 0=假，pass_value 已刪）
EXPECTED_DDL = """
CREATE TABLE IF NOT EXISTS expected (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id  INTEGER NOT NULL
                REFERENCES boolean(id),  -- FK：boolean_id 一定要喺 boolean 表
    description TEXT,                    -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# operator 表：operator 字典（點比）
# 2026-10-23c：加返 expression（用戶要求）——
#   meta       = operator 名（== / >= / <= / != / > / <）
#   expression = 判斷表達式（answer 同 pass_value 嘅比較），由 _judge eval 執行
# 2026-10-24：calculation 改名 operator（用戶要求）
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

QUESTION_DDL = """
CREATE TABLE IF NOT EXISTS question (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id        INTEGER NOT NULL,   -- test.id（邊個測試維度）
    "5w2h_id"      INTEGER NOT NULL,   -- "5W2H".id（邊個提問框架，數字開頭要引號）
    operator_id    INTEGER,            -- operator.id（用邊個 operator 判斷）
    expected_id    INTEGER,            -- expected.id（用邊個期望值）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    -- 2026-10-24：UNIQUE 改支持多期望值（同一 test×5w2h 可以有 exp=3 / exp=6 兩條）
    UNIQUE (test_id, "5w2h_id", expected_id)
);
"""

# flow 表：驗證鏈
# 2026-10-24：question_flow 改名 flow
FLOW_DDL = """
CREATE TABLE IF NOT EXISTS flow (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name  TEXT    NOT NULL UNIQUE,   -- 驗證鏈名（5w2h / spec ...）
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# seq 表：序號字典（第幾步，由表控制）
# step.seq_id -> seq.id（1,2,3...10）
SEQ_DDL = """
CREATE TABLE IF NOT EXISTS seq (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seq         INTEGER NOT NULL UNIQUE,  -- 序號（1, 2, 3... 10）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# step 表：驗證鏈步驟
# 2026-10-24：question_step 改名 step；seq 欄位 -> seq_id（指去 seq 表）
# 2026-10-24b：欄位排序 + 加 updated_at（用戶要求）
STEP_DDL = """
CREATE TABLE IF NOT EXISTS step (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id        INTEGER NOT NULL,   -- flow.id（邊條驗證鏈）
    question_id    INTEGER NOT NULL,   -- question.id（問邊個問題）
    seq_id         INTEGER NOT NULL,   -- seq.id（第幾步：1, 2, 3...）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, seq_id)
);
"""

# shortcut 表：API 快捷路由（api_url -> flow_name，唔 hardcode）
# 2026-10-24：支援多 flow —— API 唔帶 flow_id，而係由 api_url match shortcut
# 2026-10-24b：shortcut 欄唔 UNIQUE（多個 api_url 可以指同一個 flow）
SHORTCUT_DDL = """
CREATE TABLE IF NOT EXISTS shortcut (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    api_url     TEXT    NOT NULL UNIQUE,  -- API 路徑（例如 /run/english-word /english）
    shortcut    TEXT    NOT NULL,         -- flow 名（例如 english word）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""
# question_flow_run.value_id -> value.id（邊個值）
VALUE_DDL = """
CREATE TABLE IF NOT EXISTS value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT,                      -- 提交去檢查嘅值（例如 "Anthropic spec"）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# run 表：執行記錄（submit xxx 去驗證）
# run.value_id -> value.id（邊個值）
# 2026-10-24：question_flow_run -> question_run -> run
RUN_DDL = """
CREATE TABLE IF NOT EXISTS run (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id    INTEGER NOT NULL,   -- flow.id（邊條驗證鏈）
    value_id   INTEGER,            -- value.id（提交去檢查嘅值）
    step_id    INTEGER,            -- step.id（停喺邊步）
    status_id  INTEGER,            -- status.id（1=approved 2=rejected 3=NA）
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# boolean 表：真/假字典（0=假 1=真，id = value）
# 2026-10-24t（用戶要求）：expected/answer/status 統一用 boolean_id
# 2026-10-24u：加 CHECK —— DB 層擋垃圾值（INTEGER 會自動 CAST，'2' 都會被擋）
BOOLEAN_DDL = """
CREATE TABLE IF NOT EXISTS boolean (
    id          INTEGER PRIMARY KEY,        -- 0 或 1（id = value）
    value       INTEGER NOT NULL UNIQUE
                CHECK (value IN (0, 1)),    -- 只准 0/1（DB 層硬擋）
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

STATUS_DDL = """
CREATE TABLE IF NOT EXISTS status (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id INTEGER NOT NULL
                REFERENCES boolean(id),   -- FK：boolean_id 一定要喺 boolean 表
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# answer 字典表：答案值（boolean_id 指 boolean 表：0=假 1=真）
# result.answer_id -> answer.id
ANSWER_DICT_DDL = """
CREATE TABLE IF NOT EXISTS answer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id  INTEGER NOT NULL
                REFERENCES boolean(id),   -- FK：boolean_id 一定要喺 boolean 表
    description TEXT,                     -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# result 表：每個問題嘅答案 + 狀態（證明）
# 2026-10-24：question_answer -> answer（改名，執行記錄）-> result
#   answer欄位  -> answer_id（指 answer 字典：1/0）
#   is_pass     -> status_id（指 status 表：approved/rejected/NA）
RESULT_DDL = """
CREATE TABLE IF NOT EXISTS result (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER NOT NULL,    -- run.id（邊次執行）
    question_id  INTEGER NOT NULL,    -- question.id（邊個問題）
    answer_id    INTEGER,             -- answer.id（1=真/有，0=假/冇）
    status_id    INTEGER,             -- status.id（1=approved 2=rejected 3=NA）
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (run_id, question_id)
);
"""

# taxonomy 表：module 大類 × flow 關聯
# tree_id = taxonomy tree.id（=2 module 大類，由 taxonomy 表控制）
# 每行 = 一條驗證鏈（flow）屬於邊個 module 大類
# 2026-10-24：taxonomy_question 改名 taxonomy
TAXONOMY_DDL = """
CREATE TABLE IF NOT EXISTS taxonomy (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id     INTEGER NOT NULL,   -- taxonomy tree.id（=2 module 大類）
    flow_id     INTEGER NOT NULL,   -- flow.id（邊條驗證鏈）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id, flow_id)
);
"""

# api_type 表：HTTP 方法字典（GET / POST ...）
API_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS api_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- GET / POST / PUT / DELETE
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# api 表：module 對外 REST API 註冊（module 之間點樣 work together）
# 2026-10-24（用戶要求）：question & source 點樣經 API 合作要有表管理。
# api_type_id -> api_type.id（GET / POST）
# flow_id     -> 呢條 API 屬於邊條 flow（question 自己嘅 flow）
# value_id    -> 呢條 API 消耗邊種 value（question.value 表）
# status_id   -> status.id（1=active ...）
API_DDL = """
CREATE TABLE IF NOT EXISTS api (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    api         TEXT    NOT NULL,           -- API 路徑（例如 /run /english）
    api_type_id INTEGER NOT NULL,           -- api_type.id（GET / POST）
    flow_id     INTEGER,                    -- flow.id（呢條 API 屬於邊條 flow）
    value_id    INTEGER,                    -- value.id（呢條 API 消耗邊種 value）
    description TEXT,                       -- 描述
    status_id   INTEGER,                    -- status.id（1=active 2=deprecated）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (api, api_type_id)
);
"""

# code_type 表：程式碼類型字典（question module 8 檔標準分類）
# 2026-10-24（用戶要求）：value = preflight / schema / mission / proof /
# verify / evidence / formula / filling / output / fallback / NA / identity / audit
CODE_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS code_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- preflight / schema / mission ...
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# code_registry 表：module 檔案註冊表（邊個檔案負責邊種 code type）
# 2026-10-24（用戶要求）：question module 每個檔案註冊喺度，
# 同 api 表一樣係「module 資產管理」。
# 2026-10-24b（用戶要求）：可擴展到所有單行（ast 掃描每個 def/class）
# 2026-10-24c（用戶要求）：condition 獨立成表，registry 用 condition_id 管理
# code_type_id  -> code_type.id（呢個檔案/函數屬於邊類）
# meta          -> 用途名（例如 sql / run_flow）
# filename      -> 實際檔名（question/sql.py -> sql.py）
# mapping_line  -> 對應行（真實行號，ast 攞）
# condition_id  -> code_condition.id（file / def / class / async def，由表控制）
CODE_CONDITION_DDL = """
CREATE TABLE IF NOT EXISTS code_condition (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- file / def / class / async def / main
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

CODE_REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS code_registry (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code_type_id INTEGER NOT NULL,           -- code_type.id（邊類）
    condition_id INTEGER NOT NULL,           -- code_condition.id（file/def/class）
    meta         TEXT    NOT NULL,           -- 用途名（sql / run_flow...）
    description  TEXT,                       -- 描述
    filename     TEXT    NOT NULL,           -- 檔名（sql.py）
    mapping_line INTEGER,                    -- 對應行（真實行號）
    is_active    BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (meta, filename, mapping_line)
);
"""

# code_flow 表：程式碼流程（同 question flow 一樣 —— 檔案 = 一條 flow）
# 2026-10-24e（用戶要求）：有 code_flow + code_step，
# 定義更清晰 —— code_registry 係「邊行係咩」，
# code_flow/code_step 係「執行順序」。
# flow_name = 檔案名（sql.py 一條 flow = 初始化到執行）
CODE_FLOW_DDL = """
CREATE TABLE IF NOT EXISTS code_flow (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name   TEXT    NOT NULL UNIQUE,   -- 檔案名（sql.py / api_server.py ...）
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# code_step 表：程式碼流程步驟（同 question step 一樣 —— 每步 = 一個函數）
# 2026-10-24e（用戶要求）：code_flow 嘅每一步。
# code_flow_id -> code_flow.id（邊條 flow）
# code_registry_id -> code_registry.id（執行邊個函數行）
# seq_id       -> seq.id（第幾步）
CODE_STEP_DDL = """
CREATE TABLE IF NOT EXISTS code_step (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    code_flow_id     INTEGER NOT NULL,      -- code_flow.id（邊條 flow）
    code_registry_id INTEGER NOT NULL,      -- code_registry.id（執行邊個函數）
    seq_id           INTEGER NOT NULL,      -- seq.id（第幾步）
    is_active        BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (code_flow_id, seq_id)
);
"""

# value_defne 表：字典表（id | value）—— 任何「值」註冊喺度
# 2026-10-24f（用戶要求）：唔好 array 喺 code —— 全部用 xx_id 指住呢度。
# value = 實際值（xxx）；冇重複（UNIQUE）。
VALUE_DEFNE_DDL = """
CREATE TABLE IF NOT EXISTS value_defne (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 實際值（xxx）
    description TEXT,                       -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# unique_defne 表：唯一約束定義 —— value = value_id=value_id（配對）
# 2026-10-24f（用戶要求）：唔好 array 喺 code —— 表控制配對。
# 例如：code_type_id=condition_id 嘅唯一組合，用兩條 value_id 記錄。
# value 例：'3=2'（code_type 3 + condition 2 係唯一 pair）
UNIQUE_DEFNE_DDL = """
CREATE TABLE IF NOT EXISTS unique_defne (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    value           TEXT    NOT NULL UNIQUE,  -- 'value_id=value_id'（配對字串）
    left_value_id   INTEGER NOT NULL,         -- value_defne.id（左邊）
    right_value_id  INTEGER NOT NULL,         -- value_defne.id（右邊）
    description     TEXT,                     -- 描述
    is_active       BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (left_value_id, right_value_id)
);
"""

# question_text 表：問題文字（test_id × w5w2h_id -> 人話問題）
# 2026-10-24h（用戶要求）：code 升級 —— TEST_QUESTION_TEXT /
# W5W2H_QUESTION_TEXT 硬寫 dict 搬入 DB（表控制）。
# test_id   -> test.id（text 維度）
# w5w2h_id  -> "5W2H".id（提問框架）
# text      -> 完整問題文字
QUESTION_TEXT_DDL = """
CREATE TABLE IF NOT EXISTS question_text (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id     INTEGER NOT NULL,           -- test.id（symbol / english / INT...）
    w5w2h_id    INTEGER NOT NULL,           -- "5W2H".id（what / where...）
    text        TEXT    NOT NULL,           -- 問題文字
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (test_id, w5w2h_id)
);
"""

# w5w2h_text 表：提問框架問法（what -> 係咩？）
# 2026-10-24h（用戶要求）：W5W2H_QUESTION_TEXT 都搬入 DB
W5W2H_TEXT_DDL = """
CREATE TABLE IF NOT EXISTS w5w2h_text (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    w5w2h_id    INTEGER NOT NULL,           -- "5W2H".id（what / where...）
    text        TEXT    NOT NULL,           -- 問法（係咩？）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (w5w2h_id)
);
"""
__all__ = ['TEST_DDL', 'W5H2_DDL', 'EXPECTED_DDL', 'OPERATOR_DDL', 'VALUE_DDL', 'QUESTION_DDL', 'FLOW_DDL', 'SEQ_DDL', 'STEP_DDL', 'RUN_DDL', 'BOOLEAN_DDL', 'STATUS_DDL', 'ANSWER_DICT_DDL', 'RESULT_DDL', 'TAXONOMY_DDL', 'SHORTCUT_DDL', 'API_TYPE_DDL', 'API_DDL', 'CODE_TYPE_DDL', 'CODE_CONDITION_DDL', 'CODE_REGISTRY_DDL', 'CODE_FLOW_DDL', 'CODE_STEP_DDL', 'VALUE_DEFNE_DDL', 'UNIQUE_DEFNE_DDL', 'QUESTION_TEXT_DDL', 'W5W2H_TEXT_DDL']
