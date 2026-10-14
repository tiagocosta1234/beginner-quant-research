"""DAY2K: one setup per day, 1:1, +/-2,000 USD. Pre-registration: PREREG_DAY2K.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2k --dry-run      counts, causality (truncation) test, mechanics hand check; no cell P&L
  python -m forex.self_improving.day2k.day2k --calibrate    positive control + placebo worlds (seeds 81-83)
  python -m forex.self_improving.day2k.day2k --run          the 24 cells on DEV and VAL (HOLD is never loaded here)
  python -m forex.self_improving.day2k.day2k --hold CELL    one look at 2026-01-01..2026-09-30 for ONE named cell"""
import sys, itertools, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[3]
DATA = ROOT / "mt5" / "data_mt5"
CACHE = pathlib.Path("D:/finance/si_ledgers")
PAIRS = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
         "EURUSD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
TS = (10 * 3600 + 5 * 60, 16 * 3600 + 35 * 60)     # decision times T (server clock, seconds into the day)
KS = (0.4, 0.7)
EXIT = 21 * 3600 + 55 * 60                         # forced exit bar
AM_T = 1 * 3600 + 5 * 60                           # 01:05 reference for the morning move (after the 23-01 rollover window)
SIGS = ("M5", "M1", "AM")
RISK = 2000.0
DEV_T = 2.86                                       # DEV block-t bar (round A: Bonferroni for 24 trials)
LO, DEV_HI, VAL_LO, VAL_HI = "2021-12-01", "2024-12-31", "2025-01-01", "2025-12-31"
HOLD_LO, HOLD_HI = "2026-01-01", "2026-09-30"


def d64(s):
    return int(np.datetime64(s, "D").astype(int))


def trading_days(lo, hi):
    d = np.arange(d64(lo), d64(hi) + 1)
    return d[(d + 3) % 7 < 5]                      # 1970-01-01 was a Thursday


