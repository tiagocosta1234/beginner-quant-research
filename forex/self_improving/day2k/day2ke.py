"""DAY2K-E: gold, a +/-2,000 day nearly every day, side chosen with rates, gold vol, USD strength, flow calendar. PREREG_DAY2K_E.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2ke --dry-run | --calibrate | --run"""
import sys, warnings
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from forex.self_improving.day2k import day2k as D, day2kb as B, day2kd as G

warnings.filterwarnings("ignore")
MAC = "data/data_macro/"
OBJ = ((0, 0.20, "O1-T1005-k0.20"), (1, 0.15, "O2-T1635-k0.15"))   # (T index, k, name)
D.DEV_T = 2.50
USD_PAIRS = [("AUDUSD", -1), ("EURUSD", -1), ("GBPUSD", -1), ("NZDUSD", -1), ("USDCAD", 1), ("USDCHF", 1), ("USDJPY", 1)]


def fred(name, path=None):
    s = pd.read_csv(path or MAC + f"{name}.csv"); s.columns = ["date", "v"]; s["date"] = pd.to_datetime(s.date, format="mixed"); s["v"] = pd.to_numeric(s.v, errors="coerce")
    return s.dropna().set_index("date").v.sort_index()


def asof(series, days, lag_bd):
    """value of the last observation dated <= day minus lag_bd business days (and its date, for the dry-run check)"""
    cut = np.busday_offset(days.astype("datetime64[D]"), -lag_bd, roll="backward"); idx = series.index.values.astype("datetime64[D]")
    j = np.searchsorted(idx, cut, side="right") - 1; ok = j >= 0; jj = np.clip(j, 0, len(idx) - 1)
    return np.where(ok, series.values[jj], np.nan), np.where(ok, idx[jj], np.datetime64("NaT")), jj


def macro(days):
    out = {}; dates = {}
    for nm, s, lag in (("dgs2", fred("DGS2"), 2), ("dfii", fred("DFII10"), 2), ("dgs10", fred("DGS10"), 2), ("gvz", fred("gvz", MAC + "cboe/GVZ.csv"), 1), ("vix", fred("VIXCLS"), 1)):
        v, dt, j = asof(s, days, lag); out[nm] = v; dates[nm] = dt
        prev1 = s.values[np.clip(j - 1, 0, None)]; prev5 = s.values[np.clip(j - 5, 0, None)]
        out[nm + "_1"] = v - prev1 if nm not in ("gvz", "vix") else np.log(v / prev1)
        out[nm + "_5"] = v - prev5 if nm not in ("gvz", "vix") else np.log(v / prev5)
    out["be_1"] = out["dgs10_1"] - out["dfii_1"]; out["be_5"] = out["dgs10_5"] - out["dfii_5"]
    g = fred("gvz", MAC + "cboe/GVZ.csv"); v, _, j = asof(g, days, 1); out["gvz_pct"] = np.array([np.mean(g.values[max(0, k - 250):k] < g.values[k]) if k > 20 else np.nan for k in j])
    d64 = days.astype("datetime64[D]"); me = (d64.astype("datetime64[M]") + 1).astype("datetime64[D]")
    out["bd_to_me"] = np.busday_count(d64, me) - 1; ms = d64.astype("datetime64[M]").astype("datetime64[D]"); out["first_bd"] = (np.busday_count(ms, d64) == 0).astype(float)
    mon = (d64.astype("datetime64[M]").astype(int) % 12) + 1; out["qend"] = (np.isin(mon, (3, 6, 9, 12)) & (out["bd_to_me"] <= 2)).astype(float)
    return out, dates


