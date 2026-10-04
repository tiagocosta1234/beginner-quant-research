"""
Build the batch manifest for testing the MQL5 CodeBase MT5 Expert Advisors in the MetaTrader 5 Strategy Tester (Round 347).

Input: a crawl of www.mql5.com/en/code/mt5/experts (catalog.json: id -> title; pages/<id>.html; all_src/<id>/*.mq5|*.mqh).
Output: forex/early_mt5/ea_batch/manifest.csv (one row per EA kept or excluded, with the reason) and forex/early_mt5/ea_batch/sources.zip (the kept sources).

  python forex/early_mt5/ea_batch/build_manifest.py <crawl_dir>

RULES (fixed before any test runs):
  KEEP a trading EA = a .mq5 with OnTick that sends orders by itself (OrderSend / CTrade Buy / Sell / BuyStop / SellStop / BuyLimit / SellLimit / PositionOpen / OrderOpen).
  EXCLUDE: no .mq5; no automatic orders (panels, managers, loggers, indicators); title naming a utility (panel, manager, guard, logger, monitor, calculator, copier,
    dashboard, report, exporter, notifier, telegram, auditor, profiler, visualizer, trailing utility, close all); any `#import` (DLL or external library calls: a
    security risk on the trader's second PC); WebRequest / socket calls (network); a crypto symbol as its only market (the trader: no crypto); more than one .mq5 (ambiguous main file:
    the largest one containing OnTick is taken, others treated as includes).
  SYMBOL (first match in title, then description, then source; MT5 broker names): gold / xau -> XAUUSD; silver / xag -> XAGUSD; the FX pairs by name; us30 / dow / dj30 -> US30.cash;
    nas / nasdaq / us100 / ustec / nq100 -> US100.cash; sp500 / s&p / us500 / spx -> US500.cash; dax / ger40 / de40 / ger30 -> GER40.cash; ftse / uk100 -> UK100.cash;
    cac / fra40 -> FRA40.cash; russell / us2000 -> US2000.cash; nikkei / jp225 -> JP225.cash; oil / wti -> USOIL.cash; brent -> UKOIL.cash; none -> EURUSD.
  TIMEFRAME: the source's own default timeframe input (`input ENUM_TIMEFRAMES ... = PERIOD_xx`, if not PERIOD_CURRENT), else the most frequent timeframe token in the
    title + description (M1 M5 M15 M30 H1 H4 D1), else H1.
"""
import collections
import html
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent

UTIL = re.compile(r"\b(panel|manager|guard|logger|monitor|calculator|copier|dashboard|report|exporter|notifier|notification|telegram|auditor|profiler|visuali[sz]er|"
                  r"close ?all|trade assistant|assistant|trainer|replay|inspector|journal|utility|tool)\b", re.I)
ORDERS = re.compile(r"OrderSend\s*\(|\.(Buy|Sell|BuyStop|SellStop|BuyLimit|SellLimit|PositionOpen|OrderOpen)\s*\(")
CRYPTO = re.compile(r"\b(btc|bitcoin|eth|ethereum|crypto|xrp|solana|doge)\b", re.I)
SYMS = [(r"\b(gold|xau\w*)\b", "XAUUSD"), (r"\b(silver|xag\w*)\b", "XAGUSD"), (r"\beur ?usd\b", "EURUSD"), (r"\bgbp ?usd\b", "GBPUSD"), (r"\busd ?jpy\b", "USDJPY"),
        (r"\baud ?usd\b", "AUDUSD"), (r"\busd ?cad\b", "USDCAD"), (r"\busd ?chf\b", "USDCHF"), (r"\bnzd ?usd\b", "NZDUSD"), (r"\bgbp ?jpy\b", "GBPJPY"),
        (r"\beur ?jpy\b", "EURJPY"), (r"\beur ?gbp\b", "EURGBP"), (r"\b(us30|dow|dj30|dji)\b", "US30.cash"), (r"\b(nas\w*|us100|ustec|nq100|ndx)\b", "US100.cash"),
        (r"\b(sp500|s&amp;p|s&p|us500|spx)\b", "US500.cash"), (r"\b(dax|ger40|de40|ger30)\b", "GER40.cash"), (r"\b(ftse|uk100)\b", "UK100.cash"),
        (r"\b(cac|fra40)\b", "FRA40.cash"), (r"\b(russell|us2000)\b", "US2000.cash"), (r"\b(nikkei|jp225|n225)\b", "JP225.cash"), (r"\b(brent|ukoil)\b", "UKOIL.cash"),
        (r"\b(wti|usoil|crude|oil)\b", "USOIL.cash")]
