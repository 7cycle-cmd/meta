"""rest_api.py — value REST API

routes：
    GET  /health                        健康檢查
    GET  /values?taxonomy_id=           列出值（可按 module 篩選）
    GET  /value/<id>                    攞一個值
    GET  /value/by-value?value=xxx      按值查
    GET  /registry                      值資產 registry（即 value 表）
    GET  /count                         值數量
    GET  /split-totals?value_id=        列出拆分總覽
    GET  /split-values?split_total_id=  列出拆分值
    GET  /terminology?split_value_id=   列出 terminology 授權
    GET  /can-call-terminology?split_value_id=&terminology_id=   權限檢查
    POST /values       {"value": "...", "taxonomy_id": n}                    新增值
    POST /split        {"value_id": n, "parts": ["hello", "world", "123"]}    拆分值
    POST /terminology  {"terminology_id": n, "split_value_id": n}            授權 call terminology
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
import urllib.parse
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
            elif path.startswith("/value/") and path.endswith("/proof"):
                # /value/<value>/proof —— 完整證明鏈（要喺 /value/<id> 之前）
                val = urllib.parse.unquote(
                    path[len("/value/"):-len("/proof")])
                self._send(200, v.proof_of(val))
            elif path.startswith("/value/"):
                vid = int(path.rsplit("/", 1)[1])
                self._send(200, v.get(vid) or {"error": "唔存在"})
            elif path == "/split-totals":
                qs = self._qs()
                vid = int(qs["value_id"]) if qs.get("value_id") else None
                self._send(200, {"split_totals": v.split_totals(value_id=vid)})
            elif path == "/split-values":
                qs = self._qs()
                stid = int(qs["split_total_id"]) if qs.get("split_total_id") else None
                vid = int(qs["value_id"]) if qs.get("value_id") else None
                self._send(200, {"split_values": v.split_values(
                    split_total_id=stid, value_id=vid)})
            elif path == "/terminology":
                qs = self._qs()
                svid = int(qs["split_value_id"]) if qs.get("split_value_id") else None
                self._send(200, {"terminology": v.terminology_rows(
                    split_value_id=svid)})
            elif path == "/can-call-terminology":
                qs = self._qs()
                svid = int(qs["split_value_id"]) if qs.get("split_value_id") else None
                tid = int(qs["terminology_id"]) if qs.get("terminology_id") else None
                if svid is None or tid is None:
                    self._send(400, {"error": "需要 split_value_id + terminology_id"})
                else:
                    self._send(200, {"allowed": v.can_call_terminology(svid, tid)})
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
            elif path == "/split":
                value_id = body.get("value_id")
                parts = body.get("parts")
                if not value_id or not parts:
                    self._send(400, {"error": "需要 value_id + parts"})
                else:
                    r = v.add_split(value_id, parts)
                    self._send(200, r)
            elif path == "/split-and-prove":
                # 一站式：value → split → 行 split_value flow → 寫 run
                val = body.get("value")
                parts = body.get("parts")
                if not val or not parts:
                    self._send(400, {"error": "需要 value + parts"})
                else:
                    r = v.split_and_prove(val, parts,
                                          body.get("taxonomy_id"),
                                          body.get("role_id"))
                    self._send(200, r)
            elif path == "/terminology":
                terminology_id = body.get("terminology_id")
                split_value_id = body.get("split_value_id")
                if not terminology_id or not split_value_id:
                    self._send(400, {"error": "需要 terminology_id + split_value_id"})
                else:
                    rid = v.grant_terminology(terminology_id, split_value_id)
                    self._send(200, {"terminology_id": rid})
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