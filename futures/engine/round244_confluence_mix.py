"""
Round 244 (2026-09-30): mixing confluences onto the two rule-compliant strategies
with the most signal. the trader: "try to refine to mix confluences and refine
strategies". PRE-REGISTRATION -- every confluence, threshold, selection rule and
pass bar is fixed here before any filtered P&L is computed.

The warning this design answers: Round 223's confluence filter looked like a real
improvement on first pass and fell apart in Rounds 224-226 (no fold consistency,
reversed on independent data). Round 174: stacking confluences buys apparent
significance while collapsing trade count. So: fixed list, IS-only selection,
one OOS look with a multiple-testing bar, a random-filter control, and an
independent-market replication.

BASES (net of costs, rule-compliant):
  POC   the live bracket bot's POC-reversion trades (VA leg off, Round 230) at
        $50K sizing ($300 risk, MNQ), Databento NQ 2019-10..2026-09
  VA    unfiltered VA-rejection trades (round184.build_trades("NQ", False) --
        Combined POC+VA's full-history leg), Databento NQ
Replication market: the same two bases rebuilt on Databento ES (POC at MES $5/pt).

CONFLUENCES (binary, all causal at the 09:30 ET entry; thresholds fixed, no tuning):
  F1 trend    trade direction agrees with sign(prior close - SMA20 of prior closes)
  F2 gap      trade direction agrees with sign(today's open - prior RTH close)
  F3 smallgap |open - prior close| <= median |gap| of the prior 60 sessions
  F4 narrow   prior session range < SMA20 of prior ranges
  F5 lowvol   20-day realized vol of RTH closes < its prior-250-day median
  F6 lowvix   prior-day VIX close < its prior-250-day median (Yahoo ^VIX)
  F7 midweek  Tuesday-Thursday
  F8 quietON  overnight (18:00-09:29) range < median of the prior 20 overnights
SUBSETS per base: each confluence true / false (16) and every pair of different
confluences in all four state combinations (112) = 128.

SPLIT: IS < 2025-07-01 <= OOS (idea_harness). SELECTION, IS ONLY: a subset
qualifies if IS n >= 100, IS bootstrap P(mean > 0) >= 0.95, and IS mean >= base
IS mean + $10; qualifiers are ranked by IS bootstrap P(subset mean > the
complement's mean) and the top 5 per base become finalists (<= 10 total).
PASS (all required): OOS n >= 30; OOS P(mean > 0) >= 1 - 0.05/10 = 0.995;
OOS mean > the base's OOS mean; ES replication P(subset mean > complement mean,
full history) >= 0.80; and random control -- fewer than 5% of 500 random subsets
of the same IS size reach the finalist's IS P(mean > 0).
If anything passes, its filtered daily series goes through Round 241's one-month
sprint (P(pass within 21 days), OOS starts) and is reported against the unfiltered
base. Not ledger-eligible as new ideas (filters on existing signals); journal
either way.

POWER NOTES (--dry-run, counts only): tagged trades POC-NQ 1,206 (IS 963 / OOS
243), VA-NQ 988 (785 / 203), POC-ES 1,184, VA-ES 1,003. Confluence "gap" (trade
WITH the gap) is true for only 1-8% of trades -- both strategies fade the gap by
construction -- so its True state never reaches the n >= 100 floor; disclosed,
not changed. Other confluences split 33-64% true. With ~240 OOS trades, a subset
keeping half of them leaves ~120 OOS trades: enough for the 0.995 bar only if the
filtered edge is large.
"""
import os, sys, json, itertools, argparse, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import pandas as pd
import idea_harness as H

OOS = pd.Timestamp("2025-07-01")
FEATS = ("trend", "gap", "smallgap", "narrow", "lowvol", "lowvix", "midweek", "quietON")
N_BOOT = 2000


