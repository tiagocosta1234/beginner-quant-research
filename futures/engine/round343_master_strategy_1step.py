"""
Round 343 (2026-10-04, PRE-REGISTERED; ledger rows: the screen + one per master, k + 3 -- first written as one per cell, changed when recording for readability, disclosed in the journal): the MASTER STRATEGY.

the trader's request: go through every strategy generated for MT5, convert the futures-era ones to forex symbols, refine them, put the survivors together into one master
strategy, and backtest that master on the test the trader intends to buy (MT5 1-Step $100K: +10% target, 3% daily loss, 10% end-of-day trailing loss, best-day rule).
The honest prior (stated before the run): no sleeve of the last 340 rounds has a confirmed edge after MT5 broker costs, and combining sleeves with no edge does not create one;
a portfolio only changes the variance and the shape of the day P&L. This round makes that a measured statement on all 14 MT5 broker symbols at once instead of a claim.

DATA: MT5 M1 bid / ask (forex/data/<symbol>_M1_ticks_full.parquet, server clock = New York + 7 h), 14 symbols: US100.cash, US500.cash, US30.cash, US2000.cash (US
indices), GER40.cash, UK100.cash, FRA40.cash (European indices, the new conversion target), XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF (forex + gold, new
for the six FX pairs at the daily-ticket scale). Crypto excluded (the trader's constraint). 2021-09-20 .. 2026-10-02.
SESSIONS (New York time, fixed): US indices 09:30-16:00 (>= 370 bars, first bar 09:30); EU indices 03:00-11:30 (>= 450 bars, first bar 03:00; their cash open is 03:00 NY
except 1-3 weeks a year when the US and EU clocks change on different dates: disclosed, not corrected); FX + gold 03:00-12:00 (London open to the NY lunch, >= 500 bars).

TICKET MECHANICS (Round 321 / 324, unchanged, every symbol): stop = 0.25 x mean session high-low of the last 20 sessions, target = k x stop for k in the table's ladder
(1.5, 2.5, 4, 6, 9), stop wins a bar that touches both, else exit at the last session bar. Real fills: a long buys the ASK open and exits on the BID; a short sells the BID
open and exits on the ASK. Slippage allowance 0.4 bp at entry + 0.2 bp on a stop (Round 321's 1.0 / 0.5 US100 points at 25,000), commission 0.6 bp round trip on FX
($6 a lot), 0.2 bp on gold, 0 on index CFDs.

THE SLEEVE LIBRARY (every family generated so far that works at the daily-ticket scale, each converted to every symbol; refinement = the variants listed, all counted):
  LONG / SHORT                         drift (Round 321); entry at the session open
  PRIOR_F / PRIOR_X                    follow / fade the previous session's close-to-close return (Rounds 321, 323)
  PRE_F / PRE_X                        follow / fade the move from the previous session's close to this open (US: overnight gap; EU / FX: the Asia session) (Round 323)
  DRIVE_F_T / DRIVE_X_T, T 30/60/120   follow / fade the move since the open, entry T minutes after the open (Rounds 324, 332, 333, 338: the 10:30 lead is DRIVE_F_60)
  VWAP_F_T / VWAP_X_T, T 60/120        follow / fade the price's side of the session VWAP (tick-volume weighted) at T (the VWAP-stretch family, Rounds 294, 309, 310)
  ORB_F_M / ORB_X_M, M 15/30/60        first bar CLOSE outside the first-M-minute range before open + 180 min, entry next bar (opening range breakout / quantstack, Round 340)
  TSM_F_N / TSM_X_N, N 20/60           follow / fade the previous close vs its N-session mean (time-series momentum: the gold SuperTrend / Donchian family, Round 307)
  DIP_X_z / DIP_F_z, z 1.5/2.0         fade / follow a 3-session move of >= z sigma (dip-reversal, Rounds 285-305), both directions
  DIP_LONG_2                           indices only: long after a 3-session fall of >= 2 sigma (the original Round 285 lead)
  FOMC_LONG                            indices + gold: long the ASK at 14:00 NY the day before a scheduled statement, exit the BID at 13:59 on the statement day (Rounds
                                       328, 337); stop 0.5 x the 20-session range (an overnight hold), same k ladder; booked on the statement day
  Per symbol 30 cells + DIP_LONG_2 on 7 indices + FOMC on 8 = 435 cells.
NOT RE-RUN, with the reason (disclosed): the 1-minute signal strategies (Reversal Detector, ICT stack, FVG + VWAP killzone, exhaustion / VWAP-stretch fades, seconds-scale
HF, POC / volume-profile legs, the two EAs, BTC) were each measured on MT5 broker bid / ask data, most on these FX pairs too (Rounds 290, 294, 302, 306, 308-315, 335-336, 340), at
-0.07 to -0.25 R a trade net: a negative-expectancy sleeve can only lower a portfolio's pass probability. Their daily-scale analogues are in the library above.

SCREEN STATISTIC (Round 333's, every cell): on every traded day excess = 0.5 x (mean over k of R_side - mean over k of R_opposite) = the R gained over the coin flip on the
same ticket (spread and costs are paid by both sides, so a positive excess is direction skill, not drift alone; for LONG it IS drift). One-sided day-bootstrap p of the IS mean
(2,000 draws, seed 343). IS = sessions before 2024-01-01, OOS = from 2024-01-01. Cells with < 15 IS traded days are not testable (FOMC cells have about 17 IS meetings).
CONFIRMED CELL (fixed now): Benjamini-Hochberg q = 0.10 over all 435 IS p-values, AND OOS mean excess > 0 with OOS one-sided p < 0.10. OOS is read only for BH survivors in
the decision; it is printed for all cells, marked descriptive.

THE MASTERS (replayed day by day through the 1-Step rules on the US100 trading calendar; dates the US is closed are skipped, disclosed):
  BASE    the deployed policy: coin flip on US100.cash at the open (the current best, Round 296 / replication on MT5 broker fills)
  H1      SCREEN MASTER: every confirmed cell (empty if none survive: then H1 = no strategy and BASE stays)
  H2      LEADS MASTER (fixed now, before any of this round's numbers): US100 + US500 DRIVE_F_60, US100 + US500 FOMC_LONG, US100 + US500 DIP_LONG_2 (the leads the state
          page lists; US30 / US2000 drive follow excluded because Rounds 332-333 did not confirm them)
  NAIVE   descriptive overfit check: up to 20 cells with IS mean > 0 and unadjusted IS p < 0.05 (the highest IS t): what "refine until it looks good" does out of sample
  DIV     descriptive: coin flip at the open on all 14 symbols at once (does diversification alone help the 1-Step?)
SIZING (every master): the deployed table (forex/specs/round275_onestep_policy_risk1000.npz) gives (risk, k) from the account state each day; day risk = min(m x risk,
0.9 x room to the nearer floor, $5,000 / k so the best-day rule cannot bind), skipped under $250; split equally over the sleeves active that day; every ticket uses the
day's k. FILLER: on a day with no active sleeve the master either stays flat or trades BASE's coin ticket. The two knobs m in {0.5, 1, 1.5, 2} and filler in {off, on} are
chosen per master (BASE: m only) by the IS 57-day pass probability, then frozen for OOS. COIN tickets: 20 random draws per start (seed 343).
WINDOWS: every start day; IS windows start and end before 2024-01-01; OOS windows start from 2024-01-01 and end by the last day. Horizon 57 trading days (the trader's deadline,
the standing protocol); 120 and 250 (MT5 1-Step has no time limit) reported with the 57-day knobs. Pass = balance > $110,000 with the best-day rule met.
DECISION (fixed now): a master (H1 or H2) REPLACES BASE only if its OOS 57-day pass probability >= BASE's OOS + 8 points AND the 90% lower bound of a circular block
bootstrap (blocks of 57 starts, 2,000 draws) of the paired per-start difference is > 0 AND its IS pass probability >= BASE's IS. Otherwise BASE stays. NAIVE and DIV
never replace BASE. Not widened after the run.
POWER (honest): OOS has about 690 sessions = about 12 independent 57-day windows, so a pass-probability difference under about 12-15 points is inside noise; a day-level
cell excess of +0.05 R has an s.e. of about 0.05 R on ~500 IS days, so BH over 435 cells only finds effects of roughly +0.15 R or more.
DRY-RUN COUNTS (sessions and event counts only, no R read): 435 cells. Tradable IS / OOS sessions: US100 531 / 684, US500 532 / 684, US30 532 / 684, US2000 465 / 684,
GER40 520 / 698, UK100 538 / 691, FRA40 555 / 663, XAUUSD 558 / 710, the six FX pairs 571-572 / 713-714. FOMC meetings: 40 on US100 / US500 / US30 / UK100 / XAUUSD,
37 US2000 / GER40, 36 FRA40. |z3| >= 2 days 49-78 per symbol. ORB breaks on 896-1,285 sessions per symbol and range length.
UNIT CHECK (before the run): this file's ticket code against Round 321's trade_R on 1,211 common US100 sessions: identical to 0.01 R on 99.4-100% of tickets at every k and
side; the rest differ because this file accepts sessions with >= 370 bars (Round 321: 380), which changes a few 20-session ranges.
"""
import os, sys, json, time
os.environ["ROUND_DATA"] = "mt5broker"; os.environ["ROUND_FILLS"] = "ask"
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..")); sys.path.insert(0, ROOT)
from mt5 import onestep as OS
from mt5 import clock

