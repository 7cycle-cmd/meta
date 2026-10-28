"""rest_api.py — common REST API 入口（字典層）

標準 http.server（冇第三方依賴）；統一 pattern：
    127.0.0.1:PORT  -> 每個 module 一個 REST 接口

端點：
    GET /health           健康檢查
    GET /positions        列出全部位置字典（seq 表，1-100）
    GET /position?meta=N  由位置名攞 position
    GET /seqs             列出全部 seq 字典
    GET /seq?meta=N       由位置名攞 seq

啟動：
    python -m common.rest_api --port 9500
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
import sqlite3
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
        if "?" not in self.path:
            return {}
        q = urllib.parse.parse_qs(self.path.split("?", 1)[1])
        return {k: v[0] for k, v in q.items()}

    def _check_token(self, qs):
        """rest_api 守衛（2026-10-26：guard 只保留喺 HTTP 入口）

        token 由 ?token=xxx 或 X-API-Token header 提供，
        喺 common.db token 表驗證（存在 + is_active=1）。
        """
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
        from common import Common
        c = Common()
        try:
            if path in ("/health", ""):
                self._send(200, {"status": "ok",
                                 "module": "common",
                                 "api": "common.rest_api"})
                return
            self._check_token(qs)
            if path in ("/positions", "/seqs"):
                self._send(200, {"positions": c.list_positions()})
            elif path in ("/position", "/seq"):
                meta = qs.get("meta")
                if not meta:
                    self._send(400, {"error": "需要 ?meta="})
                else:
                    r = c.get_position(meta)
                    self._send(200, r if r else {"error": f"meta={meta} 唔存在"})
            elif path == "/booleans":
                self._send(200, {"booleans": c.list_booleans()})
            elif path == "/boolean":
                val = qs.get("value")
                if not val:
                    self._send(400, {"error": "需要 ?value=0|1"})
                else:
                    r = c.get_boolean(int(val))
                    self._send(200, r if r else {"error": f"value={val} 唔存在"})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            c.close()

def main(port=9500):
    print(f"common rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()

if __name__ == "__main__":
    _port = 9500
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)
