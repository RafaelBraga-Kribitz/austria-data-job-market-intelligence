# Economic evaluation: Austria Data-Job Market Intelligence

Pre-build scenario exercise · evaluation date 2026-09-16 · method v2.0 · cost basis v1.1 ([COST_BASIS.md](https://github.com/RafaelBraga-Kribitz/braga-portfolio-docs/blob/main/docs/value-evaluation/COST_BASIS.md))

## Decision

A data-job seeker in Graz decides which roles, regions and skills to target and which skills the next portfolio projects show; a dataset of Austrian data-role ads pays if it avoids rework, that is, project hours spent showing skills the market does not ask for.

## Assumptions

* Target region and role families: Greater Graz first, data roles in Austria [sourced: `config/profile.json` at 6a256e0].
* Public series count ads by year and coarse occupation; none lists skills, German requirement and pay per ad in Styria [sourced: `docs/research-landscape.md` §1 at 6a256e0].
* Baseline: reading job boards by hand, about 8 h per cycle [assumption].
* Planned portfolio work: three projects of about 60 h, 180 h [estimate: earlier projects took 36–84 h, cost-basis hours table].
* Horizon: one six-month search cycle [assumption].
* Rate: €45 per hour all-in, the market cost of the role this work needs (advertised minimum, ADJMI snapshot 2026-10-18): data engineering, seniority unspecified. Avoided hours count at the same rate.
* Best alternative: hand-tag about 50 ads in a spreadsheet, about 6 h (€270) [estimate].

## Scenarios

| Scenario | Outcome | Hours avoided | Value | Probability |
|---|---|---|---|---|
| Redirects the plan | 30 % of the 180 h aimed at the wrong skills | 54 h | €2,430 | 0.20 [assumption: career change, no per-ad data] |
| Refines one project | 10 % of the hours change emphasis | 18 h | €810 | 0.30 [assumption] |
| Confirms the plan | Only manual reading saved | 8 h | €360 | 0.25 [assumption] |
| Not used | Answer late or ignored | 0 h | €0 | 0.15 [assumption] |
| Misleads | Rule-based tags steer a project wrong | −18 h | −€810 | 0.10 [assumption: recall unmeasured] |

Probabilities include adoption.

## Value and cost

Expected gross value = 0.20 × 2,430 + 0.30 × 810 + 0.25 × 360 + 0.15 × 0 − 0.10 × 810 = **€738** (16 h of avoided rework).

Total cost = build hours × €45 + maintenance (10 % of build hours a year, for half a year); hosting €0.

| Case | Hours | Build | Maintenance | Total cost | Multiple |
|---|---|---|---|---|---|
| Central | 28 h | €1,260 | €63 | €1,323 | 0.56× |
| 0.5× hours | 14 h | €630 | €32 | €662 | 1.1× |
| 1.5× hours | 42 h | €1,890 | €95 | €1,985 | 0.37× |

## Verdict

**fails financial hurdle** at 0.56× central, against 4×.

* Maximum affordable cost: €738 / 4 = **€180**, about 4 h.
* Break-even driver, expected avoided rework: 29 h for 1×, 118 h for 4× (two thirds of the planned hours).
* Rate check: at a rate 30 % higher (€58), value and cost scale together; the central multiple stays 0.56×.
* Earlier earnings are not monetised: hiring evidence is shared across the portfolio and is not added here.
* Reverses if two thirds of the planned project hours are expected to be redirected, or if the planned project work is about eight times larger (about 1,450 h) at the same shares.

## Recommendation

**smaller version**: hand-tag a sample of ads within about 4 h. A full pipeline built for other portfolio reasons keeps this verdict.

Measure: active hours from the first private commit, project hours redirected by the data (decision-log entries), applications and responses by family and region (`schemas/application_log_schema.md`), weeks to first offer.

Actuals and lessons: [lessons-learned.md](lessons-learned.md).
