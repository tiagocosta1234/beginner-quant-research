"""Round 347g -- Dutchy's "ATH / OTE / STDV" routine (youtube M6rIs6kR7wQ, 2026-10-06) turned into fixed rules and run through the test rules.  (the trader: "do that")

WHAT THE VIDEO SHOWS (frames + auto-generated captions): NQ1! on 5 and 15 minute charts, New York time. A purple box marks an overnight range; standard-deviation levels (-1.5 .. -4.5) are projected beyond
it; horizontal markers at [18:00], [00:00], [9:30], [10:00]; after price taps a deviation level he waits for a break of structure, draws a fib on the displacement leg and enters at 0.5 / 0.62 / 0.705 / 0.79
with a tight stop, aiming at the next liquidity. Every example is hindsight-picked and every judgment (which range, which leg, "high risk" vs "lower risk") is discretionary.
THIS MODULE IS MY MECHANICAL READING OF THAT, NOT HIS RULES. The anchor of his deviation scale is not fully readable on screen; I chose the overnight range below. Everything here was FIXED BEFORE ANY RESULT
WAS LOOKED AT. Nothing is tuned: the grid below is reported in full and the primary spec is declared now.

CLOCK     MT5 broker server time = New York time + 7 h all year (the data's daily break sits at NY 17:00-18:00 in winter and summer; checked in selftest). Everything below is New York time.
RANGE     accumulation range of trading day D = high / low of the MID price over NY 18:00 (D-1) .. 00:00 (D); R = high - low. Days with R < 0.10% of the midnight price are skipped.
TAP       between 00:00 and 11:00 on 5-minute MID bars, the first bar whose low <= range low - k R (a long setup) or whose high >= range high + k R (a short setup). The first tap decides the side for the day;
          a bar that taps both sides skips the day.  k = 2.0 primary (the first level he names), 1.5 and 2.5 in the grid.
STRUCTURE after a long tap (shorts are the mirror image): the running low since the tap is the leg low LL. The structure high S is the latest 5-minute swing high (higher than the 2 bars on each side, so it is
          confirmed 2 bars later) that precedes the leg-low bar; with none, the highest high of the 6 bars before it. A 5-minute bar that CLOSES above S after the leg-low bar is the break of structure
          (decided at that close, nothing later). The leg high LH is the highest mid price from the leg low onward, updated every minute until the order fills.
ENTRY     a limit order at LH - f (LH - LL) from the first minute after the break; a long fills when the ASK low touches it (at the level, or at the open if the minute gapped through it), a short when the
          BID high touches it. If a new low under LL prints before the fill, the setup is void and the scan resumes from that bar (a later break of structure can re-arm it). No fills after 11:00.
          One trade per day.  f = 0.62 primary, 0.5 and 0.79 in the grid.
STOP      at LL (mirror: at LH), but never closer than 0.05% of the entry price. The stop is hit on the BID low for a long / ASK high for a short, entry minute included (conservative); filled at the stop,
          or at the open of a minute that gapped through it.
TARGET    entry + m x stop distance (m = 2 primary, 1 in the grid), filled at the target or better at a gap, never in the entry minute; if stop and target are both in one minute the stop wins.
TIME      anything still open is closed at the first minute at or after NY 16:00 at the bid (long) / ask (short) open.
SIZE      the stop distance risks r% of $100K (not compounded); r is swept 0.1 .. 3%, never fitted per trade. Costs: the real bid / ask of MT5 broker's 1-minute files; no commission on the cash indices.
GRID      3 symbols (US100.cash, US500.cash, US30.cash) x k {1.5, 2, 2.5} x f {0.5, 0.62, 0.79} x m {1, 2} = 54 runs. The best of 54 flatters: read the whole table, not the maximum.
NULL      for every real trade, the same entry minute (entered at that minute's open), the same stop distance and the same reward multiple, but a COIN-FLIP SIDE: whatever it earns is spread, the stop / target
          geometry and luck, not information in the tap -> structure -> retracement logic. 50 seeds.

  python -m mt5broker.ea_batch.ote_stdv_eval --selftest
  python -m mt5broker.ea_batch.ote_stdv_eval --grid               # trade statistics of all 54 runs
  python -m mt5broker.ea_batch.ote_stdv_eval --primary            # the rule-set evaluation + the null of the primary spec
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_batch import trendline_eval as T

HERE = Path(__file__).resolve().parent
INDEX = ("US100.cash", "US500.cash", "US30.cash")
for _s in INDEX:
    T.SYMBOLS[_s] = (f"{_s}_M1_ticks_full.parquet", lambda p: 1.0, 0.0, "B")
NY_OFFSET_MIN = 7 * 60
MIN_RANGE, MIN_STOP = 0.0010, 0.0005
START, END = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-09-30")


class Data:
    """One symbol's minute arrays in the 'long' frame (sign +1) and the mirrored frame (sign -1: prices negated, bid and ask swap roles), so one long-only core serves both sides."""

    def __init__(self, sym: str, m1: pd.DataFrame | None = None, through: float = 0.0):
        self.sym = sym
        self.through = through                                                                    # price units a limit must trade THROUGH to fill (futures bars have no bid / ask)
        self.m1 = T.load_m1(sym) if m1 is None else m1
        m = self.m1
        self.nym = m.index.values.astype("datetime64[m]").astype(np.int64) - NY_OFFSET_MIN
        bo, bh, bl, bc = (m[c].values for c in ("open", "high", "low", "close"))
        ao, ah, al, ac = (m[c].values for c in ("ask_open", "ask_high", "ask_low", "ask_close"))
        mh, ml, mc = (bh + ah) / 2, (bl + al) / 2, (bc + ac) / 2
        self.A = {1: dict(bo=bo, bh=bh, bl=bl, ao=ao, al=al, mh=mh, ml=ml, mc=mc),
                  -1: dict(bo=-ao, bh=-al, bl=-ah, ao=-bo, al=-bh, mh=-ml, ml=-mh, mc=-mc)}
        d = self.nym // 1440
        self.days = [int(x) for x in np.unique(d) if (int(x) + 3) % 7 < 5                        # Monday .. Friday (1970-01-01 was a Thursday)
                     and START <= pd.Timestamp(int(x) * 86400, unit="s") <= END]

    def ix(self, minute_of_epoch: int) -> int:
        return int(np.searchsorted(self.nym, minute_of_epoch))

    def run_exit(self, s: int, i0: int, pe: float, stop: float, target: float, c: int):
        """Exit scan in the frame of sign s (long logic). Returns (exit index, exit price)."""
        A = self.A[s]; n = len(self.nym)
        seg = slice(i0, max(c, i0 + 1))
        sh = A["bl"][seg] <= stop
        th = A["bh"][seg] >= target + self.through
        th[0] = False                                                                             # no target in the entry minute
        js = int(np.argmax(sh)) if sh.any() else None
        jt = int(np.argmax(th)) if th.any() else None
        if js is not None and (jt is None or js <= jt):
            return i0 + js, (stop if js == 0 else min(stop, A["bo"][i0 + js]))
        if jt is not None:
            return i0 + jt, max(target, A["bo"][i0 + jt])
        x = c if c < n else n - 1
        return x, A["bo"][x]

    def day_trade(self, d: int, k: float, f: float, mult: float, trunc: int | None = None):
        nym = self.nym
        a0, a1, b1, c = (self.ix(x) for x in ((d - 1) * 1440 + 1080, d * 1440, d * 1440 + 660, d * 1440 + 960))
        if trunc is not None:
            b1 = min(b1, trunc); c = min(c, trunc)
        if a1 - a0 < 60 or b1 - a1 < 15 or (trunc is None and c <= b1):
            return None
        A1 = self.A[1]
        H, L = A1["mh"][a0:a1].max(), A1["ml"][a0:a1].min()
        R = H - L
        if R < MIN_RANGE * A1["mc"][a1 - 1]:
            return None
        key = nym[a1:b1] // 5
        st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]); en = np.r_[st[1:], b1 - a1]
        nb = len(st)
        B = {}
        for s in (1, -1):
            A = self.A[s]
            B[s] = (np.maximum.reduceat(A["mh"][a1:b1], st), np.minimum.reduceat(A["ml"][a1:b1], st), A["mc"][a1:b1][en - 1])
        lvl = {1: L - k * R, -1: -(H + k * R)}
        tap = {}
        for s in (1, -1):
            hit = np.flatnonzero(B[s][1] <= lvl[s]); tap[s] = int(hit[0]) if len(hit) else None
        if tap[1] is None and tap[-1] is None:
            return None
        if tap[1] is not None and tap[-1] is not None:
            if tap[1] == tap[-1]:
                return None
            s = 1 if tap[1] < tap[-1] else -1
        else:
            s = 1 if tap[-1] is None else -1
        bh5, bl5, bc5 = B[s]; A = self.A[s]; t0 = tap[s]
        t = t0
        while t < nb - 1:
            jl = t0 + int(np.argmin(bl5[t0:t + 1])); ll = bl5[jl]
            S = None
            for j in range(min(jl - 1, t - 2), 1, -1):
                if bh5[j] > max(bh5[j - 2], bh5[j - 1], bh5[j + 1], bh5[j + 2]):
                    S = bh5[j]; break
            if S is None:
                S = bh5[max(0, jl - 6):jl + 1].max()
            if t > jl and bc5[t] > S:                                                              # break of structure at the close of bar t
                lh = bh5[jl:t + 1].max()
                q, fill, void = a1 + int(en[t]), None, False
                while q < b1:
                    level = lh - f * (lh - ll)
                    if A["al"][q] <= level - self.through:
                        fill = q; pe = min(level, A["ao"][q]); break
                    if A["ml"][q] < ll:                                                            # a new low under the leg: setup void, rescan from this bar
                        t = int(np.searchsorted(st, q - a1, side="right")) - 1; void = True; break
                    lh = max(lh, A["mh"][q]); q += 1
                if void:
                    continue
                if fill is None:
                    return None
                stop = min(ll, pe - MIN_STOP * abs(pe)); dist = pe - stop
                ix, px = self.run_exit(s, fill, pe, stop, pe + mult * dist, c)
                lots = T.RISK_REF / dist
                spr = 0.5 * ((self.m1.ask_open.values[fill] - self.m1.open.values[fill]) + (self.m1.ask_open.values[ix] - self.m1.open.values[ix])) * lots
                return dict(i0=fill, i1=ix, side=s, pe=s * pe, px=s * px, lots=lots, k=1.0, gross=(px - pe) * lots, comm=0.0, spread=spr, dist=dist, c=c, tap=t0, day=d)
            t += 1
        return None

    def simulate(self, k: float, f: float, mult: float):
        rows = [r for r in (self.day_trade(d, k, f, mult) for d in self.days) if r is not None]
        return pd.DataFrame(rows)

    def null(self, ref: pd.DataFrame, mult: float, rng):
        """Same entry minutes, stop distances and reward multiple as ref; the side is a coin flip, entry at that minute's open."""
        rows = []
        for r in ref.itertuples():
            s = 1 if rng.random() < 0.5 else -1
            A = self.A[s]
            pe = A["ao"][r.i0]; stop = pe - r.dist
            ix, px = self.run_exit(s, r.i0, pe, stop, pe + mult * r.dist, r.c)
            lots = T.RISK_REF / r.dist
            spr = 0.5 * ((self.m1.ask_open.values[r.i0] - self.m1.open.values[r.i0]) + (self.m1.ask_open.values[ix] - self.m1.open.values[ix])) * lots
            rows.append(dict(i0=r.i0, i1=ix, side=s, pe=s * pe, px=s * px, lots=lots, k=1.0, gross=(px - pe) * lots, comm=0.0, spread=spr, dist=r.dist, c=r.c, tap=r.tap, day=r.day))
        return pd.DataFrame(rows)


