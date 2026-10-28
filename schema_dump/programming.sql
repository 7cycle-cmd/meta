-- schema dump: programming.db
-- generated : 2026-10-27T16:21:48
-- objects   : 30（table=30）

-- [table] Starred_allowed
CREATE TABLE Starred_allowed (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    starred_id           TEXT    NOT NULL,   -- 可變參數名（items / kwargs ...）
    structure_type_id    INTEGER,            -- structure_type.id（module / db_table ...）
    data_format_type_id  INTEGER,            -- data_format.id（json / xml ...）
    allowed              TEXT,               -- 允許值（JSON 陣列 / NULL = 任何）
    is_active            BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (starred_id, structure_type_id, data_format_type_id)
);

-- [table] data_format
CREATE TABLE data_format (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,
    description TEXT,
    source_id   INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] db_field_value
CREATE TABLE "db_field_value" (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                structure_db_field_id  INTEGER NOT NULL,
                db_field_check_id      INTEGER NOT NULL,
                is_active              INTEGER NOT NULL DEFAULT 1,
                created_at             TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at             TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                UNIQUE (structure_db_field_id, db_field_check_id)
            );

-- [table] evidence_SQL
CREATE TABLE evidence_SQL (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   INTEGER NOT NULL,   -- source.db source.id（ISO/IEC 9075 等）
    language_id INTEGER NOT NULL,   -- programming_language.id（sql=25）
    sql_type_id INTEGER NOT NULL,   -- sql_type.id（DDL / DML）
    value       TEXT    NOT NULL,   -- SQL 語句/關鍵字（CREATE TABLE / SELECT ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (source_id, language_id, sql_type_id, value)
);

-- [table] evidence_ast
CREATE TABLE evidence_ast (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   INTEGER NOT NULL,   -- source.db source.id（官方來源）
    language_id INTEGER NOT NULL,   -- programming_language.id
    ast_id      INTEGER,            -- ast.db function.id（可選）
    value       TEXT    NOT NULL,   -- AST 節點名（FunctionDef / ClassDef ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (source_id, language_id, ast_id, value)
);

-- [table] evidence_decorators
CREATE TABLE evidence_decorators (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id      INTEGER NOT NULL,   -- source.db source.id（官方來源）
    language_id    INTEGER NOT NULL,   -- programming_language.id
    decorators_id  INTEGER,            -- template.db decorator.id（可選）
    value          TEXT    NOT NULL,   -- decorator 名（formula_def / property ...）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (source_id, language_id, decorators_id, value)
);

-- [table] field_allowed
CREATE TABLE field_allowed (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    arg_id               TEXT    NOT NULL,   -- 參數名（attr / items / obj ...）
    structure_type_id    INTEGER,            -- structure_type.id（module / db_table ...）
    data_format_type_id  INTEGER,            -- data_format.id（json=5 / xml=6 / csv=7 / yaml=8）
    is_active            BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (arg_id, structure_type_id, data_format_type_id)
);

-- [table] file
CREATE TABLE file (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id  INTEGER NOT NULL,   -- channel 身份
    module_id   INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    package_id  INTEGER,            -- package.id（屬邊個 package）
    file_name   TEXT    NOT NULL,   -- 檔案名
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, package_id, file_name)
);

-- [table] function_mapping
CREATE TABLE function_mapping (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id   INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    function_id INTEGER NOT NULL,   -- function.id（函數身份）
    line_ids    TEXT    NOT NULL,   -- JSON：["line:1 to 3", ...]
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, function_id)
);

-- [table] language_alias
CREATE TABLE language_alias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id INTEGER NOT NULL,   -- programming_language.id（正名語言）
    alias       TEXT    NOT NULL,   -- 別名（py / js / java / c ...）
    description TEXT,
    source_id   INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (language_id, alias)
);

-- [table] line_ast
CREATE TABLE line_ast (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id   INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    language_id INTEGER NOT NULL,   -- programming_language.id（語言）
    ast         TEXT    NOT NULL,   -- AST 節點（語句名 / 結構）
    package_id  INTEGER,            -- package.id（屬邊個 package）
    file_id     INTEGER,            -- file.id（屬邊個檔案）
    line_number INTEGER NOT NULL,   -- 行號
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, language_id, file_id, line_number)
);

-- [table] line_field
CREATE TABLE line_field (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id          INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    language_id        INTEGER NOT NULL,   -- programming_language.id（語言）
    db_field_check_id  INTEGER,            -- structure.db db_field_check.id（檢查）
    package_id         INTEGER,            -- package.id（屬邊個 package）
    file_id            INTEGER,            -- file.id（屬邊個檔案）
    line_number        INTEGER NOT NULL,   -- 行號
    is_active          INTEGER NOT NULL DEFAULT 1,
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, language_id, file_id, line_number)
);