KS = [float(k) for k in OS.Policy().ks]
SPLIT = pd.Timestamp("2024-01-01")
SEED = 343
US, EU, FX = "US", "EU", "FX"
SYMBOLS = {"US100.cash": US, "US500.cash": US, "US30.cash": US, "US2000.cash": US, "GER40.cash": EU, "UK100.cash": EU, "FRA40.cash": EU,
           "XAUUSD": FX, "EURUSD": FX, "GBPUSD": FX, "USDJPY": FX, "AUDUSD": FX, "USDCAD": FX, "USDCHF": FX}
SESSION = {US: (570, 960, 370), EU: (180, 690, 450), FX: (180, 720, 500)}       # open minute, close minute (exclusive), minimum bars
COMM_BP = {s: (0.6 if c == FX else 0.0) for s, c in SYMBOLS.items()}; COMM_BP["XAUUSD"] = 0.2
SLIP_E_BP, SLIP_S_BP = 1.0 / 25000 * 1e4, 0.5 / 25000 * 1e4
ENTRIES = ("T0", "T30", "T60", "T120", "ORB15", "ORB30", "ORB60", "FOMC")
INDICES = [s for s, c in SYMBOLS.items() if c in (US, EU)]
FOMC_SYMS = INDICES + ["XAUUSD"]
LEADS = [("US100.cash", "DRIVE_F_60"), ("US500.cash", "DRIVE_F_60"), ("US100.cash", "FOMC_LONG"), ("US500.cash", "FOMC_LONG"),
         ("US100.cash", "DIP_LONG_2"), ("US500.cash", "DIP_LONG_2")]
