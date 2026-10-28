"""schema.py — ast 權威 DDL 入口

ast.db 存放 AST 分析結果（2026-10-26 用戶要求）：
    function        函數字典（function | class_id | programming_language_id）
    function_class  函數類別字典（class 名，幫 function 有 value）
    analyze_root    root 層分析（structure_root_id | function_id | db_field_check_id）
    analyze_module  module 層分析（structure_module_id | function_id | db_field_check_id）
    analyze_skill   skill 層分析（structure_skill_id | function_id | db_field_check_id）

分析鏈：AST 掃描每個 module 嘅 .py 檔 -> 抽出 function -> 寫入 function 字典
+ 對應層嘅 analyze 表（root / module / skill）。
db_field_check_id = structure.db db_field_check.id（規格檢查，可選）。
"""

# function 表：函數字典
#    function = 函數名（例如 build_column_definitions）
#    class_id = function_class.id（函數屬於邊個 class，可選）
#    programming_language_id = programming.db programming_language.id（python=1）
FUNCTION_DDL = """
CREATE TABLE IF NOT EXISTS function (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    function                  TEXT    NOT NULL UNIQUE,  -- 函數名
    class_id                  INTEGER,                  -- function_class.id（可選）
    programming_language_id   INTEGER NOT NULL,         -- programming_language.id（python=1）
    is_active                 BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at                TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at                TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# function_class 表：函數類別字典（幫 function 有 value）
#    meta = class 名（例如 SqlStore / Terminology / Definition）
FUNCTION_CLASS_DDL = """
CREATE TABLE IF NOT EXISTS function_class (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- class 名
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# analyze_root 表：root 層分析
#    structure_root_id = structure.db structure_root.id
#    function_id       = function.id（AST 抽出嘅函數）
#    db_field_check_id = structure.db db_field_check.id（規格檢查，可選）
ANALYZE_ROOT_DDL = """
CREATE TABLE IF NOT EXISTS analyze_root (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_root_id   INTEGER NOT NULL,   -- structure_root.id
    function_id         INTEGER NOT NULL,   -- function.id
    db_field_check_id   INTEGER,            -- db_field_check.id（可選）
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_root_id, function_id)
);
"""

# analyze_module 表：module 層分析
#    structure_module_id = structure.db structure_module.id
#    function_id         = function.id（AST 抽出嘅函數）
#    db_field_check_id   = structure.db db_field_check.id（規格檢查，可選）
ANALYZE_MODULE_DDL = """
CREATE TABLE IF NOT EXISTS analyze_module (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_module_id INTEGER NOT NULL,   -- structure_module.id
    function_id         INTEGER NOT NULL,   -- function.id
    db_field_check_id   INTEGER,            -- db_field_check.id（可選）
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_module_id, function_id)
);
"""

# analyze_skill 表：skill 層分析
#    structure_skill_id = structure.db structure_skill.id
#    function_id        = function.id（AST 抽出嘅函數）
#    db_field_check_id  = structure.db db_field_check.id（規格檢查，可選）
ANALYZE_SKILL_DDL = """
CREATE TABLE IF NOT EXISTS analyze_skill (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_skill_id  INTEGER NOT NULL,   -- structure_skill.id
    function_id         INTEGER NOT NULL,   -- function.id
    db_field_check_id   INTEGER,            -- db_field_check.id（可選）
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_skill_id, function_id)
);
"""

# decorator 表：Python decorator 字典（2026-10-28 用戶：由 programming 搬嚟 ast）
# ast = AST 分析中心 —— decorator 係語言語法單元，同 function / function_class
# 一齊歸 ast module。
# 每表只 1 meta（用戶規則）：meta = decorator 名（formula_def / property / app.route ...）
DECORATOR_DDL = """
CREATE TABLE IF NOT EXISTS decorator (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- decorator 名（formula_def / property ...）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 官方 decorator + 全站實際用過嘅 decorator 種子（2026-10-28 upgrade：加漏咗嘅）
# 2026-10-28（用戶要求）：meta 統一 snake_case 全詞（classmethod -> class_method）
DEFAULT_DECORATORS = [
    ("property", "內建：唯讀屬性（docs.python.org library/functions）"),
    ("class_method", "內建：類別方法（class 自身作第一參數）"),
    ("static_method", "內建：靜態方法（冇 self/cls）"),
    ("abstract_method", "abc：抽象方法（子類必須實作）"),
    ("formula_definition", "template/decorators.py：公式定義掛鉤（table-driven）"),
    ("data_class", "dataclasses：自動生成 __init__ 等"),
    ("function_tools.wraps", "functools：保留被裝飾函數 metadata"),
    ("context_manager", "contextlib：用 generator 寫 context manager"),
    ("app.route", "Flask：URL 路由"),
    ("python_test.fixture", "pytest：測試 fixture"),
    ("lru_cache", "functools：函式結果快取"),
    ("cached_property", "functools：一次性計算屬性"),
    # 2026-10-28 upgrade：加漏咗嘅（全站掃描見到常用）
    ("single_dispatch", "functools：單派發泛型函數"),
    ("total_ordering", "functools：填補比較運算子"),
    ("final", "typing：禁止覆寫"),
    ("override", "typing：標記覆寫（Python 3.12+）"),
    ("atexit.register", "atexit：程序退出時執行"),
    ("async_context_manager", "contextlib：async context manager"),
    ("suppress", "contextlib：靜默特定異常"),
    ("partial", "functools：局部套用函數"),
    ("wraps", "functools：保留 metadata（簡寫）"),
    ("deprecated", "warnings：棄用標記"),
    ("class_property", "classmethod 變體：類別屬性"),
    ("lru_cache.maxsize", "functools.lru_cache：指定容量"),
]


__all__ = ["FUNCTION_DDL", "FUNCTION_CLASS_DDL",
           "ANALYZE_ROOT_DDL", "ANALYZE_MODULE_DDL",
           "ANALYZE_SKILL_DDL",
           "DECORATOR_DDL", "DEFAULT_DECORATORS"]
