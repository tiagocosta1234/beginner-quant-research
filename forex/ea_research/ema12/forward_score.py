"""Scorer of the forward log (PREREG_FORWARD2026.md, Amendment 1). python forward_score.py FORWARD_LOG.csv [--today YYYY-MM-DD]      python forward_score.py --selftest
FORWARD_LOG.csv = the rows of the Notion view 'Forward log' (Claude exports them with notion-query-data-sources, e.g.
  SELECT url, createdTime, "date:Data:start", Direction, "date:Hora do registo:start", Entry, Stop, Target, "Tipo de alvo", "Largura FVG (pts)", Result
  FROM "collection://3ec46e08-4a8d-80da-a20c-000bb093fa28" WHERE Teste = 'Forward London 2026' ORDER BY "date:Data:start"  and adds the column `shot` after looking at the screenshot).
Columns: date (YYYY-MM-DD), side (Long / Short / No trade), hhmm (HH:MM, the last closed 1-minute candle, local clock), entry, stop, target, created_utc (Notion createdTime, UTC), tipo (FVG / High / Low / Outro or empty),
         width (FVG width in points or empty), shot (1 = the screenshot shows the same last candle and the same three prices, 0 = mismatch / missing, empty = not checked yet).
MT5 M1 bid / ask is read from the main PC's MT5 terminal (read-only: copy_rates_range; ask = bid + spread of the bar, exactly how XAUUSD_M1_rates.parquet was built; checked 14 Oct: bid OHLC identical on every minute).
Scorable (prereg section 3): Long / Short, entry / stop / target typed, hhmm inside 08:00-08:15, row created (local clock) at most 5 minutes after the logged candle CLOSED (hhmm + 1 min + 5 min), shot = 1, entry within 1.5 USD of the MT5 broker mid (+-5 min retime allowed, as in blind_score), day finished (MT5 broker bars to 17:00 local).
Unlogged weekdays (no row at all) since START are counted; more than 10% voids the look. Decision text follows the prereg: futility at >= 20 scorable (excess < +0.05), supported at F1 (44) / F2 (80) iff mean R >= +0.10 and P <= 0.03.
--selftest: rebuilds BLIND_LOG_JAN2026.csv as a forward log and must reproduce blind_score's January numbers through this whole path."""
import sys, os, datetime as dt, numpy as np, pandas as pd
from blind_score import score, TOL, CLOSE_HM
START = pd.Timestamp("2026-10-21").date(); TERMINAL = os.getenv("mt5_MT5_TERMINAL") or r"C:\Program Files\MT5 MT5 Terminal\terminal64.exe"
try:
    from zoneinfo import ZoneInfo; LIS = ZoneInfo("Europe/London"); ZoneInfo("UTC")
except Exception:
    LIS = None
def local(ts_utc):
    t = pd.Timestamp(ts_utc); t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    if LIS is not None: return t.tz_convert(LIS).tz_localize(None)
    y = t.year; last_sun = lambda m: max(d for d in pd.date_range("%d-%02d-01" % (y, m), periods=31) if d.month == m and d.weekday() == 6)    # EU summer time: last Sunday of March 01:00 UTC .. last Sunday of October 01:00 UTC
    return (t + pd.Timedelta(hours=1 if last_sun(3).tz_localize("UTC") + pd.Timedelta(hours=1) <= t < last_sun(10).tz_localize("UTC") + pd.Timedelta(hours=1) else 0)).tz_localize(None)
