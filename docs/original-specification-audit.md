# Original-specification audit

Audit date 2026-09-16. The original one-shot brief ("Austria Data Job Market Intelligence") is used as a literal checklist. Each requirement is classified COMPLETE / PARTIALLY COMPLETE / WEAK / MISSING / NOT APPLICABLE after verifying the implementation and the evidence in the repository, not the previous run's report. Where the audit changed something, the action is named. Counts refer to the post-audit run (DECISION_LOG D-012).

## A. Second-pass verification of the previous report's claims

| Claim | Verified? | Evidence |
|---|---|---|
| 12,429 raw rows | Yes | `data/raw/*/2026-09-16/details.jsonl` line counts: EURES 4,569 + karriere 2,114 + LinkedIn 4,133 + willhaben 1,508 + jobs.at 105 |
| 10,945 unique postings | Yes | `postings_dedup.parquet`: 10,945 groups / canonical rows |
| 824 core postings, 65 in Styria | **No longer** — 720 / 58 after the taxonomy precision fix (D-012); the old values were reproducible but contained ~29 % false positives on a hand-labelled sample |
| per-source counts | Yes (raw); core canonical now LinkedIn 300, EURES 202, karriere 134, jobs.at 58, willhaben 26 |
| 590 JobBarometer pages | Yes |
| 120+ evidence tables, 13 figures, 11 JSON summaries, 43 tests | Yes: 146 tables (now 149 with Q03c and T11e), 13 figures, 11 JSON; tests now 67 |
| Every canonical posting traceable to a source record | Yes: `posting_uid`, `source`, `source_id`, `source_url` populated for 100 % of core rows (private file) |
| Duplicates / cross-posts | Union-find on company+title+state and description fingerprint; 24.2 % in-scope duplicates; 20 % of core groups span sources; reposts collapsed by key; agency ads flagged (4.5 %) but not linked to client ads |
| EURES/AMS mirror treated appropriately | Yes: EURES rows are the AMS feed; anonymised employers (140 core rows) reported as "unnamed", not as separate employers |
| Stale postings | Age by source reported (T13b); 34 core ads > 180 days kept and flagged |

## B. Requirement-by-requirement table

