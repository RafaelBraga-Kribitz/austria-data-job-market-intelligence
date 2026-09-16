# DECISION_LOG

Analytical and engineering decisions, in chronological order. Each entry: what was decided, why, and what it affects. Dates are absolute (Europe/Vienna).

## D-001 · 2026-09-16 · Sources selected and excluded

**Decided.** Posting-level evidence is collected from five sources that are reachable by a plain HTTP client without login, token, or CAPTCHA: EURES public API (mirror of AMS "PES Austria" feed), karriere.at, LinkedIn logged-out guest endpoints, willhaben Jobs, jobs.at. Official aggregate evidence comes from AMS JobBarometer (yearly online-ad counts per occupation × Bundesland) and the AMS/Statistik Austria/Eurostat sources listed in docs/research-landscape.md.

**Excluded.** StepStone.at (HTTP 403 bot wall), Indeed.at (Cloudflare 403), hokify (AWS WAF JavaScript challenge), Glassdoor (login wall), AMS "alle jobs" API directly (returns 401 without an OAuth bearer token issued by the AMS authentication service; not bypassed — the same postings are obtained via EURES), metajob.at (aggregator; would duplicate), derStandard Jobs (structure unclear, low marginal value), devjobs.at (listing is a streamed React Router payload and robots.txt disallows search/API paths; deferred). Adzuna/Jooble APIs require account registration, which this project does not do.

**Why.** Rule: never bypass access controls; maximise coverage across platform types (public employment service, generalist board, professional network, classifieds board).

**Effect.** Platform bias is measurable via cross-source overlap (T01b) but StepStone/Indeed-only postings are missing; see docs/limitations.md.

## D-002 · 2026-09-16 · Search strategy: broad title-keyword superset, relevance decided downstream

**Decided.** Each source is queried Austria-wide with ~45 title keywords (EN+DE, config/queries.json). Relevance is NOT decided by the query but by rule-based title normalization (config/role_taxonomy.json). Everything retrieved is retained in data/raw; out-of-scope rows stay in the processed files with role_family = out_of_scope.

**Why.** Query-based inclusion would silently encode the search terms into the market definition. Keeping the superset allows auditing false negatives and re-classifying later.

**Effect.** ~85% of raw rows are out of scope (EURES title search is token-based and returns e.g. every "Engineer"). This is expected and documented in docs/data-quality.md.

## D-003 · 2026-09-16 · Role taxonomy and title normalization

**Decided.** Ordered regex rules map cleaned titles to (normalized_title, role_family). Families: data_analytics, bi, data_science, data_engineering, data_governance, marketing_analytics, product_analytics, business_analysis (= CORE); ai_software_engineering and other_data (= ADJACENT, reported separately); out_of_scope. Title cleaning removes gender markers, location/hours noise and hyphenation; the AMS occupation label appended by AMS in parentheses is kept in ams_occupation_label. Hard exclusions: data entry, data center, Datenerfassung. Soft exclusions (lab/biomedical analysts, IFRS/accounting reporting, security/SOC analysts, generic software/backend/platform roles without a data/AI word) apply only to titles that no specific rule matched.

**Why.** Transparent, auditable, bilingual; the user's target families must be visible as separate categories rather than collapsed. "AI software engineer" titles are frequent but are software-engineering roles, so they are isolated instead of contaminating data_science.

**Effect.** The core analysis set = canonical rows in CORE families. A misclassification audit is in docs/data-quality.md.

## D-004 · 2026-09-16 · Geography

**Decided.** State (Bundesland) is derived from, in priority order: explicit location fields, NUTS-3 codes (EURES), workplace lines / postcodes / city names in the description, city names in the title. "Graz area" = Graz city plus the Graz-Umgebung municipalities and district towns on S-Bahn lines within ~45 min (config/geo.json → graz_commute), an analytical assumption. is_austria_wide flags "österreichweit"/unspecified-Austria postings. A posting labelled "Graz" is not assumed to be physically in Graz beyond the employer's stated location.

## D-005 · 2026-09-16 · Salary normalization

