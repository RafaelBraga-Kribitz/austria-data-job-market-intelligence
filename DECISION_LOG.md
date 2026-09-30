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

**Decided.** (a) Role rules tightened after a hand-labelled precision audit of 25 titles per family (Q03c): BI consultant patterns now require a data/analytics/BI word (generic SAP, banking and AI consultants had been counted as BI); "reporting specialist" no longer counts without a data word; regulatory/financial/ESG/EDI reporting, security/SOC, embedded/firmware, laboratory, thesis, privacy-officer and "Bi-Static" titles are hard exclusions; actuaries/mathematicians move to an adjacent rule; product owners and lab "Produktanalytiker" leave product_analytics; generic "Künstliche Intelligenz" titles go to ai_software_engineering; the ML-engineer label becomes "Machine Learning / AI Engineer" because it contains "AI Engineer" titles; data_governance is split into governance proper and "Master / Product Data Management (operational)". (b) SQL now counts "SQL Server" mentions; aliases "MS SQL", "Microsoft Power BI", "Power Query" and certification exam codes (DP-/AZ-/PL-, Google Professional, CDMP/DAMA, IREB/IIBA/CBAP, PMP/IPMA/PRINCE2) added. (c) New field `degree_requirement` (required / preferred / mentioned / none) and tables T11e. (d) New salary flags `salary_all_in_mention`, `salary_bonus_mention`, `salary_part_time_basis_risk`; T09 coverage extended. (e) T04b now reports named vs unnamed employer postings. (f) Tests extended to 67. The one-off patch is `src/pipeline/migrations/patch_configs_2026-09-16_audit.py` (moved from `src/pipeline/` on 2026-09-30).

**Why.** The audit found 40 % strict false positives in the BI sample, 36 % in business analysis and 44 % in governance; overall strict precision 71 %. **Effect.** Core set 824 → 720 postings (Styria 65 → 58); strict precision on the same sample 83 % (lenient 95 %); all T/D/Q tables, figures and JSON exports regenerated; all decision documents rewritten with the new numbers. The pre-D-012 processed file is kept privately as `data/processed/_pre_D012/postings_dedup.parquet` (git-ignored, 52 MB, 2026-09-16) for the audit trail.

## D-013 · 2026-09-16 · Collection terms and future acquisition

**Decided.** The legal/publication audit (docs/legal-and-publication-audit.md) established that all five posting sources restrict automated extraction in their terms (EURES "Find a job" terms reserve API/scraping extraction to EURES partners; karriere.at Nutzungsbedingungen 2.8.3 and jobs.at AGB 2.3.3 forbid "automatisierte Auswertung"; LinkedIn User Agreement 8.2 and robots.txt `Disallow: /jobs-guest/`; willhaben robots.txt `Disallow: /jobs/suche?*` plus AGB Pkt 8 TDM reservation). The 2026-09-16 collection is kept as a one-off private research dataset. The LinkedIn and willhaben collectors are not to be re-run; re-running the EURES, karriere.at and jobs.at collectors requires an explicit owner decision or permission from the source. The AMS JobBarometer collector remains usable. The originally planned "monthly re-collection" is re-scoped to permitted channels (JobBarometer, AMS open data, permissions, licensed data).

**Why.** The original brief forbade bypassing technical access controls but did not require a terms review; the audit is the first place these clauses were read. **Effect.** README, AGENT_CONTEXT §21 and docs/limitations.md state the restriction; the public repository does not distribute the posting collectors.

## D-014 · 2026-09-16 · Split publication model

**Decided.** The repository is published on GitHub as a sanitised research version built by `src/publish/export_public.py`: code (without the six posting collectors), configs, schemas, tests, docs, decision documents, figures, aggregated tables (five per-posting tables and every text/URL column removed) and JSON summaries, with a fresh git history. `data/raw`, `data/processed`, `data/external`, logs and the posting collectors remain private. Licence: MIT for code, CC BY 4.0 for documents and aggregated outputs.

**Why.** The raw material contains third-party advertisement text and personal contact data and was collected against source terms; aggregated statistics contain neither, are not a substantial part of any source database, and are what the research needs to be auditable. Details and risk levels in docs/legal-and-publication-audit.md; decision in PUBLICATION_DECISION.md.

