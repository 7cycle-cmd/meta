-- schema dump: environment.db
-- generated : 2026-10-27T15:47:40
-- objects   : 10（table=10）

-- [table] environment_hotkey
CREATE TABLE environment_hotkey (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_id  INTEGER NOT NULL,           -- environment_setting.id
    hotkey      INTEGER NOT NULL,           -- keyboard_button.id
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (setting_id, hotkey)
);

-- [table] environment_identity
CREATE TABLE environment_identity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type_id     INTEGER NOT NULL,           -- type.id（computer / IDE / Browser / APP）
    name        TEXT    NOT NULL UNIQUE,    -- 實際環境名（VScode / Google Chrome ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] environment_setting
CREATE TABLE environment_setting (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    setting     TEXT    NOT NULL UNIQUE,   -- permission / delegate / mode / models ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] environment_setting_option
CREATE TABLE environment_setting_option (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    option      TEXT    NOT NULL,           -- default / autopilot / allow all ...
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (option)
);

-- [table] environment_setting_value
CREATE TABLE environment_setting_value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_id  INTEGER NOT NULL,           -- environment_setting.id
    option_id   INTEGER NOT NULL,           -- environment_setting_option.id
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (setting_id, option_id)
);

-- [table] keyboard_button
CREATE TABLE keyboard_button (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    keyboard_button TEXT NOT NULL UNIQUE,  -- Ctrl / Alt / . / K / F2 / Enter / Shift
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] registry
CREATE TABLE registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT, meta TEXT NOT NULL UNIQUE, description TEXT, is_active BOOLEAN NOT NULL CHECK (is_active IN (0,1)) DEFAULT 1, created_at TEXT DEFAULT (datetime('now', 'localtime')), updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- [table] skill
CREATE TABLE skill (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_key    TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- [table] type
CREATE TABLE type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT    NOT NULL UNIQUE,   -- computer / IDE / Browser / APP
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