BIG = 10**9


def load_full(sym):
    d = os.environ.get("MT5BROKER_DATA_DIR") or os.path.join(ROOT, "mt5", "data")
    raw = pd.read_parquet(os.path.join(d, f"{sym}_M1_ticks_full.parquet"))
    idx = clock.server_to_ny(raw["time"].to_numpy())
    b = pd.DataFrame({"o": raw["open"].to_numpy(), "h": raw["high"].to_numpy(), "l": raw["low"].to_numpy(), "c": raw["close"].to_numpy(),
                      "ao": raw["ask_open"].to_numpy(), "ah": raw["ask_high"].to_numpy(), "al": raw["ask_low"].to_numpy(), "ac": raw["ask_close"].to_numpy(),
                      "v": raw["tick_volume"].to_numpy().astype(float)}, index=idx).sort_index()
    return b[~b.index.duplicated(keep="first")]


def ladder(a, i0, i1, side, stop, comm_bp):
    """R at every k of one ticket entered at the open of bar i0 and run to bar i1 - 1 (inclusive) of the arrays a (bid o/h/l/c, ask o/h/l/c)."""
    if side == 1:
        entry, hi, lo, last = a["ao"][i0], a["h"][i0:i1], a["l"][i0:i1], a["c"][i1 - 1]
    else:
        entry, hi, lo, last = a["o"][i0], a["ah"][i0:i1], a["al"][i0:i1], a["ac"][i1 - 1]
    e_cost = (SLIP_E_BP + comm_bp) * 1e-4 * entry / stop
    s_cost = SLIP_S_BP * 1e-4 * entry / stop
    sl = entry - side * stop
    hs = (lo <= sl) if side == 1 else (hi >= sl)
    i_s = int(np.argmax(hs)) if hs.any() else BIG
    out = np.empty(len(KS))
    for j, k in enumerate(KS):
        tg = entry + side * k * stop
        ht = (hi >= tg) if side == 1 else (lo <= tg)
        i_t = int(np.argmax(ht)) if ht.any() else BIG
        if i_s <= i_t and i_s < BIG:
            r = -1.0 - s_cost
        elif i_t < BIG:
            r = k
        else:
            r = side * (last - entry) / stop
        out[j] = r - e_cost
    return out


