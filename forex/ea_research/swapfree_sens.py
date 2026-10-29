"""Sensitivity of the D2 swap-free drift book (descriptive, after the registered result: no selection, the registered D2 stays the candidate).
One parameter at a time around D2: SMA 100/150/250, vol window 20/40/120, decision weekday Wed/Fri, decision hour 16:00/20:00 server.
HOLD 2026 is already open for D2, so its neighbours' HOLD numbers are not a clean test.   python -m forex.ea_research.swapfree_sens"""
import pandas as pd

from forex.ea_research import swapfree_drift as S


def run(label, D, C):
    r = dict(label=label)
    for p, (a, b) in S.PER.items():
        s = S.run_book(D["HD"] if p == "OOT" else D["MT5"], C, "D2", a, b)
        r[p] = s.V.mean(); r[f"{p}_sh"] = s.V.mean() / s.V.std() * 252 ** 0.5
    dv = pd.concat([S.run_book(D["MT5"], C, "D2", *S.PER["DEV"]), S.run_book(D["MT5"], C, "D2", *S.PER["VAL"])])
    r["DEVVAL_t"] = dv.V.mean() / dv.V.std() * len(dv) ** 0.5
    print(f"{label:22s} OOT {r['OOT']:+6.1f} | DEV {r['DEV']:+6.1f} | VAL {r['VAL']:+6.1f} | HOLD {r['HOLD']:+6.1f} | DEV+VAL t {r['DEVVAL_t']:+.2f} | Sharpe DEV {r['DEV_sh']:+.2f} VAL {r['VAL_sh']:+.2f} HOLD {r['HOLD_sh']:+.2f}", flush=True)
    return r


def main():
    D = {"MT5": S.build("MT5"), "HD": S.build("HD")}; C = S.spliced_closes(D["MT5"], D["HD"])
    rows = [run("D2 registered", D, C)]
    for n in (100, 150, 250):
        S.SMAN = n; rows.append(run(f"SMA {n}", D, C))
    S.SMAN = 200
    for n in (20, 40, 120):
        S.VOLN = n; rows.append(run(f"vol window {n}", D, C))
    S.VOLN = 60
    for wd, nm in ((2, "Wed"), (4, "Fri")):
        S.WD = wd; rows.append(run(f"decide {nm}", D, C))
    S.WD = 0
    for h in (16, 20):
        S.DEC_MIN = h * 60; Dh = {"MT5": S.build("MT5"), "HD": S.build("HD")}
        rows.append(run(f"decide {h}:00 server", Dh, C))
    S.DEC_MIN = 18 * 60
    pd.DataFrame(rows).to_csv("data/si_ledgers/SWAPFREE_SENS.csv", index=False)


if __name__ == "__main__":
    main()
