"""rest_api.py — terminology 嘅 REST API 伺服器（標準庫 http.server，零依賴）

自己擁有執行引擎：flows / flow-steps / run / runs（唔 import question module）。

    GET  /health                健康檢查
    GET  /flows                 列出驗證鏈
    GET  /flow-steps?flow=spec  列出一個 flow 嘅步驟（test / operator / expected）
    GET  /run?flow=spec        提交一個值，行 flow，自動判定
         &value=build
         &answers={"qs":0}     （可選：手動 answers；留空 = 全部自動）
    GET  /runs                 最近執行記錄（證明）
    GET  /terms                術語列表（原有能力）
    GET  /word-proof?value=data 一個 word 嘅完整證明（registry + 證據 + 來源）

守衛：所有 route（health 除外）要 ?token=（guard.db registry 有效 token）。

用法：
    python -m terminology.rest_api [--port 8500]

例子：
    curl "http://127.0.0.1:8500/run?flow=single_word&value=build&token=terminology.api"
    curl "http://127.0.0.1:8500/word-proof?value=data&token=terminology.api"
    curl "http://127.0.0.1:8500/runs"
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
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

META = r"C:\projects\meta"

def _run_flow(flow_name, answers=None, value=None):
    """行一個 terminology flow（自己嘅引擎，唔 import question）

    answers = None -> store._auto_answers 自動計（引擎自己擁有）
    返回：run_flow 結果 + task_id + flow
    """
    from terminology import Terminology
    t = Terminology()
    try:
        if answers is not None:
            # JSON key 係字串（"11"）-> 轉 int（question_id 係 int）
            answers = {int(k): v for k, v in answers.items()}
        res = t.run_flow(flow_name, answers, value=value, save=True)
        flow_row = t.store.conn.execute(
            "SELECT id, flow_name FROM flow WHERE flow_name = ?"
            " AND is_active = 1", (flow_name,)).fetchone()
        res["flow"] = {
            "id": flow_row["id"] if flow_row else None,
            "name": flow_row["flow_name"] if flow_row else flow_name,
        }
        return res
    finally:
        t.close()

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
        """rest_api 守衛（2026-10-26：guard 只保留喺 HTTP 入口）

        token 由 ?token=xxx 或 X-API-Token header 提供，
        喺 guard.db registry 驗證（存在 + is_active=1）。
        冇 token / token 無效 -> 直接回 401 JSON，返回 False。
        """
        tok = qs.get("token")
        if not tok:
            # header fallback
            hdr = self.headers.get("X-API-Token")
            if hdr:
                tok = hdr
        if not tok:
            self._send(401, {"error": "需要 ?token=（guard.db registry 嘅有效 token）"})
            return False
        from guard import Guard
        g = Guard()
        try:
            ok = g.valid(tok)
        finally:
            g.close()
        if not ok:
            self._send(401, {"error": f"token '{tok}' 無效（guard.db registry 查無 / 已停用）"})
            return False
        return tok

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        qs = self._qs()
        try:
            if path == "/health" or path == "":
                self._send(200, {"status": "ok",
                                 "module": "terminology",
                                 "api": "terminology.api_server"})
                return
            # 守衛：HTTP 入口一定要有效 token（guard 只留喺度）
            if not self._check_token(qs):
                return
            from terminology import Terminology
            t = Terminology()
            try:
                if path == "/flows":
                    self._send(200, {"flows": t.flows()})
                elif path == "/flow-steps":
                    name = qs.get("flow", "spec")
                    self._send(200, {"flow": name,
                                     "steps": t.flow_steps(name)})
                elif path == "/run":
                    name = qs.get("flow", "spec")
                    value = qs.get("value")
                    if value is not None:
                        value = urllib.parse.unquote(value)
                    answers = None
                    if qs.get("answers"):
                        answers = json.loads(qs["answers"])
                    res = _run_flow(name, answers, value)
                    self._send(200, res)
                elif path == "/branches":
                    rid = qs.get("run_id")
                    if rid:
                        self._send(200, {"branches": t.branches(int(rid))})
                    else:
                        self._send(200, {"branches": t.branches()})
                elif path == "/next-flows":
                    self._send(200, {"next_flows": t.next_flows()})
                elif path == "/add-branch":
                    flow = qs.get("flow")
                    condition = qs.get("condition")
                    status = qs.get("status")
                    target = qs.get("target")
                    if not flow or not condition or status is None \
                            or not target:
                        self._send(400, {"error":
                                         "需要 ?flow=&condition=&status=0/1&target="})
                    else:
                        nfid = t.add_branch_rule(
                            flow, condition, int(status), target)
                        self._send(200, {"next_flow_id": nfid,
                                         "rules": t.next_flows()})
                elif path == "/runs":
                    self._send(200, {"runs": t.flow_runs()})
                elif path == "/terms":
                    self._send(200, {"terms": t.list_terms()})
                elif path == "/bind":
                    value = qs.get("value")
                    run_id = qs.get("run_id")
                    cond = qs.get("condition", "industry")
                    if not value or not run_id:
                        self._send(400, {"error": "需要 ?value=&run_id="})
                    else:
                        eid = t.record_evidence(value, int(run_id), cond)
                        self._send(200, {"evidence": eid,
                                          "value": value,
                                          "run_id": int(run_id),
                                          "condition": cond,
                                          "industries": t.word_industries(value)})
                elif path == "/word-industries":
                    value = qs.get("value")
                    if not value:
                        self._send(400, {"error": "需要 ?value="})
                    else:
                        self._send(200, {"value": value,
                                         "industries": t.word_industries(value)})
                elif path == "/unbind":
                    value = qs.get("value")
                    run_id = qs.get("run_id")
                    if not value or not run_id:
                        self._send(400, {"error": "需要 ?value=&run_id="})
                    else:
                        ok = t.unbind_word_industry(value, int(run_id))
                        self._send(200, {"removed": ok})
                elif path == "/evidence":
                    value = qs.get("value")
                    cond = qs.get("condition")
                    if not value:
                        self._send(400, {"error": "需要 ?value="})
                    else:
                        self._send(200, {"value": value,
                                         "evidence": t.evidence_of(
                                             value, cond)})
                elif path == "/word-proof":
                    value = qs.get("value")
                    if not value:
                        self._send(400, {"error": "需要 ?value="})
                    else:
                        self._send(200, t.word_proof(
                            urllib.parse.unquote(value)))
                elif path == "/source-register":
                    # 設定 / 列出詞 -> source 選擇（2026-10-27 表話事）
                    word = qs.get("word")
                    source_id = qs.get("source_id")
                    if word and source_id:
                        try:
                            rid = t.set_source_for_word(
                                urllib.parse.unquote(word),
                                int(source_id), "api")
                            self._send(200, {"source_register_id": rid,
                                             "word": word,
                                             "source_id": int(source_id),
                                             "rows": t.source_register_rows()})
                        except Exception as exc:
                            self._send(400, {"error": str(exc)})
                    else:
                        self._send(200, {"rows": t.source_register_rows()})
                elif path == "/get-source":
                    # 攞一個詞用邊個 source（source_register 表話事）
                    # 冇 word -> 後備 source
                    word = qs.get("word")
                    if word:
                        self._send(200, {"word": word,
                                         "source_id": t.get_source(
                                             urllib.parse.unquote(word))})
                    else:
                        self._send(200, {"source_id": t.get_source()})
                elif path == "/verify-source":
                    word = qs.get("word")
                    if not word:
                        self._send(400, {"error": "需要 ?word="})
                    else:
                        self._send(200, {"word": word,
                                         "proof": t.verify_source(
                                             urllib.parse.unquote(word))})
                elif path == "/proof-source":
                    word = qs.get("word")
                    if not word:
                        self._send(400, {"error": "需要 ?word="})
                    else:
                        self._send(200, t.proof_source(
                            urllib.parse.unquote(word)))
                else:
                    self._send(404, {"error": f"唔知 route: {path}"})
            finally:
                t.close()
        except Exception as e:
            # 2026-10-27 fix：呢度 run 喺 ast shadow 環境 -> 用標準庫 traceback
            # （未防範之前，print_exc 內部 ast.parse 崩潰 -> 連線被切斷）
            import traceback as _tb
            _tb.print_exc()
            self._send(500, {"error": str(e)})

    do_POST = do_GET  # 統一 GET 處理（demonstration 夠用）

def main(argv=None):
    p = argparse.ArgumentParser(description="terminology REST API")
    p.add_argument("--port", type=int, default=8500)
    a = p.parse_args(argv)
    httpd = ThreadingHTTPServer(("127.0.0.1", a.port), ApiHandler)
    print(f"terminology api_server @ http://127.0.0.1:{a.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0

if __name__ == "__main__":
    sys.exit(main())