def fomc_dates():
    d = pd.read_csv(os.path.join(HERE, "..", "data", "events", "fomc_statement_dates.csv"), parse_dates=["date"])["date"]
    return set(x for x in d if pd.Timestamp("2021-10-01") <= x <= pd.Timestamp("2026-10-03"))


def build_symbol(sym):
    """Per session day: features, sides of every rule and the R ladder of every entry for both sides. Returns (feature frame, R dict entry -> (n, 2, K))."""
    cls = SYMBOLS[sym]; o_min, c_min, min_bars = SESSION[cls]
    full = load_full(sym)
    t = full.index.hour * 60 + full.index.minute
    s = full[(t >= o_min) & (t < c_min) & (full.index.dayofweek < 5)]
    dkey = s.index.normalize()
    codes, starts = np.unique(dkey.values, return_index=True)
    ends = np.r_[starts[1:], len(s)]
    arr = {c: s[c].to_numpy() for c in ("o", "h", "l", "c", "ao", "ah", "al", "ac", "v")}
    first_min = (s.index.hour * 60 + s.index.minute).to_numpy()
    days, spans = [], []
    for d, a, b in zip(codes, starts, ends):
        if b - a >= min_bars and first_min[a] == o_min:
            days.append(pd.Timestamp(d)); spans.append((a, b))
    days = pd.DatetimeIndex(days)
    rng_ = pd.Series([arr["h"][a:b].max() - arr["l"][a:b].min() for a, b in spans], index=days)
    close = pd.Series([arr["c"][b - 1] for a, b in spans], index=days)
    opn = pd.Series([arr["o"][a] for a, b in spans], index=days)
    r20 = rng_.rolling(20).mean().shift(1)
    ret = np.log(close).diff()
    sig = ret.rolling(60).std().shift(1)
    z3 = (np.log(close / close.shift(3)) / (sig * np.sqrt(3))).shift(1)
    feat = pd.DataFrame(index=days)
    feat["r20"] = r20
    feat["prior"] = ret.shift(1)
    feat["pre"] = np.log(opn / close.shift(1))
    feat["z3"] = z3
    for n in (20, 60):
        feat[f"tsm{n}"] = np.sign(close - close.rolling(n).mean()).shift(1)
    fomc = fomc_dates() if sym in FOMC_SYMS else set()
    fidx = full.index
    farr = {c: full[c].to_numpy() for c in ("o", "h", "l", "c", "ao", "ah", "al", "ac")}
    n = len(days)
    R = {e: np.full((n, 2, len(KS)), np.nan) for e in ENTRIES}
    cols = {f"drive{T}": np.zeros(n) for T in (30, 60, 120)}
    cols.update({f"vwap{T}": np.zeros(n) for T in (60, 120)})
    cols.update({f"orb{M}": np.zeros(n) for M in (15, 30, 60)})
    for i, (d, (a, b)) in enumerate(zip(days, spans)):
        if not np.isfinite(r20.iloc[i]) or d < pd.Timestamp("2021-10-01"):
            continue
        stop = 0.25 * r20.iloc[i]
        x = {c: v[a:b] for c, v in arr.items()}
        m = b - a
        for e, i0 in (("T0", 0), ("T30", 30), ("T60", 60), ("T120", 120)):
            for si, side in enumerate((1, -1)):
                R[e][i, si] = ladder(x, i0, m, side, stop, COMM_BP[sym])
        o0 = x["o"][0]
        for T in (30, 60, 120):
            cols[f"drive{T}"][i] = np.sign(x["o"][T] - o0)
        tp = (x["h"] + x["l"] + x["c"]) / 3
        for T in (60, 120):
            vv = x["v"][:T]
            vw = (tp[:T] * vv).sum() / vv.sum() if vv.sum() > 0 else tp[:T].mean()
            cols[f"vwap{T}"][i] = np.sign(x["o"][T] - vw)
        for M in (15, 30, 60):
            hi, lo = x["h"][:M].max(), x["l"][:M].min()
            c = x["c"][M:min(180, m - 1)]
            brk = np.flatnonzero((c > hi) | (c < lo))
            if len(brk):
                j = M + int(brk[0])
                cols[f"orb{M}"][i] = 1.0 if x["c"][j] > hi else -1.0
                for si, side in enumerate((1, -1)):
                    R[f"ORB{M}"][i, si] = ladder(x, j + 1, m, side, stop, COMM_BP[sym])
        if d in fomc and i > 0:
            tin, tout = days[i - 1] + pd.Timedelta(hours=14), d + pd.Timedelta(hours=13, minutes=59)
            i0, i1 = fidx.searchsorted(tin), fidx.searchsorted(tout)
            if i0 < len(fidx) and fidx[i0] == tin and i1 < len(fidx) and fidx[i1] == tout:
                for si, side in enumerate((1, -1)):
                    R["FOMC"][i, si] = ladder(farr, i0, i1 + 1, side, 2 * stop, COMM_BP[sym] + 1.0)   # +1 bp: one night's swap allowance
    for k, v in cols.items():
        feat[k] = v
    feat["fomc"] = np.isfinite(R["FOMC"][:, 0, 0])
    return feat, R