def load_days_mt5(d0, d1):
    import MetaTrader5 as mt5
    if not mt5.initialize(path=TERMINAL, timeout=30000): raise SystemExit("cannot attach to the MT5 broker terminal: %s" % (mt5.last_error(),))
    try:
        U = dt.timezone.utc; a = dt.datetime.combine(pd.Timestamp(d0).date() - dt.timedelta(days=1), dt.time(0), tzinfo=U); b = dt.datetime.combine(pd.Timestamp(d1).date() + dt.timedelta(days=2), dt.time(0), tzinfo=U)
        r = mt5.copy_rates_range("XAUUSD+", mt5.TIMEFRAME_M1, a, b)
    finally:
        mt5.shutdown()
    if r is None or len(r) == 0: raise SystemExit("no M1 bars returned for %s..%s" % (d0, d1))
    r = pd.DataFrame(r).rename(columns={"time": "t", "open": "bo", "high": "bh", "low": "bl", "close": "bc"}).sort_values("t").reset_index(drop=True); r["sp"] = r.spread / 100.0
    for b_, a_ in (("bo", "ao"), ("bh", "ah"), ("bl", "al"), ("bc", "ac")): r[a_] = r[b_] + r.sp
    z = r.sp <= 0; med = r[~z].sp.median()
    for b_, a_ in (("bo", "ao"), ("bh", "ah"), ("bl", "al"), ("bc", "ac")): r.loc[z, a_] = r.loc[z, b_] + med
    r["dt"] = pd.to_datetime(r.t, unit="s"); r["day"] = r.dt.dt.date; r["hm"] = r.dt.dt.hour * 60 + r.dt.dt.minute; r["mo"] = (r.bo + r.ao) / 2
    return {k: g.reset_index(drop=True) for k, g in r.groupby("day")}
def stats(Z):
    n = len(Z); L, S = Z.R_L.to_numpy(), Z.R_S.to_numpy(); mine = np.where(Z.side == "L", L, S); rng = np.random.default_rng(11); null = np.where(rng.random((200000, n)) < 0.5, L, S).mean(axis=1)
    return dict(n=n, wins=int((mine > 0).sum()), mean=mine.mean(), mirror=np.where(Z.side == "L", S, L).mean(), random=null.mean(), excess=mine.mean() - null.mean(), P=float((null >= mine.mean()).mean()), mine=mine)
def run(F, today, start=START, quiet=False):
    F = F.copy(); F["date"] = pd.to_datetime(F.date).dt.date; F["trade"] = F.side.astype(str).str.strip().str.lower().map({"long": "L", "short": "S", "l": "L", "s": "S"})
    days = load_days_mt5(min(F.date.min(), start), max(F.date.max(), today)); why = {}
    def bad(i, msg): why[i] = msg
    for i, r in F.iterrows():
        if pd.isna(r.trade): continue
        if pd.isna(r.entry) or pd.isna(r.stop) or pd.isna(r.target): bad(i, "entry / stop / target missing"); continue
        hm = int(str(r.hhmm)[:2]) * 60 + int(str(r.hhmm)[3:5])
        if not 8 * 60 <= hm <= 8 * 60 + 15: bad(i, "logged candle %s outside 08:00-08:15" % r.hhmm); continue
        cr = local(r.created_utc); close = pd.Timestamp(str(r.date) + " " + str(r.hhmm)[:5]) + pd.Timedelta(minutes=1)
        if cr > close + pd.Timedelta(minutes=5): bad(i, "row created %s, more than 5 min after the candle closed (%s)" % (cr.strftime("%H:%M:%S"), close.strftime("%H:%M"))); continue
        if cr < close - pd.Timedelta(minutes=1): bad(i, "WARNING row created %s BEFORE the logged candle closed (%s): check" % (cr.strftime("%H:%M:%S"), close.strftime("%H:%M")))
        if pd.isna(r.get("shot")): bad(i, "screenshot not checked yet"); continue
        if int(r.shot) != 1: bad(i, "screenshot does not match / missing"); continue
        g = days.get(r.date)
        if g is None or g.hm.max() < CLOSE_HM["London"] - 1: bad(i, "day not finished (no MT5 broker bars to 17:00 local yet)"); continue
    ok = F[F.trade.notna() & ~F.index.isin([i for i, m in why.items() if not m.startswith("WARNING")])]
    log = pd.DataFrame(dict(date=ok.date.astype(str), ses="London", side=ok.trade, hhmm=ok.hhmm.astype(str).str[:5], entry=ok.entry, stop=ok.stop, target=ok.target, flag=0, pre=1))
    Z = score(log, days, lag=1) if len(log) else pd.DataFrame(); mism = Z[Z.note.str.startswith("PRICE MISMATCH")] if len(Z) else Z
    if len(mism): Z = Z[~Z.note.str.startswith("PRICE MISMATCH")]
    wk = [d.date() for d in pd.date_range(start, today) if d.weekday() < 5 and d.date() in days and ((days[d.date()].hm >= 600) & (days[d.date()].hm <= 615)).sum() >= 10]
    logged = set(F.date); unlogged = [d for d in wk if d not in logged]
    if not quiet:
        print("rows %d (%d Long / Short, %d No trade) | weekdays with a London session since %s: %d | unlogged: %d (%.0f%%)%s" % (len(F), F.trade.notna().sum(), (F.side.astype(str).str.lower() == "no trade").sum(), start, len(wk), len(unlogged), 100 * len(unlogged) / max(len(wk), 1), "  >>> MORE THAN 10% UNLOGGED: THE LOOK IS VOID" if len(wk) and len(unlogged) / len(wk) > 0.10 else ""))
        if unlogged: print("  unlogged days:", ", ".join(str(d) for d in unlogged))
        for i, m in why.items(): print("  not scored %s %s: %s" % (F.loc[i, "date"], F.loc[i, "side"], m))
        for _, m in mism.iterrows(): print("  not scored %s: %s" % (m.date, m.note))
    keep = set(Z.date.astype(str)) if len(Z) else set(); Z.attrs["log"] = log[log.date.isin(keep)].reset_index(drop=True); Z.attrs["days"] = days    # for secondaries()
    return Z, F, why, unlogged, wk
