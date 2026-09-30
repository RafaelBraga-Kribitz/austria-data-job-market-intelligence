# Limitations and representativeness

Numbers below are from `outputs/market_summary.json`, `outputs/data_quality.json` and the Q*/T01* tables of the post-audit run (2026-09-16, DECISION_LOG D-012); the structural limitations do not change between runs.

## How representative is this analysis?

| Question | Answer (current run) | Where to verify |
|---|---|---|
| How many postings? | 12,429 raw rows → 10,945 unique → **720 core** (719 with full description); 546 adjacent; Styria 58, Graz area 52, Vienna 350 (location flag incl. multi-site ads; by primary state Styria 54, Vienna 343, T03a) | T01, T03a, market_summary.json |
| From which sources? | LinkedIn 300 core, EURES/AMS 202, karriere.at 134, jobs.at 58, willhaben 26 (after dedupe); official series from AMS JobBarometer (590 pages) | T01, docs/data-sources.md |
| Which period? | one-day snapshot of open ads collected 2026-09-16; first-publish dates mostly 2026 (median age 5–41 days by source), 34 evergreen ads > 180 days; JobBarometer 2020–2025 yearly | T13b, JB01 |
| Which locations? | all Austria; Bundesland known for 97 %; 22 Austria-wide/unspecified; 61 multi-site | T03 |
| Which job families? | 8 core families + 2 adjacent; defined by title rules; 9,679 retrieved rows out of scope by design; title precision 83 % strict / 95 % lenient on a 177-title hand-labelled sample | docs/role-taxonomy.md, Q03a, Q03c |
| What share could be deduplicated? | 24.2 % of in-scope rows (1,670 → 1,266 groups); 20 % of core groups appear on ≥ 2 sources | Q04, T01b |
| What is missing? | StepStone.at, Indeed.at, hokify, Glassdoor (blocked); company career pages; unadvertised jobs; postings whose title has no data word | this page |

## Structural limitations