-- [table] owner
CREATE TABLE owner (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id INTEGER NOT NULL,   -- programming_language.id（邊種語言）
    format_id   INTEGER NOT NULL,   -- data_format.id（邊種數據格式）
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (language_id, format_id)
);

-- [table] owner_INT
CREATE TABLE owner_INT (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    INTEGER NOT NULL,   -- owner.id（邊個語言×格式組合）
    int_id      INTEGER NOT NULL,   -- character.db "INT".id（接受邊個數字 0-9）
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (owner_id, int_id)
);

-- [table] owner_letter
CREATE TABLE owner_letter (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    INTEGER NOT NULL,   -- owner.id（邊個語言×格式組合）
    letter_id   INTEGER NOT NULL,   -- character.db letter.id（接受邊個字母）
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (owner_id, letter_id)
);

-- [table] owner_symbol
CREATE TABLE owner_symbol (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    INTEGER NOT NULL,   -- owner.id（邊個語言×格式組合）
    symbol_id   INTEGER NOT NULL,   -- character.db symbol.id（接受邊個符號）
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (owner_id, symbol_id)
);

-- [table] package
CREATE TABLE package (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id   INTEGER NOT NULL,   -- channel 身份
    module_id    INTEGER NOT NULL,   -- taxonomy.package.id（module 身份）
    package_name TEXT    NOT NULL,   -- package 名
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (channel_id, module_id, package_name)
);

-- [table] programming_language
CREATE TABLE programming_language (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    meta         TEXT    NOT NULL UNIQUE,
    description  TEXT,
    source_id    INTEGER,
    char_format  TEXT,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] proof_line_ast
CREATE TABLE proof_line_ast (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    line_ast_id  INTEGER NOT NULL,   -- line_ast.id
    value_json   TEXT    NOT NULL,   -- {"ast名": "該行真實內容"}
    location     TEXT    NOT NULL,   -- 完整路徑（full path of the file）
    line_number  INTEGER NOT NULL,   -- 行號
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (line_ast_id, line_number)
);

-- [table] proof_line_field
CREATE TABLE proof_line_field (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    line_field_id  INTEGER NOT NULL,   -- line_field.id
    value_json     TEXT    NOT NULL,   -- {"欄位名": "該行真實內容"}
    location       TEXT    NOT NULL,   -- 完整路徑（full path of the file）
    line_number    INTEGER NOT NULL,   -- 行號
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (line_field_id, line_number)
);

-- [table] python_ast
CREATE TABLE python_ast (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id INTEGER NOT NULL,   -- programming_language.id（python=1）
    ast         TEXT    NOT NULL,   -- AST 節點名（FunctionDef / Starred ...）
    description TEXT,               -- 節點說明（例如 "*items" = Starred vararg）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')), symbol TEXT,
    UNIQUE (language_id, ast)
);

-- [table] python_decorators
CREATE TABLE python_decorators (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id INTEGER NOT NULL,   -- programming_language.id（python=1）
    decorators  TEXT    NOT NULL,   -- decorator 名（formula_def / property ...）
    description TEXT,               -- 用途（例如 @property = 唯讀屬性）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (language_id, decorators)
);

-- [table] registry
CREATE TABLE registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT, meta TEXT NOT NULL UNIQUE, description TEXT, is_active BOOLEAN NOT NULL CHECK (is_active IN (0,1)) DEFAULT 1, created_at TEXT DEFAULT (datetime('now', 'localtime')), updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- [table] skill
CREATE TABLE skill (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_key    TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1
                            CHECK (is_active IN (0,1)),
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] skill_mapping
CREATE TABLE skill_mapping (id INTEGER PRIMARY KEY AUTOINCREMENT,module_id INTEGER NOT NULL, skill_id INTEGER NOT NULL,line_ids TEXT NOT NULL,is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),UNIQUE (module_id, skill_id));

-- [table] sql_allowed
CREATE TABLE sql_allowed (
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

-- [table] sql_type
CREATE TABLE sql_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- DDL / DML
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- [table] start_char
CREATE TABLE start_char (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL,   -- 開頭字符約束（例如 0-9 = 唔畀數字開頭）
    owner_id    INTEGER NOT NULL,   -- owner.id（呢個組合唔畀呢個開頭）
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (owner_id, value)
);

-- [table] structure_type
CREATE TABLE structure_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type TEXT NOT NULL UNIQUE,  -- module / channel / skill / db_table / db_field
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