def secondaries(Z):
    """PREREG_FORWARD2026 Amendment 2 (logging only): S1 own stop / 1.0 R and S2 fixed 10 / 10 at 2 lots on the scorable trades, the code of blind_secondaries.py."""
    import blind_secondaries as bs
    L, days = Z.attrs.get("log"), Z.attrs.get("days")
    if L is None or len(L) < 2: return None
    out = {}
    for sp, dd in (("feed spread", days), ("flat 0.48", bs.reprice(days))):
        print("\n=== secondary bracket readings (descriptive, Amendment 2), %s ===" % sp); out[sp] = bs.report(bs.variants(L, dd), "forward block")
    bs.readings(out["feed spread"]); return out
def report(Z, F, why, unlogged, wk):
    n = len(Z)
    if n < 2: return print("scorable trades: %d (nothing to score yet)" % n)
    s = stats(Z); print("\nscorable trades: %d | his side: wins %d mean R %+.3f | mirror %+.3f | random side %+.3f | excess %+.3f | P(random >= his) %.4f" % (n, s["wins"], s["mean"], s["mirror"], s["random"], s["excess"], s["P"]))
    for lab, ec in (("extra cost 0.30 USD", 0.30),):
        adj = ec / Z.risk.to_numpy() if "risk" in Z else 0; print("  (descriptive) %s: mean R %+.3f" % (lab, np.where(Z.side == "L", Z.R_L.to_numpy() - adj, Z.R_S.to_numpy() - adj).mean() if n else float("nan")))
    void = len(wk) and len(unlogged) / len(wk) > 0.10
    print("DECISION TEXT (prereg bars: supported iff mean R >= +0.10 and P <= 0.03; futility at >= 20 scorable if excess < +0.05):")
    if void: print("  look VOID: more than 10% of the weekdays are unlogged")
    elif n < 20: print("  collecting: %d of 20 scorable trades before the futility check, 44 for Look F1, 80 for F2" % n)
    elif s["excess"] < 0.05 and n < 44: print("  FUTILITY: excess %+.3f < +0.05 at n = %d: stop the log (no edge shown)" % (s["excess"], n))
    elif n < 44: print("  continuing: excess %+.3f >= +0.05 at n = %d; Look F1 at 44" % (s["excess"], n))
    else:
        look = "F2" if n >= 80 else "F1"; sup = s["mean"] >= 0.10 and s["P"] <= 0.03
        print("  Look %s at n = %d: %s (mean R %+.3f vs +0.10, P %.4f vs 0.03)%s" % (look, n, "SUPPORTED" if sup else "NOT supported", s["mean"], s["P"], "" if sup or look == "F2" else ("; futility (excess < +0.05): stop" if s["excess"] < 0.05 else "; continue to F2 at 80")))
    by = F.assign(d=F.date.astype(str)).drop_duplicates("d").set_index("d")      # one row per day (a second row on a day is never scored)
    tz = by.tipo.replace("", np.nan) if "tipo" in by else None
    if tz is not None:
        lab = tz.reindex(Z.date.astype(str)).fillna("unlabelled").to_numpy(); mine = np.where(Z.side == "L", Z.R_L, Z.R_S); share = np.mean(lab == "unlabelled")
        print("\ntarget type (descriptive): unlabelled %.0f%%%s" % (100 * share, " (more than 10%: split not reported)" if share > 0.10 else ""))
        if share <= 0.10:
            for t in sorted(set(lab)): print("  %-10s n %2d | wins %2d | mean R %+.3f" % (t, (lab == t).sum(), (mine[lab == t] > 0).sum(), mine[lab == t].mean()))
            if "width" in by: w = by.width.reindex(Z.date.astype(str)).to_numpy().astype(float); w = w[(lab == "FVG") & ~np.isnan(w)]; print("  FVG width (points): n %d, median %s" % (len(w), "%.2f" % np.median(w) if len(w) else "-"))
    secondaries(Z)
