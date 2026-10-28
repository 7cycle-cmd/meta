"""rest_api.py — template REST API 入口

標準 http.server（冇第三方依賴）；統一 pattern：
    127.0.0.1:PORT  -> 每個 module 一個 REST 接口

    GET  /health                   健康檢查
    GET  /tables                   列出全部表
    GET  /counts                   每張表行數
    GET  /table?name=flow          攞一張表內容（limit 可選）

    Proof 系統（2026-10-27 用戶設計）：
    GET  /flows                    列出全部 flow
    GET  /flow-steps?flow=name     一個 flow 嘅 steps
    GET  /run-flow?flow=&value=    行一條 flow（寫 run）
    GET  /flow-runs?limit=20       執行記錄
    GET  /formulas                 列出全部 formula
    GET  /formula?id=1             一條 formula 全檢視
    GET  /cut-formula?id=1         公式切粒
    GET  /exec-formula?id=1&k=v    執行 formula（params 入 query）

啟動：
    python -m template.rest_api --port 9500
"""
import sys

# ---- ast shadow 保衛（2026-10-27 fix）----
# C:\projects\meta\ast\ 資料夾 shadow 咗標準庫 ast -> traceback.print_exc()
# 內部 ast.parse() 崩潰 -> HTTP connection 被切斷（連 error JSON 都收唔到）。
# 喺其他地方 import traceback 之前，確保 sys.modules['ast'] = 標準庫 ast。
_ast_mod = sys.modules.get("ast")
if _ast_mod is None or (getattr(_ast_mod, "__file__", "") or "").startswith(r"C:\projects\meta"):
    _keep = [p for p in sys.path if p not in ("", r"C:\projects\meta")]
    _save = sys.path[:]
    try:
        sys.path = _keep
        import ast as _stdlib_ast
        sys.modules["ast"] = _stdlib_ast
    except Exception:
        pass
    finally:
        sys.path = _save


