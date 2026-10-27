"""api_server.py — source 嘅 REST API 伺服器（用標準庫 http.server，零依賴）

透過 HTTP 查 source / provider / authority_level / industry：

    GET  /sources            列出全部 source
    GET  /sources/<id>       攞一個 source
    GET  /providers          列出全部 provider
    GET  /providers/<id>     攞一個 provider
    GET  /levels             列出全部 authority_level
    GET  /industries         列出全部 industry
    GET  /health             health check

    POST /sources            {"source": "RFC 9110", "provider": "IETF", "description": "..."}   註冊 source
    POST /providers          {"meta": "W3C", "level": "official", "industry": "information technology",
                              "url": "https://www.w3.org", "description": "..."}                 註冊 provider
    POST /industries         {"meta": "education", "description": "..."}                         註冊 industry

用法：
    python -m source.api_server [--port 8100]
"""

import argparse
import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import Source

META = r"C:\projects\meta"
SOURCE_DB = rf"{META}\source.db"

def _conn(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c

class SourceApiHandler(BaseHTTPRequestHandler):
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
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def log_message(self, *args):
        pass  # 靜音，避免刷屏

    def _path_parts(self):
        """將 path 拆做 parts（例如 /sources/3 -> ["sources", "3"]）"""
        return [p for p in self.path.split("/") if p]

    def _qs(self):
        """拆 query string -> dict（首個值）"""
        import urllib.parse
        if "?" not in self.path:
            return {}
        q = urllib.parse.parse_qs(self.path.split("?", 1)[1])
        return {k: v[0] for k, v in q.items()}

    # ---------------- GET ----------------
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
        s = Source(SOURCE_DB)
        try:
            parts = self._path_parts()
            # 守衛：除 health 外全部要 token（guard 只保留喺 HTTP 入口）
            if not parts or parts[0] != "health":
                qs = self._qs()
                self._check_token(qs)
            # 驗證路由（/<route>=<value>）—— proof by value
            if "=" in self.path:
                if self.do_GET_verify(self.path, s):
                    return
            parts = self._path_parts()
            if not parts:
                self._send(200, {
                    "endpoints": [
                        "GET  /sources", "GET  /sources/<id>",
                        "GET  /providers", "GET  /providers/<id>",
                        "GET  /levels", "GET  /industries",
                        "POST /sources", "POST /providers", "POST /industries",
                    ]})
            elif parts[0] == "health":
                self._send(200, {"status": "ok"})
            elif parts[0] == "sources" and len(parts) == 1:
                rows = []
                for r in s.list_sources():
                    prov = ""
                    if r.get("provider_id"):
                        p = s.get_provider(r["provider_id"])
                        prov = p["meta"] if p else ""
                    rows.append({**r, "provider": prov})
                self._send(200, {"sources": rows})
            elif parts[0] == "sources" and len(parts) == 2:
                r = s.get(int(parts[1]))
                self._send(200, r if r else {"error": "唔存在"})
            elif parts[0] == "providers" and len(parts) == 1:
                rows = []
                for r in s.list_providers():
                    lv = ""
                    if r.get("authority_level_id"):
                        a = s.get_authority_level(r["authority_level_id"])
                        lv = a["meta"] if a else ""
                    ind = ""
                    if r.get("industry_id"):
                        i = s.get_industry(r["industry_id"])
                        ind = i["meta"] if i else ""
                    rows.append({**r, "authority_level": lv, "industry": ind})
                self._send(200, {"providers": rows})
            elif parts[0] == "providers" and len(parts) == 2:
                r = s.get_provider(int(parts[1]))
                self._send(200, r if r else {"error": "唔存在"})
            elif parts[0] == "levels":
                self._send(200, {"levels": s.list_authority_levels()})
            elif parts[0] == "industries":
                self._send(200, {"industries": s.list_industries()})
            else:
                self._send(404, {"error": "唔知嘅 route"})
        except Exception as e:
            self._send(500, {"error": str(e)})
        finally:
            s.close()

    def do_GET_verify(self, raw_path, s):
        """驗證路由：/<route>=<value> 提交值去驗證（唔係 display）

        2026-10-24o（用戶要求）：/sources=xxxx 要 proof by value。
        flow 由 api 表（flow_id）決定，行 run_flow 驗證，
        返回 pass/fail + run 記錄。
        """
        route, _, value = raw_path.lstrip("/").partition("=")
        if not value:
            return False
        # api 表查 flow
        row = s.store.conn.execute(
            "SELECT a.flow_id, f.flow_name FROM api a"
            " LEFT JOIN flow f ON f.id = a.flow_id"
            " WHERE a.api = ? AND a.is_active = 1 LIMIT 1",
            (f"/{route}",)).fetchone()
        if not row or not row["flow_name"]:
            return False
        flow_name = row["flow_name"]
        # 行 flow 驗證（run + result 記錄）
        res = s.run_flow(flow_name, save=True)
        self._send(200, {
            "route": f"/{route}",
            "value": value,
            "flow_id": row["flow_id"],
            "flow": flow_name,
            "verify": res,
        })
        return True

    # ---------------- POST ----------------
    def do_POST(self):
        try:
            body = self._read_body()
            parts = self._path_parts()
            if not parts:
                self._send(404, {"error": "唔知嘅 route"})
                return
            qs = self._qs()
            self._check_token(qs)
            s = Source(SOURCE_DB)
            try:
                if parts[0] == "sources":
                    self._post_source(s, body)
                elif parts[0] == "providers":
                    self._post_provider(s, body)
                elif parts[0] == "industries":
                    self._post_industry(s, body)
                else:
                    self._send(404, {"error": "唔知嘅 route"})
            finally:
                s.close()
        except Exception as e:
            self._send(500, {"error": str(e)})

    def _post_source(self, s, body):
        """POST /sources {"source": "...", "provider": "...", "description": "..."}"""
        source = body.get("source")
        if not source:
            self._send(400, {"error": "需要 source"})
            return
        provider_id = None
        prov_meta = body.get("provider")
        if prov_meta:
            p = s.lookup_provider(prov_meta)
            if p:
                provider_id = p["id"]
            else:
                self._send(404, {"error": f"provider '{prov_meta}' 唔存在"})
                return
        sid, created = s.register(source, body.get("description"), provider_id)
        self._send(200, {"status": "ok", "source": source, "id": sid, "created": created})

    def _post_provider(self, s, body):
        """POST /providers {"meta": "...", "level": "official", "industry": "...", "url": "...", "description": "..."}"""
        meta = body.get("meta")
        if not meta:
            self._send(400, {"error": "需要 meta"})
            return
        # level
        authority_level_id = None
        lv_meta = body.get("level")
        if lv_meta:
            a = s.lookup_authority_level(lv_meta)
            if a:
                authority_level_id = a["id"]
            else:
                self._send(404, {"error": f"level '{lv_meta}' 唔存在（official/authoritative/unofficial）"})
                return
        # industry（唔存在會自動建立）
        industry_id = None
        ind_meta = body.get("industry")
        if ind_meta:
            ind = s.lookup_industry(ind_meta)
            if ind:
                industry_id = ind["id"]
            else:
                industry_id, _ = s.register_industry(ind_meta)
        pid, created = s.register_provider(
            meta, authority_level_id, industry_id,
            body.get("url"), body.get("description"))
        self._send(200, {"status": "ok", "provider": meta, "id": pid, "created": created})

    def _post_industry(self, s, body):
        """POST /industries {"meta": "...", "description": "..."}"""
        meta = body.get("meta")
        if not meta:
            self._send(400, {"error": "需要 meta"})
            return
        iid, created = s.register_industry(meta, body.get("description"))
        self._send(200, {"status": "ok", "industry": meta, "id": iid, "created": created})

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description="source REST API")
    parser.add_argument("--port", type=int, default=8100)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), SourceApiHandler)
    server.daemon_threads = True
    print(f"✅ source API 伺服器起動: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()

if __name__ == "__main__":
    main()