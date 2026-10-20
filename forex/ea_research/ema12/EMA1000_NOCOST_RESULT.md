# EMA1000 with no spread and with limit orders (run 20 Oct 2026 12:08-12:20, main PC, local clock)

the trader: "run it again but with limit orders, no spread". Pre-registration `PREREG_EMA1000_NOCOST.md` (sha256 a2a343c175e743aacfdf77263e3e7f1f26770f2be750af5234393669e6935a9f, 12:04:51). Engine `ema1000_nocost.py`, checks `EMA1000_NOCOST_DRYRUN_OUTPUT.txt` (market path reproduces EMA1000_MARKETS.csv exactly; 225,288 limit fills checked, 0 violations; truncation test 160 fills, 0 mismatches). Output `EMA1000_NOCOST_OUTPUT.txt`, `EMA1000_NOCOST_TRIALS.csv`, `EMA1000_NOCOST_MARKETS.csv`. Same 1,000 variants, 46 MT5 broker, DEV 2022-24 / VAL 2025; nothing after 2025-12-31 loaded.

## Result: with no spread the rule is break-even, and still has no edge
Median over the 1,000 variants, DEV mean R per filled trade (VAL 2025 in brackets):

| Fill model | Rule side | Inverted side | Fill rate | Variants above 0 (rule) | Best rule t |
|---|---|---|---|---|---|
| EMA1000 original (real spread, market entry) | -0.180 | -0.184 | 100% | 0% | -9.5 |
| Z: no spread, market entry | -0.005 (-0.002) | -0.008 (-0.010) | 100% | 19% | +1.65 |
| L: no spread, limit at the signal close | -0.013 (-0.010) | -0.015 (-0.017) | 98% | 7% | +1.27 |
| Q: real spread, limit at the signal close | -0.139 (-0.159) | -0.143 (-0.168) | 81% | 0% | -5.78 |

- **The spread explains almost the whole loss.** Removing it moves the median from -0.180 to -0.005 R a trade (+0.177). What is left is a coin flip: the random side is -0.005, and the rule's direction beats the inverted side by only +0.002 R (68% of variants slightly above zero, none significant).
- **No variant reaches an edge even at zero cost:** the best Z variant is +0.018 R with a day-clustered t of 1.65 (bar 3.99), and its VAL year is -0.004. 0 candidates in Z, L and Q (Z and L could not produce one by design). Inverting does not help: the best inverted variant is +0.019 (t 1.67) and its 2025 is about zero.
- **Limit orders (L) are not better than market orders (Z):** -0.013 against -0.005. A limit at the signal close fills 98% of the time, so it behaves like a market order with no lag, not a pullback entry. Part of the gap is my conservative convention (in the fill minute a target touch is ignored); I did not separate the two.
- **Q is the only fill model MT5 broker could offer** (real bid / ask, a long fills when the ask comes down to the limit). The limit saves part of the spread on the trades it fills (-0.139 against -0.180), but fills only 81% of the time (-0.108 per signal) and no variant is positive: best -0.048, no market has a positive median, 0 candidates.
- **A few markets look positive at zero spread** (Z median: ASX +0.015, EURCAD +0.012, CADCHF +0.011, NZDCAD, NZDCHF, NSDQ +0.006; 11 of 46 positive). That is a ceiling that MT5 broker's spread removes, picked out of 46 markets, and it is not a candidate: in Q none is positive.

## What it means
- The 12 EMA cross rule has no directional information to sell: before costs it earns nothing (-0.005 R), and its inverse earns nothing either. The 0.18 R loss of EMA1000 was the spread paid against small targets, as the follow-up said, now measured directly.
- For any discretionary version the cost bar is the spread itself: about 0.06 R a trade on gold at January's stops (median 8.1 points) and about 0.11 R at April-May's (4.3 points). Anything the trader adds by hand has to beat that before MT5 broker pays him.
- Mechanical question closed under every fill model tried: 3 fill models x 2 sides x 1,000 variants, 0 candidates. The 2026 hold-out stays sealed; nothing goes near the account. The blind replay of his discretion (batch 2 tonight) is still the only test of what he adds.
