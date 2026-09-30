# Bounded meta-labeling plan (2026-09-30)

> **STATUS: BUILT and run as Round 228 (`round228_vwapz_meta_labeling.py`, pre-registered in `3b4b0ff`). Result: NOT a candidate (2 of 6 pre-registered gates passed) -- see the "Round 228" entry in `TRADING_JOURNAL.md`. Two deviations from this plan, both disclosed in the script's docstring: the base set is the leg's real sequential trades (3,411) rather than raw signals, and the label is sign(P&L) since the ATR-trail exit has no fixed profit barrier.** The rest of this document is the original plan, kept unchanged for reference.

the trader proposed "a massive machine learning that constantly iterates through the whole
dataset and learns until it can find the edge we're looking for," after watching a
/watch review of a meta-labeling walk-forward video. Flagged directly before building
anything: "iterate until it finds an edge" is definitionally overfitting at scale, and
today's own the trader confluence-filter branch (Rounds 223-226) is a live example of why --
a simple rule looked like a real, statistically-backed edge on first pass, then fell
apart under mechanism testing, fold-consistency checks, and independent-data
replication. A "massive" model searching unsupervised over the same ~4-7 years of
1-minute bars will produce many more results that look exactly that convincing before
they're checked, for the same reason: search enough of a noisy, low-signal dataset and
you are guaranteed to find something that looks good in-sample. the trader chose the
alternative: a bounded, disciplined version, same shape as every other round this
session -- plan now, build next session (the trader is switching Claude accounts to a fresh
usage pool; this doc exists so the new session doesn't need the conversation transcript
to pick this up).

## What this is NOT

Not a deep model, not an ensemble, not a feature/architecture search, not a loop that
reruns until a target metric is hit. Capacity is capped by design, not tuned against
results. If it fails honestly, it gets reported as a failure, same as Round 224-227
today.

## What's already been tried (don't re-test a disguised repeat)

Meta-labeling itself is not new here -- check `IDEA_LEDGER.md` k=380-381 and the journal
entries for Round 198/199 before building anything:

