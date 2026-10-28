"""route.py — tool CLI 入口

用法：
    python -m tool <command>
    tools [module_id] [skill_id]
    add <module_id> [skill_id] [REST_API_WRITE_id] [REST_API_READ_id]
    count
"""

import sys

from .api import Tool


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("可用命令（tool）:")
        for m in ['tools', 'add', 'count']:
            print(f"    {m}")
        return 0
    cmd = argv[0]
    if cmd not in ['tools', 'add', 'write-apis', 'add-write', 'count']:
        print(f"未知命令: {cmd}")
        return 1
    obj = Tool()
    try:
        if cmd == "write-apis":
            module_id = int(argv[1]) if len(argv) > 1 else None
            for x in obj.write_apis(module_id=module_id):
                print(f"{x['id']}\t{x['module_id']}\t{x['rest_api']}")
        elif cmd == "add-write":
            if len(argv) < 3:
                print("需要 module_id + rest_api")
                return 1
            module_id = int(argv[1])
            rest_api = argv[2]
            print("write api id:", obj.add_write_api(module_id, rest_api))
        elif cmd == "tools":
            module_id = int(argv[1]) if len(argv) > 1 else None
            skill_id = int(argv[2]) if len(argv) > 2 else None
            for x in obj.tools(module_id=module_id, skill_id=skill_id):
                print(f"{x['id']}\t{x['module_id']}\t{x['skill_id'] or ''}"
                      f"\t{x['REST_API_WRITE_id'] or ''}"
                      f"\t{x['REST_API_READ_id'] or ''}")
        elif cmd == "add":
            if len(argv) < 2:
                print("需要 module_id")
                return 1
            module_id = int(argv[1])
            skill_id = int(argv[2]) if len(argv) > 2 else None
            rw = int(argv[3]) if len(argv) > 3 else None
            rr = int(argv[4]) if len(argv) > 4 else None
            print("tool id:", obj.add_tool(module_id, skill_id, rw, rr))
        elif cmd == "count":
            print(obj.count())
    finally:
        obj.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())