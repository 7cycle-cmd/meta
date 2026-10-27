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

__all__ = ["FUNCTION_DDL", "FUNCTION_CLASS_DDL",
           "ANALYZE_ROOT_DDL", "ANALYZE_MODULE_DDL",
           "ANALYZE_SKILL_DDL"]
