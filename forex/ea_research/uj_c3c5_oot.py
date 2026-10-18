"""UJ_C3C5_OOT part A: USDJPY London breakout + C3 risk-on / + C5 FVG on the 2026 hold-out (PREREG_UJ_C3C5_OOT.md).
Uses uj_conf.trades() unchanged.   python -m forex.ea_research.uj_c3c5_oot"""
import numpy as np, pandas as pd
from forex.ea_research.uj_conf import trades
from forex.ea_research.orbx import ct


def main():
    from forex.ea_research.usdjpy_account_env import account, HZ
    T, _, _ = trades()
    H = T[(T.day >= "2026-01-01") & (T.day < "2026-10-17")]
    print(f"2026 hold-out: base n {len(H)} {H.R.mean():+.3f} R (base 2026 already known)\n")
    for name, c in (("UJ+C3 risk-on", "C3_risk_on"), ("UJ+C5 FVG", "C5_fvg")):
        w, wo = H[H[c]], H[~H[c]]; mu, t = ct(w)
        ok = mu > 0 and t >= 1.96 and mu > wo.R.mean()
        print(f"{name:14s} 2026: n {len(w)} {mu:+.3f} R (t {t:+.2f}, win {(w.R > 0).mean():.0%}) | without the flag n {len(wo)} {wo.R.mean():+.3f} R -> part A {'PASS' if ok else 'FAIL'}")
        print(f"{'':14s} by period with / without: " + ", ".join(f"{a}: {T[(T.day>=lo)&(T.day<hi)&T[c]].R.mean():+.3f} / {T[(T.day>=lo)&(T.day<hi)&~T[c]].R.mean():+.3f}"
              for a, lo, hi in (("2022-24", "2022-01-01", "2025-01-01"), ("2025", "2025-01-01", "2026-01-01"), ("2026", "2026-01-01", "2026-10-17"))))
    days = pd.bdate_range("2022-01-03", "2026-10-16"); Hh = max(HZ.values()); rng = np.random.default_rng(1625)
    print("\naccount view (information only; 2022-26 trades, in-sample for 2022-25), from 95,472, pass% / breach%:")
    for name, c in (("base", None), ("UJ+C3", "C3_risk_on"), ("UJ+C5", "C5_fvg")):
        x = T if c is None else T[T[c]]
        for hc in (0.0, 0.06):
            Rd = x.set_index("day").R.reindex(days) - hc; trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
            s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
            for risk in (150, 250):
                st, ev, _ = account(r[bi], trd[bi], risk)
                print(f"  {name:6s} ${risk} haircut {hc:.2f} ({len(x)} trades, {x.R.mean() - hc:+.3f} R): " + "  ".join(
                    f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("22 Dec", "31 Mar 27", "30 Jun 27")))


if __name__ == "__main__":
    main()
