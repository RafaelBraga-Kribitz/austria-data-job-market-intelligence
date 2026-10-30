# Lessons learned: Austria Data-Job Market Intelligence

Expectations come from the [economic evaluation](economic-evaluation.md).

## Expectations against actuals (as of 2026-10-30)

| Item | Expected | Actual | Evidence |
|---|---|---|---|
| Effort | 28 h central (14–42 h) | 28 h by the commit-day convention; 9 h by commit sessions; the first public commit holds a whole private build (220 files) | cost-basis hours table; commit 6a256e0 |
| Total cost | €1,323 central | €1,260 build by convention; maintenance not logged | cost-basis hours table |
| Technical performance | Rule-based tags good enough to rank skills and regions | Title precision 83 % strict, 95 % lenient on a hand-labelled sample; skill recall unmeasured | `docs/original-specification-audit.md`; README, Known limits |
| Adoption | The data sets the next projects' skills | Targeting decisions cite it (Graz plus Vienna hybrid, English-written ads, SQL over a modelled schema) | [viability review](https://github.com/RafaelBraga-Kribitz/braga-portfolio-docs/blob/main/docs/viability/austria-data-job-market-intelligence.md) |
| Operational outcome | About 16 h of project rework avoided | Unmeasured: no time log. 0 applications sent as of 2026-10-28 | viability review |
| Attributable value | €738 expected | Unmeasured | — |

## Lessons

**L-ADJMI-1 · Advice counts only when it is acted on.** Scope: career research and other information projects. The targeting answers exist, but no application had been sent by 2026-10-28, so the value chain stops before any outcome. Track the action the advice is meant to change from the first week. Evidence: viability review. Date: 2026-10-30.

**L-ADJMI-2 · Log hours from the private start.** Scope: projects published from a private repository. The public history starts with one squashed export, so commit days (28 h) and commit sessions (9 h) differ threefold, and neither is a record. Evidence: commit 6a256e0; cost-basis hours table. Date: 2026-10-30.

**L-ADJMI-3 · A build should show the gap it finds.** Scope: this project and the next portfolio project. SQL is named in 40 % of ads and shown by 10 % of observed candidates, yet this repository shows SQL in one query (`src/analysis/supplement_radar.py`). Evidence: README, Decision summary, finding 3. Date: 2026-10-30.
