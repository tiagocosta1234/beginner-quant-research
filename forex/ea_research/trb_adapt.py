"""TRB-ADAPT (2026-10-15, the trader: "on 2024 a type of breakout, on 2025 a better one, 2026 the same - the markets never stay the same,
we're the ones that need to adapt"). Tests ADAPTATION itself on the 2,808-variant breakout grid of 46 MT5, 2022-01..2026-10-02
(2026 already open for breakouts). Diagnostic, not a new candidate unless one speed is positive in every year 2023-2026.
   1. the prize: each year's best variant per market, chosen with hindsight
   2. persistence: rank correlation across variants between the last L months and the next month (L = 1, 3, 6, 12)
   3. the adaptive trader: each month, per market, trade the best variant of the last L months (and the average of the top 20)
   python -m forex.ea_research.trb_adapt"""
import numpy as np
import pandas as pd

from forex.ea_research import trb
from forex.ea_research.trb_best import CACHE26

LS = (1, 3, 6, 12)
YEARS = (2023, 2024, 2025, 2026)


def monthly(sym):
    z = np.load(CACHE26 / f"{sym}.npz")
    days = pd.to_datetime(z["days"], unit="s")
    R = z["R"].reshape(len(days), -1).astype(np.float64)
    mon = days.to_period("M")
    months = pd.period_range("2022-01", "2026-10", freq="M")
    tot = np.zeros((len(months), R.shape[1]))
    cnt = np.zeros_like(tot)
    for i, m in enumerate(months):
        x = R[mon == m]
        tot[i], cnt[i] = np.nansum(x, 0), np.sum(~np.isnan(x), 0)
    return months, tot, cnt


def rankcorr(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 50:
        return np.nan
    ra, rb = pd.Series(a[ok]).rank().to_numpy(), pd.Series(b[ok]).rank().to_numpy()
    return np.corrcoef(ra, rb)[0, 1]


def main():
    prize, corr, trades = [], {L: [] for L in LS}, []
    for s in trb.SYMS:
        months, tot, cnt = monthly(s)
        yr = months.year
        for y in (2022, 2023, 2024, 2025, 2026):
            n, t = cnt[yr == y].sum(0), tot[yr == y].sum(0)
            ok = n >= (100 if y < 2026 else 75)
            if ok.any():
                prize.append(dict(sym=s, year=y, best_R=(t[ok] / n[ok]).max()))
        for i, m in enumerate(months):
            if m.year < 2023:
                continue
            nxt = np.where(cnt[i] > 0, tot[i] / np.maximum(cnt[i], 1), np.nan)
            for L in LS:
                lt, ln = tot[i - L:i].sum(0), cnt[i - L:i].sum(0)
                score = np.where(ln >= max(8, 4 * L), lt, np.nan)
                corr[L].append(rankcorr(np.where(np.isfinite(score), lt / np.maximum(ln, 1), np.nan), nxt))
                if np.all(np.isnan(score)):
                    continue
                order = np.argsort(np.where(np.isnan(score), -np.inf, score))[::-1]
                best = order[0]
                top = [c for c in order[:20] if np.isfinite(score[c])]
                trades.append(dict(sym=s, month=m, year=m.year, L=L, kind="best", R=tot[i, best], n=cnt[i, best]))
                trades.append(dict(sym=s, month=m, year=m.year, L=L, kind="top20", R=tot[i, top].sum() / 20, n=cnt[i, top].sum() / 20))
    P = pd.DataFrame(prize)
    print("1. THE PRIZE - each year's best variant per market, chosen WITH HINDSIGHT (mean over markets, R per trade):")
    print("   " + " | ".join(f"{y}: {P[P.year == y].best_R.mean():+.3f}" for y in (2022, 2023, 2024, 2025, 2026)))
    print("\n2. PERSISTENCE - rank correlation across the 2,808 variants between the last L months and the next month (mean over markets x months):")
    print("   " + " | ".join(f"L={L}m: {np.nanmean(corr[L]):+.4f}" for L in LS) + "   (0 = recent results say nothing about next month)")
    T = pd.DataFrame(trades)
    print("\n3. THE ADAPTIVE TRADER - re-pick every month on the last L months, trade the next month (R per trade, all markets pooled):")
    rows = []
    for (kind, L), g in T.groupby(["kind", "L"]):
        r = dict(rule=f"{kind} of last {L}m")
        for y in YEARS:
            x = g[g.year == y]
            r[str(y)] = x.R.sum() / max(x.n.sum(), 1)
        mm = g.groupby("month").apply(lambda x: x.R.sum() / max(x.n.sum(), 1), include_groups=False)
        r["months positive"] = f"{(mm > 0).sum()}/{len(mm)}"
        r["$ at 1k/trade, 2023-26"] = g.R.sum() * 1000
        rows.append(r)
    A = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(A.round(3).to_string(index=False))
    A.to_csv("data/si_ledgers/TRB_ADAPT.csv", index=False)


if __name__ == "__main__":
    main()
