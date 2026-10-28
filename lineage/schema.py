"""schema.py — lineage 權威 DDL 入口（唯一 schema 來源）

lineage.db 存放「值嘅運行時條件」：
    lineage    運行時條件記錄（id | resource_id | value_id | taxonomy_id |
               run_id | flow_id | step_id | value）
"""

# lineage 表：記錄 value 嘅 runtime condition（2026-10-27 用戶要求）
#   一行 = 一個值喺一次運行（run）入面嘅條件快照
#   resource_id = 來源資源（邊度嚟）
#   value_id    = value.id（受記錄嘅值）
#   taxonomy_id = taxonomy.registry.id（邊個 module 登記）
#   run_id      = run.id（邊次運行）
#   flow_id     = flow.id（邊條 flow）
#   step_id     = step.id（行到邊步）
#   value       = 值字串快照（方便睇，唔使 JOIN value.db）
LINEAGE_DDL = """
CREATE TABLE IF NOT EXISTS lineage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER,
    value_id    INTEGER,
    taxonomy_id INTEGER,
    run_id      INTEGER,
    flow_id     INTEGER,
    step_id     INTEGER,
    value       TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ["LINEAGE_DDL"]