"""schema.py — sweep 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：ACTION_DDL, STATUS_DDL, RESOURCE_TYPE_DDL, PHYSICAL_TYPE_DDL, TARGET_DDL, MISSION_DDL, EVIDENCE_DDL, PROOF_DDL, MISSION_LOG_DDL
（8 檔標準：__init__/function/api/route/schema/sql/registry/rest_api）
"""

ACTION_DDL = """
CREATE TABLE IF NOT EXISTS action (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- DROP / KEEP / RENAME / ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

STATUS_DDL = """
CREATE TABLE IF NOT EXISTS status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- empty / dead / legacy / active / ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

RESOURCE_TYPE_DDL = ""

PHYSICAL_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS physical_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- package / folder / coding / ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

TARGET_DDL = """
CREATE TABLE IF NOT EXISTS target (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id       TEXT    NOT NULL,   -- 資源識別（例如 taxonomy.db.module）
    identity_id       TEXT,                -- 身份（taxonomy_id + resource_id）
    status_id         INTEGER,             -- FK -> status.id（empty / dead / legacy / active）
    resource_type_id  INTEGER,             -- FK -> resource_type.id（db_table / db_field / ...）
    physical_type_id  INTEGER,             -- FK -> physical_type.id（package / folder / coding）
    source_version_id INTEGER,             -- version.db version.id（由邊版嚟，v1.5.0）
    target_version_id INTEGER,             -- version.db version.id（去邊版，v1.5.0）
    plan_action       TEXT,                -- upgrade / rebuild / drop / keep（v1.5.0）
    plan_status       TEXT    NOT NULL DEFAULT 'none',  -- none / pending / done / rejected（v1.5.0）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

MISSION_DDL = """
CREATE TABLE IF NOT EXISTS mission (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id   INTEGER NOT NULL,          -- FK -> target.id
    action_id   INTEGER NOT NULL,          -- FK -> action.id（DROP / KEEP）
    flow_id     INTEGER,                   -- flow.db flow.id（邊個 flow 執行）
    step_id     INTEGER,                   -- code_gen.db step.id（邊個 step 執行）
    task_id     INTEGER,                   -- task.db task.id（邊個 task 觸發）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (target_id, action_id)
);
"""

MISSION_RUN_DDL = """
CREATE TABLE IF NOT EXISTS mission_run (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id     INTEGER NOT NULL,       -- FK -> mission.id
    status_id      INTEGER,                -- common.db status.id（pass/fail/NA）
    schema_run_id  INTEGER,                -- schema.db schema_run.id（授權）
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

EVIDENCE_DDL = """
CREATE TABLE IF NOT EXISTS evidence (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id   INTEGER NOT NULL,          -- FK -> target.id
    proof_run_id  INTEGER,                 -- proof.db proof_run.id（證明嘅證據，by_id）
    verify_run_id INTEGER,                 -- verify.db verify_run.id（驗證嘅證據，by_id）
    collected_at TEXT   NOT NULL DEFAULT (datetime('now', 'localtime')),
    detail      TEXT,                       -- 收集到嘅證據（例如 0 行 / NULL 值）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

PROOF_DDL = """
CREATE TABLE IF NOT EXISTS proof (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id INTEGER NOT NULL,          -- FK -> evidence.id
    mission_id  INTEGER,                    -- FK -> mission.id（邊個任務用咗呢個證明）
    proof       TEXT,                       -- 證明內容
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

MISSION_LOG_DDL = """
CREATE TABLE IF NOT EXISTS mission_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id  INTEGER NOT NULL,          -- FK -> mission.id
    run_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    status      TEXT    NOT NULL,          -- success / failed / skipped
    detail      TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# ============ flow / condition / step / run（2026-10-27 用戶要求：sweep 加 flow） ============
# 跟 terminology pattern —— 判斷入表（condition），執行有證明（run）。
# 每個 target 嘅狀態判斷（empty/dead/legacy/orphan/active）變 condition，
# sweep_prove flow 自動行，寫 run + evidence。

CONDITION_DDL = """
CREATE TABLE IF NOT EXISTS condition (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta       TEXT    NOT NULL UNIQUE,   -- sweep_empty / sweep_dead / sweep_legacy / sweep_orphan / sweep_active
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

FLOW_DDL = """
CREATE TABLE IF NOT EXISTS flow (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name  TEXT    NOT NULL UNIQUE,   -- sweep_prove
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

STEP_DDL = """
CREATE TABLE IF NOT EXISTS step (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id        INTEGER NOT NULL,       -- flow.id
    condition_id   INTEGER NOT NULL,        -- condition.id
    seq_id         INTEGER NOT NULL,        -- 次序
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, seq_id)
);
"""

RUN_DDL = """
CREATE TABLE IF NOT EXISTS run (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id     INTEGER NOT NULL,           -- flow.id
    target_id   INTEGER NOT NULL,           -- sweep target.id（證明邊個目標）
    status_id   INTEGER NOT NULL,           -- 1=approved 2=rejected（boolean）
    step_id     INTEGER,                    -- 停步（全 PASS = 最後一步）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# sweep 條件種子：狀態判斷（2026-10-27 用戶要求）
# sweep_unproven = 有實體但冇證明記錄（worker build 咗但忘記記錄，2026-10-27b）
DEFAULT_CONDITIONS = [
    "sweep_empty",
    "sweep_dead",
    "sweep_legacy",
    "sweep_orphan",
    "sweep_unproven",
    "sweep_active",
]

__all__ = ['ACTION_DDL', 'STATUS_DDL', 'RESOURCE_TYPE_DDL', 'PHYSICAL_TYPE_DDL',
           'TARGET_DDL', 'MISSION_DDL', 'MISSION_RUN_DDL', 'EVIDENCE_DDL',
           'PROOF_DDL', 'MISSION_LOG_DDL',
           'CONDITION_DDL', 'FLOW_DDL', 'STEP_DDL', 'RUN_DDL',
           'DEFAULT_CONDITIONS']