1. **Snapshot, not flow.** One collection day counts the *stock* of open ads. Long-open (hard-to-fill or evergreen) ads are over-represented relative to fast-filled ones. Use JobBarometer yearly counts for flow and trend; never read the snapshot as "jobs per year", "vacancies" or "hires".
2. **Coverage gaps.** StepStone.at (major white-collar board) and Indeed.at are bot-blocked; hokify is behind a WAF; Glassdoor requires login; Styrian company career pages were not crawled. LinkedIn is capped at 1,000 results per query. The direction of bias: corporate/white-collar postings that appear *only* on StepStone are missing; postings that appear on several boards are captured through the others. See §"Invisible market" below.
3. **Title-based inclusion.** A job is "in scope" if its *title* matches the taxonomy. Data-heavy jobs with non-data titles (e.g. "Controller", "Growth Manager") are excluded from the core set; the supplementary full-text sweep (`eures_textsearch`) quantifies that adjacent demand for the AMS feed of Styria/Vienna/Upper Austria only. Recall of the title rules is not measured.
4. **Measured precision, not recall.** The taxonomy was audited on 25 titles per family (Q03c): strict precision 83 % after the audit; business_analysis (76 %) and data_governance (64 %; operational master-data titles) remain the weakest families. Skills, languages and degrees are rule-based on a fixed bilingual vocabulary; unknown tools are not discovered automatically. Spot-check samples (Q09, Q03b, Q07a) exist; formal precision/recall for those extractors has not been measured.
5. **Anonymised employers.** 140 of 720 core postings (all AMS/EURES rows) hide the employer ("siehe Beschreibung"); employer counts are lower bounds ("named employers", not "employers represented") and the employer tables are dominated by board and LinkedIn data.
6. **Salary = advertised minimum.** 81 % of parsed figures are single collective-agreement minimums; ranges are rare (15 %); LinkedIn omits figures in 41 % of its ads; 10 % of ads are "all-in" contracts and 9 % mention bonuses that cannot be separated. Our salary tables measure *floors on ads*, not pay; actual compensation cannot be estimated from this data.
7. **Language variables are proxies.** `posting_language` (ad written in English) is not "English is enough": 19 % of English ads still state a German requirement. `german_requirement` reads what the ad says; ads silent on German (many AMS ads written in German) are `not_mentioned`, which for a German-written ad usually implies German. The "C1-equivalent" bucket is mostly "sehr gut/very good" wording (172 of 261), an assumed mapping. The addressable-market scenarios (T07e) therefore bracket rather than pin the truth, and none of them measures negotiability or hiring outcomes.
8. **Geography is the employer's stated location.** Hybrid arrangements, multi-site postings and "Austria-wide" ads blur the Graz/Styria count (54 by primary state vs 58 including multi-site). `is_graz_area` uses a fixed commuting list (config/geo.json), an assumption.
9. **Small cells.** Styria has 58 core postings and single-digit counts for most families; marketing_analytics (24) and product_analytics (1) are rare everywhere. Any percentage computed on fewer than ~30 postings is flagged in the tables and should be read as "indicative"; Styrian figures are reported as counts.
10. **No seasonality from the postings.** A one-day snapshot observes an advertisement only if it is still open, so its first-publish dates are a survival curve (52 % of the core set was published in the collection month, 90 % within 90 days). Seasonal questions are answered from a separate external series with its own limits (docs/seasonality.md); no seasonal statement may be made from the snapshot.
11. **No hiring outcomes.** Nothing here measures interviews, offers or hires. Applicant counts (LinkedIn only) are descriptive. No statement in this repository is causal.
12. **Clusters are heuristic.** k-means silhouette is 0.075 (Layer 1, T15); clusters are reading aids, not occupational categories.
13. **JobBarometer is a different unit.** AMS occupation classes (e.g. "Data Scientist (m/w)" bundles analysts) and a web-crawl methodology that AMS does not fully disclose; use for trend direction and relative regional size, not for absolute counts of "data analyst jobs".
14. **Reproducibility of acquisition.** Sources change daily and may change their HTML/API; the acquisition scripts are dated and raw data is stored privately so that all downstream steps reproduce exactly. In the public repository the posting raw data and the posting collectors are absent (PUBLICATION_DECISION.md), so outsiders can reproduce the analysis logic and audit the aggregates but not regenerate them; the exception is the seasonality layer, whose Eurostat source and raw response are published and re-runnable (docs/seasonality.md §8).
15. **Collection terms vs private research (D-013, D-022).** The audit of 2026-09-16 found that the five snapshot sources restrict automated extraction. That is why collectors and raw records are unpublished. It is not a ban on private research re-collection: new dated folders, never merged with this snapshot, no CAPTCHA/WAF bypass, never republished (D-022). The *public* repository still cannot be refreshed the same way.

## Invisible market: what this dataset plausibly cannot see

* **StepStone.at** — the largest Austrian white-collar board by advertised volume (docs/research-landscape.md §8); its ads that are not cross-posted to karriere.at, LinkedIn or the AMS feed are invisible. Plausible size: comparable to the karriere.at contribution (order of one to two hundred core postings on a given day); direction of bias: corporate, German-language, mid-to-senior analyst/BI roles.
* **Company career pages and applicant-tracking feeds** (Workday, SuccessFactors, SmartRecruiters) of large Styrian employers (AVL, Magna, KNAPP, Andritz, ams OSRAM, Infineon Graz) — partly cross-posted to LinkedIn, partly not; internal and referral hires never advertised.
* **hokify / Indeed / metajob** — mostly aggregators of the boards already covered; marginal.
* **Specialist and university boards** (devjobs.at, ÖH/FH/TU Graz career portals, research-institution postings) — small, tech-heavy, partly academic.
* **Agency mandates** advertised without a client name (4.5 % of named postings are agencies) and vacancies filled through networks.
Net effect: the *ranking* of families, technologies and languages is unlikely to flip, but absolute counts (especially Styrian ones) are lower bounds, and the German-requirement share is probably *under*-stated because the missing sources are German-language corporate boards.


<!-- BQ30_source_coverage:start (figure generated by src/analysis/make_visual_layer.py - do not edit by hand) -->
**Q. How much of the Austrian market can this dataset simply not see?**

LinkedIn and EURES/AMS carry most of the 720 core postings, and the corporate white-collar segment is missing entirely: StepStone.at and Indeed.at returned HTTP 403, and company career pages, university portals and hokify were never collected - so the corporate share of Austrian data demand is an unmeasured gap, not a measured absence.

