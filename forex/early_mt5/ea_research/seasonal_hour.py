"""Family K3 (sparse hour-of-day x market seasonality, execution at minute 5), exactly as registered in PREREG_SEASONAL_HOUR.md (the trader 2026-10-10).
   python -m mt5broker.ea_research.seasonal_hour --dev | --holdout
--dev: placebo check + 2024 / 2025 development numbers (contaminated, see the pre-registration). --holdout: opens 2026 ONCE, only if the development acceptance (1, 2) holds."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_research import confluence_h1 as H

HERE = Path(__file__).resolve().parent
DATA = H.DATA
LEDGER = HERE / "LEDGER.csv"
CACHE = Path("D:/finance/tmp/seasonal_hour_bars.parquet")
OUT_JSON = HERE / "SEASONAL_HOUR_STATE.json"
MARKETS = H.MARKETS
CLS = H.CLS
CLS_NAME = H.CLS_NAME
TARGET, SLIP = 0.0005, 1e-5
TRAIN_START = pd.Timestamp("2022-01-01").timestamp()
PER = {"Y2024": ("2024-01-01", "2024-12-31"), "Y2025": ("2025-01-01", "2025-12-31"), "DEV": ("2024-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def load_market(m: str) -> pd.DataFrame:
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao", "bc", "ac"]).sort_values("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo) & (d.ac >= d.bc) & (d.bc > 0)]
    hb = (d.t // 3600).to_numpy("int64"); g = d.groupby(hb, sort=True); f, l = g.first(), g.last()
    mid0 = (f.bo + f.ao) / 2; c = (l.bc + l.ac) / 2
    d5 = d[(d.t % 3600) >= 300]; g5 = d5.groupby((d5.t // 3600).to_numpy("int64")); f5 = g5.first(); m5 = (f5.bo + f5.ao) / 2; sp5 = (f5.ao - f5.bo) / m5
    b = pd.DataFrame({"hb": f.index.to_numpy(), "n": g.size().to_numpy(), "sp0": ((f.ao - f.bo) / mid0).to_numpy(), "sp1": ((l.ac - l.bc) / c).to_numpy(), "c": c.to_numpy(), "mid0": mid0.to_numpy()})
    b["m5"] = m5.reindex(b.hb).to_numpy(); b["sp5"] = sp5.reindex(b.hb).to_numpy(); b["T"] = b.hb * 3600
    dow = pd.to_datetime(b["T"], unit="s").dt.dayofweek.to_numpy()
    b = b[(b.n >= 20) & (dow < 5) & (b.sp0 < 0.05) & (b.sp1 < 0.05) & (b.sp5 < 0.05) & b.m5.notna()].reset_index(drop=True)
    b = b[~((np.log(b.c / b.mid0).abs() > 0.15))].reset_index(drop=True)
    lr = np.log(b.c).diff(); sig = np.sqrt((lr ** 2).ewm(alpha=0.02, min_periods=100, adjust=False).mean()); b["sig_prev"] = sig.shift(1)
    nxt = b["T"].shift(-1); b["nr"] = b.m5.shift(-1) / b.m5 - 1.0; b["x"] = np.log(b.m5.shift(-1) / b.m5) / b.sig_prev
    b["hour"] = ((b["T"] // 3600) % 24).astype(int); b["end"] = nxt
    b["tradable"] = ((nxt - b["T"]) == 3600) & b.hour.between(1, 22) & b.nr.notna() & (b.sig_prev > 0)
    b["date"] = pd.to_datetime(b["T"], unit="s").dt.normalize(); b["mkt"] = m
    return b[["mkt", "T", "date", "hour", "m5", "sp5", "nr", "x", "sig_prev", "end", "tradable"]]


def build(rebuild=False) -> pd.DataFrame:
    if CACHE.exists() and not rebuild: return pd.read_parquet(CACHE)
    P = pd.concat([load_market(m) for m in MARKETS], ignore_index=True).sort_values(["mkt", "T"]).reset_index(drop=True); CACHE.parent.mkdir(parents=True, exist_ok=True); P.to_parquet(CACHE); return P


def cells(tr: pd.DataFrame) -> pd.DataFrame:
    g = tr.groupby(["mkt", "hour"]); s = pd.DataFrame({"n": g.x.size(), "mean": g.x.mean(), "sd": g.x.std(ddof=1), "mean_bp": g.nr.mean() * 1e4, "sp5": g.sp5.median()})
    s["t"] = s["mean"] / (s["sd"] / np.sqrt(s["n"])); s["cost_bp"] = 2 * (0.5 * s.sp5 + SLIP) * 1e4
    s["sel"] = (s.n >= 300) & (s.t.abs() >= 4.0) & (s.mean_bp.abs() >= 1.5 * s.cost_bp); s["pos"] = np.where(s.sel, np.sign(s["mean"]), 0.0); return s


def train_rows(P: pd.DataFrame, Y: int) -> pd.DataFrame:
    return P[P.tradable & (P["end"] < pd.Timestamp(f"{Y}-01-01").timestamp()) & (P["T"] >= TRAIN_START)]


def placebo(tr: pd.DataFrame, seed=5) -> pd.DataFrame:
    rng = np.random.default_rng(seed); t = tr.copy(); key = t.mkt.astype(str) + "|" + t.date.astype(str)
    t["hour"] = t.groupby(key).hour.transform(lambda s: rng.permutation(s.to_numpy())); return t


def positions(P: pd.DataFrame, Y: int):
    tr = train_rows(P, Y); C = cells(tr); pc = cells(placebo(tr)); m = P.merge(C[["pos"]], left_on=["mkt", "hour"], right_index=True, how="left"); pos = m.pos.fillna(0.0).to_numpy() * P.tradable.to_numpy()
    return pos, C, pc


def build_R(P: pd.DataFrame, years):
    R = []; info = {}
    for Y in years:
        pos, C, pc = positions(P, Y); a, b = f"{Y}-01-01", f"{Y}-12-31" if Y < 2026 else "2026-09-30"; msk = ((P.date >= a) & (P.date <= b)).to_numpy()
        x = P[msk].assign(pos=pos[msk]); R.append(x); info[Y] = dict(C=C, pc=pc)
    return pd.concat(R, ignore_index=True), info


def parts_of(R: pd.DataFrame):
    R = R.sort_values(["mkt", "T"]); codes, uniq = pd.factorize(R.date, sort=True); R = R.assign(dc=codes); out = []
    for mk, g in R.groupby("mkt", sort=False):
        sg = g.sig_prev.to_numpy(); w = np.where(np.isfinite(sg) & (sg > 0), g.pos.to_numpy() * TARGET / np.where(sg > 0, sg, 1.0), 0.0)
        out.append((mk, w, np.nan_to_num(g.nr.to_numpy("float64")), (0.5 * g.sp5.to_numpy("float64") + SLIP), g.dc.to_numpy(), g.hour.to_numpy()))
    return out, uniq


def daily(parts, nd, shifts=None):
    gross = np.zeros(nd); net = np.zeros(nd)
    for j, (mk, w, nr, cs, dc, hour) in enumerate(parts):
        if shifts is not None: w = np.roll(w, shifts[j])
        dw = np.abs(np.diff(w, prepend=0.0)); gx = w * nr; gross += np.bincount(dc, weights=gx, minlength=nd); net += np.bincount(dc, weights=gx - cs * dw, minlength=nd)
    return gross, net


def evaluate(R: pd.DataFrame, per: str, perm=0, seed=9):
    a, b = PER[per]; W = R[(R.date >= a) & (R.date <= b)]; parts, uniq = parts_of(W); nd = len(uniq); g, n = daily(parts, nd); out = dict(net=H.stat(n, uniq), gross=H.stat(g, uniq), n=n, g=g, uniq=uniq, parts=parts)
    if perm:
        rng = np.random.default_rng(seed); obs = out["net"]["sharpe"]; null = []
        for _ in range(perm):
            sh = [int(rng.integers(24, max(25, len(p[1]) - 24))) for p in parts]; nn = daily(parts, nd, sh)[1]; null.append(nn.mean() / nn.std(ddof=1) * np.sqrt(252) if nn.std(ddof=1) > 0 else 0.0)
        out["p"] = (1 + sum(v >= obs for v in null)) / (1 + perm); out["null"] = float(np.mean(null))
    return out


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},seasonal_hour,{trial},{period},{s['n']},,,{s['bp']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def cell_oos(R: pd.DataFrame, per: str) -> pd.DataFrame:
    a, b = PER[per]; W = R[(R.date >= a) & (R.date <= b) & (R.pos != 0)].copy(); W["w"] = W.pos * TARGET / W.sig_prev; W["g"] = W.w * W.nr
    return W.groupby(["mkt", "hour"]).agg(gross_bp=("g", lambda s: s.sum() * 1e4), days=("g", "size"), pos=("pos", "first"))


def describe(R, info, years, per_tag):
    for Y in years:
        C = info[Y]["C"]; pc = info[Y]["pc"]; sel = C[C.sel]; ps = int(pc.sel.sum())
        print(f"  test {Y}: training cells {len(C)} | SELECTED {len(sel)} (placebo with shuffled hours selects {ps}: {100*ps/max(1,len(sel)):.1f}% of real) | class mix {sel.reset_index().mkt.map(CLS).map(CLS_NAME).value_counts().to_dict()}")
        top = sel.reindex(sel.t.abs().sort_values(ascending=False).index).head(8); print("     strongest cells (market, hour: t, mean bp, cost bp):", [(m, int(h), round(float(r.t), 1), round(float(r.mean_bp), 1), round(float(r.cost_bp), 1)) for (m, h), r in top.iterrows()])


def run_dev():
    P = build(); print("bars", len(P), "| tradable", int(P.tradable.sum())); R, info = build_R(P, (2024, 2025)); print("\n== selection ==")
    describe(R, info, (2024, 2025), "dev"); res = {}
    for per in ("Y2024", "Y2025", "DEV"):
        e = evaluate(R, per, perm=500 if per == "DEV" else 0); res[per] = e
        print(f"{per:6s} days {e['net']['n']:4d} | net Sharpe {e['net']['sharpe']:+5.2f} | daily t {e['net']['t']:+5.2f} | {e['net']['bp']:+6.2f} bp/day | PF {e['net']['pf']:4.2f} | maxDD {100*e['net']['dd']:5.1f}% | gross Sharpe {e['gross']['sharpe']:+5.2f} (gross {e['gross']['bp']:+.2f} bp/day)")
        ledger("K3", per, e["net"], f"net Sharpe {e['net']['sharpe']:+.2f}; gross Sharpe {e['gross']['sharpe']:+.2f}")
    e = res["DEV"]; print(f"permutation p (500 circular shifts, DEV) {e['p']:.4f}, null mean Sharpe {e['null']:+.2f}")
    ntr = sum(int((p[1][1:] != p[1][:-1]).sum()) for p in e["parts"]); print(f"position changes: {ntr/e['net']['n']:.1f} per day over {len(e['parts'])} markets")
    pos_share = {}
    for Y in (2024, 2025):
        co = cell_oos(R, f"Y{Y}"); pos_share[Y] = float((co.gross_bp > 0).mean()) if len(co) else float("nan"); print(f"  {Y}: selected cells traded {len(co)}, share with positive out-of-sample gross {100*pos_share[Y]:.0f}%; gross by class (bp):", {CLS_NAME[k]: round(v) for k, v in co.reset_index().assign(cl=co.reset_index().mkt.map(CLS)).groupby("cl").gross_bp.sum().items()})
    a1 = all(int(info[Y]["pc"].sel.sum()) < 0.1 * max(1, int(info[Y]["C"].sel.sum())) for Y in (2024, 2025)); a2 = res["Y2024"]["net"]["sharpe"] > 0 and res["Y2025"]["net"]["sharpe"] > 0 and res["DEV"]["net"]["t"] >= 2.0 and res["DEV"]["p"] <= 0.01
    print(f"\nacceptance 1 (placebo < 10% of real): {a1} | acceptance 2 (both years > 0, pooled t >= 2.0, p <= 0.01): {a2} => {'hold-out may be opened' if (a1 and a2) else 'CLOSED, hold-out stays unopened'}")
    OUT_JSON.write_text(json.dumps(dict(a1=bool(a1), a2=bool(a2), pooled_t=res["DEV"]["net"]["t"], p=res["DEV"]["p"], sharpe={k: res[k]["net"]["sharpe"] for k in ("Y2024", "Y2025", "DEV")}), indent=1), encoding="utf-8")


def run_holdout():
    st = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else None
    if not st or not (st["a1"] and st["a2"]): print("Development acceptance 1-2 not met: the 2026 hold-out stays CLOSED (registered rule)."); return
    P = build(); R, info = build_R(P, (2026,)); e = evaluate(R, "HOLD", perm=500); C = info[2026]["C"]; pc = info[2026]["pc"]; print(f"2026: selected cells {int(C.sel.sum())}, placebo {int(pc.sel.sum())}")
    print(f"HOLD days {e['net']['n']} | net Sharpe {e['net']['sharpe']:+.2f} | daily t {e['net']['t']:+.2f} | {e['net']['bp']:+.2f} bp/day | PF {e['net']['pf']:.2f} | maxDD {100*e['net']['dd']:.1f}% | gross Sharpe {e['gross']['sharpe']:+.2f} | permutation p {e['p']:.4f} (null mean {e['null']:+.2f})")
    co = cell_oos(R, "HOLD"); share = float((co.gross_bp > 0).mean()); print(f"selected cells traded {len(co)}, share with positive out-of-sample gross {100*share:.0f}%")
    ok = e["net"]["sharpe"] >= 0.5 and e["net"]["t"] >= 1.65 and share >= 0.6; print("acceptance 3 (Sharpe >= 0.5, t >= 1.65, >= 60% cells positive):", ok); ledger("K3", "HOLD", e["net"], f"net Sharpe {e['net']['sharpe']:+.2f}; cells positive {share:.2f}; passed {ok}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); ap.add_argument("--rebuild", action="store_true"); a = ap.parse_args()
    if a.rebuild: build(rebuild=True)
    if a.dev: run_dev()
    if a.holdout: run_holdout()


if __name__ == "__main__":
    main()
