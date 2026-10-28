"""rest_api.py — skill REST API 入口

標準 http.server（冇第三方依賴）；統一 pattern：
    127.0.0.1:PORT  -> 每個 module 一個 REST 接口

routes：
    GET  /health
    GET  /registry
    POST /registry   {"name": "...", "resource_formula_id": n, "resource_structure_id": n}

啟動：
    python -m skill.rest_api --port 9500
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

from .api import Skill


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

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        s = Skill()
        try:
            if path in ("/health", ""):
                self._send(200, {"status": "ok",
                                 "module": "skill",
                                 "api": "skill.rest_api"})
            elif path == "/registry":
                self._send(200, {"registry": s.registry()})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            s.close()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = {}
        if length:
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                body = {}
        path = self.path.split("?", 1)[0].rstrip("/")
        s = Skill()
        try:
            if path == "/registry":
                name = body.get("name")
                if not name:
                    self._send(400, {"error": "需要 name"})
                else:
                    sid = s.register(name, body.get("resource_formula_id"),
                                     body.get("resource_structure_id"))
                    self._send(200, {"skill_id": sid})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            s.close()


def main(port=9500):
    print(f"skill rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9500
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)
