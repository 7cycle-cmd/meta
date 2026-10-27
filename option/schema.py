"""schema.py — option 權威 DDL 入口（唯一 schema 來源）

option.db 存放「值域定義」（2026-10-24u，2026-10-25 擴充）：
    每個欄位 / 表（structure）可以有允許值清單。
    定義層話你知「呢個欄位可以填咩」——
    唔執行判斷（執行 = run/result 真實發生記錄）。

    2026-10-25（用戶要求）：
        + structure_db_field_id    （structure.db structure_db_field.id）
        + structure_db_table_id    （structure.db structure_db_table.id）
        而家 0/1 例子（840233）用 resource_id 指 registry；新欄位直接指
        真結構。reset API：清空重來。

（8 檔標準：__init__/function/api/route/schema/sql/registry/rest_api）
"""

DB_FIELD_OPTION_DDL = """
CREATE TABLE IF NOT EXISTS table_field_option (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id            INTEGER,   -- resource.db registry.id（舊；可選）
    structure_db_field_id  INTEGER,   -- structure.db structure_db_field.id（欄位）
    structure_db_table_id  INTEGER,   -- structure.db structure_db_table.id（表）
    value                  TEXT    NOT NULL,   -- 允許值（'0' / '1' / 'json' ...）
    description            TEXT,               -- 描述
    is_active              INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (resource_id, value),
    UNIQUE (structure_db_field_id, value)
);
"""

__all__ = ["DB_FIELD_OPTION_DDL"]