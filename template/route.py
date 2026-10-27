"""route.py — template CLI

命令：
    flows                                     列出全部 flow
    flow-steps          --flow <name>         一個 flow 嘅 steps
    run-flow            --flow <name> --value <v>  行一條 flow（寫 run）
    flow-runs           [--limit N]           執行記錄
    formulas                                  列出全部 formula
    formula             --id <n>              一條 formula 全檢視（含 cuter）
    cut-formula         --id <n>              公式切粒入 formula_cuter
    exec-formula        --id <n> --p k=v [--p k=v ...]   執行 formula
    evidences           [--limit N]           證據記錄（flow 自動寫）
    evidence-summary                          證據統計（total/match/mismatch）
    gen-evidence        [--targets t1,t2]     掃 SSOT 表生成證據（空=全部）
"""


def _store():
    from template import Template
    return Template()


def _arg(argv, flag, default=None):
    """攞 --flag 值（'--flag value' 或 '--flag=value'）"""
    for i, a in enumerate(argv):
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
        if a == flag and i + 1 < len(argv):
            return argv[i + 1]
    return default


def main(argv=None):
    """CLI 入口"""
    import sys
    sys.argv = argv or sys.argv
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = args[0]
    t = _store()
    try:
        if cmd == "flows":
            for f in t.flows():
                print(f"   #{f['id']} {f['flow_name']}")
            return 0
        if cmd == "flow-steps":
            flow = _arg(args, "--flow")
            if not flow:
                print("需要 --flow <name>")
                return 1
            for s in t.flow_steps(flow):
                print(f"   step{s['seq']}: condition={s['condition']:<14}"
                      f" w5w2h={s['w5w2h']:<6}"
                      f" op={s['operator_meta']:<3}"
                      f" expected={s['expected_boolean_id']}")
            return 0
        if cmd == "run-flow":
            flow = _arg(args, "--flow")
            value = _arg(args, "--value")
            if not flow or value is None:
                print("需要 --flow <name> --value <v>")
                return 1
            r = t.run_flow(flow, value)
            print(f"   status={r['status_id']}（1=approved 2=rejected）"
                  f" run_id={r['run_id']}")
            for j in r["steps"]:
                pf = ""
                if j.get("proof") and not j["is_pass"]:
                    pf = f"  ({j['proof'].get('error', '')[:60]})"
                print(f"   step{j['seq']}: condition={j['condition']:<14}"
                      f" answer={j['answer']} pass={j['is_pass']}{pf}")
            return 0
        if cmd == "flow-runs":
            limit = int(_arg(args, "--limit", 20))
            for run in t.flow_runs(limit):
                print(f"   #{run['id']} flow={run['flow_name']}"
                      f" value={run['value']!r}"
                      f" status={run['status']} @ {run['created_at']}")
            return 0
        if cmd == "formulas":
            for f in t.formulas():
                print(f"   #{f['id']} {f['full'][:80]}")
            return 0
        if cmd == "formula":
            fid = _arg(args, "--id")
            if not fid:
                print("需要 --id <n>")
                return 1
            d = t.formula(int(fid))
            if not d:
                print(f"   formula {fid} 唔存在")
                return 1
            print(f"   full      = {d['full']}")
            print(f"   package   = {d['package_id']}"
                  f"   file      = {d['file_id']}"
                  f"   line      = {d['line']}")
            print(f"   cuter     = {len(d['cuter'])} 粒")
            print("   tokens: " + " | ".join(x['value'] for x in d['cuter']))
            print(f"   proofs    = {len(d['proofs'])}"
                  f"   tables    = {len(d['tables'])}"
                  f"   conditions= {len(d['conditions'])}")
            return 0
        if cmd == "cut-formula":
            fid = _arg(args, "--id")
            if not fid:
                print("需要 --id <n>")
                return 1
            toks = t.cut_formula(int(fid))
            print(f"   {len(toks)} 粒: " + " | ".join(toks))
            return 0
        if cmd == "exec-formula":
            fid = _arg(args, "--id")
            if not fid:
                print("需要 --id <n>")
                return 1
            params = {}
            for a in args:
                if a.startswith("--p "):
                    pass
            # 收集 --p k=v（可多個）
            it = iter(args)
            for a in it:
                if a.startswith("--p="):
                    k, v = a[3:].split("=", 1)
                    params[k] = v
                elif a == "--p":
                    nxt = next(it, None)
                    if nxt and "=" in nxt:
                        k, v = nxt.split("=", 1)
                        params[k] = v
            res = t.execute_formula(int(fid), params)
            print(f"   ok={res.get('ok')} rows={res.get('rows')}"
                  f" table={res.get('table')}")
            if res.get("sql"):
                print(f"   sql={res['sql']}")
                if res.get("args"):
                    print(f"   args={res['args']}")
            if res.get("error"):
                print(f"   error={res['error']}")
            return 0
        if cmd == "evidences":
            limit = int(_arg(args, "--limit", 50))
            for e in t.evidences(limit):
                print(f"   #{e['id']} {e['table_name']}.{e['field_name']}"
                      f" value={e['value']!r}"
                      f" expected={e['expected']!r} actual={e['actual']!r}"
                      f" match={'Y' if e['is_match'] else 'N'}"
                      f" @ {e['created_at']}")
            return 0
        if cmd == "evidence-summary":
            sm = t.evidence_summary()
            print(f"   total={sm['total']} match={sm['match']}"
                  f" mismatch={sm['mismatch']}"
                  f" rate={sm['match'] / sm['total'] * 100:.1f}%"
                  if sm["total"] else "   total=0")
            return 0
        if cmd == "gen-evidence":
            targets = _arg(args, "--targets")
            tl = [x.strip() for x in targets.split(",")
                  if x.strip()] if targets else []
            res = t.gen_evidence_formulas(tl)
            print(f"   targets={res.get('targets')}")
            print(f"   formulas={res.get('formulas')}")
            print(f"   evidences={res.get('evidences')}")
            if res.get("errors"):
                for x in res["errors"][:5]:
                    print(f"   error: {x}")
            return 0
    finally:
        t.close()
    print(f"    唔知命令: {cmd}（python -m template help）")
    return 1


if __name__ == "__main__":
    main()
