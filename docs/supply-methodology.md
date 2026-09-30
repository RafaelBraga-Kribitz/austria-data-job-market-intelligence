# Supply methodology (Layer 2: observed candidate supply)

**Version:** Supply v1 · collection 2026-09-17 · taxonomy `supply-v1 (2026-09-17)` (`config/supply_taxonomy.json`). Decisions: `DECISION_LOG.md` D-016 – D-020. Schema: `schemas/supply_schema.md`. Numbers: `docs/supply-findings.md`, tables `outputs/tables/C*`, `O*`, `SQ*`.

## 1. Research question and unit of observation

*Who is publicly observable as a candidate for the data roles measured in Layer 1, what do they demonstrate, where are they, and how does that compare with advertised demand?* Layer 2 does **not** measure the Austrian labour supply. It measures **public-profile density**: accounts on a public platform whose free-text location points to Austria and whose bio or repositories carry a data signal. The unit is the account (GitHub), the respondent (Stack Overflow survey) or the graduate/employee count (Eurostat). None is a person in the census sense; the same person may hold several accounts, and most data professionals hold none.

## 2. Sources, access and quality tags

| Source | Access | What it yields | Quality | Public? |
|---|---|---|---|---|
| **GitHub REST API v3** (`/search/users`, `/users/{login}`, `/users/{login}/repos`, `/repos/{o}/{r}/readme`, `/repos/{o}/{r}/git/trees/{branch}`, `/users/{login}/social_accounts`) | documented API, owner token via `gh`, rate limits respected (search 30/min, core 5,000/h), descriptive User-Agent, names and e-mails never requested | profile bio, free-text location, company field, website, hireable flag, counters, account dates; owner repositories with description/topics/language/stars/forks/dates/license/homepage; README text and top-level tree for data repositories; social-account link types | **B** (direct public profile via structured API; free-text fields are self-reported) | code yes; raw records **no** (personal information); aggregates yes |
| **Eurostat** `educ_uoe_grad02`, `lfsa_egai2d`, `isoc_sks_itspt` | open, documented API; reuse permitted with attribution | yearly graduates by ISCED level × detailed ISCED-F field; employment by ISCO-08 2-digit; ICT specialists | **A** | code, raw and aggregates yes |
| **Stack Overflow Developer Survey 2025** | ODbL 1.0; official URL 404 on 2026-09-17, identical zip (sha256 recorded) from a public GitHub mirror | self-reported role, stack, education, experience, work model, industry for 410 Austrian respondents (≈ 28 in data roles) | **B** (secondary copy of a self-selected survey) | code and aggregates yes; extract private (ODbL share-alike, size) |
| LinkedIn | **not collected by automation** (D-013, D-018) | manual slot only (§7) | B/C when filled | never |
| Kaggle, portfolio sites, search-engine-indexed profiles, job-board candidate databases | not collected (D-017) | link *types* on GitHub profiles/READMEs counted instead | — | — |

`SOURCE_QUALITY` A = direct structured public source · B = direct public profile/page · C = indexed/secondary public result · D = secondary aggregation · E = inference. Every table names its source and quality; aggregates never mix GitHub with survey or Eurostat rows in one denominator.

## 3. Sampling frames (GitHub)

GitHub user search is token-based on the location field and capped at 1,000 results per query, so the population is assembled from three frames (`config/supply_taxonomy.json → github_search`):

* **Frame A — bio-signal.** 39 data keywords (English and German, e.g. `data scientist`, `machine learning`, `"BI analyst"`, `Datenanalyse`, `kaggle`, `Power BI`) searched `in:bio` against 25 Austrian location tokens (country, Bundesländer, main cities). This frame finds accounts that *describe themselves* with data words wherever they are in Austria.
* **Frame B — complete Styrian population.** Every account with ≥ 1 public repository whose location matches one of 34 Styrian tokens (Graz, Styria/Steiermark, district towns, Graz commuting municipalities), sliced by repository count when a token exceeds 1,000 results. This frame makes **Styria the only region whose GitHub population is enumerated**, so repo-evidenced (T2) candidates without data words in the bio are captured there.
* **Frame C — base-rate sample.** For Vienna, Linz, Salzburg, Innsbruck, Klagenfurt, Dornbirn, Wels, Villach, St. Pölten and the country tokens, accounts with ≥ 1 repository sliced into five account-creation windows and truncated to 120 per slice (ordered by join date). This is a systematic, not random, sample used to estimate what share of general Austrian accounts carry a data signal and to calibrate Frame A's recall.

Consequences: supply *shares across states* are not comparable (Vienna is a sample, Styria is complete); *within-state* shares (e.g. share of Styrian data-signal candidates who are students) are; Vienna counts are lower bounds. Organisations and bot accounts are dropped; an account found by several queries is one row (`n_search_hits` records the multiplicity).

## 4. Normalisation (`src/pipeline/build_supply.py`)

