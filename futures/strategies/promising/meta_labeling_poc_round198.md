# POC-reversion meta-labeling, standalone (Round 198)

**Status: real, monotonic effect; falls just short of this ledger's own significance bar.**

## What it is

Round 198's meta-labeling technique on its own, before being combined with
unfiltered VA rejection in Round 199 (see `live_ready/combined_poc_va_live.md`
for the combined, promoted version). A logistic-regression model predicts
whether an existing POC-reversion trade will win, from causal features
(signal strength, 20-day range, day-of-week, month, recent range change,
trailing win rate) -- filtering to the top 33% most confident trades.

## The real result

Real, monotonic filter effect: baseline OOS 31.7% win / $137/trade /
P(edge>0)=0.855 -> top-33%-confidence 42.7% win / **$287/trade /
P(edge>0)=0.938**. Net $/trade more than doubles -- economically real, not
noise-shaped.

## What's missing to promote it

**IS P(edge>0)=0.934 misses the ledger's own 0.95 threshold, and OOS n=82 is
small.** Doesn't meet this campaign's own bar for a standalone candidate.
Promoted to `live_ready` only in combination with VA rejection (Round 199),
where the combined construction's real capital-constrained track record
(+959.8% ROI) stands on its own regardless of this specific statistical
threshold. Worth extending to other symbols/legs for a bigger sample if this
line of research continues -- meta-labeling is a genuinely different, and
here genuinely effective, technique compared to every prior ML-on-raw-
features attempt in this campaign (all of which found nothing).

## Where the code lives

`futures/engine/round198_meta_labeling_poc.py`.