## D-015 · 2026-09-16 · Seasonality answered from an external series, not from the snapshot

**Decided.** Seasonality ("when in the year are most jobs advertised?") is answered from Eurostat `jvs_q_nace2` (Statistik Austria Offene-Stellen-Erhebung), Austria, quarterly, non-seasonally-adjusted, 2009-Q1…2025-Q4, via a new public collector `src/acquisition/collect_eurostat_jvs.py` and `src/analysis/seasonality.py` (tables S01–S06, figure F13, `outputs/seasonality.json`, `docs/seasonality.md`). The seasonal index is computed two ways — ratio to own-year mean and ratio to a 2×4 centred moving average — with t-based intervals across years and sensitivity runs excluding 2020–2021 and restricted to 2015+.

**Why not from our own data.** The posting layer is a one-day snapshot, so the distribution of first-publish dates is posting volume multiplied by the probability that an advertisement is still open: 52 % of the 720 core postings were first published in the collection month and 90 % within 90 days. That is survival decay and seasonality is not identifiable from it. This is recorded as table S05 so the claim is checkable rather than asserted.

**Findings.** Q4 is the weakest quarter in all four sector aggregates, under both methods and all samples, and the modal weakest quarter in 8–10 of 16–17 years; Q1 is the most frequent annual peak in industry & construction and in the total economy; the Q3 peak in market services is confounded with tourism and retail, which share the NACE G-N aggregate with ICT; and the seasonal amplitude (5–14 %) is 19–49 times smaller than the between-year variation (255–567 %).

**Effect.** New sections in `CAREER_DECISION_MAP.md` ("When in the year should I apply…") and `AGENT_CONTEXT.md` §11b, with an explicit advising rule not to recommend month-level timing on this evidence. Eurostat is an openly licensed, documented API with no restriction on automated access, so its collector **and its raw response** are published — the seasonality layer is the one part of the project an outsider can reproduce end to end.

## D-016 · 2026-09-17 · Layer 2 (candidate supply) and Layer 3 (demand × supply) added; Layer 1 preserved

**Decided.** The project gains a second analytical layer (observed candidate supply) and a third (demand × supply × evidence) without touching the Layer 1 pipeline, taxonomies or tables. Layer 2 reuses the Layer 1 role rules (applied to profile bios after bio-specific overrides), the Layer 1 skill vocabulary (applied to bios, repository metadata and READMEs) and the Layer 1 geography file; it adds only what Layer 1 does not need (`config/supply_taxonomy.json`: sampling frames, data-repository lexicon, project topic/format/README taxonomies, evidence rules; `config/capability_map.json`: skill → capability groups used on both sides). Versions: Demand v1 (2026-09-16), Supply v1 (2026-09-17), Demand × Supply v1.

**Why.** A parallel taxonomy would make the join meaningless; the brief's requirement is that Layer 3 preserves Layer 1's assumptions.

## D-017 · 2026-09-17 · Sources for candidate supply: GitHub API as the only automated profile-level source