* **Geography.** Free-text location → Bundesland/city with `config/geo.json` (state aliases, Vienna/Graz-area cities) plus a supplementary city list for the other Bundesländer; `unspecified (Austria)` when only the country is named; flags for foreign places also named and multi-location strings. An account is *Austrian-located* when a state is found, or the country is named and no foreign place is.
* **Role family / title.** Bio-specific overrides first (self-descriptions such as "ML engineer", "data engineering", "business intelligence", "growth analytics"), then the Layer 1 title cleaner and role rules (`config/role_taxonomy.json`). When the bio states a transition ("marketing manager turned data analyst", "…, now …"), the segment after the transition word is classified first. Bios without a match have no family (they can still be T2).
* **Seniority.** Explicit bio wording only: student · junior (incl. "aspiring", "career changer", "open to work") · unlabelled · senior · lead/head (head of, lead, principal, staff, CTO/CDO, founder). Never inferred from age or account age.
* **Transition signals.** Explicit wording (former, turned, career change, background in, …) and prior-domain groups named in the same bio (marketing, business, finance, engineering, science, economics, statistics, software, social science). A named domain is a weak signal; explicit wording is the strong one.
* **Education / certification.** Level, field and Austrian institution wording in bios and project READMEs; candidate-side certificate phrasings (e.g. Google Data Analytics capstone repositories, exam codes) plus the Layer 1 certification patterns. Absence of wording is reported as "no education wording observable", never as "no degree".
* **Skills.** The Layer 1 controlled vocabulary (`config/skills_taxonomy.json`, ~260 bilingual patterns) on bio text, on repository name + description + topics, on primary language (mapped, e.g. Jupyter Notebook → Jupyter, HCL → Terraform), and on README text of data repositories. Evidence strength per (candidate, skill): mentioned · used · demonstrated · project-demonstrated (D-019).
* **Data repositories.** Owned, non-fork repositories whose primary language is Jupyter Notebook or R, or whose name/description/topics match the data lexicon (≈ 130 keywords, 90 topics) and no exclusion (dotfiles, metadata, personal websites, games…). Educational/tutorial flag from course, homework, thesis, certificate, `100days`, playground wording.
* **Projects, formats, topics, README features, archetypes.** Definitions in `schemas/supply_schema.md`; taxonomies in `config/supply_taxonomy.json` (`project_topics`, `project_formats`, `readme_features`, `repo_archetypes`). README sections are detected from markdown headings; content features (images, badges, metrics words, business words, limitations words, reproduce commands, German text) from the whole text.
* **Cross-platform links.** Link *types* (LinkedIn, Kaggle, personal site, GitHub Pages, Medium/blog, Tableau Public, Hugging Face, Scholar/ORCID, X, XING, Streamlit/HF Spaces) from the website field, GitHub social accounts and README links. URLs never leave the private files.
* **Deduplication.** GitHub accounts are unique by numeric id. Cross-platform matching is *not* attempted (no other automated source); the manual LinkedIn slot uses observer-assigned pseudo ids that cannot be linked. Duplicate rates are reported in `SQ02`.

## 5. Populations and denominators

| Population | Definition | Used for |
|---|---|---|
| P_all | Austrian-located GitHub accounts across all frames | frame coverage, tier shares, base rates |
| P_data | P_all ∩ (T1 ∪ T2) — bio-declared or repo-evidenced | technologies, capabilities, projects, education, certifications, links, geography counts |
| P_T1 | P_all ∩ T1 — bio declares a data role | families, titles, seniority, transitions, family × anything |
| projects / documented / substantive | data repositories of P_data meeting the project definition / README ≥ 1k / and not educational | formats, topics, README patterns, project capabilities |
| Styrian frame B | accounts with ≥ 1 repo matching a Styrian token | Styria/Graz density, the only complete regional frame |

LinkedIn search counts (when recorded) are *result indices*, not unique people, and are never added to GitHub counts. Survey respondents and Eurostat counts are separate tables (`O*`).

## 6. What is and is not observable (per dimension of the brief)

| Dimension | Observable on GitHub | Not observable / proxy |
|---|---|---|
| Titles | bio self-description (raw phrase, normalized title, family) | job titles as employers would list them (LinkedIn slot) |
| Seniority | explicit bio words; account age as tenure-on-platform | years of experience, career history → **title-to-experience mismatch is not measurable** |
| Geography | free-text location; hireable flag | willingness to relocate, remote preference (hireable flag is the only signal) |
| Language | language written in bio/README (de/en) | **CEFR proficiency — not observable**; English bio ≠ no German |
| Technologies | bio, repo metadata, primary language, README | proprietary tools rarely appear in code (Power BI/Tableau/SAP under-observed by construction) |
| Capabilities | project themes and README content | professional experience |
| Education | wording in bios/READMEs; institutions named | degrees actually held |
| Certifications | wording, capstone repos | certificates not written down |
| Projects / formats / READMEs / GitHub activity | fully observable for public repos | private repositories, deleted work |
| LinkedIn positioning | LinkedIn link share only | everything else → manual slot |
| Industry | company field wording (not analysed by name) | — |

