#!/bin/bash
# Round 347 cloud batch babysitter: run next to `python forex/ea_batch/cloud_run.py --workers N` (from the repo root):
#   nohup bash forex/ea_batch/cloud_babysit.sh > /root/ea_babysit.log 2>&1 &
# Every 30 s it truncates runaway MT5 journals in every worker prefix (chatty EAs write GBs of tester log; truncating frees the space
# even while the terminal holds the file open). Every EVERY new status rows it commits and pushes forex/ea_batch/results (git add -f),
# as the repo's configured user, so progress survives a container restart. When the batch process is gone it commits once more and exits.
cd "$(dirname "$0")/../.." || exit 1
ROOT=${EA_CLOUD_ROOT:-/root/mt5cloud}
EVERY=${EA_COMMIT_EVERY:-20}
BRANCH=$(git rev-parse --abbrev-ref HEAD)
STATUS=forex/ea_batch/results/status.csv
last=-1
commit() {
  [ -f "$STATUS" ] || return
  n=$(($(wc -l < "$STATUS") - 1))
  git add -f forex/ea_batch/results >/dev/null 2>&1
  git commit -q -m "Round 347 EA batch results: $n of 1,220 EAs (cloud, offline tester on MT5 broker M1 bars)" >/dev/null 2>&1
  for d in 2 4 8 16; do git push -q -u origin "$BRANCH" >/dev/null 2>&1 && break; sleep $d; done
  pushed=$([ "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$BRANCH")" ] && echo ok || echo FAILED)
  echo "COMMIT $(date -u +%H:%M) status_rows=$n deals_files=$(ls forex/ea_batch/results | grep -vc status) push=$pushed"
}
while true; do
  find "$ROOT"*/prefix/drive_c/Program\ Files/MetaTrader\ 5/Tester "$ROOT"*/prefix/drive_c/Program\ Files/MetaTrader\ 5/logs \
       -name "*.log" -size +30M -exec truncate -s 0 {} \; 2>/dev/null
  if [ -f "$STATUS" ]; then
    n=$(($(wc -l < "$STATUS") - 1))
    [ "$last" -lt 0 ] && last=$n
    if [ "$n" -ge $((last + EVERY)) ]; then commit; last=$n; fi
  fi
  if ! pgrep -f "[c]loud_run.py --workers" >/dev/null; then commit; echo "BATCH_ENDED"; exit 0; fi
  sleep 30
done
