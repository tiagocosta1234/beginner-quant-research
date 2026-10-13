"""
Round 271 (2026-10-01, PRE-REGISTERED): is there a frequent 1:1 trade generator with a net-of-cost win rate above break-even on MT5 broker's
own bid/ask data? the trader (buying a $100K 1-Step account): "now time to find the edge, create a flawless frequent 1:1 trades generator
with a high win rate". Prior: 466 ideas, none cleared the bar; walk-forward ML on 1:1 brackets (ledger rows 137-138, 182-183, 396) was
negative on Databento NQ/gold futures. This round is new in data (MT5 CFD bid/ask, 13 instruments, 2021-10..2026-09) and in
universe (indices, gold, 6 FX pairs), not in idea class; the honest expectation is no survivor, the point is to find out cleanly.

UNIVERSE: US100, US500, US30, GER40, FRA40, UK100 (cash indices), XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF (tick-built M1
bid/ask bars, forex/data/*_M1_ticks_full.parquet; server = NY + 7 h).

DECISIONS: every closed M15 bar whose close is 03:00-15:00 NY on weekdays; features known at the close; entry at the next M1 bar.
LABELS (both sides, stop = s x ATR14 of the M15 bars with s in (1.0, 2.0); target = stop distance, i.e. 1:1): long fills at the next M1 ask
open + 1.0 x the instrument's median spread (slippage), exits on the bid; short mirrored; stop wins a same-bar tie; a stop gap-fill
at min(stop, bar open) minus 0.5 x median spread; the target is a limit; forced flat after 32 M15 bars or 16:50 NY (before the
rollover: no swap). Net R = P&L / stop distance, costs included. A WIN is net R > 0 (timeouts count by their sign).
FEATURES (26, causal): returns over 1,2,4,8,16,32,64 M15 bars and the position in the 32- and 96-bar range, ATR ratio, candle body and
wicks, RSI14, Bollinger z, efficiency ratio, streak, distance to the trading-day open and the previous day's close/high/low (all in ATR),
time of day (sin, cos), weekday, tick-volume z, spread z.
MODELS (walk-forward, retrained at each half-year start from 2023-01-01, 2-day embargo, expanding window): logistic regression (L2,
C = 0.1, standardised) and HistGradientBoosting (depth 3, 120 iterations, lr 0.06). Separate models per side and s.
SIGNAL: at a decision, side with predicted P(win) >= (training base rate for that side and s) + delta, delta in (0.06, 0.10); the larger
margin wins; one position at a time per instrument (a signal is skipped until the previous trade has exited).
CELLS: 13 instruments x 2 models x 2 s x 2 delta = 104. k = 462 + 104 = 566.
EVALUATION: IS = predictions 2023-01..2025-06, OOS = 2025-07..2026-09 (the repo's split). Per cell: trades, trades/day, win %, mean net R,
bootstrap P(mean > 0) (4,000 draws). Pooled across instruments per (model, s, delta) as well. CANDIDATE (harness rule, fixed now):
IS P(mean>0) >= 0.95 AND OOS P(mean>0) >= 1 - 0.01/566 AND OOS mean net R > 0 AND >= 150 OOS trades. Also reported: Benjamini-Hochberg
q = 0.10 over the 104 OOS one-sided p-values, and the OOS win rate against the cell's break-even win rate (1 + c)/2 where c = mean cost in R.
POWER_NOTES: a cell with 1,000 OOS trades has a win-rate standard error of 1.6 pp; a 55% net win rate would be 3 sigma. Models are
selected on nothing: all 104 cells are reported, none dropped. Slippage convention is the conservative one of Rounds 261-263.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from mt5 import clock

SYMS = ["US100.cash", "US500.cash", "US30.cash", "GER40.cash", "FRA40.cash", "UK100.cash", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY",
        "AUDUSD", "USDCAD", "USDCHF"]
S_GRID, DELTAS, MODELS = (1.0, 2.0), (0.06, 0.10), ("logit", "hgb")
H_BARS, FLAT_H, FLAT_M = 32, 16, 50
FOLDS = pd.to_datetime(["2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01", "2025-01-01", "2025-07-01", "2026-01-01", "2026-07-01", "2026-10-02"])
OOS_FROM = pd.Timestamp("2025-07-01")
K_TOTAL = 462 + len(SYMS) * len(MODELS) * len(S_GRID) * len(DELTAS)
FEATS = []


def load(sym):
    raw = pd.read_parquet(os.path.join(ROOT, "mt5", "data", f"{sym}_M1_ticks_full.parquet"))
    idx = clock.server_to_ny(raw["time"].to_numpy())
    cols = ("open", "high", "low", "close", "ask_open", "ask_high", "ask_low", "ask_close", "spread", "tick_volume")
    df = pd.DataFrame({k: raw[k].to_numpy(float) for k in cols}, index=idx)
    return df[~df.index.duplicated(keep="first")].sort_index()


def m15(df):
    g = df.resample("15min", label="left", closed="left")
    b = pd.DataFrame({"o": g["open"].first(), "h": g["high"].max(), "l": g["low"].min(), "c": g["close"].last(), "tv": g["tick_volume"].sum(),
                      "spr": g["spread"].median(), "n": g["close"].count()})
    return b[b["n"] >= 8].dropna()


def features(b):
    global FEATS
    c, h, l, o = b["c"], b["h"], b["l"], b["o"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr, atr96 = tr.rolling(14).mean(), tr.rolling(96).mean()
    f = pd.DataFrame(index=b.index)
    for n in (1, 2, 4, 8, 16, 32, 64):
        f[f"ret{n}"] = (c - c.shift(n)) / atr
    for n in (32, 96):
        lo, hi = l.rolling(n).min(), h.rolling(n).max()
        f[f"pos{n}"] = (c - lo) / (hi - lo + 1e-12)
    f["volr"] = atr / atr96
    f["body"] = (c - o) / atr
    f["upw"] = (h - np.maximum(o, c)) / atr
    f["lww"] = (np.minimum(o, c) - l) / atr
    d = c.diff()
    up, dn = d.clip(lower=0).ewm(alpha=1 / 14).mean(), (-d.clip(upper=0)).ewm(alpha=1 / 14).mean()
    f["rsi"] = 100 - 100 / (1 + up / (dn + 1e-12))
    f["bbz"] = (c - c.rolling(20).mean()) / (c.rolling(20).std() + 1e-12)
    f["er16"] = (c - c.shift(16)).abs() / (d.abs().rolling(16).sum() + 1e-12)
    sgn = np.sign(c - o)
    grp = (sgn != sgn.shift()).cumsum()
    f["streak"] = (sgn.groupby(grp).cumcount() + 1).clip(upper=6) * sgn
    dk = (b.index - pd.Timedelta(hours=17)).normalize()
    dd = pd.DataFrame({"o": o.values, "h": h.values, "l": l.values, "c": c.values, "dk": dk}, index=b.index)
    dopen = dd.groupby("dk")["o"].transform("first")
    agg = dd.groupby("dk").agg(ph=("h", "max"), pl=("l", "min"), pc=("c", "last")).shift(1)
    m = agg.reindex(dk)
    f["d_open"] = (c.values - dopen.values) / atr.values
    f["d_pc"] = (c.values - m["pc"].values) / atr.values
    f["d_ph"] = (c.values - m["ph"].values) / atr.values
    f["d_pl"] = (c.values - m["pl"].values) / atr.values
    tc = b.index + pd.Timedelta(minutes=15)
    hr = tc.hour + tc.minute / 60
    f["hsin"], f["hcos"] = np.sin(2 * np.pi * hr / 24), np.cos(2 * np.pi * hr / 24)
    f["dow"] = tc.dayofweek
    f["tvz"] = (b["tv"] - b["tv"].rolling(96).mean()) / (b["tv"].rolling(96).std() + 1)
    f["sprz"] = b["spr"] / (b["spr"].rolling(96).median() + 1e-9)
    FEATS = list(f.columns)
    return f.replace([np.inf, -np.inf], np.nan), atr


def sim(side, i0, iend, S, ms, a):
    o, h, l, c, ao, ah, al, ac = a
    if side == 1:
        fill = ao[i0] + ms
        stop, tgt = fill - S, fill + S
        hs, ht = np.flatnonzero(l[i0:iend] <= stop), np.flatnonzero(h[i0:iend] >= tgt)
    else:
        fill = o[i0] - ms
        stop, tgt = fill + S, fill - S
        hs, ht = np.flatnonzero(ah[i0:iend] >= stop), np.flatnonzero(al[i0:iend] <= tgt)
    js, jt = (hs[0] if len(hs) else 10 ** 9), (ht[0] if len(ht) else 10 ** 9)
    if js == 10 ** 9 and jt == 10 ** 9:
        j = iend - 1 - i0
        ex = (c[iend - 1] - 0.5 * ms) if side == 1 else (ac[iend - 1] + 0.5 * ms)
    elif js <= jt:
        j = js
        if side == 1:
            ex = (min(stop, o[i0 + js]) if js > 0 else stop) - 0.5 * ms
        else:
            ex = (max(stop, ao[i0 + js]) if js > 0 else stop) + 0.5 * ms
    else:
        j, ex = jt, tgt
    r = (ex - fill) / S if side == 1 else (fill - ex) / S
    return r, i0 + j


def build(sym):
    df = load(sym)
    b = m15(df)
    f, atr = features(b)
    t_ns = df.index.values.astype("datetime64[ns]").astype(np.int64)
    arr = tuple(df[k].to_numpy(float) for k in ("open", "high", "low", "close", "ask_open", "ask_high", "ask_low", "ask_close"))
    ms = float(np.median((df["ask_open"] - df["open"]).to_numpy()[(df["ask_open"] - df["open"]).to_numpy() > 0]))
    tc = b.index + pd.Timedelta(minutes=15)
    ok = (tc.hour >= 3) & (tc.hour < 15) & (tc.dayofweek < 5) & f.notna().all(axis=1).values & (atr.values > 0)
    rows = np.flatnonzero(ok)
    tcn = tc.values.astype("datetime64[ns]").astype(np.int64)
    recs = []
    for r in rows:
        i0 = int(np.searchsorted(t_ns, tcn[r]))
        if i0 >= len(t_ns) - 5 or t_ns[i0] - tcn[r] > 2 * 60 * 10 ** 9:
            continue
        day = tc[r].normalize()
        flat = (day + pd.Timedelta(hours=FLAT_H, minutes=FLAT_M)).to_datetime64().astype("datetime64[ns]").astype(np.int64)
        iend = min(i0 + H_BARS * 15, int(np.searchsorted(t_ns, flat)))
        if iend - i0 < 5:
            continue
        rec = [r, tcn[r]]
        for s in S_GRID:
            S = s * float(atr.iloc[r])
            for side in (1, -1):
                rr, ie = sim(side, i0, iend, S, ms, arr)
                rec += [rr, t_ns[min(ie, len(t_ns) - 1)]]
        recs.append(rec)
    R = np.array(recs, float)
    X = f.iloc[R[:, 0].astype(int)].to_numpy(float)
    return dict(sym=sym, X=X, t=R[:, 1].astype("int64"), R=R[:, 2:], ms=ms)


def boot_p(x, n=4000, seed=7):
    if len(x) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), (n, len(x)))
    return float(np.mean(x[idx].mean(axis=1) > 0))


def fit_predict(kind, Xtr, ytr, Xte):
    if kind == "logit":
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
        m = LogisticRegression(C=0.1, max_iter=300).fit((Xtr - mu) / sd, ytr)
        return m.predict_proba((Xte - mu) / sd)[:, 1]
    m = HistGradientBoostingClassifier(max_depth=3, max_iter=120, learning_rate=0.06, l2_regularization=1.0, min_samples_leaf=200, random_state=0)
    return m.fit(Xtr, ytr).predict_proba(Xte)[:, 1]


def run_symbol(d):
    X, t, R = d["X"], d["t"], d["R"]
    tt = pd.to_datetime(t)
    out = {}
    # columns of R: for s index si: [long R, long exit_t, short R, short exit_t]
    preds = {(m, si, sd): np.full(len(t), np.nan) for m in MODELS for si in range(2) for sd in range(2)}
    base = {(m, si, sd): np.full(len(t), np.nan) for m in MODELS for si in range(2) for sd in range(2)}
    for k in range(len(FOLDS) - 1):
        te = (tt >= FOLDS[k]) & (tt < FOLDS[k + 1])
        tr = tt < FOLDS[k] - pd.Timedelta(days=2)
        if te.sum() == 0 or tr.sum() < 3000:
            continue
        for si in range(2):
            for sd in range(2):
                y = (R[:, si * 4 + sd * 2] > 0).astype(int)
                for m in MODELS:
                    preds[(m, si, sd)][te] = fit_predict(m, X[tr], y[tr], X[te])
                    base[(m, si, sd)][te] = y[tr].mean()
    for m in MODELS:
        for si, s in enumerate(S_GRID):
            for delta in DELTAS:
                pl, ps = preds[(m, si, 0)], preds[(m, si, 1)]
                bl, bs = base[(m, si, 0)], base[(m, si, 1)]
                ml, ms_ = pl - bl - delta, ps - bs - delta
                last_exit, rec = -1, []
                for i in np.flatnonzero(~np.isnan(pl)):
                    if t[i] < last_exit:
                        continue
                    if max(ml[i], ms_[i]) < 0:
                        continue
                    sd = 0 if ml[i] >= ms_[i] else 1
                    rr, ex = R[i, si * 4 + sd * 2], R[i, si * 4 + sd * 2 + 1]
                    last_exit = int(ex)
                    rec.append((t[i], rr))
                out[(m, s, delta)] = np.array(rec, float) if rec else np.zeros((0, 2))
    return out


def stats(a, lo, hi, total_days):
    if len(a) == 0:
        return dict(n=0)
    t = pd.to_datetime(a[:, 0].astype("int64"))
    sel = a[(t >= lo) & (t < hi), 1]
    n = len(sel)
    if n == 0:
        return dict(n=0)
    return dict(n=int(n), per_day=float(n / max(total_days, 1)), win=float((sel > 0).mean()), meanR=float(sel.mean()), P=boot_p(sel))


def main():
    t0 = time.time()
    res, ms = {}, {}
    for sym in SYMS:
        d = build(sym)
        ms[sym] = d["ms"]
        print(f"{sym}: {len(d['t'])} decisions, features {len(FEATS)}, median spread {d['ms']:.5g}, built {time.time() - t0:.0f}s", flush=True)
        res[sym] = run_symbol(d)
        print(f"   models done {time.time() - t0:.0f}s", flush=True)
    IS = (pd.Timestamp("2023-01-01"), OOS_FROM)
    OS = (OOS_FROM, pd.Timestamp("2026-10-02"))
    d_is, d_os = 630, 330     # approximate trading days
    rows = []
    for sym in SYMS:
        for (m, s, delta), a in res[sym].items():
            rows.append(dict(sym=sym, model=m, s=s, delta=delta, IS=stats(a, *IS, d_is), OOS=stats(a, *OS, d_os)))
    pooled = []
    for m in MODELS:
        for s in S_GRID:
            for delta in DELTAS:
                a = np.vstack([res[sym][(m, s, delta)] for sym in SYMS if len(res[sym][(m, s, delta)])])
                pooled.append(dict(model=m, s=s, delta=delta, IS=stats(a, *IS, d_is), OOS=stats(a, *OS, d_os)))
    thr = 1 - 0.01 / K_TOTAL
    print(f"\n=== Round 271: 104 cells, k = {K_TOTAL}, candidate bar: IS P >= 0.95, OOS P >= {thr:.5f}, OOS mean R > 0, OOS n >= 150 ===")
    print(f"{'symbol':>11} {'model':>5} {'s':>3} {'d':>5} | {'IS n':>6} {'win%':>6} {'meanR':>7} {'P':>5} | {'OOS n':>6} {'n/day':>6} {'win%':>6} {'meanR':>7} {'P':>5}")
    cands = []
    for r in sorted(rows, key=lambda r: -(r["IS"].get("meanR", -9))):
        i_, o_ = r["IS"], r["OOS"]
        line = f"{r['sym']:>11} {r['model']:>5} {r['s']:>3} {r['delta']:>5} | "
        line += (f"{i_['n']:>6} {i_['win']:>6.1%} {i_['meanR']:>+7.3f} {i_['P']:>5.2f}" if i_["n"] else f"{'-':>6}") + " | "
        line += (f"{o_['n']:>6} {o_['per_day']:>6.2f} {o_['win']:>6.1%} {o_['meanR']:>+7.3f} {o_['P']:>5.2f}" if o_["n"] else f"{'-':>6}")
        print(line)
        if i_["n"] and o_["n"] >= 150 and i_.get("P", 0) >= 0.95 and o_.get("P", 0) >= thr and o_["meanR"] > 0:
            cands.append(r)
    print(f"\nCANDIDATES under the pre-registered rule: {len(cands)}")
    # Benjamini-Hochberg on OOS one-sided p = 1 - P (bootstrap; floor 1/4000)
    ps = [(max(1 - r["OOS"]["P"], 1 / 4000), r) for r in rows if r["OOS"]["n"] >= 150]
    ps.sort(key=lambda x: x[0])
    m = len(ps)
    bh = [r for i, (p, r) in enumerate(ps, 1) if p <= 0.10 * i / max(m, 1)]
    print(f"BH q = 0.10 over {m} cells with OOS n >= 150: {len(bh)} pass")
    print("\n=== Pooled across the 13 instruments ===")
    for p in pooled:
        i_, o_ = p["IS"], p["OOS"]
        print(f"{p['model']:>5} s={p['s']} d={p['delta']}: IS n {i_.get('n', 0)} win {i_.get('win', float('nan')):.1%} meanR {i_.get('meanR', float('nan')):+.3f} P {i_.get('P', float('nan')):.2f} | "
              f"OOS n {o_.get('n', 0)} win {o_.get('win', float('nan')):.1%} meanR {o_.get('meanR', float('nan')):+.3f} P {o_.get('P', float('nan')):.2f}")
    json.dump(dict(k=K_TOTAL, rows=rows, pooled=pooled, n_candidates=len(cands), bh=len(bh)), open(os.path.join(HERE, "round271_results.json"), "w"), indent=1, default=float)
    print(f"\nSaved round271_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
