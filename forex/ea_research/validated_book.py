"""PREREG_VALIDATED_BOOK: D2 (guarded) + USDJPY London (tick haircut) + index dips DA on the account.   python -m forex.ea_research.validated_book"""
import numpy as np
import pandas as pd

from forex.ea_research import combo_grid as cg
from forex.ea_research import d2_account as A
from forex.ea_research import swapfree_drift as S
from forex.ea_research import swapfree_mt5sim as Q

HZ = {**Q.HZ, "31 Dec 27": int(np.busday_count(Q.START, np.datetime64("2028-01-01")))}
HAIR = 0.06


def main():
    DE, DH = S.build("MT5"), S.build("HD"); C = S.spliced_closes(DE, DH); cache = A.day_cache()
    d2 = {G: A.run(cache, C, G, 1500, "2022-01-03", "2026-10-02") for G in (75_000, 100_000)}
    e = pd.read_parquet("data/si_ledgers/BRK_EXITS.parquet"); e = e[(e.mkt == "USDJPY") & (e.kind == "BRK")]
    uj = e.groupby(pd.to_datetime(e.day)).X4_noTP.first() - HAIR
    da = cg.dip_days(500); da.index = pd.to_datetime(da.index, unit="D")
    days = d2[100_000].index; days = days[days >= "2022-02-15"]
    U = uj.reindex(days).fillna(0.0); Dv = da.V.reindex(days).fillna(0.0); Db = da.B.reindex(days).fillna(0.0)
    print(f"legs on {len(days)} days: USDJPY mean {U[U != 0].mean():+.3f} R after the {HAIR} R haircut ({(U != 0).sum()} trades); DA {int((Dv != 0).sum())} days, mean {Dv[Dv != 0].mean():+.0f} USD")
    x = d2[100_000].V.reindex(days)
    print(f"daily correlations: D2-USDJPY {np.corrcoef(x, U)[0, 1]:+.3f}, D2-DA {np.corrcoef(x, Dv)[0, 1]:+.3f}, USDJPY-DA {np.corrcoef(U, Dv)[0, 1]:+.3f}")
    rng = np.random.default_rng(1510265); rows = []
    for G, ur, use_da in ((100_000, 0, False), (100_000, 150, False), (100_000, 300, False), (100_000, 0, True), (100_000, 150, True), (75_000, 300, True)):
        s = d2[G].reindex(days)
        V = s.V + U * ur + (Dv if use_da else 0); B = s.B + np.minimum(U, 0) * ur + (Db if use_da else 0)
        g = B <= -1500; V = np.where(g, np.minimum(V, B), V); B = np.minimum(B, V)
        lab = f"D2 {G/1000:.0f}k" + (f" + USDJPY {ur}" if ur else "") + (" + DA" if use_da else "")
        for nm, end in (("2022-25", "2025-12-31"), ("2022-26", "2026-10-02")):
            m = days <= end; H = max(HZ.values()) + 1
            st, day = Q.simulate(np.asarray(V)[m], np.asarray(B)[m], H, rng)
            cells = {k: (100 * np.mean((st == 1) & (day < h)), 100 * np.mean((st == 2) & (day < h))) for k, h in HZ.items()}
            vv = np.asarray(V)[m]
            print(f"{lab:28s} {nm}: mean {vv.mean():+.1f}/day sd {vv.std():.0f} | " + " | ".join(f"{k} {p:.1f}/{b:.1f}" for k, (p, b) in cells.items()), flush=True)
            rows.append(dict(config=lab, pool=nm, mean=vv.mean(), sd=vv.std(), **{f"pass {k}": p for k, (p, b) in cells.items()}, **{f"breach {k}": b for k, (p, b) in cells.items()}))
    pd.DataFrame(rows).to_csv("data/si_ledgers/VALIDATED_BOOK.csv", index=False)


if __name__ == "__main__":
    main()