def rule_sides(sym, feat):
    """rule -> (entry, side array in {-1, 0, 1})."""
    n = len(feat); one = np.ones(n)
    sp, pr = np.sign(feat["prior"].fillna(0).values), np.sign(feat["pre"].fillna(0).values)
    z3 = feat["z3"].values
    out = {"LONG": ("T0", one), "SHORT": ("T0", -one), "PRIOR_F": ("T0", sp), "PRIOR_X": ("T0", -sp), "PRE_F": ("T0", pr), "PRE_X": ("T0", -pr)}
    for T in (30, 60, 120):
        s = feat[f"drive{T}"].values
        out[f"DRIVE_F_{T}"], out[f"DRIVE_X_{T}"] = (f"T{T}", s), (f"T{T}", -s)
    for T in (60, 120):
        s = feat[f"vwap{T}"].values
        out[f"VWAP_F_{T}"], out[f"VWAP_X_{T}"] = (f"T{T}", s), (f"T{T}", -s)
    for M in (15, 30, 60):
        s = feat[f"orb{M}"].values
        out[f"ORB_F_{M}"], out[f"ORB_X_{M}"] = (f"ORB{M}", s), (f"ORB{M}", -s)
    for N in (20, 60):
        s = feat[f"tsm{N}"].fillna(0).values
        out[f"TSM_F_{N}"], out[f"TSM_X_{N}"] = ("T0", s), ("T0", -s)
    for z in (1.5, 2.0):
        big = np.where(np.isfinite(z3) & (np.abs(np.nan_to_num(z3)) >= z), np.sign(np.nan_to_num(z3)), 0.0)
        out[f"DIP_X_{z}"], out[f"DIP_F_{z}"] = ("T0", -big), ("T0", big)
    if sym in INDICES:
        out["DIP_LONG_2"] = ("T0", np.where(np.isfinite(z3) & (np.nan_to_num(z3) <= -2.0), 1.0, 0.0))
    if sym in FOMC_SYMS:
        out["FOMC_LONG"] = ("FOMC", feat["fomc"].values.astype(float))
    return out


def cell_series(sym, feat, R, entry, side):
    """Per day: the R ladder of the chosen side (n, K) (NaN where no trade) and the daily excess over the coin."""
    Rl, Rs = R[entry][:, 0], R[entry][:, 1]
    chosen = np.where((side > 0)[:, None], Rl, np.where((side < 0)[:, None], Rs, np.nan))
    opp = np.where((side > 0)[:, None], Rs, np.where((side < 0)[:, None], Rl, np.nan))
    ex = 0.5 * (np.nanmean(chosen, 1) - np.nanmean(opp, 1)) if np.isfinite(chosen).any() else np.full(len(side), np.nan)
    return chosen, ex


