# Economic evaluation: Austria Data-Job Market Intelligence

Pre-build scenario exercise · evaluation date 2026-09-16 · method v2.0 · cost basis v1.2 ([COST_BASIS.md](https://github.com/RafaelBraga-Kribitz/braga-portfolio-docs/blob/main/docs/value-evaluation/COST_BASIS.md))

## Decision

A data-job seeker in Graz decides which roles, regions, tools and skills to prepare for. Could better market evidence prevent months of preparation for the wrong path, and is a full research system better than a focused manual study?

## Assumptions

* Target: data roles in Austria, Greater Graz first [sourced: `config/profile.json` at 6a256e0].
* Public series count ads by year and coarse occupation; none lists skills, German requirement or pay per ad in Styria [sourced: `docs/research-landscape.md` §1 at 6a256e0].
* Wrong-path risk is real: preparation had already gone into a tool and applications without market evidence, a Tableau dashboard and applications filtered out by applicant-tracking systems (ATS) [sourced: owner statement 2026-10-30; [Tableau Public dashboard](https://public.tableau.com/app/profile/rafael.braga.kribitz/viz/HumanoidRoboticsTCO/Dashboard1)].
* A month of earlier employment is valued at €4,170: the midpoint of the AMS collective-agreement entry floor for Data Scientist, €2,800–4,350 a month × 14, ÷ 12. This is a market floor, not a salary expectation [sourced: `docs/research-landscape.md` §1.4 at 6a256e0]. If unemployment benefit is paid meanwhile, only the difference counts.
* The wrong path is measured once, through employment timing; rework hours are not counted again.
* Baseline: job boards read by hand. Alternatives: a focused study (about 50 hand-tagged ads plus the AMS series, 40 h) or the full system. Horizon: one 12-month job search.

## Scenarios

State of the existing plan, months of employment lost without research, and months each option recovers [assumptions].

| State of the plan | Probability | Lost without research | Focused gains | Full gains |
|---|---|---|---|---|
| On target | 0.15 | 0 | 0 | 0 |
| Partly off: one tool or skill wrong | 0.35 | 2 | 1 | 1.5 |
| Substantially off: role family, region, language or ATS keywords | 0.30 | 6 | 3 | 4.5 |
| Severe: a year lost before the course changes | 0.10 | 12 | 6 | 9 |
| Research misleads | 0.10 | — | −0.5 | −1 |

## Expected value and cost

- Cost of not knowing: 0.35 × 2 + 0.30 × 6 + 0.10 × 12 = 3.7 months, **€15.4k**, the upper bound on what research is worth.
- Focused study: 1.8 months, **€7.5k**. Full system: 2.7 months, **€11.2k**.

Rate: €45 per active hour, the market cost of the role this work needs (data engineering, advertised minimum, ADJMI snapshot 2026-10-18; ADJMI = Austria Data-Job Market Intelligence). Hours: owner scope estimate, 240 h, including first-year maintenance [estimate]. Hosting €0.

| Case | Full system: hours · cost · multiple | Focused study: hours · cost · multiple |
|---|---|---|
| Central | 240 · €10,800 · 1.0× | 40 · €1,800 · 4.2× |
| 0.5× hours | 120 · €5,400 · 2.1× | 20 · €900 · 8.3× |
| 1.5× hours | 360 · €16,200 · 0.69× | 60 · €2,700 · 2.8× |

## Verdict

**Fails financial hurdle** for the full system as built: 1.0× central, 0.81× at a rate 30 % higher (the inputs are floors). The focused study passes at the central case, 4.2×, and fails at 1.5× hours or a 30 % higher rate (3.3×).

- Maximum affordable cost of the full system: €11.2k ÷ 4 = **€2.8k**.
- Break-even driver, expected months gained: 2.6 for 1×, 10.4 for 4×. Even preventing the worst case recovers at most 9 months in that state, so on one job search the full system cannot reach 4×.
- Decision advantage: the focused study nets +€5.7k; the full system +€0.4k.

Reversing assumptions:

1. The full system serves more than one decision: later project selection, or other job seekers. Together, the extra uses must add about 7.7 months' worth of expected gain to reach 4×.
2. The focused study runs past about 42 h.

## Recommendation

**Smaller version**: the focused study first; extend only if it shows the plan is substantially off. Measure: hours; decisions changed (log entries); preparation hours redirected; applications and responses by family and region (`schemas/application_log_schema.md`); months to first offer.

Actuals and lessons: [lessons-learned.md](lessons-learned.md).
