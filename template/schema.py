"""schema.py — template 權威 DDL 入口（唯一 schema 來源）

2026-10-26（用戶要求）：template 完全獨立 module，唔再 clone question。
自己 define 12 張表（字典表 + runtime 表分開）：

    字典表（有 seed 資料）：
        value          提交值
        "5W2H"         提問框架（what/where/when/who/why/how/how much）
        answer         答案字典（boolean_id 指 boolean）
        operator       運算子字典（meta + expression；2026-10-27 rename from calculation）
        expected       期望值字典（boolean_id 指 boolean）
        condition      條件維度字典（symbol/english/INT...；2026-10-27 rename from test）
        seq            序號字典（1-300）
        status         狀態字典（boolean_id 指 boolean）
        boolean        真/假字典（0/1）

    runtime 表（冇資料，等新 module 用）：
        flow           驗證鏈
        step           驗證鏈步驟
        question       問題（condition × 5W2H 組合）
        run            執行記錄

（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

VALUE_DDL = """
CREATE TABLE IF NOT EXISTS value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

W5H2_DDL = """
CREATE TABLE IF NOT EXISTS "5W2H" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

ANSWER_DDL = """
CREATE TABLE IF NOT EXISTS answer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id  INTEGER NOT NULL
                REFERENCES boolean(id),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