def boot_p(x, rng, draws=2000):
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return float("nan"), float("nan")
    idx = rng.integers(0, len(x), (draws, len(x)))
    return float(x.mean()), float((x[idx].mean(1) <= 0).mean())


def bh(p, q=0.10):
    p = np.asarray(p); n = len(p); o = np.argsort(p)
    thr = q * (np.arange(1, n + 1) / n)
    ok = p[o] <= thr
    k = np.max(np.flatnonzero(ok)) + 1 if ok.any() else 0
    keep = np.zeros(n, bool); keep[o[:k]] = True
    return keep


# ------------------------------------------------------------------------------------------------------------------ replay
def master_arrays(cal, cells, data):
    """Per calendar day: number of active cells and the mean R ladder over them (n_days, K)."""
    tot = np.zeros((len(cal), len(KS))); cnt = np.zeros(len(cal))
    for sym, rule in cells:
        feat, R, rules = data[sym]
        entry, side = rules[rule]
        chosen, _ = cell_series(sym, feat, R, entry, side)
        df = pd.DataFrame(chosen, index=feat.index).reindex(cal)
        v = df.values; ok = np.isfinite(v).all(1)
        tot[ok] += v[ok]; cnt[ok] += 1
    with np.errstate(invalid="ignore"):
        mean = tot / cnt[:, None]
    return cnt, mean


def run(start, h, cnt, mean, coin_R, coin_side, m, filler, pol):
    """One window. coin_R: (n, 2, K) US100 T0 ladder for the filler; coin_side: (n,) +-1 for this draw. Returns 1 if passed."""
    bal, hwm, pos, best = OS.INITIAL, OS.INITIAL, 0.0, 0.0
    end = min(start + h, len(cnt))
    for j in range(start, end):
        hwm = max(hwm, bal)
        floor = max(hwm - OS.TRAIL, bal - OS.DAILY_LOSS)
        if cnt[j] > 0:
            ladd = mean[j]
        elif filler and np.isfinite(coin_R[j, 0, 0]):
            ladd = coin_R[j, 0] if coin_side[j] > 0 else coin_R[j, 1]
        else:
            continue
        risk, k = pol.lookup(j - start, bal, hwm)
        if risk <= 0:
            continue
        ki = KS.index(k)
        risk = min(m * risk, 0.9 * (bal - floor), OS.MAX_TICKET_PAYOFF / k)
        if risk < OS.MIN_RISK_USD:
            continue
        pnl = risk * ladd[ki]
        bal += pnl
        if pnl > 0:
            pos += pnl; best = max(best, pnl)
        if bal > OS.TARGET and best <= 0.5 * pos:
            return 1
        if bal <= floor + 1e-6:
            return 0
    return 0


def pass_vec(starts, h, cnt, mean, coin_R, coin_sides, m, filler, pol, coin_driven):
    reps = coin_sides.shape[0] if coin_driven or filler else 1
    return np.array([np.mean([run(s, h, cnt, mean, coin_R, coin_sides[r], m, filler, pol) for r in range(reps)]) for s in starts])


def block_lb(diff, rng, block=57, draws=2000, q=0.10):
    n = len(diff); nb = int(np.ceil(n / block)); means = np.empty(draws)
    for b in range(draws):
        st = rng.integers(0, n, nb)
        idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        means[b] = diff[idx].mean()
    return float(np.quantile(means, q))


