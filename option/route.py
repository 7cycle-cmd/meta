"""route.py — option CLI"""



def main(argv=None):
    """CLI 入口：python -m option.route <command>

    commands:
        list [resource_id]            列出允許值（可按資源篩選）
        list-field <structure_db_field_id>  列出欄位允許值
        add <value> <desc?>           新增值（可配 --resource / --field / --table）
        has <value> [resource_id]     檢查值喺唔喺
        remove <value> [resource_id]  刪除值
        reset                         清空全部（重新開始）
    """
    import sys
    from .api import Option

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("help", "-h", "--help"):
        print(__doc__)
        return 0
        return _main(argv)


def _main(argv):
    from .api import Option

    opt = Option()
    try:
        cmd = argv[0]
        if cmd == "list":
            rid = int(argv[1]) if len(argv) > 1 else None
            for r in opt.options(resource_id=rid):
                print(f"{r['id']}\t{r.get('resource_id')}"
                      f"\t{r.get('structure_db_field_id')}"
                      f"\t{r['value']}\t{r.get('description') or ''}")
        elif cmd == "list-field":
            fid = int(argv[1])
            for r in opt.options(structure_db_field_id=fid):
                print(f"{r['id']}\t{r['value']}\t{r.get('description') or ''}")
        elif cmd == "add":
            value = argv[1]
            desc = argv[2] if len(argv) > 2 else None
            rid = None
            fid = None
            tid = None
            rest = argv[3:]
            for i, a in enumerate(rest):
                if a == "--resource":
                    rid = int(rest[i + 1])
                elif a == "--field":
                    fid = int(rest[i + 1])
                elif a == "--table":
                    tid = int(rest[i + 1])
            oid = opt.add_option(resource_id=rid, value=value, description=desc,
                                 structure_db_field_id=fid,
                                 structure_db_table_id=tid)
            print(f"added id={oid}")
        elif cmd == "has":
            value = argv[1]
            rid = int(argv[2]) if len(argv) > 2 else None
            print(opt.has_option(resource_id=rid, value=value))
        elif cmd == "remove":
            value = argv[1]
            rid = int(argv[2]) if len(argv) > 2 else None
            opt.remove_option(resource_id=rid, value=value)
            print("removed")
        elif cmd == "reset":
            opt.reset()
            print("reset：全部 option 已清")
        else:
            print(f"未知命令: {cmd}")
            print(__doc__)
            return 1
        return 0
    finally:
        opt.close()


if __name__ == "__main__":
    main()
