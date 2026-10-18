"""NOV30: the maximum chance of passing by 30 Nov 2026 with the gold EA pair, ManualDip and the USDJPY London breakout, from the
live state (95,472.14, counted -4,527.86). Pre-registration: forex/ea_research/PREREG_NOV30.md. Machinery of pair_from_today.py
(combo_grid + pass70). The pair and dip legs need the main PC (D:); the USDJPY leg runs anywhere.
   python -m forex.ea_research.nov30 [--start 2026-10-19] [--uj-only]"""
import argparse, itertools
import numpy as np, pandas as pd

C0_LIVE, C0_REF = -4527.86, -2291.92
GUARD, HAIRCUT = 1500.0, 0.06
PAIR_M, DIP_R, UJ_R = (0.0, 1.0, 1.2, 1.5, 1.8, 2.0), (0, 500, 1000), (0, 150, 250, 500)


def uj_days(risk, hc=HAIRCUT):
    """USDJPY London breakout per server day: V = (R - haircut) x risk, B = min(V, -risk), Hi = max(V, 0)."""
    from forex.ea_research.uj_conf import trades
    T, _, _ = trades()
    d = ((T.day - pd.Timestamp("1970-01-01")).dt.days).astype(int)
    V = (T.R.to_numpy() - hc) * risk
    X = pd.DataFrame({"V": V, "B": np.minimum(V, -risk), "Hi": np.maximum(V, 0.0)}, index=d.to_numpy())
    return X.groupby(level=0).sum()


def add_leg(S, D, g=GUARD):
    """combo_grid.add_dip pattern: add a leg's day rows; the guard cuts a combined day below -(g + 100)."""
    X = D.reindex(S["days"]).fillna(0.0); V, B, Hi = S["V"] + X.V.values, S["B"] + X.B.values, S["Hi"] + X.Hi.values
    floor = -(g + 100.0); cut = B < floor
    return dict(V=np.where(cut, np.minimum(S["V"], floor), V), B=np.where(cut, np.minimum(S["B"], floor), B), Hi=Hi, days=S["days"])


def shift_edge(S, frac):
    """keep frac of the pair's edge: every day shifted down by (1 - frac) x the mean pair day (pass70 shift semantics)."""
    d = (1 - frac) * float(np.mean(S["V"]))
    return dict(V=S["V"] - d, B=S["B"] - d, Hi=np.maximum(S["Hi"] - d, 0.0), days=S["days"])


def horizons(start):
    s = np.datetime64(start)
    return {"30 Nov": int(np.busday_count(s, np.datetime64("2026-12-01"))), "22 Dec": int(np.busday_count(s, np.datetime64("2026-12-23")))}


def run(P, series_by_pool, H):
    res = {pool: P.simulate([S] * len(P.MULTS), P.I12, H) for pool, S in series_by_pool.items()}
    return res


