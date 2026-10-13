"""Family M: turn of the month on index CFDs, as registered in PREREG_TURN_OF_MONTH.md.   python -m forex.ea_research.turn_of_month --dev | --holdout"""
import argparse, datetime as dt, json
from pathlib import Path
import numpy as np, pandas as pd
from forex.ea_research import event_macro as V
from forex.ea_research.overnight_grid import srv
HERE = Path(__file__).resolve().parent; STATE = HERE / "TURN_OF_MONTH_STATE.json"
MK = {"SP": ("America/New_York", 15, 55), "NSDQ": ("America/New_York", 15, 55), "DOW": ("America/New_York", 15, 55), "DAX": ("Europe/Berlin", 17, 25)}
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}

def closes(m, last):
    tz, hh, mm = MK[m]; rows = []
    for D in pd.bdate_range("2021-11-01", last):
        q = V.quote(m, srv(str(D.date()), tz, hh, mm, 0))
        if q is not None: rows.append((D, q[0], q[1]))
    return pd.DataFrame(rows, columns=["date", "bid", "ask"]).set_index("date")

def events(last):
    ev = {"M1": [], "M2": []}; diag = []
    for m in MK:
        C = closes(m, last); C["ym"] = C.index.to_period("M"); C["mid"] = (C.bid + C.ask) / 2
        months = C.ym.unique()
        idx = {p: C.index[C.ym == p] for p in months}
        win_days = set()
        for a, b in zip(months[:-1], months[1:]):
            A, B = idx[a], idx[b]
            if len(A) < 6 or len(B) < 3: continue
            for nm, k in (("M1", 2), ("M2", 5)):
                ei, xi = A[-k], B[2]
                ev[nm].append(dict(month=pd.Timestamp(b.start_time), mkt=m, net=(C.at[xi, "bid"] / C.at[ei, "ask"] - 1) * 1e4 - 2 * V.SLIP * 1e4))
            win_days |= {A[-1], B[0], B[1], B[2]}
        r = np.log(C.mid).diff() * 1e4; diag.append(pd.DataFrame({"mkt": m, "r": r, "win": [d in win_days for d in C.index]}, index=C.index))
    return {k: pd.DataFrame(v).groupby("month").net.mean() for k, v in ev.items()}, pd.concat(diag)

def st(s, p):
    a, b = PER[p]; x = s[(s.index >= a) & (s.index <= b)]; n = len(x)
    return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 2 else np.nan, win=float((x > 0).mean()), worst=float(x.min()))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev:
        E, D = events("2025-12-31"); res = {}
        for nm, s in E.items():
            for p in ("DEV", "VAL"):
                z = st(s, p); print(f"{nm} {p}: months {z['n']} | mean {z['mean']:+.1f} bp | months up {100*z['win']:.0f}% | t {z['t']:+.2f} | worst {z['worst']:+.1f}")
                with open(V.LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},turn_of_month,{nm},{p},{z['n']},{z['n']},,{z['mean']:.4f},,{z['t']:.2f},{z['win']:.3f},\n")
            d, v = st(s, "DEV"), st(s, "VAL"); res[nm] = bool(d["mean"] > 0 and d["t"] >= 2.24 and v["mean"] > 0); print(f"   {nm} acceptance 1-2: {res[nm]}")
        X = D[(D.index >= "2022-01-01") & (D.index <= "2025-12-31")].dropna()
        for m, g in X.groupby("mkt"):
            w, o = g[g.win].r, g[~g.win].r; print(f"   diag {m}: window days mean {w.mean():+.1f} bp/day (n {len(w)}) vs other days {o.mean():+.1f} (n {len(o)}) | Welch t {(w.mean()-o.mean())/np.sqrt(w.var()/len(w)+o.var()/len(o)):+.2f}")
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No trial passed acceptance 1-2: the 2026 hold-out stays CLOSED.")
        else:
            E, _ = events("2026-09-30")
            for nm in live: z = st(E[nm], "HOLD"); print(f"{nm} HOLD: months {z['n']} mean {z['mean']:+.1f} bp t {z['t']:+.2f}")
