"""sql.py — environment.db 存取層（執行環境：類型 + 實際環境 + 設定 + 熱鍵）"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\environment\environment.db"








# seed 資料（跟用戶設計）
DEFAULT_TYPES = ["computer", "IDE", "Browser", "APP"]
DEFAULT_ENVS = [
    (1, "DESKTOP-csdcsdcs"),
    (2, "VScode"),
    (3, "Google Chrome"),
    (3, "Microsoft Edge"),
    (4, "OpenClaw"),
]
DEFAULT_SETTINGS = [
    "permission", "delegate", "mode", "models", "efforts level",
    "session rename", "send to New chat",
]
DEFAULT_BUTTONS = ["Ctrl", "Alt", ".", "K", "F2", "Enter", "Shift"]
DEFAULT_OPTIONS = [
    "default", "autopilot", "allow all", "Local", "Copilot", "Cloud",
    "Claude", "Codex", "Ask", "agent", "Plan",
    "DeepSeek V4 Flash 0731", "DeepSeek V4 .1 Flash",
    "none", "Low", "High", "Max",
]
# environment_hotkey（setting_id -> keyboard_button body）
DEFAULT_HOTKEYS = [
    (1, 1), (1, 2), (1, 4),   # permission: Ctrl Alt K
    (2, 1), (2, 3),           # delegate: Ctrl .
    (3, 1), (3, 2), (3, 3),   # mode: Ctrl Alt .
    (6, 5),                   # session rename: F2
    (7, 1), (7, 7), (7, 6),   # send to New chat: Ctrl Shift Enter
]
# environment_setting_value（setting_id -> option_id，修正：唔重複）
DEFAULT_VALUES = [
    (1, 1), (1, 2), (1, 3),      # permission: default / autopilot / allow all
    (2, 4), (2, 5), (2, 6), (2, 7), (2, 8),  # delegate: Local / Copilot / Cloud / Claude / Codex
    (3, 9), (3, 10), (3, 11),    # mode: Ask / agent / Plan
    (4, 12), (4, 13),            # models: DeepSeek V4 Flash 0731 / DeepSeek V4 .1 Flash
    (5, 14), (5, 15), (5, 16), (5, 17),  # efforts level: none / Low / High / Max
]


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            TYPE_DDL + ENV_IDENTITY_DDL + ENV_SETTING_DDL
            + KEYBOARD_BUTTON_DDL + ENV_HOTKEY_DDL
            + ENV_SETTING_OPTION_DDL + ENV_SETTING_VALUE_DDL)
        self.conn.commit()
        self._seed()

    def _seed(self):
        for t in DEFAULT_TYPES:
            self.conn.execute(
                "INSERT OR IGNORE INTO type (type) VALUES (?)", (t,))
        for tid, name in DEFAULT_ENVS:
            self.conn.execute(
                "INSERT OR IGNORE INTO environment_identity (type_id, name)"
                " VALUES (?, ?)", (tid, name))
        for s in DEFAULT_SETTINGS:
            self.conn.execute(
                "INSERT OR IGNORE INTO environment_setting (setting)"
                " VALUES (?)", (s,))
        for b in DEFAULT_BUTTONS:
            self.conn.execute(
                "INSERT OR IGNORE INTO keyboard_button (keyboard_button)"
                " VALUES (?)", (b,))
        for o in DEFAULT_OPTIONS:
            self.conn.execute(
                "INSERT OR IGNORE INTO environment_setting_option (option)"
                " VALUES (?)", (o,))
        for sid, kid in DEFAULT_HOTKEYS:
            self.conn.execute(
                "INSERT OR IGNORE INTO environment_hotkey (setting_id, hotkey)"
                " VALUES (?, ?)", (sid, kid))
        for sid, oid in DEFAULT_VALUES:
            self.conn.execute(
                "INSERT OR IGNORE INTO environment_setting_value (setting_id, option_id)"
                " VALUES (?, ?)", (sid, oid))
        self.conn.commit()

    # ---------- type ----------
    def types(self, active_only=True):
        sql = "SELECT * FROM type WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- environment_identity ----------
    def identities(self, type_id=None, active_only=True):
        sql = """SELECT ei.id, ei.type_id, t.type AS type_name, ei.name
                 FROM environment_identity ei
                 JOIN type t ON t.id = ei.type_id
                 WHERE 1=1"""
        args = ()
        if type_id:
            sql += " AND ei.type_id = ?"
            args = (type_id,)
        if active_only:
            sql += " AND ei.is_active = 1"
        sql += " ORDER BY ei.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- settings ----------
    def settings(self, active_only=True):
        sql = "SELECT * FROM environment_setting WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def hotkeys(self, setting_id=None, active_only=True):
        sql = """SELECT eh.id, eh.setting_id, s.setting,
                        eh.hotkey, kb.keyboard_button
                 FROM environment_hotkey eh
                 JOIN environment_setting s ON s.id = eh.setting_id
                 JOIN keyboard_button kb ON kb.id = eh.hotkey
                 WHERE 1=1"""
        args = ()
        if setting_id:
            sql += " AND eh.setting_id = ?"
            args = (setting_id,)
        if active_only:
            sql += " AND eh.is_active = 1"
        sql += " ORDER BY eh.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def buttons(self, active_only=True):
        sql = "SELECT * FROM keyboard_button WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- setting options / values ----------
    def options(self, active_only=True):
        sql = "SELECT * FROM environment_setting_option WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def setting_values(self, setting_id=None, active_only=True):
        sql = """SELECT v.id, v.setting_id, s.setting,
                        v.option_id, o.option
                 FROM environment_setting_value v
                 JOIN environment_setting s ON s.id = v.setting_id
                 JOIN environment_setting_option o ON o.id = v.option_id
                 WHERE 1=1"""
        args = ()
        if setting_id:
            sql += " AND v.setting_id = ?"
            args = (setting_id,)
        if active_only:
            sql += " AND v.is_active = 1"
        sql += " ORDER BY v.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
