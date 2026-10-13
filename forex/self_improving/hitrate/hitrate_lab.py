"""Gold intraday hit-rate lab (see PREREG_HITRATE.md). python -m forex.self_improving.hitrate.hitrate_lab"""
import numpy as np, pandas as pd

F = "D:/finance/beginner-quant-research/forex/data_mt5/XAUUSD_M1_rates.parquet"
WINDOWS = {"A": ("2021-12-01", "2023-06-30"), "B": ("2023-07-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31")}
RULES = ["asian-break", "asian-fade", "ldn-mom", "ldn-fade", "ny-mom", "ny-fade", "sweep", "trend", "antitrend", "gap-fade", "gap-follow"]


def load():
    d = pd.read_parquet(F).sort_values("t").drop_duplicates("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)].reset_index(drop=True); return d


def days(d):
    t = d.t.values; day = t // 86400; hour = (t % 86400) / 3600.0; u, st = np.unique(day, return_index=True); en = np.r_[st[1:], len(t)]; return t, day, hour, u, st, en


def signals(d, t, hour, u, st, en):
    bo, bh, bl, bc = d.bo.values, d.bh.values, d.bl.values, d.bc.values; rng = np.array([bh[s:e].max() - bl[s:e].min() for s, e in zip(st, en)]); cl = np.array([bc[e - 1] for e in en]); sig = []
    for k in range(21, len(u)):
        s, e = st[k], en[k]; hr = hour[s:e]; adr = rng[k - 20:k].mean(); at = lambda h: s + int(np.searchsorted(hr, h))
        i1, i9, i10, i1630, i17, i20 = at(1.0), at(9.0), at(10.0), at(16.5), at(17.0), at(20.0)
        if i9 - i1 < 100 or i10 >= e or i17 >= e: continue
        hi, lo = bh[i1:i9].max(), bl[i1:i9].min(); ent = {}
        for i in range(i9, min(i20, e - 1)):
            if bc[i] > hi: ent["asian-break"] = (i + 1, 1); ent["asian-fade"] = (i + 1, -1); break
            if bc[i] < lo: ent["asian-break"] = (i + 1, -1); ent["asian-fade"] = (i + 1, 1); break
        r = bc[i10 - 1] - bo[i1]; sg = 1 if r > 0 else -1; ent["ldn-mom"] = (i10, sg); ent["ldn-fade"] = (i10, -sg)
        r = bc[i17 - 1] - bo[i1630]; sg = 1 if r > 0 else -1; ent["ny-mom"] = (i17, sg); ent["ny-fade"] = (i17, -sg)
        pdh, pdl = bh[st[k - 1]:en[k - 1]].max(), bl[st[k - 1]:en[k - 1]].min()
        for i in range(i1, at(18.0)):
            if bh[i] > pdh and bc[i] < pdh: ent["sweep"] = (i + 1, -1); break
            if bl[i] < pdl and bc[i] > pdl: ent["sweep"] = (i + 1, 1); break
        sg = 1 if cl[k - 1] > cl[k - 21] else -1; ent["trend"] = (i10, sg); ent["antitrend"] = (i10, -sg)
        gap = bo[i1] - cl[k - 1]
        if abs(gap) > 0.1 * adr: ent["gap-fade"] = (i1 + 5, -1 if gap > 0 else 1); ent["gap-follow"] = (i1 + 5, 1 if gap > 0 else -1)
        for rule, (i, sd) in ent.items():
            if i < e - 2: sig.append((rule, int(u[k]), i, sd, adr, at(22.0)))
    return sig


def simulate(d, sig, w):
    bo, bh, bl, bc, ao, ah, al, ac = (d[c].values for c in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")); out = []
    for rule, day, i, sd, adr, iend in sig:
        sl = w * adr; tp = sl * 4 / 3; ent = ao[i] if sd > 0 else bo[i]; end = min(iend, len(bc) - 1)
        if end <= i: continue
        if sd > 0: hit_tp = np.nonzero(bh[i:end] >= ent + tp)[0]; hit_sl = np.nonzero(bl[i:end] <= ent - sl)[0]; ex = bc[end]
        else: hit_tp = np.nonzero(al[i:end] <= ent - tp)[0]; hit_sl = np.nonzero(ah[i:end] >= ent + sl)[0]; ex = ac[end]
        a = hit_tp[0] if len(hit_tp) else 10 ** 9; b = hit_sl[0] if len(hit_sl) else 10 ** 9
        if a == 10 ** 9 and b == 10 ** 9: res, R = 0, sd * (ex - ent) / sl
        elif b <= a: res, R = -1, -1.0
        else: res, R = 1, 4 / 3
        out.append((rule, w, day, res, R))
    return pd.DataFrame(out, columns=["rule", "w", "day", "res", "R"])


def main():
    d = load(); t, day, hour, u, st, en = days(d); sig = signals(d, t, hour, u, st, en); print("signals", len(sig), flush=True); rows = []
    for w in (0.20, 0.35):
        tr = simulate(d, sig, w); tr["date"] = pd.to_datetime(tr.day * 86400, unit="s")
        for rule in RULES:
            r = {"rule": rule, "w": w}; ok = True
            for nm, (a, b) in WINDOWS.items():
                x = tr[(tr.rule == rule) & (tr.date >= a) & (tr.date <= b)]; n = len(x); dec = x[x.res != 0]
                m = x.R.mean() if n else np.nan; z = m / (x.R.std() / np.sqrt(n)) if n > 5 else np.nan; r.update({f"{nm}_n": n, f"{nm}_R": m, f"{nm}_z": z, f"{nm}_hit": 100 * (dec.res == 1).mean() if len(dec) else np.nan, f"{nm}_to": 100 * (x.res == 0).mean() if n else np.nan})
            r["pass"] = bool(r["A_R"] > 0 and r["B_R"] > 0 and r["VAL_R"] >= 0.15 and r["VAL_z"] >= 3.0 and r["VAL_n"] >= 150); rows.append(r)
    o = pd.DataFrame(rows); o.to_csv("D:/finance/si_ledgers/HITRATE_real.csv", index=False)
    cols = ["rule", "w", "A_n", "A_R", "B_R", "VAL_n", "VAL_R", "VAL_z", "VAL_hit", "VAL_to", "pass"]; print(o[cols].round(3).to_string(index=False)); print("cells passing:", int(o["pass"].sum()), "of", len(o))


if __name__ == "__main__":
    main()