def main(dry):
    t0 = time.time(); rng = np.random.default_rng(SEED)
    data = {}
    for sym in SYMBOLS:
        feat, R = build_symbol(sym)
        data[sym] = (feat, R, rule_sides(sym, feat))
        print(f"  built {sym}: {len(feat)} sessions {feat.index[0].date()}..{feat.index[-1].date()}, {time.time() - t0:.0f}s", flush=True)
    cells = [(s, r) for s in SYMBOLS for r in data[s][2]]
    if dry:
        print(f"cells {len(cells)}")
        for sym in SYMBOLS:
            feat, R, rules = data[sym]
            ok = np.isfinite(R["T0"][:, 0, 0])
            is_n, oos_n = int((ok & (feat.index < SPLIT)).sum()), int((ok & (feat.index >= SPLIT)).sum())
            orb = {M: int(np.isfinite(R[f"ORB{M}"][:, 0, 0]).sum()) for M in (15, 30, 60)}
            dip2 = int((np.abs(np.nan_to_num(feat.z3.values)) >= 2).sum())
            print(f"{sym}: tradable {is_n} IS / {oos_n} OOS sessions, ORB breaks {orb}, |z3|>=2 days {dip2}, FOMC meetings {int(feat.fomc.sum())}")
        return
    # ---- screen
    rows = []
    for sym, rule in cells:
        feat, R, rules = data[sym]
        entry, side = rules[rule]
        _, ex = cell_series(sym, feat, R, entry, side)
        isd, oosd = feat.index < SPLIT, feat.index >= SPLIT
        n_is = int(np.isfinite(ex[isd]).sum())
        m_is, p_is = boot_p(ex[isd], rng) if n_is >= 15 else (float("nan"), float("nan"))
        m_oos, p_oos = boot_p(ex[oosd], rng)
        rows.append(dict(symbol=sym, rule=rule, n_is=n_is, n_oos=int(np.isfinite(ex[oosd]).sum()), ex_is=m_is, p_is=p_is, ex_oos=m_oos, p_oos=p_oos,
                         sd=float(np.nanstd(ex))))
    sc = pd.DataFrame(rows)
    testable = sc.p_is.notna()
    sc["bh"] = False
    sc.loc[testable, "bh"] = bh(sc.loc[testable, "p_is"].values)
    sc["confirmed"] = sc.bh & (sc.ex_oos > 0) & (sc.p_oos < 0.10)
    print(f"screen: {len(sc)} cells, testable {int(testable.sum())}, BH survivors {int(sc.bh.sum())}, confirmed {int(sc.confirmed.sum())}, {time.time() - t0:.0f}s", flush=True)
    print(sc.sort_values("p_is").head(15).to_string(float_format=lambda v: f"{v:.3f}"))
    print("by family (mean IS / OOS excess R over symbols):")
    sc["family"] = sc.rule.str.replace(r"_[0-9.]+$", "", regex=True)
    print(sc.groupby("family")[["ex_is", "ex_oos"]].mean().to_string(float_format=lambda v: f"{v:+.3f}"))
    # ---- masters
    cal = data["US100.cash"][0].index
    cal = cal[np.isfinite(data["US100.cash"][1]["T0"][:, 0, 0])]
    coin_R = data["US100.cash"][1]["T0"][np.isin(data["US100.cash"][0].index, cal)]
    coin_sides = np.where(np.random.default_rng(SEED).random((20, len(cal))) < 0.5, 1, -1)
    pol = OS.Policy()
    confirmed = [tuple(x) for x in sc.loc[sc.confirmed, ["symbol", "rule"]].values]
    naive = [tuple(x) for x in sc[(sc.ex_is > 0) & (sc.p_is < 0.05)].assign(t=lambda d: d.ex_is / (d.sd / np.sqrt(d.n_is))).sort_values("t", ascending=False)
             .head(20)[["symbol", "rule"]].values]
    masters = {"H1_SCREEN": confirmed, "H2_LEADS": LEADS, "NAIVE": naive}
    is_end = int(np.searchsorted(cal, SPLIT)); n = len(cal)
    res = {"cells_confirmed": confirmed, "naive_cells": naive, "leads": LEADS}

    def starts_for(h):
        return np.arange(0, is_end - h + 1), np.arange(is_end, n - h + 1)

    base_cnt, base_mean = np.zeros(len(cal)), np.zeros((len(cal), len(KS)))           # BASE = the coin filler on every day
    configs = {}
    is57, oos57 = starts_for(57)
    # BASE: coin on US100 (cnt = 0 everywhere, filler on)
    best = None
    for m in (0.5, 1.0, 1.5, 2.0):
        p = pass_vec(is57, 57, base_cnt, base_mean, coin_R, coin_sides, m, True, pol, True).mean()
        print(f"  BASE m={m}: IS {p:.3f}", flush=True)
        if best is None or p > best[0]:
            best = (p, m)
    configs["BASE"] = dict(cnt=base_cnt, mean=base_mean, m=best[1], filler=True, coin=True, is_pass=best[0])
    # DIV: coin on all 14 symbols, one draw per symbol per day, mean ladder (descriptive), m fixed at BASE's
    div_reps = []
    for r in range(coin_sides.shape[0]):
        tot = np.zeros((len(cal), len(KS))); cnt = np.zeros(len(cal)); rr = np.random.default_rng(SEED + 1 + r)
        for sym in SYMBOLS:
            feat, R, _ = data[sym]
            side = np.where(rr.random(len(feat)) < 0.5, 1.0, -1.0)
            ch, _ = cell_series(sym, feat, R, "T0", side)
            v = pd.DataFrame(ch, index=feat.index).reindex(cal).values; ok = np.isfinite(v).all(1)
            tot[ok] += v[ok]; cnt[ok] += 1
        with np.errstate(invalid="ignore"):
            div_reps.append((cnt, tot / cnt[:, None]))
    for name, cl in masters.items():
        if not cl:
            configs[name] = None; print(f"  {name}: no cells", flush=True); continue
        cnt, mean = master_arrays(cal, cl, data)
        best = None
        for filler in (False, True):
            for m in (0.5, 1.0, 1.5, 2.0):
                p = pass_vec(is57, 57, cnt, mean, coin_R, coin_sides, m, filler, pol, False).mean()
                print(f"  {name} m={m} filler={filler}: IS {p:.3f} (active days {int((cnt > 0).sum())})", flush=True)
                if best is None or p > best[0]:
                    best = (p, m, filler)
        configs[name] = dict(cnt=cnt, mean=mean, m=best[1], filler=best[2], coin=False, is_pass=best[0])
    out = {}
    for name, c in configs.items():
        if c is None:
            out[name] = None; continue
        row = dict(m=c["m"], filler=c["filler"], IS_57=float(c["is_pass"]), active_days=int((c["cnt"] > 0).sum()))
        for h in (57, 120, 250):
            _, oos = starts_for(h)
            v = pass_vec(oos, h, c["cnt"], c["mean"], coin_R, coin_sides, c["m"], c["filler"], pol, c["coin"])
            row[f"OOS_{h}"] = float(v.mean()); row[f"_vec_{h}"] = v
        out[name] = row
        print(f"  {name}: " + ", ".join(f"{k} {v:.3f}" if isinstance(v, float) else f"{k} {v}" for k, v in row.items() if not k.startswith("_")), flush=True)
    # DIV with BASE's m, no filler (every day has US100 at least)
    dv = {}
    for h in (57, 120, 250):
        _, oos = starts_for(h)
        dv[f"OOS_{h}"] = float(np.mean([pass_vec(oos, h, cnt, mean, coin_R, coin_sides, configs["BASE"]["m"], False, pol, False).mean() for cnt, mean in div_reps[:5]]))
    dv["IS_57"] = float(np.mean([pass_vec(is57, 57, cnt, mean, coin_R, coin_sides, configs["BASE"]["m"], False, pol, False).mean() for cnt, mean in div_reps[:5]]))
    out["DIV"] = dict(m=configs["BASE"]["m"], **dv)
    print("  DIV:", {k: round(v, 3) for k, v in dv.items()}, flush=True)
    # ---- decision
    brng = np.random.default_rng(SEED + 99)
    base = out["BASE"]
    for name in ("H1_SCREEN", "H2_LEADS", "NAIVE"):
        r = out.get(name)
        if not r:
            continue
        diff = r["_vec_57"] - base["_vec_57"]
        r["diff_OOS_57"] = float(diff.mean()); r["lb90"] = block_lb(diff, brng)
        r["REPLACES_BASE"] = bool(name != "NAIVE" and r["diff_OOS_57"] >= 0.08 and r["lb90"] > 0 and r["IS_57"] >= base["IS_57"])
        print(f"  {name}: OOS diff vs BASE {r['diff_OOS_57']:+.3f}, block-bootstrap 90% lower bound {r['lb90']:+.3f}, replaces BASE: {r['REPLACES_BASE']}")
    for r in out.values():
        if r:
            for k in [k for k in r if k.startswith("_vec")]:
                r.pop(k)
    res.update(masters=out, screen=sc.to_dict("records"), seconds=time.time() - t0)
    json.dump(res, open(os.path.join(HERE, "round343_results_mt5broker_ask.json"), "w"), indent=1, default=str)
    sc.to_csv(os.path.join(HERE, "round343_screen_mt5broker_ask.csv"), index=False)
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
