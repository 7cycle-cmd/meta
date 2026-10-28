"""schema.py — permit 權威 DDL 入口（唯一 schema 來源）

permit.db 存放「授權」：
    permit       授權記錄（subject_id | permit_type_id | object_id）
    permit_type  許可類型字典（call / read / write / run ...）
    subject      主體（subject | subject_type_id）
    subject_type 主體類型字典（module / split_value / worker ...）
    object       目標（object | object_type_id）
    object_type  目標類型字典（terminology / rest_api / flow ...）

2026-10-28（用戶要求）：
    permit = subject × permit × object（統一授權模型）
    取代分散式：value.terminology / role / rule / tool 嘅授權維度
"""

# subject_type 表：主體類型字典
SUBJECT_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS subject_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_type TEXT NOT NULL UNIQUE,   -- module / split_value / worker / tool ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 預設主體類型種子（冪等）
DEFAULT_SUBJECT_TYPES = [
    ("module",      "taxonomy.registry.id（module）"),
    ("split_value", "value.split_value.id（拆分值）"),
    ("worker",      "worker.id（LLM 代理）"),
    ("tool",        "tool.registry.id（工具）"),
]

# subject 表：主體
SUBJECT_DDL = """
CREATE TABLE IF NOT EXISTS subject (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subject         TEXT    NOT NULL,      -- 主體識別（例如 value.split_value.1）
    subject_type_id INTEGER NOT NULL,      -- subject_type.id
    is_active       BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (subject, subject_type_id)
);
"""

# object_type 表：目標類型字典
OBJECT_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS object_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    object_type TEXT NOT NULL UNIQUE,    -- terminology / rest_api / flow / step ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 預設目標類型種子（冪等）
DEFAULT_OBJECT_TYPES = [
    ("terminology",  "terminology.api（word-proof 等）"),
    ("rest_api",     "REST API"),
    ("flow",         "terminology flow"),
    ("step",         "terminology step"),
    ("value",        "value.id（值資產）"),
    ("tool",         "tool.registry.id"),
]

# object 表：目標
OBJECT_DDL = """
CREATE TABLE IF NOT EXISTS object (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    object        TEXT    NOT NULL,      -- 目標識別（例如 terminology.word_proof）
    object_type_id INTEGER NOT NULL,     -- object_type.id
    is_active     BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (object, object_type_id)
);
"""

# permit_type 表：許可類型字典
PERMIT_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS permit_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    permit_type TEXT NOT NULL UNIQUE,    -- call / read / write / run / execute ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 預設許可類型種子（冪等）
DEFAULT_PERMIT_TYPES = [
    ("call",    "呼叫（例如 call terminology / REST API）"),
    ("read",    "讀"),
    ("write",   "寫"),
    ("run",     "執行（flow / run）"),
    ("order",   "落 order"),
    ("record",  "記錄（lineage）"),
]

# permit 表：授權記錄（2026-10-28 用戶要求）
#   permit = subject × permit × object
#   subject_id    = subject.id（邊個有權）
#   permit_type_id = permit_type.id（有咩許可）
#   object_id     = object.id（對邊個目標）
PERMIT_DDL = """
CREATE TABLE IF NOT EXISTS permit (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id     INTEGER NOT NULL,      -- subject.id
    permit_type_id INTEGER NOT NULL,      -- permit_type.id
    object_id      INTEGER NOT NULL,      -- object.id
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (subject_id, permit_type_id, object_id)
);
"""

__all__ = ["SUBJECT_TYPE_DDL", "DEFAULT_SUBJECT_TYPES", "SUBJECT_DDL",
           "OBJECT_TYPE_DDL", "DEFAULT_OBJECT_TYPES", "OBJECT_DDL",
           "PERMIT_TYPE_DDL", "DEFAULT_PERMIT_TYPES", "PERMIT_DDL"]