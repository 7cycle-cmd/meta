"""schema.py — environment 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：TYPE_DDL, ENV_IDENTITY_DDL, ENV_SETTING_DDL, KEYBOARD_BUTTON_DDL, ENV_HOTKEY_DDL, ENV_SETTING_OPTION_DDL, ENV_SETTING_VALUE_DDL
（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

TYPE_DDL = """
CREATE TABLE IF NOT EXISTS type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT    NOT NULL UNIQUE,   -- computer / IDE / Browser / APP
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

ENV_IDENTITY_DDL = """
CREATE TABLE IF NOT EXISTS environment_identity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type_id     INTEGER NOT NULL,           -- type.id（computer / IDE / Browser / APP）
    name        TEXT    NOT NULL UNIQUE,    -- 實際環境名（VScode / Google Chrome ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

ENV_SETTING_DDL = """
CREATE TABLE IF NOT EXISTS environment_setting (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    setting     TEXT    NOT NULL UNIQUE,   -- permission / delegate / mode / models ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

KEYBOARD_BUTTON_DDL = """
CREATE TABLE IF NOT EXISTS keyboard_button (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    keyboard_button TEXT NOT NULL UNIQUE,  -- Ctrl / Alt / . / K / F2 / Enter / Shift
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

ENV_HOTKEY_DDL = """
CREATE TABLE IF NOT EXISTS environment_hotkey (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_id  INTEGER NOT NULL,           -- environment_setting.id
    hotkey      INTEGER NOT NULL,           -- keyboard_button.id
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (setting_id, hotkey)
);
"""

ENV_SETTING_OPTION_DDL = """
CREATE TABLE IF NOT EXISTS environment_setting_option (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    option      TEXT    NOT NULL,           -- default / autopilot / allow all ...
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (option)
);
"""

ENV_SETTING_VALUE_DDL = """
CREATE TABLE IF NOT EXISTS environment_setting_value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_id  INTEGER NOT NULL,           -- environment_setting.id
    option_id   INTEGER NOT NULL,           -- environment_setting_option.id
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (setting_id, option_id)
);
"""
__all__ = ['TYPE_DDL', 'ENV_IDENTITY_DDL', 'ENV_SETTING_DDL', 'KEYBOARD_BUTTON_DDL', 'ENV_HOTKEY_DDL', 'ENV_SETTING_OPTION_DDL', 'ENV_SETTING_VALUE_DDL']
