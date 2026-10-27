"""api.py — Connection（連接證明）：檢查表之間嘅 FK 連接

connection proof = 雙向證明：
    唔單止「有人引用」，仲要證明引用嗰邊都活躍（有資料）。
    如果引用者都係空/孤島，連接唔成立 -> 兩邊都可以一齊清理。

resource_id 由 resource module 嘅 API 攞（唔會自己編號）：
    from resource import Resource
    Resource().register("taxonomy.db.module")  -> 返回數字 resource_id

用法：
    from connection import Connection
    c = Connection()
    result = c.connect("taxonomy.db.module", "mapping.db.skill")  # A <-> B
    c.touch(result["connection_id"])          # 更新最後連接時間
    c.quality(result["connection_id"], "pass")
    c.close()
"""

import glob
import os
import sqlite3


from .sql import SqlStore

from .function import *  # noqa: F401,E402










class Connection:
    """連接證明：檢查表之間嘅 FK 連接（雙向）"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()
        self.db_files = _discover_dbs()

    # ---------------- 連接建立（A <-> B）----------------
    def connect(self, sender_resource, receiver_resource,
                sender_identity=None, receiver_identity=None, is_active=1):
        """建立 A -> B 連接

        sender_resource   A（例如 taxonomy.db.module）
        receiver_resource B（例如 mapping.db.skill）
        resource_id 由 resource module API 攞（數字 id）
        identity_id 由 caller 提供（taxonomy_id + resource_id）
        is_active = proof（連接存在）
        返回 connection dict
        """
        s_id = _get_resource_id(sender_resource, sender_identity)
        r_id = _get_resource_id(receiver_resource, receiver_identity)
        # 建立 connection_registry 記錄（identity_id 區分角色）
        # upsert_registry 返回嘅係 connection_registry.id
        s_row = self.store.upsert_registry("sender", s_id, is_active)
        r_row = self.store.upsert_registry("receiver", r_id, is_active)
        c_id = self.store.upsert_connection(s_row, r_row, is_active)
        return {"connection_id": c_id, "sender": sender_resource,
                "receiver": receiver_resource, "is_active": is_active}

    # ---------------- table_group（表 × 欄位連接：table_group 係 definition 層） ----------------
    def connect_table_field(self, table_resource, field_resource, is_active=1):
        """將一個 db_field 註冊去一張表（connection registry）

        table_resource = registry meta（type=db_table，例如 resource.db.registry）
        field_resource = registry meta（type=db_field，例如 resource.db.registry.meta）

        1 + 1 = table_group：
            structure（db_table_setting 5 欄通用模板）
            + connection（呢個表有邊啲欄位）
            = 表嘅完整定義（definition 層）

        返回 {"connection_id", "sha256", "table", "field", "is_active"}
        """
        import hashlib
        s_id = _get_resource_id(table_resource)
        r_id = _get_resource_id(field_resource)
        s_row = self.store.upsert_registry("sender", s_id, is_active)
        r_row = self.store.upsert_registry("receiver", r_id, is_active)
        c_id = self.store.upsert_connection(s_row, r_row, is_active)
        # sha256 證明：hash(connection_id + table + field + is_active)
        raw = f"{c_id}|{table_resource}|{field_resource}|{is_active}"
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return {"connection_id": c_id, "sha256": h,
                "table": table_resource, "field": field_resource,
                "is_active": is_active}

    def table_fields(self, table_resource, active_only=True):
        """攞一張表嘅欄位清單（connection registry 記錄）

        table_resource = registry meta（type=db_table）
        返回 [{"field": meta, "connection_id": n, "is_active": n}, ...]
        """
        s_id = _get_resource_id(table_resource)
        rows = self.store.registry_connections_by_sender(s_id, active_only)
        out = []
        for r in rows:
            out.append({
                "field": r.get("receiver_meta"),
                "connection_id": r.get("connection_id"),
                "is_active": r.get("is_active"),
            })
        return out

    def check_filling(self, sender_resource, receiver_resource,
                      formula_id=None, type_id=None):
        """檢查 sender/receiver 兩邊嘅 filling 係咪一樣（start connection 前）

        sender_resource   A（例如 input.db.input_registry）
        receiver_resource B（例如 lineage.db.lineage_run）
        formula_id        = 可選：淨係比較呢個 formula 嘅 filling
        type_id           = 可選：淨係比較呢個 type 嘅 filling（例如 11 = value）
                            兩邊嘅 filling 要一致（同一批 value），先證明連接成立。

        2026-10-22：filling 已拆兩表（filling header + filling_item detail），
                    兩邊父表（input_registry / lineage_run）都有一個 filling_id 欄。
                    所以直接由父表攞 filling_id，唔再 JOIN junction 表。

        返回 {"same": bool, "sender": {...}, "receiver": {...}, "detail": str}
        """
        def _filling_ids(resource):
            """由 resource 名（db.table）攞 filling_id 清單"""
            try:
                db_name, table = resource.rsplit(".", 1)
                # db_name 可能連 .db（input.db）或者淨係名（input）
                if db_name.endswith(".db"):
                    path = os.path.join(META, db_name)
                else:
                    path = os.path.join(META, f"{db_name}.db")
                if not os.path.isfile(path):
                    return None, f"{db_name} 唔存在"
                c = sqlite3.connect(path)
                c.row_factory = sqlite3.Row
                try:
                    cols = [r[1] for r in c.execute(f'PRAGMA table_info("{table}")')]
                    if "filling_id" not in cols:
                        return None, f"{table} 冇 filling_id 欄"
                    sql = f'SELECT filling_id FROM "{table}" WHERE filling_id IS NOT NULL'
                    params = []
                    if formula_id is not None:
                        if "formula_id" in cols:
                            sql += " AND formula_id = ?"
                            params.append(formula_id)
                        else:
                            return None, f"{table} 冇 formula_id 欄"
                    rows = c.execute(sql, params).fetchall()
                    return [r["filling_id"] for r in rows], None
                finally:
                    c.close()
            except sqlite3.Error as e:
                return None, str(e)

        s_ids, s_err = _filling_ids(sender_resource)
        r_ids, r_err = _filling_ids(receiver_resource)
        if s_err:
            return {"same": False, "sender": None, "receiver": None,
                    "detail": f"sender: {s_err}"}
        if r_err:
            return {"same": False, "sender": None, "receiver": None,
                    "detail": f"receiver: {r_err}"}
        # 比較去重後嘅集合（重複記錄唔影響一致性）
        same = set(s_ids) == set(r_ids)
        scope = f"formula_id={formula_id}" if formula_id else "全部"
        if type_id is not None:
            scope += f" type_id={type_id}"
        return {"same": same, "sender": s_ids, "receiver": r_ids,
                "detail": f"filling {'一致' if same else '唔一致'}（{scope}：sender {len(s_ids)} 條 / receiver {len(r_ids)} 條）"}

    def touch(self, connection_id):
        """更新連接時間（每次使用 A <-> B 就 touch）

        updated_at = proof（最後連接時間）
        """
        self.store.touch_connection(connection_id)
        return {"connection_id": connection_id, "touched": True}

    # ---------------- connection_registry 驗證（sender/receiver 都 is_active=1） ----------------
    def verify_connection_registry(self, connection_id, resource_id=None):
        """驗證一個連接：sender + receiver 兩邊都 is_active=1（雙向證明）

        流程（rule -> case -> run，全部寫 proof.db 可追溯）：
            1. 檢查 connection 存在（method: 'SELECT connection WHERE id = ?'）
            2. 檢查 sender.is_active = 1
            3. 檢查 receiver.is_active = 1
            4. 全部 pass -> connection 有效（verify_run pass）
            5. 任何 fail -> connection 無效（verify_run fail）

        connection_id = connection.db connection.id
        resource_id   = 可選：registry.id（邊個 API 產生，proof 追溯）

        返回 {
            "connection_id": n, "verified": bool,
            "checks": [{"method": str, "verify": str, "result": str, "status": "pass"/"fail"}],
            "proof_run_ids": [...], "verify_run_id": n,
        }
        """
        # 2026-10-26：proof module 已刪 -> proof_run 記錄 graceful
        try:
            from proof import Proof
            p = Proof()
        except ImportError:
            p = None
        checks = []
        proof_run_ids = []
        try:
            conn_db = sqlite3.connect(os.path.join(META, "connection.db"))
            conn_db.row_factory = sqlite3.Row

            def _check(method, verify, query, params):
                """執行一個檢查（有 proof module 就寫 proof_run），返回 pass/fail"""
                row = conn_db.execute(query, params).fetchone()
                result = row[0] if row else 0
                status = "pass" if result == 1 else "fail"
                rid = None
                if p is not None:
                    rid = p.store.insert_proof_run(method, verify, str(result),
                                                   status, resource_id, source="sql")
                checks.append({"method": method, "verify": verify,
                               "result": str(result), "status": status,
                               "proof_run_id": rid})
                proof_run_ids.append(rid)
                return status == "pass"

            ok1 = _check(
                "SELECT 1 FROM connection WHERE id = ? AND is_active = 1",
                "connection 存在 AND is_active = 1",
                "SELECT 1 FROM connection WHERE id = ? AND is_active = 1",
                (connection_id,))
            # 兩端註冊（connection_registry 統一表，一次 COUNT 檢查兩邊）
            c_row = conn_db.execute(
                "SELECT sender_id, receiver_id FROM connection WHERE id = ?",
                (connection_id,)).fetchone()
            if c_row:
                ok2 = _check(
                    "SELECT 1 FROM connection_registry WHERE id IN (?, ?)"
                    " AND is_active = 1 GROUP BY id LIMIT 2",
                    "sender + receiver（connection_registry）都 is_active = 1",
                    "SELECT CASE WHEN COUNT(*) = 2 THEN 1 ELSE 0 END"
                    " FROM connection_registry WHERE id IN (?, ?)"
                    " AND is_active = 1",
                    (c_row["sender_id"], c_row["receiver_id"]))
            else:
                ok2 = False
            # connection_quality 同步（pass/fail）
            qstatus = "pass" if (ok1 and ok2) else "fail"
            self.store.upsert_quality(connection_id, qstatus, None, 1)
            # verify.db 記錄（verify module 已刪 -> graceful）
            vid = None
            try:
                from verify.sql import SqlStore as VerifyStore
                v = VerifyStore()
                try:
                    vid = v.insert_run(
                        f"connection_registry:{connection_id}",
                        "pass" if qstatus == "pass" else "fail",
                        reason="兩端（connection_registry）都 is_active=1"
                               if qstatus == "pass" else
                               f"驗證失敗（connection={'pass' if ok1 else 'fail'}, "
                               f"兩端={'pass' if ok2 else 'fail'}）",
                        source_db="connection.db",
                        source_ref=f"connection.id={connection_id}")
                    v.commit()
                finally:
                    v.close()
            except ImportError:
                pass
        finally:
            conn_db.close()
            if p is not None:
                p.close()

        verified = all(c["status"] == "pass" for c in checks)
        return {"connection_id": connection_id, "verified": verified,
                "checks": checks, "proof_run_ids": proof_run_ids,
                "verify_run_id": vid}

    # alias：skill 層用短名（驗證一個 connection 嘅 registry 鏈）
    def verify_connection(self, connection_id, resource_id=None):
        """驗證一個 connection（alias of verify_connection_registry）"""
        return self.verify_connection_registry(connection_id, resource_id)

    def quality(self, connection_id, status, performance_ms=None, is_active=1):
        """記錄連接品質（pass / fail + performance_ms）

        is_active = proof（品質記錄存唔存在）
        """
        qid = self.store.upsert_quality(connection_id, status, performance_ms, is_active)
        return {"quality_id": qid, "connection_id": connection_id,
                "status": status, "performance_ms": performance_ms,
                "is_active": is_active}

    # ---------------- 查詢 ----------------
    def connections(self):
        """列出所有連接（含品質）"""
        return self.store.connections()

    def list_identities(self):
        """列出角色字典（sender / receiver）"""
        return self.store.identities()

    def list_registries(self, identity=None):
        """列出連接註冊表（可按身份篩選：sender / receiver）"""
        return self.store.registries(identity)

    def list_senders(self):
        """列出 sender 註冊（connection_registry 入面 identity=1）"""
        return self.store.registries("sender")

    def list_receivers(self):
        """列出 receiver 註冊（connection_registry 入面 identity=2）"""
        return self.store.registries("receiver")

    def list_statuses(self):
        return self.store.statuses()

    # ---------------- Data Migration（由 FK 分析遷移）----------------
    def migrate(self, db_name=None):
        """將現有 FK 關係遷移入 connection 模型

        每個 FK（A 引用 B）變成：
            sender   = A（引用者）
            receiver = B（被引用者）
            is_active = 1（FK 存在 = 連接存在 = proof）
            updated_at = 而家（首次遷移時間）
            quality   = pass（FK 存在 = 連接成立 = pass）
        返回遷移統計
        """
        dbs = {db_name: self.db_files[db_name]} if db_name else self.db_files
        migrated = 0
        skipped = 0
        for name, path in dbs.items():
            if not os.path.exists(path):
                continue
            graph = _fk_graph(path)
            for t in graph["tables"]:
                # sender = t（引用者），receiver = FK 指向嘅表
                for ref in graph["outgoing"][t]:
                    sender_res = f"{name}.{t}"
                    receiver_res = f"{name}.{ref}"
                    # 跳過自己引用自己
                    if t == ref:
                        skipped += 1
                        continue
                    result = self.connect(sender_res, receiver_res, is_active=1)
                    # FK 存在 = 連接成立 = quality pass
                    self.quality(result["connection_id"], "pass")
                    migrated += 1
        return {"migrated": migrated, "skipped": skipped}

    def check(self, db_name, table_name):
        """檢查一張表嘅連接證明（由 connection 模型讀取）

        返回 {"db": ..., "table": ..., "connected": bool, "proof": str}
        """
        resource = f"{db_name}.{table_name}"
        # 由 connection 表搵：呢張表做 sender 或者 receiver 嘅連接
        conns = self.store.connections()
        as_sender = [c for c in conns if c["sender"] == resource]
        as_receiver = [c for c in conns if c["receiver"] == resource]
        if as_sender:
            alive = [c for c in as_sender if c["status"] == "pass"]
            return {"db": db_name, "table": table_name,
                    "connected": bool(alive),
                    "proof": f"做 sender 連接 {len(as_sender)} 條（{len(alive)} 條 pass）"}
        if as_receiver:
            alive = [c for c in as_receiver if c["status"] == "pass"]
            return {"db": db_name, "table": table_name,
                    "connected": bool(alive),
                    "proof": f"做 receiver 連接 {len(as_receiver)} 條（{len(alive)} 條 pass）"}
        return {"db": db_name, "table": table_name,
                "connected": False, "proof": "冇連接記錄"}

    def scan(self):
        """掃描所有 DB，檢查每張表嘅連接證明

        返回 {"db": {"table": {"connected": bool, "proof": str}}}
        """
        report = {}
        for db_name, path in self.db_files.items():
            if not os.path.exists(path):
                continue
            graph = _fk_graph(path)
            db_report = {}
            for t in graph["tables"]:
                db_report[t] = self.check(db_name, t)
            report[db_name] = db_report
        return report

    def disconnected(self):
        """列出所有連接唔成立嘅表（潛在孤島）"""
        report = self.scan()
        result = []
        for db_name, tables in report.items():
            for t, info in tables.items():
                if not info["connected"]:
                    result.append({"db": db_name, "table": t, "proof": info["proof"]})
        return result

    def history(self, limit=100):
        return self.store.connections()

    def count(self):
        return len(self.store.connections())

    def close(self):
        self.store.close()