"""rest_api.py — structure REST API 入口（結構層字典）

標準 http.server（冇第三方依賴）；統一 pattern：
    127.0.0.1:PORT  -> 每個 module 一個 REST 接口

端點：
    GET /health                   健康檢查
    GET /structure-types          實體類型字典（1=package 2=file 3=db_table 4=db_field 5=db 6=root）
    GET /structure-addresses      實體地址字典（structure_address：type -> value）
    GET /structure-taxonomies     樹層 ↔ 實體類型映射（structure_taxonomy）
    GET /structure-files?module_id=N  實體檔案清單（file 層 = structure_module 真檔名）
    GET /table-definitions        表定義清單
    GET /data-types              欄位格式字典（db_field_setting 組合）
    GET /field-settings          欄位規格組合表（db_field_setting）
    GET /db-field-formats        欄位格式字典（db_field_format，原子 token）
    GET /field-uniques           unique 欄位名（db_field_unique）
    GET /field-xxxxs             欄位規格組合（db_field_setting，alias）
    GET /field-checks            CHECK 約束（db_field_check）

啟動：
    python -m structure.rest_api --port 9500
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
        from structure import Structure
        s = Structure()
        try:
            if path in ("/health", ""):
                self._send(200, {"status": "ok",
                                 "module": "structure",
                                 "api": "structure.rest_api"})
                return
            self._check_token(qs)
            if path == "/structure-types":
                self._send(200,
                           {"structure_types": s.list_structure_types()})
            elif path == "/structure-addresses":
                self._send(200,
                           {"structure_addresses":
                            s.list_structure_addresses()})
            elif path == "/structure-taxonomies":
                self._send(200,
                           {"structure_taxonomies":
                            s.list_structure_taxonomies()})
            elif path == "/structure-files":
                mid = qs.get("module_id")
                files = s.list_structure_files(
                    int(mid) if mid else None)
                self._send(200, {"structure_files": files})
            elif path == "/structure-functions":
                # function 地址層（2026-10-28 用戶設計）
                mid = qs.get("module_id")
                funcs = s.list_structure_functions(
                    int(mid) if mid else None)
                self._send(200, {"structure_functions": funcs})
            elif path == "/sync-structure-functions":
                # AST 掃描 function 地址（?module= 可選）
                mod = qs.get("module")
                res = s.sync_structure_functions(mod)
                self._send(200, res)
            elif path == "/table-definitions":
                self._send(200,
                           {"table_definitions":
                            s.list_table_definitions()})
            elif path == "/data-types":
                self._send(200, {"data_types": s.list_data_types()})
            elif path == "/field-settings":
                self._send(200,
                           {"field_settings":
                            s.list_db_field_settings()})
            elif path == "/db-field-formats":
                self._send(200,
                           {"db_field_formats":
                            s.list_db_field_formats()})
            elif path == "/field-uniques":
                self._send(200,
                           {"field_uniques": s.list_db_field_uniques()})
            elif path == "/field-xxxxs":
                self._send(200,
                           {"field_xxxxs": s.list_db_field_xxxxs()})
            elif path == "/field-checks":
                xid = qs.get("db_field_setting_id")
                self._send(200,
                           {"field_checks": s.list_db_field_checks(
                               int(xid) if xid else None)})
            elif path == "/default-values":
                self._send(200, {"default_values": s.list_default_values()})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            s.close()

    def do_POST(self):
        """POST：管理寫入（default-value-add / default-value-remove）

        POST /default-value-add?type=SLUG&value=untitled
        POST /default-value-remove?type=SLUG
        """
        import urllib.parse
        path = self.path.split("?", 1)[0].rstrip("/")
        qs = self._qs()
        try:
            self._check_token(qs)
            from structure import Structure
            s = Structure()
            try:
                if path == "/default-value-add":
                    name = qs.get("type")
                    value = qs.get("value")
                    if not name or value is None:
                        self._send(400, {"error": "需要 ?type=<型別名>&value=<預設值>"})
                        return
                    # 型別名 -> id
                    tid = None
                    for r in s.list_data_types():
                        if r.get("type_name", "").upper() == name.upper():
                            tid = r["id"]
                            break
                    if not tid:
                        self._send(400, {"error": f"型別唔存在: {name}"})
                        return
                    did = s.add_default_value(tid, value)
                    self._send(200, {"default_value_id": did,
                                     "type": name, "value": value})
                elif path == "/default-value-remove":
                    name = qs.get("type")
                    if not name:
                        self._send(400, {"error": "需要 ?type=<型別名>"})
                        return
                    tid = None
                    for r in s.list_data_types():
                        if r.get("type_name", "").upper() == name.upper():
                            tid = r["id"]
                            break
                    if not tid:
                        self._send(400, {"error": f"型別唔存在: {name}"})
                        return
                    ok = s.remove_default_value(tid)
                    self._send(200, {"removed": ok, "type": name})
                else:
                    self._send(404, {"error": f"唔知 route: {path}"})
            finally:
                s.close()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send(500, {"error": str(e)})

def main(port=9500):
    print(f"structure rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()

if __name__ == "__main__":
    _port = 9500
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)
