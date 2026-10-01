"""
Round 258 (2026-10-01): a new strategy search for US100 and gold only, built on two mechanisms, on MT5 broker's own
tick-built bid/ask bars. the trader: "we need a whole new strategy for US100 and gold".
PRE-REGISTRATION -- every choice below is fixed before any return of this round is computed.

DATA: MT5 US100.cash and XAUUSD M1 bid/ask bars built from ticks (forex/early_mt5/tick_bars.py --full), 2021-10-01..2026-09-30,
New York clock (forex/early_mt5/clock.py), the same real-session calendar as Round 255 (US100) / weekdays (gold). IS = before
2025-07-01, OOS = from 2025-07-01 (untouched until the confirmation step). Every window below stays inside one
MT5 broker server day, so it crosses no 17:00 New York rollover and pays no swap.

FAMILY S -- SESSION PREMIUM (mechanism: the equity premium accrues overnight, Lucca-Moench / Cliff-Cooper-Gulen; gold's
return concentrates in the Asia/London hours and around the London fix). One hypothesis per:
  * clock hour h (a long/short hold from the open of the h:00 bar to the close of the h:59 bar, Mon-Fri start dates;
    US100: h in 18-23, 0-8, 16 -- the RTH hours 9-15 were scanned in Round 250; gold: all hours except 17, which is
    the rollover): 16 + 23 = 39 hypotheses; a window needs its first bar within the first 10 minutes of the hour and its
    last bar at minute 40 or later (both instruments stop quoting around 16:49 and reopen around 18:05 New York, so the
    16:00 and 18:00 hours are partial windows, 16:00-~16:49 and ~18:05-18:59; found in the first dry run, before any
    return was computed);
  * overnight segment 18:05 -> 09:29 New York, start dates Sun-Thu, US100 and gold: 2 hypotheses.
  Statistic: mean of (bid return of the window / trailing 60-slot sd of that window's returns, >= 40, known before)
  over IS days, two-sided t; the direction is the sign of the IS mean (the traded side is the one that sign says).
FAMILY N -- SCHEDULED-NEWS REACTION (mechanism: a release hits a thin book; the first minutes over-shoot or start a
  drift). t0 in {08:30, 10:00, 14:00} New York, weekdays. Trigger move m = bid close of the t0+1 minute bar minus
  bid open of the t0 bar; a day is an EVENT when |m| >= 2.0 x the median |m| of that clock time over the prior 60
  days (>= 40). Entry = the open of the t0+2 bar at the real quote (long = ask, short = bid) + slippage; exit at the open
  of the bar H minutes later (H in {10, 30}), market, at the real quote, + slippage. Slippage: US100 1.0 pt each way
  (harsh 5.0), gold $0.20 each way (harsh $1.00). One hypothesis per (instrument, t0, H) = 12; the direction (follow
  the move or fade it) is the sign of the IS mean of sign(m) x return / trailing sd of that window's returns.
  Both families are tested together in ONE Benjamini-Hochberg pass at q = 0.10 over all 53 hypotheses (two-sided p).
NET: a long pays the ask at entry and gets the bid at exit, a short the mirror (real recorded quotes; family N adds the
  slippage above); no swap, no commission (CFD). A BH survivor must also have an IS NET mean > 0.
CONFIRMATION (OOS, >= 2025-07-01): a survivor is CONFIRMED if its OOS net mean > 0 with one-sided bootstrap P(mean > 0)
  >= 0.95 (20,000 resamples, seed 258) and >= 25 OOS trades.
IF ANY RULE IS CONFIRMED (portfolio stage, written only then, to this spec): the confirmed rules, each trade sized so one
  trailing sd of its window return = K dollars, K from (250, 500, 750, 1000, 1500, 2000, 3000) chosen on IS starts by
  P(live <= 63 trading days), exact MT5 2-Step replay (Round 255's Prague-day machinery, worst marks from the M1 path),
  candidate = the repo's four checks (ledger rule, OOS live >= 50%, >= the random-direction control median + 10pp,
  harsh-cost OOS mean daily $ > 0). Otherwise "no survivors". LEDGER: one row for the round, k = 443 (+ one per portfolio).

EXPECTATION: Round 248 found the overnight drift gross-positive but not significant on the futures proxy (rows 419), and the
news-fade lead (rows 191, 193) was chosen after its own loss. Most likely: no confirmed rule; the interesting numbers are
how big the swap-free overnight window is and what real news-minute spreads do to a fade.

POWER NOTES (--dry-run, counts only): 53 hypotheses (39 hour slots, 2 overnight segments, 12 news cells). Session hypotheses:
IS 724-925 windows each (the 18:00-23:00 hours only on Sun-Thu starts: ~725), OOS 256-324. News cells: IS 187-274 event
days, OOS 76-89 (about 25-30% of weekdays qualify as events at 2.0x the median reaction), so news rules are tested on
~80 OOS trades and their confirmation bar (P >= 0.95 with >= 25 trades) needs an effect of roughly 0.2 sd per trade or
more. For the session slots a +0.1 sd mean gives t ~ 3 in sample; BH over 53 tests at q = 0.10 needs |t| ~ 2.9-3.3 for
the first discovery.
"""
import os, sys, json, argparse, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import numpy as np
import pandas as pd
from scipy import stats
import idea_harness as H
import round255_manual_legs_mt5broker as R5

