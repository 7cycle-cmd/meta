"""schema.py — schema 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：SCHEMA_CHECK_DDL, SCHEMA_RUN_DDL
（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

SCHEMA_CHECK_DDL = """
CREATE TABLE IF NOT EXISTS schema_check (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL,          -- task.db task.id（邊個 task 要檢查）
    check_name  TEXT    NOT NULL,          -- 檢查名（api_exists / value_active ...）
    check_type  TEXT    NOT NULL,          -- 檢查類型（api_exists / value_active / value_broken / value_missing）
    passed      INTEGER NOT NULL,          -- 1 = 通過，0 = 失敗
    detail      TEXT,                      -- 詳細（例如 10/10 api 存在）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

SCHEMA_RUN_DDL = """
CREATE TABLE IF NOT EXISTS schema_run (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL,          -- task.db task.id
    total       INTEGER NOT NULL,          -- 總檢查數
    passed      INTEGER NOT NULL,          -- 通過數
    failed      INTEGER NOT NULL,          -- 失敗數
    status      TEXT    NOT NULL,          -- ready / not_ready
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""
__all__ = ['SCHEMA_CHECK_DDL', 'SCHEMA_RUN_DDL']
