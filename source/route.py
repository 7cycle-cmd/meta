"""route.py — source.db CLI"""

import sys

from .api import Source

USAGE = """用法：
    python -m source.route list
    python -m source.route add --source SOURCE [--provider PROVIDER] [--desc DESC]
    python -m source.route lookup SOURCE
    python -m source.route count
    python -m source.route providers
    python -m source.route add-provider --meta META [--level official/authoritative/unofficial] [--industry INDUSTRY] [--url URL] [--desc DESC]
    python -m source.route levels
    python -m source.route industries
    python -m source.route add-industry --meta META [--desc DESC]
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    s = Source()
    try:
        cmd = argv[0]
        if cmd == "list":
            for r in s.list_sources():
                prov = ""
                if r.get("provider_id"):
                    p = s.get_provider(r["provider_id"])
                    prov = f" [{p['meta']}]" if p else ""
                print(f"[{r['id']}] {r['source']}{prov}  ({r['description'] or ''})")
        elif cmd == "add":
            source = argv[argv.index("--source") + 1]
            desc = None
            if "--desc" in argv:
                desc = argv[argv.index("--desc") + 1]
            provider_id = None
            if "--provider" in argv:
                prov_meta = argv[argv.index("--provider") + 1]
                p = s.lookup_provider(prov_meta)
                if p:
                    provider_id = p["id"]
                else:
                    provider_id, _ = s.register_provider(prov_meta)
            sid, created = s.register(source, desc, provider_id)
            print(f"{'✅ 新增' if created else '⚠️ 已存在'} id={sid} {source}")
        elif cmd == "lookup":
            r = s.lookup(argv[1])
            print(dict(r) if r else "唔存在")
        elif cmd == "count":
            print(f"總數: {s.count()}")
        elif cmd == "providers":
            for r in s.list_providers():
                lv = ""
                if r.get("authority_level_id"):
                    a = s.get_authority_level(r["authority_level_id"])
                    lv = f" ({a['meta']}/{a['level']})" if a else ""
                ind = ""
                if r.get("industry_id"):
                    i = s.get_industry(r["industry_id"])
                    ind = f" [{i['meta']}]" if i else ""
                url = f" {r['official_url']}" if r.get("official_url") else ""
                print(f"[{r['id']}] {r['meta']}{ind}{lv}{url}  ({r['description'] or ''})")
        elif cmd == "add-provider":
            meta = argv[argv.index("--meta") + 1]
            level_id = None
            if "--level" in argv:
                lv_meta = argv[argv.index("--level") + 1]
                a = s.lookup_authority_level(lv_meta)
                if a:
                    level_id = a["id"]
                else:
                    print(f"唔知嘅 level: {lv_meta}（official/authoritative/unofficial）")
                    return 1
            industry_id = None
            if "--industry" in argv:
                ind_meta = argv[argv.index("--industry") + 1]
                i = s.lookup_industry(ind_meta)
                if i:
                    industry_id = i["id"]
                else:
                    industry_id, _ = s.register_industry(ind_meta)
            official_url = None
            if "--url" in argv:
                official_url = argv[argv.index("--url") + 1]
            desc = None
            if "--desc" in argv:
                desc = argv[argv.index("--desc") + 1]
            pid, created = s.register_provider(meta, level_id, industry_id, official_url, desc)
            print(f"{'✅ 新增' if created else '⚠️ 已存在'} id={pid} {meta}")
        elif cmd == "levels":
            for r in s.list_authority_levels():
                print(f"[{r['id']}] {r['meta']:15s} level={r['level']}  ({r['description']})")
        elif cmd == "industries":
            for r in s.list_industries():
                print(f"[{r['id']}] {r['meta']}  ({r['description'] or ''})")
        elif cmd == "add-industry":
            meta = argv[argv.index("--meta") + 1]
            desc = None
            if "--desc" in argv:
                desc = argv[argv.index("--desc") + 1]
            iid, created = s.register_industry(meta, desc)
            print(f"{'✅ 新增' if created else '⚠️ 已存在'} id={iid} {meta}")
        else:
            print(USAGE)
            return 1
    finally:
        s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())