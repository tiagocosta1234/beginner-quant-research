"""
Round 138, batch G: a sub-hour pattern scan (1-minute bars, 5-30 minute holds).
Pre-registered 2026-09-26 -- the scan, selection rule, validation and
replication rules are committed before any result is run.

the trader: "we already have the broker data, look for any pattern ... in lower
timeframes than the 1 hour". The BrokerAPI pulls hold 53 days (2026-07-26 ->
09-24) of 24-hour 1-minute bars for MNQ, MES, MYM, M2K, MGC, SIL -- too short
to establish anything alone (a scan of hundreds of patterns on 53 days finds
some by chance). So:
  DISCOVER  on the long 1-minute MNQ and MGC files (24-hour contract files, one
            contract per day), trading days 2022-12 .. 2025-06-30;
  VALIDATE  the selected patterns on 2025-07-01 .. 2026-09 (same instrument);
  REPLICATE their direction on the BrokerAPI siblings never used for discovery:
            index patterns on MES, MYM, M2K; gold patterns on SIL.

Mechanics: each trading day (18:00 ET start) is laid on a 1-minute grid to
16:00 ET with the last traded price carried forward. A trade enters at a
minute's close and exits h minutes later (h in {5, 15, 30}) -- a pure time exit
-- and must be out by 16:00. 1 contract; cost = commission + 2 ticks per round
trip (MNQ $2.24 = 1.12 points). For triggered patterns one position at a time
(no new entry until the last one exits).

Pattern cells (the direction of each cell = the sign of its discovery-period
mean, so every cell is a "which way, if any" test):
  P1 time-of-day: each 5-minute slot of the day (263 slots, 18:05 -> 16:00),
     enter at the slot start, hold 5 minutes. 263 x 2 instruments = 526 cells.
  P2 after a big move: |1-min z| >= k or |5-min z| >= k (z = return / SD of
     the previous 60 one-minute returns, scaled by sqrt(5) for 5-min), k in
     {3, 4, 5}; follow or fade; h in {5, 15, 30}. 36 cells.
  P3 volume shock: 1-minute volume >= m x that minute-of-day's median volume
     (medians from the discovery period), m in {5, 10}; relative to that
     minute's direction; h in {5, 15, 30}. 12 cells.
  P5 lead-lag: a >= k SD 1-minute move in MNQ -> trade MGC one minute later
     (and vice versa), k in {3, 4}, h in {5, 15}. 8 cells.
  Total 582 cells.

Selection (discovery only): net mean > 0 after costs, t >= 3.5, >= 100 trades;
at most the 10 highest t. (By chance alone ~0.14 of 582 cells would pass t >= 3.5.)
Validation: each selected cell is a ledger variant (k = ledger + number
selected). Candidate = OOS net mean > 0 with bootstrap P(edge>0) >= 1 - 0.01/k,
AND replication: mean > 0 on at least 2 of MES/MYM/M2K (index cells) or on SIL
(gold cells) -- direction only; 53 days cannot show significance.
If no cell passes selection, the scan's answer is "none".
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round11_fvg_bias import load_1m_brokerapi

SPLIT = pd.Timestamp("2025-07-01")
HORIZONS = [5, 15, 30]
DAY_MIN = 22 * 60  # 18:00 -> 16:00
T_SEL, MIN_N, MAX_SEL = 3.5, 100, 10


def grid(bars):
    """bars with tday -> DataFrame (tday x minute 1..1320) of close (ffill) and volume."""
    sm = ((bars.index.hour * 60 + bars.index.minute) - 18 * 60) % 1440
    b = bars.assign(sm=sm)
    b = b[(b["sm"] >= 1) & (b["sm"] <= DAY_MIN)]
    close = b.pivot_table(index="tday", columns="sm", values="close", aggfunc="last")
    vol = b.pivot_table(index="tday", columns="sm", values="vol", aggfunc="sum")
    close = close.reindex(columns=range(1, DAY_MIN + 1)).ffill(axis=1)
    vol = vol.reindex(columns=range(1, DAY_MIN + 1)).fillna(0.0)
    keep = close.notna().sum(axis=1) >= 0.9 * DAY_MIN
    return close[keep], vol[keep]


def load_long(symbol):
    return grid(H.bars_from_days(H.load_days(symbol), "all"))


def load_tsx(symbol):
    d = load_1m_brokerapi(os.path.join(H.HERE, "..", "data", f"{symbol}_1MIN_BROKERAPI.csv"))
    d = d.assign(tday=(d.index + pd.Timedelta(hours=6)).normalize())
    return grid(d)


def features(close):
    c = close.values
    r1 = np.full_like(c, np.nan); r1[:, 1:] = np.log(c[:, 1:] / c[:, :-1])
    r5 = np.full_like(c, np.nan); r5[:, 5:] = np.log(c[:, 5:] / c[:, :-5])
    sd = pd.DataFrame(r1).T.rolling(60, min_periods=40).std().shift(1).T.values  # previous 60 minutes
    sd = np.where(sd > 0, sd, np.nan)  # stale carried-forward minutes give SD 0: no score, not infinity
    return r1, r5, r1 / sd, r5 / (sd * np.sqrt(5))


def fwd(close, h):
    c = close.values
    f = np.full_like(c, np.nan); f[:, :-h] = c[:, h:] - c[:, :-h]
    return f  # points; NaN where the exit would pass 16:00


def triggered_trades(trig, sign, f, h, pv, cost):
    """One position at a time per day: walk each day's trigger minutes, skip while in a trade."""
    out_day, out_pnl = [], []
    for i in range(trig.shape[0]):
        cols = np.flatnonzero(trig[i] & ~np.isnan(f[i]))
        nxt = -1
        for j in cols:
            if j < nxt:
                continue
            out_day.append(i); out_pnl.append(sign[i, j] * f[i, j] * pv - cost)
            nxt = j + h
    return np.array(out_day, int), np.array(out_pnl)


