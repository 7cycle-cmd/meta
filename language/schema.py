"""schema.py — language 權威 DDL 入口（唯一 schema 來源）"""

# language 表：語言字典（由 definition.db 搬嚟，2026-10-25）
LANGUAGE_DDL = """
CREATE TABLE IF NOT EXISTS language (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 語言代碼（zh / en / ja ...）
    description TEXT,                       -- 語言名（中文 / 英文 ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# display_text 表：顯示文字字典（2026-10-25 用戶要求）
DISPLAY_TEXT_DDL = """
CREATE TABLE IF NOT EXISTS display_text (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 文字 key（例如 module_name / greeting）
    description TEXT,                       -- 用途描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ["LANGUAGE_DDL", "DISPLAY_TEXT_DDL"]
