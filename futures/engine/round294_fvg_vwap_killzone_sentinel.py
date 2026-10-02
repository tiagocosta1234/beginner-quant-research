"""
Round 294 (2026-10-02, PRE-REGISTERED): the trader's "BrokerAPI: FVG + VWAP Killzone Sentinel" Pine indicator -- as written, and with every parameter tweaked.
the trader: "check the following code, understand the logic behind it and try to tweak every single parameter you can think of in the trading to refine it, you can only stop once you're making
average 5000$ per month and a max drawdown not exceeding 50%."

WHAT THE SCRIPT DOES (read from the code; it is an INDICATOR: it draws boxes and fires alerts, it places no orders and has no exit logic):
  * Killzones: bars whose start time is 09:30-11:30 or 13:30-15:30 New York.
  * VWAP: sum(hlc3 x volume) / sum(volume), reset on each new daily bar (for CME futures that is 18:00 New York, so it includes the overnight session).
  * Fair value gap on the chart timeframe: bullish when low[0] > high[2] and the middle candle closed up; bearish mirrored. Gap = [high[2], low[0]]; the "structural" stop is low[2].
  * Only the LATEST gap per direction is tracked (a new gap overwrites the old one). On the first later bar whose low touches the top of a bullish gap the gap is cleared, and IF that bar
    is inside a killzone AND closes above the VWAP, a long setup is drawn: entry = that bar's close, stop = low[2] of the gap, target = entry + (entry - stop), i.e. 1:1. Shorts mirrored.
QUIRKS FOUND (not changed in the as-written test unless stated): (1) nothing checks that the entry is on the right side of the stop -- a bar that touches the gap and closes BELOW low[2] still
fires a "long" whose stop is above the entry and whose target is below it; here such setups are skipped (stop distance under 4 ticks, or the fill at or beyond the stop). (2) The gap is cleared on the
first touch even when the filters block the signal, so each gap gives at most one chance. (3) The timeframe is whatever the chart is on; the script does not say. (4) There is no size, no exit, no
"one trade at a time" and no end-of-day flat; those are added here (below). (5) State is carried across the 17:00-18:00 break in the script; here a gap does not survive the break and no gap is
detected across it (with only the latest gap tracked this changes almost nothing -- the dry run counts it -- and it keeps weekend and contract-roll gaps out).

STEP 0, BEFORE ANY RESULT (ledger k = 1074). This idea class has been tested: plain FVG retests and FVG + displacement + VWAP side + killzone + 50% entry on MNQ/MGC (Round 150, rows 184-187), FVG
exits chosen in-sample (153), the "5 secrets" (189), OTE + FVG (76, 201), order blocks / Silver Bullet (159), their inversions (160), and yesterday's mechanical FVG retest on MT5 M1 (290): no edge
in any of them. PASS-SPEED SCREEN: a 1:1 bracket that costs 0.03-0.10R needs a 52-55% win rate to break even; nothing in that family has shown it. The honest expectation is no edge as written, and
that a large parameter search will find many in-sample winners that do not hold out of sample. THIS IS NOT an "iterate until it passes" search (CURRENT_STATE.md rejects that framing): it is ONE
pre-registered search over a fixed grid, judged ONCE on data the selection never saw. If the goal is not met out of sample the round stops and says so; the grid is not re-tuned against the test windows.

DATA. Databento 1-minute continuous front-month futures, NQ, ES, GC (full-size contracts), start-stamped UTC bars, 24 hours; trading days 2019-10-01 .. 2026-09-25 on the 18:00 New York session clock
(a trading day = 18:00 -> 17:00). Contract rolls show up as a jump between two consecutive minutes at 00:00 UTC; every such jump of >= 0.10% of price is removed by back-adjusting earlier prices
(the dry run lists them). Prices are held as integer ticks. Costs: $1.24 commission + 2 ticks of slippage per contract round trip (the repo's convention: NQ $11.24, ES $26.24, GC $21.24),
charged on every trade whatever the order type.

THE BACKTEST ENGINE (applies to every cell). Signals on N-minute candles built on the session clock; fills and exits resolved on the 1-minute bars.
  ENTRY, "close" mode (the script's): the first candle after the gap's candle that reaches the mitigation level, if no newer same-direction gap has formed first; the signal is known at that candle's
    close, the fill is the next 1-minute bar's open; the planned entry (for the bracket) is the candle's close. "limit" mode: a resting limit at the mitigation level from the moment the gap's candle
    closes until a newer same-direction gap's candle closes or the session ends; filled on the first 1-minute bar that trades one tick THROUGH the level, at the level (or at the open if it gaps through).
    Mitigation level = the gap's near edge moved into the gap by DEPTH x gap (0 = near edge as written, 0.5 = midpoint, 1 = far edge).
  STOP: "struct" (as written: the first candle's low/high), "gap" (one tick beyond the gap's far edge), "atr" (1 x the 14-candle average range at the gap's candle). A setup needs a stop distance of
    at least 4 ticks and a fill on the right side of the stop.
  TARGET: R multiples 0.5, 1 (as written), 1.5, 2, 3, or none. TIME STOP: none, or 60 one-minute bars. Everything is flat at 15:55 New York (BrokerAPI's flat rule), no entries from 15:50; an entry in
    the evening can be held to 15:55 of that trading day.
  ORDER OF EVENTS inside a 1-minute bar: the stop is assumed to be hit before the target; on a limit order's fill bar the stop counts if the bar's low reaches it and the target only if the bar CLOSES beyond it.
  INVERTED mode: the same entry taken the other way, with the stop at the original target and the target at the original stop (ties count as a loss for the inverted trade too).
  EVERY SIGNAL IS TAKEN at a fixed risk of 1R (positions may overlap; P&L is additive, so this equals trading the net position, with costs counted per signal). P&L is in R: (exit - fill) / planned stop
    distance, minus the cost in R (cost in ticks / stop distance in ticks). One-position-at-a-time is reported for the as-written cells only (descriptive).

THE GRID ("every parameter"): instrument (NQ, ES, GC) x candle (1, 2, 3, 5, 15 min) x depth (0, 0.5, 1) x entry mode (close, limit) x stop (struct, gap, atr) x target (0.5, 1, 1.5, 2, 3, none)
  x time stop (none, 60 min) x direction of the bet (normal, inverted; no inverted without a target) = 5,940 blocks, each crossed with the FILTERS:
  killzone (as written 09:30-11:30 + 13:30-15:30; AM only; PM only; all RTH 09:30-15:50; London 02:00-05:00; London + as written; all hours) x VWAP (aligned as written; off; against)
  x minimum gap size (0; 0.25; 0.5; 1.0 x the 14-candle average range) x maximum gap age at entry (any; <= 60; <= 15 candles) x side (both; long only; short only)
  x maximum cost (any; <= 0.20R; <= 0.10R; <= 0.05R, i.e. a minimum stop size) = 3,024 filter combinations. TOTAL 17,962,560 parameter sets (16,964,640 non-empty, see POWER_NOTES). The filters are applied to the SIGNALS of the as-written
  gap tracking (a filtered-out gap still occupies the "latest gap" slot and is still consumed by its first touch), so each block's trades are computed once and filtered.

WHAT "WORKS" MEANS, AND HOW IT IS JUDGED. The calendar is cut into 14 half-years (boundaries 1 April / 1 October).
  (1) AS WRITTEN: killzone as written, VWAP aligned, no size/age/cost filter, both sides, close entry at depth 0, struct stop, 1:1, no time stop, on each instrument x candle = 15 cells
      (ledger rows 1075-1089), whole sample, IS = 2019-10 .. 2024-03, OOS = 2024-04 .. 2026-09.
  (2) WALK-FORWARD (the honest version of "tweak until it works"): for each of the 10 test half-years from 2021-10 to 2026-09, the parameter set is chosen on the PREVIOUS 24 months only and then
      traded in the test half-year; the 10 test half-years are stitched into 60 months that the selection never saw. Selection score = mean / standard deviation of the daily net R over the 24 months,
      among parameter sets with a positive mean and enough trades. Six strategies (ledger rows 1090-1095):
        WF-BEST     the single best set (>= 200 trades in the 24 months);
        WF-ROBUST   the single best set with >= 1,000 trades in the 24 months;
        WF-TOP20    the 20 best sets (>= 200 trades), at most 2 per block, each at 1/20 of the risk;
        WF-NQ / WF-ES / WF-GC  the single best set of that instrument (>= 200 trades).
      For the ledger their "IS" is the stitched 2021-10 .. 2024-03 and "OOS" the stitched 2024-04 .. 2026-09.
  P(edge > 0): bootstrap of the daily net R over all trading days of the window (4,000 draws; 40,000 if >= 0.99). CANDIDATE (the repo's rule): net and before-cost mean > 0, IS P >= 0.95,
      OOS P >= 1 - 0.01/k (k = 1,095). Ledger k = 1074 + 21 = 1095.
  MANUAL'S GOAL, in R so that the dollar size is free: sized so that the average month makes $5,000, the worst peak-to-trough loss must be <= $50,000 (50% of a $100K account), i.e.
      max drawdown in R <= 10 x the average monthly net R (and the average month must be positive). A strategy MEETS THE GOAL OUT OF SAMPLE only if this holds on its out-of-sample series (the 60
      stitched months for the walk-forward strategies; the whole 84 months for the as-written cells, where nothing is fitted) AND it is a candidate (otherwise the numbers are not distinguishable from luck).
  DESCRIPTIVE (not a test): how many of the parameter sets meet the goal numbers IN SAMPLE on the full 84 months (>= 500 trades) -- that is what parameter tweaking in a strategy tester shows; the best
      in-sample set; whether first-half (2019-10 .. 2023-03) performance carries into the second half (2023-04 .. 2026-09) across sets: the share profitable in each half and in both, the rank correlation
      of the net daily Sharpe and of the BEFORE-COST R per trade (the net one is positive from costs alone: an expensive set loses in both halves), and the fate of the 1,000 best first-half sets;
      one-parameter-at-a-time changes from the as-written cell.
  PLACEBO (run BEFORE this pre-registration was committed: `--placebo`, results in round294_placebo.json): the identical pipeline with every gap's before-cost R multiplied by a random sign (one sign per
      gap, shared by every trade that gap produces in every block; costs unchanged) -- a world with no edge anywhere but the same trades, magnitudes and costs. It is the yardstick for the real run.
POWER_NOTES (dry run and placebo, before any real result; the dry run prints counts, costs and timings only):
  * FIDELITY: a literal bar-by-bar emulation of the Pine code (state carried across sessions, no validity checks) and the engine give IDENTICAL signal sets on all nine pairs checked (NQ, ES, GC at 1, 5 and
    15 minutes; e.g. NQ 1-min 30,513 signals, none in only one of the two), so dropping gaps at the 17:00-18:00 break changes nothing. The vectorised engine equals an independent slow simulator on 8 blocks x
    6 random days for each of the 15 instrument-candle pairs: 34,388 trades compared, every field equal (entry bar, side, filter cell, net R).
  * DATA: roll jumps removed: NQ 17, ES 17, GC 25 (listed by the dry run); 1,824 calendar trading days, 1,803-1,807 with data per instrument.
  * AS-WRITTEN CELLS, valid setups over the 84 months and median cost per trade: NQ 29,566 / 15,448 / 10,645 / 6,635 / 2,491 at 1 / 2 / 3 / 5 / 15 min (0.039 / 0.027 / 0.022 / 0.017 / 0.010 R);
    ES 26,095 / 14,156 / 9,834 / 6,281 / 2,397 (0.150 / 0.110 / 0.087 / 0.070 / 0.041 R); GC 27,007 / 14,560 / 9,982 / 6,183 / 2,182 (0.163 / 0.118 / 0.092 / 0.071 / 0.038 R). Setups dropped by quirk (1)
    (stop on the wrong side or under 4 ticks): 1-3% on NQ, 2-8% on ES, 2-15% on GC. A 1:1 bracket that costs c needs a win rate of (1 + c) / 2 to break even: 50.5-52% on NQ, 52-57.5% on ES, 52-58% on GC.
  * POWER: with 2,200-29,600 trades per as-written cell the standard error of the mean is ~0.006-0.021R per trade before day clustering; the out-of-sample bar (P >= 0.99999, z ~ 4.3) on 30 months needs
    roughly 0.04R (NQ 1-min) to 0.15R (15-min) per trade.
  * GRID: 330 of the 5,940 blocks are empty (an entry at the gap's far edge with a stop one tick beyond it is under the 4-tick minimum), leaving 5,610 blocks = 16,964,640 parameter sets. A full run takes
    ~12 minutes on 8 processes.
  * WHAT THE GOAL MEANS: for a strategy with independent daily returns, "max drawdown <= 10 months of average profit" over 5-7 years is met about half the time at an annualised Sharpe of 1.5 and 87% of the
    time at 2.0 (0.0-0.3% at Sharpe 0, 1-3% at 0.5, 13-21% at 1.0): the goal is a Sharpe of roughly 1.5-2 after costs.
  * PLACEBO (no edge anywhere; same trades and costs): the as-written cells lose their cost (before costs -0.02 to +0.03R, net -0.02 to -0.20R per trade); the six walk-forward strategies make -2.5 to +0.8R
    a month, none a candidate, none meeting the goal numbers. IN SAMPLE, 456,248 of the 10,062,974 sets with >= 500 trades are profitable (4.5%), 49 meet the goal numbers (3 at <= 5 months of profit), and
    the best shows +9.1R a month on 522 trades with a 44.7R drawdown, i.e. "$5,000 a month with a $24,621 max drawdown at $550 a trade" out of coin flips. Of 8,817,992 sets with >= 300 trades in each half,
    5.56% are profitable in the first half, 7.18% in the second and 1.20% in both; the rank correlation between the halves is +0.816 for the net daily Sharpe (a pure cost effect) and -0.003 for the
    before-cost R per trade; the 1,000 best first-half sets go from +1.7R a month (+0.175R per trade before costs) to -0.5R a month (-0.011R). The real run has to beat THESE numbers to mean anything.
"""
import os, sys, json, time, pickle, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):      # 8 worker processes: keep each one's linear algebra to 2 threads (speed only)
    os.environ.setdefault(_v, "2")
