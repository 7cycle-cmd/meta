"""api.py — schema.db 對外 API

schema = 環境檢查層：mission 之前要過 schema 檢查（環境 ready 先可以做 mission）

    check_environment(task_id, required_apis)  檢查環境（api 夠唔夠 / value active / broken / missing）
    is_ready(task_id)                          呢個 task 嘅環境 ready 未？

檢查類型：
    api_exists     = 要 call N 個 site，有冇 N 個 api？（registry type_id=4）
    value_active   = value 係咪 active？（registry type_id=11 is_active=1）
    value_broken   = value 會唔會 broken？（有冇對應 db_field / lineage）
    value_missing  = value 係咪 missing？（要 build + proof 先可以做 mission）

用法：
    from schema import Schema
    s = Schema()
    result = s.check_environment(task_id=1, required_apis=10)
    s.close()
"""

import sqlite3

from .sql import SqlStore

RESOURCE_DB = r"C:\projects\meta\resource\resource.db"


class Schema:
    """環境檢查層（schema.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def check_environment(self, task_id, required_apis=0, resource_ids=None):
        """檢查環境：mission 之前要過呢啲檢查（per-dish 食材檢查，強制）

        resource_ids = 呢個 mission 要用嘅資源 id 清單（「呢碟菜嘅食材」）
            — 必須提供；冇 = raise ValueError（唔可以 fallback 去全局統計，
              嗰啲係假檢查：「成個冰櫃有貨」唔等於「呢碟菜 ready」）

        檢查（每件食材）：
            resource_exists:<id>  — registry 有呢個資源（冇 = 食材唔存在）
            resource_active:<id>  — is_active = 1（冇 = 食材壞咗）
            resource_proved:<id>  — proof_case 有 proof（冇 = 冇證據係真）
        全部過 -> resources_ready ✓

        返回 {"ready": bool, "checks": [...]}
        """
        if not resource_ids:
            raise ValueError(
                "check_environment 一定要 resource_ids（呢碟菜嘅食材清單）"
                " — 唔准全局統計 fallback（假檢查）")
        if isinstance(resource_ids, (str, int)):
            resource_ids = [resource_ids]
        resource_ids = [int(x) for x in resource_ids]
        checks = []

        import os as _os
        if not _os.path.exists(RESOURCE_DB):
            # resource module 已 drop（2026-10-26）-> 冇資源可以證明
            for rid in resource_ids:
                checks.append({
                    "name": f"resource_exists:{rid}", "type": "resource_exists",
                    "passed": False,
                    "detail": f"{rid} 唔存在（resource module 已 drop，等重建）"})
            checks.append({
                "name": "resources_ready", "type": "resources_ready",
                "passed": False,
                "detail": "resource module 已 drop（2026-10-26），待重建"})
            return {"ready": False, "checks": checks,
                    "missing": [{"resource_id": rid, "gap": "exists",
                                 "meta": None} for rid in resource_ids]}

        reg = sqlite3.connect(RESOURCE_DB)
        reg.row_factory = sqlite3.Row
        proved_ids = set()
        try:
            # proof：proof.db.proof_case.resource_id（跨 DB 分開查）
            try:
                p = sqlite3.connect(r"C:\projects\meta\proof\proof.db")
                try:
                    proved_ids = {r[0] for r in p.execute(
                        "SELECT DISTINCT resource_id FROM proof_case"
                        " WHERE resource_id IS NOT NULL AND is_active = 1")}
                finally:
                    p.close()
            except sqlite3.Error:
                proved_ids = set()

            # 一次過攞晒（避免逐個查）
            rows = {}
            for i in range(0, len(resource_ids), 500):
                chunk = resource_ids[i:i + 500]
                ph = ",".join("?" * len(chunk))
                for r in reg.execute(
                        f"SELECT id, meta, is_active, type_id FROM registry"
                        f" WHERE id IN ({ph})", chunk):
                    rows[r["id"]] = r

            for rid in resource_ids:
                r = rows.get(rid)
                # 1. 存在
                exists = r is not None
                checks.append({
                    "name": f"resource_exists:{rid}", "type": "resource_exists",
                    "passed": exists,
                    "detail": f"{rid} 存在" if exists else f"{rid} 唔存在（registry 冇）"})
                if not exists:
                    continue
                # 2. active
                active = r["is_active"] == 1
                checks.append({
                    "name": f"resource_active:{rid}", "type": "resource_active",
                    "passed": active,
                    "detail": f"{rid} active" if active else f"{rid} 唔 active（is_active=0）"})
                # 3. proof
                proved = rid in proved_ids
                checks.append({
                    "name": f"resource_proved:{rid}", "type": "resource_proved",
                    "passed": proved,
                    "detail": f"{rid} 有 proof" if proved else f"{rid} 冇 proof（proof_case 冇）"})
        finally:
            reg.close()

        # 總 check：全部過先算 ready
        all_ok = all(c["passed"] for c in checks)

        # missing 分類（自動 build 用）：逐件 missing 抽出（唔可以淨係 block）
        #   resource_exists  -> 資源唔存在（要 register build）
        #   resource_active  -> 資源停用（要 activate build）
        #   resource_proved  -> 冇證明（要 proof build）
        missing = []  # [{"resource_id", "gap", "meta"}]
        for rid in resource_ids:
            r = rows.get(rid)
            if r is None:
                missing.append({"resource_id": rid, "gap": "exists",
                                "meta": None})
            elif r["is_active"] != 1:
                missing.append({"resource_id": rid, "gap": "active",
                                "meta": r["meta"]})
            elif rid not in proved_ids:
                missing.append({"resource_id": rid, "gap": "proof",
                                "meta": r["meta"]})

        checks.append({
            "name": "resources_ready", "type": "resources_ready",
            "passed": all_ok,
            "detail": (f"{len(resource_ids)} 件食材全部 ready"
                       if all_ok else
                       f"{len(missing)} 件缺（{', '.join(m['gap'] for m in missing[:5])}）")})

        # 記錄檢查
        for c in checks:
            self.store.add_check(task_id, c["name"], c["type"], c["passed"], c["detail"])
        # 記錄 run
        total = len(checks)
        passed = sum(1 for c in checks if c["passed"])
        failed = total - passed
        run_id = self.store.add_run(task_id, total, passed, failed)
        self.store.commit()

        return {"ready": all_ok, "checks": checks, "run_id": run_id,
                "missing": missing,
                "total": total, "passed": passed, "failed": failed}

    def is_ready(self, task_id):
        """呢個 task 嘅環境 ready 未？（最後一次 schema_run）"""
        runs = self.store.runs(task_id, 1)
        if not runs:
            return {"ready": False, "reason": "未做過 schema 檢查"}
        r = runs[0]
        return {"ready": r["status"] == "ready", "run_id": r["id"],
                "total": r["total"], "passed": r["passed"], "failed": r["failed"]}

    def _check_exec_chain(self, flow_name=None, skill_id=None,
                          step_name=None):
        """執行鏈檢查：skill → flow → step 組合（worker 開工前全部驗證）

        唔可以淨係 check 食材（resource_ids）：
            - skill 唔存在              → 冇能力（廚師）
            - flow 唔存在 / 停用        → 冇食譜
            - flow 冇 step 組合          → 食譜有封面冇內容（worker 去到先炸）
            - step 嘅 action 唔存在      → 動作庫冇呢個動作

        返回 [{name, passed, detail}, ...]
        """
        import sqlite3
        import os as _os
        checks = []
        flow_name = flow_name
        SKILL_DB = r"C:\projects\meta\skill\skill.db"
        FLOW_DB = r"C:\projects\meta\flow\flow.db"
        STEP_DB = r"C:\projects\meta\step\step.db"
        # 2026-10-26：flow / step module 已刪 -> 鏈檢查 fail（誠實）

        # 1. skill_id（可選但推薦）—— 能力存在？
        if skill_id is not None:
            if not _os.path.exists(SKILL_DB):
                checks.append({
                    "name": f"skill_exists:{skill_id}",
                    "passed": False,
                    "detail": "skill module 冇能力字典"})
            else:
                skill_db = sqlite3.connect(SKILL_DB)
                skill_db.row_factory = sqlite3.Row
                try:
                    cap = skill_db.execute(
                        "SELECT id FROM module_skill WHERE id = ?",
                        (skill_id,)).fetchone()
                    ok = cap is not None
                    checks.append({
                        "name": f"skill_exists:{skill_id}",
                        "passed": ok,
                        "detail": (f"skill {skill_id} 存在" if ok
                                   else f"skill {skill_id} 唔存在")})
                finally:
                    skill_db.close()

        # 2. flow：flow_name -> flow（食譜存在 + active）
        flow_row = None
        if flow_name:
            if not _os.path.exists(FLOW_DB):
                checks.append({
                    "name": f"flow_skill:{flow_name}",
                    "passed": False,
                    "detail": "flow module 已刪（2026-10-26），冇食譜"})
            else:
                flow_db = sqlite3.connect(FLOW_DB)
                flow_db.row_factory = sqlite3.Row
                try:
                    flow_row = flow_db.execute(
                        "SELECT * FROM flow WHERE flow_name = ? AND is_active = 1",
                        (flow_name,)).fetchone()
                    if not flow_row:
                        checks.append({
                            "name": f"flow_exists:{flow_name}",
                            "passed": False,
                            "detail": f"flow '{flow_name}' 唔存在於 flow.db 或已停用"})
                    else:
                        checks.append({
                            "name": f"flow_exists:{flow_name}",
                            "passed": True,
                            "detail": f"flow '{flow_name}' → flow_id={flow_row['id']}"})
                finally:
                    flow_db.close()

        # 3. step 組合：flow 有冇 step？（食譜有內容？）
        if flow_row:
            if not _os.path.exists(STEP_DB):
                checks.append({
                    "name": f"flow_steps:{flow_row['id']}",
                    "passed": False,
                    "detail": "step module 已刪（2026-10-26），冇 step 組合"})
            else:
                step_db = sqlite3.connect(STEP_DB)
                step_db.row_factory = sqlite3.Row
                try:
                    steps = [dict(r) for r in step_db.execute(
                        "SELECT * FROM step WHERE flow_id = ? AND is_active = 1"
                        " ORDER BY id", (flow_row["id"],))]
                    if not steps:
                        checks.append({
                            "name": f"flow_steps:{flow_row['id']}",
                            "passed": False,
                            "detail": (f"flow '{flow_name}'（id={flow_row['id']}）"
                                       f"冇任何 step 組合 — worker 去到冇嘢做")})
                    else:
                        # 4. 每個 step 嘅 action 存在？（動作庫有呢個動作？）
                        actions = {r["id"]: r["action"] for r in step_db.execute(
                            "SELECT id, action FROM action WHERE is_active = 1")}
                        missing = [s for s in steps
                                   if s["action_id"] not in actions]
                        ok = not missing
                        checks.append({
                            "name": f"flow_steps:{flow_row['id']}",
                            "passed": ok,
                            "detail": (f"flow '{flow_name}' 有 {len(steps)} steps"
                                       + ("" if ok else
                                          f"，但 {len(missing)} 個 action 唔存在"
                                          f"（id {[m['action_id'] for m in missing]}）"))})
                finally:
                    step_db.close()

        # 5. step_name 指定咗 -> 存在？（可選）
        if step_name:
            if not _os.path.exists(STEP_DB):
                checks.append({
                    "name": f"step_action:{step_name}",
                    "passed": False,
                    "detail": "step module 已刪（2026-10-26），冇動作字典"})
            else:
                step_db = sqlite3.connect(STEP_DB)
                step_db.row_factory = sqlite3.Row
                try:
                    srow = step_db.execute(
                        "SELECT id FROM action WHERE action = ? AND is_active = 1",
                        (step_name,)).fetchone()
                    ok = srow is not None
                    checks.append({
                        "name": f"step_action:{step_name}",
                        "passed": ok,
                        "detail": (f"action '{step_name}' 存在（id={srow['id']}）"
                                   if ok else f"action '{step_name}' 唔存在")})
                finally:
                    step_db.close()

        return checks

    def proceed_mission(self, task_id, required_apis=0, action="run",
                        authority=None, mission_type="skill",
                        next_action=None, params=None):
        """自動鏈：schema 檢查 → ready → mission（下令）→ task（自動開工）

        schema 檢查通過先開 mission（環境 ready 先有權下令）；
        mission 記錄 authority（邊個下令）；
        再自動 enqueue 一個新 task（mission 派生嘅工作）

        params:
            task_id       = 現有 task.id（檢查對象）
            required_apis = 保留但唔用（冇 resource_ids = 唔准 proceed）
            action        = mission action（'run' 預設）
            authority     = 邊個下令（worker 名 / module 名，必填）
            mission_type  = mission 類型
            next_action   = 派生 task 嘅 next_action
            params        = 派生 task 嘅 enqueue 參數（dict）：
                            - resource_ids = 呢碟菜要嘅食材（registry.id 清單）
                                              -> 逐件 check 存在/active/proof
                            - skill_id / flow_id / step_id → mission 引用
                            - flow = 派生 task 行咩 flow（例如 sweep_run）
                            - step = step 名（可選）

        返回 {"ready": bool, "schema": {...}, "mission_id": n|None,
              "task_id": n|None（派生嘅新 task）, "blocked": str|None}
        """
        params = params or {}

        # 0. 硬閘（兩張 run 表）：preflight_run（廚房整體）+ schema_run（呢個 task）
        #    兩張都要有「最新一次 run」且通過，先准開 mission
        gates = []
        # 閘 1：preflight_run（成個 system 起飛前檢查）
        # 2026-10-26：preflight module 已刪 -> 閘 1 fail（唔可以假綠）
        try:
            from preflight import Preflight
            pf = Preflight()
            try:
                pf_summary = pf.last_summary()
            finally:
                pf.close()
        except ImportError:
            pf_summary = None
        if pf_summary is None:
            gates.append(
                {"name": "preflight_run", "passed": False,
                 "detail": "preflight 未跑過（preflight module 已刪/未跑）"})
        elif not pf_summary["ok"]:
            gates.append(
                {"name": "preflight_run", "passed": False,
                 "detail": (f"preflight 最近一次有 {pf_summary['failed']} 項失敗"
                            f"（{pf_summary['passed']}/{pf_summary['total']}，"
                            f"run_at={pf_summary['run_at']}）")})
        else:
            gates.append(
                {"name": "preflight_run", "passed": True,
                 "detail": (f"preflight {pf_summary['passed']}/{pf_summary['total']}"
                            f" 通過（run_at={pf_summary['run_at']}）")})

        # 閘 2：schema_run（呢個 task 做過 by_id 食材檢查？）
        runs = self.store.runs(task_id, 1)
        if not runs:
            gates.append(
                {"name": "schema_run", "passed": False,
                 "detail": f"task {task_id} 未做過 schema 檢查"})
        elif runs[0]["status"] != "ready":
            gates.append(
                {"name": "schema_run", "passed": False,
                 "detail": (f"task {task_id} 最近一次 schema_run"
                            f" 唔 ready（{runs[0]['failed']} 項失敗）")})
        else:
            gates.append(
                {"name": "schema_run", "passed": True,
                 "detail": f"task {task_id} schema_run ready（{runs[0]['passed']} 項通過）"})

        gate_failures = [g for g in gates if not g["passed"]]
        if gate_failures:
            return {"ready": False,
                    "gates": gates,
                    "mission_id": None, "task_id": None,
                    "blocked": "硬閘唔過："
                              + "；".join(g["detail"] for g in gate_failures)}

        # 0b. 執行鏈檢查（skill → flow → step）：唔可以淨 check 食材，
        #     能力（skill；廚師）/ 食譜（flow + step 組合）都要 ready，
        #     否則 worker 去到先炸（「step 缺失冇人知」就係呢度發生）
        flow_name = params.get("flow")
        flow_checks = self._check_exec_chain(
            flow_name=flow_name,
            skill_id=params.get("skill_id"),
            step_name=params.get("step"))
        # 冇 flow = 冇食譜，唔可以開 mission（worker 冇嘢做）
        if not flow_name:
            flow_checks.append({
                "name": "flow_required", "passed": False,
                "detail": "params['flow'] 必填（冇食譜唔可以開 mission）"})
        flow_failures = [c for c in flow_checks if not c["passed"]]
        if flow_failures:
            return {"ready": False,
                    "exec_chain": flow_checks,
                    "mission_id": None, "task_id": None,
                    "blocked": "執行鏈唔過："
                              + "；".join(c["detail"] for c in flow_failures)}

        # 1. schema 檢查（食材檢查強制：冇 resource_ids = 唔准開 mission）
        resource_ids = params.get("resource_ids")
        if not resource_ids:
            raise ValueError(
                "proceed_mission 一定要 params['resource_ids']"
                "（呢碟菜嘅食材清單）— 冇食材檢查唔可以開 mission")
        schema = self.check_environment(task_id, resource_ids=resource_ids)
        if not schema["ready"]:
            # schema 發現 missing：「唔好淨係 block」→ 自動開 build missions
            # 一件 missing = 一個 build mission（冇資源要整資源，整完先可以煮）
            missing = schema.get("missing", [])
            if not missing:
                return {"ready": False, "schema": schema,
                        "mission_id": None, "task_id": None,
                        "blocked": f"schema 未 ready（{schema['failed']} 項失敗）"}

            # gap -> build 動作（唔係假檢查，係真 build 指令）
            GAP_TO_ACTION = {
                "exists": "build_register",   # 資源唔存在 -> 註冊
                "active": "build_activate",   # 資源停用 -> 啟用
                "proof":  "build_proof",      # 冇證明 -> 建立 proof
            }
            # 2026-10-26：guard/task 已刪除 -> 唔可以自動開 build task
            #（由 caller 決定點處理 missing；呢度只報告）
            built = []
            for miss in missing:
                gap = miss["gap"]
                built.append({"mission_id": None, "task_id": None,
                              "gap": gap,
                              "resource_id": miss["resource_id"]})
            return {"ready": False,
                    "schema": schema,
                    "mission_id": None, "task_id": None,
                    "blocked": (f"schema 未 ready（{len(missing)} 件缺）"
                                f"—— guard/task 已刪，自動 build 停用"),
                    "built_missions": built}

        # 2. mission（下令；schema_run_id 授權）
        #    2026-10-26：mission module 已刪 -> 只有 task 訂單（冇獨立 mission）
        from common import Common as _Cmpre
        _cpre = _Cmpre()
        try:
            # action 名 -> 字典 id（唔可以寫死 None / 唔准自動註冊）
            act = params.get("action", action) or action
            action_id = _cpre.action_id(act)
            if not action_id:
                raise ValueError(
                    f"action '{act}' 唔喺 common.db action 字典"
                    f"（真數據 registry），唔准自動註冊")
            mid = None   # mission module 已刪（2026-10-26）
            _na2 = _cpre.status_id("NA") or _cpre.register_status("NA")
        finally:
            _cpre.close()

        # 3. 2026-10-26：guard/task 已刪除 -> 唔再自動開 task
        #    proceed_mission 只做 schema 檢查 + 返回 ready（冇 task）
        new_task_id = None
        task_flow_id = None

        return {"ready": True, "schema": schema,
                "mission_id": mid, "task_id": new_task_id,
                "blocked": None, "authority": authority}

    def check_module(self, module_id, task_id=None):
        """檢查一個 module 嘅 schema（由 module_file 表 + rule 表定義，唔係 code 寫死）

        檢查：
            1. 檔案結構 — module_file 表定義（sql/api/route/schema/__init__ 齊？）
            2. __init__  — __init__.py 有冇正確 export（from .api import X + __all__）？
            3. 規則 — rule 表定義（每條規則嘅 db_field 資源存在？）
        返回 {"ready": bool, "checks": [...]}
        """
        import os
        from definition import Definition
        try:
            from resource import Resource
        except ImportError:
            res_ok = False
        else:
            res_ok = True
        checks = []

        # 1. 檔案結構（file_required 表定義，唔再經 module_file module）
        d = Definition()
        try:
            r = d.check_module_files(module_id)
            checks.append({
                "name": "module_files", "type": "module_files",
                "passed": r["complete"],
                "detail": f"missing={r['missing']}" if r["missing"]
                          else "必需檔案齊（由 file_required 定義）"})
        finally:
            d.close()

        # 2. __init__.py 有冇正確 export（schema 幫 __init__）
        folder = None
        res = Resource() if res_ok else None
        try:
            if res is not None:
                row = res.get(module_id)
                if row:
                    name = row.get("meta", "").split(".")[0]
                    folder = os.path.join(r"C:\projects\meta", name)
                    if not os.path.isdir(folder):
                        folder = None
        finally:
            if res is not None:
                res.close()
        init_path = os.path.join(folder, "__init__.py") if folder else None
        if init_path and os.path.isfile(init_path):
            with open(init_path, encoding="utf-8") as f:
                content = f.read()
            has_import = "from .api import" in content
            has_all = "__all__" in content
            ok = has_import and has_all
            checks.append({
                "name": "init_export", "type": "init_export", "passed": ok,
                "detail": ("from .api import + __all__ 齊" if ok
                           else f"缺 {'from .api import' if not has_import else ''}"
                                f"{' / ' if not has_import and not has_all else ''}"
                                f"{'__all__' if not has_all else ''}")})
        else:
            checks.append({
                "name": "init_export", "type": "init_export", "passed": False,
                "detail": "__init__.py 唔存在"})

        # 3. 規則（rule 表）
        #    2026-10-26：rule module 已刪 -> 規則檢查 graceful（唔可以假綠）
        try:
            from rule import Rule
            rl = Rule()
            try:
                rules = rl.rules()
                for rule in rules:
                    fields = rl.fields_for_rule(rule["id"])
                    ok = len(fields) > 0
                    checks.append({
                        "name": f"rule:{rule['meta_key']}", "type": "rule",
                        "passed": ok,
                        "detail": f"{len(fields)} 個 db_field" if ok
                                  else "冇 db_field 資源"})
            finally:
                rl.close()
        except ImportError:
            checks.append({
                "name": "rules", "type": "rule",
                "passed": False,
                "detail": "rule module 已刪（2026-10-26），規則檢查停用"})

        # 記錄
        if task_id is not None:
            for c in checks:
                self.store.add_check(task_id, c["name"], c["type"],
                                     c["passed"], c["detail"])
            total = len(checks)
            passed = sum(1 for c in checks if c["passed"])
            failed = total - passed
            self.store.add_run(task_id, total, passed, failed)
            self.store.commit()

        passed = sum(1 for c in checks if c["passed"])
        return {"ready": passed == len(checks), "checks": checks,
                "total": len(checks), "passed": passed,
                "failed": len(checks) - passed}

    def checks(self, task_id=None, limit=100):
        return self.store.checks(task_id, limit)

    def close(self):
        self.store.close()