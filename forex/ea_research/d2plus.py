"""D2PLUS (PREREG_D2PLUS.md): breadth, correlation, downside-vol and hysteresis refinements of the D2 book.
   python -m forex.ea_research.d2plus [--dry-run]"""
import sys

import numpy as np
import pandas as pd

import forex.ea_research.swapfree_drift as sd

VOLN, SMAN = sd.VOLN, sd.SMAN
BASE = sd.signals
STATE = {}


def signals(C, day, variant):
    if variant in sd.VARIANTS: return BASE(C, day, variant)
    past = C[C.index < day]
    if len(past) < VOLN + 1 or past.iloc[-SMAN:].notna().sum().min() < SMAN:
        z = pd.Series(0.0, index=C.columns); return z, z > 0
    ret = np.log(past).diff().iloc[-VOLN:]
    vol = ret.std() * np.sqrt(252)
    sma = past.iloc[-SMAN:].mean(); last = past.iloc[-1]
    on = last > sma
    if variant == "P41":
        w = (1 / vol) / (1 / vol).sum()
        if on.sum() < 3: on[:] = False
    elif variant == "P42":
        cor = ret.corr(); mc = (cor.sum() - 1) / (len(cor) - 1)
        q = 1 / (vol * (1 + mc)); w = q / q.sum()
    elif variant == "P43":
        dn = ret.clip(upper=0); sdv = np.sqrt((dn ** 2).mean()) * np.sqrt(252)
        q = 1 / sdv; w = q / q.sum()
    elif variant == "P47":
        w = (1 / vol) / (1 / vol).sum()
        st = STATE.setdefault("hyst", {})
        prev = st.get("on", pd.Series(False, index=C.columns))
        on = prev.copy()
        on[last > 1.01 * sma] = True; on[last < 0.99 * sma] = False
        st["on"] = on.copy()
    return w * on, on


VARS = ("D2", "P41", "P42", "P43", "P47")
PER = {"OOT": sd.PER["OOT"], "DEV": sd.PER["DEV"], "VAL": sd.PER["VAL"], "HOLD": sd.PER["HOLD"]}


def main():
    sd.signals = signals
    DE, DH = sd.build("MT5"), sd.build("HD"); C = sd.spliced_closes(DE, DH)
    if "--dry-run" in sys.argv:
        for x in (pd.Timestamp("2022-06-13"), pd.Timestamp("2024-03-04")):
            for v in ("P41", "P42", "P43"):
                a, _ = signals(C, x, v); b, _ = signals(C[C.index <= x], x, v)
                assert np.allclose(a.fillna(0), b.fillna(0)), (x, v)
            print(x.date(), {v: signals(C, x, v)[0].round(3).to_dict() for v in ("D2", "P42", "P43")})
        print("truncation passed (P47 is a path-dependent state of past closes only)")
        return
    S = {}
    for v in VARS:
        for p, (a, b) in PER.items():
            STATE.clear()
            S[(v, p)] = sd.run_book(DH if p == "OOT" else DE, C, v, a, b)
    rows = []
    for v in VARS:
        dv = pd.concat([S[(v, "DEV")], S[(v, "VAL")]])
        r = dict(variant=v, **{f"{p}_mean": S[(v, p)].V.mean() for p in PER}, DEVVAL_t=sd.stats(dv)["t"], DEVVAL_sharpe=sd.stats(dv)["sharpe"],
                 OOT_t=sd.stats(S[(v, "OOT")])["t"], maxdd_DEVVAL=sd.stats(dv)["maxdd"])
        if v != "D2":
            dif = pd.concat([S[(v, p)].V - S[("D2", p)].V.reindex(S[(v, p)].index).fillna(0) for p in ("OOT", "DEV", "VAL")])
            r["diff_mean"] = dif.mean(); r["diff_t"] = dif.mean() / dif.std() * np.sqrt(len(dif)) if dif.std() > 0 else 0
            r["corr_D2"] = np.corrcoef(dv.V, pd.concat([S[("D2", "DEV")], S[("D2", "VAL")]]).V.reindex(dv.index).fillna(0))[0, 1]
            r["improves"] = bool(r["DEVVAL_t"] >= 2.50 and r["OOT_mean"] > 0 and r["diff_mean"] > 0 and r["diff_t"] >= 2.24)
        rows.append(r)
    T = pd.DataFrame(rows); pd.set_option("display.width", 250)
    print("USD a day per 100k gross (HOLD = 2026, context only):")
    print(T.round(3).to_string(index=False))
    T.to_csv("D:/finance/si_ledgers/D2PLUS.csv", index=False)


if __name__ == "__main__":
    main()
