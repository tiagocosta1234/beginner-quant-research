"""the trader 2026-10-13: every session must end at +2,000 or -L (100%). A finisher gold position (direction of the last 20 business days) is opened at FIN_HOUR server time when the session is still unresolved, and held to 23:00 server time,
carried over nothing. Compared with D alone. python -m forex.self_improving.session.session_finisher"""
import numpy as np, pandas as pd
from forex.self_improving.session import session_lab as S, session_passrate as PR


def with_fin(T, hour, tm_bars=None):
    tr, lo, hi = T; tm, bc, sp = S.bars; rows = []
    for d in range(lo, hi + 1):
        if pd.Timestamp(d * 86400, unit="s").dayofweek >= 5: continue
        t0 = d * 86400 + hour * 3600; i = int(np.searchsorted(tm, t0)); j = int(np.searchsorted(tm, d * 86400 + 23 * 3600 - 60)); k = int(np.searchsorted(tm, t0 - 28 * 86400))
        if i >= len(tm) or j >= len(tm) or tm[i] - t0 > 1800 or i - k < 100 or j <= i: continue
        sd = 1 if bc[i] > bc[k] else -1; ent = bc[i] + sp[i] if sd > 0 else bc[i]; ex = bc[j] if sd > 0 else bc[j] + sp[j]
        rows.append((tm[i], tm[j], sd, ent, 1.0, sd * (ex - ent) * 1.0))
    out = {k_: np.concatenate([np.asarray(v), np.array([x[c] for x in rows], dtype=float)]) for c, (k_, v) in zip((0, 1, 2, 3, 4, 5), [(kk, tr[kk]) for kk in ("in_s", "out_s", "side", "entry", "q", "pl")])}
    for kk in tr:
        if kk not in out: out[kk] = np.concatenate([np.asarray(tr[kk]), np.zeros(len(rows), dtype=np.asarray(tr[kk]).dtype)]) if np.asarray(tr[kk]).ndim == 1 else tr[kk]
    out["fin"] = np.r_[np.zeros(len(tr["in_s"]), bool), np.ones(len(rows), bool)]
    o = np.argsort(out["in_s"], kind="stable"); return {k_: v[o] for k_, v in out.items()}, lo, hi


def stats(df, L):
    st, day = PR.boot(df); up = df[df.res == 1].pnl - S.UP; dn = -(df[df.res == -1].pnl + L)
    return dict(up=100 * (df.res == 1).mean(), down=100 * (df.res == -1).mean(), unres=100 * (df.res == 0).mean(), p44=100 * np.mean((st == 1) & (day < 44)), p120=100 * np.mean((st == 1) & (day < 120)), breach=100 * np.mean(st == 2), ov_dn_max=dn.max() if len(dn) else 0, worst=df.low.min())


def main():
    L = 1500.0; args = (L, 3.0, 1.0, 0.0, 3.0)
    for nm, T in (("MT5 12m", S.load("MT5")), ("FT 2025-26", S.load("FT", "2025-01-01", "2026-09-30"))):
        S.FINMODE = None; o = stats(S.run(*T, *args), L); print(f"{nm:10s} D alone                      : +2000 {o['up']:.0f}% -L {o['down']:.0f}% unresolved {o['unres']:.0f}% | P(pass<=44bd) {o['p44']:.1f}% breach {o['breach']:.1f}% | worst loss overshoot {o['ov_dn_max']:.0f}, worst day {o['worst']:.0f}", flush=True)
        for hour in (8, 12, 16):
            TF = with_fin(T, hour)
            for mode in ("safe", "max"):
                S.FINMODE = mode; o = stats(S.run(*TF, *args), L); print(f"{nm:10s} finisher {hour:02d}h {mode:4s}            : +2000 {o['up']:.0f}% -L {o['down']:.0f}% unresolved {o['unres']:.0f}% | P(pass<=44bd) {o['p44']:.1f}% breach {o['breach']:.1f}% | worst loss overshoot {o['ov_dn_max']:.0f}, worst day {o['worst']:.0f}", flush=True)
    S.FINMODE = None


if __name__ == "__main__":
    main()
