"""schema.py — character 權威 DDL 入口（唯一 schema 來源）

character.db 存放字符定義（2026-10-24s 由 terminology 拆出）：
    字符集：symbol / letter / letter_char_format / INT

（8 檔標準：__init__/function/api/route/schema/sql/registry/rest_api）
"""

SYMBOL_DDL = """
CREATE TABLE IF NOT EXISTS symbol (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,
    description TEXT,
    source_id   INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

LETTER_DDL = """
CREATE TABLE IF NOT EXISTS letter (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    letter_char_format_id  INTEGER NOT NULL,  -- letter_char_format.id（uppercase / lowercase）
    value                   TEXT    NOT NULL,  -- 字母本身（a-z / A-Z）
    description             TEXT,
    source_id               INTEGER,
    is_active               INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at              TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (letter_char_format_id, value)
);
"""

INT_DDL = """
CREATE TABLE IF NOT EXISTS "INT" (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,
    description TEXT,
    source_id   INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

LETTER_CHAR_FORMAT_DDL = """
CREATE TABLE IF NOT EXISTS letter_char_format (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,
    description TEXT,
    source_id   INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ["SYMBOL_DDL", "LETTER_DDL", "INT_DDL", "LETTER_CHAR_FORMAT_DDL"]