def selftest():
    D = Data("US100.cash")
    ny = pd.DatetimeIndex(D.nym.astype("datetime64[m]"))
    for day in ("2026-01-13", "2026-07-14", "2025-03-12", "2025-04-02"):
        x = ny[(ny >= day) & (ny < pd.Timestamp(day) + pd.Timedelta(days=1))]
        gap = np.flatnonzero(np.diff(x.values.astype("datetime64[m]").astype(np.int64)) > 5)
        print(f"{day}: NY-clock first {x.min().strftime('%H:%M')} last {x.max().strftime('%H:%M')}; gaps > 5 min start at {[x[g].strftime('%H:%M') + '->' + x[g + 1].strftime('%H:%M') for g in gap]}")
    tr = D.simulate(2.0, 0.62, 2.0)
    v, m, ent = T.day_frames(tr, D.m1)
    print(f"US100 primary: {len(tr)} trades; sum of daily v {v.sum():.2f} vs trades' net {tr.gross.sum():.2f}; days with m > v: {int((m > v + 1e-9).sum())}")
    # causality: the entry must not change when every minute after the fill is removed from the day
    bad = 0
    for r in tr.sample(min(150, len(tr)), random_state=0).itertuples():
        q = D.day_trade(r.day, 2.0, 0.62, 2.0, trunc=r.i0 + 1)
        if q is None or q["i0"] != r.i0 or abs(abs(q["pe"]) - abs(r.pe)) > 1e-9 or q["side"] != r.side:
            bad += 1
    print(f"causality: {bad} of {min(150, len(tr))} sampled entries changed when the data after the fill minute was removed (must be 0)")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--selftest", action="store_true"); ap.add_argument("--grid", action="store_true"); ap.add_argument("--primary", action="store_true")
    ap.add_argument("--seeds", type=int, default=50)
    a = ap.parse_args(argv)
    if a.selftest:
        selftest(); return
    if a.grid:
        rows = []
        for sym in INDEX:
            D = Data(sym)
            for k, f, mult in itertools.product((1.5, 2.0, 2.5), (0.5, 0.62, 0.79), (1.0, 2.0)):
                tr = D.simulate(k, f, mult)
                if tr.empty:
                    rows.append(dict(symbol=sym, k=k, f=f, m=mult, trades=0)); continue
                v, m, ent = T.day_frames(tr, D.m1)
                ts = T.trade_stats(tr, v); R = (tr.gross - 2 * tr.comm) / T.RISK_REF
                ts.update(symbol=sym, k=k, f=f, m=mult, avg_stop_pct=float((tr.dist / tr.pe.abs()).mean() * 100), long_share=float((tr.side == 1).mean()), worst_day_pct_at_1pct=float(m.min() / T.INITIAL * 100))
                rows.append(ts)
                print(f"{sym} k={k} f={f} m={mult:g}: {ts['trades']} trades ({ts['per_year']:.0f}/yr, long {ts['long_share']:.0%}) win {ts['win_pct']:.0f}% meanR {ts['mean_R']:+.3f} (t {ts['t_stat']:+.1f}, pre-cost {ts['mean_R_before_costs']:+.3f}, cost {ts['cost_R']:.3f}R) PF {ts['profit_factor']:.2f} stop {ts['avg_stop_pct']:.2f}%", flush=True)
        pd.DataFrame(rows).to_csv(HERE / "ote_stdv_grid.csv", index=False)
        return
    if a.primary:
        W = T.windows("B"); out = []
        for sym in INDEX:
            D = Data(sym); tr = D.simulate(2.0, 0.62, 2.0)
            v, m, ent = T.day_frames(tr, D.m1); ts = T.trade_stats(tr, v)
            print(f"\n{sym} PRIMARY (k=2, f=0.62, m=2): {ts['trades']} trades ({ts['per_year']:.0f}/yr) win {ts['win_pct']:.0f}% meanR {ts['mean_R']:+.3f} (t {ts['t_stat']:+.1f}) PF {ts['profit_factor']:.2f}; worst intraday equity day at 1% risk {m.min() / T.INITIAL * 100:.1f}%", flush=True)
            ev = T.evaluate(v, m, ent, W); ev.insert(0, "kind", "real"); ev.insert(0, "symbol", sym); out.append(ev)
            for H in T.HORIZONS:
                e = ev[ev.horizon == H].set_index("rule")
                print(f"  within {H:>2} days: " + " | ".join(f"{r} {e.loc[r, 'pass_pct']:.0f}% (breach {e.loc[r, 'breach_pct']:.0f}%, r={e.loc[r, 'best_risk_pct']}%; leave-1-yr-out {e.loc[r, 'loyo_pass_pct']:.0f}%)" for r in e.index if pd.notna(e.loc[r, 'pass_pct'])), flush=True)
            rs, evs = [], []
            for seed in range(a.seeds):
                nt = D.null(tr, 2.0, np.random.default_rng(seed)); nv, nm, nen = T.day_frames(nt, D.m1)
                rs.append(float(((nt.gross) / T.RISK_REF).mean()))
                if seed < 10:
                    e = T.evaluate(nv, nm, nen, W); e["seed"] = seed; evs.append(e)
            e = pd.concat(evs); e["kind"] = "null"; e["symbol"] = sym; out.append(e)
            e86 = e[e.horizon == 86].groupby("rule")[["pass_pct", "loyo_pass_pct"]].mean()
            e30 = e[e.horizon == 30].groupby("rule")[["pass_pct", "loyo_pass_pct"]].mean()
            print(f"  NULL ({a.seeds} coin-flip-side runs): mean R {np.mean(rs):+.3f} (5th..95th pct {np.percentile(rs, 5):+.3f}..{np.percentile(rs, 95):+.3f}; real {ts['mean_R']:+.3f} -> beats {np.mean(np.array(rs) < ts['mean_R']):.0%} of null runs)", flush=True)
            print("  NULL pass in-sample / leave-1-yr-out (mean of 10 seeds), 30 days: " + ", ".join(f"{r} {e30.loc[r, 'pass_pct']:.0f}/{e30.loc[r, 'loyo_pass_pct']:.0f}%" for r in e30.index) + " | Dec31: " + ", ".join(f"{r} {e86.loc[r, 'pass_pct']:.0f}/{e86.loc[r, 'loyo_pass_pct']:.0f}%" for r in e86.index), flush=True)
        pd.concat(out).to_csv(HERE / "ote_stdv_primary.csv", index=False)


if __name__ == "__main__":
    main()
