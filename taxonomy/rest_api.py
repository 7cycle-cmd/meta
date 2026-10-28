"""rest_api.py — taxonomy 嘅 REST API 伺服器（JSON 登記 + 搜尋）

worker 可以透過 HTTP 用 JSON 登記 / 搜尋 taxonomy：

    GET  /categories          列出大類（tree）
    GET  /items?tree=T        列出分類項目（registry，可按 tree 篩選）
    GET  /modules             列出全部 module
    GET  /skills              列出全部 skill
    GET  /channels            列出全部 channel
    POST /register            {"module": "..."} / {"skill": "..."} / {"channel": "..."}
    POST /search              {"module": "..."} / {"skill": "..."} / ...
    GET  /dump                成個倒出做 JSON
    GET  /health              健康檢查

用法：
    python -m taxonomy.rest_api [--port 9000]
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---- ast shadow 保衛（2026-10-27：同 terminology 一樣）----
# C:\projects\meta\ast\ shadow 咗標準庫 ast -> traceback 崩潰 -> 連線斷。
_ast_mod = sys.modules.get("ast")
if _ast_mod is None or (getattr(_ast_mod, "__file__", "") or "").startswith(
        r"C:\projects\meta"):
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

from .api import Taxonomy
from .sql import SqlStore


class ApiHandler(BaseHTTPRequestHandler):
    # ---------------- helpers ----------------
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _qs(self):
        """拆 query string -> dict（首個值）"""
        if "?" not in self.path:
            return {}
        q = dict(p.split("=", 1) for p in
                 self.path.split("?", 1)[1].split("&") if "=" in p)
        return q

    def log_message(self, *args):
        pass

    # ---------------- GET ----------------
    def do_GET(self):
        reg = SqlStore()
        try:
            if self.path.startswith("/items"):
                tree = None
                if "?tree=" in self.path:
                    tree = self.path.split("?tree=", 1)[1].split("&")[0]
                self._send(200, {"items": reg.items(tree)})
            elif self.path == "/modules":
                self._send(200, {"modules": reg.items("module")})
            elif self.path == "/categories":
                self._send(200, {"categories": reg.categories()})
            elif self.path == "/skills":
                self._send(200, {"skills": reg.items("skill")})
            elif self.path == "/channels":
                self._send(200, {"channels": reg.items("channel")})
            elif self.path == "/dump":
                self._send(200, reg.dump())
            elif self.path == "/health":
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "唔知嘅 route"})
        finally:
            reg.close()

    # ---------------- POST ----------------
    def do_POST(self):
        reg = SqlStore()
        try:
            body = self._read_body()
            if self.path == "/register":
                result = reg.register_json(body)
                code = 200 if result.get("status") == "ok" else 400
                self._send(code, result)
            elif self.path == "/search":
                self._send(200, reg.search(body))
            else:
                self._send(404, {"error": "唔知嘅 route"})
        except Exception as e:
            self._send(500, {"error": str(e)})
        finally:
            reg.close()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description="taxonomy REST API")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ApiHandler)
    print(f"✅ taxonomy API 伺服器起動: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()


if __name__ == "__main__":
    main()