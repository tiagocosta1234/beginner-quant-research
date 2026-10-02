"""
Round 315 (2026-10-02, PRE-REGISTERED, DESCRIPTIVE -- no ledger row): how much does it matter that the TradingView / OANDA chart and the MT5 broker chart give different signals?
the trader: "how, and check how much this matters". Background (journal 2026-10-02, Check): on TradingView's own EURUSD bars the Python signal engine reproduces the Pine indicator exactly (5 of 5 setups), but on MT5 broker bars only 3 of those 5
signal bars recur (plus 5 MT5-only ones): the feeds differ by ~0.26 pip (sd) on the close, yet the 3-bar RSI / MACD divergence flips on such differences.
QUESTION: if the signal is read on an OANDA-like chart and the trade is filled at MT5 broker prices (what trading an MT5 broker account from the TradingView chart would be), how different is the 5-year result from the pure-MT5 broker backtest
(Rounds 311-314: strict signal, stop 4 ATR, target 3 x the stop, 1-minute, one position at a time; EURUSD -0.173R, XAUUSD -0.028R, US100 -0.074R a trade)?

METHOD (fixed now):
 1. Feed difference. For EURUSD, XAUUSD and US100 (the OANDA charts: EURUSD, XAUUSD, NAS100USD) take every 1-minute bar TradingView held on 2026-10-02 (about 6,400 bars, 7 days; EURUSD: the 3,344 it held) and the MT5 broker bid bars for the same minutes
    (MT5 broker file updated to 2026-10-02, UTC -> New York = -4 h). The difference series d = OANDA - MT5 broker bid is computed for open, high, low and close. Its slow part (a level offset that drifts over minutes to hours; NAS100 differs by tens of points)
    is removed with a centered 61-minute rolling median, leaving the high-frequency feed noise d_hf, which is the only part a divergence signal can feel.
 2. OANDA-like feed. The MT5 broker bid bars for the whole of Oct 2021 - Oct 2026 plus d_hf resampled by BLOCK BOOTSTRAP (blocks of 30 consecutive minutes, drawn at random from the measured series, tiled over the whole history; the ask = the perturbed bid + the real spread);
    high and low are repaired to contain the perturbed open and close.
 3. Signals and sizing from the OANDA-like feed (what the indicator on the TradingView chart would show: the strict signal, ATR spike 1.0, lookback 3, MACD histogram direction, stop = 4 x its ATR, target 3 x the stop), FILLS at the real MT5 broker prices:
    a long enters at the MT5 broker ask close of the signal minute, exits on the MT5 broker bid book (shorts reversed), stop wins a tie, hold <= 120 bars, one position at a time, FX commission $6 a lot, the real spread: identical to Round 313-314's resolver.
 4. Baseline = signals from the unperturbed MT5 broker feed (the Rounds 311-314 backtest). Draws: 8 at the measured noise scale (1.0x), 4 at 0.5x and 4 at 2.0x (a closer / a worse feed match), seeds fixed.
 REPORTED per instrument and scale: trades, net R per trade (mean and sd across draws), gross R, cost R; the share of baseline signal minutes that the OANDA-like feed also signals and the share of its signals that are baseline signals;
    the mean R of the SHARED signals vs the baseline-only vs the OANDA-only signals (does a signal that survives the perturbation do better than one that flips?).
 Not a hypothesis test and not a candidate search: no ledger rows (k stays 2018). The perturbation is a model of a feed difference measured on ONE week, so its size is an estimate; the 0.5x and 2.0x scales bracket it.
 Honest expectation (before the run): the net R per trade stays within about +-0.05R of the baseline at every scale (a signal that is nearly noise does not care which noise it reads), the share of shared signals is 40-70% at 1.0x, and
 the shared signals are not better than the flipped ones; a large improvement or deterioration of the net R would mean the signal's value depends on the feed and would be reported as such.

DATA: the three TradingView extracts are saved in futures/data/tv_oanda_1m/ (OANDA:EURUSD 6,730 bars, OANDA:XAUUSD 6,449, OANDA:NAS100USD 6,470; 2026-09-27 17:00 .. 2026-10-02 ~13:50 UTC, read from the chart's own series). The MT5 broker files are the ones updated to 2026-10-02 09:24 New York.
Measured on the common minutes before the run (no P&L read): the high-frequency feed noise (OANDA - MT5, slow offset removed) has an sd of about 0.10 dollars on gold (a typical 1-minute move is 0.29), 0.36-0.51 points on NAS100 / US100 (typical move 2.2) and 0.26 pip on EURUSD (typical 0.6),
i.e. 17-43% of a typical 1-minute move; the slow offset is +0.21 dollars on gold and +43 points on NAS100 (irrelevant to a divergence signal). Each experiment cell has 3,000-3,700 trades (standard error of the mean net R about 0.03R), so differences from the baseline below about +-0.06R are not distinguishable from noise.
"""
import os, sys, json, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import round271_one_to_one_generator as M
import round312_reversal_detector_eurusd_tweaks as R
import round313_reversal_detector_five_pairs_confirmation as R3

