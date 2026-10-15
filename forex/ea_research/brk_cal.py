"""BRK-CAL exactly as in PREREG_BRK_CAL.md: turn of month, after options expiry, first day of month, on round 1's session breakouts.
   python -m forex.ea_research.brk_cal"""
import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.ict2 import nw_t

DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")


def flags(days):
    d = pd.DatetimeIndex(sorted(set(days)))
    s = pd.Series(d, index=d)
    mon = d.to_period("M")
    rank_fwd = s.groupby(mon).cumcount()
    rank_back = s.groupby(mon).cumcount(ascending=False)
    tom = (rank_fwd < 3) | (rank_back == 0)
    third_fri = {p: pd.date_range(p.start_time, p.end_time, freq="W-FRI")[2] for p in set(mon)}
    post_opex = pd.Series([0 < (x - third_fri[x.to_period("M")]).days <= 5 and x.weekday() <= 2 for x in d], index=d)
    first = rank_fwd == 0
    return pd.DataFrame({"tom": tom.values, "post_opex": post_opex.values, "first": first.values}, index=d)


def main():
    ex = pd.read_parquet("D:/finance/si_ledgers/BRK_EXITS.parquet")
    ex["c"] = ex.mkt.map(mclass)
    out = []
    for m, g in ex.groupby("mkt"):
        f = flags(g.day)
        out.append(g.join(f, on="day"))
    df = pd.concat(out)
    df = df[df.day >= DEV[0]]
    chk = flags(df[df.mkt == "SP"].day)
    print("check: SP 2024 post-OPEX days:", [str(x.date()) for x in chk[(chk.post_opex) & (chk.index.year == 2024)].index[:6]], "| turn-of-month share", round(chk.tom.mean(), 3))
    cells = (("C1 turn of month, indices", (df.c == "index"), "tom"), ("C2 after options expiry, indices", (df.c == "index"), "post_opex"), ("C3 first day of month, all", df.c.notna(), "first"))
    for name, sel, col in cells:
        b, c = df[sel & (df.kind == "BRK")], df[sel & (df.kind == "CTRL")]
        r = {}
        for lab, (a, z) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = b[(b.day >= a) & (b.day <= z)]
            on, off = s[s[col]], s[~s[col]]
            cc = c[(c.day >= a) & (c.day <= z)]
            r[lab] = (len(on), on.X4_noTP.mean(), nw_t(on.groupby("day").X4_noTP.mean().to_numpy()), off.X4_noTP.mean(), cc[cc[col]].X4_noTP.mean())
        gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.39, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        print(f"{name}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) other days {v[3]:+.3f} random {v[4]:+.3f}" for k, v in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}")


if __name__ == "__main__":
    main()
