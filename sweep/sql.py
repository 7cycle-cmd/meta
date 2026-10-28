"""sql.py — sweep.db 存取層（完整資料模型）

sweep = module（清理能力）
    字典表：
        action          動作（DROP / KEEP / RENAME / ...）
        status          狀態（empty / dead / legacy / active / ...）
        resource_type   資源類型（db_table / db_field / function / api / route / SQL / package / module / channel / skill）
        physical_type   實體類型（package / folder / coding / ...）
    核心表：
        target          清理目標（resource_id | identity_id | status_id | resource_type_id | physical_type_id）
        mission         任務（target_id | action_id | is_active）
    證據鏈：
        evidence        收集證據（collect evidence）
        proof           證明（proof）
        mission_log     任務執行記錄（apply mission）
"""

import os as _os
import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\sweep\sweep.db"

# ---------------- 字典表 ----------------


# sweep.target.resource_type_id 而家指向 resource.db type.id（唔再係本地表）



# ---------------- 核心表 ----------------


# ---------------- 證據鏈 ----------------




class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            ACTION_DDL + STATUS_DDL + RESOURCE_TYPE_DDL + PHYSICAL_TYPE_DDL
            + TARGET_DDL + MISSION_DDL + MISSION_RUN_DDL
            + EVIDENCE_DDL + PROOF_DDL + MISSION_LOG_DDL
            + CONDITION_DDL + FLOW_DDL + STEP_DDL + RUN_DDL)
        self.conn.commit()
        # 2026-10-22：資源類型唯一權威 = resource.db type 表
        #   target.resource_type_id 指向 resource.db type.id
        #   resource.db type 由 resource module 管理（白名單 + description）
        #   呢度 ATTACH resource.db 嚟 JOIN / 查 type
        # 2026-10-28：resource module 未重建（空殼）-> 唔 ATTACH（避免自動建空檔）
        import os as _os
        _RES_DB = r"C:\projects\meta\resource\resource.db"
        self._res_attached = False
        if _os.path.exists(_RES_DB):
            self.conn.execute("ATTACH DATABASE ? AS resdb", (_RES_DB,))
            self._res_attached = True
        # resource_type 重複表已移除（2026-10-22）
        # 如果 live DB 仍然存在舊表 -> 刪除（target.resource_type_id 已遷移）
        tables = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "resource_type" in tables:
            try:
                if _res_attached:
                    # 遷移：舊 sweep.resource_type.meta -> resource.db type.id
                    rows = self.conn.execute(
                        "SELECT t.id AS tid, rt.meta AS old_meta"
                        " FROM target t JOIN resource_type rt"
                        "   ON rt.id = t.resource_type_id"
                        " WHERE t.resource_type_id IS NOT NULL").fetchall()
                    for r in rows:
                        m = self.conn.execute(
                            "SELECT id FROM resdb.type WHERE type = ?",
                            (r["old_meta"],)).fetchone()
                        if m:
                            self.conn.execute(
                                "UPDATE target SET resource_type_id = ?"
                                " WHERE id = ?", (m["id"], r["tid"]))
                        else:
                            self.conn.execute(
                                "UPDATE target SET resource_type_id = NULL"
                                " WHERE id = ?", (r["tid"],))
                    self.conn.commit()
            except sqlite3.Error:
                pass
            self.conn.execute("DROP TABLE resource_type")
            self.conn.commit()
        self._migrate_mission()
        self._migrate_evidence()
        self._migrate_target()
        self._seed_dicts()
        self._seed_flow()

    def _migrate_target(self):
        """舊版 target 升級：加 plan / version 欄（保留資料）"""
        cols = [c[1] for c in self.conn.execute("PRAGMA table_info('target')")]
        for col in ("source_version_id", "target_version_id", "plan_action", "plan_status"):
            if col not in cols:
                if col == "plan_status":
                    self.conn.execute(
                        "ALTER TABLE target ADD COLUMN plan_status"
                        " TEXT NOT NULL DEFAULT 'none'")
                else:
                    self.conn.execute(
                        f"ALTER TABLE target ADD COLUMN {col} INTEGER"
                        if col.endswith("_id") else
                        f"ALTER TABLE target ADD COLUMN {col} TEXT")
        self.conn.commit()

    def _migrate_evidence(self):
        """舊版 evidence 表升級：缺 proof_run_id / verify_run_id 就加（保留資料）"""
        cols = [c[1] for c in self.conn.execute("PRAGMA table_info('evidence')")]
        for col in ("proof_run_id", "verify_run_id"):
            if col not in cols:
                self.conn.execute(
                    f"ALTER TABLE evidence ADD COLUMN {col} INTEGER")
        self.conn.commit()

    def _migrate_mission(self):
        """舊版 mission 表升級：缺 flow_id / step_id / task_id 就加（保留資料）"""
        cols = [c[1] for c in self.conn.execute("PRAGMA table_info('mission')")]
        for col in ("flow_id", "step_id", "task_id"):
            if col not in cols:
                self.conn.execute(
                    f"ALTER TABLE mission ADD COLUMN {col} INTEGER")
        self.conn.commit()

    def _seed_dicts(self):
        """預填字典表"""
        for meta, desc in [
            ("DROP", "刪除"),
            ("KEEP", "保留"),
            ("RENAME", "改名"),
            ("REPLACE", "替換"),
            ("MERGE", "合併"),
            ("UPGRADE", "原地升級（ALTER 套新版）"),
            ("REBUILD", "刪咗重建（DROP + CREATE）"),
        ]:
            self.conn.execute(
                "INSERT OR IGNORE INTO action (meta, description) VALUES (?, ?)",
                (meta, desc))
        for meta, desc in [
            ("empty", "空（0 行）"),
            ("dead", "死（可以清理）"),
            ("legacy", "遺留（保留參考）"),
            ("active", "啟用"),
        ]:
            self.conn.execute(
                "INSERT OR IGNORE INTO status (meta, description) VALUES (?, ?)",
                (meta, desc))
        # resource_type 已移除（2026-10-22）：資源類型由 resource.db type 管
        for meta in ["package", "folder", "coding"]:
            self.conn.execute(
                "INSERT OR IGNORE INTO physical_type (meta) VALUES (?)", (meta,))
        self.conn.commit()

    def _seed_flow(self):
        """seed sweep_prove flow + condition + step（2026-10-27 用戶要求）

        condition：sweep_empty / sweep_dead / sweep_legacy / sweep_orphan / sweep_active
        flow：sweep_prove（5 步，每 condition 一步）
        冪等（UNIQUE + WHERE NOT EXISTS）。
        """
        # 1. condition seed
        for cmeta in DEFAULT_CONDITIONS:
            self.conn.execute(
                "INSERT INTO condition (meta)"
                " SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM condition WHERE meta = ?)",
                (cmeta, cmeta))
        # 2. flow seed
        self.conn.execute(
            "INSERT INTO flow (flow_name)"
            " SELECT 'sweep_prove' WHERE NOT EXISTS"
            " (SELECT 1 FROM flow WHERE flow_name = 'sweep_prove')")
        self.conn.commit()
        # 3. step seed（flow_id + seq_id UNIQUE -> 冪等）
        frow = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = 'sweep_prove'").fetchone()
        if not frow:
            return
        fid = frow["id"]
        for seq, cmeta in enumerate(DEFAULT_CONDITIONS, start=1):
            crow = self.conn.execute(
                "SELECT id FROM condition WHERE meta = ?", (cmeta,)).fetchone()
            if not crow:
                continue
            self.conn.execute(
                "INSERT INTO step (flow_id, condition_id, seq_id)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?)",
                (fid, crow["id"], seq, fid, seq))
        self.conn.commit()

    def _condition_judge(self, condition_meta, target_row):
        """一個 sweep condition 嘅判斷（由 target 真實資料計）

        target_row = sweep target 行（dict 或 Row，含 resource_id + status_id）
        返回 1=PASS 0=FAIL。

        判斷（同 Sweep API 一致）：
            sweep_empty    -> target 對應張表 0 行
            sweep_dead     -> status = dead（孤島/冇連接）
            sweep_legacy   -> status = legacy（有資料但冇人引用）
            sweep_orphan   -> status = orphan（孤兒）
            sweep_unproven -> 有實體但冇證明記錄（worker build 咗但忘記記錄）
            sweep_active   -> status = active（有人引用 + 有資料）
        """
        meta = condition_meta

        def _row_status():
            # target.status_id -> status.meta
            r = self.conn.execute(
                "SELECT st.meta FROM status st"
                " WHERE st.id = ?", (target_row["status_id"],)).fetchone()
            return r["meta"] if r else None

        if meta == "sweep_empty":
            return 1 if target_row.get("row_count") == 0 else 0
        elif meta == "sweep_dead":
            return 1 if _row_status() == "dead" else 0
        elif meta == "sweep_legacy":
            return 1 if _row_status() == "legacy" else 0
        elif meta == "sweep_orphan":
            return 1 if _row_status() == "orphan" else 0
        elif meta == "sweep_unproven":
            # 有實體（target 存在）但冇證明記錄：
            #   terminology.run / evidence / lineage 都冇呢個資源嘅記錄
            #   = worker build 咗但忘記記錄（冇 run_id = 冇證明鏈）
            return 1 if self._has_no_proof(target_row) else 0
        elif meta == "sweep_active":
            return 1 if _row_status() == "active" else 0
        return 0

    def _has_no_proof(self, target_row):
        """一個 target 有冇任何證明記錄（run / evidence / lineage）

        冇 = worker build 咗但忘記記錄（unproven）。
        查詢（CQRS：經各 module 自己 DB）：
            terminology.db run / evidence（value_id 對應）
            lineage.db lineage（value_id 對應）
        """
        # target.resource_id 格式：例如 "taxonomy.db.module" / "value.db.value"
        # 由 resource_id 攞 value 名（最後一段）
        rid = str(target_row.get("resource_id") or "")
        value_name = rid.split(".")[-1] if "." in rid else rid
        if not value_name:
            return True  # 冇資源名 = 冇得證明
        # 1. value.db 有冇呢個值（冇 = 連值都未登記）
        try:
            import sqlite3 as _sq
            vc = _sq.connect(r"C:\projects\meta\value\value.db")
            vc.row_factory = _sq.Row
            try:
                vrow = vc.execute(
                    "SELECT id FROM value WHERE value = ? AND is_active = 1",
                    (value_name,)).fetchone()
            finally:
                vc.close()
        except Exception:
            vrow = None
        if not vrow:
            return True  # 值都未登記 = 冇證明
        vid = vrow["id"]
        # 2. terminology run / evidence 有冇呢個 value_id
        try:
            tc = _sq.connect(r"C:\projects\meta\terminology\terminology.db")
            tc.row_factory = _sq.Row
            try:
                r = tc.execute(
                    "SELECT 1 FROM run WHERE value_id = ? AND is_active = 1"
                    " LIMIT 1", (vid,)).fetchone()
                if not r:
                    r = tc.execute(
                        "SELECT 1 FROM evidence WHERE value_id = ?"
                        " AND is_active = 1 LIMIT 1", (vid,)).fetchone()
            finally:
                tc.close()
        except Exception:
            r = None
        if r:
            return False  # 有 run / evidence = 有證明
        # 3. lineage 有冇呢個 value_id
        try:
            lc = _sq.connect(r"C:\projects\meta\lineage\lineage.db")
            lc.row_factory = _sq.Row
            try:
                r2 = lc.execute(
                    "SELECT 1 FROM lineage WHERE value_id = ?"
                    " AND is_active = 1 LIMIT 1", (vid,)).fetchone()
            finally:
                lc.close()
        except Exception:
            r2 = None
        if r2:
            return False  # 有 lineage = 有證明
        return True  # 全部冇 = unproven（worker 做咗但忘記記錄）

    def prove_flow(self, target_id):
        """行 sweep_prove flow 證明一個 target（自動判斷 + 寫 run + evidence）

        返回 {"run_id", "status_id", "status", "steps": [...]}
        """
        # target 一定要存在
        trow = self.conn.execute(
            "SELECT * FROM target WHERE id = ?", (target_id,)).fetchone()
        if not trow:
            raise ValueError(f"target 唔存在: {target_id}")
        flow = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = 'sweep_prove'"
            " AND is_active = 1").fetchone()
        if not flow:
            raise ValueError("sweep_prove flow 未 seed")
        # 攞 steps（condition 次序）
        steps = self.conn.execute(
            "SELECT s.id AS step_id, s.seq_id, c.meta AS condition_meta,"
            " c.id AS condition_id"
            " FROM step s JOIN condition c ON c.id = s.condition_id"
            " WHERE s.flow_id = ? AND s.is_active = 1"
            " ORDER BY s.seq_id", (flow["id"],)).fetchall()
        if not steps:
            raise ValueError("sweep_prove flow 冇 steps")
        # row_count：由 target.resource_id（db.table）數真實行
        row_count = None
        rid = trow["resource_id"] or ""
        if "." in rid:
            db_name, tbl = rid.split(".", 1)
            # 掃全站 *.db（同 function.DB_FILES 一致，零 hardcode）
            import glob as _glob
            db_path = None
            for _p in _glob.glob(r"C:\projects\meta\**\*.db",
                                 recursive=True):
                if _os.path.basename(_p) == db_name + ".db":
                    db_path = _p
                    break
            if db_path:
                try:
                    _c = sqlite3.connect(
                        f"file:{db_path}?mode=ro", uri=True)
                    try:
                        row_count = _c.execute(
                            "SELECT COUNT(*) FROM [%s]" % tbl.replace("]", "]]")
                        ).fetchone()[0]
                    finally:
                        _c.close()
                except Exception:
                    row_count = None
        # 判斷
        judged = []
        stopped = None
        all_pass = True
        for s in steps:
            ok = self._condition_judge(s["condition_meta"],
                                       dict(trow) | {"row_count": row_count})
            judged.append({"step_id": s["step_id"], "seq": s["seq_id"],
                           "condition": s["condition_meta"],
                           "is_pass": bool(ok)})
            if not ok:
                all_pass = False
                stopped = s["step_id"]
                break
        status_id = 1 if all_pass else 2
        # 寫 run
        cur = self.conn.execute(
            "INSERT INTO run (flow_id, target_id, status_id, step_id)"
            " VALUES (?, ?, ?, ?)",
            (flow["id"], target_id, status_id, stopped))
        run_id = cur.lastrowid
        # 寫 evidence（全 PASS -> 一條，記錄判斷）
        self.conn.execute(
            "INSERT INTO evidence (target_id, detail)"
            " VALUES (?, ?)",
            (target_id, f"sweep_prove run={run_id} status={status_id}"
                       f" steps={len(judged)}"))
        self.conn.commit()
        status_meta = "approved" if status_id == 1 else "rejected"
        return {"run_id": run_id, "status_id": status_id,
                "status": status_meta, "steps": judged}

    # ---------------- 字典查詢 ----------------
    def actions(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM action WHERE is_active = 1 ORDER BY id")]

    def statuses(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM status WHERE is_active = 1 ORDER BY id")]

    def resource_types(self):
        """列出資源類型字典（唯一權威 = resource.db type 表）

        2026-10-28：resource module 未重建（空殼）-> 空清單（等重建）。
        """
        if not getattr(self, "_res_attached", False):
            return []
        return [dict(r) for r in self.conn.execute(
            "SELECT id, type AS meta FROM resdb.type"
            " WHERE is_active = 1 ORDER BY id")]

    def physical_types(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM physical_type WHERE is_active = 1 ORDER BY id")]

    def _id_by_meta(self, table, meta):
        # resource_type 已移除：改為查 resource.db type（唯一權威）
        if table == "resource_type":
            if not getattr(self, "_res_attached", False):
                return None  # resource module 未重建（2026-10-28）
            r = self.conn.execute(
                "SELECT id FROM resdb.type WHERE type = ?", (meta,)).fetchone()
            return r["id"] if r else None
        r = self.conn.execute(
            f"SELECT id FROM {table} WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    # ---------------- target ----------------
    def insert_target(self, resource_id, identity_id=None, status=None,
                      resource_type=None, physical_type=None):
        """建立清理目標"""
        status_id = self._id_by_meta("status", status) if status else None
        rt_id = self._id_by_meta("resource_type", resource_type) if resource_type else None
        pt_id = self._id_by_meta("physical_type", physical_type) if physical_type else None
        cur = self.conn.execute(
            """INSERT OR IGNORE INTO target
               (resource_id, identity_id, status_id, resource_type_id, physical_type_id)
               VALUES (?, ?, ?, ?, ?)""",
            (resource_id, identity_id, status_id, rt_id, pt_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM target WHERE resource_id = ?", (resource_id,)).fetchone()
        return r["id"] if r else cur.lastrowid

    def targets(self):
        if getattr(self, "_res_attached", False):
            rows = [dict(r) for r in self.conn.execute(
                """SELECT t.id, t.resource_id, t.identity_id,
                          s.meta AS status, rt.type AS resource_type, pt.meta AS physical_type,
                          t.plan_action, t.plan_status,
                          t.source_version_id, t.target_version_id,
                          t.is_active
                   FROM target t
                   LEFT JOIN status s ON s.id = t.status_id
                   LEFT JOIN resdb.type rt ON rt.id = t.resource_type_id
                   LEFT JOIN physical_type pt ON pt.id = t.physical_type_id
                   ORDER BY t.id""")]
        else:
            # resource module 未重建（2026-10-28）-> 冇 resource_type JOIN
            rows = [dict(r) for r in self.conn.execute(
                """SELECT t.id, t.resource_id, t.identity_id,
                          s.meta AS status, NULL AS resource_type, pt.meta AS physical_type,
                          t.plan_action, t.plan_status,
                          t.source_version_id, t.target_version_id,
                          t.is_active
                   FROM target t
                   LEFT JOIN status s ON s.id = t.status_id
                   LEFT JOIN physical_type pt ON pt.id = t.physical_type_id
                   ORDER BY t.id""")]
        # version 字典喺 version.db（跨 DB 唔可以 join，用 code 補名）
        # 2026-10-27：version 表改名 registry（value_id -> value.value）
        try:
            import sqlite3 as _s
            _v = _s.connect(r"C:\projects\meta\version\version.db")
            _vm = {r[0]: r[1] for r in _v.execute(
                "SELECT r.id, v.value FROM registry r"
                " LEFT JOIN value v ON v.id = r.value_id")}
            _v.close()
            for row in rows:
                row["source_version"] = _vm.get(row.get("source_version_id"))
                row["target_version"] = _vm.get(row.get("target_version_id"))
        except Exception:
            pass
        return rows

    # ---------------- plan（v1.5.0：資源 × 版本 × 處置） ----------------
    def upsert_target_status(self, resource_id, status_meta, resource_type_id=None,
                             physical_type_id=None):
        """將 analyze() 計算出嘅 status 寫入 target 表（唔再即場算完就算）"""
        st = self.conn.execute(
            "SELECT id FROM status WHERE meta = ?", (status_meta,)).fetchone()
        if not st:
            return None
        row = self.conn.execute(
            "SELECT id FROM target WHERE resource_id = ?", (resource_id,)).fetchone()
        if row:
            self.conn.execute(
                "UPDATE target SET status_id = ?,"
                " resource_type_id = COALESCE(?, resource_type_id),"
                " physical_type_id = COALESCE(?, physical_type_id)"
                " WHERE id = ?",
                (st["id"], resource_type_id, physical_type_id, row["id"]))
            tid = row["id"]
        else:
            cur = self.conn.execute(
                "INSERT INTO target (resource_id, status_id, resource_type_id,"
                " physical_type_id) VALUES (?, ?, ?, ?)",
                (resource_id, st["id"], resource_type_id, physical_type_id))
            tid = cur.lastrowid
        self.conn.commit()
        return {"target_id": tid, "status": status_meta}

    def set_plan(self, resource_id, plan_action, source_version=None,
                 target_version=None):
        """為一個 target 建立計畫：upgrade / rebuild / drop / keep"""
        if plan_action not in ("upgrade", "rebuild", "drop", "keep"):
            raise ValueError(
                f"plan_action 必須係 upgrade/rebuild/drop/keep，收到 {plan_action}")
        row = self.conn.execute(
            "SELECT id FROM target WHERE resource_id = ?", (resource_id,)).fetchone()
        if not row:
            raise ValueError(f"target 唔存在: {resource_id}（要嘅話先 analyze）")
        src = tgt = None
        # version 字典喺 version.db（跨 DB 要開另一條連線）
        # 2026-10-27：version 表改名 registry（value_id -> value.value）
        if source_version or target_version:
            import sqlite3 as _s
            _v = _s.connect(r"C:\projects\meta\version\version.db")
            try:
                if source_version:
                    row_v = _v.execute(
                        "SELECT r.id FROM registry r"
                        " JOIN value v ON v.id = r.value_id"
                        " WHERE v.value = ?",
                        (source_version,)).fetchone()
                    src = row_v[0] if row_v else None
                if target_version:
                    row_v = _v.execute(
                        "SELECT r.id FROM registry r"
                        " JOIN value v ON v.id = r.value_id"
                        " WHERE v.value = ?",
                        (target_version,)).fetchone()
                    tgt = row_v[0] if row_v else None
            finally:
                _v.close()
        self.conn.execute(
            "UPDATE target SET plan_action = ?, plan_status = 'pending',"
            " source_version_id = COALESCE(?, source_version_id),"
            " target_version_id = COALESCE(?, target_version_id)"
            " WHERE id = ?",
            (plan_action, src, tgt, row["id"]))
        self.conn.commit()
        return {"target_id": row["id"], "resource_id": resource_id,
                "plan": plan_action, "status": "pending"}

    def pending_plans(self):
        """全部 pending 嘅 plan（monitor / preflight 睇呢個）"""
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM target WHERE plan_status = 'pending'"
            " AND plan_action IS NOT NULL ORDER BY id")]
        # 補 version 名（version 字典喺 version.db）
        # 2026-10-27：version 表改名 registry（value_id -> value.value）
        try:
            import sqlite3 as _s
            _v = _s.connect(r"C:\projects\meta\version\version.db")
            _vm = {r[0]: r[1] for r in _v.execute(
                "SELECT r.id, v.value FROM registry r"
                " LEFT JOIN value v ON v.id = r.value_id")}
            _v.close()
            for row in rows:
                row["source_version"] = _vm.get(row.get("source_version_id"))
                row["target_version"] = _vm.get(row.get("target_version_id"))
        except Exception:
            pass
        return rows

    def complete_plan(self, resource_id, result="done"):
        """執行完畢 -> plan_status = done"""
        self.conn.execute(
            "UPDATE target SET plan_status = ? WHERE resource_id = ?",
            (result, resource_id))
        self.conn.commit()
        return True

    # ---------------- 證據鏈 ----------------
    def insert_mission(self, target_id, action_id, flow_id=None,
                       step_id=None, task_id=None):
        """建立 mission（sweep.db 自己嘅 mission 表，2026-10-26）

        2026-10-26：mission module 已刪除 —— sweep 唔再 import mission，
        直接寫自己 DB 嘅 mission 表（target_id + action_id 唯一）。
        """
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO mission"
            " (target_id, action_id, flow_id, step_id, task_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (target_id, action_id, flow_id, step_id, task_id))
        self.conn.commit()
        if cur.rowcount == 0:
            row = self.conn.execute(
                "SELECT id FROM mission WHERE target_id = ? AND action_id = ?",
                (target_id, action_id)).fetchone()
            return row[0] if row else None
        return cur.lastrowid

    def insert_mission_run(self, mission_id, status_id=None, schema_run_id=None):
        """記錄 mission_run（mission module 已刪，由 sweep 自己記 status）"""
        cur = self.conn.execute(
            "INSERT INTO mission_run (mission_id, status_id, schema_run_id)"
            " VALUES (?, ?, ?)",
            (mission_id, status_id, schema_run_id))
        self.conn.commit()
        return cur.lastrowid

    def mission_runs(self, mission_id=None, limit=100):
        """列出 mission 執行記錄（可按 mission 篩選）"""
        if mission_id is not None:
            return [dict(r) for r in self.conn.execute(
                "SELECT * FROM mission_run WHERE mission_id = ?"
                " ORDER BY id DESC LIMIT ?", (mission_id, limit))]
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM mission_run ORDER BY id DESC LIMIT ?", (limit,))]

    def insert_evidence(self, target_id, detail, proof_run_id=None,
                        verify_run_id=None):
        """收集證據（collect evidence）

        proof_run_id  = proof.db proof_run.id（證明嘅證據，by_id）
        verify_run_id = verify.db verify_run.id（驗證嘅證據，by_id）
        """
        cur = self.conn.execute(
            "INSERT INTO evidence (target_id, detail, proof_run_id, verify_run_id)"
            " VALUES (?, ?, ?, ?)",
            (target_id, detail, proof_run_id, verify_run_id))
        self.conn.commit()
        return cur.lastrowid

    def insert_proof(self, evidence_id, mission_id, proof):
        """證明（proof）"""
        cur = self.conn.execute(
            "INSERT INTO proof (evidence_id, mission_id, proof) VALUES (?, ?, ?)",
            (evidence_id, mission_id, proof))
        self.conn.commit()
        return cur.lastrowid

    def insert_mission_log(self, mission_id, status, detail=None):
        """任務執行記錄（apply mission）"""
        cur = self.conn.execute(
            "INSERT INTO mission_log (mission_id, status, detail) VALUES (?, ?, ?)",
            (mission_id, status, detail))
        self.conn.commit()
        return cur.lastrowid

    def evidences(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM evidence ORDER BY id DESC LIMIT 50")]

    def proofs(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM proof ORDER BY id DESC LIMIT 50")]

    def mission_logs(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM mission_log ORDER BY id DESC LIMIT 50")]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()