HERE = os.path.dirname(os.path.abspath(__file__))
TV_DIR = os.path.join(HERE, "..", "data", "tv_oanda_1m")
TV_FILES = {
    "EURUSD": os.path.join(TV_DIR, "OANDA_EURUSD_1m_20261002.csv"),
    "XAUUSD": os.path.join(TV_DIR, "OANDA_XAUUSD_1m_20261002.csv"),
    "US100.cash": os.path.join(TV_DIR, "OANDA_NAS100USD_1m_20261002.csv"),
}
FX = {"EURUSD": True, "XAUUSD": False, "US100.cash": False}
BLOCK = 30
STOPM, RRR = 4.0, 3.0
DRAWS = {1.0: 8, 0.5: 4, 2.0: 4}


def load_tv(path):
    b = pd.read_csv(path).rename(columns={"time_utc_s": "t", "open": "o", "high": "h", "low": "l", "close": "c"})
    b.index = pd.to_datetime(b["t"], unit="s") - pd.Timedelta(hours=4)            # UTC -> New York (EDT)
    return b[["o", "h", "l", "c"]]


def feed_noise(tv, mt5broker):
    j = tv.join(mt5broker[["open", "high", "low", "close"]], how="inner")
    out = {}
    for a, b_ in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close")):
        d = j[a] - j[b_]
        out[a] = (d - d.rolling(61, center=True, min_periods=15).median()).dropna().to_numpy()
    n = min(len(v) for v in out.values())
    return {k: v[:n] for k, v in out.items()}, len(j)