def data():
    days, R0, RES0, S, F = G.gold()
    A = D.load("XAUUSD"); full = D.trading_days("2021-10-01", D.VAL_HI); atr = D.atr20(A, full)[np.isin(full, days)]
    keep = D.KS; D.KS = (0.15, 0.20)
    try: R, RES = D.outcomes_for(A, days, atr)                      # R[day, T, k(0.15,0.20), side]
    finally: D.KS = keep
    _, FB = B.build_feats(D.LO, D.VAL_HI, "devval"); usd = np.zeros((len(days), 2, 2))
    for p, sg in USD_PAIRS:
        pi = D.PAIRS.index(p) if p in D.PAIRS else B.D.PAIRS.index(p)
        usd[:, :, 0] += sg * FB[:, pi, :, B.FI["m1"]] / len(USD_PAIRS); usd[:, :, 1] += sg * FB[:, pi, :, B.FI["m5"]] / len(USD_PAIRS)
    mac, dates = macro(days)
    return days, R, RES, F, usd, mac, dates


FX28 = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
        "EURUSD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
MAC_COLS = ["dgs2_1", "dgs2_5", "dfii_1", "dfii_5", "be_1", "be_5", "gvz_1", "gvz_5", "gvz_pct", "vix_1", "bd_to_me", "first_bd", "qend"]
PX_COLS = ["m1", "m5", "am", "pdh", "pdl", "apos", "rr", "spr", "dow", "surp", "nhigh"]


def X_for(F, usd, mac, ti):
    cols = [F[:, 0, ti, B.FI[c]].astype(float) for c in PX_COLS] + [usd[:, ti, 0], usd[:, ti, 1]] + [mac[c] for c in MAC_COLS]
    return np.column_stack(cols)


def wf(X, rl, rs, days, kind, leak=False):
    y = (rl > rs).astype(float); y[~(np.isfinite(rl) & np.isfinite(rs))] = np.nan
    if leak: X = np.column_stack([X, np.nan_to_num(y, nan=0.5)])
    out = np.full(len(days), np.nan); edges = sorted(set([B.SCORE_START] + [int(np.datetime64(f"{yy}-{mm:02d}-01", "D").astype(int)) for yy in range(2022, 2027) for mm in (3, 6, 9, 12) if int(np.datetime64(f"{yy}-{mm:02d}-01", "D").astype(int)) > B.SCORE_START] + [int(days.max()) + 1]))
    for a, b in zip(edges[:-1], edges[1:]):
        tr = (days < a) & np.isfinite(y); te = (days >= a) & (days < b) & np.isfinite(rl) & np.isfinite(rs)
        if te.sum() == 0 or tr.sum() < 100: continue
        if kind == "HGB":
            m = HistGradientBoostingClassifier(max_depth=3, max_iter=100, learning_rate=0.06, min_samples_leaf=60, l2_regularization=1.0, random_state=0).fit(X[tr], y[tr]); p = m.predict_proba(X[te])[:, 1]
        else:
            Xt = np.nan_to_num(X[tr]); sc = StandardScaler().fit(Xt); m = LogisticRegression(C=0.1, max_iter=500).fit(sc.transform(Xt), y[tr]); p = m.predict_proba(sc.transform(np.nan_to_num(X[te])))[:, 1]
        out[np.where(te)[0]] = np.where(p >= 0.5, rl[te], rs[te])
    return out


