"""DESCRIPTIVE ONLY (20 Oct 2026, the trader: 'before going to next setup run that check'). His rule for a sweep reversal (his words): confirmed by 'a gap in the reversal direction, or a significant displacement candle (BOS)'.
Sample: the entries among his 50 FX Replay trades (29 Apr-May 2025 + 21 Jan 2026, XAUUSD) that follow a sweep of the previous 60-candle extreme within the last 6 candles of the signal candle (MT5 1-minute mid) and have a stop (the unlogged 30 Jan 08:39 trade has none and is excluded). No parameter is tuned; nothing is a test, a bar or a rule; n is tiny.
For each trade, on MT5 broker bid / ask prices (a buy enters at the ask, exits at the bid; a sell the other way; same-minute stop + target = loss; time exit 17:00 local at the exit-side close; entry at the open quote of the minute AFTER the signal candle, the blind-replay convention):
  A = his actual entry (his logged stop and target levels).
  B = wait for the confirmation: the first candle k from the signal candle on (up to 30 candles) that completes a gap in the trade direction (low[k] > high[k-2] for a buy) OR is a displacement candle (body >= 1 x ATR14 in the trade direction) closing beyond the previous 5 candles' extreme; enter at the open quote of k+1 with HIS stop and target DISTANCES; no confirmation in 30 candles = no trade.
  C = as B but with HIS stop and target LEVELS (if the target is already reached at the confirmation the trade does not exist).
R is in units of his stop distance (R = P&L / his stop distance), so costs (spread) are included."""
import numpy as np, pandas as pd, datetime as dt
F = pd.read_csv("FXREPLAY_TRADES_2026-10-20.csv"); F["tm"] = pd.to_datetime(F.chart_entry); F = F[F.side.isin(["Buy", "Sell"]) & F.stop.notna()].copy()
d = pd.read_parquet("forex/data_mt5/XAUUSD_M1_rates.parquet").sort_values("t").reset_index(drop=True)
lis = pd.to_datetime(d.t, unit="s") - pd.Timedelta(hours=2); idx = {t: i for i, t in enumerate(lis)}
bo, bh, bl, bc, ao, ah, al, ac = (d[k].to_numpy() for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")); o, h, l, c = (bo + ao) / 2, (bh + ah) / 2, (bl + al) / 2, (bc + ac) / 2
ema = pd.Series(c).ewm(span=12, adjust=False).mean().to_numpy(); atr = pd.Series(h - l).rolling(14).mean().shift(1).to_numpy(); lisn = lis.to_numpy()
def sweep(i, s, w=6, back=60): return bool(l[i-w+1:i+1].min() < l[i-w-back+1:i-w+1].min()) if s > 0 else bool(h[i-w+1:i+1].max() > h[i-w-back+1:i-w+1].max())
def confirmed(k, s):
    gap = (l[k] > h[k-2]) if s > 0 else (h[k] < l[k-2]); body = (c[k] - o[k]) * s
    disp = body >= atr[k] and ((c[k] > h[k-5:k].max()) if s > 0 else (c[k] < l[k-5:k].min())); return bool(gap or disp), ("gap" if gap else "") + ("+" if gap and disp else "") + ("disp" if disp else "")
def run(i_entry_minute, s, stop, target, t_end):
    """enter at the open quote of minute index i_entry_minute; stop / target are PRICES; returns (R in price units, exit label, entry price)"""
    ent = ao[i_entry_minute] if s > 0 else bo[i_entry_minute]; sd = abs(ent - stop)
    if (s > 0 and (target <= ent or stop >= ent)) or (s < 0 and (target >= ent or stop <= ent)): return None
    j = i_entry_minute
    while j < len(d) and lisn[j] <= t_end:
        if s > 0: hs, ht = bl[j] <= stop, bh[j] >= target
        else: hs, ht = ah[j] >= stop, al[j] <= target
        if hs: return (stop - ent) * s, "stop", ent
        if ht: return (target - ent) * s, "target", ent
        j += 1
    jj = min(j, len(d) - 1); ex = bc[jj] if s > 0 else ac[jj]; return (ex - ent) * s, "time", ent
rows = []
for _, r in F.iterrows():
    s = 1 if r.side == "Buy" else -1; sig = idx[r.tm.floor("min")]
    if not sweep(sig, s): continue
    day_end = np.datetime64(r.tm.floor("D") + pd.Timedelta(hours=17)); sd0 = abs(r.entry - r.stop); td0 = abs(r.target - r.entry)
    A = run(sig + 1, s, r.stop, r.target, day_end)                      # his logged levels, entry at the quote after the signal candle
    kconf = None
    for k in range(sig, sig + 31):
        ok, lab = confirmed(k, s)
        if ok: kconf = (k, lab); break
    B = Cc = None
    if kconf:
        k, lab = kconf; ent = (ao if s > 0 else bo)[k + 1]; B = run(k + 1, s, ent - s * sd0, ent + s * td0, day_end); Cc = run(k + 1, s, r.stop, r.target, day_end)
    rows.append(dict(when=str(r.tm.floor("min")), side=r.side, wrong_side=bool((c[sig] - ema[sig]) * s < 0), sd=sd0, td=td0, A=A, conf=kconf, delay=(kconf[0] - sig) if kconf else None, B=B, C=Cc))
def R(x, sd): return np.nan if x is None else x[0] / sd
print("Sweep entries with a stop: %d (7 close on the wrong side of the EMA)\n" % len(rows))
print("%-17s %-4s %-5s | A his entry: R, exit | confirmation (candle, minutes later) | B same distances: R, exit, entry shift | C his levels: R, exit" % ("signal candle", "side", "wrong"))
tot = dict(A=[], B=[], C=[])
for x in rows:
    sd = x["sd"]; a = x["A"]; b = x["B"]; c_ = x["C"]
    print("%-17s %-4s %-5s | %+6.2f %-6s | %-22s | %s | %s" % (x["when"], x["side"], x["wrong_side"], R(a, sd), a[1] if a else "-", ("%s +%d min" % (x["conf"][1], x["delay"])) if x["conf"] else "none in 30 candles", ("%+6.2f %-6s %+.2f pts" % (R(b, sd), b[1], b[2] - a[2])) if b else "no trade", ("%+6.2f %s" % (R(c_, sd), c_[1])) if c_ else "no trade (target already passed / stop invalid)"))
    tot["A"].append(R(a, sd)); tot["B"].append(R(b, sd)); tot["C"].append(R(c_, sd))
A_, B_, C_ = (np.array(tot[k], dtype=float) for k in ("A", "B", "C"))
print("\nTOTALS (R per trade in units of his stop distance, MT5 broker bid / ask):")
print("  A his actual entries        : n %d, wins %d, mean R %+.3f, sum %+.2f" % (len(A_), (A_ > 0).sum(), np.nanmean(A_), np.nansum(A_)))
print("  B wait for confirmation     : trades %d of %d (%d with no confirmation in 30 candles), wins %d, mean R %+.3f, sum %+.2f" % (np.isfinite(B_).sum(), len(B_), np.isnan(B_).sum(), (B_ > 0).sum(), np.nanmean(B_), np.nansum(B_)))
print("  C confirmation, his levels  : trades %d of %d, wins %d, mean R %+.3f, sum %+.2f" % (np.isfinite(C_).sum(), len(C_), (C_ > 0).sum(), np.nanmean(C_), np.nansum(C_)))
m = np.isfinite(B_); print("  on the same trades that exist in B: A mean R %+.3f vs B mean R %+.3f" % (np.nanmean(A_[m]), np.nanmean(B_[m])))
print("  (n is tiny: a difference of one trade is +/- 1 R in the sum; this is a description, not evidence)")