TF_INPUT = re.compile(r"input\s+ENUM_TIMEFRAMES\s+\w+\s*=\s*PERIOD_(M1|M5|M15|M30|H1|H4|D1)\b")
TF_TOKEN = re.compile(r"\b(M1|M5|M15|M30|H1|H4|D1)\b")


def description(page: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)); t = re.sub(r"\s+", " ", t)
    i = t.find("Go to Freelance")
    return t[i + 16:i + 4000] if i >= 0 else ""


def main(crawl: Path):
    cat = json.load(open(crawl / "catalog.json"))
    rows, keep_files = [], []
    for eid, title in cat.items():
        d = crawl / "all_src" / eid
        mq5 = sorted(d.glob("*.mq5")) if d.exists() else []
        page = (crawl / "pages" / f"{eid}.html").read_text(encoding="utf-8", errors="ignore") if (crawl / "pages" / f"{eid}.html").exists() else ""
        desc = description(page)
        r = dict(id=eid, title=title, main="", symbol="", period="", keep=False, reason="")
        if not mq5:
            r["reason"] = "no .mq5"; rows.append(r); continue
        srcs = {p: p.read_text(encoding="utf-8", errors="ignore") for p in mq5}
        allsrc = "\n".join(srcs.values()) + "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in d.glob("*.mqh"))
        main_ = max((p for p in srcs if "OnTick" in srcs[p]), key=lambda p: len(srcs[p]), default=None)
        if main_ is None:
            r["reason"] = "no OnTick"; rows.append(r); continue
        r["main"] = main_.name
        if UTIL.search(title):
            r["reason"] = "utility title"
        elif not ORDERS.search(allsrc):
            r["reason"] = "no automatic orders"
        elif re.search(r"#import\b", allsrc):
            r["reason"] = "#import (DLL / library): security"
        elif re.search(r"\bWebRequest\s*\(|\bSocket\w*\s*\(", allsrc):
            r["reason"] = "network calls"
        else:
            text = f"{title} {desc}"
            sym = next((s for pat, s in SYMS if re.search(pat, text, re.I)), None) or next((s for pat, s in SYMS if re.search(pat, srcs[main_], re.I)), None)
            if sym is None and CRYPTO.search(text):
                r["reason"] = "crypto only (the trader: no crypto)"
            else:
                m = TF_INPUT.search(srcs[main_])
                tf = m.group(1) if m else (collections.Counter(TF_TOKEN.findall(text)).most_common(1) or [("H1", 0)])[0][0]
                r.update(symbol=sym or "EURUSD", period=tf, keep=True, reason="kept")
                keep_files += [p for p in d.iterdir() if p.suffix in (".mq5", ".mqh")]
        rows.append(r)
    m = pd.DataFrame(rows)
    m.to_csv(HERE / "manifest.csv", index=False)
    with zipfile.ZipFile(HERE / "sources.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in keep_files:
            z.write(p, f"{p.parent.name}/{p.name}")
    print(m.reason.value_counts().to_string())
    k = m[m.keep]
    print(f"kept {len(k)}; symbols: {k.symbol.value_counts().to_dict()}; periods: {k.period.value_counts().to_dict()}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