def cell_trades(kind, params, data, sym, other=None):
    close, vol, feats = data
    pv, cost = H.PV[sym], H.cost_per_contract(sym)
    r1, r5, z1, z5 = feats
    days = close.index
    if kind == "P1":
        slot, = params
        j = slot * 5 - 1  # enter at the close of minute 5*slot (array column m-1 holds minute m)
        f = fwd(close, 5)[:, j]
        ok = ~np.isnan(f)
        return days[ok], f[ok] * pv - cost, np.ones(ok.sum())
    if kind == "P2":
        zname, k, h = params
        z = z1 if zname == "1m" else z5
        trig = np.abs(np.nan_to_num(z)) >= k
        d, pnl = triggered_trades(trig, np.sign(np.nan_to_num(z)), fwd(close, h), h, pv, cost)
        return days[d], pnl, None
    if kind == "P3":
        m, h, med = params
        trig = (vol.values >= m * np.maximum(med, 1.0)) & (np.nan_to_num(r1) != 0)
        d, pnl = triggered_trades(trig, np.sign(np.nan_to_num(r1)), fwd(close, h), h, pv, cost)
        return days[d], pnl, None
    if kind == "P5":
        k, h = params
        lead_z1 = np.full_like(other, np.nan)
        lead_z1[:, 1:] = other[:, :-1]  # act one minute AFTER the other market's move
        trig = np.abs(np.nan_to_num(lead_z1)) >= k
        d, pnl = triggered_trades(trig, np.sign(np.nan_to_num(lead_z1)), fwd(close, h), h, pv, cost)
        return days[d], pnl, None


def signed(pnl_raw, cost, direction):
    """pnl_raw already includes -cost for the +1 direction; flip the gross part only."""
    return direction * (pnl_raw + cost) - cost


def tstat(x):
    return float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else 0.0


