"""Can any strategy in hand be added to the live gold pair as a second leg? (the trader: "lock in and make it work", 2026-10-14)
Pair = ManualSDB + XAU5 at x2.0 (MT5 broker real-tick pool, 2025-10-01..2026-09-30, guarded daily results V / in-day low B / in-day high Hi from clean_boot_lib).
Candidate legs: UT Bot and swing-level S/R trades from this week's engines, each trade risking RISK usd, daily P&L by exit day (closed trades); the joint bootstrap keeps the same-day pairing (so the correlation is kept).
Sim: from counted profit -374.30, 12 trading days to 30 Oct, MT5 broker rules (counted day capped at +2,000, breach = in-day low <= -2,500 or equity <= 92,000, counted-equity lock 8,100). Gate (from the clean add-on work): correlation <= 0.3 and uplift >= +1.0 pt of P(pass by 30 Oct) with <= +1.0 pt more breach.
python -m forex.ea_research.addon_leg_test"""
import sys, numpy as np, pandas as pd
sys.argv = [sys.argv[0]]
from forex.ea_research import clean_boot_lib as CL, clean_bootstrap as BS
from forex.ea_research import utbot as U
from forex.ea_research import sr_test as S

A, CAPD, TARGET, C0, H = 100000.0, 2000.0, 8000.0, -374.30, 12
RISK = 500.0
pair = CL.series("MT5", 2.0)
days = pair["days"]
d0, d1 = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-10-02")
T0, T1 = d0.timestamp(), d1.timestamp()
VAR = {"base": (1.0, False), "k2": (2.0, False), "k3": (3.0, False), "ha": (1.0, True)}
cache = {}