OOS = pd.Timestamp("2025-07-01")
INSTR = {"US100.cash": dict(slip=1.0, slip_h=5.0, hours=list(range(18, 24)) + list(range(0, 9)) + [16]),
         "XAUUSD": dict(slip=0.20, slip_h=1.00, hours=[h for h in range(24) if h != 17])}
SD_WIN, SD_MIN = 60, 40
FDR_Q, N_BOOT, SEED = 0.10, 20_000, 258
EVENT_T = {"0830": 8 * 60 + 30, "1000": 10 * 60, "1400": 14 * 60}
HOLDS = (10, 30)
TRIG_MULT = 2.0


def load_sym(sym):
    R5.SYM = sym
    G = R5.load()
    G.sym = sym
    return G


def valid_days(G, sym):
    if sym == "US100.cash":
        sess, _ = R5.sessions(G)
        return set(sess)
    return set(np.unique(G.nyd[(G.nyd + 3) % 7 < 5]))


def wk(nyd):
    return (np.asarray(nyd) + 3) % 7                       # Monday = 0


def window_table(G, valid, starts, ends):
    """Per window (given first/last M1 indices): bid return, long net, short net (price units)."""
    bo, bh, bl, bc, ao, ah, al, ac = G.px["base"]
    return dict(gross=bc[ends] - bo[starts], long_net=bc[ends] - ao[starts], short_net=bo[starts] - ac[ends])


