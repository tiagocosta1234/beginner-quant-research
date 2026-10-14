"""'From zero' book: every small confirmed edge in one account, sized together (MT5 broker pool, same pipeline as faster_than_live.py): gold pair + ManualDip + RSI(2) US dips (each at day risk 500, x0.75 as in combo_grid) at pair sizes x1.0 / x1.5 / x2.0.
python -m forex.self_improving.session.book_assembly"""
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, rsi2_leg as R2
from forex.self_improving.session.manualdip_weight import stats

P.C0 = 0.0


def main():
    kd = G.dip_days(500); rs = R2.D2; rows = []
    for m, g in ((1.0, 1500.0), (1.5, 1500.0), (2.0, 2000.0)):
        base = G.pair_series("MT5", m, m, g)
        for nm, S in (("pair", base), ("pair + ManualDip", G.add_dip(base, kd, g)), ("pair + RSI2", G.add_dip(base, rs, g)), ("pair + ManualDip + RSI2", G.add_dip(G.add_dip(base, kd, g), rs, g))):
            o = stats(S); rows.append(dict(size=m, loss=g, book=nm, **o)); print({k: (round(float(v), 1) if not isinstance(v, str) else v) for k, v in rows[-1].items()}, flush=True)
    pd.DataFrame(rows).to_csv("D:/finance/si_ledgers/BOOK_ASSEMBLY.csv", index=False)


if __name__ == "__main__":
    main()
