#!/bin/bash
# Dead-weight cleanup, prepared 27 Oct 2026. the trader: "mt5broker research is also dead, analyze the whole project and get rid of dead weight".
# Run it yourself:   ! bash /d/finance/beginner-quant-research/london_aplus/cleanup_dead_weight.sh
# Checked before writing: no process runs from these folders, no active script imports them (london_aplus, apprentice, prop10k, ema12 replay app, tools, live_bot, hooks).
# Tracked files inside the repo folders can be restored with `git checkout -- <folder>`; the untracked parts of forex/data (about 300 MB) and everything outside the repo cannot.
LOG=/d/finance/beginner-quant-research/london_aplus/CLEANUP_LOG_2026-10-27.txt
echo "cleanup $(date '+%F %H:%M'). Free space before: $(df -h /d | tail -1 | awk '{print $4}')" > "$LOG"
rmx() { p="$1"; [ -e "$p" ] || { echo "skip (missing): $p" >> "$LOG"; return; }; s=$(du -sh "$p" 2>/dev/null | cut -f1); rm -rf -- "$p"; echo "deleted $p ($s)" | tee -a "$LOG"; }

# keep the one useful file from the worktree cleanup before _LEGACY_ARCHIVE goes
[ -f /d/finance/beginner-quant-research/_LEGACY_ARCHIVE/worktree_drafts_2026-09-20.zip ] && mv /d/finance/beginner-quant-research/_LEGACY_ARCHIVE/worktree_drafts_2026-09-20.zip /d/finance/beginner-quant-research/london_aplus/

# outside the repo: dead MT5 installs and data (MT5 broker / MT5 broker), the holding folder, FX tick history, reinstallable Python envs of the Fincept app
rmx /d/finance/mt5_mt5_tester          # 22 GB, has the LIVE login saved
rmx /d/finance/mt5_mt5_data            # 12 GB
rmx /d/finance/mt5_mt5broker_tester        # 1 GB
rmx /d/finance/_removed_mt5_2026-10-26 # 2.1 GB, the MT5 broker data I moved on 26 Oct
rmx /d/finance/ticks                  # 7.4 GB, MT5 FX / crypto ticks
rmx /d/finance/apps/fincept_data/uv-cache
rmx /d/finance/apps/fincept_data/venv-numpy1
rmx /d/finance/apps/fincept_data/venv-numpy2

# inside the repo: MT5 broker / MT5 broker dead folders with no reference from active work
cd /d/finance/beginner-quant-research || exit 1
for p in forex/data mt5broker forex/_ARCHIVE_MT5BROKER forex/factor_lab forex/self_improving forex/agent_lab forex/intraday_lab multi_fx_ea _LEGACY_ARCHIVE; do rmx "$p"; done

echo "Free space after: $(df -h /d | tail -1 | awk '{print $4}')" | tee -a "$LOG"
echo DONE | tee -a "$LOG"
# KEPT on purpose: mempalace (memory), scratch (live tool logs), data_mt5 (XAUUSD / DOW for blind batch 2), futures/data (Databento, BrokerAPI, merged micros),
# forex/apprentice, forex/prop10k, forex/ea_research (replay app), forex/tools, forex/specs / ea_batch / expert_advisors / forward_test (still referenced), si_ledgers, live_bot, reels, .gitnexus, .env.
