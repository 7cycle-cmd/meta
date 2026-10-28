"""rest_api.py — tool REST API 入口

標準 http.server（冇第三方依賴）；統一 pattern：
    127.0.0.1:PORT  -> 每個 module 一個 REST 接口

routes：
    GET  /health
    GET  /tools?module_id=&skill_id=
    POST /tools   {"module_id": n, "skill_id": n,
                   "REST_API_WRITE_id": n, "REST_API_READ_id": n}

啟動：
    python -m tool.rest_api --port 9100
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

from .api import Tool


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
        t = Tool()
        try:
            if path in ("/health", ""):
                self._send(200, {"status": "ok",
                                 "module": "tool",
                                 "api": "tool.rest_api"})
            elif path == "/tools":
                qs = self._qs()
                module_id = int(qs["module_id"]) if qs.get("module_id") else None
                skill_id = int(qs["skill_id"]) if qs.get("skill_id") else None
                self._send(200, {"tools": t.tools(module_id=module_id,
                                                  skill_id=skill_id)})
            elif path == "/write-apis":
                qs = self._qs()
                module_id = int(qs["module_id"]) if qs.get("module_id") else None
                self._send(200, {"write_apis": t.write_apis(module_id)})
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
        t = Tool()
        try:
            if path == "/tools":
                module_id = body.get("module_id")
                if not module_id:
                    self._send(400, {"error": "需要 module_id"})
                else:
                    tid = t.add_tool(module_id, body.get("skill_id"),
                                     body.get("REST_API_WRITE_id"),
                                     body.get("REST_API_READ_id"))
                    self._send(200, {"tool_id": tid})
            elif path == "/write-apis":
                module_id = body.get("module_id")
                rest_api = body.get("rest_api")
                if not module_id or not rest_api:
                    self._send(400, {"error": "需要 module_id + rest_api"})
                else:
                    wid = t.add_write_api(module_id, rest_api)
                    self._send(200, {"write_api_id": wid})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            t.close()


def main(port=9100):
    print(f"tool rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9100
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)