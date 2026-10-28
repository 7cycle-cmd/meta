"""rest_api.py — task REST API 入口

標準 http.server（冇第三方依賴）；統一 pattern：
    127.0.0.1:PORT  -> 每個 module 一個 REST 接口

routes：
    GET  /health
    GET  /tasks?preflight_id=&schema_id=&plan_id=&role_id=&rule_id=&tool_id=&value_id=
    POST /tasks   {"preflight_id": n, "schema_id": n, "run_id": n,
                   "plan_id": n, "role_id": n, "rule_id": n,
                   "tool_id": n, "value_id": n}

啟動：
    python -m task.rest_api --port 9200
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


import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import Task


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

    def _qs(self):
        qs = {}
        if "?" in self.path:
            for p in self.path.split("?", 1)[1].split("&"):
                if "=" in p:
                    k, val = p.split("=", 1)
                    qs[k] = val
        return qs

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        t = Task()
        try:
            if path in ("/health", ""):
                self._send(200, {"status": "ok",
                                 "module": "task",
                                 "api": "task.rest_api"})
            elif path == "/tasks":
                qs = self._qs()
                preflight_id = int(qs["preflight_id"]) if qs.get("preflight_id") else None
                schema_id = int(qs["schema_id"]) if qs.get("schema_id") else None
                plan_id = int(qs["plan_id"]) if qs.get("plan_id") else None
                role_id = int(qs["role_id"]) if qs.get("role_id") else None
                rule_id = int(qs["rule_id"]) if qs.get("rule_id") else None
                tool_id = int(qs["tool_id"]) if qs.get("tool_id") else None
                value_id = int(qs["value_id"]) if qs.get("value_id") else None
                self._send(200, {"tasks": t.tasks(
                    preflight_id=preflight_id, schema_id=schema_id,
                    plan_id=plan_id, role_id=role_id, rule_id=rule_id,
                    tool_id=tool_id, value_id=value_id)})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            t.close()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = {}
        if length:
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                body = {}
        path = self.path.split("?", 1)[0].rstrip("/")
        t = Task()
        try:
            if path == "/tasks":
                preflight_id = body.get("preflight_id")
                schema_id = body.get("schema_id")
                run_id = body.get("run_id")
                if not preflight_id or not schema_id or not run_id:
                    self._send(400, {"error": "需要 preflight_id + schema_id + run_id"})
                else:
                    tid = t.add_task(preflight_id, schema_id, run_id,
                                     body.get("plan_id"),
                                     body.get("role_id"),
                                     body.get("rule_id"),
                                     body.get("tool_id"),
                                     body.get("value_id"))
                    self._send(200, {"task_id": tid})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            t.close()


def main(port=9200):
    print(f"task rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9200
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)