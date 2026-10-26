// Daily 15m bias from the BrokerAPI chart (the trader 26 Oct 2026: "yes switch the bias to brokerapi"). Read-only: run with yolo-chrome evalJs
// on the brokerapi.com/trade tab. Builds 15m candles (UTC-aligned) from the chart's loaded 1m bars, keeps only candles that opened at or
// before 07:45 UTC today (local = UTC since 25 Oct), EMA12 on closes (alpha 2/13, seeded with the first close).
// LONG if the 07:45 close > its EMA12 and that EMA12 > the EMA12 four candles earlier; SHORT if both are below / lower; else NEUTRAL.
(() => {
  const f = Array.from(document.querySelectorAll('iframe')).find(x => /^tradingview_/.test(x.id));
  if (!f) return { error: 'no chart iframe on this tab' };
  const s = f.contentWindow.chartWidget.model().mainSeries();
  const b = s.bars();
  const day = new Date().toISOString().slice(0, 10);
  const cut = Date.parse(day + 'T07:45:00Z') / 1000;
  const m = new Map();
  for (let i = b.firstIndex(); i <= b.lastIndex(); i++) {
    const v = b.valueAt(i); if (!v) continue;
    const k = Math.floor(v[0] / 900) * 900; if (k > cut) continue;
    const e = m.get(k);
    if (!e) m.set(k, { t: k, c: v[4], n: 1, last: v[0] });
    else { e.n++; if (v[0] > e.last) { e.c = v[4]; e.last = v[0]; } }
  }
  const bars = [...m.values()].sort((a, z) => a.t - z.t);
  if (bars.length < 6) return { error: 'too few 15m candles: ' + bars.length };
  let ema = null; const E = [];
  for (const x of bars) { ema = ema === null ? x.c : x.c * 2 / 13 + ema * 11 / 13; E.push(ema); }
  const L = bars.length - 1, last = bars[L];
  const r = { sym: s.symbol(), res: s.interval(), n15: bars.length, first_open: new Date(bars[0].t * 1000).toISOString(),
              last_open: new Date(last.t * 1000).toISOString().slice(0, 16), last_minutes: last.n, close: last.c,
              ema12: +E[L].toFixed(2), ema12_4_earlier: +E[L - 4].toFixed(2) };
  r.bias = (r.close > E[L] && E[L] > E[L - 4]) ? 'LONG' : (r.close < E[L] && E[L] < E[L - 4]) ? 'SHORT' : 'NEUTRAL';
  return r;
})()