OPERATOR_DDL = """
CREATE TABLE IF NOT EXISTS operator (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- operator 名（== / >= / <= ...）
    expression  TEXT,                      -- 判斷表達式
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 2026-10-27（用戶要求）：calculation 表 rename -> operator。
# 舊表由 migration 搬資料後 drop（_migrate_names）。
CALCULATION_DDL = """
CREATE TABLE IF NOT EXISTS calculation (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,
    expression  TEXT,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

EXPECTED_DDL = """
CREATE TABLE IF NOT EXISTS expected (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id  INTEGER NOT NULL
                REFERENCES boolean(id),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

CONDITION_DDL = """
CREATE TABLE IF NOT EXISTS condition (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 2026-10-27（用戶要求）：test 表 rename -> condition。
# 舊表由 migration 搬資料後 drop（_migrate_names）。
TEST_DDL = """
CREATE TABLE IF NOT EXISTS test (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
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

STATUS_DDL = """
CREATE TABLE IF NOT EXISTS status (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    boolean_id INTEGER NOT NULL
                REFERENCES boolean(id),
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

BOOLEAN_DDL = """
CREATE TABLE IF NOT EXISTS boolean (
    id          INTEGER PRIMARY KEY,
    value       INTEGER NOT NULL UNIQUE
                CHECK (value IN (0, 1)),
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
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
    flow_id        INTEGER NOT NULL,   -- flow.id
    question_id    INTEGER NOT NULL,   -- question.id
    seq_id         INTEGER NOT NULL,   -- seq.id（第幾步）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, seq_id)
);
"""

QUESTION_DDL = """
CREATE TABLE IF NOT EXISTS question (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id   INTEGER NOT NULL,   -- condition.id（2026-10-27 rename from test_id）
    "5w2h_id"      INTEGER NOT NULL,   -- "5W2H".id
    operator_id    INTEGER,            -- operator.id（用邊個 operator）
    expected_id    INTEGER,            -- expected.id
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (condition_id, "5w2h_id", expected_id)
);
"""

RUN_DDL = """
CREATE TABLE IF NOT EXISTS run (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id    INTEGER NOT NULL,   -- flow.id
    value_id   INTEGER,            -- value.id
    step_id    INTEGER,            -- step.id
    status_id  INTEGER,            -- status.id
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 12 張 keep 表（2026-10-26 用戶指定；2026-10-27 test->condition calculation->operator）
TEMPLATE_DDL = (VALUE_DDL + W5H2_DDL + ANSWER_DDL + OPERATOR_DDL
                + CALCULATION_DDL + EXPECTED_DDL + CONDITION_DDL
                + TEST_DDL + SEQ_DDL + STATUS_DDL
                + BOOLEAN_DDL + FLOW_DDL + STEP_DDL + QUESTION_DDL
                + RUN_DDL)

# ============ Proof 系統（2026-10-27 用戶設計） ============
# formula：一條完整證明公式（full = 完整字串；package_id/file_id/line = 出處地址）
FORMULA_DDL = """
CREATE TABLE IF NOT EXISTS formula (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full        TEXT    NOT NULL,   -- 完整公式（xxx=<select * from ...>）
    package_id  INTEGER,            -- taxonomy.taxonomy.id（出處 package）
    file_id     INTEGER,            -- structure_module.id（出處 file 層）
    line        INTEGER,            -- 出處行號
    db_file     TEXT,               -- 執行 DB（template.db / structure.db / None = structure）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# formula_cuter：公式切粒（seq_id = 次序，value = 一粒）
# 2026-10-27：position_id -> seq_id（用戶統一命名）
# 2026-10-27：python_ast_id + source_id（每粒 symbol 可證明 = programming.python_ast 節點，
#            source = programming_language.source_id / python.org）
FORMULA_CUTER_DDL = """
CREATE TABLE IF NOT EXISTS formula_cuter (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    formula_id   INTEGER NOT NULL,   -- formula.id
    seq_id       INTEGER NOT NULL,   -- 次序（1 開始）
    value        TEXT    NOT NULL,   -- token（select / * / from / SPACE ...）
    python_ast_id INTEGER,            -- programming.python_ast.id（呢粒 token 對應邊個 AST 節點）
    source_id    INTEGER,            -- source.db source.id（官方來源，python.org）
    UNIQUE (formula_id, seq_id)
);
"""

# proof：一條公式用邊種語言（language_id 指向 dictionary）
PROOF_DDL = """
CREATE TABLE IF NOT EXISTS proof (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id  INTEGER NOT NULL,   -- language.id（SQL / Python ...）
    formula_id   INTEGER NOT NULL,   -- formula.id
    is_active    BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (language_id, formula_id)
);
"""

# preflight_table：一條 formula 驗證邊張真表（structure_db_table.id）
PREFLIGHT_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS preflight_table (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    formula_id            INTEGER NOT NULL,  -- formula.id
    structure_db_table_id INTEGER NOT NULL,  -- structure.db structure_db_table.id
    is_active             BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at            TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (formula_id, structure_db_table_id)
);
"""

# preflight_condition：一條 formula 嘅條件（package_id = "module_id" 等）
# operator_id = operator.id（== / >= ...；2026-10-27 rename from calculation）
PREFLIGHT_CONDITION_DDL = """
CREATE TABLE IF NOT EXISTS preflight_condition (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    formula_id             INTEGER NOT NULL,  -- formula.id
    structure_db_field_id  INTEGER NOT NULL,  -- structure.db structure_db_field.id
    operator_id            INTEGER,           -- calculation.id
    preflight_id           INTEGER,           -- preflight 值（id）
    is_active              BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (formula_id, structure_db_field_id, preflight_id)
);
"""

PROOF_DDL_ALL = (FORMULA_DDL + FORMULA_CUTER_DDL + PROOF_DDL
                 + PREFLIGHT_TABLE_DDL + PREFLIGHT_CONDITION_DDL)

# ============ decorator 表：公式裝飾器定義（2026-10-27 用戶要求 table-driven） ============
# decorator = 公式嘅「出生證明」模板——內容全部由表定義（零 code 寫死）：
#   name              = 裝飾器名（@formula_def 掛喺 function 上面）
#   formula_full      = 完整公式（xxx=<select * from ...>；可有 <table> 等 placeholder）
#   language_id       = language.id（SQL=1）
#   table_meta        = 真表名（seq / condition / structure_db_field ...）
#   field_meta        = 欄位名（id / package_id ...）
#   operator_meta     = operator.meta（== / >= ...；冇 = 唔寫條件）
#   preflight_value   = 條件值（"module_id" 等；冇 = 淨驗證表存在）
#   db_file           = 執行 DB（template.db / structure.db / None = structure）
#   cuter_split       = 1 要切粒入 formula_cuter / 0 唔切
# ast 掃碼時見到 @formula_def(name) → 查呢張表 → 建立 formula +
# proof + preflight_table + preflight_condition + formula_cuter，
# 再回填 formula.package_id / file_id / line（出處身份，由 ast 真實攞）。
DECORATOR_DDL = """
CREATE TABLE IF NOT EXISTS decorator (
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
"""

DEFAULT_DECORATORS = [
    # 字典表證明（template.db 自證：seq / condition / operator / flow）
    ("prove_seq_by_id",
     "xxx=<select * from \"seq\" where \"id\" = \"1\">",
     1, "seq", "id", "==", None, "template.db", 1),
    ("prove_condition_by_id",
     "xxx=<select * from \"condition\" where \"id\" = \"1\">",
     1, "condition", "id", "==", None, "template.db", 1),
    ("prove_operator_by_id",
     "xxx=<select * from \"operator\" where \"id\" = \"1\">",
     1, "operator", "id", "==", None, "template.db", 1),
    ("prove_flow_by_id",
     "xxx=<select * from \"flow\" where \"id\" = \"1\">",
     1, "flow", "id", "==", None, "template.db", 1),
    # 真表證明（structure.db 層）
    ("prove_structure_field_exists",
     "xxx=<select * from structure_db_field where package_id =\"module_id\""
     " and file_id =\"file_id\">",
     1, "structure_db_field", "package_id", "==", "module_id",
     "structure.db", 1),
]

# ============ Evidence（2026-10-27 用戶要求：formula 生成證據） ============
# evidence 表：一條 formula 執行嘅證據記錄（SSOT vs 真正 coding 比較）
#   formula_id    = formula.id（邊條公式）
#   table_name    = 被證明嘅表（position / db_field_check / seq ...）
#   field_name    = 被證明嘅欄位（meta / value / json ...）
#   value         = 比較值（SSOT 嘅真值）
#   expected      = 期望值（formula 預期）
#   actual        = 實際值（執行 formula 攞到）
#   is_match      = expected == actual（證明結果）
#   evidence      = raw 結果（raw SQL row）
#   run_at        = 執行時間
EVIDENCE_DDL = """
CREATE TABLE IF NOT EXISTS evidence (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    formula_id   INTEGER NOT NULL,   -- formula.id（0 = flow 執行證據，非 formula）
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
"""

EVIDENCE_DDL_ALL = EVIDENCE_DDL

# formula_comment 表：formula 嘅註解（2026-10-28 用戶設計）
# 目的：code 入面嘅 comment 唔再留喺 file（減少 hardcode/噪音），
#       搬入表 —— formula_comment 記錄「呢條 formula 想做咩」。
#   formula_id = template.formula.id
#   comment    = 註解文字（由 AST 掃描時抽出嘅 docstring / # comment）
FORMULA_COMMENT_DDL = """
CREATE TABLE IF NOT EXISTS formula_comment (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    formula_id  INTEGER NOT NULL,          -- formula.id
    comment     TEXT    NOT NULL,          -- 註解文字
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (formula_id, comment)
);
"""

__all__ = ["VALUE_DDL", "W5H2_DDL", "ANSWER_DDL", "OPERATOR_DDL",
           "CALCULATION_DDL", "EXPECTED_DDL", "CONDITION_DDL",
           "TEST_DDL", "SEQ_DDL", "STATUS_DDL",
           "BOOLEAN_DDL", "FLOW_DDL", "STEP_DDL", "QUESTION_DDL",
           "RUN_DDL", "TEMPLATE_DDL",
           "FORMULA_DDL", "FORMULA_CUTER_DDL", "PROOF_DDL",
           "PREFLIGHT_TABLE_DDL", "PREFLIGHT_CONDITION_DDL",
           "PROOF_DDL_ALL", "DECORATOR_DDL", "DEFAULT_DECORATORS",
           "EVIDENCE_DDL", "EVIDENCE_DDL_ALL",
           "FORMULA_COMMENT_DDL"]