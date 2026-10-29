# The self-improving research loop

An attempt to automate the search for an edge: a program that proposes trading rules, tests them,
keeps the promising ones and proposes variations of those, generation after generation. It was
built after a series of social-media videos claimed such agents "learn" an edge by themselves.

## Design

- **Search space.** Four rule families (short-term pops, dips to recent lows, RSI dips,
  breakouts) on 46 MT5 symbols (indices, forex, commodities, crypto), one decision a day,
  2022-2026, with costs and a flat holding cost per day.
- **Honest null.** Each candidate is compared with circular time shifts of its own entries (same
  markets, sides and holding days, 400 shifts), so a rule only counts if its timing matters.
- **Multiple-testing control.** A cumulative Benjamini-Hochberg bar (q = 0.10) over every rule ever
  tested, so the bar rises as the loop tries more ideas.
- **Placebo worlds first.** Before the real run, the loop was run on markets with every day
  shuffled, where no edge can exist. It had to find nothing there (it found 0, 0 and 0 in three
  worlds) before it was allowed to look at real data. An earlier calibration with 20-day blocks
  failed, because blocks keep short-term structure.

## Result (`SI_V3_RESULT.md`)

- 40 generations, 12,000 rules. Candidates that cleared the first bar peaked at 40 in generation
  13 and fell to 0 by generation 25 as the cumulative bar rose. **No rule survived.**
- The 40 rules that ever passed were checked on 2025: median +39.5 bp per trade in the search
  window, -1.0 bp the next year. The winner's curse, measured.
- The best score per generation did not climb with more generations. More search does not mean
  more edge; it means more chances to find noise.

## Other experiments in this folder

`day2k/` (one learned "best setup" a day across 28 pairs: no edge), `llm_bench/` (comparing
language models as rule writers), `freeform/`, `hf/`, `ml/`, `ensemble/`, `regime/`, `events/`,
`barrier/`, `reverse/`, `hitrate/`, `sds/`, `slow/`: each subfolder has its own `PREREG_*` and
`*_RESULT.md`. The lessons files (`SI_LESSONS_V2.md`, `SI_LESSONS_V3.md`, `SI_V1_LESSONS.md`)
record what each version taught the next.
