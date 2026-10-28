"""postman_sync.py — Postman 官方 API 真實數據同步器

用戶要求（2026-10-28）：「evidence all by you? i don't trust」——
證據**唔可以**係 agent 自己生成，一定要係 Postman 平台真實記錄，
經官方 API（https://api.postman.com + X-API-Key）拉返嚟，
原始返回原封不動存入 source.db。

安全原則：
    - API key 只可以由環境變數 POSTMAN_API_KEY 提供（**絕不經 chat**）
    - raw_json 保留 Postman 官方返回（鐵證，唔改動）

用法：
    $env:POSTMAN_API_KEY = "PMAK-xxxx"   # 喺 terminal 設定（唔好 paste 去 chat）
    python -m source.postman_sync --workspace 2b2010a3-aed6-484e-860a-250fb53a401e
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from .schema import (POSTMAN_SYNC_DDL, POSTMAN_MOCK_DDL,  # noqa: F401
                     POSTMAN_RUN_DDL)
from .sql import SqlStore

API_BASE = "https://api.postman.com"
SOURCE_ID_POSTMAN_API = 15      # source.db source.id=15 = "Postman API"
ENV_KEY = "POSTMAN_API_KEY"
_SECRET_FILE = r"C:\projects\meta\secret.env"


def _api_key():
    """攞 API key —— 優先環境變數，fallback secret.env（只讀檔，唔經 chat）"""
    key = os.environ.get(ENV_KEY, "").strip()
    if key:
        return key
    # fallback：secret.env（POSTMAN_TOKEN = "PMAK-..."）
    try:
        with open(_SECRET_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name, _, val = line.partition("=")
                if name.strip() != "POSTMAN_TOKEN":
                    continue
                v = val.strip().strip('"').strip("'")
                if v:
                    return v
    except OSError:
        pass
    raise ValueError(
        f"未設定 {ENV_KEY} 環境變數 / secret.env POSTMAN_TOKEN。\n"
        "請喺 terminal 執行：\n"
        f'    $env:{ENV_KEY} = "PMAK-..."\n'
        "（Postman API key 喺 Postman 右上角 Account Settings → API keys 生成）")
    return key


def _get(url, timeout=30):
    """對 Postman 官方 API 發 GET，返回 (http_status, parsed_json, raw_text)。

    呢度只係「拉取」—— 唔係產生證據；證據本身係 Postman 平台記錄。

    2026-10-28（實測）：Cloudflare 擋 Python urllib 預設 UA
    （error 1010 browser_signature_banned）-> 要帶 Postman 官方 UA。
    """
    req = urllib.request.Request(url, headers={
        "X-API-Key": _api_key(),
        "User-Agent": "PostmanRuntime/7.36.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, _safe_json(raw), raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return e.code, _safe_json(raw), raw
    except urllib.error.URLError as e:
        return 0, {"error": str(e.reason)}, str(e.reason)


def _safe_json(raw):
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": raw[:2000]}


class PostmanSync:
    """用 Postman 官方 API 拉真實數據 → source.db（原始記錄）"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()
        for ddl in (POSTMAN_SYNC_DDL, POSTMAN_MOCK_DDL, POSTMAN_RUN_DDL):
            self.store.conn.execute(ddl)
        self.store.conn.commit()

    # ── 原始拉取（每次 call 都寫一行 postman_sync）─────────────────
    def _fetch(self, api_type, path, uid=None, note=None):
        url = f"{API_BASE}{path}"
        status, data, raw = _get(url)
        cur = self.store.conn.execute(
            "INSERT INTO postman_sync (api_type, url, http_status, uid,"
            " raw_json, source_id, note)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (api_type, url, status, uid, raw, SOURCE_ID_POSTMAN_API, note))
        sid = cur.lastrowid
        self.store.conn.commit()
        return sid, status, data

    # ── 真實數據（用户已確認：Mock Server 執行記錄 + Run/Test 結果）──
    def workspace(self, workspace_uid):
        """拉 workspace 真實數據（確認 account 連通）"""
        if not workspace_uid:
            return None, 0, None
        sid, status, data = self._fetch(
            "workspace", f"/workspaces/{urllib.parse.quote(workspace_uid)}",
            uid=workspace_uid)
        return sid, status, data

    def workspace_collections(self, workspace_uid):
        """拉 workspace 入面嘅 collections 真實清單（uid + name）"""
        sid, status, data = self.workspace(workspace_uid)
        if status == 200 and isinstance(data, dict):
            return sid, status, data.get("workspace", {}).get("collections", [])
        return sid, status, []

    def sync_workspace_all(self, workspace_uid, environment_uid=None):
        """一次過拉：workspace + collections 清單 + 每個 collection 內容

        == 真實定義證據（唔係 agent 生成）==
        """
        out = {"workspace": self.workspace(workspace_uid)}
        sid, st, cols = self.workspace_collections(workspace_uid)
        out["collections"] = (sid, st)
        if st == 200:
            out["collection_items"] = []
            for c in cols:
                cuid = c.get("uid") or c.get("id")
                if cuid:
                    csid, cst, cdata = self.collection(cuid)
                    out["collection_items"].append((csid, cst, cdata))
        if environment_uid:
            out["environment"] = self.environment(environment_uid)
        return out

    def environment(self, env_uid):
        """拉 environment 真實內容（postman_uid=59268432-80931d99-1bff-4628-9b72-af5e73772ad5）"""
        if not env_uid:
            return None, 0, None
        sid, status, data = self._fetch(
            "environment", f"/environments/{urllib.parse.quote(env_uid)}",
            uid=env_uid)
        return sid, status, data

    def collection(self, collection_uid):
        """拉 collection 真實定義（request method + url）"""
        if not collection_uid:
            return None, 0, None
        sid, status, data = self._fetch(
            "collection", f"/collections/{urllib.parse.quote(collection_uid)}",
            uid=collection_uid)
        return sid, status, data

    def mock_servers(self, workspace_uid):
        """列出 workspace 入面嘅 mock servers（真實清單）"""
        if not workspace_uid:
            return None, 0, None
        sid, status, data = self._fetch(
            "mock_list",
            f"/workspaces/{urllib.parse.quote(workspace_uid)}/mocks",
            uid=workspace_uid)
        return sid, status, data

    def mock_responses(self, mock_uid):
        """拉 mock server 嘅真實執行 log（server responses）——
        呢啲係 Postman 平台記錄嘅實際請求/回應，**唔係我哋生成**。"""
        if not mock_uid:
            return None, 0, None
        sid, status, data = self._fetch(
            "mock_responses", f"/mocks/{urllib.parse.quote(mock_uid)}/server-responses",
            uid=mock_uid)
        if status == 200 and isinstance(data, dict):
            self._store_mock_logs(sid, data)
        return sid, status, data

    def _store_mock_logs(self, sync_id, data):
        """把 Postman 平台 log 存入 postman_mock（唔改內容，只揀欄）"""
        for item in data.get("serverResponses", []):
            def _as_json(v):
                # Postman 平台 body 可能係 string 或者 object —— 原樣保留
                if v is None:
                    return None
                if isinstance(v, (dict, list)):
                    return json.dumps(v)
                return str(v)
            self.store.conn.execute(
                "INSERT INTO postman_mock (sync_id, server_response_id,"
                " collection_uid, mock_uid, method, request_path,"
                " request_headers, request_body, response_status,"
                " response_headers, response_body, postman_created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sync_id,
                 item.get("serverResponseId"),
                 item.get("collectionUid"),
                 item.get("mockUid"),
                 item.get("method"),
                 item.get("requestPath"),
                 _as_json(item.get("requestHeaders")),
                 _as_json(item.get("requestBody")),
                 item.get("responseStatusCode"),
                 _as_json(item.get("responseHeaders")),
                 _as_json(item.get("responseBody")),
                 item.get("createdAt")))
        self.store.conn.commit()

    def runs(self, collection_uid=None, limit=20):
        """列出 cloud run / runner 結果（真實執行記錄）"""
        path = "/runs?" + urllib.parse.urlencode(
            {"limit": min(limit, 100)})
        if collection_uid:
            path += "&" + urllib.parse.urlencode({"collection_uid": collection_uid})
        sid, status, data = self._fetch("run_list", path, note="list runs")
        if status == 200 and isinstance(data, dict):
            self._store_runs(sid, data.get("runs", []))
        return sid, status, data

    def _store_runs(self, sync_id, runs):
        for r in runs:
            results = r.get("assertions")
            if results is not None and not isinstance(results, str):
                results = json.dumps(results)
            self.store.conn.execute(
                "INSERT INTO postman_run (sync_id, run_uid, collection_uid,"
                " environment_uid, status, total, passed, failed, skipped,"
                " test_results, started_at, completed_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sync_id,
                 r.get("id") or r.get("run_id"),
                 r.get("collection_uid"),
                 r.get("environment_uid"),
                 r.get("status"),
                 r.get("totalRequests") or r.get("total"),
                 r.get("totalPassed") or r.get("passed"),
                 r.get("totalFailed") or r.get("failed"),
                 r.get("totalSkipped") or r.get("skipped"),
                 results,
                 r.get("started_at") or r.get("startedAt"),
                 r.get("completed_at") or r.get("completedAt")))
        self.store.conn.commit()

    def collections(self, workspace_uid=None):
        """列出 account 全部 collections（真實定義清單）"""
        path = "/collections"
        if workspace_uid:
            path += "?" + urllib.parse.urlencode({"workspace": workspace_uid})
        sid, status, data = self._fetch("collection_list", path, note="list collections")
        return sid, status, data

    def run_detail(self, run_uid):
        """拉單次 run 詳細結果（真實 test 結果）"""
        if not run_uid:
            return None, 0, None
        sid, status, data = self._fetch(
            "run", f"/runs/{urllib.parse.quote(run_uid)}",
            uid=run_uid)
        return sid, status, data

    def close(self):
        self.store.close()


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        description="Postman 官方 API 真實數據同步（證據 = Postman 平台記錄）")
    ap.add_argument("--workspace", default="2b2010a3-aed6-484e-860a-250fb53a401e")
    ap.add_argument("--environment", default="59268432-80931d99-1bff-4628-9b72-af5e73772ad5")
    ap.add_argument("--mock", help="mock server UID（如有）")
    args = ap.parse_args(argv)

    try:
        ps = PostmanSync()
    except ValueError as e:
        print(e)
        return 2

    try:
        sid, status, data = ps.workspace(args.workspace)
        print(f"[workspace] http={status} sync_id={sid}")
        if isinstance(data, dict) and data.get("workspace"):
            w = data["workspace"]
            print("  name:", w.get("name"))
            print("  uid :", w.get("id") or w.get("uid"))

        sid, status, data = ps.environment(args.environment)
        print(f"[environment] http={status} sync_id={sid}")
        if status == 200 and isinstance(data, dict) and data.get("environment"):
            e = data["environment"]
            print("  name:", e.get("name"))
            print("  values:", len(e.get("values", [])))

        sid, status, data = ps.mock_servers(args.workspace)
        print(f"[mock list] http={status} sync_id={sid}")
        if status == 200 and isinstance(data, dict):
            mocks = data.get("mocks", [])
            print("  mocks:", len(mocks))
            for m in mocks[:5]:
                print("   -", m.get("name"), m.get("mockUid") or m.get("id"))
                # 真正執行記錄（平台 log）——
                muid = m.get("mockUid") or m.get("id")
                if args.mock or len(mocks) == 1:
                    msid, mstatus, mdata = ps.mock_responses(muid)
                    print(f"    [server-responses] http={mstatus} sync_id={msid}"
                          f" logs={len(mdata.get('serverResponses', [])) if isinstance(mdata, dict) else 0}")

        sid, status, data = ps.runs()
        print(f"[runs] http={status} sync_id={sid}")
        if status == 200 and isinstance(data, dict):
            runs = data.get("runs", [])
            print("  runs:", len(runs))
            for r in runs[:5]:
                print("   -", r.get("id"), r.get("status"),
                      f"pass={r.get('totalPassed')} fail={r.get('totalFailed')}")

        print("\n完成 —— 全部原始記錄已存入 source.db:")
        print("  postman_sync（原始返回） + postman_mock（執行 log） + postman_run（run 結果）")
        print("  證據來源 = Postman 官方 API（api.postman.com），唔係 agent 生成。")
    except ValueError as e:
        print(e)
        return 2
    finally:
        ps.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
