"""
Round 283 (2026-10-01, PRE-REGISTERED): SPREAD REVERSION between near-identical index CFDs (idea 2 of the brainstorm the trader approved).
Hypothesis: two index CFDs of the same region (US500/US100/US30; GER40/FRA40/UK100) share most of their return, so their log price ratio should revert
after a short-horizon dislocation; dollar-neutral trades are market-neutral, the swap does not matter (flat inside one regional session), and the costs are
tiny index spreads. Prior (stated now): the ratio of two indices has a stochastic relative drift (tech vs industrials, German vs French sectors), so on hours-long
horizons it behaves much like a random walk; whatever mean reversion exists at minutes is microstructure/quote noise that the real bid/ask will mostly eat. The
honest expectation is no survivor. COMPLIANCE NOTE: MT5 broker forbids strategies that exploit price display errors or delayed updates; this test trades 5-minute
z-score deviations with holds of 1-3 hours, not tick-level quote lag, but any positive result would need to be re-read against that rule before use. WTI/Brent is NOT
testable here (no intraday oil data locally).

DATA: MT5 M1 bars from ticks (bid and ask OHLC, server = NY + 7 h) of US100, US500, US30, GER40, FRA40, UK100, resampled to 5-minute bars (a bar needs >= 4 of 5
minutes in BOTH legs; mid = (bid close + ask close) / 2).
SPREAD: s_t = ln(mid_A) - ln(mid_B) per pair. z_t = (s_t - mean of s over the 78 PREVIOUS 5-minute bars) / SD of s over those 78 bars (needs >= 60). 78 bars = one US cash
session; no parameter is tuned.
PAIRS (6): US500/US100, US500/US30, US100/US30, GER40/FRA40, GER40/UK100, FRA40/UK100. WINDOWS (NY): US pairs 10:00-15:00 entries, flat by 15:55; EU pairs 04:00-10:30 entries,
flat by 11:25 (the regional cash sessions; no overnight, no swap, no rollover).
RULES: when z_t >= +Zin the spread is rich: short A, long B; when z_t <= -Zin: long A, short B (equal notional per leg). Decision at the close of the 5-minute bar t, entry at the OPEN
of bar t+1 (long legs at the ask, short legs at the bid). EXIT (decision at a bar close, filled at the next bar's open, longs sold at the bid, shorts covered at the ask): |z| <= 0.5
(reverted), OR |z| >= Zin + 2 (stop), OR H bars held, OR the forced-flat bar. One position per pair at a time; no entry on the bar after an exit.
Net bps = pair P&L / one leg's notional x 10,000 (both legs paid at the real bid/ask; the measured demo costs: fills at the quote, no added slippage, index commission 0).
CELLS: 6 pairs x Zin (2, 3) x H (12, 36 bars = 1 h, 3 h) = 24; ledger k = 822 + 24 = 846. IS = 2022-01-01..2024-06-30, OOS = 2024-07-01..2026-09-30. Per cell: trades, win rate, mean net
bps, mean cost bps (round-trip, from the gross-mid difference), bootstrap P(mean > 0) (4,000 draws). Pooled per (Zin, H): the daily mean over the six pairs, day bootstrap, annualised Sharpe.
CANDIDATE (the repo's rule, fixed now): IS P >= 0.95 AND OOS P >= 1 - 0.01/846 AND OOS mean net bps > 0 AND OOS trades >= 150; also Benjamini-Hochberg q = 0.10 over the OOS p-values
(cells with n >= 150). DIAGNOSTIC (reported, not a test): the autocorrelation of 5-minute z-score changes at lags 1 and 12, the share of entries that reach |z| <= 0.5 before the
other exits, and the mean gross (mid-to-mid) bps per trade.
PLACEBO (dry-run): random pair side with the same exits must average about minus the cost.
DRY-RUN DISCLOSURE: the dry-run printed the FULL-SAMPLE (IS + OOS) result of one cell (Zin 2, H 12) per pair: gross (mid-to-mid) mean between -0.5 and +0.05 bps, net -1.0 to -2.8 bps, i.e. net =
minus the cost; z-change autocorrelation at lag 1 was -0.09 to -0.15 and ~0 at lag 12. Nothing in the rules, the grid or the bar was changed after seeing it.
POWER_NOTES: pair trades move 5-30 bps; a few hundred trades per cell give standard errors of 1-2 bps against a 2-5 bps round-trip cost of two legs.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round271_one_to_one_generator as M

PAIRS = [("US500.cash", "US100.cash", "US"), ("US500.cash", "US30.cash", "US"), ("US100.cash", "US30.cash", "US"),
         ("GER40.cash", "FRA40.cash", "EU"), ("GER40.cash", "UK100.cash", "EU"), ("FRA40.cash", "UK100.cash", "EU")]
WIN = {"US": ((10, 0), (15, 0), (15, 55)), "EU": ((4, 0), (10, 30), (11, 25))}      # entry from, entry to, forced-flat bar start (NY)
ZIN, HS, ZOUT, LB = (2.0, 3.0), (12, 36), 0.5, 78
IS_FROM, OOS_FROM, LAST = pd.Timestamp("2022-01-01"), pd.Timestamp("2024-07-01"), pd.Timestamp("2026-09-30")
K_TOTAL = 822 + len(PAIRS) * len(ZIN) * len(HS)


def bars5(sym):
    df = M.load(sym)
    g = df.resample("5min", label="left", closed="left")
    b = pd.DataFrame({"bo": g["open"].first(), "bc": g["close"].last(), "ao": g["ask_open"].first(), "ac": g["ask_close"].last(), "n": g["close"].count()})
    return b[b["n"] >= 4].dropna()


def pair_frame(a, b, B):
    x = pd.DataFrame({"a_bo": B[a]["bo"], "a_ao": B[a]["ao"], "a_mid": (B[a]["bc"] + B[a]["ac"]) / 2, "b_bo": B[b]["bo"], "b_ao": B[b]["ao"], "b_mid": (B[b]["bc"] + B[b]["ac"]) / 2}).dropna()
    s = np.log(x["a_mid"]) - np.log(x["b_mid"])
    prior = s.shift(1)
    mu, sd = prior.rolling(LB, min_periods=60).mean(), prior.rolling(LB, min_periods=60).std()
    x["z"] = (s - mu) / sd
    return x.dropna()


def run_pair(x, region, zin, H, rng=None):
    (eh, em), (xh, xm), (fh, fm) = WIN[region]
    t = x.index
    hm = t.hour * 60 + t.minute
    lo, hi, ff = eh * 60 + em, xh * 60 + xm, fh * 60 + fm
    z = x["z"].values
    a_bo, a_ao, b_bo, b_ao = x["a_bo"].values, x["a_ao"].values, x["b_bo"].values, x["b_ao"].values
    n = len(x)
    out = []
    i = 0
    day = np.asarray(t.normalize())
    while i < n - 2:
        # entry decision at bar i close, fill at the open of bar i+1 (same day, contiguous bar)
        if lo <= hm[i] <= hi and abs(z[i]) >= zin and day[i + 1] == day[i] and (t[i + 1] - t[i]) == pd.Timedelta(minutes=5):
            side = -1 if z[i] > 0 else 1                       # +1: long A short B (spread cheap); -1: short A long B (spread rich)
            if rng is not None:
                side = 1 if rng.random() < 0.5 else -1
            j0 = i + 1
            if side > 0:
                ent_a, ent_b = a_ao[j0], b_bo[j0]               # long A at ask, short B at bid
            else:
                ent_a, ent_b = a_bo[j0], b_ao[j0]
            k = j0
            reason = "time"
            while True:
                dec = k                                          # decision at the close of bar k
                if k + 1 >= n or day[k + 1] != day[k] or (t[k + 1] - t[k]) != pd.Timedelta(minutes=5):
                    reason = "gap"; break                         # no contiguous next bar to fill at: the trade is discarded (not counted)
                held = k - j0 + 1
                if (side > 0 and z[k] >= -ZOUT) or (side < 0 and z[k] <= ZOUT):
                    reason = "reverted"; break
                if abs(z[k]) >= zin + 2.0 and np.sign(z[k]) == -side:
                    reason = "stop"; break
                if held >= H:
                    reason = "time"; break
                if hm[k] >= ff - 5:
                    reason = "flat"; break
                k += 1
            if reason == "gap":
                i = k + 1
                continue
            j1 = k + 1
            if side > 0:
                ex_a, ex_b = a_bo[j1], b_ao[j1]                 # sell A at bid, cover B at ask
                pnl = (ex_a / ent_a - 1.0) + (1.0 - ex_b / ent_b) * 1.0
                gross = (x["a_mid"].values[j1] / x["a_mid"].values[j0] - 1.0) - (x["b_mid"].values[j1] / x["b_mid"].values[j0] - 1.0)
            else:
                ex_a, ex_b = a_ao[j1], b_bo[j1]                 # cover A at ask, sell B at bid
                pnl = (1.0 - ex_a / ent_a) + (ex_b / ent_b - 1.0)
                gross = -(x["a_mid"].values[j1] / x["a_mid"].values[j0] - 1.0) + (x["b_mid"].values[j1] / x["b_mid"].values[j0] - 1.0)
            out.append((t[j0], pnl * 1e4, gross * 1e4, reason))
            i = j1 + 1
        else:
            i += 1
    return pd.DataFrame(out, columns=["date", "net", "gross", "why"])


def pstat(x, lo, hi):
    y = x[(x["date"] >= lo) & (x["date"] <= hi)]
    if len(y) < 5:
        return dict(n=int(len(y)), mean=float("nan"), P=float("nan"), win=float("nan"), cost=float("nan"), rev=float("nan"))
    return dict(n=int(len(y)), mean=float(y["net"].mean()), P=M.boot_p(y["net"].values), win=float((y["net"] > 0).mean()), cost=float((y["gross"] - y["net"]).mean()),
                rev=float((y["why"] == "reverted").mean()))


def pooled(parts, lo, hi):
    d = pd.concat([p.assign(day=p["date"].dt.normalize())[["day", "net"]] for p in parts if not p.empty])
    d = d[(d["day"] >= lo) & (d["day"] <= hi)].groupby("day")["net"].mean()
    if len(d) < 20:
        return dict(n=int(len(d)), mean=float("nan"), P=float("nan"), sharpe=float("nan"))
    return dict(n=int(len(d)), mean=float(d.mean()), P=M.boot_p(d.values), sharpe=float(d.mean() / d.std() * np.sqrt(252)))


def bh(ps, q=0.10):
    p = np.array(ps, float); o = np.argsort(p); m = len(p); ok = np.zeros(m, bool); thr = -1
    for r, i in enumerate(o, 1):
        if p[i] <= q * r / m:
            thr = r
    if thr > 0:
        ok[o[:thr]] = True
    return ok


def load_all():
    syms = sorted({s for a, b, _ in PAIRS for s in (a, b)})
    B = {s: bars5(s) for s in syms}
    return {(a, b): pair_frame(a, b, B) for a, b, _ in PAIRS}


def dry_run():
    t0 = time.time()
    F = load_all()
    print(f"built pair frames ({time.time() - t0:.0f}s)")
    rng = np.random.default_rng(5)
    for a, b, reg in PAIRS:
        x = F[(a, b)]
        zc = x["z"].diff()
        ac1, ac12 = zc.autocorr(1), zc.autocorr(12)
        tr = run_pair(x, reg, 2.0, 12)
        pl = run_pair(x, reg, 2.0, 12, rng)
        print(f"{a[:6]}/{b[:6]}: {len(x)} bars, z-change autocorr lag1 {ac1:+.3f} lag12 {ac12:+.3f}; Zin 2 H 12: {len(tr)} trades mean {tr['net'].mean():+.2f} bps gross {tr['gross'].mean():+.2f}; "
              f"placebo (random side) {len(pl)} trades mean {pl['net'].mean():+.2f} (cost {(pl['gross'] - pl['net']).mean():.2f}); exits {tr['why'].value_counts().to_dict()}")
    # causality: z at bar i uses only bars <= i (the mean/SD are over shift(1) bars and s_t itself is known at the close of bar t)
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    F = load_all()
    rows, pool = [], []
    cache = {}
    for zin in ZIN:
        for H in HS:
            parts = []
            for a, b, reg in PAIRS:
                tr = run_pair(F[(a, b)], reg, zin, H)
                tr = tr[(tr["date"] >= IS_FROM) & (tr["date"] <= LAST + pd.Timedelta(days=1))]
                parts.append(tr)
                rows.append(dict(a=a, b=b, zin=zin, H=H, IS=pstat(tr, IS_FROM, OOS_FROM - pd.Timedelta(days=1)), OOS=pstat(tr, OOS_FROM, LAST + pd.Timedelta(days=1))))
            pool.append(dict(zin=zin, H=H, IS=pooled(parts, IS_FROM, OOS_FROM - pd.Timedelta(days=1)), OOS=pooled(parts, OOS_FROM, LAST)))
    print(f"{'pair':>14} {'Zin':>3} {'H':>3} | {'IS n':>5} {'mean':>6} {'P':>5} | {'OOS n':>5} {'mean':>6} {'win':>5} {'cost':>5} {'rev':>5} {'P':>5}")
    for r in rows:
        i, o = r["IS"], r["OOS"]
        print(f"{r['a'][:6] + '/' + r['b'][:6]:>14} {r['zin']:>3.0f} {r['H']:>3} | {i['n']:>5} {i['mean']:>+6.2f} {i['P']:>5.2f} | {o['n']:>5} {o['mean']:>+6.2f} {o['win']:>5.1%} {o['cost']:>5.2f} {o['rev']:>5.0%} {o['P']:>5.2f}")
    cand = [r for r in rows if r["IS"]["P"] >= 0.95 and r["OOS"]["P"] >= 1 - 0.01 / K_TOTAL and r["OOS"]["mean"] > 0 and r["OOS"]["n"] >= 150]
    elig = [r for r in rows if r["OOS"]["n"] >= 150]
    ok = bh([1 - r["OOS"]["P"] for r in elig], 0.10)
    print(f"\nCANDIDATES (IS P >= 0.95, OOS P >= {1 - 0.01 / K_TOTAL:.6f}, OOS mean > 0, n >= 150): {len(cand)} of {len(rows)}; Benjamini-Hochberg q=0.10 over {len(elig)} cells: {int(ok.sum())}")
    print("\nPooled (daily mean over the six pairs):")
    for p in pool:
        i, o = p["IS"], p["OOS"]
        print(f"  Zin {p['zin']:.0f} H {p['H']:>2}: IS {i['n']} days mean {i['mean']:+.2f} bps (P {i['P']:.2f}) | OOS {o['n']} days mean {o['mean']:+.2f} bps (P {o['P']:.2f}, Sharpe {o['sharpe']:+.2f})")
    allm = np.array([r["OOS"]["mean"] for r in rows if np.isfinite(r["OOS"]["mean"])])
    print(f"OOS mean net bps over all {len(allm)} cells: mean {allm.mean():+.2f}, positive in {np.mean(allm > 0):.0%}")
    json.dump(dict(rows=rows, pooled=pool, n_candidates=len(cand), n_bh=int(ok.sum()), k_total=K_TOTAL), open(os.path.join(HERE, "round283_results.json"), "w"), indent=1, default=float)
    print(f"Saved round283_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