def daily_context(sym):
    """Per trading day (tday), causal features from Databento 1-min + ^VIX."""
    import round229_rth_vs_24x5 as R229
    old = R229.DB_FILE
    R229.DB_FILE = os.path.join(HERE, "..", "data", "databento", f"futures_{sym}.F_1m.parquet")
    days = R229.load_days()
    R229.DB_FILE = old
    rows = []
    for d in days:
        b, m = d["bars"], d["mins"]
        rth = b[(m >= 570) & (m < 960)]
        on = b[(m >= 1080) | (m < 570)]
        if rth.empty:
            continue
        rows.append(dict(tday=d["tday"], open=float(rth["open"].iloc[0]), close=float(rth["close"].iloc[-1]),
                         rng=float(rth["high"].max() - rth["low"].min()),
                         on_rng=float(on["high"].max() - on["low"].min()) if len(on) else np.nan))
    c = pd.DataFrame(rows).set_index("tday").sort_index()
    pc = c["close"].shift(1)
    c["prev_close"] = pc
    c["sma20"] = c["close"].rolling(20).mean().shift(1)
    c["gap"] = c["open"] - pc
    c["gap_med60"] = c["gap"].abs().rolling(60).median().shift(1)
    c["prev_rng"] = c["rng"].shift(1)
    c["rng_sma20"] = c["rng"].rolling(20).mean().shift(1)
    ret = np.log(c["close"]).diff()
    c["rv20"] = ret.rolling(20).std().shift(1)
    c["rv20_med250"] = c["rv20"].rolling(250, min_periods=120).median()
    c["on_med20"] = c["on_rng"].rolling(20).median().shift(1)
    vix = pd.read_csv(os.path.join(HERE, "..", "data", "daily", "^VIX_yahoo_daily.csv"), parse_dates=["date"]).set_index("date")["close"]
    vix_prev = vix.shift(1).reindex(c.index, method="ffill")
    c["vix_prev"] = vix_prev
    c["vix_med250"] = vix.shift(1).rolling(250, min_periods=120).median().reindex(c.index, method="ffill")
    return c


def tag(trades, ctx):
    """trades: tday (normalized date), direction, pnl. Adds F1..F8 (bool) and drops rows with missing context."""
    t = trades.merge(ctx, left_on="tday", right_index=True, how="left")
    t["trend"] = t["direction"] * np.sign(t["prev_close"] - t["sma20"]) > 0
    t["gap"] = t["direction"] * np.sign(t["gap"]) > 0
    t["smallgap"] = (t["open"] - t["prev_close"]).abs() <= t["gap_med60"]
    t["narrow"] = t["prev_rng"] < t["rng_sma20"]
    t["lowvol"] = t["rv20"] < t["rv20_med250"]
    t["lowvix"] = t["vix_prev"] < t["vix_med250"]
    t["midweek"] = pd.to_datetime(t["tday"]).dt.weekday.isin([1, 2, 3])
    t["quietON"] = t["on_rng"] < t["on_med20"]
    need = ["sma20", "gap_med60", "rng_sma20", "rv20_med250", "vix_med250", "on_med20"]
    return t.dropna(subset=need).reset_index(drop=True)


def subsets():
    for f in FEATS:
        for s in (True, False):
            yield ((f, s),)
    for f1, f2 in itertools.combinations(FEATS, 2):
        for s1, s2 in itertools.product((True, False), repeat=2):
            yield ((f1, s1), (f2, s2))


def mask(t, sub):
    m = np.ones(len(t), bool)
    for f, s in sub:
        m &= (t[f].to_numpy() == s)
    return m


def p_pos(x, seed=0):
    x = np.asarray(x, float)
    if len(x) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    return float((rng.choice(x, (N_BOOT, len(x))).mean(1) > 0).mean())


