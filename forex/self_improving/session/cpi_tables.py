"""All the decision tables redone on ONE basis: news flat on the CPI only (the live guard's setting), MT5 broker pool, same pipeline (1-minute guard daily series + day-block bootstrap, 40,000 paths, 250 business days).
A: pair only; B: book (pair + ManualDip 500 + RSI(2) 500); journeys with retries (a breach costs a 451 USD fee and a new attempt starts at once); C: ManualDip weight and the gold-run stress; D: session variants (profit stop, SDB runner) at x1.5.
python -m forex.self_improving.session.cpi_tables"""
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, rsi2_leg as R2, event_macro as EM
from forex.self_improving.session import faster_than_live as F, session_sdbrunner as R

cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); G.EV = np.array(sorted(EM.server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI")); P.C0 = 0.0; F.P.C0 = 0.0
rng = np.random.default_rng(11)


def run(S):
    st, dy = P.simulate([S] * len(P.MULTS), P.I12, 250, paths=40000); st = np.asarray(st); dy = np.asarray(dy) + 1; ps = st == 1; n = len(st); tot = []; att = []
    for _ in range(8000):
        t = 0; a = 0
        while True:
            i = rng.integers(0, n); a += 1
            if st[i] == 1: t += dy[i]; break
            t += dy[i] if st[i] == 2 else 250
            if t > 400: t = np.nan; break
        tot.append(t); att.append(a)
    tot = np.array(tot); att = np.array(att)
    return dict(breach1=100 * np.mean(st == 2), p22=100 * np.mean(ps & (dy <= 22)), p33=100 * np.mean(ps & (dy <= 33)), p44=100 * np.mean(ps & (dy <= 44)), p66=100 * np.mean(ps & (dy <= 66)), p120=100 * np.mean(ps & (dy <= 120)), med1=float(np.median(dy[ps])) if ps.any() else np.nan,
                j_med=float(np.nanmedian(tot)), j_p33=100 * np.nanmean(tot <= 33), j_p44=100 * np.nanmean(tot <= 44), j_p60=100 * np.nanmean(tot <= 60), attempts=att.mean(), fees=451 * att.mean())


def show(tag, rows, df):
    print(f"\n== {tag}", flush=True); print(df.round(1).to_string(index=False), flush=True)


def main():
    kd = G.dip_days(500); rs = R2.D2; out = []
    cfgs = ((1.0, 1500.0), (1.5, 1500.0), (1.8, 1800.0), (2.0, 2000.0), (2.5, 2000.0), (3.0, 2000.0))
    A = []; B = []
    for m, g in cfgs:
        base = G.pair_series("MT5", m, m, g); A.append(dict(system="pair", size=m, loss=g, **run(base))); B.append(dict(system="book", size=m, loss=g, **run(G.add_dip(G.add_dip(base, kd, g), rs, g))))
    dA = pd.DataFrame(A); dB = pd.DataFrame(B); show("A pair only (CPI list)", A, dA); show("B book: pair + ManualDip + RSI(2) (CPI list)", B, dB)
    d0 = (pd.Timestamp("2026-01-12") - pd.Timestamp("1970-01-01")).days; d1 = (pd.Timestamp("2026-03-10") - pd.Timestamp("1970-01-01")).days; Cn = []
    for m, g in ((1.0, 1500.0), (1.5, 1500.0), (2.0, 2000.0)):
        base = G.pair_series("MT5", m, m, g); days = np.asarray(base["days"]); keep = ~((days >= d0) & (days <= d1))
        for r in (0, 500, 1000, 2000):
            S = base if r == 0 else G.add_dip(base, G.dip_days(r), g); full = F.stats(S); cut = F.stats({k: (np.asarray(v)[keep] if k != "days" else days[keep]) for k, v in S.items()})
            Cn.append(dict(size=m, loss=g, dip_risk=r, p44=full["p44"], breach=full["breach"], med=full["med"], p44_nogold=cut["p44"], breach_nogold=cut["breach"], med_nogold=cut["med"]))
    dC = pd.DataFrame(Cn); show("C ManualDip weight and gold-run stress (CPI list)", Cn, dC)
    tr, lo, hi = R.load_flag("MT5"); Dd = []
    for Pc in (F.NONE, 2000.0):
        for rn in (False, True):
            t = R.runner_leg(tr, 0, "sdb") if rn else tr; Dd.append(dict(profit=("none" if Pc == F.NONE else Pc), runner=rn, **F.stats(F.series(t, lo, hi, 1.5, Pc, 1500.0))))
    dD = pd.DataFrame(Dd); show("D session variants at x1.5 / 1.5% (CPI list)", Dd, dD)
    with pd.ExcelWriter if False else open(os.devnull, "w"): pass
    dA.to_csv("D:/finance/si_ledgers/CPI_TABLE_A_pair.csv", index=False); dB.to_csv("D:/finance/si_ledgers/CPI_TABLE_B_book.csv", index=False); dC.to_csv("D:/finance/si_ledgers/CPI_TABLE_C_manualdip.csv", index=False); dD.to_csv("D:/finance/si_ledgers/CPI_TABLE_D_sessions.csv", index=False)


if __name__ == "__main__":
    main()
