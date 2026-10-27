"""route.py — identity CLI"""

import sys

from .api import Identity

USAGE = """用法：
    python -m identity.route [command]

commands:
    register <kind> <name> [ref_id]   登記一個身份
    lookup <kind> <name>              按 kind + name 查
    list [kind]                       列出全部（可按 kind 篩選）
    kinds                             列出所有 kind
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    i = Identity()
    try:
        cmd = argv[0]
        if cmd == "register":
            kind, name = argv[1], argv[2]
            ref_id = int(argv[3]) if len(argv) > 3 else None
            rid = i.register(kind, name, ref_id)
            print(f"✅ 已登記 {kind}:{name} -> identity id={rid}")
        elif cmd == "lookup":
            kind, name = argv[1], argv[2]
            r = i.lookup(kind, name)
            if r:
                print(f"{r['id']}\t{r['kind']}\t{r['name']}\tref_id={r['ref_id']}\t{r['description'] or ''}")
            else:
                print(f"❌ 搵唔到 {kind}:{name}")
        elif cmd == "list":
            kind = argv[1] if len(argv) > 1 else None
            for r in i.list_all(kind):
                print(f"{r['id']}\t{r['kind']}\t{r['name']}\tref_id={r['ref_id']}\t{r['description'] or ''}")
        elif cmd == "kinds":
            for k in i.list_kinds():
                print(f"  {k}")
        else:
            print(USAGE)
            return 1
    finally:
        i.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
