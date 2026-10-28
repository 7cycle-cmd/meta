"""sql.py — permit.db 存取層（授權模型）"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\permit\permit.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(";\n".join([
            SUBJECT_TYPE_DDL, SUBJECT_DDL, OBJECT_TYPE_DDL, OBJECT_DDL,
            PERMIT_TYPE_DDL, PERMIT_DDL,
        ]))
        self.conn.commit()
        self._seed_dicts()

    def _seed_dicts(self):
        """seed 字典（冪等，唔燒 sqlite_sequence）"""
        for meta, desc in DEFAULT_SUBJECT_TYPES:
            self.conn.execute(
                "INSERT INTO subject_type (subject_type, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM subject_type WHERE subject_type = ?)",
                (meta, desc, meta))
        for meta, desc in DEFAULT_OBJECT_TYPES:
            self.conn.execute(
                "INSERT INTO object_type (object_type, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM object_type WHERE object_type = ?)",
                (meta, desc, meta))
        for meta, desc in DEFAULT_PERMIT_TYPES:
            self.conn.execute(
                "INSERT INTO permit_type (permit_type, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM permit_type WHERE permit_type = ?)",
                (meta, desc, meta))
        self.conn.commit()

    # ---------- 字典 id ----------
    def subject_type_id(self, subject_type):
        r = self.conn.execute(
            "SELECT id FROM subject_type WHERE subject_type = ?",
            (subject_type,)).fetchone()
        return r["id"] if r else None

    def object_type_id(self, object_type):
        r = self.conn.execute(
            "SELECT id FROM object_type WHERE object_type = ?",
            (object_type,)).fetchone()
        return r["id"] if r else None

    def permit_type_id(self, permit_type):
        r = self.conn.execute(
            "SELECT id FROM permit_type WHERE permit_type = ?",
            (permit_type,)).fetchone()
        return r["id"] if r else None

    # ---------- subject ----------
    def add_subject(self, subject, subject_type):
        """登記一個主體（冪等：subject + type 組合）"""
        stid = self.subject_type_id(subject_type)
        if not stid:
            raise ValueError(f"subject_type '{subject_type}' 唔存在"
                             f"（permit.db subject_type 字典）")
        cur = self.conn.execute(
            "INSERT INTO subject (subject, subject_type_id)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM subject WHERE subject = ? AND subject_type_id = ?)",
            (subject, stid, subject, stid))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM subject WHERE subject = ? AND subject_type_id = ?",
            (subject, stid)).fetchone()
        return r["id"] if r else None

    def subjects(self, subject_type=None, active_only=True):
        sql = "SELECT s.*, st.subject_type FROM subject s"\
              " LEFT JOIN subject_type st ON st.id = s.subject_type_id"\
              " WHERE 1=1"
        args = []
        if subject_type:
            sql += " AND st.subject_type = ?"
            args.append(subject_type)
        if active_only:
            sql += " AND s.is_active = 1"
        sql += " ORDER BY s.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- object ----------
    def add_object(self, object, object_type):
        """登記一個目標（冪等：object + type 組合）"""
        otid = self.object_type_id(object_type)
        if not otid:
            raise ValueError(f"object_type '{object_type}' 唔存在"
                             f"（permit.db object_type 字典）")
        cur = self.conn.execute(
            "INSERT INTO object (object, object_type_id)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM object WHERE object = ? AND object_type_id = ?)",
            (object, otid, object, otid))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM object WHERE object = ? AND object_type_id = ?",
            (object, otid)).fetchone()
        return r["id"] if r else None

    def objects(self, object_type=None, active_only=True):
        sql = "SELECT o.*, ot.object_type FROM object o"\
              " LEFT JOIN object_type ot ON ot.id = o.object_type_id"\
              " WHERE 1=1"
        args = []
        if object_type:
            sql += " AND ot.object_type = ?"
            args.append(object_type)
        if active_only:
            sql += " AND o.is_active = 1"
        sql += " ORDER BY o.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- permit ----------
    def add_permit(self, subject, subject_type, permit_type, object,
                   object_type):
        """授權（冪等）：subject × permit × object

        subject    = 主體識別（例如 value.split_value.1 / terminology.module）
        permit_type = call / read / write / run / order / record ...
        object     = 目標識別（例如 terminology.word_proof）
        """
        sid = self.add_subject(subject, subject_type)
        oid = self.add_object(object, object_type)
        ptid = self.permit_type_id(permit_type)
        if not ptid:
            raise ValueError(f"permit_type '{permit_type}' 唔存在"
                             f"（permit.db permit_type 字典）")
        cur = self.conn.execute(
            "INSERT INTO permit (subject_id, permit_type_id, object_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM permit"
            "  WHERE subject_id = ? AND permit_type_id = ? AND object_id = ?)",
            (sid, ptid, oid, sid, ptid, oid))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM permit"
            " WHERE subject_id = ? AND permit_type_id = ? AND object_id = ?",
            (sid, ptid, oid)).fetchone()
        return r["id"] if r else None

    def permits(self, subject=None, permit_type=None, object=None,
                active_only=True, limit=200):
        """列出授權（可按 subject / permit_type / object 篩選）"""
        sql = ("SELECT p.id, s.subject, st.subject_type, pt.permit_type,"
               " o.object, ot.object_type, p.is_active, p.created_at"
               " FROM permit p"
               " LEFT JOIN subject s ON s.id = p.subject_id"
               " LEFT JOIN subject_type st ON st.id = s.subject_type_id"
               " LEFT JOIN permit_type pt ON pt.id = p.permit_type_id"
               " LEFT JOIN object o ON o.id = p.object_id"
               " LEFT JOIN object_type ot ON ot.id = o.object_type_id"
               " WHERE 1=1")
        args = []
        if subject:
            sql += " AND s.subject = ?"
            args.append(subject)
        if permit_type:
            sql += " AND pt.permit_type = ?"
            args.append(permit_type)
        if object:
            sql += " AND o.object = ?"
            args.append(object)
        if active_only:
            sql += " AND p.is_active = 1"
        sql += " ORDER BY p.id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def can(self, subject, subject_type, permit_type, object, object_type):
        """檢查：subject 對 object 有冇 permit（冪等）"""
        r = self.conn.execute(
            "SELECT 1 FROM permit p"
            " JOIN subject s ON s.id = p.subject_id"
            " JOIN permit_type pt ON pt.id = p.permit_type_id"
            " JOIN object o ON o.id = p.object_id"
            " WHERE s.subject = ? AND s.subject_type_id = ?"
            " AND pt.permit_type = ?"
            " AND o.object = ? AND o.object_type_id = ?"
            " AND p.is_active = 1",
            (subject, self.subject_type_id(subject_type), permit_type,
             object, self.object_type_id(object_type))).fetchone()
        return r is not None

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) c FROM permit WHERE is_active = 1").fetchone()["c"]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()