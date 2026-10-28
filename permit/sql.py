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
            IMPORT_REGISTRY_DDL, IMPORT_PERMIT_DDL,
        ]))
        self.conn.commit()
        self._seed_dicts()
        self._seed_import_permits()

    def _seed_import_permits(self):
        """seed import_permit 字典（2026-10-28：合法 import allowlist）

        1. standard library permits（唔限 module）：sqlite3 / json / os / sys。
           `import sqlite3` = 冇 from ... import *，symbols = ''。
        2. 每個 module 有權用自己嘅 .schema（module_id = 自己，symbols = 'ALL'）
        3. common.api / common.skill 等常用跨 module（module_id NULL = 全局）
        """
        # 1. 標準庫（任何 module 都准）
        for symbol, desc in DEFAULT_IMPORT_PERMITS:
            if symbol == "module.schema":
                continue
            self.conn.execute(
                "INSERT INTO import_permit (module_id, imported, symbols,"
                " description)"
                " SELECT NULL, ?, '', ? WHERE NOT EXISTS"
                " (SELECT 1 FROM import_permit WHERE module_id IS NULL"
                "  AND imported = ? AND symbols = '')",
                (symbol, "标准库: %s" % desc, symbol))
        # 2. 每個 module 自己嘅 .schema（ALL symbols 准）
        try:
            import sqlite3 as _sq
            tc = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            try:
                tc.row_factory = _sq.Row
                mods = [r["id"] for r in tc.execute(
                    "SELECT id FROM registry WHERE tree_id = 2"
                    " AND is_active = 1")]
                for mid in mods:
                    self.conn.execute(
                        "INSERT INTO import_permit"
                        " (module_id, imported, symbols, description)"
                        " SELECT ?, '.schema', 'ALL',"
                        " 'module 自己嘅 schema（顯式 import）'"
                        " WHERE NOT EXISTS"
                        " (SELECT 1 FROM import_permit"
                        "  WHERE module_id = ? AND imported = '.schema'"
                        "  AND symbols = 'ALL')",
                        (mid, mid))
            finally:
                tc.close()
        except Exception:
            pass
        self.conn.commit()

    # ---------- import_permit（2026-10-28 用戶：worker 唔可以靠 import 逃工）----------

    def check_import_permit(self, module_name, imported, symbols="*"):
        """檢查一個 module 有冇權 import 某啲 symbols（allowlist 之外 = 擋）

        module_name = taxonomy.registry.meta（module 名）
        imported    = 被 import 嘅嘢（'.schema' / 'sqlite3' / '.api'）
        symbols     = import 嘅 symbols（'*' = wildcard）

        返回 {"allowed": bool, "reason": str}
        規則：
            import_permit 有 record（module_id 對應 或 NULL = 任何 module
            + imported + symbols 符合）-> allowed
            wildcard（symbols='*'）一定要有 import_permit record
            （之前 `from .schema import *` 冇 permit -> 擋）
        """
        # module_id 反查
        module_id = None
        try:
            import sqlite3 as _sq
            c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            try:
                c.row_factory = _sq.Row
                r = c.execute(
                    "SELECT id FROM registry WHERE tree_id = 2"
                    " AND meta = ? AND is_active = 1", (module_name,)
                ).fetchone()
                module_id = r["id"] if r else None
            finally:
                c.close()
        except Exception:
            pass
        # allowlist 查：module 級 permit（module_id = 自己）或 全局（NULL）
        # 兩種形式都准：
        #   - symbols 精準 match
        #   - permit symbols = 'ALL'（module 自己 schema 全部 symbol 准）
        row = self.conn.execute(
            "SELECT id FROM import_permit"
            " WHERE imported = ? AND is_active = 1"
            "   AND ((symbols = ?) OR (symbols = 'ALL'))"
            "   AND (module_id IS NULL OR module_id = ?) LIMIT 1",
            (imported, symbols, module_id)).fetchone()
        if row:
            return {"allowed": True, "reason": f"import_permit({imported} {symbols})"}
        # wildcard 冇 permit -> 擋
        if symbols == "*":
            return {"allowed": False,
                    "reason": f"wildcard import '{imported} *' 冇 permit ——"
                              " 全部 symbol 要入表 + permit 先准"}
        return {"allowed": False,
                "reason": f"import '{imported} {symbols}' 冇 permit ——"
                          " 要喺 import_permit 表登記"}

    def register_import(self, module_name, imported, symbols="*"):
        """登記一個 import（import_registry 表，記錄實際發生嘅 import）

        **唔可以逃過 permit**：先 check_import_permit，擋住就 raise。
        返回 {"registry_id", "allowed"}
        """
        chk = self.check_import_permit(module_name, imported, symbols)
        if not chk["allowed"]:
            raise PermissionError(
                f"[permit] {module_name} 唔准 import {imported} {symbols}"
                f" —— {chk['reason']}")
        module_id = None
        try:
            import sqlite3 as _sq
            c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            try:
                c.row_factory = _sq.Row
                r = c.execute(
                    "SELECT id FROM registry WHERE tree_id = 2"
                    " AND meta = ? AND is_active = 1", (module_name,)
                ).fetchone()
                module_id = r["id"] if r else None
            finally:
                c.close()
        except Exception:
            pass
        self.conn.execute(
            "INSERT INTO import_registry (module_id, imported, symbols,"
            " is_wildcard)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM import_registry"
            "  WHERE module_id IS ? AND imported = ? AND symbols = ?)",
            (module_id, imported, symbols, int(symbols == "*"),
             module_id, imported, symbols))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM import_registry WHERE module_id IS ?"
            " AND imported = ? AND symbols = ?",
            (module_id, imported, symbols)).fetchone()
        return {"registry_id": r["id"] if r else None, "allowed": True}

    def imports(self, module_name=None, active_only=True):
        """列出 import_registry（可按 module 篩選）"""
        sql = ("SELECT ir.*, t.meta AS module"
               " FROM import_registry ir"
               " LEFT JOIN taxonomy t ON t.id = ir.module_id")
        args = []
        if active_only:
            sql += " WHERE ir.is_active = 1"
        if module_name:
            sql += " AND t.meta = ?"
            args.append(module_name)
        sql += " ORDER BY ir.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def import_permits(self, active_only=True):
        """列出 import_permit allowlist"""
        sql = "SELECT * FROM import_permit"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

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