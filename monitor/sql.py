"""sql.py — monitor.db 存取層（全站當前計數快照）"""

import os
import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\monitor\monitor.db"
STRUCTURE_DB = r"C:\projects\meta\structure\structure.db"
TAXONOMY_DB = r"C:\projects\meta\taxonomy\taxonomy.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(CURRENT_STRUCTURE_DDL + CURRENT_TAXONOMY_DDL
                                + DB_FIELD_CHECK_DDL + SKILL_DDL
                                + SOURCE_REGISTER_DDL + SWEEP_DDL + FALLBACK_DDL
                                + REST_API_READ_DDL + REST_API_WATCH_DDL)
        self.conn.commit()
        self._sync_skills()

    # ---------- sweep 快照（2026-10-27 用戶要求） ----------
    def _real_sweep(self):
        """掃 sweep.db：target + run -> 監控狀態"""
        out = []
        try:
            src = sqlite3.connect(
                f"file:{r'C:\projects\meta\sweep\sweep.db'}?mode=ro", uri=True)
            src.row_factory = sqlite3.Row
            try:
                rows = src.execute(
                    "SELECT t.id, t.resource_id, t.plan_action,"
                    " st.meta AS status_meta,"
                    " (SELECT COUNT(*) FROM run r WHERE r.target_id = t.id)"
                    "   AS run_count,"
                    " (SELECT CASE WHEN r.status_id = 1 THEN 'approved'"
                    "              ELSE 'rejected' END"
                    "  FROM run r WHERE r.target_id = t.id"
                    "  ORDER BY r.id DESC LIMIT 1) AS last_run_status"
                    " FROM target t"
                    " LEFT JOIN status st ON st.id = t.status_id"
                    " ORDER BY t.id").fetchall()
                for r in rows:
                    out.append(dict(r))
            finally:
                src.close()
        except Exception as e:
            print(f"[monitor] sweep 掃描失敗: {e}")
        return out

    def refresh_sweep(self):
        """更新 sweep 快照（冪等：upsert）"""
        real = self._real_sweep()
        n = 0
        for r in real:
            cur = self.conn.execute(
                "INSERT INTO sweep"
                " (sweep_id, resource_id, status_meta, plan_action,"
                "  run_count, last_run_status)"
                " SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM sweep WHERE sweep_id = ?)",
                (r["id"], r.get("resource_id"), r.get("status_meta"),
                 r.get("plan_action"), r.get("run_count", 0),
                 r.get("last_run_status"), r["id"]))
            n += cur.rowcount
            self.conn.execute(
                "UPDATE sweep SET resource_id = ?, status_meta = ?,"
                " plan_action = ?, run_count = ?, last_run_status = ?,"
                " updated_at = datetime('now','localtime')"
                " WHERE sweep_id = ?"
                " AND (resource_id != ? OR status_meta != ?"
                "      OR plan_action != ? OR run_count != ?"
                "      OR last_run_status != ?)",
                (r.get("resource_id"), r.get("status_meta"),
                 r.get("plan_action"), r.get("run_count", 0),
                 r.get("last_run_status"), r["id"],
                 r.get("resource_id"), r.get("status_meta"),
                 r.get("plan_action"), r.get("run_count", 0),
                 r.get("last_run_status")))
        self.conn.commit()
        return n, len(real)

    def current_sweep(self, active_only=True):
        """列出 sweep 快照"""
        sql = "SELECT * FROM sweep WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY sweep_id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- fallback 快照（2026-10-27 用戶要求） ----------
    def _real_fallbacks(self):
        """掃全站「後備值」

        來源 1：terminology 後備 source（source.db 第一個有 official_url；
                terminology._fallback_source_id 邏輯一致，零 hardcode）
        來源 2：terminology.db source_register 表（每個詞 -> source 選擇）
        """
        out = []
        # 1. 後備 source（source.db 第一個有 official_url 嘅 source）
        try:
            sc = sqlite3.connect(
                f"file:{r'C:\projects\meta\source\source.db'}?mode=ro",
                uri=True)
            sc.row_factory = sqlite3.Row
            try:
                r = sc.execute(
                    "SELECT s.id, s.source, p.meta AS provider"
                    " FROM source s"
                    " JOIN provider p ON p.id = s.provider_id"
                    " WHERE p.official_url IS NOT NULL"
                    " AND p.official_url != ''"
                    " ORDER BY s.id LIMIT 1").fetchone()
                if r:
                    out.append({"fallback_id": r["id"],
                                "resource": "source_register",
                                "value": str(r["id"]),
                                "description":
                                    f"後備 source（{r['source']} / {r['provider']}）"})
            finally:
                sc.close()
        except Exception as e:
            print(f"[monitor] fallback source 掃描失敗: {e}")
        # 2. source_register 表（詞 -> source 選擇）每一行都係一個「指定」
        try:
            tc = sqlite3.connect(
                f"file:{r'C:\projects\meta\terminology\terminology.db'}?mode=ro",
                uri=True)
            tc.row_factory = sqlite3.Row
            try:
                for r in tc.execute(
                        "SELECT id, word, source_id, registered_by"
                        " FROM source_register WHERE is_active = 1"
                        " ORDER BY id"):
                    row = dict(r)
                    out.append({"fallback_id": row["id"],
                                "resource": "source_register." + row["word"],
                                "value": str(row["source_id"]),
                                "description":
                                    f"詞 '{row['word']}' 指定 source"
                                    f"（{row.get('registered_by')}）"})
            finally:
                tc.close()
        except Exception as e:
            print(f"[monitor] source_register 掃描失敗: {e}")
        return out

    def refresh_fallback(self):
        """更新 fallback 快照（冪等：upsert）"""
        real = self._real_fallbacks()
        n = 0
        for r in real:
            cur = self.conn.execute(
                "INSERT INTO fallback (fallback_id, resource, value, description)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM fallback WHERE resource = ? AND value = ?)",
                (r["fallback_id"], r["resource"], r["value"],
                 r["description"], r["resource"], r["value"]))
            n += cur.rowcount
            self.conn.execute(
                "UPDATE fallback SET fallback_id = ?, description = ?,"
                " updated_at = datetime('now','localtime')"
                " WHERE resource = ? AND value = ?",
                (r["fallback_id"], r["description"], r["resource"], r["value"]))
        self.conn.commit()
        return n, len(real)

    def current_fallback(self, active_only=True):
        """列出 fallback 快照"""
        sql = "SELECT * FROM fallback WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY resource, value"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- rest_api_READ（2026-10-27 用戶要求：全站 READ API 中心） ----------
    def _each_module_read_apis(self):
        """攞全站 READ API（monitor 自己掃 module/rest_api.py）

        READ 中心 = monitor（2026-10-27 用戶要求）。
        taxonomy 唔再做 API 註冊 —— monitor 自己 scan module/rest_api.py
        抽 path == "/xxx"（唔經 taxonomy，佢只做分類）。
        """
        out = []
        import re as _re
        modules = [
            d for d in os.listdir(r"C:\projects\meta")
            if os.path.isdir(os.path.join(r"C:\projects\meta", d))
            and os.path.exists(os.path.join(
                r"C:\projects\meta", d, "rest_api.py"))
        ]
        # module 名 -> taxonomy_id（taxonomy.db 查，零 hardcode）
        tid_map = {}
        try:
            tc = sqlite3.connect(
                f"file:{TAXONOMY_DB}?mode=ro", uri=True)
            tc.row_factory = sqlite3.Row
            try:
                for r in tc.execute(
                        "SELECT id, meta FROM registry"
                        " WHERE tree_id = 2 AND is_active = 1"):
                    tid_map[r["meta"]] = r["id"]
            finally:
                tc.close()
        except Exception:
            pass
        for mod in sorted(modules):
            rap = os.path.join(r"C:\projects\meta", mod, "rest_api.py")
            try:
                txt = open(rap, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for m in _re.finditer(
                    r'path\s*==\s*["\'](/[A-Za-z0-9_\-]*)["\']', txt):
                api = m.group(1)
                if api in ("/health", ""):
                    continue
                tid = tid_map.get(mod)
                if tid is None:
                    continue
                out.append({"taxonomy_id": tid, "rest_api": api})
        return out

    def refresh_rest_api_read(self):
        """更新 rest_api_READ 中心（冪等：upsert）"""
        real = self._each_module_read_apis()
        n = 0
        for r in real:
            cur = self.conn.execute(
                "INSERT INTO rest_api_READ (taxonomy_id, rest_api)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM rest_api_READ"
                "  WHERE taxonomy_id = ? AND rest_api = ?)",
                (r["taxonomy_id"], r["rest_api"],
                 r["taxonomy_id"], r["rest_api"]))
            n += cur.rowcount
        self.conn.commit()
        return n, len(real)

    def refresh_rest_api_watch(self):
        """更新 rest_api_watch（expected vs actual 比對，2026-10-27 用戶要求）

        每次掃描 = 一個快照，同上一次比對：
            ready   = 上個快照有 + 今次都有（連續出現）
            missing = 上個快照有 + 今次冇（route 消失）
            new     = 上個快照冇 + 今次有（新出現）

        返回 {"ready": n, "missing": n, "new": n, "total": n}
        """
        real = self._each_module_read_apis()
        real_keys = {(r["taxonomy_id"], r["rest_api"]) for r in real}
        # 上個快照（watch 表現有行）
        prev = {(r["taxonomy_id"], r["rest_api"])
                for r in self.conn.execute(
                    "SELECT taxonomy_id, rest_api FROM rest_api_watch"
                    " WHERE is_active = 1")}
        n_ready = n_missing = n_new = 0
        # 1. 今次有嘅：ready（之前有）或 new（之前冇）
        for tid, api in sorted(real_keys):
            if (tid, api) in prev:
                self.conn.execute(
                    "UPDATE rest_api_watch SET status = 'ready',"
                    " last_seen = datetime('now', 'localtime'),"
                    " updated_at = datetime('now', 'localtime')"
                    " WHERE taxonomy_id = ? AND rest_api = ?",
                    (tid, api))
                n_ready += 1
            else:
                self.conn.execute(
                    "INSERT INTO rest_api_watch (taxonomy_id, rest_api, status)"
                    " SELECT ?, ?, 'new' WHERE NOT EXISTS"
                    " (SELECT 1 FROM rest_api_watch"
                    "  WHERE taxonomy_id = ? AND rest_api = ?)",
                    (tid, api, tid, api))
                n_new += 1
        # 2. 上個快照有但今次冇：missing
        for tid, api in sorted(prev - real_keys):
            self.conn.execute(
                "UPDATE rest_api_watch SET status = 'missing',"
                " updated_at = datetime('now', 'localtime')"
                " WHERE taxonomy_id = ? AND rest_api = ?",
                (tid, api))
            n_missing += 1
        self.conn.commit()
        return {"ready": n_ready, "missing": n_missing, "new": n_new,
                "total": len(real_keys)}

    def current_rest_api_watch(self, status=None, active_only=True):
        """列出 REST API 就緒度監控（可按 status 篩選）"""
        sql = "SELECT * FROM rest_api_watch WHERE 1=1"
        args = []
        if status:
            sql += " AND status = ?"
            args.append(status)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY taxonomy_id, rest_api"
        rows = []
        for r in self.conn.execute(sql, args):
            d = dict(r)
            try:
                tc = sqlite3.connect(
                    f"file:{r'C:\projects\meta\taxonomy\taxonomy.db'}?mode=ro",
                    uri=True)
                tc.row_factory = sqlite3.Row
                try:
                    m = tc.execute(
                        "SELECT meta FROM registry WHERE id = ?",
                        (d["taxonomy_id"],)).fetchone()
                    d["module"] = m["meta"] if m else None
                finally:
                    tc.close()
            except Exception:
                d["module"] = None
            rows.append(d)
        return rows

    def current_rest_api_read(self, active_only=True):
        """列出 READ API 中心（JOIN taxonomy.db 攞 module 名）"""
        rows = []
        for r in self.conn.execute(
                "SELECT * FROM rest_api_READ WHERE 1=1"
                + (" AND is_active = 1" if active_only else "")
                + " ORDER BY taxonomy_id, rest_api"):
            d = dict(r)
            try:
                tc = sqlite3.connect(
                    f"file:{r'C:\projects\meta\taxonomy\taxonomy.db'}?mode=ro",
                    uri=True)
                tc.row_factory = sqlite3.Row
                try:
                    m = tc.execute(
                        "SELECT meta FROM registry WHERE id = ?",
                        (d["taxonomy_id"],)).fetchone()
                    d["module"] = m["meta"] if m else None
                finally:
                    tc.close()
            except Exception:
                d["module"] = None
            rows.append(d)
        return rows

    # ---------- current_structure（structure.db 各實體類型行數） ----------
    def _real_structure_totals(self):
        """掃 structure.db：structure_type_id -> 真實行數"""
        out = {}
        try:
            src = sqlite3.connect(f"file:{STRUCTURE_DB}?mode=ro", uri=True)
            src.row_factory = sqlite3.Row
            try:
                # structure_type 字典
                types = [r["id"] for r in src.execute(
                    "SELECT id FROM structure_type WHERE is_active = 1")]
                # 各層表：structure_type_id 對應行數
                for tid in types:
                    meta = src.execute(
                        "SELECT meta FROM structure_type WHERE id = ?",
                        (tid,)).fetchone()["meta"]
                    tbl = {
                        "package": "structure_module",
                        "file": "structure_module",
                        "db": "structure_module",
                        "root": "structure_root",
                        "db_table": "structure_db_table",
                        "db_field": "structure_db_field",
                    }.get(meta)
                    if not tbl:
                        n = 0
                    elif meta == "package":
                        n = src.execute(
                            "SELECT COUNT(*) c FROM structure_module"
                            " WHERE structure_type_id = 1").fetchone()["c"]
                    elif meta == "file":
                        n = src.execute(
                            "SELECT COUNT(*) c FROM structure_module"
                            " WHERE structure_type_id = 2").fetchone()["c"]
                    elif meta == "db":
                        n = src.execute(
                            "SELECT COUNT(*) c FROM structure_module"
                            " WHERE structure_type_id = 5").fetchone()["c"]
                    else:
                        n = src.execute(
                            f"SELECT COUNT(*) c FROM [{tbl}]").fetchone()["c"]
                    out[tid] = n
            finally:
                src.close()
        except Exception as e:
            print(f"[monitor] structure 掃描失敗: {e}")
        return out

    def refresh_structure(self):
        """更新 current_structure（冪等：upsert）"""
        real = self._real_structure_totals()
        n = 0
        for tid, total in real.items():
            cur = self.conn.execute(
                "INSERT INTO current_structure (structure_type_id, total)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM current_structure WHERE structure_type_id = ?)",
                (tid, total, tid))
            n += cur.rowcount
            self.conn.execute(
                "UPDATE current_structure SET total = ?,"
                " updated_at = datetime('now', 'localtime')"
                " WHERE structure_type_id = ? AND total != ?",
                (total, tid, total))
        self.conn.commit()
        return n, len(real)

    def current_structure(self, active_only=True):
        """列出快照（JOIN structure.db structure_type 名）"""
        rows = []
        for r in self.conn.execute(
                "SELECT * FROM current_structure WHERE 1=1"
                + (" AND is_active = 1" if active_only else "")
                + " ORDER BY structure_type_id"):
            d = dict(r)
            try:
                src = sqlite3.connect(f"file:{STRUCTURE_DB}?mode=ro", uri=True)
                src.row_factory = sqlite3.Row
                try:
                    m = src.execute(
                        "SELECT meta FROM structure_type WHERE id = ?",
                        (d["structure_type_id"],)).fetchone()
                    d["structure_type"] = m["meta"] if m else None
                finally:
                    src.close()
            except Exception:
                d["structure_type"] = None
            rows.append(d)
        return rows

    # ---------- current_taxonomy（taxonomy.db 各樹層行數） ----------
    def _real_taxonomy_totals(self):
        """掃 taxonomy.db：tree_id -> 真實行數（registry 表，2026-10-27 rename）"""
        out = {}
        try:
            src = sqlite3.connect(f"file:{TAXONOMY_DB}?mode=ro", uri=True)
            src.row_factory = sqlite3.Row
            try:
                for r in src.execute("SELECT id FROM tree WHERE is_active = 1"):
                    out[r["id"]] = src.execute(
                        "SELECT COUNT(*) c FROM registry WHERE tree_id = ?"
                        " AND is_active = 1", (r["id"],)).fetchone()["c"]
            finally:
                src.close()
        except Exception as e:
            print(f"[monitor] taxonomy 掃描失敗: {e}")
        return out

    def refresh_taxonomy(self):
        """更新 current_taxonomy（冪等：upsert）"""
        real = self._real_taxonomy_totals()
        n = 0
        for tid, total in real.items():
            cur = self.conn.execute(
                "INSERT INTO current_taxonomy (tree_id, total)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM current_taxonomy WHERE tree_id = ?)",
                (tid, total, tid))
            n += cur.rowcount
            self.conn.execute(
                "UPDATE current_taxonomy SET total = ?,"
                " updated_at = datetime('now', 'localtime')"
                " WHERE tree_id = ? AND total != ?",
                (total, tid, total))
        self.conn.commit()
        return n, len(real)

    def current_taxonomy(self, active_only=True):
        """列出快照（JOIN taxonomy.db tree 名）"""
        rows = []
        for r in self.conn.execute(
                "SELECT * FROM current_taxonomy WHERE 1=1"
                + (" AND is_active = 1" if active_only else "")
                + " ORDER BY tree_id"):
            d = dict(r)
            try:
                src = sqlite3.connect(f"file:{TAXONOMY_DB}?mode=ro", uri=True)
                src.row_factory = sqlite3.Row
                try:
                    m = src.execute(
                        "SELECT meta_key FROM tree WHERE id = ?",
                        (d["tree_id"],)).fetchone()
                    d["tree"] = m["meta_key"] if m else None
                finally:
                    src.close()
            except Exception:
                d["tree"] = None
            rows.append(d)
        return rows

    def _sync_skills(self):
        """seed skill 表（冪等，2026-10-27 用戶要求）

        skill = 技能登記：id | resource_id | value
        seed：1 | x | json_not_integer（監控 db_field_check.json 有冇非整數）
        """
        n = 0
        for sid, sval, sdesc in DEFAULT_SKILLS:
            cur = self.conn.execute(
                "INSERT INTO skill (id, resource_id, value)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM skill WHERE id = ?)",
                (sid, 0, sval, sid))
            n += cur.rowcount
        self.conn.commit()
        return n

    def skills(self, active_only=True):
        """列出技能（skill 表）"""
        sql = "SELECT * FROM skill WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- db_field_check 快照（2026-10-27 用戶要求） ----------
    def _real_field_check_flags(self):
        """掃 structure.db db_field_check：每行嘅 json 有冇「非整數」值

        返回 {db_field_check_id: json_not_integer}（1=有非整數 0=全整數）。
        """
        import json as _json
        out = {}
        try:
            src = sqlite3.connect(f"file:{STRUCTURE_DB}?mode=ro", uri=True)
            src.row_factory = sqlite3.Row
            try:
                rows = src.execute(
                    "SELECT id, json FROM db_field_check").fetchall()
                for r in rows:
                    flag = 0
                    try:
                        vals = _json.loads(r["json"])
                        if isinstance(vals, list):
                            for v in vals:
                                if isinstance(v, (int, float)) \
                                        and not isinstance(v, bool):
                                    continue
                                flag = 1  # 有非整數（bool/字串）
                                break
                    except Exception:
                        flag = 1  # json 壞 -> 當有問題
                    out[r["id"]] = flag
            finally:
                src.close()
        except Exception as e:
            print(f"[monitor] db_field_check 掃描失敗: {e}")
        return out

    def refresh_field_check(self):
        """更新 db_field_check 快照（冪等：upsert）

        每個 structure.db db_field_check 行 -> monitor.db 一行：
            db_field_check_id = structure.db db_field_check.id
            json_not_integer  = json 有冇非整數值（1=有 0=全整數）
        """
        real = self._real_field_check_flags()
        n = 0
        for ckid, flag in real.items():
            cur = self.conn.execute(
                "INSERT INTO db_field_check"
                " (db_field_check_id, json_not_integer)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM db_field_check WHERE db_field_check_id = ?)",
                (ckid, flag, ckid))
            n += cur.rowcount
            self.conn.execute(
                "UPDATE db_field_check SET json_not_integer = ?,"
                " updated_at = datetime('now', 'localtime')"
                " WHERE db_field_check_id = ? AND json_not_integer != ?",
                (flag, ckid, flag))
        self.conn.commit()
        return n, len(real)

    def current_field_check(self, active_only=True):
        """列出 db_field_check 快照（JOIN structure.db 攞表/欄位/型別）"""
        rows = []
        for r in self.conn.execute(
                "SELECT * FROM db_field_check WHERE 1=1"
                + (" AND is_active = 1" if active_only else "")
                + " ORDER BY db_field_check_id"):
            d = dict(r)
            try:
                src = sqlite3.connect(f"file:{STRUCTURE_DB}?mode=ro", uri=True)
                src.row_factory = sqlite3.Row
                try:
                    info = src.execute(
                        "SELECT c.structure_db_table_id, t.table_name,"
                        " c.structure_db_field_id, f.field_name,"
                        " c.db_field_type_id, ty.meta AS type_name,"
                        " c.total, c.json"
                        " FROM db_field_check c"
                        " LEFT JOIN structure_db_table t"
                        "   ON t.id = c.structure_db_table_id"
                        " LEFT JOIN structure_db_field f"
                        "   ON f.id = c.structure_db_field_id"
                        " LEFT JOIN db_field_type ty"
                        "   ON ty.id = c.db_field_type_id"
                        " WHERE c.id = ?", (d["db_field_check_id"],)).fetchone()
                    if info:
                        d.update(dict(info))
                finally:
                    src.close()
            except Exception:
                pass
            rows.append(d)
        return rows

    def refresh(self):
        """一次過 refresh 全部快照表"""
        n1, t1 = self.refresh_structure()
        n2, t2 = self.refresh_taxonomy()
        n3, t3 = self.refresh_field_check()
        n4, t4 = self.refresh_source_register()
        n5, t5 = self.refresh_sweep()
        n6, t6 = self.refresh_fallback()
        n7, t7 = self.refresh_rest_api_read()
        return {"structure": (n1, t1), "taxonomy": (n2, t2),
                "db_field_check": (n3, t3), "source_register": (n4, t4),
                "sweep": (n5, t5), "fallback": (n6, t6),
                "rest_api_READ": (n7, t7)}

    # ---------- source_register 快照（2026-10-27 用戶要求） ----------
    def _real_source_register(self):
        """掃 terminology 嘅 source_register（CQRS：經 API 讀，唔直接開 DB）

        2026-10-27：READ 經 terminology module 嘅 contract
        （Terminology().source_register_rows()）—— 唔可以直接連
        terminology.db（WRITE 歸 terminology，READ 都經 API，encapsulation）。
        """
        out = []
        try:
            from terminology import Terminology
            t = Terminology()
            try:
                for r in t.source_register_rows():
                    out.append(r)
            finally:
                t.close()
        except Exception as e:
            print(f"[monitor] source_register 讀取失敗（經 terminology API）: {e}")
        return out

    def refresh_source_register(self):
        """更新 source_register 快照（冪等：upsert）"""
        real = self._real_source_register()
        n = 0
        for r in real:
            cur = self.conn.execute(
                "INSERT INTO source_register"
                " (source_register_id, word, source_id, registered_by)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM source_register"
                "  WHERE source_register_id = ?)",
                (r["id"], r["word"], r["source_id"], r.get("registered_by"),
                 r["id"]))
            n += cur.rowcount
            self.conn.execute(
                "UPDATE source_register SET word = ?, source_id = ?,"
                " registered_by = ?, updated_at = datetime('now','localtime')"
                " WHERE source_register_id = ?"
                " AND (word != ? OR source_id != ?)",
                (r["word"], r["source_id"], r.get("registered_by"),
                 r["id"], r["word"], r["source_id"]))
        self.conn.commit()
        return n, len(real)

    def current_source_register(self, active_only=True):
        """列出 source_register 快照（JOIN source.db 攞來源名）"""
        rows = []
        for r in self.conn.execute(
                "SELECT * FROM source_register WHERE 1=1"
                + (" AND is_active = 1" if active_only else "")
                + " ORDER BY source_register_id"):
            d = dict(r)
            try:
                src = sqlite3.connect(
                    f"file:{r'C:\projects\meta\source\source.db'}?mode=ro",
                    uri=True)
                src.row_factory = sqlite3.Row
                try:
                    s = src.execute(
                        "SELECT s.source, p.meta AS provider, p.official_url"
                        " FROM source s LEFT JOIN provider p"
                        "  ON p.id = s.provider_id WHERE s.id = ?",
                        (d["source_id"],)).fetchone()
                    if s:
                        d.update(dict(s))
                finally:
                    src.close()
            except Exception:
                pass
            rows.append(d)
        return rows

    def close(self):
        self.conn.close()
