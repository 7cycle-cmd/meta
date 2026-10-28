"""schema.py — value 權威 DDL 入口（唯一 schema 來源）

value.db 存放「值資產」：
    value    值字典（id | value | taxonomy_id）
"""

# value 表：值資產（2026-10-27 用戶要求：由 terminology 升做獨立 module）
#   一行 = 一個值（asset）
#   value       = 值本身（data / build / 5W2H ...）
#   taxonomy_id = taxonomy.registry.id（邊個 module 登記，trace 用）
VALUE_DDL = """
CREATE TABLE IF NOT EXISTS value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT,
    taxonomy_id INTEGER,             -- taxonomy.registry.id（邊個 module 登記）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ["VALUE_DDL"]