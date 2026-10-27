"""route.py — mcp_hub CLI

用法：
    python -m mcp_hub.route servers
    python -m mcp_hub.route tools [--server python|sql]
    python -m mcp_hub.route calls [--server python|sql] [--limit 20]
    python -m mcp_hub.route stats
    python -m mcp_hub.route run-python --code "1+1" [--source codegen]
    python -m mcp_hub.route check-syntax --code "def f(): pass" [--source codegen]
    python -m mcp_hub.route query --db resource.db --sql "SELECT COUNT(*) FROM registry" [--source codegen]
    python -m mcp_hub.route list-tables --db resource.db [--source codegen]
    python -m mcp_hub.route describe --db resource.db --table registry [--source codegen]
"""

import sys

from .api import Mcp


def _arg(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def _source_id(name):
    """由 source.db 查 source.id（唔硬寫數字）"""
    from source import Source
    s = Source()
    try:
        r = s.lookup(name)
        return r["id"] if r else None
    finally:
        s.close()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 1
    cmd = argv[0]
    m = Mcp()
    try:
        if cmd == "servers":
            for r in m.servers():
                print(f"[{r['id']}] {r['meta']:<10} {r['transport']:<6}"
                      f" {r['description'] or ''}")
        elif cmd == "tools":
            server = _arg(argv, "--server")
            for r in m.tools(server):
                print(f"[{r['id']}] {r['server']}.{r['meta']:<16}"
                      f" {r['description'] or ''}")
        elif cmd == "calls":
            server = _arg(argv, "--server")
            limit = int(_arg(argv, "--limit", "20"))
            for r in m.calls(server=server, limit=limit):
                mark = "OK  " if r["ok"] else "FAIL"
                print(f"[{r['id']}] {mark} {r['server']}.{r['tool']:<16}"
                      f" source={r['source_id']} {r['duration_ms']}ms"
                      f" {r['created_at']}")
                if r["error"]:
                    print(f"        error: {r['error'][:100]}")
        elif cmd == "stats":
            for k, v in m.stats().items():
                print(f"  {k:<12} {v}")
        elif cmd == "run-python":
            code = _arg(argv, "--code")
            src = _source_id(_arg(argv, "--source", "codegen"))
            if not code or not src:
                print("要 --code 同有效 --source")
                return 1
            r = m.run_python(code, src)
            print(f"ok={r['ok']} duration={r['duration_ms']}ms")
            if r["result"]:
                print(r["result"])
            if r["error"]:
                print(f"error: {r['error']}")
        elif cmd == "check-syntax":
            code = _arg(argv, "--code")
            src = _source_id(_arg(argv, "--source", "codegen"))
            if not code or not src:
                print("要 --code 同有效 --source")
                return 1
            r = m.check_syntax(code, src)
            print(f"ok={r['ok']} {r['error'] or ''}")
        elif cmd == "query":
            db = _arg(argv, "--db")
            sql = _arg(argv, "--sql")
            src = _source_id(_arg(argv, "--source", "codegen"))
            if not db or not sql or not src:
                print("要 --db / --sql / 有效 --source")
                return 1
            r = m.query(db, sql, src)
            print(f"ok={r['ok']} rows={len(r['rows'])}"
                  f" duration={r['duration_ms']}ms")
            for row in r["rows"][:20]:
                print(f"  {row}")
            if r["error"]:
                print(f"error: {r['error']}")
        elif cmd == "list-tables":
            db = _arg(argv, "--db")
            src = _source_id(_arg(argv, "--source", "codegen"))
            if not db or not src:
                print("要 --db 同有效 --source")
                return 1
            r = m.list_tables(db, src)
            for row in r["rows"]:
                print(f"  {row['name']}")
        elif cmd == "describe":
            db = _arg(argv, "--db")
            table = _arg(argv, "--table")
            src = _source_id(_arg(argv, "--source", "codegen"))
            if not db or not table or not src:
                print("要 --db / --table / 有效 --source")
                return 1
            r = m.describe_table(db, table, src)
            for row in r["rows"]:
                print(f"  {row['name']:<20} {row['type']:<10}"
                      f" notnull={row['notnull']} pk={row['pk']}")
        else:
            print(__doc__)
            return 1
        return 0
    finally:
        m.close()


if __name__ == "__main__":
    sys.exit(main())