- **Round 198** (`round198_meta_labeling_poc.py`): gradient-boosted trees, binary
  win/loss label, on NQ POC-reversion trades only (Round 178's signal). Features:
  `|open-POC|/S`, `S` (recent vol level), day-of-week, month, trailing-20-trade win
  rate, trailing-20-day realized-range change. Single IS/OOS split (< / >= 2025-07-01,
  `idea_harness`'s own `OOS_START`). Result: filtering to top-33%-confidence trades
  showed a real IS/OOS lift (IS P=0.934, OOS P=0.938) but fires too rarely (~67
  trades/year) to be useful on its own -- not "no signal," but "not enough of it."
- **Round 199** (`round199_meta_labeling_va.py`): same construction, extended to
  NQ Value Area rejection (Round 184/186's signal). Result: meta-labeling made it
  WORSE (OOS AUC ~0.51, no better than random) -- VA rejection's own unfiltered
  baseline was already strong (OOS P=0.971), and filtering just threw away good
  trades. Combined resolution (`round199_combined_real_year.py`): use POC filtered +
  VA unfiltered, netted per day.

**Both of disciplined_bracket's own real legs (POC reversion, VA rejection) are
already meta-labeled.** A fresh attempt needs either a genuinely different base
signal, a genuinely different labeling/validation methodology (the two gaps below),
or both -- not a third re-skin of the same POC/VA construction.

## The two genuine gaps versus Round 198/199

1. **Base signal.** the trader's own two legs (`manual_strategy.py`, live today) have never
   been meta-labeled:
   - **VWAP-Z leg** (`round49_vwap_zscore.py`) -- a real mean-reversion signal (z-score
     >= 2.5 from session VWAP + a 1-bar reversal confirmation). The higher-priority
     target: unlike TOD, this leg has real, non-random entry logic, so an ML filter
     has a more plausible mechanism to find (does the SIZE of the z-score extreme,
     the market's recent trend context, volatility, or time-of-day predict which
     VWAP-Z reversions actually work?).
   - **TOD leg** (`round19_random_entry.py`) -- entries are literally uniformly random
     by construction (round19's own explicit design). Already confluence-filtered by
     a simple univariate trend rule and killed on independent data (Rounds 223-226).
     A multivariate ML filter could in principle find a nonlinear combination a
     univariate split couldn't -- but the sample is small (~340 raw signals over
     the full MNQ history, further split into training/test), and the entry itself
     carries zero information, so this is the lower-priority, more speculative target.
     Worth a pass only after VWAP-Z, not instead of it.
2. **Methodology.** The video (`/watch` review, 2026-09-30 journal entry) used two
   real safeguards neither Round 198 nor 199 used: a **purge gap** between the
   train-label window and the test window (avoid a trade whose outcome window
   straddles the split boundary leaking into the "unseen" side), and a **minimum-
   trades-per-fold filter** (reject any fold/parameter combination with too few
   trades, so a lucky-small-sample result can't pass just because it's rare).
   `idea_harness.py`'s own `resolve_bracket`/`resolve_trailing` resolvers already
   handle exits causally, but neither prior meta-labeling round explicitly purged
   the split boundary -- worth checking directly on re-implementation, not assumed
   either way.

## Recommended shape for the next attempt

- **Base signal**: the trader's VWAP-Z leg, MNQ full history (`round49_vwap_zscore.py`'s
  own `compute_session_vwap_z`/`build_zscore_signals`, unmodified -- reuse, don't
  reimplement, same as every prior round).
- **Label**: triple-barrier (win/loss/neutral), using the SAME real ATR-trailing exit
  the trader already uses (`round19_random_entry.TRAIL_ATR_MULT`), not a new invented exit --
  the point is to label the trades the trader actually takes, not a hypothetical variant.
- **Model**: L1-penalized logistic regression or linear SVM (matching the video's own
  choice) -- linear, regularized, automatic feature pruning via the lasso penalty.
  No tree ensembles or anything nonlinear for this first pass; capacity stays low on
  purpose given the sample size.
- **Features, fixed in advance, not searched**: z-score magnitude at entry, causal
  ATR-relative volatility (reuse `causal_atr15_lookup`), a trend-context feature
  (reuse Round 224's own causal 15-min EMA lookup -- already built, already tested as
  a standalone filter and found not to hold up alone, but worth including as ONE
  input among several rather than a standalone rule), time-of-day, same-session
  money-flow sign (reuse Round 220's real MFM construction), day-of-week. Cap the
  feature count (roughly 6-8, matching the video's own set) -- more features on a
  small sample raises overfitting risk without a corresponding reason to expect more
  signal.
- **Validation**: multi-fold walk-forward (not Round 198/199's single IS/OOS split) --
  reuse `round11_fvg_bias.FOLDS`' own expanding-window convention already used
  elsewhere in this ledger, WITH an explicit purge gap added at each fold boundary,
  and a minimum-trades-per-fold floor (reject any fold below it, report descriptively
  why if too many folds get rejected rather than silently dropping them).
- **Final holdout**: decide it now, in writing, before any code runs -- the most
  recent real quarter of data (whatever that is when this is actually built), touched
  ONLY once, after every other design decision (features, model, regularization
  strength) is already frozen. This is stricter than `idea_harness`'s own single
  `OOS_START` cutoff and is the actual point of doing this fresh rather than reusing
  Round 198/199's harness unmodified.
- **Statistical bar, decided now**: report BOTH conventions for direct comparability --
  (a) this ledger's own standard (`idea_harness.test_idea`-style bootstrap, IS
  P(edge>0) >= 0.95, OOS >= the bar at the ledger's k at build time) for consistency
  with every other round, and (b) the video's own pooled two-proportion z-test
  (taken vs. skipped win rate) for direct comparability to what was just watched.
  Whichever is used to call this a candidate, state it before running, not after.
- **Honest reporting, no exceptions**: if the result is a p=0.06-shaped "probably
  noise, slightly promising, don't trust it" outcome -- exactly what the video itself
  got doing this properly -- report that plainly, the way every Round 220-227 result
  was reported this session, rather than treating "almost significant" as a green
  light. No re-tuning against the final holdout after seeing it fail.

## Not ledger-eligible framing

Like Round 198/199, this is a filter test on an already-existing real signal
(the trader's VWAP-Z leg), not a new standalone idea in `idea_harness`'s own trade-level
sense -- no ledger row expected, same convention as every Round 206-227 the trader/
disciplined_bracket variant this session. Journal it either way.

## Picking this up next session

1. Read this file in full before writing any code.
2. Check `IDEA_LEDGER.md`'s current count and `CURRENT_STATE.md`'s kb-state line for
   what's changed since 2026-09-30 (last commit at plan time: e717bf3).
3. Build as a new round script (`round228_...py` or whatever the next free number is
   by then) under `futures/engine/`, importing the trader's real primitives
   directly rather than reimplementing them (`round49_vwap_zscore`,
   `round19_random_entry`, `round224_manual_confluence_robustness`'s `htf_trend_lookup`
   for the trend feature, `round220_money_flow_divergence`'s MFM construction for the
   money-flow feature).
4. Run `detect_changes(scope=all)` before committing, per this repo's own CLAUDE.md.
5. Journal the result honestly in `TRADING_JOURNAL.md`, update `CURRENT_STATE.md`'s
   kb-state line, run `kb_health_check.py` (tolerate the pre-existing "FVG real
   secrets" k=339 false positive, a known, already-tracked issue, not a new one).
