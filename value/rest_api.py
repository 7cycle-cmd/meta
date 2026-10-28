"""rest_api.py — value REST API

routes：
    GET  /health
    GET  /values?taxonomy_id=        列出值（可按 module 篩選）
    GET  /value/<id>                 攞一個值
    GET  /value/by-value?value=xxx   按值查
    GET  /registry                   值資產 registry（即 value 表）
    GET  /count                      值數量
    POST /values   {"value": "...", "taxonomy_id": n}   新增值
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

from .api import Value


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
        v = Value()
        try:
            if path in ("/health", ""):
                self._send(200, {"status": "ok", "module": "value"})
            elif path == "/values":
                qs = self._qs()
                tid = int(qs["taxonomy_id"]) if qs.get("taxonomy_id") else None
                self._send(200, {"values": v.list(taxonomy_id=tid)})
            elif path == "/registry":
                # value 表本身就係 registry（值資產）
                self._send(200, {"registry": v.list()})
            elif path == "/count":
                self._send(200, {"count": v.count()})
            elif path == "/value/by-value":
                qs = self._qs()
                val = qs.get("value")
                if not val:
                    self._send(400, {"error": "需要 value"})
                else:
                    self._send(200, v.by_value(val) or {"error": "唔存在"})
            elif path.startswith("/value/"):
                vid = int(path.rsplit("/", 1)[1])
                self._send(200, v.get(vid) or {"error": "唔存在"})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            v.close()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = {}
        if length:
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                body = {}
        path = self.path.split("?", 1)[0].rstrip("/")
        v = Value()
        try:
            if path == "/values":
                val = body.get("value")
                if not val:
                    self._send(400, {"error": "需要 value"})
                else:
                    vid = v.add(val, body.get("taxonomy_id"))
                    self._send(200, {"value_id": vid})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            v.close()


def main(port=9800):
    print(f"value rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9800
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)