"""schema.py — value 權威 DDL 入口（唯一 schema 來源）

value.db 存放「值資產」：
    value         值字典（id | value | taxonomy_id）
    split_total   拆分總表（value_id | split_total | json）
    split_value   拆分值表（value_id | split_total_id | split_value | common.seq_id | json）
    terminology   前端→terminology 授權（terminology_id | split_value_id）
"""

# value 表：值資產（2026-10-27 用戶要求：由 terminology 升做獨立 module）
#   一行 = 一個值（asset）
#   value       = 值本身（data / build / 5W2H ...）
#   taxonomy_id = taxonomy.registry.id（邊個 module 登記，trace 用）
#   permit_id   = permit.db permit.id（呢個值嘅授權，2026-10-28b 方案 B）
#                 一跳直達：value → permit_id → permit.db 確認有冇權
VALUE_DDL = """
CREATE TABLE IF NOT EXISTS value (
    id          INTEGER PRIMARY KEY,   -- 唔用 AUTOINCREMENT（2026-10-28：防跳號，新 id = MAX+1）
    value       TEXT,
    taxonomy_id INTEGER,             -- taxonomy.registry.id（邊個 module 登記）
    permit_id   INTEGER,             -- permit.db permit.id（授權）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# split_total 表：值拆分總覽（2026-10-28 用戶要求）
#   一行 = 一個值嘅一次拆分（幾多份 + 拆出嚟嘅 json 快照）
#   value_id     = value.id（邊個值被拆）
#   split_total  = 拆成幾多份
#   json         = 拆分結果快照（["split_value":"hello, seq=1"; ...]）
SPLIT_TOTAL_DDL = """
CREATE TABLE IF NOT EXISTS split_total (
    id          INTEGER PRIMARY KEY,   -- 唔用 AUTOINCREMENT（2026-10-28：防跳號）
    value_id    INTEGER NOT NULL,      -- value.id（邊個值被拆）
    split_total INTEGER NOT NULL,       -- 拆成幾多份
    json        TEXT,                  -- 拆分結果快照
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# split_value 表：拆分值（2026-10-28 用戶要求）
#   一行 = 一個拆分出嚟嘅值
#   value_id         = value.id（原值）
#   split_total_id   = split_total.id（今次拆分）
#   split_value      = 拆出嚟嘅值（hello / world / 123）
#   seq_id           = common.seq.id（次序，由 common.db 字典）
#   json             = 該份嘅快照
SPLIT_VALUE_DDL = """
CREATE TABLE IF NOT EXISTS split_value (
    id              INTEGER PRIMARY KEY,   -- 唔用 AUTOINCREMENT（2026-10-28：防跳號）
    value_id        INTEGER NOT NULL,      -- value.id（原值）
    split_total_id  INTEGER NOT NULL,      -- split_total.id（今次拆分）
    split_value     TEXT    NOT NULL,      -- 拆出嚟嘅值
    seq_id          INTEGER NOT NULL,      -- common.seq.id（次序）
    json            TEXT,                  -- 該份快照
    is_active       BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# terminology 表：前端 → terminology 授權（2026-10-28 用戶要求）
#   一行 = 一個「有權 call terminology」嘅 split_value
#   terminology_id = terminology.api/route id（授權標記）
#   split_value_id = split_value.id（邊個拆分值有權）
#   permit_id      = permit.db permit.id（2026-10-28b 方案 B：直接連授權）
# 用法：REST_API_WRITE -> 127.0.0.1:8500/word-proof?value=<value>&token=terminology.api
#       -> <value> = split_value 對應嘅值（有 terminology_id = 有權工作）
TERMINOLOGY_DDL = """
CREATE TABLE IF NOT EXISTS terminology (
    id              INTEGER PRIMARY KEY,   -- 唔用 AUTOINCREMENT（2026-10-28：防跳號）
    terminology_id  INTEGER NOT NULL,      -- terminology.api id（授權標記）
    split_value_id  INTEGER NOT NULL,      -- split_value.id（邊個拆分值有權）
    permit_id       INTEGER,              -- permit.db permit.id（2026-10-28b）
    is_active       BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (terminology_id, split_value_id)
);
"""

__all__ = ["VALUE_DDL", "SPLIT_TOTAL_DDL", "SPLIT_VALUE_DDL",
           "TERMINOLOGY_DDL"]