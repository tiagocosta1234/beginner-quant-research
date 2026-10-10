"""GoldenShot at 1% risk on top of the pair, under TESTER-like and LIVE-like trade statistics (the trader 2026-10-09: "(original wording omitted)").
   python -m mt5broker.ea_research.gs_live_like
Day P&L of the EA is simulated per path: trades per business day ~ Poisson(lam); each trade is a winner (+W USD) or a loser (-L USD); at the default 1% risk (lot about 0.5 on 100,000): tester numbers = W 116, L 653 (full stop about 1,000-1,250), lam 1.5, loss rate 4.4%; live-signal numbers = W 87.5, L 581 (1.75 and 11.63 USD per oz x 50 oz), lam 0.6 (3 trades a week), loss rate 12.9%.
Combined with the pair (clean_boot_lib series MT5 broker x1.2, aligned day bootstrap, mean block 5): V = pair + f x EA, in-day low = pair low + f x min(EA day, 0) (the worst moments coincide, conservative), the guard floors the day at -2,000, counted profit min(day, 2,000), breach = in-day low <= -2,500 or equity <= 92,000. Option 'one loss a day' = the EA's own setting 'Max Losing Trades Per Day = 1' (the manual recommends it for account accounts)."""
from __future__ import annotations

import numpy as np

from mt5broker.ea_research import clean_boot_lib as L
from mt5broker.ea_research import clean_bootstrap as BS

A, CAPD, TARGET = BS.A, BS.CAPD, BS.TARGET
RNG = np.random.default_rng(777)
SCEN = {"tester-like": dict(lam=1.5, ploss=0.044, W=116.0, L=653.0), "in between": dict(lam=1.0, ploss=0.085, W=100.0, L=620.0), "live-like (author's signal)": dict(lam=0.6, ploss=0.129, W=87.5, L=581.0),
        "worse than live": dict(lam=0.6, ploss=0.16, W=87.5, L=581.0)}


def ea_day(n, p, f, one_loss):
    k = RNG.poisson(p["lam"], n); losses = RNG.binomial(k, p["ploss"]); wins = k - losses
    if one_loss:                                                                       # the EA stops after the day's first loss: later trades are not taken (on average half of the winners come before it)
        wins = np.where(losses >= 1, wins // 2, wins); losses = np.minimum(losses, 1)
    return f * (wins * p["W"] - losses * p["L"]), f * (-losses * p["L"])


def run(Vp, Bp, p, f, one_loss, paths=8000, H=BS.H22, with_ea=True):
    n = len(Vp); idx = BS.stationary_idx(n, paths, H); cnt = np.full(paths, BS.C0); st = np.zeros(paths, np.int8); day = np.full(paths, -1); worst = 0
    for j in range(H):
        v, b = Vp[idx[:, j]], Bp[idx[:, j]]
        if with_ea:
            g, gl = ea_day(paths, p, f, one_loss); v = np.maximum(v + g, -CAPD); b = np.maximum(b + np.minimum(gl, 0.0), -2100.0)
        act = st == 0; br = act & ((b <= -0.025 * A) | (A + cnt + b <= 0.92 * A)); st = np.where(br, 2, st); day = np.where(br, j, day); act = st == 0
        cnt = np.where(act, cnt + np.where(v > 0, np.minimum(v, CAPD), v), cnt); ps = act & (cnt >= TARGET); st = np.where(ps, 1, st); day = np.where(ps, j, day)
    return np.mean((st == 1) & (day < BS.H30)), np.mean((st == 1) & (day < H)), np.mean(st == 2)


def main():
    s = L.series("MT5", 1.2); Vp, Bp = s["V"], s["B"]
    base = run(Vp, Bp, None, 0, False, with_ea=False); print(f"pair alone (same pool): by 30 Nov {100*base[0]:.1f}% | by 22 Dec {100*base[1]:.1f}% | breach by 22 Dec {100*base[2]:.1f}%")
    for name, p in SCEN.items():
        ev = p["lam"] * ((1 - p["ploss"]) * p["W"] - p["ploss"] * p["L"]); pf = (1 - p["ploss"]) * p["W"] / (p["ploss"] * p["L"])
        print(f"\n== {name}: lam {p['lam']}/day, loss rate {100*p['ploss']:.1f}%, W {p['W']:.0f}, L {p['L']:.0f}  ->  PF {pf:.2f}, expected {ev:+.0f} USD a day at 1% risk")
        for f in (0.5, 1.0):
            for one in (False, True):
                m = run(Vp, Bp, p, f, one); print(f"   risk {f:.1f}% per trade{' + one loss a day' if one else '                 '}: by 30 Nov {100*m[0]:5.1f}% | by 22 Dec {100*m[1]:5.1f}% | breach {100*m[2]:4.1f}%")


if __name__ == "__main__":
    main()
