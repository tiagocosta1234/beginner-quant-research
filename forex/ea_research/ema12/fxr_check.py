"""FX Replay 'Trades' page -> blind log, with checks. python fxr_check.py [FXR.csv]   (default FXREPLAY_TRADES_2026-10-20.csv)
FXR.csv columns: group, chart_entry, realtime_entry, side (Buy/Sell), entry, stop, target, exit_chart, exit_price, R_fxr, note   (copied from the Trades page; Entry Date (Chart) = replay clock = local clock)
1. January 2026 rows are compared with BLIND_LOG_JAN2026.csv (read from screenshots) and the April-May 2025 rows with replay_mt5.csv (distances): every difference is listed.
2. R check: for every row with a stop, a win must have R = |target - entry| / |entry - stop| (to 0.011) and a loss -1: catches a mistyped stop or target.
3. --to-log GROUP OUT.csv writes a blind_score.py log for the rows of GROUP (date, ses, side, hhmm = chart entry minute, entry, stop, target, flag, pre; flag / pre left empty to fill from the trader's answers).
Prices only: no result is read except R_fxr in check 2."""
import sys, numpy as np, pandas as pd
a = [x for x in sys.argv[1:] if not x.startswith("--")]; F = pd.read_csv(a[0] if a and a[0].endswith(".csv") and "--to-log" not in sys.argv[:1] else "FXREPLAY_TRADES_2026-10-20.csv")
F["t"] = pd.to_datetime(F.chart_entry); F["date"] = F.t.dt.strftime("%Y-%m-%d"); F["hhmm"] = F.t.dt.strftime("%H:%M"); F["ses"] = np.where(F.t.dt.hour < 12, "London", "NY"); F["side1"] = F.side.map({"Buy": "L", "Sell": "S"})
F["risk"] = (F.entry - F.stop).abs(); F["rew"] = (F.target - F.entry).abs()
if "--to-log" in sys.argv:
    g, out = sys.argv[sys.argv.index("--to-log") + 1:sys.argv.index("--to-log") + 3]; Z = F[F.group == g]
    Z = Z[Z.stop.notna()].copy(); Z = Z[(Z.hhmm >= "08:00") & (Z.hhmm <= "08:15")] if g.startswith("jan") or g.startswith("batch") or g.startswith("ext") else Z
    pd.DataFrame(dict(date=Z.date, ses=Z.ses, side=Z.side1, hhmm=Z.hhmm, entry=Z.entry, stop=Z.stop, target=Z.target, flag="", pre="")).to_csv(out, index=False); print("wrote %d rows to %s" % (len(Z), out)); raise SystemExit
print("rows by group:", F.groupby("group").size().to_dict())
bad = F[F.stop.notna() & (F.R_fxr != -1) & ((F.rew / F.risk - F.R_fxr).abs() > 0.011)]; print("\nR check (win: R = target distance / stop distance; loss: -1): %d row(s) off" % len(bad)); print(bad[["chart_entry", "side", "entry", "stop", "target", "R_fxr"]].to_string(index=False) if len(bad) else "  all consistent")
L = pd.read_csv("BLIND_LOG_JAN2026.csv", dtype={"hhmm": str}); L = L[L.side.isin(["L", "S"])]; J = F[(F.group == "jan2026") & (F.hhmm >= "08:00") & (F.hhmm <= "08:15")]
print("\nJanuary 2026: %d log rows against %d FX Replay rows inside 08:00-08:15" % (len(L), len(J)))
for _, r in L.iterrows():
    m = J[J.date == r.date]
    if len(m) != 1: print("  %s: %d FX Replay rows in the window" % (r.date, len(m))); continue
    m = m.iloc[0]; d = []
    if m.side1 != r.side: d.append("side %s/%s" % (r.side, m.side1))
    if m.hhmm != r.hhmm: d.append("time %s/%s" % (r.hhmm, m.hhmm))
    for c in ("entry", "stop", "target"):
        if abs(m[c] - r[c]) > 1e-6: d.append("%s log %.3f / FX Replay %.3f (%+.3f)" % (c, r[c], m[c], r[c] - m[c]))
    if d: print("  %s: %s" % (r.date, "; ".join(d)))
print("  every other January field is identical")
missing = sorted(set(J.date) - set(L.date)); print("  FX Replay days not in the log:", missing or "none")
O = pd.read_csv("replay_mt5.csv"); A = F[F.group == "aprmay2025"]; miss = []; off = []
for _, r in O.iterrows():
    m = A[(A.date == str(r.day)) & (A.ses == r.ses) & (A.side1 == r.side)]
    if len(m) != 1: miss.append("%s %s %s" % (r.day, r.ses, r.side)); continue
    m = m.iloc[0]
    if abs(m.risk - r.risk) > 0.005 or abs(m.rew - r.rew) > 0.005: off.append("%s %s: stop dist %.3f/%.3f target dist %.3f/%.3f" % (r.day, r.ses, r.risk, m.risk, r.rew, m.rew))
print("\nApril-May 2025: replay_mt5.csv has %d trades, FX Replay rows %d | not found in FX Replay: %s | distances off: %s" % (len(O), len(A), miss or "none", off or "none"))
print("FX Replay April-May rows not in replay_mt5.csv:", sorted(set(zip(A.date, A.ses)) - set(zip(O.day.astype(str), O.ses))) or "none")
