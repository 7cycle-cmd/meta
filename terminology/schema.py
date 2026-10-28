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

# 2026-10-28（用戶確認）：terminology 唔再擁有 value 表 ——
# value 由 value module 擁有（value.db SSOT），terminology ATTACH 做 vdb。
# 舊遺留 VALUE_DDL 已移除（啟動時 drop 舊表，唔再建）。

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
    role_id    INTEGER,                 -- role.db registry.id（邊個角色執行，2026-10-27）
    rule_id    INTEGER,                 -- rule.db rule.id（跟邊條規則，2026-10-27e）
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

FLOW_DDL = """
CREATE TABLE IF NOT EXISTS flow (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name   TEXT    NOT NULL UNIQUE,
    total_step  INTEGER NOT NULL DEFAULT 0,  -- 步數總計（2026-10-28 用戶要求）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

STEP_DDL = """
CREATE TABLE IF NOT EXISTS step (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id        INTEGER NOT NULL,
    question_id    INTEGER NOT NULL,       -- 永遠唔可以空（用戶 2026-10-25：never）
    seq_id         INTEGER NOT NULL,
    action         TEXT,                   -- 動作名（1 line = 1 action；表話事，2026-10-28）
    input_desc     TEXT,                   -- 輸入（食咩）
    output_desc    TEXT,                   -- 輸出（出咩）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, seq_id)
);
"""

# flow_branch 表：每次 run 對每個 condition 嘅實際判斷結果（2026-10-25 用戶要求）
# runtime 自動寫入（發生過咩 -> 記錄）。唔係規則！
# step_input 表：condition × 5W2H 7 維度輸入測量（2026-10-28 用戶設計）
# 目的：量度「呢個 condition 喺 7 個 5W2H 維度入面嘅 input 係咪齊」
#   source_table / source_column -> 呢個維度嘅 id 由邊張表邊個欄攞
#   （DB driven：全部可以 by id -> how much = *_id）
# 完整度測量：每 condition 應有 7 行（5W2H 全維度）；
#   step_input 有但 flow 冇用 = wrong define；flow 用到但冇 = missing。
STEP_INPUT_DDL = """
CREATE TABLE IF NOT EXISTS step_input (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id  INTEGER NOT NULL,          -- terminology.condition.id
    "5w2h_id"     INTEGER NOT NULL,          -- "5W2H".id（1-7）
    source_table  TEXT,                      -- e.g. 'value' / 'permit' / 'identity'
    source_column TEXT,                      -- e.g. 'id' / 'permit_type'
    is_active     BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (condition_id, "5w2h_id")
);
"""

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
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id        INTEGER NOT NULL,       -- condition.id（判斷條件）
    "5w2h_id"           INTEGER NOT NULL,
    operator_id         INTEGER,
    expected_id         INTEGER,
    expected_source_id  INTEGER,                -- expected_source.id（期望值來源，2026-10-28）
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (condition_id, "5w2h_id", operator_id, expected_id)
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

# ============ step_output / expected_source（2026-10-28 用戶設計）============
# step_input = 輸入測量（condition × 5W2H 7 維度）
# step_output = 輸出測量：每步實際輸出（expert_id 判斷 + value 1,0）
#
# expected_source：期望值來源（Table-driven，blackbox code = formula）
#   question_id   = terminology.question.id
#   formula_id    = template.formula.id（執行 blackbox 公式 -> 得到期望 value）
#   formula       = formula 內容 snapshot（直接睇到係咩，2026-10-28 用戶要求）
#   value         = 期望值（formula 執行結果 / 直接值）
#   value_id      = value.db value.id（proof at db，2026-10-28）
#   output_format = 輸出格式（預設 '1,0'：boolean 化）
# 鏈：value -> condition_id * 5W2H * operator(yes>==, no>!=)
#           -> expected_source -> output_format = 1,0
# 2026-10-28（用戶）：移除 formula_cutter_id（公式切粒定位已冇用）
EXPECTED_SOURCE_DDL = """
CREATE TABLE IF NOT EXISTS expected_source (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id       INTEGER NOT NULL,      -- terminology.question.id
    formula_id        INTEGER,               -- template.formula.id（blackbox 來源）
    formula           TEXT,                   -- formula 內容 snapshot（直接睇）
    value             TEXT,                   -- 期望值（formula 執行結果 / 直接值）
    value_id          INTEGER,               -- value.db value.id（proof at db，2026-10-28）
    output_format     TEXT NOT NULL DEFAULT '1,0',  -- 輸出格式（1,0 boolean）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (question_id, formula_id)
);
"""

# step_output：每步實際輸出記錄
#   step_id     = terminology.step.id
#   run_id      = terminology.run.id（邊次執行）
#   question_id = question.id
#   expert_id   = 邊個判斷（identity / skill 可選）
#   expected_id = expected.id（期望 1/0，由 expected_source 推）
#   value       = 實際輸出 1,0（output_format 化）
STEP_OUTPUT_DDL = """
CREATE TABLE IF NOT EXISTS step_output (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    step_id       INTEGER NOT NULL,          -- terminology.step.id
    run_id        INTEGER NOT NULL,          -- terminology.run.id
    question_id   INTEGER NOT NULL,          -- question.id
    expert_id     INTEGER,                   -- 邊個判斷（identity / skill.id）
    expected_id   INTEGER,                   -- expected.id（期望 1/0）
    value         INTEGER NOT NULL CHECK (value IN (0,1)),  -- 實際輸出 1,0
    output_value  TEXT,                      -- 實際輸出 snapshot（累計數等，2026-10-28）
    output_format TEXT    NOT NULL DEFAULT '1,0',
    is_active     BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (run_id, step_id, question_id)
);
"""

# ============ output_by / output_type（2026-10-28 用戶設計）============
# 目的：分辨「設計係 by code 定 by table」—— 每個輸出（step_output）
#       都要知道個 value 來源係 code（blackbox）定 db_table（data-driven）。
#   output_by      = 邊個 output 由邊種方式產生
#   output_type    = 來源方式字典
# 已知：db_field_check / db_field_option（structure.db）已標明
#       「id 係邊張 db_table 邊個 db_field 出嚟」。
# 未經呢條路（直接寫死值）= hardcode -> hardcode_value 表記錄。

OUTPUT_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS output_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- code / db_table
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 預設 seed（冪等）：code = 由程式邏輯產生（blackbox）；
#                     db_table = 由真表/真欄位查詢產生（data-driven）
DEFAULT_OUTPUT_TYPES = ["code", "db_table"]

OUTPUT_BY_DDL = """
CREATE TABLE IF NOT EXISTS output_by (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    output_id      INTEGER NOT NULL,          -- step_output.id（邊個輸出）
    output_type_id INTEGER NOT NULL,          -- output_type.id（code / db_table）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (output_id, output_type_id)
);
"""

# hardcode_value：標記「無 db_table/db_field 出處」嘅硬編碼值（2026-10-28）
#   value_id     = value.db value.id（個值）
#   package_id   = taxonomy.registry.id（邊個 package 寫死）
#   file_id      = structure.module.id（邊個實體檔案，optional）
#   taxonomy_id  = taxonomy.registry.id（分類）
#   skill_id     = skill.registry.id（邊個 skill）
# 用途：
#   - 代碼掃描（ast）見到「直接寫嘅字面值」而 db_field_check / db_field_option
#     又冇記錄 -> 登記做 hardcode
#   - monitor 可以查「全站有幾多 hardcode / 邊度」-> 慢慢收斂做 table-driven
HARDCODE_VALUE_DDL = """
CREATE TABLE IF NOT EXISTS hardcode_value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id    INTEGER NOT NULL,          -- value.db value.id（個值）
    package_id  INTEGER,                   -- taxonomy.registry.id（package）
    file_id     INTEGER,                   -- structure.module.id（檔案）
    taxonomy_id INTEGER,                   -- taxonomy.registry.id（分類）
    skill_id    INTEGER,                   -- skill.registry.id（skill）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (value_id, package_id, file_id, taxonomy_id, skill_id)
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