def summarise(res, n):
    pp = {p: 100 * np.mean((r[0] == 1) & (r[1] < n)) for p, r in res.items()}; bb = {p: 100 * np.mean((r[0] == 2) & (r[1] < n)) for p, r in res.items()}
    return np.mean(list(pp.values())), np.mean(list(bb.values())), pp, bb


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--start", default="2026-10-19"); ap.add_argument("--uj-only", action="store_true")
    a = ap.parse_args(); HZ = horizons(a.start); H = max(HZ.values()) + 1
    if a.uj_only:                                                         # second PC check of the USDJPY leg alone
        for risk in UJ_R[1:]:
            X = uj_days(risk); print(f"USDJPY ${risk}: {len(X)} trade days, mean day {X.V.mean():+.1f} USD, worst {X.V.min():,.0f}, best {X.V.max():,.0f}")
        return
    from forex.ea_research import combo_grid as cg, pass70 as P
    from forex.ea_research.event_macro import server_s
    cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv")
    cg.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))   # news flat on CPI only (11-Oct plan)
    print("horizons in business days from", a.start, HZ)
    # ---- engine check: reproduce PAIR_FROM_TODAY (x1.5 + ManualDip 500 from 97,708 on Fri 16 Oct: 18.0% by 30 Nov, 36.5% by 22 Dec, MIX)
    P.C0 = C0_REF; HR = horizons("2026-10-16"); dip500 = cg.dip_days(500)
    ref = {pool: cg.add_dip(cg.pair_series(pool, 1.5, 1.5, GUARD), dip500, GUARD) for pool in ("MT5", "FT")}
    r = run(P, ref, max(HR.values()) + 1)
    print("engine check vs PAIR_FROM_TODAY (expected 18.0% / 36.5%): " + ", ".join(f"{k} pass {summarise(r, n)[0]:.1f}% breach {summarise(r, n)[1]:.1f}%" for k, n in HR.items()))
    # ---- the grid from the live state
    P.C0 = C0_LIVE
    pair = {(pool, m): cg.pair_series(pool, m, m, GUARD) for pool in ("MT5", "FT") for m in PAIR_M}
    dips = {r_: (cg.dip_days(r_) if r_ else None) for r_ in DIP_R}
    ujs = {r_: (uj_days(r_) if r_ else None) for r_ in UJ_R}
    rows = []
    for m, dr, ur in itertools.product(PAIR_M, DIP_R, UJ_R):
        if m == 0 and dr == 0 and ur == 0:
            continue
        S = {}
        for pool in ("MT5", "FT"):
            X = pair[(pool, m)]
            if dr:
                X = add_leg(X, dips[dr])
            if ur:
                X = add_leg(X, ujs[ur])
            S[pool] = X
        res = run(P, S, H)
        p30, b30, pp, bb = summarise(res, HZ["30 Nov"]); p22, b22, _, _ = summarise(res, HZ["22 Dec"])
        worst = min(float(np.min(S[p]["B"])) for p in S)
        rows.append(dict(pair=m, dip=dr, uj=ur, pass_30nov=p30, breach_30nov=b30, pass_mt5=pp["MT5"], pass_FT=pp["FT"], breach_mt5=bb["MT5"], breach_FT=bb["FT"],
                         pass_22dec=p22, breach_22dec=b22, worst_day=worst))
    G = pd.DataFrame(rows).sort_values("pass_30nov", ascending=False)
    G.to_csv("forex/ea_research/NOV30_GRID.csv", index=False)
    pd.set_option("display.width", 250)
    print("\nTop 15 configurations by P(pass by 30 Nov), MIX of MT5 12-month and FT 2022-26 pools:")
    print(G.head(15).round(1).to_string(index=False))
    G["ratio"] = G.pass_30nov / G.breach_30nov.clip(lower=0.1)
    best_ratio = G[G.pass_30nov >= 5].sort_values("ratio", ascending=False).head(5)
    print("\nBest pass-per-breach configurations (pass >= 5% by 30 Nov):"); print(best_ratio.round(2).to_string(index=False))
    # ---- robustness of the max-pass and best-ratio configurations
    for tag, row in (("max-pass", G.iloc[0]), ("best ratio", best_ratio.iloc[0] if len(best_ratio) else G.iloc[0])):
        m, dr, ur = row.pair, int(row.dip), int(row.uj)
        for frac, seed in ((1.0, 2), (0.7, 1), (0.7, 2)):
            P.RNG = np.random.default_rng(1000 + seed); S = {}
            for pool in ("MT5", "FT"):
                X = shift_edge(pair[(pool, m)], frac) if m else pair[(pool, m)]
                X = add_leg(X, dips[dr]) if dr else X; X = add_leg(X, ujs[ur]) if ur else X; S[pool] = X
            res = run(P, S, H); p30, b30, pp, _ = summarise(res, HZ["30 Nov"]); p22, b22, _, _ = summarise(res, HZ["22 Dec"])
            print(f"  {tag} (pair x{m}, dip {dr}, USDJPY ${ur}) edge {int(frac*100)}% seed {seed}: 30 Nov pass {p30:.1f}% (MT5 {pp['MT5']:.0f}% / FT {pp['FT']:.0f}%) breach {b30:.1f}% | 22 Dec pass {p22:.1f}% breach {b22:.1f}%")
    # ---- dynamic-sizing ceiling (pass70.dp over its multipliers, with the max-pass config's dip / USDJPY legs)
    dr, ur = int(G.iloc[0].dip), int(G.iloc[0].uj)
    by_pool = []
    for pool in ("MT5", "FT"):
        L_ = []
        for mm in P.MULTS:
            X = cg.pair_series(pool, mm, mm, GUARD); X = add_leg(X, dips[dr]) if dr else X; X = add_leg(X, ujs[ur]) if ur else X; L_.append(X)
        by_pool.append(L_)
    for lam in (0.0, 1.0):
        pol, W = P.dp(by_pool, (0.5, 0.5), lam, HZ["30 Nov"])
        res = {pool: P.simulate(by_pool[i], pol, H) for i, pool in enumerate(("MT5", "FT"))}
        p30, b30, pp, _ = summarise(res, HZ["30 Nov"])
        print(f"  DP ceiling over pair multipliers {P.MULTS} (dip {dr}, USDJPY ${ur}), lambda {lam}: 30 Nov pass {p30:.1f}% (MT5 {pp['MT5']:.0f}% / FT {pp['FT']:.0f}%) breach {b30:.1f}%")


if __name__ == "__main__":
    main()
