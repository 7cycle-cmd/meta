"""function.py — monitor 業務邏輯（零 SQL，都喺 sql.py 存取層）"""


def verify_totals(current, real):
    """核對快照 total 同真實掃描一致（返回偏差清單）"""
    diffs = []
    for row in current:
        expected = real.get(row["structure_type_id"] if "structure_type_id" in row
                            else row["tree_id"])
        label = ("structure_type_id" if "structure_type_id" in row else "tree_id")
        if expected is None:
            diffs.append(f"{label}={row[label]} 快照有、真實冇")
        elif row["total"] != expected:
            diffs.append(f"{label}={row[label]} 快照={row['total']} 真實={expected}")
    return diffs