| Original requirement | Status | Evidence | Gap | Action taken |
|---|---|---|---|---|
| Real Austrian labour-market data only; no fabrication | COMPLETE | Every number in the documents is printed by `src/reporting/digest.py` from `outputs/`; raw records stored verbatim (private) | — | Consistency check re-run after the rewrite |
| Styria/Graz focus | COMPLETE (small n) | Styria/Graz flags, T03c cities, T04a employers, Styria columns in every T05/T07/T09/T10 table, JB05 | n = 58 | Styrian figures now reported as counts ("8 of 58") |
| Job titles (exist, overlap, common, rare) | COMPLETE | T02, T02b (20 normalized titles), T02c raw titles, Q03c precision | Recall unmeasured | Precision audit added; 22 FP removed |
| Skills | COMPLETE | 13 categories, ~260 items (T05_*) | Rule-based; no discovery of unknown tools | Aliases added (D-012) |
| Technologies | COMPLETE | cloud_platforms, data_platforms, bi_tools, data_engineering categories reported separately | — | — |
| Frameworks | PARTIALLY COMPLETE | ml frameworks (PyTorch, TensorFlow, scikit-learn, LangChain, Hugging Face), web (FastAPI/Flask), orchestration (Airflow, dbt) exist inside python_ecosystem / data_engineering | No separate "frameworks" table; ads name frameworks in < 5 % of cases, so a dedicated table would be mostly zeros | Documented; categories listed in market-guide §5 |
| Libraries | COMPLETE (as observed) | python_ecosystem category (16 items) | Libraries are almost never named (pandas 3 %) — a finding, not a gap | — |
| Programming languages | COMPLETE | programming_languages category (16 items; SQL now includes SQL Server) | — | D-012 |
| Cloud platforms / databases / BI tools / ML tools | COMPLETE | separate categories and tables | — | — |
| Statistical skills | COMPLETE | statistics_methods category | Rarely named in ads (finding) | — |
| Business/domain skills; soft skills | COMPLETE (indicative) | business_domain, soft_skills categories; labelled "indicative wording counts" | Soft-skill patterns are coarse | — |
| Languages (German level, English-only, by role, by location) | COMPLETE after fix | T07 family: requirement class, level bucket, posting language, cross-tab, three addressable scenarios by scope and family | The "C1" bucket is mostly "sehr gut" wording; negotiability unmeasured | "English-only" renamed to "English-written, no stated German requirement"; bucket composition disclosed; causal wording removed |
| Certifications requested vs popular | COMPLETE | T11d after vocabulary extension with exam codes; ≤ 3 % each | Candidate-side popularity not in scope of postings data | D-012 vocabulary; finding stands |
| Degrees required vs preferred; study backgrounds | COMPLETE after fix | T11e (required/preferred/mentioned/none), T11a levels, T11b fields | "preferred" is rare (2.5 %) | New field and tables (D-012) |
| Remote/hybrid/local by role | COMPLETE | T10 (+ by family, by Styria, by source); days-per-week (6 ads) | Ads rarely state days | — |
| Salary (ranges, transparency, 14-salary convention, floors vs surveys) | COMPLETE | T09 coverage (minimum-only vs range, KV, overpay, all-in, bonus, part-time risk), T09b by family/title/seniority/state/language/skill; docs/salary-context.md | Actual compensation not estimable — stated explicitly | All-in/bonus/part-time flags added; wording "advertised floors" everywhere |
| Experience (years; what senior/junior mean) | COMPLETE | T08, T08a–d | Only 19 % of ads state years | — |
| Education | COMPLETE | see degrees | — | — |
| Locations; geographic concentration; commuting geography | COMPLETE | T03a–e, config/geo.json commuting list, multi-site handling | Commuting list is an assumption | — |
| Frequency / keyword frequency / title / location / language / certification / degree / tool frequency | COMPLETE | T02, T03, T05, T07, T11 with n, count, share and Wilson CI in every table | — | Denominators restated at the top of market-guide |
| Requirement co-occurrence; technology and skill combinations; rare/high-value combinations | COMPLETE | T06 pairs (lift, conditional shares), T06b size-3 stacks, T15 clusters/NMF; specific pairs (Python+SQL, SQL+Power BI, Azure+Databricks, Power BI+DAX, dbt+SQL) quoted | Clusters weak (silhouette 0.07) | Pair section expanded in market-guide §5 |
| Career paths | COMPLETE | docs/career-map.md §5, D01/D02 | No family robust (Styria < 30) | Ranking re-explained as size/openness/floor ranking, not ease of entry |
| Learning roadmap | COMPLETE | D04, career-map §7 | — | Re-derived from new tables |
| Project implications | COMPLETE | career-map §8 | — | — |
| CV / LinkedIn / GitHub implications | COMPLETE | career-map §9, CAREER_DECISION_MAP | — | — |
| Agent context (AGENT_CONTEXT.md with derived-from-evidence statement and date) | COMPLETE | AGENT_CONTEXT.md §0 and §21 | — | Publication status, data boundary, collection restrictions and update procedure added |
| Machine-readable JSON outputs | COMPLETE | 11 JSON files | — | URL/snippet keys scrubbed in the public export |
| Reproducibility | PARTIALLY COMPLETE (by design) | Deterministic pipeline from raw data; raw data private; posting collectors private | Outsiders cannot regenerate the aggregates; they can audit rules, code and table consistency | Stated in README and limitations §13 |
| Data quality report | COMPLETE | docs/data-quality.md with measured title precision | Extraction precision/recall for skills/language/salary still spot-checks only | Follow-up listed |
| Uncertainty | COMPLETE | Wilson CIs, robust/tentative rule, small-n flags, "What would change this map?" | — | Section added to CAREER_DECISION_MAP |
| Market/posting bias | COMPLETE | docs/posting-bias.md | — | — |
| Source provenance | COMPLETE | envelopes with source, collected_at, query, page; query logs; source_url per row (private) | — | — |
| Employer analysis; employer concentration; agencies; anonymised employers | COMPLETE after fix | T04, T04a, T04b now with named vs unnamed counts | Agency-client linkage impossible | "421 employers" wording replaced by "387 named employers nationally / 32 Styria; 140 postings unnamed" |
| Industry concentration | PARTIALLY COMPLETE | business_domain wording; LinkedIn industry field (T04c) for LinkedIn rows only | No industry field for AMS/karriere rows | Documented |
| Time dimension / longitudinal | PARTIALLY COMPLETE | T13 posted-by-week, T13b age by source; JobBarometer 2020–2025 | Single snapshot; permitted refresh channels only | Stock/flow wording audited; refresh re-scoped (D-013) |
| Salary normalisation (monthly × 14, plausibility) | COMPLETE | D-005; T09 | ×14 assumed uniformly (4 % of ads state it) | Assumption disclosed |
| Language bifurcation (German-written vs English-written; German required vs English-only) | COMPLETE after fix | T07c, T07d, T07e | — | Wording corrected |
| Austrian regional comparison (Vienna, Upper Austria, Salzburg, Tyrol, Styria) | COMPLETE | T03a, T03_family_by_state, T09b by state, JB05 | Small n outside Vienna/UA/Styria | — |
| Multinational vs Austrian companies | WEAK | Only proxied by posting language and LinkedIn industry; no ownership field | Would need an employer-attribute table | Listed as a follow-up; not claimed |
| Contract types; full-time vs part-time; internships/working-student | COMPLETE | T12, T12a | — | — |
| Employer/board overlap and platform bias | COMPLETE | T01b, T03e, T07 by source, T09a | — | — |
| Research-landscape survey (GitHub/Kaggle/HF/ESCO/O*NET) | COMPLETE | docs/research-landscape.md | AMS open-data catalogue not verifiable (JS) | — |
| Decision framework with weights and sensitivity | COMPLETE | docs/decision-framework.md, D01/D02 | V5 is subjective (self-declared profile) | Stated explicitly |
| DECISION_LOG | COMPLETE | D-001 … D-014 | — | — |
| Tests/validation | COMPLETE | 67 tests; digest consistency check | — | Tests for new rules added |
| Self-critique; final report | COMPLETE | this audit; docs/limitations.md; PUBLICATION_DECISION.md | — | — |
| Do not bypass access controls | COMPLETE (technical) / see note | No login, CAPTCHA or paywall bypass; **but** the sources' terms restrict automated extraction (not checked in the original run) | — | Recorded in the legal audit; collection restrictions adopted (D-013) |
| Private repository / rich raw evidence retained | COMPLETE | 1.3 GB raw + processed retained privately | — | Public version sanitised |

