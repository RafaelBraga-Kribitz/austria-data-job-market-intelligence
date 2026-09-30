# Methodology

This document describes how evidence flows from raw sources to decision documents. Every step is a script in `src/`; every rule lives in `config/`; every intermediate file is kept in `data/`.

```text
raw sources ──► data/raw/<source>/<date>/*.jsonl        (src/acquisition/collect_*.py)
      │
      ▼  build_interim.py      one row per source posting, common schema, full text retained
data/processed/interim_postings.jsonl
      │
      ▼  normalize.py          titles → families; geography; work model; salary; languages;
      │                        experience; education; skills (config/*.json rules)
data/processed/postings_normalized.jsonl
      │
      ▼  dedupe.py             cross-source duplicate groups, canonical row per group
data/processed/postings_dedup.jsonl
      │
      ├─► run_analysis.py      outputs/tables/T*.csv (incl. T04d, T05f, T17), outputs/market_summary.json
      ├─► cluster_requirements.py   outputs/tables/T15_*.csv, outputs/clusters.json
      ├─► jobbarometer_analysis.py  outputs/tables/JB*.csv, outputs/jobbarometer.json
      ├─► build_decision_matrix.py  D01–D04b, career_paths.json
      ├─► supplement_radar.py  T19 dated Arbeitnow/hunter aggregates (never merged into 720; needs the private hunter DB)
      ├─► make_figures.py      outputs/figures/*.png (F14 intern vs junior)
      └─► export_agent_json.py outputs/{skills,roles,locations,languages,salaries}.json
      │
      ▼  hand-written synthesis (numbers copied from tables, each with table id)
docs/market-guide.md · docs/career-map.md · CAREER_DECISION_MAP.md · AGENT_CONTEXT.md
```

## 1. Acquisition

