# Decision framework: how career paths are compared

This framework turns market tables into a comparison of candidate paths for one specific profile (senior marketing/growth professional, English-fluent, German beginner–intermediate, Graz-based, building Python/SQL/R/statistics). It is deliberately simple and fully visible; the numbers it uses are produced by `src/analysis/build_decision_matrix.py` into `outputs/tables/D01_decision_matrix.csv` and `outputs/career_paths.json`.

## Candidate paths (= role families in the taxonomy)

data_analytics · bi · marketing_analytics · product_analytics · business_analysis · data_science · data_engineering · data_governance (adjacent: ai_software_engineering, reported but not scored as a target).

## Variables (all from tables, per family)

| Variable | Definition | Table | Direction |
|---|---|---|---|
| V1 Market size (AT) | canonical core postings in the family | T02 | more = better |
| V2 Styria availability | postings located in Styria | T02 (styria_count) | more = better |
| V3 English-posting share | share of postings written in English (proxy for international teams) | T07c by family | more = better for this profile |
| V4 German-required share | share with german_requirement ∈ {required, required_implied} | T07 by family | less = better for this profile |
| V5 Profile skill overlap | share of the family's 15 most-mentioned skills that are in the profile's self-declared *have* **or** *developing* lists (`config/profile.json`) — a subjective, ordinal indicator (e.g. data_analytics 13 of 15), not a fit probability | T05 by family, D01 | more = better |
| V6 Technical gap | share of the family's top-15 skills that are *structural* for the profile (see profile.json: e.g. Spark, Kubernetes, Java) | T05 by family | less = better |
| V7 Advertised salary | median advertised minimum annual gross (T09b); n reported | T09b | more = better |
| V8 Remote/hybrid share | share with remote_type ∈ {remote, hybrid, hybrid_or_flexible} | T10 by family | more = better |
| V9 Senior-entry openness | share of postings that are not junior/intern AND do not state ≥5 years (proxy for entry with transferable seniority) | T08, T08d | more = better |
| V10 Degree-required share | share with degree_required phrase | T11c | less = better |

## Normalisation and weights

Each variable is min-max scaled across the scored families to 0–1 (direction applied so that 1 = best for this profile). Default weights (sum = 1):

| V1 | V2 | V3 | V4 | V5 | V6 | V7 | V8 | V9 | V10 |
|---|---|---|---|---|---|---|---|---|---|
| 0.15 | 0.15 | 0.10 | 0.10 | 0.15 | 0.10 | 0.05 | 0.05 | 0.10 | 0.05 |

Rationale: geography and language are the user's binding constraints; skill overlap determines transition time; salary is a weak discriminator because advertised minimums are collective-agreement floors.

## Sensitivity

The script re-scores under three alternative weight sets: (a) *geography-first* (V2 = 0.35), (b) *language-first* (V3+V4 = 0.40), (c) *equal weights*. A path is called **robust** if it stays in the top 3 under all four weightings and its V1 and V2 counts are each ≥ 30; **tentative** otherwise. Small-n cells (< 30 postings) are flagged in the matrix and the ranking text says so.

## Current result (run of 2026-09-16, D01/D02)

Default weights: data_engineering 0.63, data_science 0.61, data_analytics 0.59, marketing_analytics 0.45, business_analysis 0.41, data_governance 0.40, bi 0.33; product_analytics unranked (n = 1). Data analytics is 3rd under all four weightings; engineering and science swap 1st/2nd (science leads under language-first weights). No family meets the robustness rule because every Styrian count is below 30. The matrix ranks market size, English openness and advertised floors; it does not rank ease of entry, which is why the career map derives the entry family from the gap variables (V5/V6) rather than from the total score.

## What the score is not

It is not a probability of getting hired, not a forecast, and it ignores competition (applicant counts exist only for LinkedIn and are reported descriptively). Use it to order investigation and preparation effort, then read the underlying tables for the family you pick.
