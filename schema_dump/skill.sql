-- schema dump: skill.db
-- generated : 2026-10-27T15:47:40
-- objects   : 3（table=3）

-- [table] module_skill
CREATE TABLE module_skill (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id INTEGER NOT NULL,
    flow_id  INTEGER NOT NULL,
    value_id INTEGER NOT NULL,
    UNIQUE (skill_id, flow_id, value_id)
);

-- [table] registry
CREATE TABLE registry (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    value     TEXT    NOT NULL,
    UNIQUE (module_id, value)
);

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);
