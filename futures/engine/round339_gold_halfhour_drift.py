"""
Round 339 (2026-10-04, PRE-REGISTERED; ONE ledger row, k + 1): unconditional half-hour drift of gold (XAUUSD) by time of day on MT5 broker bid / ask minute bars, including the LBMA price-fix windows.

Mechanism: benchmark auctions (LBMA gold price, 10:30 and 15:00 London = 05:30 and 10:00 New York) and regional session opens concentrate flows at fixed clock times; published work found pre-fix drifts that mostly faded after the 2015 reform. Gold's cost is tiny (about 1 bp), so even a few-bp pattern could be tradable. Ledger checked first (k = 2040): Round 319 tested prior-slot follow / fade on GC / SI futures (Databento), Round 298 / 421 US-index slots; unconditional per-slot drift of XAUUSD on MT5 broker fills and the fix windows are not in the ledger.
DATA: MT5 XAUUSD M1 bid / ask (forex/early_mt5/data, via Round 321's _mt5broker_bars, ROUND_DATA=mt5broker, ROUND_FILLS=ask), 2021-10..2026-10, all hours Monday-Friday, New York clock; 48 half-hour slots minus those inside the daily break and any with fewer than 400 usable IS days; a slot-day needs all 30 minutes present.
TRADE (per slot, per direction, 96 hypotheses minus dropped slots): LONG buys at the ASK open of the slot's first minute and sells at the BID close of its last minute; SHORT sells at the bid open and buys at the ask close; net bp = return x 1e4 - 0.5 (commission / slippage allowance).
SPLIT: IS 2021-10-01..2023-12-31, OOS 2024-01-01 onward. SELECTION: Benjamini-Hochberg q = 0.10 on IS one-sided p-values (day bootstrap, 2,000 draws, seed 339); OOS only for IS survivors. CANDIDATE (fixed now): BH survivor in IS AND OOS mean net >= +1.0 bp with P(>0) >= 0.99 AND the opposite direction's OOS mean <= 0. The two LBMA slots (05:30-06:00 and 10:00-10:30 New York) are among the hypotheses, not tested separately. Not widened after the run (no new slots, lengths, directions, conditioning or assets).
DRY-RUN COUNTS (days only, no returns): 44 half-hour slots remain (00:00-16:30 New York and 18:30-23:30; slots 16:30-18:00 are the daily break and 18:00 starts partial); IS days per slot 424-579 (the late-evening slots have fewer: 424-464), OOS 556-711; none dropped by the 400-day floor; m = 88 hypotheses (44 x long / short).
POWER: per-slot half-hour sd about 12-25 bp, n about 460-579 IS days, so the s.e. of an IS mean is about 0.6-1.1 bp; after a cost of about 1.5 bp (spread about 0.7 bp, allowance 0.5 bp, the rest the round trip's own spread paid by the ask / bid fills) an IS drift above about +3 bp a slot would be visible.
"""
import os, sys, json
os.environ["ROUND_DATA"] = "mt5broker"; os.environ["ROUND_FILLS"] = "ask"
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import round321_long_bias_bold_play as R

R.MT5BROKER_SYMBOL.update({"XAU": "XAUUSD"})
SLIP = 0.5; IS_END = pd.Timestamp("2023-12-31"); MIN_IS = 400


def slot_trades():
    b = R._mt5broker_bars("XAU"); b = b[b.index.dayofweek < 5]
    day = b.index.normalize(); slot = (b.index.hour * 2 + b.index.minute // 30)
    g = b.groupby([day, slot])
    n = g.c.count(); first_o = g.o.first(); first_ao = g.ao.first(); last_c = g.c.last(); last_ac = g.ac.last()
    full = n == 30
    df = pd.DataFrame({"o": first_o, "ao": first_ao, "c": last_c, "ac": last_ac})[full]
    df["long"] = (df.c / df.ao - 1) * 1e4 - SLIP
    df["short"] = (df.o / df.ac - 1) * 1e4 - SLIP
    df = df.reset_index(); df.columns = ["date", "slot", "o", "ao", "c", "ac", "long", "short"]
    return df


def main(dry):
    df = slot_trades(); rng = np.random.default_rng(339); res = []
    for s in sorted(df.slot.unique()):
        x = df[df.slot == s]; a, b = x[x.date <= IS_END], x[x.date > IS_END]
        if len(a) < MIN_IS:
            if dry: print(f"slot {s // 2:02d}:{30 * (s % 2):02d} dropped (IS days {len(a)})")
            continue
        if dry:
            print(f"slot {s // 2:02d}:{30 * (s % 2):02d}: IS {len(a)} OOS {len(b)}"); continue
        for d in ("long", "short"):
            va, vb = a[d].values, b[d].values
            ma = va[rng.integers(0, len(va), (2000, len(va)))].mean(1); mb = vb[rng.integers(0, len(vb), (2000, len(vb)))].mean(1)
            res.append(dict(slot=f"{s // 2:02d}:{30 * (s % 2):02d}", dir=d, n_is=len(va), n_oos=len(vb), is_net=float(va.mean()), p_is=float((ma <= 0).mean()), oos_net=float(vb.mean()), oos_P=float((mb > 0).mean())))
    if dry: return
    r = pd.DataFrame(res).sort_values("p_is").reset_index(drop=True); m = len(r)
    ok = r.p_is.values <= (np.arange(1, m + 1) / m) * 0.10; k = int(np.flatnonzero(ok).max() + 1) if ok.any() else 0
    r["bh"] = False
    if k: r.loc[:k - 1, "bh"] = True
    r["cand"] = False
    for i in range(k):
        q = r.iloc[i]; o_ = r[(r.slot == q.slot) & (r.dir != q.dir)]
        r.loc[i, "cand"] = bool(q.oos_net >= 1.0 and q.oos_P >= .99 and len(o_) and float(o_.oos_net.iloc[0]) <= 0)
    print(f"hypotheses m={m}; BH survivors in IS: {k}; candidates: {int(r.cand.sum())}"); print(r.head(12).round(3).to_string())
    print("mean IS net %.2f, mean OOS net %.2f; LBMA slots:" % (r.is_net.mean(), r.oos_net.mean())); print(r[r.slot.isin(["05:30", "10:00"])].round(2).to_string())
    r.to_csv(os.path.join(HERE, "round339_grid.csv"), index=False)
    json.dump(dict(m=m, bh=k, candidates=int(r.cand.sum()), mean_is_net=float(r.is_net.mean()), mean_oos_net=float(r.oos_net.mean())), open(os.path.join(HERE, "round339_results_mt5broker_ask.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