# source_register 表：詞 → source 登記選擇（2026-10-27 用戶要求）
#   一行 = 一個詞用邊個 source 證明（由表話事，零 hardcode）
#   id            = 登記行 id
#   word          = 詞（細楷）
#   source_id     = source.db source.id（證明來源）
#   registered_by = 邊個 caller 登記（terminology.source_register / api）
#   run_id        = source flow run.id（批准嗰次驗證）
SOURCE_REGISTER_DDL = """
CREATE TABLE IF NOT EXISTS source_register (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    word          TEXT    NOT NULL UNIQUE,  -- 詞（細楷）
    source_id     INTEGER NOT NULL,          -- source.db source.id
    registered_by TEXT,                       -- 邊個 caller 登記
    run_id        INTEGER,                    -- source run.id（可選）
    is_active     BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# question_template：提問模板（2026-10-28 用戶要求）
# 每行 = 一條可重用嘅提問定義：
#   value_id            = 提交值（value.db id；0 = 模板未綁值）
#   condition_id        = 判斷條件（condition.id）
#   operator_id         = 比對方式（operator.id，== / != ...）
#   expected_source_id  = 期望值來源（expected_source.id，攞期望 / measure unit）
QUESTION_TEMPLATE_DDL = """
CREATE TABLE IF NOT EXISTS question_template (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id            INTEGER NOT NULL DEFAULT 0,  -- 提交值（value.db id）
    condition_id        INTEGER NOT NULL,            -- condition.id
    operator_id         INTEGER NOT NULL,            -- operator.id
    expected_source_id  INTEGER,                     -- expected_source.id
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (value_id, condition_id, operator_id, expected_source_id)
);
"""

__all__ = ["INDUSTRY_DDL", "EVIDENCE_DDL",
           "CONDITION_DDL", "W5H2_DDL", "RUN_DDL", "FLOW_DDL", "STEP_DDL",
           "STEP_INPUT_DDL",
           "EXPECTED_SOURCE_DDL", "STEP_OUTPUT_DDL",
           "OUTPUT_TYPE_DDL", "OUTPUT_BY_DDL", "HARDCODE_VALUE_DDL",
           "FLOW_BRANCH_DDL", "NEXT_FLOW_DDL",
           "EXPECTED_DDL", "OPERATOR_DDL", "ANSWER_DDL", "BOOLEAN_DDL",
           "QUESTION_DDL", "SEQ_DDL", "STATUS_DDL", "REGISTRY_DDL",
           "WORD_CATEGORY_DDL", "SOURCE_REGISTER_DDL",
           "QUESTION_TEMPLATE_DDL"]
