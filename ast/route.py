"""route.py — ast.db CLI"""

import sys

from .api import Ast

USAGE = """用法：
    python -m ast.route scan <module>    AST 掃描一個 module
    python -m ast.route scan-all         AST 掃描全部 module
    python -m ast.route functions        列出函數字典
    python -m ast.route classes          列出函數類別字典
    python -m ast.route analyze <table>  列出一個 analyze 表
        table = analyze_root / analyze_module / analyze_skill
"""



def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
        return _main(argv)


def _main(argv):
    cmd = argv[0]
    a = Ast()
    try:
        if cmd == "scan" and len(argv) >= 2:
            r = a.scan_module(argv[1])
            print("scan %s: %s" % (argv[1], r))
        elif cmd == "scan-all":
            results = a.scan_all()
            total = sum(r.get("functions", 0) for r in results)
            print("scan-all: %d module, %d functions" % (len(results), total))
            for r in results:
                print("  %-20s %s" % (r.get("module"), r))
        elif cmd == "functions":
            for f in a.list_functions():
                print("%d  %-40s class=%s lang=%s" % (
                    f["id"], f["function"], f.get("class_name"),
                    f["programming_language_id"]))
        elif cmd == "classes":
            for c in a.list_function_classes():
                print("%d  %s" % (c["id"], c["meta"]))
        elif cmd == "analyze" and len(argv) >= 2:
            table = argv[1]
            if table not in ("analyze_root", "analyze_module",
                             "analyze_skill"):
                print("未知 analyze 表: %s" % table)
                return 1
            rows = a.list_analyze(table)
            print("%s: %d 行" % (table, len(rows)))
            for r in rows[:50]:
                print("  %s -> %s" % (r.get("function_name"), r))
        else:
            print(USAGE)
            return 1
    finally:
        a.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