**Decided.** Advertised figures only. Monthly gross figures are converted to annual gross using ×14 (Austrian collective-agreement convention of 14 payments) and labelled salary_conversion_note. Annual figures are taken as stated. Figures outside 900–20,000 €/month or 12,000–300,000 €/year are marked implausible and excluded. Minimum-only figures (typical Austrian "KV-Mindestgehalt" statements) are kept separate from ranges (salary_basis). Third-party salary surveys are never merged into these tables; they are cited separately in docs/salary-context.md.

**Why.** Austrian job ads legally state a minimum salary; most figures are therefore legal minimums, not offers. Mixing them with survey medians would be misleading.

## D-006 · 2026-09-16 · Language requirement classification

**Decided.** German/English requirements are extracted from context windows around language mentions: required / required_implied (level stated, no explicit "required" word) / preferred / mentioned / german_or_english / explicitly_not_required / not_mentioned; level buckets from CEFR codes or descriptor words (verhandlungssicher→C1/fluent, gut→B2/good, Grundkenntnisse→A1-A2). Posting language (de/en) is inferred from stop-word ratios and reported as a separate variable. "Addressable market" scenarios (T07e) use explicit rule sets rather than a single binary.

## D-007 · 2026-09-16 · Duplicate detection

**Decided.** Union-find over three keys: (company_norm, title_clean, state); (title_clean, state|any, description fingerprint of first 400 normalised chars); (company_norm, title_clean) when a state is missing. Canonical row = longest description, tie-break by source priority karriere > linkedin > eures > willhaben > jobsat. Within-source duplicates by source_id are collapsed earlier. All rows are retained with group ids.

**Why.** Cross-posting is common (karriere↔jobs.at↔LinkedIn). EURES/AMS rows anonymise the employer, so they can only match by fingerprint; residual duplication is quantified in T01b/dedupe_summary.csv.

## D-008 · 2026-09-16 · Skill extraction = controlled vocabulary, not ML

**Decided.** ~250 canonical skills in 13 categories (config/skills_taxonomy.json) matched with bilingual regexes on title+description. No embedding/NER model.

**Why.** Transparent, reproducible, bilingual, and the sample (low thousands) does not justify a model whose errors could not be audited. Known weaknesses: single-letter "R", generic words ("cloud", "AI") are kept as separate "(generic)" entries; soft-skill patterns are indicative only.

## D-009 · 2026-09-16 · Denominators

**Decided.** Text-derived features (skills, languages, education, remote, experience) use postings with a description of >300 characters as denominator; structural features (family, state, seniority, salary presence) use all canonical core postings. Every table stores n.

## D-010 · 2026-09-16 · Repository location

**Decided.** The repository lives at C:\Users\Benutzer1\Dev\austria-data-job-market-intelligence (moved out of the session scratch workspace, which is deleted with the session).

## D-011 · 2026-09-16 · Extraction fixes after first full-data audit

**Decided.** (a) The R-language pattern now requires an upper-case, stand-alone "R" not preceded by a gender-suffix separator (":r", "*r", "/r") — German inclusive forms ("interne:r", "jede/r") had produced ~20% false positives in business-analysis ads. (b) Degree levels/fields are detected only within ±200 characters of an education word ("Studium", "degree", "Abschluss", …) so that "software engineering" in a task list no longer counts as an engineering degree. (c) Salary upper ends above €300k or above 3× the minimum are dropped as parsing artefacts. (d) Generic "optimisation/simulation" mentions were removed from the ML vocabulary; "flexible" was removed from the resilience soft-skill pattern (it matched "flexible Arbeitszeiten"). (e) JobBarometer yearly tables are re-parsed from stored HTML after a regex bug that skipped alternate years; the 2025 Austrian count for "Data Scientist (m/w)" is 2,207 (not 2,680, which was 2024).

**Why.** Audit of table outputs (Q03b/Q07a/Q09 samples) against raw text. **Effect.** All T05/T09/T11/JB tables regenerated; rule versions are those committed with this log entry.

