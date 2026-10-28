"""rest_api.py — migration REST 伺服器（查看審計記錄）

用法：
    python -m migration.rest_api [--port 8300]
"""
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import Migration

DB = r"C:\projects\meta\migration\migration.db"


class MigrationHandler(BaseHTTPRequestHandler):
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
        path = self.path.split("?", 1)[0]
        m = Migration(DB)
        try:
            if path == "/migrations":
                # query: ?module=source&type=schema
                q = {}
                if "?" in self.path:
                    for kv in self.path.split("?", 1)[1].split("&"):
                        if "=" in kv:
                            k, v = kv.split("=", 1)
                            q[k] = v
                rows = m.logs(module_name=q.get("module"),
                              migration_type=q.get("type"))
                self._send(200, {"migrations": rows,
                                 "total": len(rows)})
            elif path == "/health":
                self._send(200, {"status": "ok",
                                 "module": "migration"})
            else:
                self._send(404, {"error": "唔知嘅 route"})
        except Exception as e:
            self._send(500, {"error": str(e)})
        finally:
            m.close()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description="migration REST API")
    parser.add_argument("--port", type=int, default=8300)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), MigrationHandler)
    server.daemon_threads = True
    print(f"[OK] migration API server: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
        server.server_close()


if __name__ == "__main__":
    main()
