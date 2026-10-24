# ML8 result: FAIL (25 Oct 2026, 00:05 local clock)
Pre-registration `PREREG_ML8.md`; output `ML8_OUTPUT.txt`.
- 12 model x stop cells scored on 427 unseen VAL days (2023-24). Top-10% win rates: 42%-60%; the best, logit at stop 4xS, is 60% (n 43, P 0.032), which does not clear the Bonferroni bar (P <= 0.0083) and its neighbours (top 50%) fall back to base.
- Nothing approaches 90%. 90% at 1:1 means mean R +0.8 per trade; 27/30 wins by luck at 50% has P 4e-6.
- Base win rates of a 1:1 bracket from 08:00 are 33-54% depending on stop size; the models add ~0-8 points in the best slice and nothing across slices.
- Conclusion: from the 08:00 open with these features, no model gets close to 90%; the realistic ceiling here is the base rate (+0-8 pts), i.e. below the 62% a 2-week account pass at $950 risk needs.
