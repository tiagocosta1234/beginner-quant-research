"""
Round 134, batch C: smarter targets, independent confirmation.
Pre-registered 2026-09-26 -- rules, variants and verdict rules committed before
any result is run. Everything is flat by 16:00 ET, through idea_harness, with
real costs and $300 risk per trade unless stated.

C1  Regime-conditioned STDV continuation (Round 132's rule, k=2.0, T=0.5)
    regime score before day t = |r20| / (sd of the 20 daily log returns * sqrt(20)),
    r20 = the 20-RTH-close return up to day t-1; "trending" = score >= the 2/3
    quantile of all earlier scores (expanding, >= 60 prior days).
    Variants: trending only; trending AND breakout direction = sign(r20).
    MNQ = discovery; MGC = the decisive test (this idea was motivated by 2025's
    MNQ results). Sanity: unfiltered must reproduce Round 132 (MNQ n=520
    +$19.29; MGC n=256 -$9.2).
    Replication: the MGC version of the same variant has positive net
    expectancy with P(edge>0) >= 0.95 over all its trades.
    Power note (from signal counts, before any P&L): the MGC filter leaves 69
    (trending) and 28 (aligned) trades, so this test has little power -- a miss
    there is weak evidence either way, but the rule stands as written.
C2  Crabel NR7 opening-range breakout: trade day t only if day t-1's RTH range
    was the narrowest of days t-7..t-1. Range (09:30, 09:30+N], first close beyond
    it by 12:00, stop at the other side, 2R target or hold to the close.
    Variants: N in {15, 30} x exit in {2R, hold} on MNQ and on MGC (8).
    Replication: the same variant on the other instrument positive with P >= 0.95.
C3  Gold session drift, MGC 24-hour data. Segments (whole hours, so the hourly
    source can match): Asia 18:00-02:00, London 02:00-08:00, NY morning
    08:00-11:00, NY rest 11:00-16:00. One contract per day: enter at the first
    bar's open after the segment start, exit at the last close by its end.
    Direction per segment = the sign of its IN-SAMPLE mean (so in-sample P is
    inflated by design; out-of-sample is the test). 4 variants.
    Replication: GC=F hourly (a separate data source, same market and period) --
    same sign with P >= 0.95.
C4  Hourly momentum across 7 instruments (Yahoo hourly, May 2024 - Sep 2026:
    ES, YM, RTY, NQ, GC, SI, CL as micros). At the bar closing at H, trade each
    instrument in the sign of its return since the previous day's 16:00 close;
    stop 1 x ATR(14 hourly bars), no target, flat at 16:00. One trade per
    instrument per day. Variants: H in {10:00, 15:00}, judged as the
    equal-risk portfolio (per-instrument rows are descriptive).
    Replication: at least 5 of the 7 instruments positive on their own.

18 variants (C1 4, C2 8, C3 4, C4 2) take the ledger from k=108 to k=126.
Candidate (unchanged bar): net and before-cost expectancy > 0, IS P(edge>0) >= 0.95,
OOS P(edge>0) >= 1 - 0.01/126 = 0.99992 -- AND its replication rule above.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round132_stdv_continuation as S

T = dt.time
N_VARIANTS = 18


# ---------------------------------------------------------------- C1 ----

def regime_table(days):
    """Per tday: score and sign of the prior-20-day trend, and the causal threshold."""
    close = pd.Series({d["tday"]: float(d["session"]["close"].iloc[-1]) for d in days}).sort_index()
    lr = np.log(close).diff()
    r20 = close.shift(1) / close.shift(21) - 1
    vol = lr.shift(1).rolling(20).std() * np.sqrt(20)
    score = (r20.abs() / vol).replace([np.inf, -np.inf], np.nan)
    thresh = score.shift(1).expanding(min_periods=60).quantile(2 / 3)
    return pd.DataFrame({"score": score, "sign": np.sign(r20), "thresh": thresh})


def c1_filter(sig, regime, align):
    tday = (pd.to_datetime(sig["ts"]) + pd.Timedelta(hours=6)).dt.normalize()
    rg = regime.reindex(tday.values)
    keep = (rg["score"].values >= rg["thresh"].values)
    if align:
        keep &= (rg["sign"].values == sig["direction"].values)
    return sig[keep].reset_index(drop=True)


# ---------------------------------------------------------------- C2 ----

def orb_signals(days, symbol, minutes, target, nr7_only=True):
    tick, out = H.TK[symbol], []
    end_or = (dt.datetime(2000, 1, 1, 9, 30) + dt.timedelta(minutes=minutes)).time()
    rng = pd.Series({d["tday"]: d["session"]["high"].max() - d["session"]["low"].min() for d in days}).sort_index()
    nr7 = (rng == rng.rolling(7).min()).shift(1).fillna(False)  # yesterday was the narrowest of its last 7
    for d in days:
        if nr7_only and not nr7.get(d["tday"], False):
            continue
        s = d["session"]
        t = s.index.time
        box = s[(t > T(9, 30)) & (t <= end_or)]
        if len(box) < minutes * 0.8:
            continue
        hi_, lo_ = box["high"].max(), box["low"].min()
        for ts, c in s[(t > end_or) & (t <= T(12, 0))]["close"].items():
            dd = 1 if c > hi_ else -1 if c < lo_ else 0
            if dd == 0:
                continue
            sl = lo_ if dd == 1 else hi_
            dist = abs(c - sl)
            if dist >= 8 * tick:
                out.append((ts, dd, c, sl, c + dd * 2 * dist if target == "2R" else np.nan))
            break
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


# ---------------------------------------------------------------- C3 ----

SEGMENTS = {"Asia 18-02": (T(18, 0), T(2, 0)), "London 02-08": (T(2, 0), T(8, 0)),
            "NY morning 08-11": (T(8, 0), T(11, 0)), "NY rest 11-16": (T(11, 0), T(16, 0))}


def _sm(t):
    return ((t.hour * 60 + t.minute) - 18 * 60) % 1440  # minutes since 18:00 ET


def segment_moves(bars, start, end):
    """Per tday: (entry_ts, exit_ts, first open after start, last close by end)."""
    sm = pd.Series([_sm(t) for t in bars.index.time], index=bars.index)
    a, b = _sm(start), _sm(end) if end != T(18, 0) else 1440
    seg = bars[(sm > a) & (sm <= b)]
    g = seg.groupby("tday")
    return pd.DataFrame({"entry_ts": g.apply(lambda x: x.index[0]), "exit_ts": g.apply(lambda x: x.index[-1]),
                         "entry": g["open"].first(), "exit": g["close"].last(), "n": g.size()})


def c3_trades(moves, symbol, direction, min_bars):
    m = moves[moves["n"] >= min_bars]
    cpc = H.cost_per_contract(symbol)
    pnl = direction * (m["exit"] - m["entry"]) * H.PV[symbol] - cpc
    return pd.DataFrame({"entry_ts": m["entry_ts"].values, "exit_ts": m["exit_ts"].values,
                         "direction": direction, "contracts": 1, "pnl": pnl.values, "r": np.nan})


# ---------------------------------------------------------------- C4 ----

def hourly_momentum_trades(df, micro, hour):
    tr_ = pd.concat([df["high"] - df["low"], (df["high"] - df["close"].shift()).abs(),
                     (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    atr = tr_.rolling(14).mean()
    close16 = df[df.index.hour == 16].groupby("tday")["close"].last()
    prev = close16.shift(1)
    sig_bars = df[df.index.hour == hour]
    rows = []
    for ts, r in sig_bars.iterrows():
        pc, a = prev.get(r["tday"], np.nan), atr.get(ts, np.nan)
        if np.isnan(pc) or np.isnan(a) or a <= 0 or r["close"] == pc:
            continue
        d = 1 if r["close"] > pc else -1
        rows.append((ts, d, r["close"], r["close"] - d * a, np.nan))
    sig = pd.DataFrame(rows, columns=["ts", "direction", "entry", "sl", "tp"])
    tr = H.resolve_bracket(sig, df, micro, flat_time=T(16, 0))
    return tr.assign(cost=tr["contracts"] * H.cost_per_contract(micro), symbol=micro)


# -------------------------------------------------------------- main ----

if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch C = {k}; OOS bar = {H.oos_bar(k):.5f}\n")
    mnq, mgc = H.load_days("MNQ"), H.load_days("MGC")
    days = {"MNQ": mnq, "MGC": mgc}
    tdays = {s: [d["tday"] for d in days[s]] for s in days}
    allbars = {s: H.bars_from_days(days[s], "all") for s in days}
    sess = {s: H.bars_from_days(days[s], "session") for s in days}
    rows, verdicts = [], {}

    print("C1 regime-conditioned STDV continuation")
    base = {s: S.continuation_signals(days[s], s, 2.0, 0.5) for s in days}
    for s, (n0, e0) in {"MNQ": (520, 19.29), "MGC": (256, -9.2)}.items():
        tr0 = H.resolve_bracket(base[s], allbars[s], s)
        assert len(tr0) == n0 and abs(tr0["pnl"].mean() - e0) < 0.15, f"C1 sanity failed for {s}"
    c1 = {}
    for align in [False, True]:
        for s in ["MNQ", "MGC"]:
            sig = c1_filter(base[s], regime_table(days[s]), align)
            label = f"C1 {s} STDV continuation, trending regime{' + aligned' if align else ''}"
            c1[(s, align)] = H.test_idea(label, H.resolve_bracket(sig, allbars[s], s), tdays[s], s, k)
            rows.append(c1[(s, align)])
    for align in [False, True]:
        g = c1[("MGC", align)]
        st = J.edge_stats(H.resolve_bracket(c1_filter(base["MGC"], regime_table(mgc), align), allbars["MGC"], "MGC"))
        rep = g["exp"] > 0 and st["p_pos"] >= 0.95
        verdicts[f"C1 align={align}"] = dict(replicated=rep, candidate=c1[("MNQ", align)]["candidate"] and rep, mgc_p_all=st["p_pos"])

    print("\nC2 NR7 opening-range breakout")
    c2, c2_tr = {}, {}
    for s in ["MNQ", "MGC"]:
        for m in [15, 30]:
            for tg in ["2R", "hold"]:
                c2_tr[(s, m, tg)] = H.resolve_bracket(orb_signals(days[s], s, m, tg), sess[s], s)
                c2[(s, m, tg)] = H.test_idea(f"C2 {s} NR7 ORB {m}-min, {tg}", c2_tr[(s, m, tg)], tdays[s], s, k)
                rows.append(c2[(s, m, tg)])
    for (s, m, tg), r in c2.items():
        o = ("MGC" if s == "MNQ" else "MNQ", m, tg)
        st = J.edge_stats(c2_tr[o])
        rep = c2[o]["exp"] > 0 and st["p_pos"] >= 0.95
        verdicts[f"C2 {s} {m} {tg}"] = dict(replicated=rep, candidate=r["candidate"] and rep)

    print("\nC3 gold session drift (direction = sign of the in-sample mean)")
    gc_h = H.load_yahoo_hourly("GC=F")
    for name, (a, b) in SEGMENTS.items():
        mv = segment_moves(allbars["MGC"], a, b)
        need = int(0.8 * (((_sm(b) if b != T(18, 0) else 1440) - _sm(a))))
        is_mean = c3_trades(mv[mv.index < J.OOS_START], "MGC", 1, need)["pnl"].mean()
        d = 1 if is_mean > 0 else -1
        tr = c3_trades(mv, "MGC", d, need)
        r = H.test_idea(f"C3 MGC {name}, {'long' if d == 1 else 'short'} 1 contract", tr, tdays["MGC"], "MGC", k)
        rows.append(r)
        hv = segment_moves(gc_h, a, b)
        htr = c3_trades(hv, "MGC", d, int(0.8 * need / 60))
        hs = J.edge_stats(htr)
        rep = hs["exp"] > 0 and hs["p_pos"] >= 0.95
        print(f"     GC=F hourly, same direction: n={hs['n']} ${hs['exp']:+.1f}/day P(edge>0) {hs['p_pos']:.3f} -> "
              f"{'replicates' if rep else 'does not replicate'}")
        verdicts[f"C3 {name}"] = dict(replicated=rep, candidate=r["candidate"] and rep)

    print("\nC4 hourly momentum, 7-instrument equal-risk portfolio (Yahoo hourly)")
    hourly = {y: H.load_yahoo_hourly(y) for y in H.YAHOO_MICRO}
    for hour in [10, 15]:
        parts = []
        for y, micro in H.YAHOO_MICRO.items():
            tr = hourly_momentum_trades(hourly[y], micro, hour)
            parts.append(tr)
            st = J.edge_stats(tr)
            print(f"     {micro:<4} {hour}:00 n={st['n']:>4} ${st['exp']:+7.1f}/trade P(edge>0) {st['p_pos']:.2f}")
        port = pd.concat(parts, ignore_index=True)
        pdays = sorted(set().union(*[set(h["tday"]) for h in hourly.values()]))
        r = H.test_idea(f"C4 hourly momentum {hour}:00 -> 16:00, 7-instrument portfolio", port, pdays, "MNQ", k)
        rows.append(r)
        n_pos = sum(p["pnl"].mean() > 0 for p in parts)
        verdicts[f"C4 {hour}:00"] = dict(instruments_positive=int(n_pos), replicated=n_pos >= 5, candidate=r["candidate"] and n_pos >= 5)

    lines = H.ledger_rows(rows, "Round 134 batch C (pre-registered)", commit)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round134_results.json"), "w") as f:
        json.dump(dict(rows=rows, verdicts=verdicts), f, indent=1, default=str)
    print("\nverdicts (candidate = ledger bar AND replication):")
    for key, v in verdicts.items():
        print(f"  {key:<32} {v}")
    print(f"\n==== {sum(v['candidate'] for v in verdicts.values())} candidates; ledger now k={H.ledger_count()} ====")
