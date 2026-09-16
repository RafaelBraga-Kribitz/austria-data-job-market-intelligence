# Data-quality report (run of 2026-09-16, post-audit)

Generated from `outputs/tables/Q*.csv`, `outputs/data_quality.json`, `dedupe_summary.csv`, `T01*`, `T13b`. Re-run `src/analysis/data_quality.py` after every pipeline run and update this page. The pre-audit run (824 core postings) is superseded by the rule revision in DECISION_LOG D-012.

## 1. What was collected

| Source | Raw rows | In-scope rows | Adjacent rows | With description | Core canonical | Detail fetch |
|---|---|---|---|---|---|---|
| EURES (AMS mirror) | 4,569 | 223 | 134 | 100 % | 202 | 4,569/4,569 detail records (reference, feed) |
| karriere.at | 2,114 | 200 | 126 | 100 % (JSON-LD) | 134 | 2,114/2,114 (HTTP 500 retried with backoff; 0 missing) |
| LinkedIn guest | 4,133 | 486 | 363 | 99.8 % | 300 | 4,133/4,133 |
| willhaben | 1,508 | 40 | 21 | 100 % | 26 | 1,508/1,508 |
| jobs.at | 105 | 65 | 12 | 100 % | 58 | 105/105 |
| AMS JobBarometer | 590 pages (59 occupations × 10 regions) | – | – | – | – | 0 failures |
| EURES full-text sweep (Styria/Vienna/Upper Austria) | 3,867 / 3,419 / 4,811 postings | – | – | 100 % | – | – |

No source returned CAPTCHA or blocked mid-run; all query logs are in `data/raw/<source>/2026-09-16/query_log.jsonl` (private). Terms-of-service findings for each source are in docs/legal-and-publication-audit.md §2.

## 2. Duplicate rate and source overlap (Q04, T01b)

* 12,429 rows → 10,945 unique groups overall; among in-scope rows 1,670 → 1,266 groups (**24.2 % duplicates**). 186 core groups have size > 1; 145 core groups (20 %) span more than one source.
* Single-source groups dominate: LinkedIn-only 290, AMS-only 186, karriere-only 77; cross-source: karriere+LinkedIn 48, jobs.at+karriere 33, jobs.at+karriere+LinkedIn 20, EURES+LinkedIn 16. jobs.at is largely a karriere.at mirror; AMS and LinkedIn barely overlap.
* Reposts vs separate vacancies: within-source reposts (same employer + title, different ids) are listed in Q04a and collapsed by the (company, title, state) key; multi-post ads (`number_of_posts` > 1 in EURES) are counted once. Residual duplication is likely among AMS rows with anonymised employers (140 core rows) where only the description fingerprint can match, and among LinkedIn re-posts with changed ids. Estimated residual: low single-digit percent (not measured).
* Recruitment agencies: `is_agency` flags 4.5 % of named postings; agency and client ads for the same vacancy cannot be linked and are counted separately.

## 3. Missingness and coverage (Q01, Q02)

Core postings, share with usable value:

| Field | EURES | karriere | LinkedIn | willhaben | jobs.at |
|---|---|---|---|---|---|
| description > 300 chars | 100 % | 100 % | 99.8 % | 100 % | 100 % |
| salary figure | 94 % | 92 % | 64 % | 95 % | 95 % |
| salary range | 22 % | 19 % | 8 % | 3 % | 19 % |
| German mentioned | 56 % | 62 % | 63 % | 68 % | 62 % |
| state known | 99 % | 100 % | 96 % | 100 % | 97 % |
| city known | 54 % | 92 % | 89 % | 93 % | 97 % |
| posted date | 100 % | 100 % | 100 % | 100 % | 100 % |
| seniority word in title | 31 % | 40 % | 55 % | 30 % | 48 % |
| remote statement | 47 % | 84 % | 53 % | 48 % | 69 % |
| employer named | 31 % (69 % anonymised) | 100 % | 100 % | 100 % | 100 % |

Implications: salary analysis is AMS/karriere-weighted (LinkedIn under-reports); employer analysis is LinkedIn/karriere-weighted; city-level geography for AMS rows relies on NUTS-3 codes (Graz = AT221) rather than addresses.

## 4. Title normalization confidence (Q03a, Q03b, Q03c)

* 10,945 canonical rows → core 720 (6.6 %), other_data 235, ai_software_engineering 311, out_of_scope 9,679 (of which 4,410 matched no rule at all, 235 were removed by a soft override after a generic data match, 54 by hard overrides such as "data center", security, laboratory, embedded, regulatory reporting, privacy).
* The high out-of-scope share is expected: EURES/LinkedIn keyword search is token-based ("data engineer" returns every "engineer").
* **Measured precision (Q03c).** 25 random canonical titles per family from the pre-audit run were hand-labelled TP / borderline / FP and re-classified with the revised rules:

| Family | strict precision before → after | lenient (borderline = correct) before → after | FP removed / TP lost |
|---|---|---|---|
| bi | 56 % → 88 % | 60 % → 94 % | 9 / 0 |
| business_analysis | 64 % → 76 % | 80 % → 90 % | 3 / 0 |
| data_analytics | 84 % → 95 % | 92 % → 100 % | 2 / 1 |
| data_engineering | 88 % → 88 % | 96 % → 96 % | 0 / 0 |
| data_governance | 56 % → 64 % | 84 % → 95 % | 3 / 0 |
| data_science | 72 % → 90 % | 88 % → 100 % | 3 / 0 |
| marketing_analytics | 83 % → 83 % | 92 % → 92 % | 0 / 0 |
| product_analytics (n 3) | 33 % → 100 % | 33 % → 100 % | 2 / 0 |
| **all (177)** | **71 % → 83 %** | **84 % → 95 %** | 22 / 1 |

  The main false positives were generic SAP/banking/AI consultants under "bi", regulatory/EDI reporting specialists, security analysts, privacy officers, actuaries under data science, a laboratory "Produktanalytiker" and a "Bi-Static" radar thesis. Remaining borderline mass: master/product-data maintenance roles (kept in data_governance under their own normalized title) and IT-analyst/process-owner titles in business_analysis. Recall (data roles with titles that match no rule) is not measured; `other_data` (235) holds the candidates.
* AMS occupation labels (attached in EURES titles) are retained; the AMS "Data-Warehouse-Analyst/in" class maps to several of our families (T02d).

## 5. Geography (Q03a)

716 of 720 core rows have high-confidence location (explicit field or NUTS code); 3 have none; 22 are Austria-wide/unspecified; 61 are multi-site. The "Graz area" flag uses a fixed commuting list (config/geo.json) — an assumption.

## 6. Stale postings (Q05, T13b)

Median age at collection: karriere.at 5 days (the board refreshes dates, so its ages are not comparable), LinkedIn 14, jobs.at 19, willhaben 34, AMS/EURES 41 days. 153 core rows are older than 60 days, 34 older than 180 days, 6 older than a year (evergreen ads, mostly AMS/willhaben). They are kept; downstream tables do not weight by age.

## 7. Salary parsing (Q07, Q07a, Q07b, T09)

* 569 core postings with a plausible figure; 39 from structured fields (karriere JSON-LD, willhaben), 530 parsed from text near salary words. 4 figures were discarded as implausible (< €900 or > €20,000 per month; > €300k per year); upper ends above €300k or 3× the minimum are dropped.
* Kind of figure: 460 of 569 are a single minimum (81 %); 109 ranges; collective-agreement wording in 59 % of core ads; overpay wording 53 %; "all-in" 10 %; bonus/variable 9 %; 8 parsed figures sit next to part-time wording (flag `salary_part_time_basis_risk`).
* Period detection: context words (monat/jahr) where present, otherwise magnitude (< €12,000 → monthly). Monthly × 14 (the Austrian 14-payment convention; only 4 % of ads state "14×" explicitly, so the factor is an assumption applied uniformly). Gross is assumed; two ads with "netto" nearby state gross figures.
* Spot-check sample of 40 (Q07a): figures and periods were consistent with the snippet text; the main residual risk is part-time bases stated as monthly figures and figures for a different role in multi-role ads.
* What cannot be measured: actual offers, market-clearing pay, bonus size, the value of "Überzahlung".

## 8. Language, remote, education extraction

* Language classification is context-window based; the audit found the main confusion to be company blurbs ("deutsches Unternehmen"), which are excluded by pattern, and lists like "Deutsch und Englisch verhandlungssicher", which are correctly read as both required. The C1/fluent bucket contains 30 explicit C1 codes, 56 "verhandlungssicher/fließend/fluent" and 172 "sehr gut/very good/excellent" — the last mapping is an assumption stated in every document.
* Remote: 40 % of ads say nothing; "hybrid_or_flexible" (26 %) is a generic home-office mention without a pattern. Only 6 ads give days per week — the "office attendance" question cannot be answered from ads.
* Education: level/field detection is restricted to windows around education words (D-011). Since D-012 the wording strength is stored in four classes (`degree_requirement` = required / preferred / mentioned / none, T11e); "preferred" is rare (2.5 %) because Austrian ads seldom soften degree wording explicitly.

## 9. Skill extraction (Q09)

Controlled vocabulary of ~260 canonical items (SQL now includes SQL Server mentions; "MS SQL", "Microsoft Power BI", "Power Query" aliases and certification exam codes added in D-012). A 30-posting spot-check (Q09) showed no false positives for Python/SQL/Power BI/Azure and one remaining generic-term issue: "Data Governance/Quality" also fires on "Datenqualität" in task descriptions (kept as a wording indicator). Precision/recall are not formally measured; see docs/limitations.md follow-up 4.

## 10. Personal data and secrets in the collected material

The raw and processed files contain named contact persons, e-mail addresses and phone numbers from the advertisements (≈2,400 distinct addresses) and willhaben `contact` objects; no credentials or tokens of the author. These fields are not used by any analysis and are excluded from every public artefact (docs/legal-and-publication-audit.md §1, §7).

## 11. What this dataset can and cannot say

Can (robust): ranking of role families and titles; ranking and approximate level of the top-10 technologies; German-vs-English posting split; that certifications and PhDs are rarely requested; Vienna dominance; advertised salary floors by family/seniority; the official yearly trend and Styria's share from JobBarometer.

Cannot (or only tentatively): exact Styrian percentages (n = 58); marketing/product-analytics profiles (n ≤ 24); anything about StepStone-only employers; hiring outcomes; whether stated German levels are negotiable; remote-days norms; actual pay; year-over-year change in *our* snapshot (single run).