## 7. Manual LinkedIn protocol (dark slot; owner-run, offline)

Permitted because a member may search and read LinkedIn manually; any script or browser automation against the LinkedIn member-facing site is prohibited (D-013, D-018). Records stay in `data/raw/linkedin_supply/<date>/` (git-ignored) and feed `build_supply.py` as `source = linkedin_manual` (a stable legacy label meaning "LinkedIn slot", whatever the channel).

The slot is **channel-agnostic**: the same two tables also take rows exported from LinkedIn's own licensed products (Talent Insights, Recruiter, Campaign Manager / Marketing API), the member's own data export, licensed third-party datasets and self-report surveys, each tagged in `acquisition_method`, which defaults `source_quality`. Those channels may be scripted within their own licences; automated collection from the member site stays out of scope and is rejected by the ingest. Full contract, value domains, per-channel coverage, validation rules and the sampling design are in the private interface document `docs/linkedin-slot-interface.md` (not part of the public export).

1. **Search counts** (`search_counts.csv`): for each cell of the grid *title keyword × location filter × language/other filter*, record the "About N results" figure of a People search, the timestamp, whether LinkedIn capped the figure, and `source_quality` C (the default of `manual_ui`). Grid: the 17 Layer 1 normalized titles (English and German) × {Austria, Wien, Graz, Steiermark, Linz, Salzburg, Innsbruck} × {no filter, profile language English, profile language German}. A free People search has no Open to work filter (Open to volunteering is not a substitute); the Open to work badge is coded on the profile row when it is visible. Counts are indices of visibility, not people; the same profile appears under several titles.
2. **Coded profiles** (`profiles_manual.csv`): for a *systematic* sample (e.g. every 5th result of each title × Graz/Wien search, first 5 pages), record only fields visible without connecting, under a pseudo id you assign (never a name or URL): headline, current title, location, seniority label, explicit years of experience, education level/field, certifications, languages **with the level the profile states**, listed skills, featured/projects sections, links present (GitHub/Kaggle/portfolio), open-to-work badge, transition wording, prior domain, industry, consultant/freelancer signal; `source_quality` C, the same default of `manual_ui` as for the counts (observer-transcribed from a personalised, relevance-ranked search; §2 scale). The current title is recorded without the employer. No inference from photos, names or nationality.
3. Start a collection folder with `python src/acquisition/ingest_linkedin_manual.py --templates --date <date>`; after filling it, validate with `... --date <date> --check` (writes nothing), then ingest with `... --date <date>` (without `--date` the latest dated folder is used; two empty tables are refused, and replacing another collection date needs `--replace`). Then run `python src/pipeline/build_supply.py` (or `--linkedin-only` once the GitHub collection is redacted) and the analysis scripts; the LinkedIn rows appear in the family, title, seniority, education and skill C-tables with `source = linkedin_manual` (the GitHub-evidence tables C14–C24 exclude them), only ≥ 5-record tallies reach `outputs/supply_linkedin.json`, and the records are excluded from the public export by path.
4. After the analysis is frozen, `python src/pipeline/redact_supply_raw.py --source linkedin --date <date>` (dry run, then `--confirm`) replaces headlines and transition wording with `[redacted]`, reduces notes to the sampling tokens and clears the cockpit draft (legal audit §10.5).

## 8. Reproducibility and versioning

`python src/acquisition/collect_github_supply.py all --date <date>` (resumable; ~5–7 h at the rate limits) → `python src/acquisition/collect_eurostat_supply.py` → `python src/acquisition/ingest_stackoverflow_survey.py <zip>` → `python src/pipeline/build_supply.py` → `python src/analysis/official_supply.py && python src/analysis/supply_analysis.py && python src/analysis/project_analysis.py && python src/analysis/demand_supply.py && python src/analysis/supply_quality.py && python src/analysis/supply_figures.py && python src/analysis/export_supply_json.py` → `python -m pytest tests -q`. Every raw record carries `collected_at`; every table the population and n; `supply_build_manifest.json` the taxonomy version. Future collections go into a new dated folder and are never merged with an older snapshot (brief §66); comparisons across dates are made table-to-table.

## 9. Known limitations specific to this layer

Public-profile sample, not a census (§1); GitHub over-represents engineers, researchers and students and under-represents BI/analyst profiles whose work lives in Power BI, Excel or SAP; location strings are stale for some accounts; bios are marketing text; educational repositories inflate project counts unless the substantive filter is used; READMEs are third-party text read for features only; proficiency, experience and hiring outcomes are invisible. Quantified in `docs/supply-data-quality.md`; audited in `docs/supply-research-audit.md`.
