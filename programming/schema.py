"""schema.py — programming 權威 DDL 入口（唯一 schema 來源）

programming.db 存放程式語言/格式/組合規則（2026-10-24s 由 terminology 拆出）：
    語言：  programming_language / language_alias
    格式：  data_format
    組合：  owner / owner_letter / owner_symbol / owner_INT / start_char

（8 檔標準：__init__/function/api/route/schema/sql/registry/rest_api）
"""

PROGRAMMING_LANGUAGE_DDL = """
CREATE TABLE IF NOT EXISTS programming_language (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    meta         TEXT    NOT NULL UNIQUE,
    description  TEXT,
    source_id    INTEGER,
    char_format  TEXT,
    is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

LANGUAGE_ALIAS_DDL = """
CREATE TABLE IF NOT EXISTS language_alias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id INTEGER NOT NULL,   -- programming_language.id（正名語言）
    alias       TEXT    NOT NULL,   -- 別名（py / js / java / c ...）
    description TEXT,
    source_id   INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (language_id, alias)
);
"""

DATA_FORMAT_DDL = """
CREATE TABLE IF NOT EXISTS data_format (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,
    description TEXT,
    source_id   INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

OWNER_DDL = """
CREATE TABLE IF NOT EXISTS owner (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id INTEGER NOT NULL,   -- programming_language.id（邊種語言）
    format_id   INTEGER NOT NULL,   -- data_format.id（邊種數據格式）
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (language_id, format_id)
);
"""

OWNER_LETTER_DDL = """
CREATE TABLE IF NOT EXISTS owner_letter (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    INTEGER NOT NULL,   -- owner.id（邊個語言×格式組合）
    letter_id   INTEGER NOT NULL,   -- character.db letter.id（接受邊個字母）
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (owner_id, letter_id)
);
"""

OWNER_SYMBOL_DDL = """
CREATE TABLE IF NOT EXISTS owner_symbol (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    INTEGER NOT NULL,   -- owner.id（邊個語言×格式組合）
    symbol_id   INTEGER NOT NULL,   -- character.db symbol.id（接受邊個符號）
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (owner_id, symbol_id)
);
"""

OWNER_INT_DDL = """
CREATE TABLE IF NOT EXISTS owner_INT (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    INTEGER NOT NULL,   -- owner.id（邊個語言×格式組合）
    int_id      INTEGER NOT NULL,   -- character.db "INT".id（接受邊個數字 0-9）
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (owner_id, int_id)
);
"""

START_CHAR_DDL = """
CREATE TABLE IF NOT EXISTS start_char (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL,   -- 開頭字符約束（例如 0-9 = 唔畀數字開頭）
    owner_id    INTEGER NOT NULL,   -- owner.id（呢個組合唔畀呢個開頭）
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (owner_id, value)
);
"""

# ============ 行級映射（2026-10-26 用戶要求）============
# 每一行 = 一個實體語句 / 一欄檢查 / 一個能力 / 一個函數嘅 AST 行號位置。
# line_ids = JSON 陣列，每段 "line:1 to 3"（by_id 零 hardcode）。

# line_ast 表：每個語句一行（AST 行號）
LINE_AST_DDL = """
CREATE TABLE IF NOT EXISTS line_ast (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id   INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    language_id INTEGER NOT NULL,   -- programming_language.id（語言）
    ast         TEXT    NOT NULL,   -- AST 節點（語句名 / 結構）
    package_id  INTEGER,            -- package.id（屬邊個 package）
    file_id     INTEGER,            -- file.id（屬邊個檔案）
    line_number INTEGER NOT NULL,   -- 行號
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, language_id, file_id, line_number)
);
"""

# line_field 表：每個欄位檢查一行
LINE_FIELD_DDL = """
CREATE TABLE IF NOT EXISTS line_field (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id          INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    language_id        INTEGER NOT NULL,   -- programming_language.id（語言）
    db_field_check_id  INTEGER,            -- structure.db db_field_check.id（檢查）
    package_id         INTEGER,            -- package.id（屬邊個 package）
    file_id            INTEGER,            -- file.id（屬邊個檔案）
    line_number        INTEGER NOT NULL,   -- 行號
    is_active          INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, language_id, file_id, line_number)
);
"""

# 技能映射統一由 skill_mapping（module_id + skill_id）表達。

# function_mapping 表：function -> 行號集合
FUNCTION_MAPPING_DDL = """
CREATE TABLE IF NOT EXISTS function_mapping (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id   INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    function_id INTEGER NOT NULL,   -- function.id（函數身份）
    line_ids    TEXT    NOT NULL,   -- JSON：["line:1 to 3", ...]
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, function_id)
);
"""

# ============ package / file 樹（2026-10-26 用戶要求）============
# package 表：module 下嘅 package（channel_id + module_id + package_name）
PACKAGE_DDL = """
CREATE TABLE IF NOT EXISTS package (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id   INTEGER NOT NULL,   -- channel 身份
    module_id    INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    package_name TEXT    NOT NULL,   -- package 名
    is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (channel_id, module_id, package_name)
);
"""

# file 表：package 下嘅檔案
FILE_DDL = """
CREATE TABLE IF NOT EXISTS file (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id  INTEGER NOT NULL,   -- channel 身份
    module_id   INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    package_id  INTEGER,            -- package.id（屬邊個 package）
    file_name   TEXT    NOT NULL,   -- 檔案名
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, package_id, file_name)
);
"""

# ============ 行級證明（2026-10-26 用戶要求）============
# 每行 = 一條「真實行內容證明」：證明 line_field / line_ast 嗰行
# 真係存在，內容係咩（可驗證事實，唔係假資料）。

# proof_line_field 表：line_field 嘅證明（每行 line_field 一條 proof）
#    line_field_id = line_field.id
#    value_json    = {"欄位名": "該行真實內容"}（例如 {"is_active": "..."}）
#    location      = 完整路徑（該行屬於邊個 .py 檔）
#    line_number   = 行號（= line_field.line_number）
PROOF_LINE_FIELD_DDL = """
CREATE TABLE IF NOT EXISTS proof_line_field (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    line_field_id  INTEGER NOT NULL,   -- line_field.id
    value_json     TEXT    NOT NULL,   -- {"欄位名": "該行真實內容"}
    location       TEXT    NOT NULL,   -- 完整路徑（full path of the file）
    line_number    INTEGER NOT NULL,   -- 行號
    is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (line_field_id, line_number)
);
"""

# proof_line_ast 表：line_ast 嘅證明（每行 line_ast 一條 proof）
#    line_ast_id  = line_ast.id
#    value_json   = {"ast名": "該行真實內容"}（例如 {"fill 對外方法": "..."}）
#    location     = 完整路徑（該行屬於邊個 .py 檔）
#    line_number  = 行號（= line_ast.line_number）
PROOF_LINE_AST_DDL = """
CREATE TABLE IF NOT EXISTS proof_line_ast (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    line_ast_id  INTEGER NOT NULL,   -- line_ast.id
    value_json   TEXT    NOT NULL,   -- {"ast名": "該行真實內容"}
    location     TEXT    NOT NULL,   -- 完整路徑（full path of the file）
    line_number  INTEGER NOT NULL,   -- 行號
    is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (line_ast_id, line_number)
);
"""

# ============ file_line_type / formula_type（2026-10-28 用戶設計）============
# 目的：將一個檔案分段 — 「第幾行到第幾行係咩 formula 類型」。
#   file A（1500 行）
#     line 500        = python * definition
#     line 501-1000   = SQL * select
#     line 1001-1200  = SQL * update
#     line 1201-1300  = SQL * insert
#     line 1301-1330  = python * function A
#     line 1331-1380  = python * function B
#     line 1401-1450  = python * api
#     line 1451-1500  = python * rest_api

# ============ formula subject × action × object（2026-10-28 用戶 redesign）============
# 舊 formula_type（language_id + meta 兩欄分類值）係錯設計（用戶指出）。
# 正規化：subject * action * object 三張字典（每張只 1 個 meta）+ formula 組合表。
#   python * definition  = subject(python) × action(definition) × object(class)
#   python * function    = subject(python) × action(function)  × object(function)
#   python * api         = subject(python) × action(api)       × object(api)
#   python * route       = subject(python) × action(route)     × object(route)
#   python * rest_api    = subject(python) × action(rest_api)  × object(endpoint)
#   python * formula     = subject(python) × action(formula)   × object(formula)
#   sql * select         = subject(sql)    × action(select)    × object(table)
#   sql * update         = subject(sql)    × action(update)    × object(table)
#   sql * insert         = subject(sql)    × action(insert)    × object(table)
#   sql * delete         = subject(sql)    × action(delete)    × object(table)
#   sql * create         = subject(sql)    × action(create)    × object(table)
#   sql * alter          = subject(sql)    × action(alter)     × object(table)
# 每張字典表只有 1 個 meta 欄（用戶要求：each table only allow 1 meta）。

FORMULA_SUBJECT_DDL = """
CREATE TABLE IF NOT EXISTS formula_subject (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,  -- python / sql
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

FORMULA_ACTION_DDL = """
CREATE TABLE IF NOT EXISTS formula_action (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,  -- definition / function / api / route / rest_api / formula / select / update / insert / delete / create / alter
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

FORMULA_OBJECT_DDL = """
CREATE TABLE IF NOT EXISTS formula_object (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,  -- class / decorator / constant / function / api / route / endpoint / formula / table / row / column / field
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# formula 組合表：subject × action × object（全 by id，一行一個組合）
FORMULA_DDL = """
CREATE TABLE IF NOT EXISTS formula (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id  INTEGER NOT NULL,          -- formula_subject.id
    action_id   INTEGER NOT NULL,          -- formula_action.id
    object_id   INTEGER NOT NULL,          -- formula_object.id
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (subject_id, action_id, object_id)
);
"""

# formula 預設種子（冪等）：subject × action × object 組合（2026-10-28 用戶例子）
# action 次序：python 版 + sql 版；加咗 route（用戶問「where is python * route?」）
DEFAULT_FORMULA_SUBJECTS = [
    ("python", "Python 程式"),
    ("sql", "SQL 查詢語言"),
]

DEFAULT_FORMULA_ACTIONS = [
    ("definition", "定義"),
    ("function", "函數"),
    ("api", "API 方法"),
    ("route", "路由"),
    ("rest_api", "REST endpoint"),
    ("formula", "公式（@formula_def）"),
    ("select", "SELECT 查詢"),
    ("update", "UPDATE 更新"),
    ("insert", "INSERT 寫入"),
    ("delete", "DELETE 刪除"),
    ("create", "CREATE 建表"),
    ("alter", "ALTER 修改"),
]

DEFAULT_FORMULA_OBJECTS = [
    ("class", "類別"),
    ("decorator", "裝飾器"),
    ("constant", "常量"),
    ("function", "函數"),
    ("api", "API"),
    ("route", "路由"),
    ("endpoint", "端點"),
    ("formula", "公式"),
    ("table", "表"),
    ("row", "行"),
    ("column", "欄"),
    ("field", "欄位"),
]

# 預設組合（subject_meta, action_meta, object_meta, description）
DEFAULT_FORMULAS = [
    ("python", "definition", "class", "python 定義（def class）"),
    ("python", "definition", "decorator", "python 定義（decorator）"),
    ("python", "definition", "constant", "python 定義（常量）"),
    ("python", "function", "function", "python 函數"),
    ("python", "api", "api", "python API 方法"),
    ("python", "route", "route", "python 路由"),
    ("python", "rest_api", "endpoint", "python REST endpoint"),
    ("python", "formula", "formula", "python formula（@formula_def）"),
    ("sql", "select", "table", "SQL SELECT 查詢"),
    ("sql", "update", "table", "SQL UPDATE 更新"),
    ("sql", "insert", "table", "SQL INSERT 寫入"),
    ("sql", "delete", "table", "SQL DELETE 刪除"),
    ("sql", "create", "table", "SQL CREATE 建表"),
    ("sql", "alter", "table", "SQL ALTER 修改"),
]

# file_line_type 表：檔案行範圍分段（一行 = 一個連續範圍；全 by id）
#   file_id      = programming.file.id（屬邊個檔案）
#   start_line   = 開始行號（含）
#   end_line     = 結束行號（含）
#   formula_id   = formula.id（subject × action × object 組合，全 by id）
#   function_id  = ast.db function.id（可選；function 專屬段）
FILE_LINE_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS file_line_type (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id          INTEGER NOT NULL,     -- programming.file.id
    start_line       INTEGER NOT NULL,     -- 開始行（含）
    end_line         INTEGER NOT NULL,     -- 結束行（含）
    formula_id       INTEGER NOT NULL,     -- formula.id（subject×action×object）
    function_id      INTEGER,              -- ast.db function.id（可選）
    is_active        BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (file_id, start_line, end_line)
);
"""

# ============ 欄位值域（db_field_value，2026-10-26 用戶要求）============
# 每個「真表欄位」（structure.db structure_db_field）適用嘅值域檢查
# （structure.db db_field_check）一行。資料由「真實 db_field」
# （resource.db db_field 實例）推導 —— 只記真欄位 × 真 check，零假資料。
#    structure_db_field_id = structure.db structure_db_field.id（真欄位）
#    db_field_check_id     = structure.db db_field_check.id（值域檢查）
DB_FIELD_VALUE_DDL = """
CREATE TABLE IF NOT EXISTS db_field_value (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_db_field_id  INTEGER NOT NULL,  -- structure.db structure_db_field.id
    db_field_check_id      INTEGER NOT NULL,  -- structure.db db_field_check.id
    is_active              INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_db_field_id, db_field_check_id)
);
"""

# ============ 欄位設定（db_field_setting）============
# 2026-10-26：已搬去 structure module（structure.db db_field_setting 表）——
# 欄位設定字典嘅家 = structure（同 db_field_unique / db_field_property 一齊）。

# ============ 程式語言證據（2026-10-27 用戶設計：source 官方網站可證明） ============
# 概念：evidence = data can proof by source（官方網站 / 標準文件）。
# 程式語言層一樣可以證明：每種語法單元（AST node / decorator / SQL 語句）
# 對應一個官方來源（source_id -> source.db source.id），
# 呢度記錄「該語法單元喺官方來源可證明」嘅證據。
#
# sql_type 表：SQL 語句類型字典（DDL / DML）—— 2026-10-28 用戶 redesign
# 正規化：id | language_id | action_id | value（meta 展示）
#   language_id = programming_language.id（sql=25）
#   action_id   = formula_action.id（DDL/DML 係動作分類；create/alter = DDL，
#                 select/insert/update/delete = DML）
#   value       = 展示名（DDL / DML，保留做 meta）
SQL_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS sql_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id INTEGER NOT NULL,          -- programming_language.id（sql=25）
    action_id   INTEGER NOT NULL,          -- formula_action.id（DDL/DML 動作分類）
    value       TEXT    NOT NULL UNIQUE,   -- 展示名（DDL / DML）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# sql_type 預設種子（2026-10-27 用戶指定；2026-10-28 加 language_id + action_id）
# （language_id=25 sql；action_id 由 formula_action.meta 反查：DDL/DML 係動作）
DEFAULT_SQL_TYPES = [
    ("DDL", "資料定義語言（CREATE / ALTER / DROP / RENAME / TRUNCATE ...）"),
    ("DML", "資料操作語言（SELECT / INSERT / UPDATE / DELETE ...）"),
]

# python_ast 表：Python AST 節點字典（2026-10-27 用戶設計；2026-10-28 用戶 redesign）
# 正規化：id | language_id | object_id | ast（meta 展示）| symbol
#   language_id = programming_language.id（python=1）
#   object_id   = formula_object.id（AST 節點係「被操作嘅語法對象」
#                 -> formula_object；FunctionDef=function_statement ...）
#   ast         = AST 節點名（FunctionDef / Starred ...，保留做 meta 展示）
#   symbol      = 對應符號（Starred -> "*" / Compare -> "=="...；冇 = NULL）
# 一行 = 一個官方語法節點（docs.python.org 可證明），
# 用嚟切 code 行 / function 做 AST pattern（同 formula_cuter 對照嘅語言層版本），
# 亦俾 formula_cuter 每粒 symbol token 反查到「呢粒 = 邊個 AST 節點」。
PYTHON_AST_DDL = """
CREATE TABLE IF NOT EXISTS python_ast (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id INTEGER NOT NULL,   -- programming_language.id（python=1）
    object_id   INTEGER NOT NULL,   -- formula_object.id（AST 節點 = 語法對象）
    ast         TEXT    NOT NULL,   -- AST 節點名（FunctionDef / Starred ...，meta 展示）
    symbol      TEXT,               -- 對應符號（Starred -> "*" / Compare -> "=="）
    description TEXT,               -- 節點說明（例如 "*items" = Starred vararg）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (language_id, ast)
);
"""

# Python 官方（docs.python.org/3/library/ast.html）AST 節點預設種子
# symbol = 該節點最常用嘅標記符號（formula_cuter 反查用）
DEFAULT_PYTHON_ASTS = [
    (1, "FunctionDef", None, "函數定義（def name(...):）"),
    (1, "AsyncFunctionDef", None, "異步函數定義（async def ...）"),
    (1, "ClassDef", None, "類別定義（class Name:）"),
    (1, "Return", None, "return 語句"),
    (1, "Assign", "=", "賦值（x = y）"),
    (1, "AugAssign", "+=", "複合賦值（x += 1）"),
    (1, "If", None, "if 條件語句"),
    (1, "For", None, "for 迴圈"),
    (1, "While", None, "while 迴圈"),
    (1, "Call", None, "函式呼叫（f(...)）"),
    (1, "Raise", None, "raise 語句"),
    (1, "Import", None, "import 語句"),
    (1, "ImportFrom", None, "from x import y"),
    (1, "Compare", "==", "比較表達式（a < b）"),
    (1, "Subscript", "[]", "下標（obj[i]）"),
    (1, "Attribute", ".", "屬性存取（obj.attr）"),
    (1, "Starred", "*", "可變參數（*items / **kwargs）"),
    (1, "GeneratorExp", None, "生成器表達式（x for x in y）"),
    (1, "Lambda", None, "lambda 表達式"),
    (1, "Tuple", None, "tuple 建構（(a, b)）"),
    (1, "List", None, "list 建構（[a, b]）"),
    (1, "Dict", None, "dict 建構（{k: v}）"),
    (1, "Set", None, "set 建構（{a, b}）"),
    (1, "BinOp", "+", "二元運算（a + b）"),
    (1, "BoolOp", "and", "布林運算（a and b）"),
    (1, "UnaryOp", "not", "一元運算（not a / -a）"),
    (1, "NamedExpr", ":=", "海象運算子（:=，Python 3.8+）"),
    (1, "Try", None, "try/except 語句"),
    (1, "With", None, "with 語句"),
    (1, "Global", None, "global 宣告"),
    (1, "Nonlocal", None, "nonlocal 宣告"),
    (1, "Constant", None, "常數（數字/字串/None/True/False）"),
    (1, "Name", None, "名稱載入（x）"),
    (1, "AnnAssign", ":", "帶型別註解嘅賦值（x: int = 1）"),
    (1, "Yield", None, "yield 語句"),
    (1, "Await", None, "await 表達式"),
    (1, "Match", None, "match 語句（Python 3.10+）"),
    (1, "arg", None, "參數（def name(arg) 嘅每個參數）"),
]

# python 語法字典（官方可證明，docs.python.org）
# 2026-10-28（用戶要求）：python_decorators 表已搬去 ast module
# （decorator 係語言語法單元，歸 AST 分析中心）——呢度淨保留 python_ast。
PYTHON_SYNTAX_DDL = PYTHON_AST_DDL

# ============ structure_type（2026-10-27 用戶設計：語境層級字典） ============
# 每個語法節點（arg / Starred）出現喺邊種「結構層級」：
#   module / channel / skill / db_table / db_field
# 用嚟做 *_allowed 語境允許嘅分類維度（一個 arg 可以喺唔同層級）。
STRUCTURE_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS structure_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type TEXT NOT NULL UNIQUE,  -- module / channel / skill / db_table / db_field
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

DEFAULT_STRUCTURE_TYPES = [
    ("module", "module 層"),
    ("channel", "channel 層"),
    ("skill", "skill 層"),
    ("db_table", "真表"),
    ("db_field", "真欄位"),
]

# ============ field_allowed 語境允許表（2026-10-27 用戶設計） ============
# python_ast 節點（arg / Starred / Name ...）喺真實 code 出現時，
# 佢嘅「值」唔可以亂——要喺允許清單（*_allowed）入面先算正確。
# 正規分類（用戶指定，取代 NULL NULL 含糊設計；allowed 欄已移除）：
#   arg_id              = 參數名（attr / items ...；即 python_ast 嘅 arg 節點實例）
#   structure_type_id   = structure_type.id（module/db_table/db_field... 語境層級）
#   data_format_type_id = programming.data_format.id（json=5 / xml=6 / csv=7 / yaml=8）
#
# field_allowed 表（rename 自 arg_allowed，2026-10-27）：函數參數嘅語境允許
FIELD_ALLOWED_DDL = """
CREATE TABLE IF NOT EXISTS field_allowed (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    arg_id               TEXT    NOT NULL,   -- 參數名（attr / items / obj ...）
    structure_type_id    INTEGER,            -- structure_type.id（module / db_table ...）
    data_format_type_id  INTEGER,            -- data_format.id（json=5 / xml=6 / csv=7 / yaml=8）
    is_active            BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (arg_id, structure_type_id, data_format_type_id)
);
"""

# Starred_allowed 表：Starred 節點（*items / **kwargs）允許出現嘅可變參數
STARRED_ALLOWED_DDL = """
CREATE TABLE IF NOT EXISTS Starred_allowed (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    starred_id           TEXT    NOT NULL,   -- 可變參數名（items / kwargs ...）
    structure_type_id    INTEGER,            -- structure_type.id（module / db_table ...）
    data_format_type_id  INTEGER,            -- data_format.id（json / xml ...）
    allowed              TEXT,               -- 允許值（JSON 陣列 / NULL = 任何）
    is_active            BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (starred_id, structure_type_id, data_format_type_id)
);
"""

# sql_keyword 表：SQL 關鍵字字典（2026-10-28 用戶：formula_cuter 證明用）
#   language_id = programming_language.id（sql=25）
#   sql_type_id = sql_type.id（DDL / DML 歸屬，可空 = 通用）
#   value       = keyword（SELECT / FROM / WHERE / JOIN / TABLE ...）
#   source_id   = source.db source.id（ISO/IEC 9075 = 2）
# 一行 = 一個 SQL 關鍵字（官方標準可證明），
# 用嚟 formula_cuter 每粒 SQL token 反查到「呢粒 = 官方 SQL keyword」。
SQL_KEYWORD_DDL = """
CREATE TABLE IF NOT EXISTS sql_keyword (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id INTEGER NOT NULL,          -- programming_language.id（sql=25）
    sql_type_id INTEGER,                    -- sql_type.id（DDL / DML；NULL = 通用）
    value       TEXT    NOT NULL UNIQUE,   -- keyword（SELECT / FROM / WHERE ...）
    source_id   INTEGER,                    -- source.db source.id（ISO/IEC 9075 = 2）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# SQL 關鍵字預設種子（2026-10-28：ISO/IEC 9075 可證明；全 keyword）
DEFAULT_SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "JOIN", "LEFT JOIN", "RIGHT JOIN",
    "INNER JOIN", "OUTER JOIN", "ON", "GROUP BY", "ORDER BY", "HAVING",
    "LIMIT", "OFFSET", "AS", "DISTINCT", "ALL", "UNION", "INTERSECT",
    "EXCEPT", "IN", "NOT IN", "EXISTS", "NOT EXISTS", "BETWEEN", "LIKE",
    "IS NULL", "IS NOT NULL", "AND", "OR", "NOT", "CASE", "WHEN", "THEN",
    "ELSE", "END", "INSERT INTO", "VALUES", "UPDATE", "SET", "DELETE FROM",
    "CREATE TABLE", "ALTER TABLE", "DROP TABLE", "TRUNCATE", "RENAME",
    "CREATE INDEX", "DROP INDEX", "CREATE VIEW", "DROP VIEW",
    "CREATE TRIGGER", "DROP TRIGGER", "PRAGMA", "EXPLAIN", "VACUUM",
    "ATTACH", "DETACH", "REINDEX", "ANALYZE", "WITH", "RECURSIVE",
    "TABLE", "INDEX", "VIEW", "TRIGGER", "DATABASE", "SCHEMA",
]

# sql_allowed 表：SQL 語句（DDL/DML）允許出現嘅表/欄位（SQL 版 *allowed）
#   sql_type_id  = sql_type.id（DDL / DML）
#   value        = SQL 語句/關鍵字（CREATE TABLE / SELECT ...）
#   db_table_id  = structure.db structure_db_table.id（呢句 SQL 對應邊張真表）
#   db_field_id  = structure.db structure_db_field.id（呢句 SQL 對應邊個真欄位）
#   allowed      = 允許值（JSON / NULL = 任何）
SQL_ALLOWED_DDL = """
CREATE TABLE IF NOT EXISTS sql_allowed (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    sql_type_id       INTEGER NOT NULL,  -- sql_type.id（DDL / DML）
    value             TEXT    NOT NULL,   -- SQL 語句/關鍵字（CREATE TABLE / SELECT ...）
    db_table_id       INTEGER,            -- structure.db structure_db_table.id（對應真表）
    db_field_id       INTEGER,            -- structure.db structure_db_field.id（對應真欄位）
    allowed           TEXT,               -- 允許值（JSON 陣列 / NULL = 任何）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (sql_type_id, value, db_table_id, db_field_id)
);
"""

# python *_allowed 系列（2026-10-27 用戶設計：節點 -> 分類 -> 值允許）
PYTHON_ALLOWED_DDL = (FIELD_ALLOWED_DDL + STARRED_ALLOWED_DDL
                      + SQL_ALLOWED_DDL)

# evidence_ast 表：AST 語法節點嘅 source 證據
#   source_id   = source.db source.id（官方 spec：Python Language Reference = python.org）
#   language_id = programming_language.id（python=1 / sql=25 ...）
#   ast_id      = ast.db function.id（該節點出現喺邊個 function）／冇 = NULL
#   value       = AST 節點名（FunctionDef / ClassDef / Call / For ...）
# 一行 = 「呢個 AST 節點喺官方文件可證明」（證據 = source 存在）。
EVIDENCE_AST_DDL = """
CREATE TABLE IF NOT EXISTS evidence_ast (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   INTEGER NOT NULL,   -- source.db source.id（官方來源）
    language_id INTEGER NOT NULL,   -- programming_language.id
    ast_id      INTEGER,            -- ast.db function.id（可選）
    value       TEXT    NOT NULL,   -- AST 節點名（FunctionDef / ClassDef ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (source_id, language_id, ast_id, value)
);
"""

# evidence_decorators 表：decorator 嘅 source 證據
#   decorators_id = template.db decorator.id（啱啱整嘅 table-driven decorator 表）
#   value         = decorator 名（formula_def / app.route / property ...）
# 一行 = 「呢個 decorator 喺官方文件可證明」。
EVIDENCE_DECORATORS_DDL = """
CREATE TABLE IF NOT EXISTS evidence_decorators (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id      INTEGER NOT NULL,   -- source.db source.id（官方來源）
    language_id    INTEGER NOT NULL,   -- programming_language.id
    decorators_id  INTEGER,            -- template.db decorator.id（可選）
    value          TEXT    NOT NULL,   -- decorator 名（formula_def / property ...）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (source_id, language_id, decorators_id, value)
);
"""

# evidence_SQL 表：SQL 語句嘅 source 證據
#   sql_type_id = sql_type.id（DDL / DML）
#   value       = SQL 語句/關鍵字（CREATE TABLE / SELECT ...）
# 一行 = 「呢句 SQL 喺官方標準可證明」（ISO/IEC 9075 = source.db id 2）。
EVIDENCE_SQL_DDL = """
CREATE TABLE IF NOT EXISTS evidence_SQL (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   INTEGER NOT NULL,   -- source.db source.id（ISO/IEC 9075 等）
    language_id INTEGER NOT NULL,   -- programming_language.id（sql=25）
    sql_type_id INTEGER NOT NULL,   -- sql_type.id（DDL / DML）
    value       TEXT    NOT NULL,   -- SQL 語句/關鍵字（CREATE TABLE / SELECT ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (source_id, language_id, sql_type_id, value)
);
"""

PROGRAMMING_EVIDENCE_DDL = (SQL_TYPE_DDL + EVIDENCE_AST_DDL
                            + EVIDENCE_DECORATORS_DDL + EVIDENCE_SQL_DDL)

__all__ = ["PROGRAMMING_LANGUAGE_DDL", "LANGUAGE_ALIAS_DDL",
           "DATA_FORMAT_DDL", "OWNER_DDL", "OWNER_LETTER_DDL",
           "OWNER_SYMBOL_DDL", "OWNER_INT_DDL", "START_CHAR_DDL",
           "LINE_AST_DDL", "LINE_FIELD_DDL",
           "FUNCTION_MAPPING_DDL",
           "PACKAGE_DDL", "FILE_DDL",
           "PROOF_LINE_FIELD_DDL", "PROOF_LINE_AST_DDL",
           "DB_FIELD_VALUE_DDL",
           "PYTHON_AST_DDL", "DEFAULT_PYTHON_ASTS",
           "PYTHON_SYNTAX_DDL",
           "STRUCTURE_TYPE_DDL", "DEFAULT_STRUCTURE_TYPES",
           "FIELD_ALLOWED_DDL", "STARRED_ALLOWED_DDL", "SQL_ALLOWED_DDL",
           "PYTHON_ALLOWED_DDL",
           "SQL_KEYWORD_DDL", "DEFAULT_SQL_KEYWORDS",
           "SQL_TYPE_DDL", "DEFAULT_SQL_TYPES", "EVIDENCE_AST_DDL",
           "EVIDENCE_DECORATORS_DDL", "EVIDENCE_SQL_DDL",
           "PROGRAMMING_EVIDENCE_DDL",
           "FORMULA_SUBJECT_DDL", "FORMULA_ACTION_DDL", "FORMULA_OBJECT_DDL",
           "FORMULA_DDL",
           "DEFAULT_FORMULA_SUBJECTS", "DEFAULT_FORMULA_ACTIONS",
           "DEFAULT_FORMULA_OBJECTS", "DEFAULT_FORMULAS",
           "FILE_LINE_TYPE_DDL"]