def load(sym):
    df = pd.read_parquet(DATA / f"{sym}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "sp"])
    return {c: df[c].to_numpy() for c in df.columns}


def atr20(A, days):
    """mean daily bid high-low of the 20 previous full trading days, for each day in `days` (days since epoch); NaN when unknown"""
    t = A["t"]; di = t // 86400
    u, st = np.unique(di, return_index=True); n = np.diff(np.append(st, len(t)))
    rng = np.maximum.reduceat(A["bh"], st) - np.minimum.reduceat(A["bl"], st)
    keep = ((u + 3) % 7 < 5) & (n >= 600)
    ku = u[keep]; roll = pd.Series(rng[keep]).rolling(20, min_periods=15).mean().to_numpy()
    j = np.searchsorted(ku, days, side="left") - 1                      # last complete day strictly before each day
    return np.where(j >= 0, roll[np.clip(j, 0, len(roll) - 1)], np.nan)


def price_at(A, sec, max_gap=300):
    """bid close of the last bar whose start time is <= sec (a bar starting at sec-60 closes at sec); NaN if the gap is large"""
    t = A["t"]; i = np.searchsorted(t, sec, side="right") - 1
    ok = (i >= 0) & (sec - t[np.clip(i, 0, len(t) - 1)] <= max_gap)
    return np.where(ok, A["bc"][np.clip(i, 0, len(t) - 1)], np.nan)


def scores_for(A, days, atr):
    """S[day, T, sig] normalised by ATR20; uses bars that started at or before T-60 s of the same/earlier days only"""
    out = np.full((len(days), len(TS), len(SIGS)), np.nan)
    for ti, T in enumerate(TS):
        pT = price_at(A, days * 86400 + T - 60)
        p_m1 = np.roll(pT, 1); p_m1[0] = np.nan
        p_m5 = np.roll(pT, 5); p_m5[:5] = np.nan
        p_am = price_at(A, days * 86400 + AM_T - 60)
        out[:, ti, 0] = (pT - p_m5) / atr; out[:, ti, 1] = (pT - p_m1) / atr; out[:, ti, 2] = (pT - p_am) / atr
    return out


def outcomes_for(A, days, atr):
    """R[day, T, k, side] (side 0 long, 1 short) and resolved flag. Entry at the open of the bar starting T+60 s."""
    t = A["t"]; R = np.full((len(days), len(TS), len(KS), 2), np.nan); RES = np.zeros(R.shape, bool)
    for di, d in enumerate(days):
        if not np.isfinite(atr[di]): continue
        for ti, T in enumerate(TS):
            e_t = d * 86400 + T + 60; x_t = d * 86400 + EXIT
            i0 = np.searchsorted(t, e_t); i1 = np.searchsorted(t, x_t)
            if i0 >= len(t) or i1 >= len(t) or t[i0] != e_t or t[i1] != x_t or i1 - i0 < 30: continue
            bh, bl, ah, al = A["bh"][i0:i1], A["bl"][i0:i1], A["ah"][i0:i1], A["al"][i0:i1]
            EL, ES = A["ao"][i0], A["bo"][i0]; XL, XS = A["bo"][i1], A["ao"][i1]
            for ki, k in enumerate(KS):
                Dd = k * atr[di]
                # long: TP when the bid reaches EL+D, SL when the bid falls to EL-D (tie in one bar = loss)
                jt = np.argmax(bh >= EL + Dd) if (bh >= EL + Dd).any() else 10 ** 9
                js = np.argmax(bl <= EL - Dd) if (bl <= EL - Dd).any() else 10 ** 9
                if js <= jt and js < 10 ** 9: R[di, ti, ki, 0] = -1.0; RES[di, ti, ki, 0] = True
                elif jt < 10 ** 9: R[di, ti, ki, 0] = 1.0; RES[di, ti, ki, 0] = True
                else: R[di, ti, ki, 0] = np.clip((XL - EL) / Dd, -1, 1)
                jt = np.argmax(al <= ES - Dd) if (al <= ES - Dd).any() else 10 ** 9
                js = np.argmax(ah >= ES + Dd) if (ah >= ES + Dd).any() else 10 ** 9
                if js <= jt and js < 10 ** 9: R[di, ti, ki, 1] = -1.0; RES[di, ti, ki, 1] = True
                elif jt < 10 ** 9: R[di, ti, ki, 1] = 1.0; RES[di, ti, ki, 1] = True
                else: R[di, ti, ki, 1] = np.clip((ES - XS) / Dd, -1, 1)
    return R, RES


def build(lo, hi, tag):
    f = CACHE / f"day2k_{tag}.npz"
    days = trading_days(lo, hi)
    if f.exists():
        z = np.load(f); return days, z["R"], z["RES"], z["S"]
    R = np.full((len(days), len(PAIRS), len(TS), len(KS), 2), np.nan, np.float32); RES = np.zeros(R.shape, bool); S = np.full((len(days), len(PAIRS), len(TS), len(SIGS)), np.nan, np.float32)
    full = trading_days("2021-10-01", hi)                 # warm-up days so ATR20 / 5-day look-backs exist from the first day
    for pi, sym in enumerate(PAIRS):
        A = load(sym); atr_f = atr20(A, full); sc_f = scores_for(A, full, atr_f); r, rs = outcomes_for(A, days, atr_f[np.isin(full, days)])
        m = np.isin(full, days); S[:, pi] = sc_f[m]; R[:, pi] = r; RES[:, pi] = rs
        print(f"  built {sym}", flush=True)
    np.savez_compressed(f, R=R, RES=RES, S=S)
    return days, R, RES, S


def block_t(x, b=5):
    x = x[np.isfinite(x)]; n = len(x) // b
    if n < 10: return np.nan, np.nan
    m = x[:n * b].reshape(n, b).mean(1); return float(x.mean()), float(m.mean() / (m.std(ddof=1) / np.sqrt(n)))


def pick(R, S, sig, cont, ti, ki, rng=None, oracle=False):
    """daily R of one cell: the pair with the largest |score| (noise when rng is given), side by direction"""
    s = S[:, :, ti, sig].astype(float)
    if rng is not None: s = rng.standard_normal(s.shape) * np.isfinite(s) + np.where(np.isfinite(s), 0, np.nan)
    rl, rsh = R[:, :, ti, ki, 0], R[:, :, ti, ki, 1]
    valid = np.isfinite(s) & np.isfinite(rl) & np.isfinite(rsh)
    sc = np.where(valid, np.abs(s), -1); p = sc.argmax(1); ok = sc.max(1) >= 0
    di = np.arange(len(s)); sv = s[di, p]
    long = (sv > 0) if cont else (sv < 0)
    if oracle: long = rl[di, p] >= rsh[di, p]
    out = np.where(long, rl[di, p], rsh[di, p]); out[~ok] = np.nan
    return out


def baseline(R, ti, ki):
    return np.nanmean(R[:, :, ti, ki, :].reshape(R.shape[0], -1), axis=1)


def cells():
    return [(sg, cont, ti, ki) for sg, cont, ti, ki in itertools.product(range(3), (True, False), range(2), range(2))]


def name(c):
    sg, cont, ti, ki = c; return f"{SIGS[sg]}-{'cont' if cont else 'fade'}-T{TS[ti] // 3600:02d}{(TS[ti] % 3600) // 60:02d}-k{KS[ki]}"


def mt5_rolling(r, horizon=None):
    """sequential test attempts on a daily R series (R x 2,000 USD, counted cap 2,000/day): pass +8,000, breach at -8,000 (static floor) or a day <= -2,500"""
    r = r[np.isfinite(r)] * RISK; n = len(r); res = []
    for s in range(n):
        c = 0.0; out = "open"; bd = n - s
        for j in range(s, n):
            x = r[j]
            if x <= -2500: out = "breach"; bd = j - s + 1; break
            c += min(x, 2000.0) if x > 0 else x
            if c <= -8000: out = "breach"; bd = j - s + 1; break
            if c >= 8000: out = "pass"; bd = j - s + 1; break
        res.append((out, bd))
    o = [x for x, _ in res]; done = [x for x in o if x != "open"]
    pb = [b for x, b in res if x == "pass"]
    return dict(starts=n, pass_=o.count("pass"), breach=o.count("breach"), open_=o.count("open"), pass_rate=100 * o.count("pass") / max(1, len(done)), med_days=float(np.median(pb)) if pb else np.nan)


def evaluate(R, S, days, rng_seed=None, oracle=False, quiet=False):
    dev = days <= d64(DEV_HI); val = (days >= d64(VAL_LO)) & (days <= d64(VAL_HI)); rows = []
    rng = np.random.default_rng(rng_seed) if rng_seed is not None else None
    for c in cells():
        sg, cont, ti, ki = c; r = pick(R, S, sg, cont, ti, ki, rng, oracle); b = baseline(R, ti, ki)
        md, td = block_t(r[dev]); mv, tv = block_t(r[val]); bd = float(np.nanmean(b[dev])); bv = float(np.nanmean(b[val]))
        nv = int(np.isfinite(r[val]).sum()); s1 = bool(md > 0 and td >= DEV_T and md > bd and mv > 0 and tv >= 1.65 and nv >= 200)
        rows.append(dict(cell=name(c), n_dev=int(np.isfinite(r[dev]).sum()), dev_R=md, dev_t=td, dev_base=bd, n_val=nv, val_R=mv, val_t=tv, val_base=bv, S1=s1))
    return pd.DataFrame(rows)


def dry_run():
    days, R, RES, S = build(LO, DEV_HI, "dev")
    print("days", len(days), days[0], days[-1], "| R matrix", R.shape)
    for ti in range(2):
        v = np.isfinite(R[:, :, ti, 0, 0]); print(f"T{TS[ti]//3600:02d}{(TS[ti]%3600)//60:02d}: valid pair-days {int(v.sum())} of {v.size}; days with >= 20 pairs {int((v.sum(1)>=20).sum())}; resolved share k0.4 {RES[:,:,ti,0,:][np.isfinite(R[:,:,ti,0,:])].mean():.3f} k0.7 {RES[:,:,ti,1,:][np.isfinite(R[:,:,ti,1,:])].mean():.3f}")
    # clock check: mean spread by server hour (rollover peak at hour 0 would confirm the server clock)
    A = load("EURUSD"); h = (A["t"] % 86400) // 3600; sp = pd.Series(A["sp"]).groupby(h).mean(); print("EURUSD mean spread by server hour (pips):", (sp * 1e4).round(2).to_dict())
    # truncation test: scores and ATR recomputed from bars strictly before T equal the matrix values
    rng = np.random.default_rng(5); bad = 0; n = 0
    for _ in range(40):
        pi = int(rng.integers(len(PAIRS))); di = int(rng.integers(30, len(days))); ti = int(rng.integers(2)); A = load(PAIRS[pi]); cut = days[di] * 86400 + TS[ti]
        m = A["t"] < cut; B = {k: v[m] for k, v in A.items()}
        dd = trading_days("2021-10-01", DEV_HI); atr_t = atr20(B, dd); sc_t = scores_for(B, dd, atr_t); j = int(np.searchsorted(dd, days[di]))
        a = sc_t[j, ti]; b = S[di, pi, ti]
        n += 1; bad += int(not np.allclose(np.nan_to_num(a, nan=-99), np.nan_to_num(b.astype(float), nan=-99), atol=1e-4))
    print(f"truncation test: {n - bad}/{n} pair-days give identical scores with bars after T removed")
    # mechanics hand check: one pair-day, print the levels and the path outcome
    A = load("EURUSD"); d = int(days[400]); atr = atr20(A, np.array([d]))[0]; T = TS[0]; i0 = int(np.searchsorted(A["t"], d * 86400 + T + 60)); i1 = int(np.searchsorted(A["t"], d * 86400 + EXIT))
    EL = A["ao"][i0]; Dd = 0.4 * atr; print(f"hand check EURUSD {np.datetime64(d,'D')}: ATR20 {atr:.5f}, D {Dd:.5f}, long entry(ask) {EL:.5f} TP {EL+Dd:.5f} SL {EL-Dd:.5f}, bars {i1-i0}, max bid high {A['bh'][i0:i1].max():.5f}, min bid low {A['bl'][i0:i1].min():.5f}, matrix R {R[400, PAIRS.index('EURUSD'), 0, 0, 0]}")


def main():
    a = sys.argv[1:]
    if "--dry-run" in a: dry_run(); return
    if "--calibrate" in a:
        days, R, RES, S = build(LO, VAL_HI, "devval")
        c = evaluate(R, S, days, oracle=True); print("POSITIVE CONTROL (oracle side): mean dev R by cell:", c.dev_R.round(2).tolist())
        for seed in (81, 82, 83):
            e = evaluate(R, S, days, rng_seed=seed); print(f"placebo seed {seed}: S1 survivors {int(e.S1.sum())}, best dev t {e.dev_t.max():.2f}, best val t {e.val_t.max():.2f}, cells with dev t>=2.86: {int((e.dev_t>=2.86).sum())}")
        return
    if "--run" in a:
        days, R, RES, S = build(LO, VAL_HI, "devval"); e = evaluate(R, S, days); pd.set_option("display.width", 200)
        e.to_csv(CACHE / "DAY2K_cells.csv", index=False); print(e.round(3).to_string(index=False)); print("S1 survivors:", int(e.S1.sum()))
        dev = days <= d64(DEV_HI)
        for ti in range(2):
            for ki in range(2):
                b = baseline(R, ti, ki); print(f"baseline T{TS[ti]//3600:02d}{(TS[ti]%3600)//60:02d} k{KS[ki]}: dev {np.nanmean(b[dev]):+.4f} R, mt5 rolling {mt5_rolling(b)}")
        return
    if "--hold" in a:
        nm = a[a.index("--hold") + 1]; c = next(x for x in cells() if name(x) == nm); days, R, RES, S = build(HOLD_LO, HOLD_HI, "hold")
        r = pick(R, S, *c); m, t = block_t(r); print(nm, "HOLD mean R", m, "t", t, "n", int(np.isfinite(r).sum()), "mt5", mt5_rolling(r)); return
    print(__doc__)


if __name__ == "__main__":
    main()
