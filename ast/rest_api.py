"""rest_api.py — ast 嘅 REST API 伺服器（標準庫 http.server，零依賴）

    GET  /health                健康檢查
    GET  /functions             列出函數字典
    GET  /classes               列出函數類別字典
    GET  /analyze?table=analyze_module  列出一個 analyze 表
    POST /scan?module=codegen   AST 掃描一個 module
    POST /scan-all              AST 掃描全部 module

用法：
    python -m ast.rest_api [--port 8501]

例子：
    curl "http://127.0.0.1:8501/functions"
    curl "http://127.0.0.1:8501/analyze?table=analyze_module"
    curl -X POST "http://127.0.0.1:8501/scan?module=codegen"
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
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

META = r"C:\projects\meta"

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parse_qs(self):
        return urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query)

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
        from ast import Ast
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = self._parse_qs()
        a = Ast()
        try:
            if path == "/health":
                self._send(200, {"status": "ok"})
                return
            self._check_token(qs)
            if path == "/functions":
                self._send(200, {"functions": a.list_functions()})
            elif path == "/classes":
                self._send(200, {"classes": a.list_function_classes()})
            elif path == "/analyze":
                table = (qs.get("table") or ["analyze_module"])[0]
                if table not in ("analyze_root", "analyze_module",
                                 "analyze_skill"):
                    self._send(400, {"error": "未知 analyze 表: %s" % table})
                    return
                self._send(200, {"table": table,
                                 "rows": a.list_analyze(table)})
            else:
                self._send(404, {"error": "not found"})
        finally:
            a.close()

    def do_POST(self):
        from ast import Ast
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = self._parse_qs()
        a = Ast()
        try:
            self._check_token(qs)
            if path == "/scan":
                module = (qs.get("module") or [""])[0]
                if not module:
                    self._send(400, {"error": "module 參數必需"})
                    return
                self._send(200, a.scan_module(module))
            elif path == "/scan-all":
                self._send(200, {"results": a.scan_all()})
            else:
                self._send(404, {"error": "not found"})
        finally:
            a.close()

def main():
    ap = argparse.ArgumentParser(description="ast REST API")
    ap.add_argument("--port", type=int, default=8501)
    args = ap.parse_args()
    print("ast REST API on http://127.0.0.1:%d" % args.port)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()

if __name__ == "__main__":
    main()