def align(z_other, days_other, days_self):
    df = pd.DataFrame(z_other, index=days_other).reindex(days_self)
    return df.values


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    long_ = {}
    for sym in ["MNQ", "MGC"]:
        close, vol = load_long(sym)
        long_[sym] = (close, vol, features(close))
        c = close.values
        for h in HORIZONS:
            sdh = np.nanstd(c[:, h:] - c[:, :-h])
            print(f"{sym}: {len(close)} days | {h}-min move SD {sdh:.2f} pts; round-trip cost "
                  f"{H.cost_per_contract(sym) / H.PV[sym]:.2f} pts = {H.cost_per_contract(sym) / H.PV[sym] / sdh:.0%} of it")

    # ---- discovery scan ----
    cells = []
    for sym in ["MNQ", "MGC"]:
        cells += [(sym, "P1", (s,)) for s in range(1, DAY_MIN // 5)]
        cells += [(sym, "P2", (zn, k, h)) for zn in ["1m", "5m"] for k in [3, 4, 5] for h in HORIZONS]
        close, vol, _ = long_[sym]
        med = np.nanmedian(vol[vol.index < SPLIT].values, axis=0)
        cells += [(sym, "P3", (m, h, med)) for m in [5, 10] for h in HORIZONS]
        cells += [(sym, "P5", (k, h)) for k in [3, 4] for h in [5, 15]]
    scan = []
    for sym, kind, params in cells:
        other = None
        if kind == "P5":
            o = "MGC" if sym == "MNQ" else "MNQ"
            other = align(long_[o][2][2], long_[o][0].index, long_[sym][0].index)
        days, pnl, _ = cell_trades(kind, params, long_[sym], sym, other)
        is_ = days < SPLIT
        cost = H.cost_per_contract(sym)
        gross_is = pnl[is_] + cost
        direction = 1 if gross_is.mean() > 0 else -1
        net_is = signed(pnl[is_], cost, direction)
        scan.append(dict(sym=sym, kind=kind, params=params, direction=direction, n_is=int(is_.sum()),
                         mean_is=float(net_is.mean()) if len(net_is) else np.nan, t_is=tstat(net_is)))
    sdf = pd.DataFrame(scan)
    print(f"\nscan: {len(sdf)} cells; cells with net mean > 0 in discovery: {(sdf.mean_is > 0).sum()}; "
          f"t >= 2: {(sdf.t_is >= 2).sum()}, t >= 3: {(sdf.t_is >= 3).sum()}, t >= 3.5: {(sdf.t_is >= 3.5).sum()}")
    print("top 8 by discovery t:")
    for _, r in sdf.sort_values("t_is", ascending=False).head(8).iterrows():
        p = r.params[:2] if r.kind == "P3" else r.params
        print(f"   {r.sym} {r.kind} {p} dir {r.direction:+d}: n={r.n_is} net ${r.mean_is:+.2f}/trade t={r.t_is:.2f}")
    sel = sdf[(sdf.mean_is > 0) & (sdf.t_is >= T_SEL) & (sdf.n_is >= MIN_N)].sort_values("t_is", ascending=False).head(MAX_SEL)
    print(f"\nselected: {len(sel)}")

    # ---- validation + replication ----
    k = H.ledger_count() + len(sel)
    rows = []
    if len(sel):
        tsx = {s: None for s in ["MES", "MYM", "M2K", "SIL", "MNQ", "MGC"]}
        for s in tsx:
            c, v = load_tsx(s)
            tsx[s] = (c, v, features(c))
        for _, r in sel.iterrows():
            sym, kind, params, d = r.sym, r.kind, r.params, r.direction
            other = None
            if kind == "P5":
                o = "MGC" if sym == "MNQ" else "MNQ"
                other = align(long_[o][2][2], long_[o][0].index, long_[sym][0].index)
            days, pnl, _ = cell_trades(kind, params, long_[sym], sym, other)
            cost = H.cost_per_contract(sym)
            oos = signed(pnl[days >= SPLIT], cost, d)
            st = J.edge_stats(pd.DataFrame({"pnl": oos}), n_boot=40_000)
            sibs = ["MES", "MYM", "M2K"] if sym == "MNQ" else ["SIL"]
            rep = {}
            for s in sibs:
                if kind == "P3":
                    med_s = np.nanmedian(tsx[s][1].values, axis=0)
                    p_s = (params[0], params[1], med_s)
                else:
                    p_s = params
                oth = None
                if kind == "P5":
                    o = "MGC" if sym == "MNQ" else "MNQ"
                    oth = align(tsx[o][2][2], tsx[o][0].index, tsx[s][0].index)
                dd, pp, _ = cell_trades(kind, p_s, tsx[s], s, oth)
                rep[s] = float(signed(pp, H.cost_per_contract(s), d).mean()) if len(pp) else np.nan
            need = 2 if sym == "MNQ" else 1
            replicated = sum(v > 0 for v in rep.values() if not np.isnan(v)) >= need
            bar = H.oos_bar(k)
            cand = bool(st["exp"] > 0 and st["p_pos"] >= bar and replicated)
            name = f"G {sym} {kind} {r.params[:2] if kind == 'P3' else r.params} dir {d:+d}"
            print(f"  {name:<44} disc n={r.n_is} ${r.mean_is:+.2f} t={r.t_is:.2f} | OOS n={st['n']} ${st['exp']:+.2f} "
                  f"P {st['p_pos']:.4f} (bar {bar:.5f}) | BrokerAPI {', '.join(f'{s} ${v:+.2f}' for s, v in rep.items())} | "
                  f"{'CANDIDATE' if cand else 'no'}")
            rows.append(dict(name=name, n=st["n"], exp=st["exp"], exp_gross=st["exp"] + cost, p_is=1.0,
                             p_oos=st["p_pos"], replication=rep, candidate=cand))
        lines = [f"| {n} | 2026-09-26 | {r['name']} | Round 138 sub-hour scan (pre-registered) | {commit} | {r['n']} "
                 f"| {r['exp']:+.2f} | {r['exp_gross']:+.2f} | selected t>=3.5 / {r['p_oos']:.3f} | "
                 f"{'CANDIDATE' if r['candidate'] else 'no edge'} |" for n, r in enumerate(rows, start=H.ledger_count() + 1)]
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round138_results.json"), "w") as f:
        json.dump(dict(scan_size=len(sdf), passed_t35=int((sdf.t_is >= 3.5).sum()),
                       top=sdf.sort_values("t_is", ascending=False).head(20).drop(columns="params").to_dict("records"),
                       selected=rows), f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} candidates of {len(rows)} selected; ledger now k={H.ledger_count()} ====")
