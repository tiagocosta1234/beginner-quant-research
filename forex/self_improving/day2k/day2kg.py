"""DAY2K-G: strongest-trend market of the day, traded with the trend, wide 1:1 held until hit. PREREG_DAY2K_G.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2kg --dry-run | --calibrate | --run"""
import sys
import numpy as np, pandas as pd
from forex.self_improving.day2k import day2k as D

MK = D.PAIRS + ["XAUUSD", "XAGUSD", "SP", "NSDQ", "DOW", "DAX", "NIKKEI", "BRENT", "WTI", "BTCUSD", "ETHUSD"]
CLS = {m: ("fx" if m in D.PAIRS else "metal" if m.startswith("XA") else "energy" if m in ("BRENT", "WTI") else "crypto" if m.endswith("USD") and m[:3] in ("BTC", "ETH") else "index") for m in MK}
LB = (20, 60, 120); KS = (1.0, 1.5, 2.0); T = 10 * 3600 + 5 * 60; MAXD = 250 * 86400
D.DEV_T = 2.45


def sim_market(sym, days, full):
    """for each day: score (per lookback), and hold-until-hit outcomes R[k, side] with exit time and bars, entry at the 10:06 bar"""
    A = D.load(sym); t = A["t"]; atr = D.atr20(A, full); pT = D.price_at(A, full * 86400 + T - 60); m = np.isin(full, days)
    sc = np.full((len(full), len(LB)), np.nan)
    for li, l in enumerate(LB): sc[l:, li] = (pT[l:] - pT[:-l]) / atr[l:]
    spr = pd.Series(A["sp"] / np.where(np.isfinite(atr[np.clip(np.searchsorted(full, t // 86400), 0, len(full) - 1)]), atr[np.clip(np.searchsorted(full, t // 86400), 0, len(full) - 1)], np.nan)).median()
    R = np.full((len(days), len(KS), 2), np.nan); EX = np.full((len(days), len(KS), 2), 0, np.int64); idx = np.where(m)[0]
    for di, fi in enumerate(idx):
        d = int(full[fi]); a = atr[fi]
        if not np.isfinite(a): continue
        i0 = int(np.searchsorted(t, d * 86400 + T + 60))
        if i0 >= len(t) or t[i0] != d * 86400 + T + 60: continue
        j1 = int(np.searchsorted(t, d * 86400 + T + MAXD))
        for ki, k in enumerate(KS):
            for si, side in enumerate((1, -1)):
                E = A["ao"][i0] if side > 0 else A["bo"][i0]; Dd = k * a; tp = E + side * Dd; sl = E - side * Dd
                pos = i0; r = np.nan; ex = 0; step = 4000
                while pos < j1:
                    e = min(pos + step, j1)
                    hi = A["bh"][pos:e] if side > 0 else A["ah"][pos:e]; lo = A["bl"][pos:e] if side > 0 else A["al"][pos:e]
                    htp, hsl = (hi >= tp, lo <= sl) if side > 0 else (lo <= tp, hi >= sl)
                    x = int(np.argmax(htp)) if htp.any() else 10 ** 9; y = int(np.argmax(hsl)) if hsl.any() else 10 ** 9
                    if x < 10 ** 9 or y < 10 ** 9:
                        if y <= x:
                            op = A["bo"][pos + y] if side > 0 else A["ao"][pos + y]; fill = op if (side > 0 and op < sl) or (side < 0 and op > sl) else sl; r = side * (fill - E) / Dd; ex = int(t[pos + y])
                        else: r = 1.0; ex = int(t[pos + x])
                        break
                    pos = e
                R[di, ki, si] = r; EX[di, ki, si] = ex
    return sc[m], R, EX, spr


def build(lo, hi, tag):
    f = D.CACHE / f"day2kg_{tag}.npz"; days = D.trading_days(lo, hi)
    if f.exists(): z = np.load(f); return days, z["SC"], z["R"], z["EX"], z["SP"]
    full = D.trading_days("2021-01-01", hi); SC = np.full((len(days), len(MK), len(LB)), np.nan); R = np.full((len(days), len(MK), len(KS), 2), np.nan); EX = np.zeros((len(days), len(MK), len(KS), 2), np.int64); SP = np.zeros(len(MK))
    for mi, sym in enumerate(MK):
        SC[:, mi], R[:, mi], EX[:, mi], SP[mi] = sim_market(sym, days, full); print("  built", sym, flush=True)
    np.savez_compressed(f, SC=SC, R=R, EX=EX, SP=SP); return days, SC, R, EX, SP


def select(SC, SP, li, shuffle=None):
    s = SC[:, :, li].copy(); s[:, SP > 0.02] = np.nan
    if shuffle is not None: s = s[shuffle]
    a = np.where(np.isfinite(s), np.abs(s), -1); mk = a.argmax(1); ok = a.max(1) > 0
    return mk, np.where(ok, np.sign(s[np.arange(len(s)), mk]), 0).astype(int), ok


def everyday(days, SC, R, SP, li, ki, shuffle=None, oracle=False):
    mk, sd, ok = select(SC, SP, li, shuffle); di = np.arange(len(days)); si = np.where(sd > 0, 0, 1)
    r = R[di, mk, ki, si]
    if oracle: r = np.fmax(R[di, mk, ki, 0], R[di, mk, ki, 1])
    r = np.where(ok, r, np.nan); return r, mk, sd


def one_at_a_time(days, SC, R, EX, SP, li, ki, risk):
    mk, sd, ok = select(SC, SP, li); rows = []; busy = 0
    for di, d in enumerate(days):
        if not ok[di] or d * 86400 + T < busy: continue
        si = 0 if sd[di] > 0 else 1; r = R[di, mk[di], ki, si]
        if not np.isfinite(r): continue
        ex = int(EX[di, mk[di], ki, si]); rows.append((int(d), ex // 86400, r, mk[di])); busy = ex + 60
    x = pd.DataFrame(rows, columns=["entry", "exit_day", "R", "mk"]); V = pd.Series(0.0, index=days)
    g = (x.groupby("exit_day").R.sum() * risk); g = g[g.index.isin(days)]; V.loc[g.index] += g
    return x, V.to_numpy()


def mt5_cycles(V):
    return D.mt5_rolling_daily(V) if hasattr(D, "mt5_rolling_daily") else None


def rolling(V):
    n = len(V); out = []
    for s in range(n):
        c = 0.0; res = "open"; end = n - 1
        for j in range(s, n):
            if V[j] <= -2500: res = "BREACH-day"; end = j; break
            c += min(V[j], 2000.0) if V[j] > 0 else V[j]
            if c <= -8000: res = "BREACH-floor"; end = j; break
            if c >= 8000: res = "PASS"; end = j; break
        out.append((res, end - s + 1))
    return pd.DataFrame(out, columns=["out", "bd"])


def block20(x, b=20):
    x = x[np.isfinite(x)]; n = len(x) // b
    if n < 8: return np.nan, np.nan
    m = x[:n * b].reshape(n, b).mean(1); return float(x.mean()), float(m.mean() / (m.std(ddof=1) / np.sqrt(n)))


def null_p(days, R, SP, SC, li, ki, mk, sd, ok, dev, n=400, seed=0):
    """permutation null with the SAME market/side mix: the picks (market, side) are shuffled among the days that have a pick; returns the share of shuffles whose DEV mean R >= the real one"""
    rng = np.random.default_rng(seed); idx = np.where(ok)[0]; si = np.where(sd > 0, 0, 1); real = np.nanmean(R[idx, mk[idx], ki, si[idx]][dev[idx]]); cnt = 0; nm = []
    for _ in range(n):
        pm = rng.permutation(idx); r = R[idx, mk[pm], ki, si[pm]]; m = np.nanmean(r[dev[idx]]); nm.append(m); cnt += int(m >= real)
    return (cnt + 1) / (n + 1), float(np.mean(nm))


def cells(days, SC, R, SP, shuffle=None, oracle=False):
    dev = days <= D.d64(D.DEV_HI); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); rows = []
    for li, l in enumerate(LB):
        for ki, k in enumerate(KS):
            r, mk, sd = everyday(days, SC, R, SP, li, ki, shuffle, oracle); md, td = block20(r[dev]); mv, tv = block20(r[val])
            dec = r[np.isfinite(r)]; win = float(np.mean(dec[np.abs(dec) >= 0.999] > 0)) if (np.abs(dec) >= 0.999).any() else np.nan
            mk2, sd2, ok2 = select(SC, SP, li, shuffle); pv, nullm = null_p(days, R, SP, SC, li, ki, mk2, sd2, ok2, dev)
            rows.append(dict(cell=f"L{l}-k{k}", n_dev=int(np.isfinite(r[dev]).sum()), dev_R=md, dev_t=td, null_R=nullm, null_p=pv, n_val=int(np.isfinite(r[val]).sum()), val_R=mv, val_t=tv, win=win, S1=bool(md > 0 and td >= D.DEV_T and pv <= 0.0055 and mv > 0 and tv >= 1.65)))
    return pd.DataFrame(rows)


def main():
    a = sys.argv[1:]; days, SC, R, EX, SP = build(D.LO, D.VAL_HI, "devval"); pd.set_option("display.width", 220)
    keep = SP <= 0.02; print("markets kept by the spread filter:", int(keep.sum()), "of", len(MK), "| dropped:", [MK[i] for i in range(len(MK)) if not keep[i]])
    if "--dry-run" in a:
        for li, l in enumerate(LB):
            mk, sd, ok = select(SC, SP, li); print(f"L{l}: days with a pick {int(ok.sum())} | pick share by class:", {c: round(float(np.mean([CLS[MK[m]] == c for m in mk[ok]])), 2) for c in ("fx", "metal", "energy", "index", "crypto")}, "| most picked:", pd.Series([MK[m] for m in mk[ok]]).value_counts().head(4).to_dict())
        print("resolved within 250 days (k1.0/1.5/2.0):", [round(float(np.isfinite(R[:, :, ki, 0]).mean()), 3) for ki in range(3)])
        rng = np.random.default_rng(6); full = D.trading_days("2021-01-01", D.VAL_HI); bad = n = 0
        for _ in range(30):
            mi = int(rng.integers(len(MK))); di = int(rng.integers(150, len(days))); A = D.load(MK[mi]); cut = int(days[di]) * 86400 + T
            m = A["t"] < cut; B = {k: v[m] for k, v in A.items()}; atr = D.atr20(B, full); pT = D.price_at(B, full * 86400 + T - 60); j = int(np.searchsorted(full, days[di]))
            for li, l in enumerate(LB):
                s = (pT[j] - pT[j - l]) / atr[j]; n += 1; bad += int(not np.isclose(np.nan_to_num(s, nan=-99), np.nan_to_num(SC[di, mi, li], nan=-99), atol=1e-4))
        print(f"truncation test (trend score from bars before 10:05 only): {n - bad}/{n} identical"); return
    if "--calibrate" in a:
        o = cells(days, SC, R, SP, oracle=True); print("POSITIVE CONTROL (oracle side) dev R:", o.dev_R.round(2).tolist())
        for sd in (151, 152, 153):
            perm = np.random.default_rng(sd).permutation(len(days)); e = cells(days, SC, R, SP, shuffle=perm); print(f"placebo {sd} (scores from shuffled days): S1 {int(e.S1.sum())} best dev t {e.dev_t.max():.2f} best val t {e.val_t.max():.2f}")
        return
    if "--run" in a:
        e = cells(days, SC, R, SP); e.to_csv(D.CACHE / "DAY2KG_cells.csv", index=False); print(e.round(3).to_string(index=False)); print("S1 survivors:", int(e.S1.sum()))
        gi = MK.index("XAUUSD"); dev = days <= D.d64(D.DEV_HI); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI))
        for li, l in enumerate(LB):
            for ki, k in enumerate(KS):
                s = SC[:, gi, li]; r = np.where(s > 0, R[:, gi, ki, 0], R[:, gi, ki, 1]); print(f"  gold-only yardstick L{l}-k{k}: DEV {block20(r[dev])[0]:+.3f} VAL {block20(r[val])[0]:+.3f}")
        print("\nMT5 broker CYCLES, one trade at a time (picks, win share, years, worst gap, hold):")
        for li, l in enumerate(LB):
            for ki, k in enumerate(KS):
                for risk in (2000.0,):
                    x, V = one_at_a_time(days, SC, R, EX, SP, li, ki, risk); C = rolling(V); fin = C[C.out != "open"]; p = C[C.out == "PASS"]
                    yr = x.groupby(pd.to_datetime(x.entry.to_numpy().astype("datetime64[D]")).year).R.apply(lambda s: f"{100 * (s > 0).mean():.0f}%({len(s)})").to_dict()
                    cl = pd.Series([CLS[MK[m]] for m in x.mk]).value_counts(normalize=True).round(2).to_dict()
                    print(f"  L{l} k{k}: trades {len(x)} win {100 * (x.R > 0).mean():.1f}% mean {risk * x.R.mean():+.0f} | worst {risk * x.R.min():+.0f} | pass {len(p)}/{len(fin)} ({100 * len(p) / max(1, len(fin)):.0f}%) median {p.bd.median() if len(p) else float('nan'):.0f} bd | by year {yr} | classes {cl}")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