**Decided.** Profile-level supply is collected from the **GitHub REST API** (documented, authenticated with the owner's token, within published rate limits, descriptive User-Agent, no names or e-mail addresses fetched) in three sampling frames: A = data keywords in the bio × Austrian location tokens; B = the complete population of accounts with ≥ 1 public repository whose location matches a Styrian token; C = a base-rate sample of accounts in other regions sliced by account-creation year. Repositories (owner, non-fork) are fetched for every account; README text and the top-level file tree for repositories classified as data repositories; social-account links for data-signal users. Census-type context comes from **Eurostat** (graduates by ISCED-F field, employment by ISCO, ICT specialists; open API) and the **Stack Overflow Developer Survey 2025** (ODbL; 410 Austrian respondents; official download URL returned 404 on 2026-09-17, so the identical zip was taken from a public GitHub mirror and recorded as SOURCE_QUALITY B).

**Terms reviewed.** GitHub Acceptable Use Policies §7 (fetched 2026-09-17): *"Researchers may use public, non-personal information from the Service for research purposes, only if any publications resulting from that research are open access"* and *"You may not use information from the Service … for spamming purposes, including … selling personal information, such as to recruiters, headhunters, and job boards."* The project is non-commercial, its publications are CC BY 4.0, it collects no names/e-mails and publishes only aggregates. Bios and free-text locations are personal information and are therefore retained privately only (docs/legal-and-publication-audit.md §10).

**Not collected.** Kaggle (API requires account credentials the project does not create; site scraping prohibited; Meta Kaggle carries no location), personal portfolio sites (no legitimate enumerable frame; only link *types* from GitHub profiles are counted), search-engine-indexed profiles (not reproducible; would collect names), candidate databases of job boards (employer-only access), Meetup member counts (page structure not machine-readable; low value). Each is recorded with its coverage consequence in docs/supply-research-audit.md.

## D-018 · 2026-09-17 · LinkedIn: no automated collection; a private "dark" slot for manual observations

**Decided.** LinkedIn candidate profiles are **not** collected by any automated means (User Agreement 8.2, robots.txt `Disallow: /`, D-013; automated profile collection would also be profiling of identifiable persons under GDPR). The owner asked on 2026-09-17 not to rule LinkedIn out and to keep the layer offline if necessary. The resolution is a **manual, offline slot**: `src/acquisition/ingest_linkedin_manual.py` writes two templates under `data/raw/linkedin_supply/<date>/` (people-search result counts by title × location × filter; hand-coded public profiles under observer-assigned pseudonymous ids, no names/URLs) and ingests them into the Layer 2 schema, where `build_supply.py` treats them as `source = linkedin_manual`. These paths are git-ignored and excluded from the public export. The protocol is in docs/supply-methodology.md §7. Until records exist, every LinkedIn dimension of the brief is reported as NOT COLLECTED with the GitHub cross-link share as the only proxy.

**Why.** The brief forbids circumventing source restrictions; the intelligence value can still be captured by the owner's own manual use of the platform, which its terms permit.

## D-019 · 2026-09-17 · Evidence strength, project definition, candidate tiers and populations

**Decided.** (a) Skill evidence per candidate is graded *mentioned* (bio) < *used* (repository language/topics/description) < *demonstrated* (README of a documented data project, ≥ 1,000 chars) < *project-demonstrated* (same, project not flagged educational); *professional experience* is declared not observable on GitHub. (b) A **project** is an owned, non-fork data repository with a README ≥ 300 chars, or ≥ 1 star, or a description; repositories ≠ projects. (c) Candidate **tiers**: T1 bio declares a data role (the only rows with a role family), T2 repo-evidenced (≥ 2 data repos, or ≥ 1 documented project, or ≥ 3 stars on a data repo), T3 one weak data repo, T0 none. (d) Populations: P_all (Austrian-located accounts), P_data (T1 ∪ T2), P_T1. Supply shares name their population and n on every row. (e) Language: only the language candidates *write* in (bio/README de/en) is measured; CEFR-type proficiency is declared not observable.

**Why.** The brief requires the distinction between keyword presence and demonstrated capability, and forbids inferring proficiency or education without evidence.

## D-020 · 2026-09-17 · Layer 3 join rules: shares side by side, quadrants by medians, no composite score

**Decided.** Demand and supply are joined on role family, normalized title, Layer 1 skill, capability group, state, seniority label, education level/field, certification and language presentation. Each row reports demand count/n/share, supply count/n/share with a Wilson interval, the difference in percentage points, the ratio (relative representation), project-evidence share and, where meaningful, candidate density (candidates per open posting). Quadrant labels use the medians of the joined set as thresholds and are stated in the table. Capability demand shares are computed exactly from the private posting file (union over member skills) and fall back to the maximum member-skill share in the public repository (method recorded in the table). No composite "competition score" is computed (brief §48).

**Why.** The two sides are different universes (advertisements vs public accounts); only rankings, orders of magnitude and explicit evidence gaps are defensible.

## D-021 · 2026-09-18 · Precision fixes after the first full Layer 2 build

**Decided.** Three rounds of tightening after private review samples (bios and repositories are personal/third-party text and stay private; only the summary precision figures are published in `SQ10`/`SQ11`):

1. **Bio → role family.** Generic ML/AI/data wording without a role noun ("machine learning", "deep learning", "NLP", "AI", "data analysis", "big data", tool names such as "Power BI"/"Tableau") no longer declares a data role; it is an *adjacent* bucket (`ai_ml_generic`, 1,038 accounts) that can only become data-signal through repository evidence. BI requires a role noun ("BI developer/analyst/consultant", "business intelligence"); "Data Analyst | SQL · Power BI" is a data analyst. Transition wording ("marketing manager turned data analyst") classifies the segment after the transition word. Manual review of 40 random bio-declared candidates: strict precision 31/40 (78 %), lenient 36/40 (90 %) — errors are organisation accounts read as people, engineering bios with ML words, finance/quant wording (`SQ10`).
2. **Repository classifier and tiers.** Bare "data", "ai", "experiment", "simulation", "dashboard", "pipeline", "postgres", "cv", "stats", "reporting", "survey", "optimisation" were removed from the data-repository lexicon (compound forms kept); themes count only when the repository name/description/topics match or ≥ 2 distinct patterns match the README; the repo-evidenced tier T2 now requires ≥ 1 documented data project *and* ≥ 2 data repositories, or a substantive project with ≥ 3 stars. Effect: T2 fell from 2,399 to 950 accounts and P_data from 3,258 to 1,818. Manual review of 40 random substantive projects: strict precision 30/40 (75 %), lenient 37/40 (92.5 %) — the lenient cases are data-adjacent tooling (SQL guides, dataset collections, exporters, visualisation components) (`SQ11`).
3. **README-derived skill evidence.** The Layer 1 skill vocabulary was written for advertisements; in README prose "cluster" (Kubernetes), "experiment" (any ML run), "risk", "quality", "prediction", "university", "master" (branch), "badge" over-fired. README evidence now uses stricter replacement patterns for 19 generic entries, requires ≥ 2 matches for 42 others (`config/supply_taxonomy.json → readme_skill_rules`), uses README-specific education patterns, drops "badge"/"credential" from certification wording, and treats **Git as true by construction** (no README/repo evidence; bio mentions only). Effect (P_data, any evidence): A/B testing 429 → 155 candidates, Segmentation/Clustering 469 → 329, Streaming 326 → 177, Master's wording 518 → 255, "certification (any)" 497 → 69.

Archetype order was changed so an ML repository with Docker/CI stays an ML project; the unmeasurable "open-source contribution" archetype was dropped. Three format patterns (pipeline, paper, GitHub Pages) lost their bare trigger words.

**Why.** The brief's quality bar (§61): no keyword-frequency inflation presented as capability. **Effect.** All C/DS/SQ tables, JSON summaries and figures regenerated; the precision figures are quoted in `docs/supply-data-quality.md` and every "any evidence" number is accompanied by the stricter "project-demonstrated" number.

## D-022 · 2026-09-18 · Collection rules are a publication/portfolio fence, not a ban on private research scraping

**Decided.** D-013 remains the 2026-09-16 record of the terms audit. Its *operational* reading is corrected. The split-publication model exists to keep scrapers, raw advertisements, URLs, contact data and per-job scores **out of the public repository** (portfolio and legal liability). It does **not** forbid the author from collecting postings privately, offline, for non-commercial research and study.

**Allowed in the private/gitignored tree** (when the owner asks; polite delays; dated folders; snapshots never merged): re-run or add posting collectors, including EURES, karriere.at, jobs.at, willhaben, LinkedIn *job listings*, StepStone, Indeed, and the Arbeitnow public API; import browser-saved HTML when a live path returns 403; score *jobs* against `config/profile.json`.

**Still forbidden:** publishing collectors or raw records; republishing listings; commercial use; a public dashboard of ads; bypassing CAPTCHA, login walls, WAF/JS challenges or paywalls; ranking or scoring *candidates* (D-020). **D-018 is unchanged:** LinkedIn *people/profiles* stay a manual, offline slot. LinkedIn *jobs* may be collected privately.

**Effect.** AGENT_CONTEXT §21, README, docs/methodology.md, docs/data-sources.md, docs/limitations.md, docs/legal-and-publication-audit.md §8 and PUBLICATION_DECISION.md are retargeted. `src/publish/export_public.py` remains the enforcement. Private hunter code lives in `src/private/` (gitignored).

## D-023 · 2026-09-18 · Absorb German AI Job Radar ideas (public tables + private hunter)

**Decided.** Ideas from https://github.com/vijayakumarharsath/german-ai-job-radar (MIT) are absorbed without cloning it as a public product. Public Layer 1 gains additive GenAI/MLOps/industrial topic skills (umbrella `Generative AI / LLM` kept), intern vs junior skill/language/family divergence (T17), dual-track named employers (T04d), topic-demand and learn-priority tables (T05f, D04b), and an Arbeitnow dated supplement collector. A gitignored hunter (`src/private/radar/`) ports StepStone (prefer `.at`), Indeed, python-jobspy (Indeed + LinkedIn jobs), saved-HTML fallback, profile scoring and a localhost-only explorer (`127.0.0.1`). New crawls are never merged into the 2026-09-16 720-core snapshot. T19 public aggregates are written only if a later scrape/Arbeitnow run yields material Austrian data-role volume; otherwise T19 records `not_collected` or `below_threshold`. Hunter run 2026-09-18: StepStone.at and Indeed.at live harvests stopped on HTTP 403; Arbeitnow still 1 Austria location / 0 core; python-jobspy LinkedIn jobs produced 325 Austria-location rows, **109 core data-role titles** (`published_aggregates`). Title-only (0 core JDs); not merged into 720.

**Why.** The radar's intern/junior split, dual-track employers, finer GenAI topics and per-job "what's missing for me" improve market intelligence and personal hunting. Publishing its scrapers or JD UI would recreate the reputational and GDPR BLOCKERs D-014 already removed from the public tree.

## D-024 · 2026-09-21 · A visual decision layer: one business question per finding, one chart per question, attached to the text

**Decided.** The analytical layers stay as they are; a **visual decision layer** is added on top of them. Twenty-six findings that bear on a decision are each restated as a **business question in the owner's own terms** (`config/profile.json`), answered by **one chart chosen for the relationship**, and **attached to the passage it answers** in `docs/market-guide.md`, `CAREER_DECISION_MAP.md`, `CAREER_SUPPLY_DEMAND_MAP.md`, `docs/supply-findings.md`, `docs/seasonality.md`, `docs/career-map.md`, `docs/decision-framework.md` and `docs/project-evidence-map.md`. `docs/visual-decision-board.md` collects all of them.

**Method.** Chart selection follows the GSD-DSX vocabulary (https://github.com/RafaelBraga-Kribitz/GSD-DSX, `references/chart-selection.md` and `references/chart-catalog.md`): the *relationship* is named first (comparison, trend, part-to-whole, distribution, correlation, deviation, ranking, flow, spatial, composition-over-time, uncertainty) and only then an admissible *mark* is taken from the catalogue. Both are recorded per figure in `outputs/figures/FIGURE-MANIFEST.yaml`. The DSX house style (`src/viz/styles/dsx-urban.mplstyle`, WCAG-AA palette, vendored Lato under SIL OFL 1.1) and the `finalise_figure` / `save_deterministic` helper are vendored into `src/viz/`; SVG output is byte-reproducible and sealed with SHA-256.

**Rules the layer holds itself to.** Takeaway titles, never chart names. Zero baseline on every length-encoded mark; a non-zero axis is allowed only on position-encoded marks and is declared in the figure's own note. No dual axes, no pie beyond five slices, no 3D, no rainbow ramp for a continuous value, no red/green as the sole distinction. An interval wherever an estimate is shown (Wilson intervals from the tables). n, units, source and caveat on every figure, because a chart that is screenshotted out of this repository has to defend itself alone. Capabilities that GitHub cannot observe (Power BI, Excel, SAP, soft skills) are drawn with a distinct mark so their low position reads as blindness, not absence. Families below 30 postings are drawn but labelled too small to rank and never drive a headline number (`docs/limitations.md`).

**Anti-drift.** Every answer sentence is **computed from the named table at render time**, so no figure caption can carry a number the table no longer supports; the question → answer → chart → table contract is written to `outputs/visual_questions.json`; `src/analysis/embed_figures.py` re-writes the embedded blocks in place (HTML-comment delimited) and **fails loudly on an unresolved anchor**; `tests/test_visual_layer.py` checks the seals, the anchors, the cited tables and the absence of refused marks.

**Why.** The project was legible to an auditor and to an agent, and slow for a human: the findings were correct, traceable and almost entirely textual. A decision document is read before a decision, not during an audit. **Effect.** `src/viz/` and the BQ figure generators are added to the public export (`src/publish/export_public.py`), together with `CAREER_SUPPLY_DEMAND_MAP.md`, which the README listed as public but the exporter did not copy. No table, number, taxonomy or conclusion was changed by this decision.

## D-025 · 2026-09-21 · Question-coverage audit: close the answerable gaps, register the rest as open

**Decided.** The two briefs that created this project were re-read as a question inventory and contrasted, question by question, with what the project can answer (`docs/question-coverage-audit.md`). Where a question was answerable from data already held, it was answered and attached to the text it belongs to; where it was not, it was registered in `docs/open-questions.md` with the missing evidence, a concrete closing path and the class of barrier. Nineteen figures were added (BQ27-BQ45); no table, number, taxonomy or conclusion was deleted or changed.

**Added, answerable from existing tables.** Evidence quality: the denominator funnel from 12,429 rows to the 720/719 study set (BQ27), title-classification precision per family before and after D-012 (BQ28), Styrian cell sizes against the project's own n ≥ 30 rule (BQ29), source coverage with the blocked boards named (BQ30), posting freshness by source (BQ31), what a salary figure actually is (BQ32), employer structure including the 140 anonymous rows (BQ33). Demand detail: the German level actually demanded (BQ34), and languages/tools against libraries as the separate vocabularies the first brief asked for (BQ35). Demand × supply: certifications on both sides (BQ36), geography (BQ37), education (BQ38). Candidate pool: title fragmentation (BQ39), project counts (BQ40), project topics (BQ41), repository archetypes (BQ42), positioning clusters (BQ43), transitions into data (BQ44).

**Added, requiring new estimation (D05, BQ45).** `T09d` reports the median advertised floor of ads that *mention* a skill, which is confounded by family and seniority. `src/analysis/salary_premium.py` estimates the association that survives controls: OLS on log(advertised annual minimum) with role family, seniority and state dummies, HC1 robust standard errors, numpy only (no new dependency), writing the aggregate `outputs/tables/D05_skill_salary_premium.csv` so the figure stays reproducible from a public table while the estimation needs the private per-posting file. **Result: 14 of 16 skill premiums lose their separation from zero once the controls are in.** Python's raw +8 % becomes −7 % with an interval spanning zero; only Databricks (+13 %) and Excel (−9 %) remain, and with 16 coefficients roughly one crossing by chance was expected without correction — both survive Holm and Benjamini-Hochberg adjustment (D05 `p_holm`/`p_bh`, added 2026-09-30, audit L52). The reading that changes: advertised floors are set by family and seniority label, not by the tool named in the ad — `T09d` and BQ17 must be read with BQ45 beside them.

**Registered as open (19 entries: four groups plus OQ-19, an unresolved definition; the original text said 17, corrected 2026-09-30).** Outcome questions the data structurally cannot answer (does German change hiring, are requirements negotiable, does portfolio evidence change interview rates); blocked-source questions where the evidence exists behind terms that forbid automated collection (candidate language levels, LinkedIn positioning, Kaggle, the invisible share of the market); cheap-to-close questions answerable with data already retained (taxonomy **recall** — never measured, only precision; skill-extraction recall; project quality); and structural ones (actual compensation, market change over time, the true workforce, cross-platform identity — the last deliberately not done under D-020).

**Why.** A question asked by the brief and never answered is indistinguishable, to a later reader, from a question that was answered. Writing the gaps down with their closing paths converts them from holes into a research plan, and the audit found one genuine defect in the process: the project had measured classification precision twice and recall never, leaving its only unbounded error direction undocumented.

**Effect.** 45 figures across 13 documents; `docs/question-coverage-audit.md` and `docs/open-questions.md` added; `outputs/tables/D05_skill_salary_premium.csv` and `src/analysis/salary_premium.py` added; README, AGENT_CONTEXT §26 and the digest updated (the README ranges were completed on 2026-09-30). Tests pass (count not recorded; current runs: `outputs/run_manifest.json`); the public export carries all of it.

## D-026 · 2026-09-30 · LinkedIn slot becomes channel-agnostic; Layer 1 data leaves git; three documents classified private

**Decided.** Three owner decisions of 2026-09-30, recorded together because they share one boundary (what is private, and how the private LinkedIn slot may be filled).

(a) **LinkedIn slot interface.** The Layer 2 LinkedIn slot is specified as an *acquisition-channel-agnostic* contract (`docs/linkedin-slot-interface.md`): every row carries an `acquisition_method` (`manual_ui`, `talent_insights`, `ads_audience_estimate`, `recruiter_export`, `official_api`, `member_data_export`, `licensed_vendor`, `economic_graph`, `survey_self_report`) that sets its default `source_quality` and whether individual-level rows are allowed. `src/acquisition/ingest_linkedin_manual.py` rejects any method matching `FORBIDDEN_METHODS` (scrape, crawler, browser automation, headless/selenium/puppeteer/playwright, unofficial API, guest endpoint, jobspy, proxy rotation). The manual cockpit `src/private/linkedin_coder/` (localhost, git-ignored) only helps the owner type what they read; it performs **no automated access to the member site**. The slot stays a private "dark" layer; automated collection of LinkedIn *members* remains prohibited. D-018 is narrowed, not reversed: "manual" becomes "any permitted channel, never member-site automation". LinkedIn *jobs* stay under D-022 and never enter this slot.

(b) **Layer 1 data untracked.** Layer 1 raw scrapes, processed postings and `data/external/` are removed from git (commit 826b6b9; `.gitignore`). The files stay on disk. Eurostat raw data stays tracked because it is published.

(c) **Private classification.** `docs/linkedin-slot-interface.md`, `config/profile.json` and `library_strategy/` are private: excluded from the public export. The public tree receives a neutral example profile instead of `config/profile.json`.

**Why.** (a) The channel, not "manual vs automated", decides whether data is permitted, and licensed exports (Talent Insights, Recruiter, vendors) are the only realistic way to close OQ-02 at scale. (b) Tracked scrapes contradicted the private/public split and exceeded GitHub's file-size limit (audit H17/M62/L130). (c) These three documents describe the owner's personal strategy or a private collection method.

**Effect.** AGENT_CONTEXT §22/§25, README, `docs/open-questions.md` (OQ-02, OQ-13) reference the slot contract. The slot has not been filled or ingested yet; no table changed. The exclusions are enforced in `src/publish/export_public.py` (`PRIVATE_NEVER`, `SUBSTITUTE_FILES` → `config/profile.example.json`).

## D-027 · 2026-09-30 · OQ-19 closed: canonical Styrian denominators

**Decided.** The canonical Styrian populations are the **location-resolved** counts: **56** bio-declared (P_T1; `C05a`, `DS01`, `DS05`), **248** data-signal (P_data; `C05a`, `DS05`), **2,033** Austrian-located accounts (P_all; `C05a`). The frame-B counts (**52** / **247** / **2,023**; `C05c`, `DS13`) are the complete-Styria subset and are quoted only with that label. Postings: **54** Styria / **343** Vienna by primary state (`T03a`, shares 7.5 % / 48 %) vs **58** / **350** by the location flag incl. multi-site ads (`market_summary.json`). A count and its share are always quoted on the same basis, and the basis is named.

**Why.** 56 is what the joined DS tables already contain, so no table is recomputed; the four extra accounts are Styria-located accounts found by the bio-keyword frame. Frame B stays the right population for "complete-frame" statements (base rates, activity, hireable flag).

**Effect.** Prose corrected in README, AGENT_CONTEXT §23/§24, `CAREER_SUPPLY_DEMAND_MAP.md` §1/§10, `docs/supply-findings.md` §3, `docs/supply-research-audit.md`, `docs/open-questions.md` (OQ-19 closed). Densities: 56/54 = 1.04 declared and 248/54 = 4.59 data-signal per posting (`DS05`); over the 58 flag-basis postings 0.97 and 4.28 (`DS13` as regenerated 2026-09-30, location-resolved counts). No table's counts were recomputed except `DS13`, whose densities moved from the frame-B/flag basis to location-resolved counts (0.9 → 0.97, 4.26 → 4.28); `C05a`/`C05c`/`DS13` carry the new labels; the figure answer sentences were regenerated by `run_all.py all` on 2026-09-30.

## D-028 · 2026-09-30 · Layer 2 analysis frozen; retention/redaction pass (legal audit §10.5)

**Decided.** The Layer 2 analysis is frozen as of 2026-09-30 and the redaction/retention step recommended in `docs/legal-and-publication-audit.md` §10.5 is run with `src/pipeline/redact_supply_raw.py`.

**Result.** Run 2026-09-30 21:08 after the full regeneration (`run_all.py all`, 400 tests passing) and a pre-redaction test export whose GitHub-login leak check used the clear-text logins: `redact_supply_raw.py --source github --date 2026-09-17 --confirm`. Raw folder `data/raw/github_supply/2026-09-17/`: logins and repository names pseudonymised (`sha1("<kind>:<value>")[:16]`, the `candidate_id` scheme) in profiles (9,464 rows), users_search (14,104), repos (126,013), readmes (11,798; README text and file-tree paths nulled), social (4,625; URLs reduced to the provider), repos_done (9,096) and query_log (48,129); bio/blog/company/location/twitter nulled. Processed: `supply_candidates` (9,457 rows, 31,815 personal values nulled) and `supply_projects` (9,347 rows; name/description nulled; 34,924 rare README headings dropped, 663 kept) in jsonl and parquet with a `redacted` flag; bios/names/descriptions blanked in the four review and precision-label samples (ids and labels kept); `supply_quality_frameB_nonstyria_locations.csv` deleted; `supply_skill_evidence.parquet` kept. Marker `REDACTED.json` (status complete). This is pseudonymisation, not anonymisation: the files stay private. A full rebuild of this folder is refused by `build_supply.py`; `supply_analysis.py` and `supply_quality.py` refuse redacted rows. At the owner's request, the pre-redaction state was copied outside the project to `Dev/PRIVATE-BACKUP_austria-data-job-market-intelligence_GitHub-candidate-data_BEFORE-redaction_2026-09-30/` (182 MB, SHA-256 list, README); it holds personal data and is to be deleted at the next Layer 2 re-collection or by 2027-09-30 at the latest.

**Why.** §10.5 made limited retention of README texts and bios the condition under which private processing without Art 14 notices stays proportionate.

**Effect.** The frozen outputs of 2026-09-30 are the Layer 2 reference; any later Layer 2 analysis starts from a new dated collection (D-016), not from a rebuild of the redacted files.

## D-029 · 2026-09-30 · Public export refreshed with Layers 2/3

**Decided.** The public repository is refreshed with the Layer 2/3 and visual-layer outputs and pushed on 2026-09-30, applying the D-026 (c) exclusions.

**Result.** Exported and pushed 2026-09-30 to `github.com/RafaelBraga-Kribitz/austria-data-job-market-intelligence`; the public commit hash is recorded in the release checklist of `PUBLICATION_DECISION.md` §7 in the private repository (it cannot be known inside the tree it names).

**Why.** Layer 2/3 publication was decided (PUBLICATION_DECISION §8, D-024) but the public tree was two layers behind.

**Effect.** The public tree matches this repository's aggregates as of 2026-09-30; `config/profile.json`, `library_strategy/` and `docs/linkedin-slot-interface.md` are not in it.

## D-030 · 2026-09-30 · OQ-14 closed: Kaggle is not collected

**Decided.** OQ-14 is closed as contractual and structural. Kaggle's Terms of Use (22 June 2025) prohibit crawling or scraping by manual or automated means, with no research exception; the official API and Meta Kaggle (Apache 2.0) are permitted but carry no user location, so no permitted route yields Austrian aggregates. Kaggle is not collected; the 9 % link-type share on GitHub profiles (C15) is the only Kaggle measure.

**Why.** `docs/kaggle-terms-review.md` (terms read 2026-09-30; a documented reading, not legal advice).

**Effect.** `docs/open-questions.md` OQ-14 closed. A global Meta Kaggle benchmark, if ever wanted, needs its own entry.
