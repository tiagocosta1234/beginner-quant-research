"""
Round 324b (2026-10-03, DESCRIPTIVE control, no ledger row): is Round 324's MT5 broker follow-the-opening-drive result just being long?
Run after Round 324 on MT5 broker data (ROUND_DATA=mt5broker ROUND_FILLS=ask): for entry times 09:35 and 10:30 on US100 / US500 it reports P(pass 57d) of always-long, always-short, follow and a coin flip entered at the same time.
Post hoc (written after seeing Round 324's MT5 broker cells), so it carries no weight as a test; it exists to say what the follow result is NOT (drift).
"""
import numpy as np
import round324_post_open_drive_entry as Q, round321_long_bias_bold_play as R
from mt5 import onestep as OS

pol = OS.Policy()
for sym in ("NQ", "ES"):
    for name in ("0935", "1030"):
        df = Q.day_table_T(sym, Q.TS[name]); recs = df.reset_index().to_dict("records")
        rng = np.random.default_rng(1); starts = range(0, len(recs) - 57)
        P = lambda fn: np.mean([R.run_window(recs, s, 57, fn, pol, rng)[0] == "pass" for s in starts]) * 100
        long_ = P(lambda r, g: 1); short_ = P(lambda r, g: -1)
        fol = P(lambda r, g: 0 if r["move"] == 0 else int(np.sign(r["move"])))
        coin = np.mean([P(lambda r, g: 1 if g.random() < .5 else -1) for _ in range(5)])
        up = (df.real[df.real != 0] > 0).mean() * 100
        print(f"{sym} T={name}: always-long P {long_:.1f}  always-short {short_:.1f}  follow {fol:.1f}  coin {coin:.1f}   | up-day share {up:.1f}%")
