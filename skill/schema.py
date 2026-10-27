"""skill module 權威 DDL。"""

REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    value     TEXT    NOT NULL,
    UNIQUE (module_id, value)
);
"""

MODULE_SKILL_DDL = """
CREATE TABLE IF NOT EXISTS module_skill (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id INTEGER NOT NULL,
    flow_id  INTEGER NOT NULL,
    value_id INTEGER NOT NULL,
    UNIQUE (skill_id, flow_id, value_id)
);
"""

__all__ = ["REGISTRY_DDL", "MODULE_SKILL_DDL"]