[![BQ30_source_coverage](../outputs/figures/BQ30_source_coverage.png)](../outputs/figures/BQ30_source_coverage.png)

<sub>**Figure BQ30** · comparison across categories shown as `horizontal_bar` (bivariate-simple) · built from `T01_source_coverage.csv`, `T01b_source_overlap_in_scope.csv` · units: rows / postings. **Read with:** Only 20 % of core postings were seen on more than one source, so the boards are largely disjoint universes; a missing board is a missing slice, not a redundant one.</sub>
<!-- BQ30_source_coverage:end -->

## Robust vs. tentative conclusions

Rules used in the decision documents: a conclusion is **robust** if it holds (a) on the whole core set with n ≥ 200, (b) in the same direction on both the AMS/EURES side and the LinkedIn/karriere.at side, and (c) its Wilson interval excludes the comparison value. It is **tentative** if any of these fails or if it rests on Styria-only cells < 30. Each finding in `CAREER_DECISION_MAP.md` carries this label.


<!-- BQ29_styria_sample_sizes:start (figure generated by src/analysis/make_visual_layer.py - do not edit by hand) -->
**Q. Which of my Styrian conclusions are actually too small to carry a decision?**

All of them, by the project's own rule: the largest Styrian family cell is 20 postings against a robustness threshold of 30, and four families sit at five or fewer - so Styrian findings are read as counts and directions, never as percentages.

[![BQ29_styria_sample_sizes](../outputs/figures/BQ29_styria_sample_sizes.png)](../outputs/figures/BQ29_styria_sample_sizes.png)

<sub>**Figure BQ29** · comparison across categories shown as `horizontal_bar` (bivariate-simple) · built from `T02_role_family_counts.csv` · units: postings. **Read with:** The official yearly series (JB05) puts Styria at 13.6 % of the national flow against 7.5% here (by primary state; 8.1% counting every ad with a Styrian site), so this snapshot may also understate Styrian volume, not only measure it imprecisely.</sub>
<!-- BQ29_styria_sample_sizes:end -->

## Known follow-ups that would most improve the evidence

1. Obtain StepStone.at coverage through a permitted channel (data partner or written permission); this is the single largest coverage gap.
2. Collect the career pages of the ~30 largest Styrian data employers through their published feeds where terms allow, to firm up the Graz picture.
3. Convert the snapshot into a flow with dated private re-collection (D-022) plus public-reproducible channels (AMS JobBarometer, Eurostat, Arbeitnow API). Never merge dates; never publish raw or collectors. Hunter 2026-09-18 (T19 `published_aggregates`): 109 Austrian core titles via python-jobspy LinkedIn jobs, 0 JD texts; StepStone.at/Indeed.at live 403; Arbeitnow 1,500 ATS listings, 1 Austria location, 0 core. Not merged into 720; title-query mix, not a census.
4. Manual audit of 100 random core postings for skills/language/salary extraction (templates in Q09/Q07a) to attach measured precision/recall to those rules, as was done for titles (Q03c). Protocol and sampler: `docs/labelling-protocol.md`, `src/analysis/labelling_audit.py` (OQ-09, OQ-16, OQ-22).
5. Record actual application outcomes for this profile; it is the only way to turn requirement patterns into hiring evidence.


## Layer 2 / Layer 3 limitations (added 2026-09-18)

The candidate-supply layer is a **public-profile sample, not a census**: GitHub accounts with an Austrian location string (9,409), of which 1,818 carry a data signal. It over-represents engineers, researchers and students, under-represents BI/Excel/SAP/Power BI practitioners and everyone whose work is private; it cannot observe language proficiency, years of experience, relocation intent or hiring outcomes; location strings can be stale; bios are self-marketing; frames differ by region (Styria complete, Vienna sampled); LinkedIn and Kaggle were not collected. Classification precision is measured (bio → family 78 % strict, repository → project 75 % strict). The demand × supply join compares different universes on shared taxonomies: rankings and orders of magnitude are defensible, exact ratios are not, and no composite score is computed. Details: `docs/supply-methodology.md` §9, `docs/supply-data-quality.md`, `docs/supply-research-audit.md`, `docs/demand-supply-methodology.md` §6.