def perturbed_frame(df, noise, scale, rng):
    n = len(df)
    m = len(noise["c"])
    starts = rng.integers(0, max(1, m - BLOCK), size=n // BLOCK + 2)
    idx = np.concatenate([np.arange(s, s + BLOCK) for s in starts])[:n]
    o = df["open"].to_numpy() + scale * noise["o"][idx]
    c = df["close"].to_numpy() + scale * noise["c"][idx]
    h = np.maximum(df["high"].to_numpy() + scale * noise["h"][idx], np.maximum(o, c))
    l = np.minimum(df["low"].to_numpy() + scale * noise["l"][idx], np.minimum(o, c))
    sp = (df["ask_close"] - df["close"]).to_numpy()
    out = pd.DataFrame(dict(open=o, high=h, low=l, close=c, ask_open=o + sp, ask_high=h + sp, ask_low=l + sp, ask_close=c + sp), index=df.index)
    return out


def trades(Dreal, Dsig, sym):
    """Signals / ATR from Dsig, fills on Dreal. Returns signal minutes, net R, gross R, cost R of the trades taken."""
    n = len(Dreal["t"])
    s = R.base_signals(Dsig, 1.0, 3, "ALL")
    idx = np.flatnonzero(s != 0); idx = idx[idx + 1 + R.HOLD[1] < n]
    sgn = s[idx]
    Dh = dict(Dreal); Dh["atr"] = Dsig["atr"]                     # stop distance from the signal feed's ATR; prices, spreads and gaps from the real feed
    W = R.windows(Dh, idx)
    comm = R3.comm_price(sym, Dh["bc"][idx]) if FX[sym] else np.zeros(len(idx))
    ex, r, cst = R3.resolve(Dh, idx, sgn, W, STOPM, RRR, comm)
    keep = R.one_at_a_time(idx, ex)
    return idx[keep], r[keep], r[keep] + cst[keep], cst[keep], set(idx.tolist())


def selftest():
    R.selftest()
    rng = np.random.default_rng(1)
    df = pd.DataFrame(dict(open=1.1 + rng.normal(0, 1e-4, 2000), high=1.1005, low=1.0995, close=1.1 + rng.normal(0, 1e-4, 2000), ask_open=1.1001, ask_high=1.1006, ask_low=1.0996, ask_close=1.1001),
                      index=pd.date_range("2024-01-01", periods=2000, freq="min"))
    noise = {k: rng.normal(0, 3e-5, 500) for k in "ohlc"}
    p = perturbed_frame(df, noise, 1.0, rng)
    assert (p["high"] >= p[["open", "close"]].max(axis=1) - 1e-12).all() and (p["low"] <= p[["open", "close"]].min(axis=1) + 1e-12).all() and len(p) == len(df)
    z = perturbed_frame(df, noise, 0.0, rng)
    assert np.allclose(z["close"], df["close"]), "scale 0 must reproduce the feed"
    print("selftest ok (round315)")


def main():
    selftest()
    t0 = time.time()
    results = {}
    for sym in ("EURUSD", "XAUUSD", "US100.cash"):
        mt5broker = M.load(sym)
        mt5broker = mt5broker[(mt5broker.index >= "2021-10-04")]
        tv = load_tv(TV_FILES[sym])
        noise, ncommon = feed_noise(tv, mt5broker)
        pip = 1e-4 if sym == "EURUSD" else 1.0
        print(f"\n{sym}: MT5 broker to {mt5broker.index[-1]}, TradingView minutes {len(tv)}, common {ncommon}; high-frequency feed noise sd (price units): " +
              ", ".join(f"{k} {noise[k].std():.5f}" for k in "ohlc") + f"; typical 1-min move {mt5broker['close'].diff().abs().median():.5f}", flush=True)
        Dreal = R.build(mt5broker, 1); Dreal["scale"] = 1.0
        bi, br, bg, bc_, bset = trades(Dreal, Dreal, sym)
        print(f"   BASELINE (MT5 broker signals and fills): {len(bi)} trades, net {br.mean():+.3f}R, gross {bg.mean():+.3f}R, cost {bc_.mean():.3f}R, win {(br > 0).mean():.1%}")
        results[sym] = dict(noise_sd={k: float(noise[k].std()) for k in "ohlc"}, common_minutes=int(ncommon), baseline=dict(n=int(len(bi)), net_R=float(br.mean()), gross_R=float(bg.mean()), cost_R=float(bc_.mean()), win=float((br > 0).mean())), scales={})
        for scale, nd in DRAWS.items():
            rows = []
            for d in range(nd):
                rng = np.random.default_rng(1000 * int(scale * 10) + d)
                pf = perturbed_frame(mt5broker, noise, scale, rng)
                Dp = R.build(pf, 1); Dp["scale"] = 1.0
                pi, pr, pg, pc, pset = trades(Dreal, Dp, sym)
                shared = bset & pset
                # R of the signals by group, on the trades each side actually took
                base_tr = dict(zip(bi.tolist(), br.tolist())); pert_tr = dict(zip(pi.tolist(), pr.tolist()))
                r_shared = [pert_tr[i] for i in pert_tr if i in bset]
                r_pert_only = [pert_tr[i] for i in pert_tr if i not in bset]
                r_base_only = [base_tr[i] for i in base_tr if i not in pset]
                rows.append(dict(n=len(pi), net=float(pr.mean()), gross=float(pg.mean()), cost=float(pc.mean()), win=float((pr > 0).mean()),
                                 share_base_kept=len(shared) / max(1, len(bset)), share_pert_in_base=len(shared) / max(1, len(pset)),
                                 r_shared=float(np.mean(r_shared)) if r_shared else float("nan"), n_shared=len(r_shared),
                                 r_pert_only=float(np.mean(r_pert_only)) if r_pert_only else float("nan"), n_pert_only=len(r_pert_only),
                                 r_base_only=float(np.mean(r_base_only)) if r_base_only else float("nan"), n_base_only=len(r_base_only)))
            df_ = pd.DataFrame(rows)
            m = df_.mean(numeric_only=True)
            print(f"   noise x{scale}: {nd} draws | trades {m['n']:.0f} | net R per trade {m['net']:+.3f} (sd across draws {df_['net'].std():.3f}; baseline {br.mean():+.3f}) | gross {m['gross']:+.3f} | "
                  f"signals kept {m['share_base_kept']:.0%} of baseline, {m['share_pert_in_base']:.0%} of the new signals are baseline | R shared {m['r_shared']:+.3f} (n {m['n_shared']:.0f}), "
                  f"OANDA-only {m['r_pert_only']:+.3f} (n {m['n_pert_only']:.0f}), MT5-only {m['r_base_only']:+.3f} (n {m['n_base_only']:.0f})", flush=True)
            results[sym]["scales"][str(scale)] = dict(mean={k: float(v) for k, v in m.items()}, net_sd=float(df_["net"].std()), draws=rows)
    with open(os.path.join(HERE, "round315_results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print(f"\nwrote round315_results.json in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
