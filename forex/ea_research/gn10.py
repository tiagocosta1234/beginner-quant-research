"""GN10: late-day REVERSAL on big-move days (GN9's rule with the side flipped), pooled NSDQ + SP + DOW on MT5, decided only on the
2026 hold-out. Post-hoc hypothesis from GN9. Pre-registration: forex/ea_research/PREREG_GN10.md.
   python -m forex.ea_research.gn10 --dry-run   (development evidence, post-hoc; no 2026 number)
   python -m forex.ea_research.gn10 --run       (the one look at the 2026 hold-out)"""
import argparse, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load
from forex.ea_research.orbx import ct
from forex.ea_research.gn2 import info
from forex.ea_research import gn9

MKTS = (("NSDQ", "NQ"), ("SP", "ES"), ("DOW", None))
DEC, XIT, REF = (15, 29), (15, 58), (15, 59)
DEV, VAL, HOLD, OOT = gn9.DEV, gn9.VAL, gn9.HOLD, gn9.OOT
per = gn9.per


def mt5_events(mkt, flip=True):
    E = load(mkt)
    T, C = gn9.lateday(E, gn9.mt5_SPAN[0], gn9.mt5_SPAN[1], DEC, XIT, REF, seed=gn9.seed_of(mkt), flip=flip)
    return E, T.assign(mkt=mkt), C.assign(mkt=mkt)


def fut_events(root, spread):
    F = gn9.load_fut(gn9.FUTP.format(root), spread)
    T, C = gn9.lateday(F, OOT[0], OOT[1], DEC, XIT, REF, gn9.roll_mondays(), None, seed=gn9.seed_of(root), flip=True)
    return T.assign(mkt=root), C.assign(mkt=root)


def stats(T, C, label):
    m, t = ct(T); i, ti = info(T, C)
    return f"{label} n {len(T)} {m:+.3f} R (t {t:+.2f}) win {(T.R > 0).mean():.0%} info {i:+.3f} (t {ti:+.2f})"


def collect():
    big, ctrl, fut, fctrl, allday = [], [], [], [], []
    for mkt, root in MKTS:
        E, T, C = mt5_events(mkt)
        big.append(T[T.big]); ctrl.append(C[C.big]); allday.append(T)
        if root:
            TF, CF = fut_events(root, gn9.window_spread(E, DEC, XIT))
            fut.append(TF[TF.big]); fctrl.append(CF[CF.big])
    return pd.concat(big), pd.concat(ctrl), pd.concat(fut), pd.concat(fctrl), pd.concat(allday)


def dry_run():
    for mkt, ref_mean in (("NSDQ", -0.145), ("SP", -0.058)):
        _, T, _ = mt5_events(mkt, flip=False); d = per(T[T.big], DEV)
        print(f"identity check flip=False {mkt} DEV big-day mean {d.R.mean():+.3f} (GN9: {ref_mean:+.3f}) -> {'OK' if abs(d.R.mean() - ref_mean) < 0.0005 else 'MISMATCH'}")
    B, C, F, FC, A = collect()
    print("\nDevelopment evidence (POST-HOC, these data suggested the rule): reversal on big-move days")
    for pn, p in (("DEV 2022-24", DEV), ("VAL 2025", VAL)):
        print(f"  {pn}: " + stats(per(B, p), per(C, p), "pooled") + " | " + " | ".join(
            f"{m} {per(B[B.mkt == m], p).R.mean():+.3f} (n {len(per(B[B.mkt == m], p))})" for m, _ in MKTS))
    print("  OOT futures 2020-21: " + stats(F, FC, "pooled NQ+ES") + " | " + " | ".join(f"{m} {F[F.mkt == m].R.mean():+.3f} (n {(F.mkt == m).sum()})" for m in ("NQ", "ES")))
    print(f"  normal days (not big), reversal side, DEV pooled: {per(A[~A.big], DEV).R.mean():+.3f} (n {len(per(A[~A.big], DEV))})")
    h = per(B, HOLD)
    print(f"\n2026 hold-out big days (count only): pooled trades {len(h)}, days {h.day.nunique()}, by index " + " ".join(f"{m} {(h.mkt == m).sum()}" for m, _ in MKTS))


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    B, C, F, FC, A = collect()
    h, hc = per(B, HOLD), per(C, HOLD); m, t = ct(h); i, ti = info(h, hc)
    ok = m > 0 and t >= 1.65 and i > 0
    print("GN10 R1 - 2026 HOLD-OUT (one look): " + stats(h, hc, "pooled NSDQ+SP+DOW") + f" -> {'PASS' if ok else 'FAIL'}")
    print("   by index: " + " | ".join(stats(h[h.mkt == mk], hc[hc.mkt == mk], mk) for mk, _ in MKTS))
    print("   by month: " + " ".join(f"{k.strftime('%b')} {g.R.mean():+.2f}({g.day.nunique()})" for k, g in h.groupby(h.day.dt.to_period("M"))))
    print(f"   normal days 2026 (reversal side, pooled): {per(A[~A.big], HOLD).R.mean():+.3f}")
    days = pd.bdate_range("2022-01-03", "2026-10-16"); Hh = max(HZ.values()); rng = np.random.default_rng(1627)

    def acct(x, risk):
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        return "  ".join(f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27"))

    print("\nAccount view (2022-26 big-day trades, from 95,472, MT5 broker rules; pass% / breach% by date; R = 2 S):")
    x = B[B.day >= "2022-01-01"]
    for lab, xx in (("pooled (3 index trades a day)", x), ("NSDQ alone", x[x.mkt == "NSDQ"])):
        for risk in (250, 500):
            print(f"  {lab} ${risk}: ({len(xx)} trades, {xx.R.mean():+.3f} R) {acct(xx, risk)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
