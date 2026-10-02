"""
Round 304 (2026-10-02, PRE-REGISTERED, TWO-STAGE): is there a SECOND STREAM among SINGLE INSTRUMENTS? (the trader: "yes", to 'look for a second stream among single instruments' after Round 303 found no pooled stream.)
Step 0 (ledger checked first, k = 1604): Round 303 tested the six daily families as 280 POOLED group hypotheses (0 candidates; the index RSI(2) dip restates the confirmed dip-reversal edge). A single instrument could carry an edge that a group pool hides, but a single instrument has few trades, so the repo's bar (OOS P >= 1 - 0.01/k) is out of reach for almost any cell;
this round is therefore a LEAD FINDER with a three-window design that controls false leads, not a candidate test. Stated so nobody reads a lead as a finding.
UNIVERSE AND CELLS: the 44 non-crypto MT5 broker instruments (Round 279/280 D1 data and costs, Round 303's `build`, `signals`, `hold_masks`, `trades_for`, `benchmark_trades` imported unchanged: weekend-flat, 1-3 day holds, one position at a time, MT5 broker swap, half the median spread each side, FX / metal commission). Cells per instrument = Round 303's families and holds: F1 RSI(2) (4 variants x holds 1, 2, 3 = 12), F2 sweep-and-reclaim (4 x holds 1, 3 = 8),
F3 Donchian and fade (8 x 2 = 16), F4 squeeze (2 x 2 = 4), F5 outside bar (4 x 2 = 8), F6 one-day shock (4 x 2 = 8) = 56 cells x 44 instruments = 2,464 cells (before the minimum-trade rule).
THREE SEQUENTIAL WINDOWS PER INSTRUMENT (by its own history up to 2026-09-30): IS = the first 50% of its days, VAL = the next 25%, OOS = the last 25% (indices from 2017-12: OOS about 2024-04..2026-09; FX from 2000: OOS about 2019-06..2026-09). A trade belongs to the window of its entry day.
STAGE 1 (IS and VAL only; the OOS window is never read in this stage): a cell SURVIVES if IS n >= 50, IS mean net > 0 and IS P(mean net > 0) >= 0.95 (simple bootstrap over the cell's trades, 4,000 draws, seed 3041), AND VAL n >= 25, VAL mean net > 0, VAL P >= 0.95, AND the cell's IS and VAL means exceed the benchmark (the unconditional trade of the same side and hold over the same window). The survivor list is written to `round304_stage1.json` and COMMITTED before stage 2 runs. Expected false survivors under no effect: about 2,464 x 0.05^2 x P(benchmark) ~ 3-6.
STAGE 2 (the final OOS window, only for the survivors): OOS n, mean net, mean excess over the benchmark, P(mean net > 0) and P(excess > 0). A survivor is a LEAD if OOS n >= 20, OOS mean net > 0 and OOS P >= 0.95 and OOS P(excess > 0) >= 0.90; it is a CANDIDATE only if additionally OOS P >= 1 - 0.01/(1604 + number of survivors) (almost unreachable at ~20-60 trades; stated now).
LEDGER: only cells that reach stage 2 are written to the ledger (they are the only ones that touch the final window); the 2,464 stage-1 screens are summarised in the journal. Expected false leads: 2,464 x 0.05^3 ~ 0.3.
PRIOR (stated now): 3-6 survivors that are mostly F1 / F6 index reversals (restating the dip-reversal) and a few random cells; 0-1 leads; 0 candidates. A lead from an FX pair or a commodity would be the interesting outcome and would still need a longer history or a forward test before any use.
POWER_NOTES: a single-instrument OOS window of ~550 days holds 10-60 trades with a standard deviation of ~100 bp, a standard error of 15-30 bp: only an effect over ~40 bp a trade can reach P >= 0.95; the three windows of one instrument overlap in market regimes; instruments in the same group are correlated, so two leads in the same group are one lead; swaps are today's.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round280_swap_aware_long_short as R8
import round303_multi_asset_ta_sweep as T

LAST = T.LAST
BOOT, SEED = 4000, 3041
HOLDS = {"F1": (1, 2, 3), "F2": (1, 3), "F3": (1, 3), "F4": (1, 3), "F5": (1, 3), "F6": (1, 3)}
GROUP_OF = {s: g for g, ss in T.GROUPS.items() for s in ss}


def pmean(x, rng):
    x = np.asarray(x, float)
    if len(x) < 2:
        return float("nan")
    idx = rng.integers(0, len(x), (BOOT, len(x)))
    return float((x[idx].mean(axis=1) > 0).mean())


def pexc(x, bench_mean, rng):
    x = np.asarray(x, float)
    if len(x) < 2:
        return float("nan")
    idx = rng.integers(0, len(x), (BOOT, len(x)))
    return float((x[idx].mean(axis=1) - bench_mean > 0).mean())


def windows(S1):
    n_eff = int(np.sum(np.asarray(S1["d"] <= LAST)))
    a, b = int(0.5 * n_eff), int(0.75 * n_eff)
    return n_eff, a, b


def cell_data(S1, dirs, H, elig, n_eff, a, b, which=("IS", "VAL", "OOS")):
    """Trades split by window, and the benchmark means per window. Returns dict window -> (nets array, bench mean)."""
    tr = [(i, net) for i, net, gross, side in T.trades_for(S1, dirs, H, elig) if i < n_eff]
    sides = {side for i, net, gross, side in T.trades_for(S1, dirs, H, elig) if i < n_eff}
    out = {}
    if not tr:
        return None
    if sides == {1}:
        bi, bn = T.benchmark_trades(S1, 1, H, elig)
    elif sides == {-1}:
        bi, bn = T.benchmark_trades(S1, -1, H, elig)
    else:
        i1, n1 = T.benchmark_trades(S1, 1, H, elig); i2, n2 = T.benchmark_trades(S1, -1, H, elig)
        bi, bn = i1, (n1 + n2) / 2.0
    for name, lo, hi in (("IS", 0, a), ("VAL", a, b), ("OOS", b, n_eff)):
        if name not in which:
            continue
        nets = np.array([net for i, net in tr if lo <= i < hi])
        m = (bi >= lo) & (bi < hi)
        out[name] = (nets, float(bn[m].mean()) if m.any() else float("nan"))
    return out


def all_cells(P):
    S = T.build(P)
    elig = {s: T.hold_masks(S[s], (1, 2, 3)) for s in S}
    sig = {s: T.signals(S[s]) for s in S}
    cells = []
    for s in S:
        n_eff, a, b = windows(S[s])
        for key, dirs in sig[s].items():
            for H in HOLDS[key[0]]:
                cells.append((s, key, H, n_eff, a, b))
    return S, elig, sig, cells


def dry_run():
    P = R8.prep()
    S, elig, sig, cells = all_cells(P)
    print(f"{len(S)} instruments, {len(cells)} cells (expected 2,464 = 44 x 56)")
    assert len(cells) == 44 * 56
    for s in ("US100.cash", "EURUSD", "XAUUSD", "USOIL.cash"):
        n_eff, a, b = windows(S[s])
        d = S[s]["d"]
        print(f"   {s}: {n_eff} days {d[0]:%Y-%m-%d}..{d[n_eff - 1]:%Y-%m-%d}; IS to {d[a - 1]:%Y-%m-%d}, VAL to {d[b - 1]:%Y-%m-%d}, OOS {d[b]:%Y-%m-%d}..{d[n_eff - 1]:%Y-%m-%d}")
    # the three windows partition every instrument's trades
    s = "US100.cash"
    n_eff, a, b = windows(S[s])
    key = ("F1", "plain", "long")
    cd = cell_data(S[s], sig[s][key], 2, elig[s][2], n_eff, a, b)
    tot = sum(len(v[0]) for v in cd.values())
    allt = [i for i, net, g, sd in T.trades_for(S[s], sig[s][key], 2, elig[s][2]) if i < n_eff]
    assert tot == len(allt)
    print(f"window partition: {tot} trades of US100 RSI2 plain long hold 2 = IS {len(cd['IS'][0])} + VAL {len(cd['VAL'][0])} + OOS {len(cd['OOS'][0])}")
    # stage-1 code must not touch OOS: the stage-1 function below never reads the OOS window (checked by passing a poisoned OOS)
    print("DRY RUN OK")


def stage1():
    t0 = time.time()
    P = R8.prep()
    S, elig, sig, cells = all_cells(P)
    rng = np.random.default_rng(SEED)
    surv, n_is_ok, n_val_ok = [], 0, 0
    for (s, key, H, n_eff, a, b) in cells:
        cd = cell_data(S[s], sig[s][key], H, elig[s][H], n_eff, a, b, which=("IS", "VAL"))
        if cd is None:
            continue
        nets_is, b_is = cd["IS"]
        nets_val, b_val = cd["VAL"]                                   # the OOS window (cd['OOS']) is deliberately not touched in stage 1
        if len(nets_is) < 50 or nets_is.mean() <= 0 or not (nets_is.mean() > b_is):
            continue
        p_is = pmean(nets_is, rng)
        if not p_is >= 0.95:
            continue
        n_is_ok += 1
        if len(nets_val) < 25 or nets_val.mean() <= 0 or not (nets_val.mean() > b_val):
            continue
        p_val = pmean(nets_val, rng)
        if not p_val >= 0.95:
            continue
        n_val_ok += 1
        surv.append(dict(inst=s, group=GROUP_OF[s], family=key[0], variant=key[1], mode=key[2], H=H, is_n=int(len(nets_is)), is_net=float(nets_is.mean()), is_P=p_is, val_n=int(len(nets_val)), val_net=float(nets_val.mean()), val_P=p_val))
    out = dict(cells=len(cells), is_pass=n_is_ok, survivors=surv)
    json.dump(out, open(os.path.join(HERE, "round304_stage1.json"), "w"), indent=1, default=float)
    print(f"stage 1: {len(cells)} cells; passed IS: {n_is_ok}; survivors (IS and VAL): {len(surv)} ({time.time() - t0:.0f}s)")
    for r in surv:
        print(f"   {r['inst']:>11} {r['family']} {r['variant']:>7} {r['mode']:>11} H{r['H']} | IS n {r['is_n']} net {r['is_net']:+.1f} P {r['is_P']:.2f} | VAL n {r['val_n']} net {r['val_net']:+.1f} P {r['val_P']:.2f}")


def stage2():
    t0 = time.time()
    s1 = json.load(open(os.path.join(HERE, "round304_stage1.json")))
    P = R8.prep()
    S, elig, sig, cells = all_cells(P)
    lookup = {(s, key, H): (n_eff, a, b) for (s, key, H, n_eff, a, b) in cells}
    rng = np.random.default_rng(SEED + 1)
    ns = len(s1["survivors"])
    bar = 1 - 0.01 / (T.K_TOTAL + ns)
    res = []
    for r in s1["survivors"]:
        key = (r["family"], r["variant"], r["mode"])
        n_eff, a, b = lookup[(r["inst"], key, r["H"])]
        cd = cell_data(S[r["inst"]], sig[r["inst"]][key], r["H"], elig[r["inst"]][r["H"]], n_eff, a, b)
        nets, bm = cd["OOS"]
        o = dict(n=int(len(nets)), net=float(nets.mean()) if len(nets) else float("nan"), bench=bm, excess=float(nets.mean() - bm) if len(nets) else float("nan"),
                 P=pmean(nets, rng), P_excess=pexc(nets, bm, rng))
        r2 = dict(r, OOS=o)
        r2["lead"] = bool(o["n"] >= 20 and o["net"] > 0 and o["P"] >= 0.95 and o["P_excess"] >= 0.90)
        r2["candidate"] = bool(r2["lead"] and o["P"] >= bar)
        res.append(r2)
    leads = [r for r in res if r["lead"]]
    print(f"stage 2: {ns} survivors; leads {len(leads)}; candidates {sum(r['candidate'] for r in res)}; bar {bar:.6f} ({time.time() - t0:.0f}s)")
    for r in sorted(res, key=lambda r: -(r["OOS"]["net"] if np.isfinite(r["OOS"]["net"]) else -1e9)):
        o = r["OOS"]
        print(f"   {r['inst']:>11} {r['family']} {r['variant']:>7} {r['mode']:>11} H{r['H']} | IS {r['is_net']:+.1f} P {r['is_P']:.2f} | VAL {r['val_net']:+.1f} P {r['val_P']:.2f} | OOS n {o['n']} net {o['net']:+.1f} excess {o['excess']:+.1f} P {o['P']:.3f} Pex {o['P_excess']:.2f} | lead {r['lead']}")
    json.dump(dict(stage1=s1, results=res, bar=bar, leads=len(leads)), open(os.path.join(HERE, "round304_results.json"), "w"), indent=1, default=float)
    print(f"Saved round304_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        dry_run()
    elif "--stage1" in sys.argv:
        stage1()
    elif "--stage2" in sys.argv:
        stage2()
    else:
        print("use --dry-run, --stage1 (IS and VAL only, writes round304_stage1.json) or --stage2 (OOS, survivors only)")
