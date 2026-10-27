"""route.py — Connection CLI"""

import sys

from .api import Connection

USAGE = """用法：
    python -m connection.route check --db DB --table TABLE
    python -m connection.route scan
    python -m connection.route disconnected
    python -m connection.route history
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    c = Connection()
    try:
        cmd = argv[0]
        if cmd == "check":
            db = argv[argv.index("--db") + 1]
            table = argv[argv.index("--table") + 1]
            r = c.check(db, table)
            mark = "✅ 連接成立" if r["connected"] else "❌ 連接唔成立"
            print(f"  {mark}: {r['proof']}")
        elif cmd == "scan":
            report = c.scan()
            for db_name, tables in report.items():
                print(f"  {db_name}:")
                for t, info in tables.items():
                    mark = "✅" if info["connected"] else "❌"
                    print(f"    {mark} {t}: {info['proof']}")
        elif cmd == "disconnected":
            for r in c.disconnected():
                print(f"  ❌ {r['db']}.{r['table']}: {r['proof']}")
        elif cmd == "history":
            for r in c.history(50):
                mark = "✅" if r["connected"] else "❌"
                print(f"  [{r['id']}] {r['run_at']} {r['db_name']}.{r['table_name']} {mark}: {r['proof']}")
        else:
            print(USAGE)
            return 1
    finally:
        c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())