#!/bin/bash
# Run the pre-registered analyze_reports.py UNCHANGED on a view of forex/ea_batch/results without the header-only CSVs that zero-deal EAs leave:
# its daily_pnl() returns an empty series without a date index for those and the IS/OOS split then raises a TypeError. Scoring is unaffected
# (an EA with no deals is untestable either way, and BH runs over testable EAs only); only EAs_with_results counts EAs with deals. The
# zero-deal count comes from status.csv. Outputs go where the pre-registration puts them (forex/ea_batch/results_summary.csv / .json).
#   bash forex/ea_batch/analyze_view.sh            # from the repo root
set -e
cd "$(dirname "$0")/../.."
R=$PWD/forex/ea_batch/results
V=${EA_BATCH_VIEW:-${TMPDIR:-/tmp}/ea_batch_view}
rm -rf "$V"; mkdir -p "$V"
ln -s "$R/status.csv" "$V/status.csv"
for f in "$R"/*.csv; do
  [ "$(basename "$f")" = status.csv ] && continue
  [ "$(wc -l < "$f")" -gt 1 ] && ln -s "$f" "$V/$(basename "$f")"
done
echo "EAs with deals: $(ls "$V" | grep -vc status) of $(($(wc -l < "$R/status.csv") - 1)) in status.csv"
EA_BATCH_RESULTS="$V" python3 forex/ea_batch/analyze_reports.py