def m1(sym):
    if sym not in cache:
        d = pd.read_parquet(U.DATA + f"{sym}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t").drop_duplicates("t")
        d = d[(d.t < T1) & (d.bo > 0) & (d.ao >= d.bo)]
        x = d[["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]].copy()
        x["mo"], x["mh"], x["ml"], x["mc"] = (d.bo + d.ao) / 2, (d.bh + d.ah) / 2, (d.bl + d.al) / 2, (d.bc + d.ac) / 2
        cache[sym] = x
    return cache[sym]


def daily_ut(sym, tf, var):
    b = U.bars(m1(sym)[["t", "bo", "ao", "mo", "mh", "ml", "mc"]], U.TFS[tf])
    key, ha = VAR[var]
    src = ((b.mo + b.mh + b.ml + b.mc) / 4).to_numpy() if ha else b.mc.to_numpy()
    cl = b.mc.to_numpy(); cp = np.r_[cl[0], cl[:-1]]
    tr = np.maximum.reduce([b.mh.to_numpy() - b.ml.to_numpy(), np.abs(b.mh.to_numpy() - cp), np.abs(b.ml.to_numpy() - cp)])
    atr = pd.Series(tr).ewm(alpha=1 / U.ATRP, adjust=False).mean().to_numpy()
    sg = U.signals(b, key, ha)
    t, bo, ao = b.t.to_numpy(), b.bo.to_numpy(), b.ao.to_numpy(); nxt = U.allowed_next(t)
    idx = np.nonzero(sg)[0]; ex = nxt[np.minimum(idx + 1, len(t))]; sd = sg[idx]; keep = ex < len(t); ex, sd, idx = ex[keep], sd[keep], idx[keep]
    last = np.r_[ex[1:] != ex[:-1], True]; e, s, si = ex[last], sd[last], idx[last]
    chg = np.r_[True, s[1:] != s[:-1]]; e, s, si = e[chg], s[chg], si[chg]
    ent = np.where(s[:-1] > 0, ao[e[:-1]], bo[e[:-1]]); ext = np.where(s[:-1] > 0, bo[e[1:]], ao[e[1:]])
    ret = np.where(s[:-1] > 0, ext / ent - 1, ent / ext - 1); rf = key * atr[si[:-1]] / cl[si[:-1]]
    te, tx = t[e[:-1]], t[e[1:]]
    m = (te >= T0) & (tx < T1) & (rf > 0)
    return pd.Series(RISK * ret[m] / rf[m], index=(tx[m] // 86400).astype(int)).groupby(level=0).sum()


def daily_sr(sym, tf, mode, s_):
    b = S.bars(m1(sym), S.TFS[tf])
    sig, lev, atr = S.make_signals(b)
    tx, r = S.simulate(b, sig[mode, s_], lev[mode, s_], atr)
    m = (tx >= T0) & (tx < T1)
    return pd.Series(RISK * r[m], index=(tx[m] // 86400).astype(int)).groupby(level=0).sum()


CANDS = {"UT XAUUSD H4 K3": lambda: daily_ut("XAUUSD", "H4", "k3"), "UT XAUUSD H2 default": lambda: daily_ut("XAUUSD", "H2", "base"),
         "UT XAUUSD H4 HA": lambda: daily_ut("XAUUSD", "H4", "ha"), "UT NSDQ H2 default": lambda: daily_ut("NSDQ", "H2", "base"),
         "UT SP H2 default": lambda: daily_ut("SP", "H2", "base"), "UT NIKKEI H4 K3": lambda: daily_ut("NIKKEI", "H4", "k3"),
         "UT BTCUSD H4 K3": lambda: daily_ut("BTCUSD", "H4", "k3"), "UT USDJPY H1 default": lambda: daily_ut("USDJPY", "H1", "base"),
         "SR NSDQ H1 breakout s2": lambda: daily_sr("NSDQ", "H1", 1, 1), "SR XAUUSD H4 breakout s2": lambda: daily_sr("XAUUSD", "H4", 1, 1),
         "SR SP H4 breakout s2": lambda: daily_sr("SP", "H4", 1, 1), "SR USDJPY H2 breakout s2": lambda: daily_sr("USDJPY", "H2", 1, 1)}
rng = np.random.default_rng(3)
n = len(days)
idx = BS.stationary_idx(n, 20000, H)
V, B, Hi = pair["V"], pair["B"], pair["Hi"]


def sim(L, k):
    Vc, Bc, Hc = V + k * L, B + np.minimum(k * L, 0), Hi + np.maximum(k * L, 0)
    paths = idx.shape[0]; cnt = np.full(paths, C0); st = np.zeros(paths, np.int8)
    for j in range(H):
        v, b, h = Vc[idx[:, j]], Bc[idx[:, j]], Hc[idx[:, j]]
        act = st == 0
        br = act & ((b <= -0.025 * A) | (A + cnt + b <= 0.92 * A)); st = np.where(br, 2, st); act = st == 0
        lk = act & (cnt + np.minimum(h, CAPD) >= 8100.0); st = np.where(lk, 1, st); act = st == 0
        cnt = np.where(act, cnt + np.where(v > 0, np.minimum(v, CAPD), v), cnt)
        ps = act & (cnt >= TARGET); st = np.where(ps, 1, st)
    return (st == 1).mean() * 100, (st == 2).mean() * 100


p0, b0 = sim(np.zeros(n), 0)
print(f"pair alone (x2.0, MT5 12M pool, from counted -374, 12 days): pass by 30 Oct {p0:.1f}%, breach {b0:.1f}% | pair mean day {V.mean():+.0f} sd {V.std():.0f}")
print(f"{'leg':26s}{'mean/day':>9s}{'sd':>7s}{'corr':>6s} | uplift in pass pts (breach pts) at k=0.5 / 1 / 2 | gate")
for name, f in CANDS.items():
    s = f(); L = np.array([s.get(int(d), 0.0) for d in days])
    corr = np.corrcoef(V, L)[0, 1] if L.std() > 0 else np.nan
    res = [sim(L, k) for k in (0.5, 1.0, 2.0)]
    ok = abs(corr) <= 0.3 and any((p - p0 >= 1.0) and (b - b0 <= 1.0) for p, b in res)
    print(f"{name:26s}{L.mean():9.0f}{L.std():7.0f}{corr:6.2f} | " + " / ".join(f"{p - p0:+.1f} ({b - b0:+.1f})" for p, b in res) + f" | {'PASS' if ok else '-'}")