def p_gt(a, b, seed=0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 5 or len(b) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    return float((rng.choice(a, (N_BOOT, len(a))).mean(1) > rng.choice(b, (N_BOOT, len(b))).mean(1)).mean())


def poc_trades(sym):
    import round229_rth_vs_24x5 as R229
    import round230_no_va_leg as R230
    R229.DBS.RISK_PER_TRADE, R229.DBS.CAP_WIN_DOLLARS, R229.DBS.MAX_CONTRACTS = 300.0, 1650.0, 50
    R229.DLL, R229.DAY_PROFIT_CAP = 1000.0, 1650.0
    old = (R229.DB_FILE, R229.PV, R229.COST_PER_CONTRACT, R229.DBS.POINT_VALUE_MNQ)
    if sym == "ES":
        R229.DB_FILE = os.path.join(HERE, "..", "data", "databento", "futures_ES.F_1m.parquet")
        R229.PV, R229.COST_PER_CONTRACT, R229.DBS.POINT_VALUE_MNQ = 5.0, H.cost_per_contract("MES"), 5.0
    days = R229.load_days()
    tr, _ = R230.run(days, R229.build_profiles(days), R229.VARIANTS["A_current_rth"], no_va=True)
    R229.DB_FILE, R229.PV, R229.COST_PER_CONTRACT, R229.DBS.POINT_VALUE_MNQ = old
    return pd.DataFrame(dict(tday=pd.to_datetime(tr["tday"]).dt.normalize(), direction=tr["direction"].astype(int), pnl=tr["pnl"]))


def va_trades(sym):
    from round184_value_area_breakout import build_trades
    tr, _ = build_trades(sym, False)
    e = pd.to_datetime(tr["entry_ts"])
    return pd.DataFrame(dict(tday=e.dt.normalize(), direction=tr["direction"].astype(int), pnl=tr["pnl"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    ctx = {s: daily_context(s) for s in ("NQ", "ES")}
    bases = {("POC", "NQ"): poc_trades("NQ"), ("VA", "NQ"): va_trades("NQ"),
             ("POC", "ES"): poc_trades("ES"), ("VA", "ES"): va_trades("ES")}
    T = {k: tag(v, ctx[k[1]]) for k, v in bases.items()}
    print(f"built in {time.time() - t0:.0f}s")
    for k, t in T.items():
        is_n, oos_n = int((t["tday"] < OOS).sum()), int((t["tday"] >= OOS).sum())
        print(f"  {k}: {len(t)} tagged trades (IS {is_n}, OOS {oos_n}); share True per confluence: " +
              ", ".join(f"{f} {t[f].mean():.2f}" for f in FEATS))
    if args.dry_run:
        n_sub = sum(1 for _ in subsets())
        print(f"{n_sub} subsets per base")
        sys.exit(0)

    results = {"finalists": [], "all_qualifiers": {}}
    for base in ("POC", "VA"):
        t = T[(base, "NQ")]
        is_ = t[t["tday"] < OOS]
        base_is_mean = float(is_["pnl"].mean())
        quals = []
        for sub in subsets():
            m = mask(is_, sub)
            x, y = is_["pnl"].to_numpy()[m], is_["pnl"].to_numpy()[~m]
            if len(x) < 100:
                continue
            p = p_pos(x)
            if p >= 0.95 and x.mean() >= base_is_mean + 10:
                quals.append(dict(sub=sub, n=int(len(x)), mean=float(x.mean()), p_pos=p, p_vs_rest=p_gt(x, y)))
        quals.sort(key=lambda q: -q["p_vs_rest"])
        results["all_qualifiers"][base] = [dict(q, sub=str(q["sub"])) for q in quals]
        print(f"\n{base} (NQ): base IS mean ${base_is_mean:+.2f}/trade on {len(is_)} trades; {len(quals)} of 128 subsets qualify on IS")
        for q in quals[:5]:
            sub = q["sub"]
            m_all = mask(t, sub)
            oos = t[t["tday"] >= OOS]
            m_oos = mask(oos, sub)
            xo = oos["pnl"].to_numpy()[m_oos]
            base_oos = float(oos["pnl"].mean())
            p_oos = p_pos(xo) if len(xo) >= 5 else float("nan")
            te = T[(base, "ES")]
            me = mask(te, sub)
            rep = p_gt(te["pnl"].to_numpy()[me], te["pnl"].to_numpy()[~me])
            rng = np.random.default_rng(244)
            rnd = []
            for _ in range(500):
                idx = rng.choice(len(is_), q["n"], replace=False)
                rnd.append(p_pos(is_["pnl"].to_numpy()[idx], seed=int(rng.integers(1e9))))
            frac = float(np.mean(np.array(rnd) >= q["p_pos"]))
            checks = dict(oos_n=len(xo) >= 30, oos_p=bool(p_oos >= 0.995), oos_beats_base=bool(len(xo) and xo.mean() > base_oos),
                          es_replicates=bool(rep >= 0.80), random_control=bool(frac < 0.05))
            fin = dict(base=base, sub=str(sub), is_n=q["n"], is_mean=q["mean"], is_p=q["p_pos"], is_p_vs_rest=q["p_vs_rest"],
                       oos_n=int(len(xo)), oos_mean=float(xo.mean()) if len(xo) else float("nan"), base_oos_mean=base_oos,
                       oos_p=p_oos, es_p_vs_rest=rep, random_frac=frac, checks=checks, passed=all(checks.values()))
            results["finalists"].append(fin)
            print(f"  {str(sub):<60} IS n={q['n']:>4} ${q['mean']:+7.2f} P {q['p_pos']:.3f} vs-rest {q['p_vs_rest']:.3f} | "
                  f"OOS n={len(xo):>3} ${fin['oos_mean']:+7.2f} (base ${base_oos:+.2f}) P {p_oos:.3f} | ES {rep:.2f} | "
                  f"random {frac:.2f} | {'PASS' if fin['passed'] else 'fail'}", flush=True)
    passed = [f for f in results["finalists"] if f["passed"]]
    print(f"\nRESULT: {len(passed)} of {len(results['finalists'])} finalists pass every check")
    with open(os.path.join(HERE, "round244_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"Saved round244_results.json ({time.time() - t0:.0f}s)")
