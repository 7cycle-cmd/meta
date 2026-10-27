"""route.py — definition.db CLI"""

import sys

from .api import Definition

USAGE = """用法：
    python -m definition.route [command]

commands:
    file-required   列出必須檔案字典（file_required）
    physical-files      列出實體檔案（file 層 = structure_module 真檔名）
    physical-types      列出實體類型（package/file/db_table/db_field）
    physical-required   列出每個大類必須嘅實體
    sync-physical       掃 module 資料夾，自動登記實體檔案
    check-module <name> 檢查一個 module 檔案齊唔齊（file_required 權威）
"""



def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
        return _main(argv)


def _main(argv):
    d = Definition()
    try:
        cmd = argv[0]
        if cmd == "data-types":
            from structure.api import Structure
            s = Structure()
            try:
                for r in s.list_data_types():
                    print(f"{r['id']}\t{r['meta']}\t{r['description']}")
            finally:
                s.close()
        elif cmd == "file-required":
            for r in d.list_file_requireds():
                print(f"{r['id']}\t{r['meta']}\texists=required"
                      f"\t{r['description'] or ''}")
        elif cmd == "structure-files":
            for f in d.list_modules_files():
                print(f"{f['id']}\t{f['module'] or f['module_id']}"
                      f"\t{f['file_name']}\t{f['file_type'] or ''}")
        elif cmd == "structure-types":
            for r in d.list_structure_types():
                print(f"{r['id']}\t{r['meta']}\t{r['description'] or ''}")
        elif cmd == "structure-required":
            for r in d.list_structure_requireds():
                print(f"{r['id']}\t{r['tree']}\t{r['structure_type']}")
        elif cmd == "sync-physical":
            n_before = len(d.list_modules_files())
            d.sync_physical()
            n_after = len(d.list_modules_files())
            print(f"sync 完成：structure_file {n_before} -> {n_after}")
        elif cmd == "check-module":
            if len(argv) < 2:
                print("用法: check-module <module名>")
                return 1
            r = d.check_module_files(module_name=argv[1])
            if r["virtual"]:
                print(f"{argv[1]}: 虛擬 module（冇資料夾）—— 唔適用")
                return 0
            print(f"{argv[1]}: "
                  + ("齊✓" if r["complete"] else f"缺失 {r['missing']}"))
            print(f"  已登記: {sorted(x['file_name'] for x in r['files'])}")
            return 0 if r["complete"] else 2
        elif cmd == "discover":
            r = d.report_missing_to_task()
            disc = r["report"]
            n_total = len(disc)
            n_miss = sum(1 for i in disc.values() if not i["complete"])
            print(f"發現 {n_miss} 個 module 缺檔（總共 {n_total} 個）：")
            for name, info in disc.items():
                mark = "✓" if info["complete"] else "✗"
                miss = f" 缺: {info['missing']}" if not info["complete"] else ""
                print(f"  {mark} {name}{miss}")
            print(f"\n已落 task 訂單：{len(r['new_tasks'])} 個新增"
                  f"（skip 重複 {r['dup']}）")
            for tid in r["new_tasks"]:
                print(f"  task #{tid} fill-missing-files")
            return 0
        else:
            print(USAGE)
            return 1
    finally:
        d.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())