def cells(days, R, F, usd, mac, perm=None, leak=False, seed=None, oracle=False):
    if perm is not None: R = R[perm]
    rng = np.random.default_rng(seed) if seed is not None else None
    dev = days <= D.d64(D.DEV_HI); devml = (days >= B.SCORE_START) & dev; val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); rows = []
    for ti, k, on in OBJ:
        ki = 0 if k == 0.15 else 1; rl, rs = R[:, ti, ki, 0].astype(float), R[:, ti, ki, 1].astype(float); X = X_for(F, usd, mac, ti)
        for nm in ("HGB", "LOGIT", "REAL", "USD"):
            if nm in ("HGB", "LOGIT"): r = wf(X, rl, rs, days, nm, leak); dm = devml
            else:
                s = -mac["dfii_1"] if nm == "REAL" else -usd[:, ti, 0]
                if rng is not None: s = np.where(np.isfinite(s) & (s != 0), rng.choice([-1.0, 1.0], len(s)), np.nan)
                long = s > 0
                if oracle: long = rl >= rs
                r = np.where(long, rl, rs); r[~np.isfinite(s) | (s == 0)] = np.nan; dm = dev
            b = 0.5 * (rl + rs); md, td = D.block_t(r[dm]); mv, tv = D.block_t(r[val]); nv = int(np.isfinite(r[val]).sum())
            res = r[np.abs(r) >= 0.999]; wd = float(np.mean(r[dm][np.abs(r[dm]) >= 0.999] > 0)); wv = float(np.mean(r[val][np.abs(r[val]) >= 0.999] > 0))
            rows.append(dict(cell=f"{on}-{nm}", n_dev=int(np.isfinite(r[dm]).sum()), dev_R=md, dev_t=td, dev_win=wd, dev_base=float(np.nanmean(b[dm])), n_val=nv, val_R=mv, val_t=tv, val_win=wv,
                             resolved=float(np.mean(np.abs(r[np.isfinite(r)]) >= 0.999)), S1=bool(md > 0 and td >= D.DEV_T and md > float(np.nanmean(b[dm])) and mv > 0 and tv >= 1.65 and nv >= 200)))
    return pd.DataFrame(rows)


def main():
    a = sys.argv[1:]; days, R, RES, F, usd, mac, dates = data(); pd.set_option("display.width", 230)
    if "--dry-run" in a:
        for ti, k, on in OBJ:
            ki = 0 if k == 0.15 else 1; ok = np.isfinite(R[:, ti, ki, 0]); print(on, "valid days", int(ok.sum()), "resolved share", round(float(RES[:, ti, ki, :][ok].mean()), 4))
        rng = np.random.default_rng(2)
        for di in rng.choice(len(days), 5, replace=False):
            print("day", np.datetime64(int(days[di]), "D"), "| obs used:", {k: str(v[di]) for k, v in dates.items()})
        print("coverage:", {c: round(float(np.isfinite(mac[c]).mean()), 3) for c in MAC_COLS}, "usd", round(float(np.isfinite(usd).mean()), 3)); return
    if "--calibrate" in a:
        e = cells(days, R, F, usd, mac, leak=True, oracle=True); print("POSITIVE CONTROL dev R:", e.dev_R.round(2).tolist(), flush=True)
        for s in (141, 142, 143):
            e = cells(days, R, F, usd, mac, perm=np.random.default_rng(s).permutation(len(days)), seed=s); print(f"placebo {s}: S1 {int(e.S1.sum())} best dev t {e.dev_t.max():.2f} best val t {e.val_t.max():.2f}", flush=True)
        return
    if "--run" in a:
        e = cells(days, R, F, usd, mac); e.to_csv(D.CACHE / "DAY2KE_cells.csv", index=False); print(e.round(3).to_string(index=False)); print("S1 survivors:", int(e.S1.sum()))
        dev = days <= D.d64(D.DEV_HI); val = days >= D.d64(D.VAL_LO)
        for ti, k, on in OBJ:
            ki = 0 if k == 0.15 else 1; rl, rs = R[:, ti, ki, 0].astype(float), R[:, ti, ki, 1].astype(float); s = F[:, 0, ti, B.FI["m1"]].astype(float); c24 = np.where(s > 0, rl, rs)
            for nm, r in (("always long", rl), ("24h continuation", c24)):
                print(f"yardstick {on} {nm}: DEV {np.nanmean(r[dev]):+.3f} R win {np.mean(r[dev][np.abs(r[dev])>=0.999]>0):.3f} | VAL {np.nanmean(r[val]):+.3f} R win {np.mean(r[val][np.abs(r[val])>=0.999]>0):.3f}")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
