"""api.py — Sweep（清理）：刪除殘留空表 + 留低 proof

之前嘅問題：臨時 script 刪咗 12 張空表，但冇留低 proof（證據）。
呢個 module 令每次清理動作都自動寫入 proof.db，可追溯。
cleanup 係 sweep module 嘅 skill（技能）。

設計：FK 分析（唔硬編碼、唔靠「有冇資料」估）
    _discover_dbs()   -> 自動掃描 C:\\projects\\meta\\*.db（所有 module 嘅 DB）
    analyze()         -> 每個 DB 做 FK 分析：核心表 / 孤島 / 狀態
    is_empty()        -> 空（0 行）
    is_legacy()       -> 有資料 + 冇人 FK 引用（遺留）
    is_dead()         -> 孤島（空 + 冇人引用 + 冇引用人）
"""

import glob
import os
import sqlite3
























from .sql import SqlStore

from .function import *  # noqa: F401,E402




class Sweep:
    """清理：刪除殘留空表 + 留低 proof（cleanup 係 skill）"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    # ---------------- FK 分析 ----------------
    def analyze(self, db_name=None, record_status=True):
        """分析一個（或全部）DB 嘅 FK 關係 + 活躍度 + 連接證明

        record_status = True 時，將每張表嘅 status 寫入 target 表
                        （v1.5.0：唔再即場算完就算，落表俾 monitor/observe 睇）

        返回 {"db": {"tables": [...], "references": {...}, "outgoing": {...},
                     "islands": [...], "last_active": {table: time},
                     "connection_proof": {table: {"connected": bool, "proof": str}},
                     "status": {table: active/legacy/dead/empty}}}
        """
        dbs = {db_name: DB_FILES[db_name]} if db_name else DB_FILES
        report = {}
        for name, path in dbs.items():
            if not os.path.exists(path):
                continue
            graph = _fk_graph(path)
            islands = _find_islands(path)
            last_active = {}
            conn_proof = {}
            status = {}
            for t in graph["tables"]:
                last_active[t] = _last_active(path, t)
                conn_proof[t] = _connection_proof(path, t, graph)
                rows = _row_count(path, t)
                has_id = _has_identity(name, t)
                if t in islands:
                    status[t] = "dead"
                elif rows > 0 and not graph["references"][t]:
                    status[t] = "legacy"
                elif rows > 0 and graph["references"][t] and not conn_proof[t]["connected"]:
                    # 有人引用但引用者全部空/孤島 -> 連接唔成立 -> 都算孤島
                    status[t] = "dead"
                elif rows == 0:
                    status[t] = "empty"
                else:
                    status[t] = "active"
                # 有身份證明 = 唔可以刪（即使空/孤島都保留）
                if has_id and status[t] in ("dead", "empty"):
                    status[t] = "protected"
            report[name] = {**graph, "islands": islands,
                            "last_active": last_active,
                            "connection_proof": conn_proof,
                            "identity": {t: _has_identity(name, t)
                                         for t in graph["tables"]},
                            "status": status}
            # v1.5.0：狀態落表（target.status_id）
            if record_status:
                for t, st in status.items():
                    try:
                        self.store.upsert_target_status(
                            f"{name}.{t}", st,
                            resource_type_id=None, physical_type_id=None)
                    except Exception:
                        pass
        return report

    # ---------------- 狀態檢查（掃描／觀察潛在 case）----------------
    def is_empty(self, db_name, table_name):
        """檢查目標係咪空（0 行）

        掃描：直接連目標 DB 數行數，唔靠任何 registry。
        返回 True = 空（0 行），False = 有資料。
        """
        path = DB_FILES.get(db_name)
        if not path or not os.path.exists(path):
            return False
        c = _conn(path)
        try:
            r = c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
                (table_name,)).fetchone()
            if not r:
                return False
            n = c.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
            return n == 0
        except sqlite3.Error:
            return False
        finally:
            c.close()

    def is_legacy(self, db_name, table_name):
        """檢查目標係咪 legacy（遺留）

        legacy = 有資料 + 冇任何表 FK 引用佢（冇人依賴，但保留參考）
        返回 True = legacy。
        """
        path = DB_FILES.get(db_name)
        if not path or not os.path.exists(path):
            return False
        graph = _fk_graph(path)
        if table_name not in graph["tables"]:
            return False
        return (_row_count(path, table_name) > 0
                and not graph["references"][table_name])

    def is_dead(self, db_name, table_name):
        """檢查目標係咪 dead（死，可以清理）

        dead = 孤島（island）：
            1. 空（0 行）
            2. 冇任何表 FK 引用佢（冇人依賴）
            3. 佢都冇 FK 引用人（完全孤立）
        返回 True = dead（可以 DROP）。
        """
        path = DB_FILES.get(db_name)
        if not path or not os.path.exists(path):
            return False
        islands = _find_islands(path)
        return table_name in islands

    def is_orphan(self, db_name, table_name):
        """檢查目標係咪 orphan（冇身份證明，可以 drop）

        orphan = 冇身份證明（identity.db 冇登記）：
            有身份（kind + name 對應）= 證明到身份 = 唔可以刪
            冇身份 = 證明唔到 = sweep 可以 drop
        返回 True = orphan（可以 DROP）。
        """
        return not _has_identity(db_name, table_name)

    def scan(self):
        """掃描所有 DB，觀察每個表嘅狀態（empty / legacy / dead / active）

        呢個就係「掃描／觀察潛在 case」：sweep 自己逐個 DB 檢查，
        用 FK 分析搵孤島（island），唔靠 taxonomy 或者其他 registry。
        返回 {"db": {"table": "empty/legacy/dead/active"}}
        """
        report = {}
        for db_name, path in DB_FILES.items():
            if not os.path.exists(path):
                continue
            analysis = self.analyze(db_name)
            if db_name in analysis:
                report[db_name] = analysis[db_name]["status"]
        return report

    def _find_empty_tables(self):
        """搵出所有孤島（dead）：空 + 冇人引用 + 冇引用人"""
        found = []
        for db_name, path in DB_FILES.items():
            if not os.path.exists(path):
                continue
            for t in _find_islands(path):
                found.append({"db": db_name, "table": t, "rows": 0})
        return found

    def run(self, dry_run=True, reason="殘留空表（DDL 建立咗但冇 module 用）"):
        """執行清理

        dry_run=True  -> 只偵測，唔真刪（安全）
        dry_run=False -> 真刪 + 寫入 sweep.db（sweep 表 + result 表）

        受保護目標（target.is_protected=1）唔會刪。
        """
        empty_tables = self._find_empty_tables()
        result = {"dry_run": dry_run, "found": empty_tables,
                  "deleted": [], "kept": [], "protected": []}

        if dry_run:
            result["note"] = "dry-run：未真刪，用 dry_run=False 先會刪 + 寫 proof"
            return result

        # 真刪 + 寫 sweep.db（sweep 表 + result 表）
        for item in empty_tables:
            db_name, table = item["db"], item["table"]
            path = DB_FILES[db_name]

            # 檢查受保護目標
            if self.store.is_protected(db_name, table):
                result["protected"].append(f"{db_name}.{table}")
                continue

            # 經擁有者 module 刪表（唔准自己開後門）
            try:
                c, store = _owner_conn(path)
                try:
                    c.execute(f'DROP TABLE "{table}"')
                    c.commit()
                finally:
                    store.close()
            except (ValueError, sqlite3.Error) as e:
                result["kept"].append(f"{db_name}.{table}（{e}）")
                continue
            sid = self.store.insert_sweep(db_name, table, "drop_empty_table", 0, reason)
            # 寫入 result 表（結果）
            self.store.insert_result(sid, db_name, table, "success", reason)
            result["deleted"].append(f"{db_name}.{table}")

        self.store.commit()
        result["deleted_count"] = len(result["deleted"])
        result["protected_count"] = len(result["protected"])
        return result

    # ---------------- target（清理目標）----------------
    def add_target(self, resource_id, identity_id=None, status=None,
                   resource_type=None, physical_type=None):
        """建立清理目標

        resource_id    資源識別（例如 taxonomy.db.module）
        status         empty / dead / legacy / active
        resource_type  db_table / db_field / function / api / route / SQL / package / module / channel / skill
        physical_type  package / folder / coding
        返回 target_id（INT）
        """
        tid = self.store.insert_target(resource_id, identity_id, status,
                                       resource_type, physical_type)
        return tid

    def list_targets(self):
        """列出所有清理目標（含 status / resource_type / physical_type / plan）"""
        return self.store.targets()

    # ---------------- plan（v1.5.0：資源 × 版本 × 處置） ----------------
    def set_plan(self, resource_id, plan_action, source_version=None,
                 target_version=None, task_id=None, reason=None):
        """為一個 target 建立計畫（落表，唔寫死 code）

        plan_action    = upgrade（原地套新版）/ rebuild（刪咗重建）/ drop / keep
        source_version = version.db 版本名（由邊版嚟，可選）
        target_version = version.db 版本名（去邊版，可選）
        task_id        = 可選：邊個 task 觸發
        reason         = 可選：點解（寫入 mission 記錄）

        流程：set_plan（pending）→ worker 執行 → complete_plan（done）
        """
        return self.store.set_plan(resource_id, plan_action,
                                   source_version, target_version)

    def pending_plans(self):
        """全部 pending 嘅 plan（monitor / preflight 睇呢個）"""
        return self.store.pending_plans()

    def complete_plan(self, resource_id, result="done"):
        """執行完畢 -> plan_status = done"""
        return self.store.complete_plan(resource_id, result)

    # ---------------- mission（任務）----------------
    def create_mission(self, target_id, action, task_id, flow_id=None,
                       step_id=None, skill_meta=None):
        """建立任務（target + action：DROP / KEEP / RENAME / REPLACE / MERGE）

        task_id         = 必填：task.db task.id（邊個 task 觸發）—— 冇 task 就唔應該有 mission
        flow_id         = 可選：flow.db flow.id（邊個 flow 執行）
        step_id         = 可選：code_gen.db step.id（邊個 step 執行）
        skill_meta      = 可選：skill 名（邊個技能執行，例如 sweep_drop）
        返回 mission_id（INT）

        mission 係獨立 module（mission.db）—— 唔 share 去其他 module 嘅 DB
        2026-10-23：mission（定義）+ mission_run（執行）+ flow_step（計劃）
        2026-10-23b：target -> registry resource_id -> mission.resource_id + module
        （唔可以 NULL —— target 對應到真資源就填，對唔到就明講）
        """
        if not task_id:
            raise ValueError("task_id 必填：每個 mission 都要有 task 觸發，冇 task 就唔應該有 mission")
        # target -> 由 target.resource_id 前綴推導 module（唔連 resource.db）
        resource_id = None
        module = None
        try:
            _sq = sqlite3
            _tc = _sq.connect(r"C:\projects\meta\sweep\sweep.db")
            _tc.row_factory = _sq.Row
            _t = _tc.execute(
                "SELECT resource_id FROM target WHERE id = ? AND is_active = 1",
                (target_id,)).fetchone()
            _tc.close()
            if _t and _t["resource_id"]:
                # target.resource_id 就係 registry meta 字串（例如 code_gen.db.filling）
                _meta = _t["resource_id"]
                # module 名：'code_gen.db.filling' -> 'code_gen' -> registry 正名 'codegen'
                mod_from_meta = _meta.split(".")[0] if "." in _meta else None
                if mod_from_meta:
                    module = mod_from_meta.replace("_", "")
        except sqlite3.Error:
            pass

        # action 名 -> common.db action 表（真數據 registry）攞 id
        # 唯一來源 = action 表入面嘅 value（例如 'clean'）。
        # 搵唔到 = 明講報錯，唔准自動註冊（會污染字典）。
        from common import Common as _Cm
        _cm = _Cm()
        try:
            action_id = _cm.action_id(action)
        finally:
            _cm.close()
        if not action_id:
            raise ValueError(
                f"action '{action}' 唔喺 common.db action 字典（真數據 registry）"
                f" — caller 要傳字典內嘅真 value（例如 'clean'）")

        # 2026-10-26：mission module 已刪除 —— sweep 寫自己 DB 嘅 mission 表
        mid = self.store.insert_mission(
            target_id, action_id, flow_id=flow_id, step_id=step_id,
            task_id=task_id)
        # mission_run：status=NA（未執行）
        from common import Common
        cm = Common()
        try:
            na = cm.status_id("NA") or cm.register_status("NA")
            self.store.insert_mission_run(mid, status_id=na)
        finally:
            cm.close()
        return mid

    def list_missions(self):
        """列出所有任務執行記錄（sweep.db 自己嘅 mission_run）"""
        return self.store.mission_runs()

    # ---------------- 證據鏈 ----------------
    def collect_evidence(self, target_id, detail, proof_run_id=None,
                         verify_run_id=None):
        """收集證據（collect evidence）返回 evidence_id（INT）

        proof_run_id  = proof.db proof_run.id（證明嘅證據，by_id）
        verify_run_id = verify.db verify_run.id（驗證嘅證據，by_id）
        """
        eid = self.store.insert_evidence(target_id, detail,
                                         proof_run_id, verify_run_id)
        return eid

    def prove(self, evidence_id, mission_id, proof):
        """證明（proof）返回 proof_id（INT）"""
        pid = self.store.insert_proof(evidence_id, mission_id, proof)
        return pid

    def apply_mission(self, mission_id, status, detail=None):
        """執行任務（apply mission）返回 log_id（INT）"""
        lid = self.store.insert_mission_log(mission_id, status, detail)
        return lid

    # ---------------- rename（RENAME action 嘅實際執行） ----------------
    def rename(self, resource_id, new_name, task_id, reason="結構升級改名",
               resource_type="db_table", physical_type="table",
               db_path=None, old_name=None):
        """經 API 執行資源改名（RENAME action，含完整證據鏈）

        resource_id    資源識別（例如 taxonomy.db.module / definition.db.design）
        new_name       新名
        task_id        必填：task.db task.id（邊個 task 觸發）
        reason         改名原因
        resource_type  資源類型（db_table / db_field / function / api / route / module / ...）
        physical_type  實體類型（table / column / file / folder / ...）
        db_path        可選：DB 路徑（rename table 時需要）
        old_name       可選：舊表名（db_path 提供時用）

        流程：
            1. 建立 target（resource_id）
            2. 建立 mission（action = RENAME，task_id 必填）
            3. 收集證據（evidence：舊名 + 新名 + 原因）
            4. 執行改名（table -> ALTER TABLE；其他 -> 記錄）
            5. 驗證（verify：新名真係存在？）
            6. 證明（proof：改名成功 + 驗證通過）
            7. 記錄 mission_log（applied / failed）

        返回 {"mission_id": n, "evidence_id": n, "proof_id": n,
              "log_id": n, "resource_id": str, "new_name": str,
              "verified": bool}
        """
        # 1. target（用 resource_id，唔限 table）
        tid = self.add_target(resource_id,
                              resource_type=resource_type,
                              physical_type=physical_type)
        # 2. mission（RENAME，task_id 必填）
        mid = self.create_mission(tid, "RENAME", task_id,
                                  skill_meta="sweep_rename")
        # 3. evidence
        eid = self.collect_evidence(
            tid, f"rename {resource_id} -> {new_name}（{reason}）")
        # 4. 執行改名
        detail = f"{resource_id} -> {new_name}"
        alter_error = None
        if db_path and old_name:
            conn, store = _owner_conn(db_path)
            try:
                conn.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"')
                conn.commit()
                detail = f"ALTER TABLE {old_name} RENAME TO {new_name}"
            except sqlite3.Error as e:
                alter_error = str(e)
            finally:
                store.close()
        # 5. 驗證（verify：新名真係存在？）
        verified = False
        verify_method = None
        if alter_error:
            verified = False
            verify_method = f"ALTER TABLE 失敗：{alter_error}"
        elif db_path and old_name:
            # table：檢查 sqlite_master 有新名 + 冇舊名（真正驗證）
            conn = _readonly(db_path)
            try:
                has_new = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                    (new_name,)).fetchone()
                has_old = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                    (old_name,)).fetchone()
                verified = bool(has_new) and not has_old
                verify_method = (f"SELECT 1 FROM sqlite_master"
                                 f" WHERE name='{new_name}'"
                                 f" -> has_new={bool(has_new)} has_old={bool(has_old)}")
            finally:
                conn.close()
        else:
            # 其他資源：冇實際動作可以做 -> 唔可以話成功（fail：冇嘢可以證明）
            verified = False
            verify_method = ("冇 db_path/old_name -> 冇實際動作，"
                             "唔可以證明改名成功")
        # 6. proof（改名成功 + 驗證結果）
        proof_text = (f"{detail} 成功，驗證：{'通過' if verified else '失敗'}"
                      if not alter_error
                      else f"{detail} 失敗：{alter_error}")
        pid = self.prove(eid, mid, proof_text)
        # 7. mission_log（verified 先 applied，否則 failed）
        lid = self.apply_mission(mid, "applied" if verified else "failed",
                                 f"{detail}（verify={'ok' if verified else 'fail'}）")
        return {"mission_id": mid, "evidence_id": eid, "proof_id": pid,
                "log_id": lid, "resource_id": resource_id, "new_name": new_name,
                "verified": verified, "error": alter_error,
                "verify_method": verify_method}

    # 向後兼容：rename_table 保留（內部呼叫通用 rename）
    def rename_table(self, db_path, old_name, new_name, task_id,
                     reason="結構升級改名"):
        """（舊 API）rename table —— 內部用通用 rename()"""
        import os
        db_name = os.path.basename(db_path)
        return self.rename(f"{db_name}.{old_name}", new_name, task_id, reason,
                           resource_type="db_table", physical_type="table",
                           db_path=db_path, old_name=old_name)

    # ---------------- drop（DROP action 嘅實際執行） ----------------
    def drop(self, resource_id, task_id, reason="結構升級刪除",
             resource_type="db_table", physical_type="table",
             db_path=None, object_name=None):
        """經 API 刪除一個 DB 物件（DROP action，含完整證據鏈）

        resource_id    資源識別（例如 taxonomy.db.v_package_tree）
        task_id        必填：task.db task.id（邊個 task 觸發）
        db_path        可選：DB 路徑（真刪時需要）
        object_name    可選：物件名（table / view / trigger / index）

        按 sqlite_master.type 揀正確嘅 DROP 語句（唔可以一律 DROP TABLE）：
            table   -> DROP TABLE
            view    -> DROP VIEW
            trigger -> DROP TRIGGER
            index   -> DROP INDEX
        驗證 = 物件真係唔存在（sqlite_master 查唔到）。
        """
        tid = self.add_target(resource_id,
                              resource_type=resource_type,
                              physical_type=physical_type)
        mid = self.create_mission(tid, "DROP", task_id,
                                  skill_meta="sweep_drop")
        eid = self.collect_evidence(
            tid, f"drop {resource_id}（{reason}）")
        detail = f"DROP {resource_id}"
        drop_error = None
        object_type = None
        if db_path and object_name:
            conn, store = _owner_conn(db_path)
            try:
                row = conn.execute(
                    "SELECT type FROM sqlite_master WHERE name = ?",
                    (object_name,)).fetchone()
                object_type = row[0] if row else None
                if not object_type:
                    drop_error = f"物件唔存在: {object_name}"
                else:
                    keyword = {"table": "TABLE", "view": "VIEW",
                               "trigger": "TRIGGER", "index": "INDEX"}.get(
                                   object_type)
                    if not keyword:
                        drop_error = f"唔支援嘅物件類型: {object_type}"
                    else:
                        conn.execute(
                            f'DROP {keyword} IF EXISTS "{object_name}"')
                        conn.commit()
                        detail = f"DROP {keyword} {object_name}"
            except sqlite3.Error as e:
                drop_error = str(e)
            finally:
                store.close()
        else:
            drop_error = "冇 db_path/object_name -> 冇實際動作"

        # 驗證：物件真係唔存在
        verified = False
        verify_method = None
        if drop_error:
            verify_method = f"DROP 失敗：{drop_error}"
        else:
            conn = _readonly(db_path)
            try:
                still = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE name = ?",
                    (object_name,)).fetchone()
                verified = not bool(still)
                verify_method = (f"SELECT 1 FROM sqlite_master"
                                 f" WHERE name='{object_name}'"
                                 f" -> still_exists={bool(still)}")
            finally:
                conn.close()

        pid = self.prove(
            eid, mid,
            f"{detail} {'成功' if verified else '失敗'}"
            f"（verify={'ok' if verified else 'fail'}）")
        lid = self.apply_mission(mid, "applied" if verified else "failed",
                                 f"{detail}（verify={'ok' if verified else 'fail'}）")
        return {"mission_id": mid, "evidence_id": eid, "proof_id": pid,
                "log_id": lid, "resource_id": resource_id,
                "object_type": object_type, "verified": verified,
                "error": drop_error, "verify_method": verify_method}

    # ---------------- drop_column（DROP COLUMN action） ----------------
    def drop_column(self, resource_id, task_id, db_path, table, column,
                    reason="結構升級刪欄位",
                    resource_type="db_field", physical_type="column",
                    expect_null=None):
        """經 API 刪除一個欄位（DROP COLUMN，含完整證據鏈）

        resource_id  資源識別（例如 registry.db.registry.resource_id）
        task_id      必填：task.db task.id
        db_path      DB 路徑（必填）
        table        表名（必填）
        column       欄位名（必填）
        expect_null  可選：刪之前該欄 NULL 行數（唔符就 ABORT，防誤刪有資料嘅欄）

        安全：
            - 欄位唔存在 -> 唔做（verified=False）
            - expect_null 有值 -> 先 COUNT NULL，唔符就 ABORT
            - 刪完驗證：PRAGMA table_info 冇該欄
        """
        tid = self.add_target(resource_id, resource_type=resource_type,
                              physical_type=physical_type)
        mid = self.create_mission(tid, "DROP", task_id,
                                  skill_meta="sweep_drop_column")
        eid = self.collect_evidence(
            tid, f"drop column {table}.{column}（{reason}）")
        detail = f"DROP COLUMN {table}.{column}"
        err = None
        verified = False
        verify_method = None
        nulls = None
        try:
            conn, store = _owner_conn(db_path)
            try:
                cols = [c[1] for c in conn.execute(
                    f'PRAGMA table_info("{table}")')]
                if column not in cols:
                    err = f"欄位唔存在: {table}.{column}"
                else:
                    if expect_null is not None:
                        nulls = conn.execute(
                            f'SELECT COUNT(*) FROM "{table}"'
                            f' WHERE "{column}" IS NULL').fetchone()[0]
                        if nulls != expect_null:
                            err = (f"預期 {expect_null} 行 NULL，實際 {nulls} 行"
                                   f" -> ABORT（唔改任何資料）")
                    if err is None:
                        conn.execute(
                            f'ALTER TABLE "{table}" DROP COLUMN "{column}"')
                        conn.commit()
                        after = [c[1] for c in conn.execute(
                            f'PRAGMA table_info("{table}")')]
                        verified = column not in after
                        verify_method = (f"PRAGMA table_info({table})"
                                         f" -> column_exists={column in after}")
            finally:
                store.close()
        except sqlite3.Error as e:
            err = str(e)

        pid = self.prove(
            eid, mid,
            f"{detail} {'成功' if verified else '失敗'}"
            f"（verify={'ok' if verified else 'fail'}，{verify_method or err}）")
        lid = self.apply_mission(
            mid, "applied" if verified else "failed",
            f"{detail}（verify={'ok' if verified else 'fail'}）")
        return {"mission_id": mid, "evidence_id": eid, "proof_id": pid,
                "log_id": lid, "resource_id": resource_id,
                "verified": verified, "error": err,
                "nulls_before": nulls, "verify_method": verify_method}

    # ---------------- replace（REPLACE action） ----------------
    def replace(self, resource_id, new_resource_id, task_id,
                reason="結構升級替換",
                resource_type="db_table", physical_type="table",
                db_path=None, old_name=None, new_name=None):
        """經 API 執行資源替換（REPLACE action，含完整證據鏈）

        resource_id     舊資源（例如 definition.db.old_table）
        new_resource_id 新資源（例如 definition.db.new_table）
        task_id         必填：task.db task.id（邊個 task 觸發）
        db_path         可選：DB 路徑（真替換時需要）
        old_name        可選：舊表名
        new_name        可選：新表名

        真替換（有 db_path + old_name + new_name）：
            ALTER TABLE old_name RENAME TO new_name + 驗證 sqlite_master
        冇實際動作 -> verified=False（唔可以證明成功）
        """
        tid = self.add_target(resource_id,
                              resource_type=resource_type,
                              physical_type=physical_type)
        mid = self.create_mission(tid, "REPLACE", task_id,
                                  skill_meta="sweep_replace")
        eid = self.collect_evidence(
            tid, f"replace {resource_id} -> {new_resource_id}（{reason}）")
        detail = f"{resource_id} -> {new_resource_id}"

        # 執行替換（真替換 = rename table）
        verified = False
        verify_method = None
        if db_path and old_name and new_name:
            conn, store = _owner_conn(db_path)
            try:
                conn.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"')
                conn.commit()
                # 驗證：新名存在 + 舊名唔存在
                has_new = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                    (new_name,)).fetchone()
                has_old = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                    (old_name,)).fetchone()
                verified = bool(has_new) and not has_old
                verify_method = (f"SELECT 1 FROM sqlite_master"
                                 f" WHERE name='{new_name}'"
                                 f" -> has_new={bool(has_new)} has_old={bool(has_old)}")
            except sqlite3.Error as e:
                verify_method = f"ALTER TABLE 失敗：{e}"
            finally:
                store.close()
        else:
            verify_method = ("冇 db_path/old_name/new_name -> 冇實際動作，"
                             "唔可以證明替換成功")

        pid = self.prove(eid, mid,
                         f"{detail} {'成功' if verified else '失敗'}（verify={'ok' if verified else 'fail'}）")
        lid = self.apply_mission(mid, "applied" if verified else "failed",
                                 f"{detail}（verify={'ok' if verified else 'fail'}）")
        return {"mission_id": mid, "evidence_id": eid, "proof_id": pid,
                "log_id": lid, "resource_id": resource_id,
                "new_resource_id": new_resource_id,
                "verified": verified, "verify_method": verify_method}

    # ---------------- merge（MERGE action） ----------------
    def merge(self, resource_id, into_resource_id, task_id,
              reason="結構升級合併",
              resource_type="db_table", physical_type="table",
              db_path=None, old_name=None, into_name=None):
        """經 API 執行資源合併（MERGE action，含完整證據鏈）

        resource_id      要合併嘅資源（例如 definition.db.old_table）
        into_resource_id 合併入去嘅資源（例如 definition.db.main_table）
        task_id          必填：task.db task.id（邊個 task 觸發）
        db_path          可選：DB 路徑（真合併時需要）
        old_name         可選：要合併嘅表名
        into_name        可選：合併入去嘅表名

        真合併（有 db_path + old_name + into_name）：
            INSERT INTO into_name SELECT * FROM old_name + DROP old_name + 驗證
        冇實際動作 -> verified=False（唔可以證明成功）
        """
        tid = self.add_target(resource_id,
                              resource_type=resource_type,
                              physical_type=physical_type)
        mid = self.create_mission(tid, "MERGE", task_id,
                                  skill_meta="sweep_merge")
        eid = self.collect_evidence(
            tid, f"merge {resource_id} INTO {into_resource_id}（{reason}）")
        detail = f"{resource_id} -> {into_resource_id}"

        # 執行合併（真合併 = 搬資料 + 刪舊表 + 驗證）
        verified = False
        verify_method = None
        if db_path and old_name and into_name:
            conn, store = _owner_conn(db_path)
            try:
                # 1. 搬資料（INSERT INTO ... SELECT）
                conn.execute(
                    f'INSERT INTO "{into_name}" SELECT * FROM "{old_name}"')
                # 2. 刪舊表
                conn.execute(f'DROP TABLE "{old_name}"')
                conn.commit()
                # 3. 驗證：舊表唔存在 + 新表存在
                has_old = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                    (old_name,)).fetchone()
                has_into = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                    (into_name,)).fetchone()
                verified = not has_old and bool(has_into)
                verify_method = (f"SELECT 1 FROM sqlite_master"
                                 f" WHERE name='{old_name}'"
                                 f" -> has_old={bool(has_old)} has_into={bool(has_into)}")
            except sqlite3.Error as e:
                verify_method = f"MERGE 失敗：{e}"
            finally:
                store.close()
        else:
            verify_method = ("冇 db_path/old_name/into_name -> 冇實際動作，"
                             "唔可以證明合併成功")

        pid = self.prove(eid, mid,
                         f"{detail} {'成功' if verified else '失敗'}（verify={'ok' if verified else 'fail'}）")
        lid = self.apply_mission(mid, "applied" if verified else "failed",
                                 f"{detail}（verify={'ok' if verified else 'fail'}）")
        return {"mission_id": mid, "evidence_id": eid, "proof_id": pid,
                "log_id": lid, "resource_id": resource_id,
                "into_resource_id": into_resource_id,
                "verified": verified, "verify_method": verify_method}

    def purge_rows(self, resource_id, task_id, db_path, table, where,
                   params=(), reason="清理無效資料（行級）",
                   resource_type="db_table", physical_type="table",
                   expect=1, verify_where=None, set_values=None):
        """經 API 清理無效資料行（row-level purge，含完整證據鏈）

        resource_id  資源識別（例如 code_gen.db.filling.3）
        task_id      必填：task.db task.id
        db_path      DB 路徑（必填）
        table        表名（必填）
        where        條件（必填，唔准全表）
        params       條件參數
        expect       預期影響行數（唔符合就 ABORT，防止誤刪）
        verify_where 驗證條件（預設 = where）
        set_values   有值 -> UPDATE 成呢啲值（唔刪行）；冇 -> DELETE

        安全：
            - where 唔可以係空 / 1=1 / True（唔准全表）
            - 動手前先 COUNT，同 expect 唔符 -> abort（唔改任何資料）
            - DELETE：刪完 COUNT 必須 = 0
            - UPDATE：改完 COUNT 必須 = 0（唔再符合 where）
        """
        guard = where.strip().lower()
        if not guard or guard in ("1=1", "true", "1"):
            return {"verified": False, "error": "唔准全表操作（where 太闊）",
                    "affected": 0}
        vw = verify_where if verify_where is not None else where

        tid = self.add_target(resource_id, resource_type=resource_type,
                              physical_type=physical_type)
        mid = self.create_mission(tid, "clean", task_id,
                                  skill_meta="sweep_purge_rows")
        eid = self.collect_evidence(
            tid, f"purge {resource_id}（{reason}）")
        purge_error = None
        before = None
        after = None
        affected = 0
        is_update = bool(set_values)
        try:
            conn, store = _owner_conn(db_path)
            try:
                before = conn.execute(
                    f'SELECT COUNT(*) FROM "{table}" WHERE {where}',
                    params).fetchone()[0]
                if before != expect:
                    purge_error = (f"預期 {expect} 行，實際 {before} 行 -> "
                                   f"ABORT（唔改任何資料）")
                else:
                    if is_update:
                        assigns = ", ".join(f'"{k}" = ?' for k in set_values)
                        vals = tuple(set_values.values()) + tuple(params)
                        cur = conn.execute(
                            f'UPDATE "{table}" SET {assigns} WHERE {where}',
                            vals)
                    else:
                        cur = conn.execute(
                            f'DELETE FROM "{table}" WHERE {where}', params)
                    conn.commit()
                    affected = cur.rowcount
                    after = conn.execute(
                        f'SELECT COUNT(*) FROM "{table}" WHERE {vw}',
                        params).fetchone()[0]
            finally:
                store.close()
        except sqlite3.Error as e:
            purge_error = str(e)

        verified = (purge_error is None and after == 0)
        verb = "UPDATE" if is_update else "DELETE"
        detail = f"PURGE {verb} {table} WHERE {where}（{affected} 行）"
        verify_method = (f"before={before} affected={affected} after={after}"
                         f"（預期 {expect}）")
        pid = self.prove(
            eid, mid,
            f"{detail} {'成功' if verified else '失敗'}"
            f"（verify={'ok' if verified else 'fail'}，{verify_method}）")
        lid = self.apply_mission(
            mid, "applied" if verified else "failed",
            f"{detail}（verify={'ok' if verified else 'fail'}）")
        return {"mission_id": mid, "evidence_id": eid, "proof_id": pid,
                "log_id": lid, "resource_id": resource_id,
                "verified": verified, "before": before, "after": after,
                "affected": affected, "deleted": affected,
                "error": purge_error, "verify_method": verify_method}

    def purge_registry(self, task_id, metas=None, meta_like=None,
                       reason="清理過時資源登記",
                       expect=None):
        """經 API 清理 resource.db registry 嘅過時登記（含證據鏈）

        為什麼唔用 purge_rows：resource.db.registry 有寫入守衛 trigger
        （guard_registry_delete），唔經 Resource API 一律 ABORT。
        所以呢個方法一定要經 Resource().unregister()。

        task_id    必填：task.db task.id
        metas      精確 meta 清單（list）—— 同 meta_like 二選一
        meta_like  LIKE pattern（一定要夠窄，唔准 '%' 開頭）
        expect     預期行數（唔符 -> ABORT，唔改任何資料）
        """
        try:
            from resource import Resource
        except ImportError:
            return {"verified": False, "deleted": 0,
                    "error": "resource module 已 drop（2026-10-26），待重建"}
        if not metas and not meta_like:
            return {"verified": False, "error": "要指定 metas 或 meta_like",
                    "deleted": 0}
        if meta_like is not None and meta_like.strip().startswith("%"):
            return {"verified": False,
                    "error": f"meta_like 太闊（唔准 '%' 開頭）: {meta_like}",
                    "deleted": 0}

        rid = f"resource.db.registry[{meta_like or ','.join(metas[:2])}]"
        tid = self.add_target(rid, resource_type="db_field",
                              physical_type="row")
        mid = self.create_mission(tid, "clean", task_id,
                                  skill_meta="sweep_purge_registry")
        eid = self.collect_evidence(tid, f"purge registry（{reason}）")

        r = Resource()
        deleted = 0
        purge_error = None
        try:
            if metas:
                rows = [dict(x) for x in r.store.conn.execute(
                    "SELECT id, meta FROM registry WHERE meta IN"
                    f" ({','.join('?' * len(metas))})", tuple(metas))]
            else:
                rows = [dict(x) for x in r.store.conn.execute(
                    "SELECT id, meta FROM registry WHERE meta LIKE ? ESCAPE '\\'",
                    (meta_like,))]
            if expect is not None and len(rows) != expect:
                purge_error = (f"預期 {expect} 行，實際 {len(rows)} 行 -> "
                               f"ABORT（唔改任何資料）")
            else:
                for row in rows:
                    if r.unregister(row["meta"]):
                        deleted += 1
        except Exception as e:
            purge_error = str(e)
        finally:
            r.close()

        after = len(rows) - deleted
        verified = (purge_error is None and after == 0)
        detail = f"PURGE registry（{deleted} 行）"
        verify_method = f"found={len(rows)} deleted={deleted} after={after}"
        pid = self.prove(
            eid, mid,
            f"{detail} {'成功' if verified else '失敗'}"
            f"（verify={'ok' if verified else 'fail'}，{verify_method}）")
        lid = self.apply_mission(
            mid, "applied" if verified else "failed",
            f"{detail}（verify={'ok' if verified else 'fail'}）")
        return {"mission_id": mid, "evidence_id": eid, "proof_id": pid,
                "log_id": lid, "resource_id": rid, "verified": verified,
                "before": len(rows), "after": after, "deleted": deleted,
                "error": purge_error, "verify_method": verify_method}

    def list_evidences(self):
        return self.store.evidences()

    def list_proofs(self):
        return self.store.proofs()

    def list_mission_logs(self):
        return self.store.mission_logs()

    # ---------------- 字典 ----------------
    def list_actions(self):
        return self.store.actions()

    def list_statuses(self):
        return self.store.statuses()

    def list_resource_types(self):
        return self.store.resource_types()

    def list_physical_types(self):
        return self.store.physical_types()

    def history(self, limit=100):
        """睇清理歷史（sweep.db）"""
        return self.store.sweeps(limit)

    def results(self, sweep_id=None, limit=100):
        """睇清理結果"""
        return self.store.results(sweep_id, limit)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()