import argparse
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class ApiHandler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

    def _qs(self):
        """拆 query string -> dict（首個值）"""
        if "?" not in self.path:
            return {}
        q = urllib.parse.parse_qs(self.path.split("?", 1)[1])
        return {k: v[0] for k, v in q.items()}

    def _check_token(self, qs):
        """rest_api 守衛（2026-10-26：guard 只保留喺 HTTP 入口）"""
        tok = qs.get("token")
        if not tok:
            hdr = self.headers.get("X-API-Token")
            if hdr:
                tok = hdr
        if not tok:
            raise ValueError("需要 ?token=（guard.db registry 嘅有效 token）")
        from guard import Guard
        g = Guard()
        try:
            ok = g.valid(tok)
        finally:
            g.close()
        if not ok:
            raise ValueError(f"token '{tok}' 無效（guard.db registry 查無 / 已停用）")
        return tok

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        qs = self._qs()
        try:
            if path == "/health" or path == "":
                self._send(200, {"status": "ok",
                                 "module": "template",
                                 "api": "template.rest_api"})
                return
            self._check_token(qs)
            from template import Template
            t = Template()
            try:
                if path == "/tables":
                    self._send(200, {"tables": t.tables()})
                elif path == "/counts":
                    self._send(200, {"counts": t.table_counts()})
                elif path == "/table":
                    name = qs.get("name")
                    if not name:
                        self._send(400, {"error": "需要 ?name=<表名>"})
                        return
                    limit = int(qs.get("limit", 100))
                    try:
                        self._send(200, {"table": name,
                                         "rows": t.table(name, limit)})
                    except Exception as e:
                        self._send(400, {"error": str(e)})
                # ---------- Proof 系統（2026-10-27 用戶設計）----------
                elif path == "/flows":
                    self._send(200, {"flows": t.flows()})
                elif path == "/flow-steps":
                    flow = qs.get("flow")
                    if not flow:
                        self._send(400, {"error": "需要 ?flow=<name>"})
                        return
                    self._send(200, {"flow": flow,
                                     "steps": t.flow_steps(flow)})
                elif path == "/run-flow":
                    flow = qs.get("flow")
                    value = qs.get("value")
                    if not flow or value is None:
                        self._send(400, {"error": "需要 ?flow= & ?value="})
                        return
                    self._send(200, t.run_flow(flow, value))
                elif path == "/flow-runs":
                    limit = int(qs.get("limit", 20))
                    self._send(200, {"runs": t.flow_runs(limit)})
                elif path == "/formulas":
                    self._send(200, {"formulas": t.formulas()})
                elif path == "/formula":
                    fid = qs.get("id")
                    if not fid:
                        self._send(400, {"error": "需要 ?id=<formula id>"})
                        return
                    d = t.formula(int(fid))
                    if not d:
                        self._send(404, {"error": f"formula {fid} 唔存在"})
                        return
                    self._send(200, d)
                elif path == "/cut-formula":
                    fid = qs.get("id")
                    if not fid:
                        self._send(400, {"error": "需要 ?id=<formula id>"})
                        return
                    self._send(200, {"formula_id": int(fid),
                                     "tokens": t.cut_formula(int(fid))})
                elif path == "/exec-formula":
                    fid = qs.get("id")
                    if not fid:
                        self._send(400, {"error": "需要 ?id=<formula id>"})
                        return
                    params = {k: v for k, v in qs.items() if k != "id"}
                    self._send(200, t.execute_formula(int(fid), params))
                # ---------- Evidence（2026-10-27 自動閉環）----------
                elif path == "/evidences":
                    limit = int(qs.get("limit", 50))
                    self._send(200, {"evidences": t.evidences(limit)})
                elif path == "/evidence-summary":
                    self._send(200, t.evidence_summary())
                elif path == "/gen-evidence":
                    targets = qs.get("targets")
                    tl = [x.strip() for x in targets.split(",")
                          if x.strip()] if targets else []
                    res = t.gen_evidence_formulas(tl)
                    self._send(200, res)
                # ---------- HTTP proof（2026-10-28 用戶：postman 執行記錄）----------
                elif path == "/http-proof":
                    # 記錄一次 HTTP 證明（postman 打 API 嘅結果）
                    # ?method=&url=&status=&formula_id=&description=
                    # 成功（2xx）= is_match 1；其他 = 0
                    method = qs.get("method")
                    url = qs.get("url")
                    status = qs.get("status")
                    formula_id = qs.get("formula_id")
                    if not method or not url or status is None:
                        self._send(400, {"error": "需要 ?method=&url=&status="})
                        return
                    try:
                        st = int(status)
                    except ValueError:
                        self._send(400, {"error": f"status 唔係數字: {status}"})
                        return
                    res = t.record_http_proof(
                        method.upper(), url, st,
                        formula_id=int(formula_id) if formula_id else None,
                        description=qs.get("description"))
                    self._send(200, res)
                # ---------- formula_comment（2026-10-28 用戶設計）----------
                elif path == "/formula-comments":
                    # 列出 formula 註解（可 ?formula_id= 篩選）
                    fid = qs.get("formula_id")
                    self._send(200, {"rows": t.formula_comments(
                        int(fid) if fid else None)})
                elif path == "/set-formula-comment":
                    # 設定 formula 註解（?formula_id=&comment=）
                    fid = qs.get("formula_id")
                    comment = qs.get("comment")
                    if not fid or not comment:
                        self._send(400, {"error": "需要 ?formula_id=&comment="})
                    else:
                        cid = t.set_formula_comment(int(fid), comment)
                        self._send(200, {"formula_comment_id": cid,
                                         "rows": t.formula_comments(int(fid))})
                # ---------- tool formula（2026-10-28 用戶：postman type+path）----------
                elif path == "/add-tool-formula":
                    method = qs.get("method")
                    path = qs.get("path")
                    tool_id = qs.get("tool_id")
                    if not method or not path or not tool_id:
                        self._send(400, {"error": "需要 ?method=&path=&tool_id="})
                    else:
                        res = t.add_tool_formula(
                            method, path, int(tool_id),
                            body=qs.get("body"),
                            description=qs.get("description"))
                        self._send(200, res)
                elif path == "/proofs":
                    fid = qs.get("formula_id")
                    self._send(200, {"proofs": t.proofs(
                        int(fid) if fid else None)})
                else:
                    self._send(404, {"error": f"唔知 route: {path}"})
            finally:
                t.close()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send(500, {"error": str(e)})

    do_POST = do_GET  # 統一 GET 處理（demonstration 夠用）


def main(argv=None):
    ap = argparse.ArgumentParser(description="template REST API")
    ap.add_argument("--port", type=int, default=9500)
    a = ap.parse_args(argv)
    httpd = ThreadingHTTPServer(("127.0.0.1", a.port), ApiHandler)
    print(f"template rest_api @ http://127.0.0.1:{a.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()