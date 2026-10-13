"""Post-release reversal (PREREG_REVERSAL.md). EXPLORATORY run on 2025-10-01..2026-08-15 (the profile was seen before the registration: cannot pass anything). The real test needs events >= 2026-08-16 re-exported read-only.
python -m forex.self_improving.events.reversal_lab"""
import numpy as np, pandas as pd
from forex.self_improving.events import tick_event_lab as T


def main():
    ev = T.events(False); tk = T.load_ticks(); usd = ev[ev.currency == "USD"]
    for name, sel in (("all strong USD", usd), ("tier-1 USD", usd[usd.tier1])):
        for delay, hold in ((60, 240), (60, 120), (30, 270)):
            fade = []
            for e in sel.itertuples():
                r = T.basket(tk, e, delay, hold)
                if r: fade.append(r[1] if e.S > 0 else r[0])
            f = np.array(fade); t = f.mean() / (f.std(ddof=1) / np.sqrt(len(f))) if len(f) > 2 else np.nan
            print(f"{name:15s} enter +{delay:2d}s hold {hold:3d}s FADE: n {len(f):3d} mean net {f.mean():+.2f} bp, t {t:+.2f}, win {100 * (f > 0).mean():.0f}%", flush=True)


if __name__ == "__main__":
    main()