## C. Skeptical second-pass findings and corrections

1. **Role taxonomy precision.** 25 titles per family were hand-labelled: strict precision 71 % (BI 56 %, governance 56 %, business analysis 64 %, product analytics 33 %). Rules fixed; re-measured 83 % strict / 95 % lenient. Core set 824 → 720.
2. **"English-only addressable set: 155 of 823 / 9 of 65".** The definition was "posting written in English AND german_requirement not in {required, required_implied, german_or_english}" — it included ads where German is "preferred". Renamed and explained; new values 141 of 719 / 8 of 58; the "preferred" share in English ads (19 %) is now stated next to it.
3. **"C1-equivalent in 38 % of ads".** The bucket consisted mostly of "sehr gut/very good" wording (172 of 261), not explicit C1 or "verhandlungssicher". Composition disclosed in every document.
4. **"German C1 is the single largest lever … moves the set from ~9 to 34–42".** Rewritten as an observed requirement pattern (8 / 30 / 37 of 58) with an explicit statement that negotiability and hiring effects are not measured.
5. **"87 % skill overlap".** = 13 of the 15 most-mentioned data_analytics skills are in the self-declared have-or-developing lists. Now stated as a count with its subjective basis.
6. **"421 named employers, Styria 35".** 421 was national; now "387 named employers nationally / 32 in Styria; 140 core postings (19 %) carry no employer name".
7. **Vienna "418" vs "410".** 418/410 were the multi-site vs primary-state counts; both are now labelled (350 / 343).
8. **Snapshot vs flow.** No document called the snapshot "jobs per year"; the distinction is now stated at the top of market-guide, AGENT_CONTEXT and CAREER_DECISION_MAP and in README.
9. **Salary.** Minimum-only share (81 % of figures), all-in (10 %), bonus (9 %) and part-time-basis risk (8 figures) added; "actual compensation cannot be estimated" stated.
10. **Certifications ≤ 1 %.** Re-tested after adding exam codes and professional certificates: still ≤ 3 % each (IREB/IIBA in business-analysis ads is the only one above 1 %).
11. **SQL / Power BI aliases.** "SQL Server" mentions were excluded from SQL by a negative lookahead (fixed: SQL 35 % → 40 %); "MS SQL", "Microsoft Power BI", "Power Query" added.
12. **Co-occurrence.** Specific pairs requested in the follow-up brief were computed and quoted (market-guide §5); Power BI + DAX is only 3 %, dbt + SQL 3 %.
13. **Personal data.** Present in raw/processed files and in four output tables (snippets); excluded from every public artefact by the export script and its scan.
14. **Terms of use.** Not reviewed in the original run; reviewed now (legal audit §2); consequences recorded (D-013).

## D. Areas that remain weak or out of reach

* Multinational vs Austrian employer comparison (no ownership attribute).
* Recall of the title rules; precision/recall of skill, language and salary extraction (spot-checks only).
* StepStone/Indeed coverage and Styrian career pages.
* Longitudinal evidence beyond the JobBarometer series.
* Hiring outcomes — the only observation that can turn requirement patterns into evidence about hiring.