def hour_windows(G, valid, hour):
    key = G.nyd * 100 + G.mod // 60
    sel = np.flatnonzero((G.mod // 60 == hour) & (wk(G.nyd) < 5))
    if len(sel) == 0:
        return None
    k = key[sel]
    cut = np.flatnonzero(np.r_[True, k[1:] != k[:-1]])
    s = sel[cut]; e = sel[np.r_[cut[1:] - 1, len(sel) - 1]]
    ok = (G.mod[s] % 60 <= 10) & (G.mod[e] % 60 >= 40) & np.isin(G.nyd[s], list(valid))
    s, e = s[ok], e[ok]
    return pd.DataFrame(dict(day=G.nyd[s], s=s, e=e, **window_table(G, valid, s, e)))


def overnight_windows(G, valid):
    d = np.unique(G.nyd)
    rows = []
    start_idx = np.searchsorted(G.ts, (pd.to_datetime(d.astype("datetime64[D]")) + pd.Timedelta(minutes=18 * 60 + 5)).values, side="left")
    for day, i0 in zip(d, start_idx):
        w = (day + 3) % 7
        if w not in (6, 0, 1, 2, 3) or i0 >= G.n or G.nyd[i0] != day or G.mod[i0] > 18 * 60 + 8:
            continue
        nxt = day + 1
        j = np.searchsorted(G.nyd, nxt, side="left")
        if j >= G.n or G.nyd[j] != nxt:
            continue
        m = np.searchsorted(G.ts, (pd.Timestamp(int(nxt) * 86400, unit="s") + pd.Timedelta(minutes=9 * 60 + 30)).to_datetime64(), side="left") - 1
        if m <= i0 or G.nyd[m] != nxt or G.mod[m] < 9 * 60 + 26:
            continue
        if (nxt not in valid) and G.sym == "US100.cash":
            continue
        rows.append((int(nxt), i0, m))
    a = np.array(rows)
    s, e = a[:, 1], a[:, 2]
    return pd.DataFrame(dict(day=a[:, 0], s=s, e=e, **window_table(G, valid, s, e)))


def event_windows(G, valid, t0, H_min, slip):
    bo, bh, bl, bc, ao, ah, al, ac = G.px["base"]
    d = np.unique(G.nyd)
    rows = []
    ts0 = np.searchsorted(G.ts, (pd.to_datetime(d.astype("datetime64[D]")) + pd.Timedelta(minutes=t0)).values, side="left")
    for day, i in zip(d, ts0):
        if (day + 3) % 7 >= 5 or day not in valid or i + 2 + H_min >= G.n:
            continue
        if G.nyd[i] != day or G.mod[i] != t0 or G.mod[i + 1] != t0 + 1 or G.mod[i + 2] != t0 + 2 or G.mod[i + 2 + H_min] != t0 + 2 + H_min:
            continue
        m = bc[i + 1] - bo[i]
        rows.append((int(day), i + 2, i + 2 + H_min, m, ao[i + 2] + slip, bo[i + 2] - slip, bo[i + 2 + H_min] - slip, ao[i + 2 + H_min] + slip, bo[i + 2], bo[i + 2 + H_min]))
    f = pd.DataFrame(rows, columns=["day", "s", "e", "m", "buy_in", "sell_in", "sell_out", "buy_out", "bid_in", "bid_out"])
    f["gross"] = f["bid_out"] - f["bid_in"]
    f["long_net"] = f["sell_out"] - f["buy_in"]
    f["short_net"] = f["sell_in"] - f["buy_out"]
    am = f["m"].abs()
    med = am.shift(1).rolling(SD_WIN, min_periods=SD_MIN).median()
    f["event"] = (am >= TRIG_MULT * med) & med.notna()
    return f


def stat_frame(f, signed=None):
    """z = gross / trailing sd (and net analogues) with the trailing sd known before each window."""
    sd = f["gross"].shift(1).rolling(SD_WIN, min_periods=SD_MIN).std()
    z = pd.DataFrame(dict(day=f["day"], sd=sd, zg=(f["gross"] / sd), zl=f["long_net"] / sd, zs=f["short_net"] / sd))
    if signed is not None:
        z["sgn"] = signed
    z["date"] = pd.to_datetime(z["day"].to_numpy().astype("datetime64[D]"))
    return z


def boot_p(v, n=N_BOOT, seed=SEED):
    v = np.asarray(v, float)
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for c in range(0, n, 2000):
        m = min(2000, n - c)
        out[c:c + m] = rng.choice(v, (m, len(v))).mean(1)
    return float((out > 0).mean())


def build_all():
    out = {}                               # name -> (z DataFrame, kind)
    G = {s: load_sym(s) for s in INSTR}
    V = {s: valid_days(G[s], s) for s in INSTR}
    for s in INSTR:
        for h in INSTR[s]["hours"]:
            w = hour_windows(G[s], V[s], h)
            if w is not None and len(w):
                out[f"S {s} hour {h:02d}"] = (stat_frame(w), "S")
        out[f"S {s} overnight 18:05-09:29"] = (stat_frame(overnight_windows(G[s], V[s])), "S")
        for tn, t0 in EVENT_T.items():
            for H_ in HOLDS:
                f = event_windows(G[s], V[s], t0, H_, INSTR[s]["slip"])
                z = stat_frame(f, signed=np.sign(f["m"]))
                z["event"] = f["event"].to_numpy()
                out[f"N {s} {tn} hold {H_}m"] = (z, "N")
    return G, out


def dry_run():
    G, out = build_all()
    for s in INSTR:
        print(f"{s}: M1 bars {G[s].n:,}, {pd.Timestamp(G[s].ts[0]).date()}..{pd.Timestamp(G[s].ts[-1]).date()}")
    print(f"{len(out)} hypotheses")
    for name, (z, kind) in sorted(out.items()):
        v = z.dropna(subset=["sd"])
        if kind == "N":
            v = v[v["event"]]
        print(f"  {name:36s} IS n {int((v['date'] < OOS).sum()):5d} / OOS n {int((v['date'] >= OOS).sum()):4d}")


def run(commit):
    t0 = time.time()
    G, out = build_all()
    hyp, store = [], {}
    for name, (z, kind) in out.items():
        v = z.dropna(subset=["sd", "zg"])
        if kind == "N":
            v = v[v["event"]].copy()
            v["zg"] = v["zg"] * v["sgn"]; v["zl"] = v["zl"]; v["zs"] = v["zs"]
        vi = v[v["date"] < OOS]
        if len(vi) < 40:
            hyp.append(dict(name=name, kind=kind, n_is=len(vi), mean_is=np.nan, t=np.nan, p=1.0, dir=0)); continue
        t, p = stats.ttest_1samp(vi["zg"], 0.0)
        hyp.append(dict(name=name, kind=kind, n_is=len(vi), mean_is=float(vi["zg"].mean()), t=float(t), p=float(p), dir=1 if vi["zg"].mean() > 0 else -1))
        store[name] = v
    Hy = pd.DataFrame(hyp).sort_values("p").reset_index(drop=True)
    n = len(Hy)
    Hy["bh_crit"] = (np.arange(1, n + 1) / n) * FDR_Q
    ok = Hy["p"] <= Hy["bh_crit"]
    Hy["bh_pass"] = Hy.index <= (ok[ok].index.max() if ok.any() else -1)
    print(f"{n} hypotheses; BH q={FDR_Q}: {int(Hy['bh_pass'].sum())} pass")
    print(Hy.head(12)[["name", "n_is", "mean_is", "t", "p", "bh_crit", "bh_pass"]].to_string(index=False))
    rules = []
    for r in Hy[Hy["bh_pass"]].itertuples():
        v = store[r.name]
        # traded side: the sign of the IS mean (for N: relative to sign(m) -> follow if +, fade if -)
        if r.kind == "S":
            net = v["zl"] if r.dir > 0 else v["zs"]
        else:
            # follow the move (sign(m) = +1 -> long): long net on up-move days, short net on down-move days
            sg = v["sgn"].to_numpy()
            follow = np.where(sg > 0, v["zl"], v["zs"])
            fade = np.where(sg > 0, v["zs"], v["zl"])
            net = pd.Series(follow if r.dir > 0 else fade, index=v.index)
        ni, no = net[v["date"] < OOS], net[v["date"] >= OOS]
        p_oos = boot_p(no) if len(no) >= 25 else float("nan")
        print(f"  survivor {r.name}: dir {r.dir:+d}, IS net {ni.mean():+.4f} sd (n {len(ni)}), OOS net {no.mean():+.4f} sd (n {len(no)}), P {p_oos:.3f}")
        if ni.mean() > 0:
            rules.append(dict(name=r.name, dir=int(r.dir), is_net=float(ni.mean()), oos_net=float(no.mean()), n_oos=int(len(no)), p_oos=p_oos,
                              confirmed=bool(len(no) >= 25 and no.mean() > 0 and p_oos >= 0.95)))
    conf = [x for x in rules if x["confirmed"]]
    k_total = H.ledger_count() + 1
    print(f"\nrules with IS net > 0: {len(rules)}; CONFIRMED out of sample: {len(conf)}")
    result = dict(n_hyp=n, n_bh=int(Hy["bh_pass"].sum()), table=Hy.to_dict("records"), rules=rules, confirmed=[x["name"] for x in conf])
    if not conf:
        print("NO SURVIVORS. Round ends here (pre-registered).")
        result["verdict"] = "NOT a candidate (no confirmed rule)"
        print("\nLedger row (append after review):")
        print(f"| {k_total} | 2026-10-01 | US100 + gold session-premium and scheduled-news windows (swap-free), {n} hypotheses, BH q=0.10 on IS -- {int(Hy['bh_pass'].sum())} pass, {len(rules)} IS net-positive, {len(conf)} confirmed OOS | Round 258 (pre-registered, US100 + gold new-strategy search) | {commit} | 0 | n/a | n/a | n/a / n/a | no edge |")
    else:
        result["verdict"] = "CONFIRMED RULES (portfolio stage pending)"
        print("Confirmed rules go to the MT5 broker replay stage (spec in the docstring).")
    json.dump(result, open(os.path.join(HERE, "round258_results.json"), "w"), indent=1, default=str)
    print(f"Saved round258_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", default="COMMIT")
    a = ap.parse_args()
    dry_run() if a.dry_run else run(a.commit)
