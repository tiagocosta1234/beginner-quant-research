"""DAY2K-I: index intraday momentum (first half hour / second-to-last half hour -> last half hour). PREREG_DAY2K_I.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2ki --dry-run | --calibrate | --run"""
import sys
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
from forex.self_improving.day2k import day2k as D

ATH = ZoneInfo("Europe/Athens"); UTC = ZoneInfo("UTC")
EX = {"SP": ("America/New_York", (9, 30), (16, 0)), "NSDQ": ("America/New_York", (9, 30), (16, 0)), "DOW": ("America/New_York", (9, 30), (16, 0)), "DAX": ("Europe/Berlin", (9, 0), (17, 30))}
D.DEV_T = 2.70


def srv_epoch(day, tz, hm):
    """server-clock naive epoch (seconds) of local exchange time hm on calendar date `day` (datetime.date)"""
    loc = datetime(day.year, day.month, day.day, hm[0], hm[1], tzinfo=ZoneInfo(tz)); s = loc.astimezone(ATH).replace(tzinfo=None)
    return int((s - datetime(1970, 1, 1)).total_seconds())


def day_rows(sym, days):
    tz, (oh, om), (ch, cm) = EX[sym]; A = D.load(sym); t = A["t"]; mid = lambda o, c: (A[o] + A[c]) / 2
    mo, mc = mid("bo", "ao"), mid("bc", "ac"); out = []
    def at(ep):
        i = int(np.searchsorted(t, ep)); return i if i < len(t) and t[i] == ep else -1
    prev_close_idx = None
    for d in days:
        dd = date.fromordinal(date(1970, 1, 1).toordinal() + int(d))
        o30 = at(srv_epoch(dd, tz, (oh, om))); c959 = at(srv_epoch(dd, tz, (oh, om + 29) if om + 29 < 60 else (oh + 1, om + 29 - 60)))   # last bar of the first half hour
        tm = ch * 60 + cm - 30; ts = (tm // 60, tm % 60)                                                                                            # start of the target window
        e = at(srv_epoch(dd, tz, ts)); x = at(srv_epoch(dd, tz, (ch, cm)))
        p3s = at(srv_epoch(dd, tz, ((tm - 30) // 60, (tm - 30) % 60))); p3e = at(srv_epoch(dd, tz, ((tm - 1) // 60, (tm - 1) % 60)))
        pc = at(srv_epoch(dd, tz, ((ch * 60 + cm - 1) // 60, (ch * 60 + cm - 1) % 60)))                                                              # this session's last bar (for tomorrow's overnight)
        r = dict(day=int(d), ok=False)
        if min(o30, c959, e, x, p3s, p3e) >= 0:
            m0 = (mo[e] + mc[e - 1]) / 2 if e > 0 else mo[e]
            r.update(ok=True, P1=(mc[c959] - mo[o30]) / m0 * 1e4, P3=(mc[p3e] - mo[p3s]) / m0 * 1e4, P2=np.nan, long_ret=(A["bo"][x] - A["ao"][e]) / m0 * 1e4, short_ret=(A["bo"][e] - A["ao"][x]) / m0 * 1e4,
                     gross=(mo[x] - mo[e]) / m0 * 1e4, spread=(A["ao"][e] - A["bo"][e] + A["ao"][x] - A["bo"][x]) / m0 * 1e4, c959=mc[c959], o30=mo[o30])
            if prev_close_idx is not None: r["P2"] = (mc[c959] - prev_close_idx) / m0 * 1e4
        if pc >= 0: prev_close_idx = mc[pc]
        out.append(r)
    return pd.DataFrame(out)


def stat(df, pred, perm=None, oracle=False):
    d = df[df.ok & np.isfinite(df[pred])].copy(); p = d[pred].to_numpy()
    if perm is not None: p = p[np.random.default_rng(perm).permutation(len(p))]
    long = p > 0
    if oracle: long = d.long_ret.to_numpy() >= d.short_ret.to_numpy()
    d["net"] = np.where(long, d.long_ret, d.short_ret); d["sgn"] = np.where(long, d.gross, -d.gross); d["hit"] = (d.net > 0).astype(float); return d, p


def summarise(d, p, days_all):
    dev = d.day <= D.d64(D.DEV_HI); val = (d.day >= D.d64(D.VAL_LO)) & (d.day <= D.d64(D.VAL_HI)); r = {}
    for lab, m in (("dev", dev), ("val", val)):
        x = d[m]; mn, tn = D.block_t(x.net.to_numpy()); mg = float(x.sgn.mean()); ml = float(x.long_ret.mean()); _, tl = D.block_t(x.long_ret.to_numpy())
        r[lab] = dict(n=len(x), net=mn, t=tn, gross=mg, hit=float(x.hit.mean()), long_net=ml, long_t=tl, spread=float(x.spread.mean()), rho=float(pd.Series(p[m.to_numpy()]).corr(x.gross.reset_index(drop=True), method="spearman")))
    return r


def main():
    a = sys.argv[1:]; days = D.trading_days(D.LO, D.VAL_HI); data = {s: day_rows(s, days) for s in EX}
    if "--dry-run" in a:
        for s, df in data.items(): print(f"{s}: days with all bars {int(df.ok.sum())} of {len(df)}, P2 available {int(df.P2.notna().sum())}, mean spread round trip {df.spread.mean():.2f} bp, mean abs 30-min return {df.gross.abs().mean():.2f} bp")
        d = data["SP"]; r = d[d.ok].iloc[400]; print("hand check SP", np.datetime64(int(r.day), "D"), {k: round(float(v), 3) for k, v in r.items() if k not in ("ok",)})
        print("DST check: server epoch of 09:30 NY on 2023-03-13 (US DST started 03-12, EU 03-26) and 2023-03-28:", [datetime.utcfromtimestamp(srv_epoch(date(2023, 3, dd), "America/New_York", (9, 30))).strftime("%m-%d %H:%M server") for dd in (13, 28)])
        bad = n = 0; rng = np.random.default_rng(3)
        for _ in range(40):
            s = list(EX)[int(rng.integers(4))]; df = data[s]; r = df[df.ok].iloc[int(rng.integers(50, int(df.ok.sum())))]; A = D.load(s); tz, (oh, om), (ch, cm) = EX[s]
            dd = date.fromordinal(date(1970, 1, 1).toordinal() + int(r.day)); tm = ch * 60 + cm - 30; cut = srv_epoch(dd, tz, (tm // 60, tm % 60)); m = A["t"] < cut; t = A["t"][m]
            i0 = int(np.searchsorted(t, srv_epoch(dd, tz, (oh, om)))); i1 = int(np.searchsorted(t, srv_epoch(dd, tz, (oh, om + 29) if om + 29 < 60 else (oh + 1, om + 29 - 60))))
            p1 = ((A["bc"][m][i1] + A["ac"][m][i1]) / 2 - (A["bo"][m][i0] + A["ao"][m][i0]) / 2)
            full_p1 = (r.c959 - r.o30); n += 1; bad += int(not np.isclose(p1, full_p1, atol=1e-6))
        print(f"truncation test (P1 from bars before the target window): {n - bad}/{n} identical"); return
    rows = []
    worlds = [("real", None, False)] + ([("oracle", None, True), ("p171", 171, False), ("p172", 172, False), ("p173", 173, False)] if "--calibrate" in a else [])
    for world, seed, orc in worlds:
        if "--calibrate" not in a and world != "real": continue
        for s in EX:
            for pred in ("P1", "P2", "P3"):
                d, p = stat(data[s], pred, seed, orc); r = summarise(d, p, days); rows.append(dict(world=world, cell=f"{s}-{pred}", **{f"{k}_{lab}": v for lab in ("dev", "val") for k, v in r[lab].items()}))
        us = pd.concat([data[s].assign(sym=s) for s in ("SP", "NSDQ", "DOW")]).groupby("day").mean(numeric_only=True).reset_index(); us["ok"] = us.ok > 0.99
        for pred in ("P1", "P2", "P3"):
            d, p = stat(us, pred, seed, orc); r = summarise(d, p, days); rows.append(dict(world=world, cell=f"US3-{pred}", **{f"{k}_{lab}": v for lab in ("dev", "val") for k, v in r[lab].items()}))
    R_ = pd.DataFrame(rows); R_["S1"] = (R_.net_dev > 0) & (R_.t_dev >= 2.7) & (R_.net_dev > R_.long_net_dev) & (R_.net_val > 0) & (R_.t_val >= 1.65) & (R_.n_val >= 200)
    pd.set_option("display.width", 250)
    if "--calibrate" in a:
        o = R_[R_.world == "oracle"]; print("POSITIVE CONTROL (oracle sign) mean dev net bp: min %.1f median %.1f" % (o.net_dev.min(), o.net_dev.median()))
        for w in ("p171", "p172", "p173"): q = R_[R_.world == w]; print(f"placebo {w}: S1 {int(q.S1.sum())} | cells with dev t >= 2.7: {int((q.t_dev >= 2.7).sum())} | best dev t {q.t_dev.max():.2f}")
        return
    q = R_[R_.world == "real"].drop(columns=["world"]); q.to_csv(D.CACHE / "DAY2KI_cells.csv", index=False)
    print(q[["cell", "n_dev", "gross_dev", "net_dev", "t_dev", "hit_dev", "rho_dev", "spread_dev", "long_net_dev", "n_val", "net_val", "t_val", "hit_val", "long_net_val", "S1"]].round(3).to_string(index=False)); print("S1 survivors:", int(q.S1.sum()))


if __name__ == "__main__":
    main()