import numpy as np
import pandas as pd
from types import SimpleNamespace as NS

DB_DIR = os.path.join(HERE, "..", "data", "databento")
FILES = {"NQ": "futures_NQ.F_1m.parquet", "ES": "futures_ES.F_1m.parquet", "GC": "futures_GC.F_1m.parquet"}
SPECS = {"NQ": (20.0, 0.25), "ES": (50.0, 0.25), "GC": (100.0, 0.10)}   # point value, tick size (full-size CME contracts, as Round 171)
COMM = 1.24
SYMS = ("NQ", "ES", "GC")
TFS = (1, 2, 3, 5, 15)
DEPTHS = (0.0, 0.5, 1.0)
MODES = ("close", "limit")
STOPS = ("struct", "gap", "atr")
RRS = np.array([0.5, 1.0, 1.5, 2.0, 3.0])
NRR = len(RRS)
TS_BARS = 60
MIN_DIST = 4
CUT_S, FLAT_S = 1310, 1315                 # 15:50 and 15:55 New York on the 18:00 session clock
SEG_EDGES = np.array([0, 480, 660, 930, 1050, 1170, 1290])   # 18:00, 02:00, 05:00, 09:30, 11:30, 13:30, 15:30
CAL = pd.bdate_range("2019-10-01", "2026-09-25")
D = len(CAL)
SEG_BOUNDS = pd.DatetimeIndex([pd.Timestamp(2019 + (k + 1) // 2, 10 if k % 2 == 0 else 4, 1) for k in range(15)])
SEG_START = np.searchsorted(CAL.values, SEG_BOUNDS[:-1].values)
NSEG = len(SEG_START)
SEG_ND = np.diff(np.r_[SEG_START, D])
SEG_OF_DAY = np.searchsorted(SEG_START, np.arange(D), "right") - 1
NWIN, TRAIN_SEGS = 10, 4
H1_SEGS, OOS_SEG0 = 7, 9                   # halves split at 2023-04-01; ledger OOS starts 2024-04-01
MONTHS_ALL, MONTHS_HALF, MONTHS_SEG = 84.0, 42.0, 6.0
K_BASE, N_ROWS = 1074, 21
K_TOTAL = K_BASE + N_ROWS
BIG = np.iinfo(np.int64).max // 4

KZ_NAMES = ("as written 09:30-11:30+13:30-15:30", "AM 09:30-11:30", "PM 13:30-15:30", "RTH 09:30-15:50", "London 02:00-05:00", "London + as written", "all hours")
KZ = np.zeros((7, 7))
for _k, _s in enumerate([(3, 5), (3,), (5,), (3, 4, 5, 6), (1,), (1, 3, 5), (0, 1, 2, 3, 4, 5, 6)]):
    KZ[_k, list(_s)] = 1.0
VW_NAMES = ("VWAP aligned", "VWAP off", "against VWAP")
VW = np.array([[0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])
SZ_NAMES = ("gap any", "gap >= 0.25 ATR", "gap >= 0.5 ATR", "gap >= 1 ATR")
SZ = np.triu(np.ones((4, 4)))
AG_NAMES = ("age any", "age <= 60", "age <= 15")
AG = np.array([[1.0, 1.0, 1.0], [1.0, 1.0, 0.0], [1.0, 0.0, 0.0]])
DR_NAMES = ("both sides", "long only", "short only")
DR = np.array([[1.0, 1.0], [1.0, 0.0], [0.0, 1.0]])
CS_NAMES = ("cost any", "cost <= 0.20R", "cost <= 0.10R", "cost <= 0.05R")
CS = np.triu(np.ones((4, 4)))
CELL_SHAPE = (7, 2, 4, 3, 2, 4)
NCELL = int(np.prod(CELL_SHAPE))
CFG_SHAPE = (7, 3, 4, 3, 3, 4)
NCFG = int(np.prod(CFG_SHAPE))
NFIELD = 12          # totR, maxDD, ntr, sharpe, monthly_h1, sharpe_h1, monthly_h2, sharpe_h2, ntr_h1, ntr_h2, gross R per trade h1, gross R per trade h2


def cost_ticks(sym):
    pv, tick = SPECS[sym]
    return (COMM + 2 * tick * pv) / (pv * tick)


def cfg_name(c):
    k, v, s, a, d, p = np.unravel_index(int(c), CFG_SHAPE)
    return f"{KZ_NAMES[k]}; {VW_NAMES[v]}; {SZ_NAMES[s]}; {AG_NAMES[a]}; {DR_NAMES[d]}; {CS_NAMES[p]}"


def block_name(b):
    depth, mode, stop, q, ts, inv = b
    tgt = "no target" if q == NRR else f"{RRS[q]:g}R target"
    return f"{mode} entry at depth {depth:g}; {stop} stop; {tgt}; {'60-min time stop' if ts else 'no time stop'}; {'INVERTED' if inv else 'normal'}"


# ------------------------------------------------------------------ data
def load_1m(sym):
    pv, tick = SPECS[sym]
    df = pd.read_parquet(os.path.join(DB_DIR, FILES[sym]), columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values("ts", kind="stable").drop_duplicates("ts").reset_index(drop=True)
    tsv = df["ts"].values.astype("datetime64[ns]").astype(np.int64)
    px = {k: np.rint(df[k].values / tick).astype(np.int64) for k in ("open", "high", "low", "close")}
    mins = tsv // 60_000_000_000
    gap = px["open"][1:] - px["close"][:-1]
    roll = ((mins[1:] % 1440) == 0) & (np.diff(mins) == 1) & (np.abs(gap) >= 0.001 * px["close"][:-1])
    jump = np.zeros(len(tsv), np.int64)
    jump[1:][roll] = gap[roll]
    later = np.cumsum(jump[::-1])[::-1] - jump                 # the jumps strictly after each bar
    for k in px:
        px[k] = px[k] + later
    rolls = [(str(pd.Timestamp(t, unit="ns").date()), float(g * tick)) for t, g in zip(tsv[1:][roll], gap[roll])]
    ny = df["ts"].dt.tz_convert("America/New_York")
    nymin = (ny.dt.hour * 60 + ny.dt.minute).values
    tday = (ny.dt.tz_localize(None) + pd.Timedelta(hours=6)).dt.normalize()
    day = CAL.get_indexer(pd.DatetimeIndex(tday))
    sess = (nymin - 1080) % 1440
    keep = (day >= 0) & (sess < 1380)
    B = NS(sym=sym, pv=pv, tick=tick, o=px["open"][keep], h=px["high"][keep], l=px["low"][keep], c=px["close"][keep], v=df["volume"].values[keep].astype(float),
           sess=sess[keep].astype(np.int64), day=day[keep].astype(np.int64), rolls=rolls)
    B.n = len(B.o)
    assert np.all(np.diff(B.day) >= 0)
    B.d_first = np.searchsorted(B.day, np.arange(D), "left")
    B.d_last = np.searchsorted(B.day, np.arange(D), "right") - 1
    B.X = np.zeros(D, np.int64); B.pflat = np.zeros(D, np.int64)
    for dd in range(D):
        a, b = B.d_first[dd], B.d_last[dd]
        if b < a:
            continue
        w = np.flatnonzero(B.sess[a:b + 1] >= FLAT_S)
        if len(w):
            B.X[dd] = a + w[0]; B.pflat[dd] = B.o[a + w[0]]
        else:
            B.X[dd] = b + 1; B.pflat[dd] = B.c[b]
    return B


def tf_bars(B, tf):
    key = B.day * 2000 + B.sess // tf
    st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    en = np.r_[st[1:] - 1, B.n - 1]
    T = NS(tf=tf, i0=st, i1=en, O=B.o[st], C=B.c[en], H=np.maximum.reduceat(B.h, st), L=np.minimum.reduceat(B.l, st), V=np.add.reduceat(B.v, st),
           day=B.day[st], smin=(B.sess[st] // tf) * tf)
    m = T.m = len(st)
    pvv = (T.H + T.L + T.C) / 3.0 * T.V
    cpv, cv = np.cumsum(pvv), np.cumsum(T.V)
    dfirst = np.flatnonzero(np.r_[True, T.day[1:] != T.day[:-1]])
    base = np.repeat(dfirst, np.diff(np.r_[dfirst, m]))
    bpv = np.where(base > 0, cpv[np.maximum(base - 1, 0)], 0.0)
    bv = np.where(base > 0, cv[np.maximum(base - 1, 0)], 0.0)
    T.vwap = (cpv - bpv) / (cv - bv)
    rng = (T.H - T.L).astype(float)
    cs = np.cumsum(rng)
    atr = np.empty(m)
    atr[:14] = cs[:14] / np.arange(1, 15)
    atr[14:] = (cs[14:] - cs[:-14]) / 14.0
    T.atr = np.maximum(atr, 1.0)
    T.day_first = np.full(D, -1, np.int64); T.day_last = np.full(D, -1, np.int64)
    T.day_first[T.day[dfirst]] = dfirst
    T.day_last[T.day[dfirst]] = np.r_[dfirst[1:] - 1, m - 1]
    T.tfi = np.repeat(np.arange(m), en - st + 1)
    return T


def detect(T):
    j = np.arange(2, T.m)
    same = T.day[j] == T.day[j - 2]
    bull = same & (T.L[j] > T.H[j - 2]) & (T.C[j - 1] > T.O[j - 1])
    bear = same & (T.H[j] < T.L[j - 2]) & (T.C[j - 1] < T.O[j - 1])
    parts = []
    for d, mask in ((1, bull), (-1, bear)):
        jj = j[mask]
        N = T.L[jj] if d > 0 else T.H[jj]
        F = T.H[jj - 2] if d > 0 else T.L[jj - 2]
        S = T.L[jj - 2] if d > 0 else T.H[jj - 2]
        dayj = T.day[jj]
        nxt = np.r_[jj[1:], BIG]
        sameday = np.r_[dayj[1:] == dayj[:-1], False]
        parts.append(dict(j=jj, d=np.full(len(jj), d, np.int64), N=N, F=F, S=S, day=dayj, end_excl=np.where(sameday, nxt, T.day_last[dayj] + 1),
                          last_live=np.where(sameday, nxt, T.day_last[dayj])))
    G = NS(**{k: np.concatenate([p[k] for p in parts]) for k in parts[0]})
    G.gap = G.d * (G.N - G.F)
    G.atr = T.atr[G.j]
    G.sizebin = np.digitize(G.gap / G.atr, [0.25, 0.5, 1.0])
    G.n = len(G.j)
    return G


def first_touch_tf(G, lvl, T):
    res = np.full(G.n, -1, np.int64)
    act = np.arange(G.n)
    k = 1
    while act.size:
        t = G.j[act] + k
        ok = t < G.end_excl[act]
        if not ok.all():
            act = act[ok]; t = t[ok]
            if not act.size:
                break
        da = G.d[act]
        ext = np.where(da > 0, T.L[t], T.H[t])
        hit = da * ext <= da * lvl[act]
        if hit.any():
            res[act[hit]] = t[hit]; act = act[~hit]
        k += 1
    return res


def first_touch_1m(a, b, lvl, d, B):
    res = np.full(len(a), -1, np.int64)
    act = np.flatnonzero(a < b)
    k = 0
    while act.size:
        i = a[act] + k
        ok = i < b[act]
        if not ok.all():
            act = act[ok]; i = i[ok]
            if not act.size:
                break
        da = d[act]
        ext = np.where(da > 0, B.l[i], B.h[i])
        hit = da * ext <= da * lvl[act] - 1
        if hit.any():
            res[act[hit]] = i[hit]; act = act[~hit]
        k += 1
    return res


def level(G, depth):
    off = np.zeros(G.n, np.int64) if depth == 0 else (G.gap // 2 if depth == 0.5 else G.gap)
    return G.N - G.d * off


def fills(B, T, G, depth, mode):
    lvl = level(G, depth)
    if mode == "close":
        t = first_touch_tf(G, lvl, T)
        g = np.flatnonzero(t >= 0); t = t[g]
        f = T.i1[t] + 1
        fc = np.minimum(f, B.n - 1)
        ok = (f < B.n) & (B.day[fc] == G.day[g]) & (f < B.X[G.day[g]]) & (T.smin[t] < CUT_S) & (B.sess[fc] < CUT_S)
        g, t, f = g[ok], t[ok], f[ok]
        d = G.d[g]
        fill, ref = B.o[f], T.C[t]
        vw = d * (T.C[t] - T.vwap[t]) > 0
        age = t - G.j[g]
        seg = np.searchsorted(SEG_EDGES, T.smin[t], "right") - 1
    else:
        a = T.i1[G.j] + 1
        b = np.minimum(T.i1[G.last_live] + 1, B.X[G.day])
        i = first_touch_1m(a, b, lvl, G.d, B)
        g = np.flatnonzero(i >= 0); f = i[g]
        ok = B.sess[f] < CUT_S
        g, f = g[ok], f[ok]
        d = G.d[g]
        ref = lvl[g]
        fill = np.where(d > 0, np.minimum(ref, B.o[f]), np.maximum(ref, B.o[f]))
        tb = T.tfi[f]
        p = tb - 1
        vw = d * (T.C[p] - T.vwap[p]) > 0
        age = tb - G.j[g]
        seg = np.searchsorted(SEG_EDGES, B.sess[f], "right") - 1
    base = (((seg * 2 + vw.astype(np.int64)) * 4 + G.sizebin[g]) * 3 + np.digitize(age, [16, 61])) * 2 + (d < 0).astype(np.int64)
    return NS(n=len(g), g=g, d=d, day=G.day[g], f=f, fill=fill, ref=ref, base=base, seg=seg, vw=vw, N=G.N[g], F=G.F[g], S=G.S[g], atr=G.atr[g])


def prep_scan(B, FS, stop, limit_mode):
    if stop == "struct":
        S = FS.S
    elif stop == "gap":
        S = FS.F - FS.d
    else:
        S = FS.ref - FS.d * np.maximum(MIN_DIST, np.rint(FS.atr).astype(np.int64))
    dist = FS.d * (FS.ref - S)
    ok = (dist >= MIN_DIST) & (FS.d * (FS.fill - S) > 0)
    SC = NS(n=int(ok.sum()), g=FS.g[ok], f=FS.f[ok], d=FS.d[ok], day=FS.day[ok], fill=FS.fill[ok], ref=FS.ref[ok], S=S[ok], dist=dist[ok].astype(float), base=FS.base[ok], seg=FS.seg[ok], vw=FS.vw[ok])
    SC.x = B.X[SC.day]
    SC.pflat = B.pflat[SC.day]
    SC.tps = SC.ref[:, None] + SC.d[:, None] * np.rint(RRS[None, :] * SC.dist[:, None]).astype(np.int64)
    SC.cost = cost_ticks(B.sym)
    SC.sc = scan(B, SC.f, SC.x, SC.d, SC.S, SC.tps, limit_mode)
    return SC


def scan(B, f, x, d, S, tps, limit_mode):
    n = len(f)
    tS = np.full(n, BIG, np.int64)
    pxS = S.copy()
    tT = np.full((n, NRR), BIG, np.int64)
    dS = d * S
    dT = d[:, None] * tps
    if limit_mode:
        adv = np.where(d > 0, B.l[f], B.h[f]); fav = np.where(d > 0, B.h[f], B.l[f])
        fbA = d * adv <= dS
        fbB = (d * fav)[:, None] >= dT
        fbC = (d * B.c[f])[:, None] >= dT
        act = np.flatnonzero(~fbA)
        k = 1
    else:
        fbA = np.zeros(n, bool); fbB = np.zeros((n, NRR), bool); fbC = np.zeros((n, NRR), bool)
        act = np.arange(n)
        k = 0
    pend = np.ones((n, NRR), bool)
    while act.size:
        i = f[act] + k
        ok = i < x[act]
        if not ok.all():
            act = act[ok]; i = i[ok]
            if not act.size:
                break
        da = d[act]
        up = da > 0
        adv = np.where(up, B.l[i], B.h[i]); fav = np.where(up, B.h[i], B.l[i])
        hitT = ((da * fav)[:, None] >= dT[act]) & pend[act]
        if hitT.any():
            r_, c_ = np.nonzero(hitT)
            tT[act[r_], c_] = i[r_]
            pend[act[r_], c_] = False
        st = da * adv <= dS[act]
        if st.any():
            a_, i_ = act[st], i[st]
            tS[a_] = i_
            op = B.o[i_]
            gp = (d[a_] * op <= dS[a_]) & (i_ > f[a_])
            pxS[a_] = np.where(gp, op, S[a_])
            act = act[~st]
        k += 1
    return NS(tS=tS, pxS=pxS, tT=tT, fbA=fbA, fbB=fbB, fbC=fbC)


def outcome(B, SC, q, ts, inv, want_exit=False):
    """net R and cost in R per trade of the block (q = target index, NRR = none; ts = 60-bar time stop; inv = inverted)."""
    f, x, d, sc = SC.f, SC.x, SC.d, SC.sc
    if ts:
        tb = np.minimum(x, f + TS_BARS)
        pxt = np.where(f + TS_BARS < x, B.o[np.minimum(f + TS_BARS, B.n - 1)], SC.pflat)
    else:
        tb, pxt = x, SC.pflat
    s = sc.tS < tb
    if q < NRR:
        tp, tT = SC.tps[:, q], sc.tT[:, q]
        g = tT < tb
        if not inv:
            win = g & (~s | (tT < sc.tS))
            px = np.where(win, tp, np.where(s, sc.pxS, pxt))
            px = np.where(sc.fbA, SC.S, np.where(sc.fbC[:, q], tp, px))
            R = d * (px - SC.fill) / SC.dist
            cR = SC.cost / SC.dist
            if want_exit:
                ex = np.where(win, tT, np.where(s, sc.tS, tb))
                ex = np.where(sc.fbA | sc.fbC[:, q], f, ex)
        else:
            lose = g & (~s | (tT <= sc.tS))
            px = np.where(lose, tp, np.where(s, sc.pxS, pxt))
            px = np.where(sc.fbB[:, q], tp, np.where(sc.fbA, SC.S, px))
            rd = np.maximum(1.0, np.rint(RRS[q] * SC.dist))
            R = -d * (px - SC.fill) / rd
            cR = SC.cost / rd
            if want_exit:
                ex = np.where(lose, tT, np.where(s, sc.tS, tb))
                ex = np.where(sc.fbB[:, q] | sc.fbA, f, ex)
    else:
        px = np.where(sc.fbA, SC.S, np.where(s, sc.pxS, pxt))
        R = d * (px - SC.fill) / SC.dist
        cR = SC.cost / SC.dist
        if want_exit:
            ex = np.where(sc.fbA, f, np.where(s, sc.tS, tb))
    if want_exit:
        return R - cR, cR, ex
    return R - cR, cR


# ------------------------------------------------------------------ aggregation
def contract(A):
    for ax, Mx in zip(range(1, 7), (KZ, VW, SZ, AG, DR, CS)):
        A = np.moveaxis(np.tensordot(A, Mx, axes=([ax], [1])), -1, ax)
    return A


def cell_code(SC, cR):
    return SC.base * 4 + (3 - np.digitize(cR, [0.05, 0.10, 0.20], right=True))


def seg_matrix(SC, code, w=None):
    A = np.bincount(SEG_OF_DAY[SC.day] * NCELL + code, weights=w, minlength=NSEG * NCELL).reshape((NSEG,) + CELL_SHAPE)
    return contract(A).reshape(NSEG, NCFG)


def daily_matrix(SC, code, Rn):
    A = np.bincount(SC.day * NCELL + code, weights=Rn, minlength=D * NCELL).reshape((D,) + CELL_SHAPE)
    return contract(A).reshape(D, NCFG)


def block_stats(M, cnt_seg, cost_seg):
    S_seg = np.add.reduceat(M, SEG_START, axis=0)
    Q_seg = np.add.reduceat(M * M, SEG_START, axis=0)
    cum = np.cumsum(M, axis=0)
    peak = np.maximum.accumulate(cum, axis=0)
    np.maximum(peak, 0.0, out=peak)
    maxdd = (peak - cum).max(axis=0)
    tot = cum[-1]

    def sh(Ssum, Qsum, nd):
        mean = Ssum / nd
        var = Qsum / nd - mean * mean
        return np.where(var > 1e-18, mean / np.sqrt(np.maximum(var, 1e-18)), 0.0)
    nd1, nd2 = SEG_ND[:H1_SEGS].sum(), SEG_ND[H1_SEGS:].sum()
    S1, S2 = S_seg[:H1_SEGS].sum(0), S_seg[H1_SEGS:].sum(0)
    summ = np.empty((NCFG, NFIELD), np.float32)
    summ[:, 0] = tot; summ[:, 1] = maxdd; summ[:, 2] = cnt_seg.sum(0); summ[:, 3] = sh(tot, Q_seg.sum(0), D)
    summ[:, 4] = S1 / MONTHS_HALF; summ[:, 5] = sh(S1, Q_seg[:H1_SEGS].sum(0), nd1)
    summ[:, 6] = S2 / MONTHS_HALF; summ[:, 7] = sh(S2, Q_seg[H1_SEGS:].sum(0), nd2)
    summ[:, 8] = cnt_seg[:H1_SEGS].sum(0); summ[:, 9] = cnt_seg[H1_SEGS:].sum(0)
    summ[:, 10] = (S1 + cost_seg[:H1_SEGS].sum(0)) / np.maximum(summ[:, 8], 1.0)
    summ[:, 11] = (S2 + cost_seg[H1_SEGS:].sum(0)) / np.maximum(summ[:, 9], 1.0)
    top = []
    for w in range(NWIN):
        tr = slice(w, w + TRAIN_SEGS)
        nd = SEG_ND[tr].sum()
        St = S_seg[tr].sum(0)
        score = sh(St, Q_seg[tr].sum(0), nd)
        ntr = cnt_seg[tr].sum(0)
        te = w + TRAIN_SEGS
        a, b = SEG_START[te], (SEG_START[te + 1] if te + 1 < NSEG else D)
        row = {}
        for name, min_n, keep in (("t200", 200, 2), ("t1000", 1000, 1)):
            sc_ = np.where((ntr >= min_n) & (St > 0), score, -np.inf)
            idx = np.argpartition(-sc_, keep)[:keep]
            idx = idx[np.argsort(-sc_[idx])]
            row[name] = [dict(score=float(sc_[c]), cfg=int(c), ntr_train=int(ntr[c]), test=M[a:b, c].astype(np.float32), test_n=float(cnt_seg[te, c]), test_cost=float(cost_seg[te, c]))
                         for c in idx if np.isfinite(sc_[c])]
        top.append(row)
    return summ, top


def job_blocks(B, T, G, only=None, sgn=None):
    """Yields (block, SC, Rn, cR, code, cnt_seg, cost_seg) for every block of this instrument and candle (or only those listed).
    sgn (placebo): one random sign per gap, applied to the before-cost R of every trade that gap produces in every block."""
    for depth in DEPTHS:
        for mode in MODES:
            if only is not None and not any(b[0] == depth and b[1] == mode for b in only):
                continue
            FS = fills(B, T, G, depth, mode)
            for stop in STOPS:
                if only is not None and not any(b[:3] == (depth, mode, stop) for b in only):
                    continue
                SC = prep_scan(B, FS, stop, mode == "limit")
                if SC.n == 0:
                    continue
                for q in range(NRR + 1):
                    for inv in (0, 1):
                        if inv and q == NRR:
                            continue
                        cache = None
                        for ts in (0, 1):
                            blk = (depth, mode, stop, q, ts, inv)
                            if only is not None and blk not in only:
                                continue
                            Rn, cR = outcome(B, SC, q, ts, inv)
                            if sgn is not None:
                                Rn = sgn[SC.g] * (Rn + cR) - cR
                            if cache is None:
                                code = cell_code(SC, cR)
                                cache = (code, seg_matrix(SC, code), seg_matrix(SC, code, cR))
                            yield blk, SC, Rn, cR, cache[0], cache[1], cache[2]


AS_WRITTEN = (0.0, "close", "struct", 1, 0, 0)


def run_job(args):
    sym, tf, outdir, placebo = args
    t0 = time.time()
    B = load_1m(sym); T = tf_bars(B, tf); G = detect(T)
    sgn = np.random.default_rng(29400 + 100 * SYMS.index(sym) + tf).choice(np.array([-1.0, 1.0]), G.n) if placebo else None
    blocks, summs, tops, aw = [], [], [], None
    for blk, SC, Rn, cR, code, cnt_seg, cost_seg in job_blocks(B, T, G, sgn=sgn):
        M = daily_matrix(SC, code, Rn)
        summ, top = block_stats(M, cnt_seg, cost_seg)
        blocks.append(blk); summs.append(summ); tops.append(top)
        if blk == AS_WRITTEN:
            aw = dict(daily=M[:, 0].astype(np.float64), cnt_seg=cnt_seg[:, 0].copy(), cost_seg=cost_seg[:, 0].copy(), one=one_at_a_time(B, SC, sgn))
    np.save(os.path.join(outdir, f"summ_{sym}_{tf}.npy"), np.stack(summs))
    pickle.dump(dict(sym=sym, tf=tf, blocks=blocks, tops=tops, aw=aw, n_fvg=int(G.n), secs=time.time() - t0), open(os.path.join(outdir, f"meta_{sym}_{tf}.pkl"), "wb"))
    return sym, tf, len(blocks), time.time() - t0


def one_at_a_time(B, SC, sgn=None):
    """As-written cell (killzone as written, VWAP aligned), one position at a time: daily net R, trades."""
    Rn, cR, ex = outcome(B, SC, 1, 0, 0, want_exit=True)
    if sgn is not None:
        Rn = sgn[SC.g] * (Rn + cR) - cR
    m = np.isin(SC.seg, (3, 5)) & SC.vw
    order = np.argsort(SC.f[m], kind="stable")
    f, e, r, dd = SC.f[m][order], ex[m][order], Rn[m][order], SC.day[m][order]
    daily = np.zeros(D); busy = -1; n = 0
    for i in range(len(f)):
        if f[i] >= busy:
            daily[dd[i]] += r[i]; busy = e[i] + 1; n += 1
    return dict(daily=daily, n=n, n_all=int(m.sum()))


def block_daily(sym, tf, blk, cfgs, placebo=False, cache={}):
    """Recompute the daily net R (and segment counts / costs) of given filter sets of one block."""
    key = (sym, tf)
    if key not in cache:
        cache.clear()
        B = load_1m(sym); T = tf_bars(B, tf); cache[key] = (B, T, detect(T))
    B, T, G = cache[key]
    sgn = np.random.default_rng(29400 + 100 * SYMS.index(sym) + tf).choice(np.array([-1.0, 1.0]), G.n) if placebo else None
    for b, SC, Rn, cR, code, cnt_seg, cost_seg in job_blocks(B, T, G, only=[blk], sgn=sgn):
        M = daily_matrix(SC, code, Rn)
        return {int(c): dict(daily=M[:, c].copy(), cnt_seg=cnt_seg[:, c].copy(), cost_seg=cost_seg[:, c].copy()) for c in cfgs}
    return {}


# ------------------------------------------------------------------ slow reference (cross-check only)
def _ref_trade(B, dd, g, d, f, fill, ref, smin, vw, age, stop, q, ts, inv, limit_mode, cticks):
    if stop == "struct":
        S = g["S"]
    elif stop == "gap":
        S = g["F"] - d
    else:
        S = ref - d * max(MIN_DIST, int(np.rint(g["atr"])))
    dist = d * (ref - S)
    if dist < MIN_DIST or d * (fill - S) <= 0:
        return None
    tp = None if q == NRR else ref + d * int(np.rint(RRS[q] * dist))
    x = int(B.X[dd])
    tb = min(x, f + TS_BARS) if ts else x
    pxt = B.o[f + TS_BARS] if (ts and f + TS_BARS < x) else B.pflat[dd]
    pnl = None
    for i in range(f, tb):
        adv = B.l[i] if d > 0 else B.h[i]
        fav = B.h[i] if d > 0 else B.l[i]
        hitS = d * adv <= d * S
        hitT = tp is not None and d * fav >= d * tp
        if i == f and limit_mode:
            if not inv:
                if hitS:
                    pnl = d * (S - fill); break
                if tp is not None and d * B.c[i] >= d * tp:
                    pnl = d * (tp - fill); break
            else:
                if hitT:
                    pnl = -d * (tp - fill); break
                if hitS:
                    pnl = -d * (S - fill); break
            continue
        pxs = B.o[i] if (i > f and d * B.o[i] <= d * S) else S
        if not inv:
            if hitS:
                pnl = d * (pxs - fill); break
            if hitT:
                pnl = d * (tp - fill); break
        else:
            if hitT:
                pnl = -d * (tp - fill); break
            if hitS:
                pnl = -d * (pxs - fill); break
    if pnl is None:
        pnl = (-d if inv else d) * (pxt - fill)
    rd = max(1.0, float(np.rint(RRS[q] * dist))) if inv else float(dist)
    R, cR = pnl / rd, cticks / rd
    seg = int(np.searchsorted(SEG_EDGES, smin, "right") - 1)
    sizebin = int(np.digitize(g["gap"] / g["atr"], [0.25, 0.5, 1.0]))
    agebin = int(np.digitize(age, [16, 61]))
    costbin = 3 - int(np.digitize(cR, [0.05, 0.10, 0.20], right=True))
    cell = ((((seg * 2 + int(vw)) * 4 + sizebin) * 3 + agebin) * 2 + (0 if d > 0 else 1)) * 4 + costbin
    return (int(dd), int(f), int(d), int(cell), round(float(R - cR), 9))


def ref_block(B, T, days, blk):
    depth, mode, stop, q, ts, inv = blk
    cticks = cost_ticks(B.sym)
    out = []
    for dd in days:
        t0, t1 = int(T.day_first[dd]), int(T.day_last[dd])
        if t0 < 0:
            continue
        act = {1: None, -1: None}
        cpv = cv = 0.0
        prev = None
        for t in range(t0, t1 + 1):
            if mode == "limit":
                for i in range(int(T.i0[t]), int(T.i1[t]) + 1):
                    if i >= B.X[dd]:
                        break
                    for d in (1, -1):
                        g = act[d]
                        if g is None:
                            continue
                        ext = B.l[i] if d > 0 else B.h[i]
                        if d * ext <= d * g["lvl"] - 1:
                            act[d] = None
                            if B.sess[i] < CUT_S:
                                fill = min(g["lvl"], B.o[i]) if d > 0 else max(g["lvl"], B.o[i])
                                rec = _ref_trade(B, dd, g, d, i, int(fill), int(g["lvl"]), int(B.sess[i]), d * (prev[0] - prev[1]) > 0, t - g["j"], stop, q, ts, inv, True, cticks)
                                if rec:
                                    out.append(rec)
            cpv += (T.H[t] + T.L[t] + T.C[t]) / 3.0 * T.V[t]; cv += T.V[t]
            vwap_t = cpv / cv
            new = {}
            if t - 2 >= t0:
                if T.L[t] > T.H[t - 2] and T.C[t - 1] > T.O[t - 1]:
                    new[1] = (int(T.L[t]), int(T.H[t - 2]), int(T.L[t - 2]))
                if T.H[t] < T.L[t - 2] and T.C[t - 1] < T.O[t - 1]:
                    new[-1] = (int(T.H[t]), int(T.L[t - 2]), int(T.H[t - 2]))
            for d in (1, -1):
                if d in new:
                    N, F, Sx = new[d]
                    gap = d * (N - F)
                    off = 0 if depth == 0 else (gap // 2 if depth == 0.5 else gap)
                    lo_ = max(0, t - 13)
                    atr = max(float(np.mean((T.H[lo_:t + 1] - T.L[lo_:t + 1]).astype(float))), 1.0)
                    act[d] = dict(j=t, N=N, F=F, S=Sx, gap=gap, lvl=N - d * off, atr=atr)
                elif mode == "close" and act[d] is not None:
                    g = act[d]
                    ext = T.L[t] if d > 0 else T.H[t]
                    if d * ext <= d * g["lvl"]:
                        act[d] = None
                        f = int(T.i1[t]) + 1
                        if f < B.n and B.day[f] == dd and f < B.X[dd] and T.smin[t] < CUT_S and B.sess[f] < CUT_S:
                            rec = _ref_trade(B, dd, g, d, f, int(B.o[f]), int(T.C[t]), int(T.smin[t]), d * (T.C[t] - vwap_t) > 0, t - g["j"], stop, q, ts, inv, False, cticks)
                            if rec:
                                out.append(rec)
            prev = (T.C[t], vwap_t)
    return sorted(out)


def engine_block(B, T, G, days, blk):
    days = set(int(x) for x in days)
    for b, SC, Rn, cR, code, _, _ in job_blocks(B, T, G, only=[blk]):
        m = np.array([int(x) in days for x in SC.day])
        return sorted((int(a), int(b_), int(c), int(e), round(float(r), 9)) for a, b_, c, e, r in zip(SC.day[m], SC.f[m], SC.d[m], code[m], Rn[m]))
    return []


def pine_literal(T):
    """The script exactly as written: state carried across sessions, no validity checks. Returns the set of (candle index, direction) signals."""
    kz = ((T.smin >= 930) & (T.smin < 1050)) | ((T.smin >= 1170) & (T.smin < 1290))
    H_, L_, O_, C_, V_ = (x.tolist() for x in (T.H, T.L, T.O, T.C, T.vwap))
    kz = kz.tolist()
    sig = set()
    abt = asb = None
    bbar = sbar = -1
    for t in range(2, T.m):
        if L_[t] > H_[t - 2] and C_[t - 1] > O_[t - 1]:
            abt = L_[t]; bbar = t
        if H_[t] < L_[t - 2] and C_[t - 1] < O_[t - 1]:
            asb = H_[t]; sbar = t
        if abt is not None and t > bbar and L_[t] <= abt:
            if C_[t] > V_[t] and kz[t]:
                sig.add((t, 1))
            abt = None
        if asb is not None and t > sbar and H_[t] >= asb:
            if C_[t] < V_[t] and kz[t]:
                sig.add((t, -1))
            asb = None
    return sig


def engine_signals(T, G):
    t = first_touch_tf(G, level(G, 0.0), T)
    ok = t >= 0
    t, d = t[ok], G.d[ok]
    kz = ((T.smin[t] >= 930) & (T.smin[t] < 1050)) | ((T.smin[t] >= 1170) & (T.smin[t] < 1290))
    vw = d * (T.C[t] - T.vwap[t]) > 0
    return set(zip(t[kz & vw].tolist(), d[kz & vw].tolist()))


# ------------------------------------------------------------------ dry run
def dry_run():
    t00 = time.time()
    rng = np.random.default_rng(294)
    all_blocks = [(dp, mo, st, q, ts, inv) for dp in DEPTHS for mo in MODES for st in STOPS for q in range(NRR + 1) for ts in (0, 1) for inv in (0, 1) if not (inv and q == NRR)]
    assert len(all_blocks) == 396
    print(f"grid: {len(SYMS) * len(TFS) * len(all_blocks):,} blocks x {NCFG:,} filter sets = {len(SYMS) * len(TFS) * len(all_blocks) * NCFG:,} parameter sets; {D} trading days, {NSEG} half-years, {NWIN} walk-forward windows")
    # contraction test: the as-written filter set (index 0) = cells with segment 3 or 5 and VWAP aligned
    A = rng.random((3,) + CELL_SHAPE)
    Mx = contract(A).reshape(3, NCFG)
    assert np.allclose(Mx[:, 0], A[:, [3, 5], 1].sum(axis=(1, 2, 3, 4, 5)))
    c = np.ravel_multi_index((6, 1, 2, 1, 2, 3), CFG_SHAPE)                 # all hours, VWAP off, gap >= 0.5 ATR, age <= 60, short only, cost <= 0.05R
    assert np.allclose(Mx[:, c], A[:, :, :, 2:, :2, 1, 3].sum(axis=(1, 2, 3, 4)))
    print("filter-contraction tests passed")
    for sym in SYMS:
        B = load_1m(sym)
        print(f"\n{sym}: {B.n:,} one-minute bars on {int((B.d_last >= B.d_first).sum())} trading days; cost {COMM + 2 * B.tick * B.pv:.2f} $ = {cost_ticks(sym):.3f} ticks per round trip; "
              f"{len(B.rolls)} roll jumps removed: " + ", ".join(f"{d} {g:+g}" for d, g in B.rolls))
        for tf in TFS:
            T = tf_bars(B, tf); G = detect(T)
            # candle construction check on random candles
            for t in rng.integers(0, T.m, 200):
                sl = slice(T.i0[t], T.i1[t] + 1)
                assert T.H[t] == B.h[sl].max() and T.L[t] == B.l[sl].min() and T.O[t] == B.o[T.i0[t]] and T.C[t] == B.c[T.i1[t]] and abs(T.V[t] - B.v[sl].sum()) < 1e-6
            line = f"  {tf:>2}-min: {T.m:,} candles, {G.n:,} gaps ({(G.d > 0).sum():,} bull / {(G.d < 0).sum():,} bear)"
            if tf in (1, 5, 15):
                lit = pine_literal(T); eng = engine_signals(T, G)
                line += f" | script as written: {len(lit):,} signals; engine {len(eng):,}; only in script {len(lit - eng)}, only in engine {len(eng - lit)}"
            FS = fills(B, T, G, 0.0, "close")
            SC = prep_scan(B, FS, "struct", False)
            m = np.isin(SC.seg, (3, 5)) & SC.vw
            cR = SC.cost / SC.dist[m]
            raw = np.isin(FS.seg, (3, 5)) & FS.vw
            line += (f" | as-written setups {int(raw.sum()):,}, valid {int(m.sum()):,} ({int(raw.sum()) - int(m.sum()):,} dropped: stop on the wrong side or under {MIN_DIST} ticks), {m.sum() / max(1, len(np.unique(SC.day[m]))):.1f} per day traded; "
                     f"stop distance median {np.median(SC.dist[m]) * B.tick:.2f} pts; cost median {np.median(cR):.3f}R, {np.mean(cR > 0.20):.0%} of setups cost > 0.20R")
            print(line, flush=True)
            # cross-check against the slow reference on random days and random blocks
            good = np.flatnonzero(T.day_first >= 0)
            nchk = 0
            for blk in [AS_WRITTEN] + [all_blocks[i] for i in rng.choice(len(all_blocks), 7, replace=False)]:
                days = rng.choice(good, 6, replace=False)
                a = ref_block(B, T, days, blk); b = engine_block(B, T, G, days, blk)
                assert a == b, (sym, tf, blk, len(a), len(b), [x for x in a if x not in b][:3], [x for x in b if x not in a][:3])
                nchk += len(a)
            print(f"        engine = slow reference on 8 blocks x 6 random days ({nchk:,} trades compared, every field equal)", flush=True)
            if sym == "NQ" and tf == 5:
                cnt = {(dp, mo): fills(B, T, G, dp, mo).n for dp in DEPTHS for mo in MODES}
                print("        NQ 5-min entries by (depth, mode), all hours, before the stop test: " + ", ".join(f"{k}: {v:,}" for k, v in cnt.items()))
                t1 = time.time()
                code = cell_code(SC, SC.cost / SC.dist)
                M = daily_matrix(SC, code, np.zeros(SC.n)); block_stats(M, seg_matrix(SC, code), seg_matrix(SC, code, SC.cost / SC.dist))
                print(f"        one block's statistics take {time.time() - t1:.2f}s (timed on zeros, no result computed)")
    print(f"\ndry-run time {time.time() - t00:.0f}s")
    print("DRY RUN OK")


# ------------------------------------------------------------------ main
def boot_p(x, seed=294):
    x = np.asarray(x, float)
    n = len(x)
    if n < 20:
        return float("nan")

    def run(nb, seed_):
        rng = np.random.default_rng(seed_)
        out = np.empty(nb)
        for s in range(0, nb, 500):
            idx = rng.integers(0, n, (min(500, nb - s), n))
            out[s:s + idx.shape[0]] = x[idx].mean(axis=1)
        return float((out > 0).mean())
    p = run(4000, seed)
    return run(40000, seed + 1) if p >= 0.99 else p


def series_stats(daily, months):
    cum = np.cumsum(daily)
    dd = float((np.maximum(np.maximum.accumulate(cum), 0.0) - cum).max())
    tot = float(cum[-1])
    sd = float(np.std(daily))
    return dict(total_R=tot, monthly_R=tot / months, maxdd_R=dd, daily_sharpe=float(np.mean(daily) / sd) if sd > 0 else 0.0,
                dd_months=(dd / (tot / months)) if tot > 0 else float("inf"))


def goal_view(st):
    """Dollar view at the size where the average month makes $5,000."""
    if st["monthly_R"] <= 0:
        return dict(risk_per_trade=None, maxdd_dollars=None, meets_numbers_100k=False, meets_numbers_50k=False)
    r = 5000.0 / st["monthly_R"]
    return dict(risk_per_trade=r, maxdd_dollars=st["maxdd_R"] * r, meets_numbers_100k=bool(st["maxdd_R"] <= 10 * st["monthly_R"]), meets_numbers_50k=bool(st["maxdd_R"] <= 5 * st["monthly_R"]))


def judge(name, daily, n_tr, cost_R, lo, hi, months, split):
    """daily: net R per calendar day index; lo/hi the day range judged; split the first OOS day."""
    x = daily[lo:hi]
    st = series_stats(x, months)
    is_, oos = daily[lo:split], daily[split:hi]
    row = dict(name=name, n=float(n_tr), net_R_per_trade=float(x.sum() / n_tr) if n_tr else float("nan"), gross_R_per_trade=float((x.sum() + cost_R) / n_tr) if n_tr else float("nan"),
               p_is=boot_p(is_), p_oos=boot_p(oos), is_monthly_R=float(is_.sum() / ((split - lo) / (hi - lo) * months)), oos_monthly_R=float(oos.sum() / ((hi - split) / (hi - lo) * months)), **st)
    row["candidate"] = bool(row["net_R_per_trade"] > 0 and row["gross_R_per_trade"] > 0 and row["p_is"] >= 0.95 and row["p_oos"] >= 1 - 0.01 / K_TOTAL)
    row.update(goal_view(st))
    row["meets_goal_oos"] = bool(row["meets_numbers_100k"] and row["candidate"])
    return row


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    import multiprocessing as mp
    placebo = "--placebo" in sys.argv
    outdir = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(__import__("tempfile").gettempdir(), "r294_cache_placebo" if placebo else "r294_cache")
    if placebo:
        print("##### PLACEBO RUN: every gap's before-cost R is multiplied by a random sign (a world with no edge anywhere, same trades, same costs) #####")
    os.makedirs(outdir, exist_ok=True)
    t0 = time.time()
    jobs = [(s, tf, outdir, placebo) for s in SYMS for tf in TFS if not os.path.exists(os.path.join(outdir, f"meta_{s}_{tf}.pkl"))]
    if jobs:
        with mp.Pool(min(8, len(jobs))) as pool:
            for sym, tf, nb, secs in pool.imap_unordered(run_job, jobs):
                print(f"  job {sym} {tf}-min: {nb} blocks in {secs:.0f}s ({time.time() - t0:.0f}s elapsed)", flush=True)
    metas = {(s, tf): pickle.load(open(os.path.join(outdir, f"meta_{s}_{tf}.pkl"), "rb")) for s in SYMS for tf in TFS}
    out = dict(k_total=K_TOTAL, n_sets=0, rows=[], placebo=placebo)
    series = {}
    mon_of_day = (CAL.year - 2019) * 12 + CAL.month - 10
    monthly = lambda x: np.bincount(mon_of_day, weights=x, minlength=84).tolist()
    split = int(SEG_START[OOS_SEG0])
    # (1) as written
    print("\n=== (1) AS WRITTEN (every signal taken; R per trade; monthly R; max drawdown in R) ===")
    for s in SYMS:
        for tf in TFS:
            aw = metas[(s, tf)]["aw"]
            row = judge(f"FVG+VWAP killzone sentinel AS WRITTEN, {s} {tf}-min", aw["daily"], aw["cnt_seg"].sum(), aw["cost_seg"].sum(), 0, D, MONTHS_ALL, split)
            one = series_stats(aw["one"]["daily"], MONTHS_ALL)
            row["one_at_a_time"] = dict(n=aw["one"]["n"], **one)
            row["kind"], row["sym"], row["tf"] = "as_written", s, tf
            row["monthly"] = monthly(aw["daily"]); series[f"aw_{s}_{tf}"] = aw["daily"]
            out["rows"].append(row)
            print(f"  {s} {tf:>2}-min: {row['n']:>7,.0f} trades, net {row['net_R_per_trade']:+.3f}R (gross {row['gross_R_per_trade']:+.3f}R), {row['monthly_R']:+7.1f}R a month, max DD {row['maxdd_R']:7.1f}R, "
                  f"P IS/OOS {row['p_is']:.2f}/{row['p_oos']:.3f} | one at a time: {one['monthly_R']:+.1f}R a month on {aw['one']['n']:,} trades, max DD {one['maxdd_R']:.1f}R", flush=True)
    # (2) walk-forward
    print("\n=== (2) WALK-FORWARD (chosen on the previous 24 months, traded in the next 6; 60 stitched months 2021-10 .. 2026-09) ===")
    wf_defs = [("WF-BEST", "t200", None, 1), ("WF-ROBUST", "t1000", None, 1), ("WF-TOP20", "t200", None, 20), ("WF-NQ", "t200", "NQ", 1), ("WF-ES", "t200", "ES", 1), ("WF-GC", "t200", "GC", 1)]
    lo = int(SEG_START[TRAIN_SEGS])
    for name, key, only_sym, K in wf_defs:
        daily = np.zeros(D); n_tr = cost = 0.0; picks = []
        for w in range(NWIN):
            cands = []
            for (s, tf), me in metas.items():
                if only_sym and s != only_sym:
                    continue
                for bi, top in enumerate(me["tops"]):
                    for rank, e in enumerate(top[w][key]):
                        cands.append((e["score"], s, tf, bi, rank))
            cands.sort(key=lambda z: -z[0])
            chosen = cands[:K]
            te = w + TRAIN_SEGS
            a = SEG_START[te]
            for score, s, tf, bi, rank in chosen:
                e = metas[(s, tf)]["tops"][bi][w][key][rank]
                daily[a:a + len(e["test"])] += e["test"] / K
                n_tr += e["test_n"] / K; cost += e["test_cost"] / K
            sc0, s, tf, bi, rank = chosen[0] if chosen else (float("nan"), "", 0, 0, 0)
            if chosen:
                e = metas[(s, tf)]["tops"][bi][w][key][rank]
                picks.append(dict(test_half_year=str(CAL[a].date()), train_score=sc0, train_trades=e["ntr_train"], sym=s, tf=tf, block=block_name(metas[(s, tf)]["blocks"][bi]), filters=cfg_name(e["cfg"]),
                                  test_R=float(e["test"].sum()), test_trades=e["test_n"], n_chosen=len(chosen)))
        row = judge(f"FVG+VWAP sentinel {name}: parameters re-chosen every half-year on the previous 24 months", daily, n_tr, cost, lo, D, 60.0, split)
        row["kind"], row["wf"], row["picks"] = "walk_forward", name, picks
        row["monthly"] = monthly(daily); series[name] = daily
        out["rows"].append(row)
        print(f"  {name:<9}: {row['n']:>8,.0f} trades, net {row['net_R_per_trade']:+.3f}R (gross {row['gross_R_per_trade']:+.3f}R), {row['monthly_R']:+7.1f}R a month, max DD {row['maxdd_R']:7.1f}R, "
              f"P first/second half {row['p_is']:.2f}/{row['p_oos']:.3f} -> {'CANDIDATE' if row['candidate'] else 'no edge'}; goal numbers met: {row['meets_numbers_100k']}", flush=True)
        for p in picks:
            print(f"        {p['test_half_year']}: {p['sym']} {p['tf']}-min | {p['block']} | {p['filters']} | train score {p['train_score']:.3f} on {p['train_trades']} trades -> test {p['test_R']:+.1f}R on {p['test_trades']:.0f} trades")
    # (3) descriptive: the whole grid in sample
    print("\n=== (3) DESCRIPTIVE: the whole grid on the full 84 months (in sample) ===")
    n_sets = n_500 = n_goal = n_goal50 = n_pos = n_both = pos1 = pos2 = pos12 = 0
    best = None
    h1_top = []
    samp = []
    rng = np.random.default_rng(2940)
    for (s, tf), me in metas.items():
        summ = np.load(os.path.join(outdir, f"summ_{s}_{tf}.npy"))            # (blocks, NCFG, NFIELD)
        tot, dd, ntr = summ[..., 0].astype(np.float64), summ[..., 1].astype(np.float64), summ[..., 2]
        mon = tot / MONTHS_ALL
        ok = ntr >= 500
        goal = ok & (mon > 0) & (dd <= 10 * mon)
        n_sets += summ.shape[0] * summ.shape[1]; n_500 += int(ok.sum()); n_pos += int((ok & (mon > 0)).sum()); n_goal += int(goal.sum()); n_goal50 += int((ok & (mon > 0) & (dd <= 5 * mon)).sum())
        ratio = np.where(ok & (mon > 0), mon / np.maximum(dd, 1e-9), -np.inf)
        bi, ci = np.unravel_index(int(np.argmax(ratio)), ratio.shape)
        if best is None or ratio[bi, ci] > best["ratio"]:
            best = dict(ratio=float(ratio[bi, ci]), sym=s, tf=tf, blk=me["blocks"][bi], cfg=int(ci), monthly_R=float(mon[bi, ci]), maxdd_R=float(dd[bi, ci]), n=float(ntr[bi, ci]),
                        monthly_h1=float(summ[bi, ci, 4]), monthly_h2=float(summ[bi, ci, 6]))
        e1 = summ[..., 8] >= 300
        sh1 = np.where(e1, summ[..., 5], -np.inf).ravel()
        idx = np.argpartition(-sh1, 1000)[:1000]
        _flat = {k: summ[..., k].ravel() for k in (4, 5, 6, 7, 10, 11)}
        fl = _flat.__getitem__
        h1_top += [(float(sh1[i]), float(fl(4)[i]), float(fl(6)[i]), float(fl(7)[i]), float(fl(10)[i]), float(fl(11)[i])) for i in idx if np.isfinite(sh1[i])]
        both = (e1 & (summ[..., 9] >= 300)).ravel()
        e12 = np.flatnonzero(both)
        if len(e12):
            n_both += len(e12); pos1 += int((fl(4)[e12] > 0).sum()); pos2 += int((fl(6)[e12] > 0).sum()); pos12 += int(((fl(4)[e12] > 0) & (fl(6)[e12] > 0)).sum())
            pick = rng.choice(e12, min(70000, len(e12)), replace=False)
            samp.append(np.stack([fl(5)[pick], fl(7)[pick], fl(10)[pick], fl(11)[pick]], axis=1))
    h1_top.sort(key=lambda z: -z[0]); h1_top = np.array(h1_top[:1000])
    samp = np.concatenate(samp)
    rho = float(pd.Series(samp[:, 0]).corr(pd.Series(samp[:, 1]), method="spearman"))
    rho_gross = float(pd.Series(samp[:, 2]).corr(pd.Series(samp[:, 3]), method="spearman"))
    out["n_sets"] = n_sets
    out["in_sample"] = dict(n_sets=n_sets, n_with_500_trades=n_500, n_positive=n_pos, n_meet_goal_numbers_100k=n_goal, n_meet_goal_numbers_50k=n_goal50, best=dict(best, block=block_name(best["blk"]), filters=cfg_name(best["cfg"])),
                            halves=dict(spearman_h1_h2=rho, spearman_gross_per_trade_h1_h2=rho_gross, n_sampled=int(len(samp)), n_sets_300_each_half=n_both, share_positive_h1=pos1 / max(1, n_both),
                                        share_positive_h2=pos2 / max(1, n_both), share_positive_both=pos12 / max(1, n_both), top1000_h1_monthly_R=float(h1_top[:, 1].mean()),
                                        top1000_h2_monthly_R=float(h1_top[:, 2].mean()), top1000_share_h2_positive=float((h1_top[:, 2] > 0).mean()), top1000_h1_sharpe=float(h1_top[:, 0].mean()),
                                        top1000_h2_sharpe=float(h1_top[:, 3].mean()), top1000_h1_gross_per_trade=float(h1_top[:, 4].mean()), top1000_h2_gross_per_trade=float(h1_top[:, 5].mean())))
    b = out["in_sample"]["best"]
    r = 5000.0 / b["monthly_R"]
    bd = block_daily(b["sym"], b["tf"], tuple(b["blk"]), [b["cfg"]], placebo)[b["cfg"]]["daily"]
    assert abs(bd.sum() / MONTHS_ALL - b["monthly_R"]) < 1e-3 * max(1.0, abs(b["monthly_R"])), (bd.sum() / MONTHS_ALL, b["monthly_R"])
    b["monthly"] = monthly(bd); series["in_sample_best"] = bd
    print(f"  parameter sets {n_sets:,}; with >= 500 trades {n_500:,}; of those profitable {n_pos:,} ({n_pos / max(1, n_500):.1%}); meeting the goal numbers (max DD <= 10 months of profit) {n_goal:,} ({n_goal / max(1, n_500):.2%}); <= 5 months {n_goal50:,}")
    print(f"  best in-sample set: {b['sym']} {b['tf']}-min | {b['block']} | {b['filters']}: {b['monthly_R']:+.1f}R a month on {b['n']:,.0f} trades, max DD {b['maxdd_R']:.1f}R -> at ${r:,.0f} a trade: $5,000 a month, max DD ${b['maxdd_R'] * r:,.0f}; "
          f"first half {b['monthly_h1']:+.1f}R a month, second half {b['monthly_h2']:+.1f}R")
    hv = out["in_sample"]["halves"]
    print(f"  first half vs second half, {n_both:,} sets with >= 300 trades in each half: profitable in the first half {hv['share_positive_h1']:.2%}, in the second {hv['share_positive_h2']:.2%}, in both {hv['share_positive_both']:.2%} "
          f"(independent halves would give {hv['share_positive_h1'] * hv['share_positive_h2']:.2%})")
    print(f"  rank correlation between the halves across {hv['n_sampled']:,} sampled sets: net daily Sharpe {rho:+.3f} (costs alone make this positive: an expensive set loses in both halves); BEFORE-COST R per trade {rho_gross:+.3f}")
    print(f"  the 1,000 best first-half sets: {hv['top1000_h1_monthly_R']:+.1f}R a month in the first half -> {hv['top1000_h2_monthly_R']:+.1f}R a month in the second; {hv['top1000_share_h2_positive']:.0%} stayed profitable; "
          f"before costs {hv['top1000_h1_gross_per_trade']:+.3f}R -> {hv['top1000_h2_gross_per_trade']:+.3f}R per trade")
    # one-parameter-at-a-time from the as-written cell
    print("\n=== (4) DESCRIPTIVE: one parameter changed at a time from the as-written cell (monthly R, whole sample) ===")
    sens = {}
    for (s, tf), me in metas.items():
        summ = np.load(os.path.join(outdir, f"summ_{s}_{tf}.npy"))
        bix = {b_: i for i, b_ in enumerate(me["blocks"])}
        base = AS_WRITTEN
        rec = {"as written": float(summ[bix[base], 0, 0] / MONTHS_ALL)}
        for label, blk in [("limit at the gap edge", (0.0, "limit", "struct", 1, 0, 0)), ("close entry at mid gap", (0.5, "close", "struct", 1, 0, 0)), ("limit at mid gap", (0.5, "limit", "struct", 1, 0, 0)),
                           ("limit at far edge", (1.0, "limit", "struct", 1, 0, 0)), ("gap stop", (0.0, "close", "gap", 1, 0, 0)), ("ATR stop", (0.0, "close", "atr", 1, 0, 0)),
                           ("target 0.5R", (0.0, "close", "struct", 0, 0, 0)), ("target 2R", (0.0, "close", "struct", 3, 0, 0)), ("target 3R", (0.0, "close", "struct", 4, 0, 0)),
                           ("no target", (0.0, "close", "struct", NRR, 0, 0)), ("60-min time stop", (0.0, "close", "struct", 1, 1, 0)), ("inverted", (0.0, "close", "struct", 1, 0, 1))]:
            if blk in bix:
                rec[label] = float(summ[bix[blk], 0, 0] / MONTHS_ALL)
        for label, idx in [("AM only", (1, 0, 0, 0, 0, 0)), ("PM only", (2, 0, 0, 0, 0, 0)), ("all RTH", (3, 0, 0, 0, 0, 0)), ("London", (4, 0, 0, 0, 0, 0)), ("all hours", (6, 0, 0, 0, 0, 0)),
                           ("VWAP off", (0, 1, 0, 0, 0, 0)), ("against VWAP", (0, 2, 0, 0, 0, 0)), ("gap >= 0.5 ATR", (0, 0, 2, 0, 0, 0)), ("gap >= 1 ATR", (0, 0, 3, 0, 0, 0)),
                           ("age <= 15", (0, 0, 0, 2, 0, 0)), ("long only", (0, 0, 0, 0, 1, 0)), ("short only", (0, 0, 0, 0, 2, 0)), ("cost <= 0.10R", (0, 0, 0, 0, 0, 2)), ("cost <= 0.05R", (0, 0, 0, 0, 0, 3))]:
            rec[label] = float(summ[bix[base], np.ravel_multi_index(idx, CFG_SHAPE), 0] / MONTHS_ALL)
        sens[f"{s}|{tf}"] = rec
    out["sensitivity"] = sens
    labels = list(next(iter(sens.values())).keys())
    print(f"  {'change':<24}" + "".join(f"{k:>9}" for k in sens))
    for lab in labels:
        print(f"  {lab:<24}" + "".join(f"{sens[k].get(lab, float('nan')):>+9.1f}" for k in sens))
    any_goal = [r_["name"] for r_ in out["rows"] if r_["meets_goal_oos"]]
    out["goal_met_out_of_sample"] = bool(any_goal)
    print(f"\nMANUAL'S GOAL OUT OF SAMPLE ($5,000 a month on average with a max drawdown <= $50,000, and distinguishable from luck): {'MET by ' + '; '.join(any_goal) if any_goal else 'NOT MET by any of the 21 pre-registered strategies'}")
    fn = "round294_placebo.json" if placebo else "round294_results.json"
    np.savez_compressed(os.path.join(outdir, "series.npz"), **series)
    json.dump(out, open(os.path.join(HERE, fn), "w"), indent=1, default=float)
    print(f"Saved {fn} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
