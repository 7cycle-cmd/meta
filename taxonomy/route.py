"""route.py — taxonomy.db CLI"""

import json
import sqlite3
import sys

from .api import Taxonomy
from .sql import SqlStore



def main(argv=None):

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
        return _main(argv)


def _main(argv):
    taxonomy = Taxonomy()
    try:
        cmd = argv[0]
        if cmd == "register":
            json_str = " ".join(argv[1:])
            store = SqlStore()
            try:
                result = store.register_json_str(json_str)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                if result.get("status") != "ok":
                    return 1
            finally:
                store.close()
        elif cmd in ("search", "dump"):
            store = SqlStore()
            try:
                if cmd == "search":
                    try:
                        query = json.loads(" ".join(argv[1:]))
                    except json.JSONDecodeError as exc:
                        print(f"JSON 解析失敗: {exc}")
                        return 1
                    if not isinstance(query, dict):
                        print("搜尋條件必須係 JSON 物件")
                        return 1
                    result = store.search(query)
                else:
                    result = store.dump()
                print(json.dumps(result, ensure_ascii=False, indent=2))
            finally:
                store.close()
        elif cmd == "categories":
            for row in taxonomy.list_categories():
                print(f"{row['id']}\t{row['meta_key']:12s} active={row['is_active']} seq={row['seq']}")
        elif cmd == "category":
            key = argv[argv.index("--key") + 1]
            seq = int(argv[argv.index("--seq") + 1])
            active = 1 if "--active" in argv else 0
            category_id = taxonomy.register_category(key, seq, active)
            print(f"✅ category id={category_id} {key} seq={seq} active={active}")
        elif cmd == "items":
            tree = argv[argv.index("--tree") + 1] if "--tree" in argv else None
            for row in taxonomy.list_items(tree):
                print(f"{row['id']}\t{row['tree']}\t{row['meta']}\tactive={row['is_active']}")
        elif cmd == "item":
            tree = argv[argv.index("--tree") + 1]
            key = argv[argv.index("--key") + 1]
            active = 0 if "--inactive" in argv else 1
            row_id = taxonomy.register_item(tree, key, active)
            print(f"✅ item id={row_id} tree={tree} {key} active={active}")
        elif cmd == "physical-paths":
            module = None
            if "--module" in argv:
                module = argv[argv.index("--module") + 1]
            for row in taxonomy.list_physical_paths(module):
                print(f"{row['id']}\t{row['level']:12s}\t{row['module']}"
                      f"\t{row['full_path']}")
                print(f"    {row['path_json']}")
        elif cmd in ("modules", "skills", "channels"):
            rows = {
                "modules": taxonomy.list_modules,
                "skills": taxonomy.list_skills,
                "channels": taxonomy.list_channels,
            }[cmd]()
            for row in rows:
                print(f"{row['id']}\t{row['meta']}\tactive={row['is_active']}")
        else:
            print(USAGE)
            return 1
    finally:
        taxonomy.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