## D-012 · 2026-09-16 · Taxonomy and extraction revision after the publication/completeness audit

**Decided.** (a) Role rules tightened after a hand-labelled precision audit of 25 titles per family (Q03c): BI consultant patterns now require a data/analytics/BI word (generic SAP, banking and AI consultants had been counted as BI); "reporting specialist" no longer counts without a data word; regulatory/financial/ESG/EDI reporting, security/SOC, embedded/firmware, laboratory, thesis, privacy-officer and "Bi-Static" titles are hard exclusions; actuaries/mathematicians move to an adjacent rule; product owners and lab "Produktanalytiker" leave product_analytics; generic "Künstliche Intelligenz" titles go to ai_software_engineering; the ML-engineer label becomes "Machine Learning / AI Engineer" because it contains "AI Engineer" titles; data_governance is split into governance proper and "Master / Product Data Management (operational)". (b) SQL now counts "SQL Server" mentions; aliases "MS SQL", "Microsoft Power BI", "Power Query" and certification exam codes (DP-/AZ-/PL-, Google Professional, CDMP/DAMA, IREB/IIBA/CBAP, PMP/IPMA/PRINCE2) added. (c) New field `degree_requirement` (required / preferred / mentioned / none) and tables T11e. (d) New salary flags `salary_all_in_mention`, `salary_bonus_mention`, `salary_part_time_basis_risk`; T09 coverage extended. (e) T04b now reports named vs unnamed employer postings. (f) Tests extended to 67. The one-off patch is `src/pipeline/patch_configs_2026-09-16_audit.py`.

**Why.** The audit found 40 % strict false positives in the BI sample, 36 % in business analysis and 44 % in governance; overall strict precision 71 %. **Effect.** Core set 824 → 720 postings (Styria 65 → 58); strict precision on the same sample 83 % (lenient 95 %); all T/D/Q tables, figures and JSON exports regenerated; all decision documents rewritten with the new numbers. The pre-D-012 processed file is kept privately as `data/processed/_pre_D012/` for the audit trail.

## D-013 · 2026-09-16 · Collection terms and future acquisition

**Decided.** The legal/publication audit (docs/legal-and-publication-audit.md) established that all five posting sources restrict automated extraction in their terms (EURES "Find a job" terms reserve API/scraping extraction to EURES partners; karriere.at Nutzungsbedingungen 2.8.3 and jobs.at AGB 2.3.3 forbid "automatisierte Auswertung"; LinkedIn User Agreement 8.2 and robots.txt `Disallow: /jobs-guest/`; willhaben robots.txt `Disallow: /jobs/suche?*` plus AGB Pkt 8 TDM reservation). The 2026-09-16 collection is kept as a one-off private research dataset. The LinkedIn and willhaben collectors are not to be re-run; re-running the EURES, karriere.at and jobs.at collectors requires an explicit owner decision or permission from the source. The AMS JobBarometer collector remains usable. The originally planned "monthly re-collection" is re-scoped to permitted channels (JobBarometer, AMS open data, permissions, licensed data).

**Why.** The original brief forbade bypassing technical access controls but did not require a terms review; the audit is the first place these clauses were read. **Effect.** README, AGENT_CONTEXT §21 and docs/limitations.md state the restriction; the public repository does not distribute the posting collectors.

## D-014 · 2026-09-16 · Split publication model

**Decided.** The repository is published on GitHub as a sanitised research version built by `src/publish/export_public.py`: code (without the six posting collectors), configs, schemas, tests, docs, decision documents, figures, aggregated tables (five per-posting tables and every text/URL column removed) and JSON summaries, with a fresh git history. `data/raw`, `data/processed`, `data/external`, logs and the posting collectors remain private. Licence: MIT for code, CC BY 4.0 for documents and aggregated outputs.

**Why.** The raw material contains third-party advertisement text and personal contact data and was collected against source terms; aggregated statistics contain neither, are not a substantial part of any source database, and are what the research needs to be auditable. Details and risk levels in docs/legal-and-publication-audit.md; decision in PUBLICATION_DECISION.md.