| Source | Type | Access path | What is stored |
|---|---|---|---|
| EURES portal | EU mirror of AMS "PES Austria" feed (+ a few private boards) | public JSON search API used by the portal SPA; detail endpoint for reference id | full search hit (title, HTML description, NUTS-3 codes, ESCO occupation URIs, schedule/offering codes, employer, dates) + facets per query + detail record |
| karriere.at | generalist board | listing JSON (same payload as the site's own SPA, header `X-Requested-With`) + detail HTML with schema.org JobPosting JSON-LD | listing item (title, company, size, locations, salary string, home-office flag, date) + JSON-LD (description, baseSalary, employmentType, jobLocation) + Vue detail state |
| LinkedIn | professional network — **job listings only** | logged-out "jobs-guest" HTML endpoints (list + jobPosting) | card (title, company, location, date, url) + detail (description, seniority level, employment type, function, industry, applicant count) + raw HTML; no member profiles, people search or hiring-team data |
| willhaben Jobs | classifieds board | `__NEXT_DATA__` JSON embedded in search and detail pages | entry (title, company, locations, salary, time frame, employment modes, dates) + detail data (description, attributes) |
| jobs.at | generalist board | HTML cards + detail HTML | card + detail (title, company, meta, description) + raw HTML |
| AMS JobBarometer | official aggregate | server-rendered HTML per occupation × Bundesland | yearly ad counts 2020–2025, trend rating, share label, similar occupations, Bundesland distribution, competencies + raw HTML |
| Arbeitnow Job Board API | documented public API (no key) | `collect_arbeitnow.py`; Austria filter client-side | dated supplement only — never merged into 2026-09-16; raw gitignored; 2026-09-18 probe: 1 Austria / 0 core |
| Private hunter (gitignored) | python-jobspy on LinkedIn **job listings** (the library requests the same logged-out `jobs-guest` search endpoint as the LinkedIn row above) + StepStone.at/Indeed.at attempts (HTTP 403, stopped) | `src/private/radar/` (not published); `supplement_radar.py` reads its database and skips with a notice without it | T19 2026-09-18: 109 Austrian core titles, 0 JD texts, 100 % jobspy LinkedIn; never merged into 720; terms position in docs/legal-and-publication-audit.md §11.2 |

Rules: no login, token, CAPTCHA or paywall bypass; fixed delays (0.8–2 s) and exponential backoff on 429/5xx; every request is logged in `query_log.jsonl`; every record keeps a collection envelope (`source`, `collected_at`, `query`). Blocked sources are listed in `docs/data-sources.md`. Private research re-collection of posting boards (including StepStone/Indeed/LinkedIn jobs) lives in the gitignored hunter and in new dated folders (D-022); it is never published. **LinkedIn scope:** job *listings* were collected by automation (2026-09-16 with `collect_linkedin.py`, 2026-09-18 with the hunter); LinkedIn *member/people* data was never collected by automation — the Layer 2 LinkedIn slot accepts only permitted channels (D-018, D-026).

Queries: ~45 title keywords in English and German (`config/queries.json`) run Austria-wide on each source; LinkedIn additionally per major city because it caps results at 1,000 per query. The keyword superset is deliberately broad; inclusion in the analysis is decided by title normalization, not by the query (DECISION_LOG D-002).

## 2. Interim schema (`build_interim.py`)

Common fields for every posting: `source, source_id, source_url, source_type, title, company, company_raw, location_text, nuts_codes, posted_date, modified_date, description_html, description_text, employment_type_raw, salary_text_raw, salary_min_raw, salary_max_raw, salary_period_raw, remote_flag_raw, industry_raw, seniority_raw, queries (which searches surfaced it), collected_at`, plus source-specific extras (ESCO URIs, AMS reference, applicant count, company size). Duplicates of the same `source_id` across queries are collapsed here; nothing else is dropped.

## 3. Normalization (`normalize.py`)

| Field group | Method | Config | Confidence field |
|---|---|---|---|
| `title_clean` | remove gender markers `(m/w/d)`, `*in`, hours, location noise, hyphenation | code | – |
| `normalized_title`, `role_family` | first matching ordered regex rule; hard/soft out-of-scope overrides | `role_taxonomy.json` | `role_rule`, `role_oos_reason` |
| `seniority` | title words (intern/student, trainee/junior, senior, lead/head); LinkedIn seniority field as fallback; else `unspecified` | `role_taxonomy.json` | `seniority_source` |
| `state, city, is_styria, is_graz_area` | explicit location fields → NUTS-3 → workplace/postcode/city in text → title | `geo.json` | `location_evidence`, `location_confidence` |
| `remote_type` | phrase classes: remote / hybrid (days or % stated) / hybrid_or_flexible (home office mentioned) / on_site / unknown | code | `remote_evidence` |
| `employment_type`, `is_internship_student`, `is_temporary_or_contract` | source field + phrases | code | – |
| `salary_*` | structured fields first, else figures within 160 chars of salary words; period from context or magnitude; monthly ×14 → annual gross; plausibility bounds; flags for collective-agreement wording, overpay, all-in, bonus and part-time basis | code (D-005, D-012) | `salary_source`, `salary_basis`, `salary_transparency`, `salary_conversion_note`, `salary_*_mention` |
| `german_requirement`, `german_level_*`, `english_*` | context window (±120 chars) around language mentions; CEFR codes and descriptor words; required/preferred/mentioned/… | code (D-006) | `german_snippet` |
| `posting_language` | German vs English stop-word ratio (≥60% → de, ≤40% → en) | code | `posting_language_confidence` |
| `experience_min_years` | "N Jahre/years … Erfahrung/experience" patterns; phrases for "mehrjährig" and entry-level | code | `experience_text` |
| `degree_required`, `degree_requirement` (required / preferred / mentioned / none), `degree_levels`, `degree_fields` | phrase patterns ("abgeschlossenes Studium", "degree in …"), advantage wording ("von Vorteil", "ideally") + field vocabulary in windows around education words | `skills_taxonomy.json` → education | `education_snippet` |
| `skills_<category>` | regex vocabulary, 13 categories, ~250 canonical skills, bilingual | `skills_taxonomy.json` | – |
| `company_norm` | lower-case, legal-form suffixes removed | code | – |

## 4. Deduplication (`dedupe.py`)

Union-find over (company_norm, title_clean, state), (title_clean, description fingerprint), (company_norm, title_clean) when state missing. Canonical row = longest description, tie-break by source priority. All rows retained with `dedupe_group_id`, `is_canonical`, `sources_in_group`. The in-scope duplicate rate is reported in `outputs/tables/dedupe_summary.csv` and `T01b_source_overlap_in_scope.csv`.

## 5. Analysis sets and denominators

* **Core set**: canonical rows with `role_family` ∈ {data_analytics, bi, data_science, data_engineering, data_governance, marketing_analytics, product_analytics, business_analysis}.
* **Adjacent set** (reported separately): ai_software_engineering, other_data.
* **Text-derived features** (skills, languages, education, remote, experience) use the sub-set with `description_length > 300` as denominator; structural features use the whole core set. Every table stores `n`.
* Proportions carry Wilson 95% confidence intervals where they feed decisions.


<!-- BQ27_population_funnel:start (figure generated by src/analysis/make_visual_layer.py - do not edit by hand) -->
**Q. When I read '40 % of ads', 40 % of what exactly - and how did 12,429 rows become that denominator?**

12,429 raw rows deduplicate to 10,945 unique postings, of which 720 carry a core data-role title - that is the denominator behind almost every share in the project, and only 58 of them list a Styrian site (52 of those in the Graz commuting area).

[![BQ27_population_funnel](../outputs/figures/BQ27_population_funnel.png)](../outputs/figures/BQ27_population_funnel.png)

<sub>**Figure BQ27** · part to whole shown as `horizontal_bar` (bivariate-simple) · built from `outputs/market_summary.json`, `Q04_duplicates.csv`, `T01_source_coverage.csv` · units: postings. **Read with:** Each bar is a subset of the one above it, so the bars must never be summed. Text-derived shares use the 719 postings with a description, not all 720. The Styria steps count every ad that lists a Styrian site; by primary state Styria has 54.</sub>
<!-- BQ27_population_funnel:end -->

## 6. Requirement clusters (`cluster_requirements.py`)

Binary skill matrix (tech + statistics + business vocabulary, skills with ≥8 occurrences, postings with ≥2 skills) → L2-normalised k-means, k ∈ 4…10 chosen by silhouette, plus NMF(6) for additive topics. Clusters are described by over-represented skills (lift) and family/geo mix. The silhouette is low (reported in `outputs/clusters.json`); clusters are used as descriptive archetypes only, never as "real professions".

## 7. Official series (`jobbarometer_analysis.py`)

AMS JobBarometer counts are yearly online-ad counts per AMS occupation class (Berufsuntergruppe), Austria-wide and per Bundesland, 2020–2025, with "<20" censored. They are a different unit than our postings (occupation class vs title; year vs snapshot) and are used for longitudinal and market-size context, never merged with posting-level statistics.

## 8. From evidence to decisions

`docs/market-guide.md` reports findings table by table. `docs/career-map.md` and `CAREER_DECISION_MAP.md` map findings to the user's profile using an explicit evidence table (`docs/decision-framework.md`): each path is scored on transparent variables (postings, Styria postings, English-posting share, German-required share, skill overlap with profile, median advertised minimum salary, remote share) with stated normalisation and weights, plus a sensitivity check with alternative weights. No hidden scoring.

## 9. Reproduction

Run from the repository root. The six posting-collector scripts (first six lines) exist only in the private repository; the public tree starts at `collect_jobbarometer.py`. Every collector accepts `--date YYYY-MM-DD` to continue an existing dated folder.

```bash
pip install -r requirements.txt
python src/acquisition/collect_eures.py && python src/acquisition/collect_eures.py details
python src/acquisition/collect_eures_styria_text.py     # full-text sweep Styria/Vienna/Upper Austria -> data/raw/eures_textsearch (input of adjacent_demand.py)
python src/acquisition/collect_karriere.py && python src/acquisition/collect_karriere.py details
python src/acquisition/collect_linkedin.py && python src/acquisition/collect_linkedin.py details
python src/acquisition/collect_willhaben.py && python src/acquisition/collect_willhaben.py details
python src/acquisition/collect_jobsat.py && python src/acquisition/collect_jobsat.py details
python src/acquisition/collect_jobbarometer.py
python src/pipeline/build_interim.py && python src/pipeline/normalize.py && python src/pipeline/dedupe.py
python src/analysis/run_analysis.py && python src/analysis/cluster_requirements.py
python src/analysis/jobbarometer_analysis.py && python src/analysis/adjacent_demand.py
python src/analysis/make_figures.py && python src/analysis/export_agent_json.py
python -m pytest tests -q
```

Acquisition is not bit-reproducible (postings change daily); everything from `build_interim.py` onward is deterministic given `data/raw`. Raw data and posting collectors stay **unpublished** (PUBLICATION_DECISION.md, D-022): the public tree ships pipeline, configs and aggregates. Private research re-collection is allowed when the owner asks; new runs go in a new dated folder and are never merged with 2026-09-16. Do not bypass CAPTCHA, login, WAF or paywalls. Source terms still restrict automated extraction (docs/legal-and-publication-audit.md §2); that is why collectors are dark, not why they must be absent from the author's machine.

## 10. Collection conduct (for the record)

Request throttling 0.6–2 s per request with ±30 % jitter; exponential backoff (20 s × 2ⁿ) on HTTP 429/5xx; one worker per source, no concurrency inside a source; resumable by id and by completed (keyword, location) sweep; every request logged with status and result count; fixed browser-like User-Agent; no cookies, tokens, logins or CAPTCHA solving; robots.txt was not consulted programmatically at collection time and was reviewed only in the 2026-09-16 audit (LinkedIn and willhaben disallow the used search paths). Dynamic pages were read through the JSON their own front-ends load (karriere.at listing JSON, willhaben `__NEXT_DATA__`, EURES portal API), server-rendered pages (jobs.at, LinkedIn guest pages, JobBarometer) through HTML parsing, and structured data through schema.org JobPosting JSON-LD where present.