if __name__ == "__main__":
    if "--selftest" in sys.argv:
        J = pd.read_csv("BLIND_LOG_JAN2026.csv", dtype={"hhmm": str}); J = J[J.side.isin(["L", "S"])]; n_ = len(J)
        created = [(pd.Timestamp(r.date + " " + r.hhmm) + pd.Timedelta(minutes=2)) for _, r in J.iterrows()]    # synthetic: 2 minutes after the candle label (local clock) -> UTC
        utc = [(local_c.tz_localize(LIS).tz_convert("UTC") if LIS is not None else local_c - pd.Timedelta(hours=0)).strftime("%Y-%m-%dT%H:%M:%SZ") for local_c in created]
        F = pd.DataFrame(dict(date=J.date, side=J.side.map({"L": "Long", "S": "Short"}), hhmm=J.hhmm, entry=J.entry, stop=J.stop, target=J.target, created_utc=utc, tipo="", width=np.nan, shot=1))
        Z, F2, why, unl, wk = run(F, pd.Timestamp("2026-01-30").date(), start=pd.Timestamp("2026-01-02").date(), quiet=True); s = stats(Z)
        print("SELFTEST through the MT5 loader: n %d | wins %d | mean R %+.3f | mirror %+.3f | random %+.3f | excess %+.3f | P %.4f   (blind_score.py on the same log: n 20, wins 13, +0.008, -0.224, -0.107, +0.115, P 0.2547)" % (s["n"], s["wins"], s["mean"], s["mirror"], s["random"], s["excess"], s["P"]))
        print("not scored:", {F2.loc[i, "date"]: m for i, m in why.items()} or "none", "| unlogged January weekdays:", [str(d) for d in unl] or "none")
        so = secondaries(Z); fl = so["flat 0.48"]; s1, s2 = fl["S1 own stop / 1.0 R"]["mean"], fl["S2 fixed 10 / 10"]["mean"]     # this log is the screenshot version (6 Jan stop 4451.5, not 4451.068), so S1 may differ a little from blind_secondaries' +0.277; S2 does not depend on the stop
        print("selftest secondaries (flat 0.48): S1 %+.4f (blind_secondaries on the FXR log: +0.277) | S2 %+.4f (+0.176)" % (s1, s2)); assert abs(s2 - 0.176) <= 0.005 and abs(s1 - 0.277) <= 0.02, "secondaries selftest failed"; print("selftest secondaries ok")
        raise SystemExit
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a: raise SystemExit(__doc__)
    today = pd.Timestamp(sys.argv[sys.argv.index("--today") + 1]).date() if "--today" in sys.argv else dt.date.today()
    F = pd.read_csv(a[0], dtype={"hhmm": str}); report(*run(F, today))
