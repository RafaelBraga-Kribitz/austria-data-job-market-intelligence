# Data-source inventory

Status as tested on 2026-09-16 from a plain HTTP client (no login). "Blocked" means an explicit technical barrier that this project does not bypass.

**Terms of use (audit of 2026-09-16; operational reading D-022).** Every posting source below except JobBarometer/Eurostat/Arbeitnow's documented API restricts automated extraction in its terms: EURES "Find a job" terms (no screen scraping/automated extraction; API reserved to EURES partners), karriere.at Nutzungsbedingungen 2.8.3 and jobs.at AGB 2.3.3 ("Sämtliche Formen der automatisierten Auswertung unserer Plattform sind verboten"), LinkedIn User Agreement 8.2 and robots.txt (`Disallow: /jobs-guest/`), willhaben robots.txt (`Disallow: /jobs/suche?*`) and AGB Pkt 8. Quotes: docs/legal-and-publication-audit.md §2 and §6. The public repository does not distribute posting collectors or source records. Private, non-commercial research collection remains in-scope (D-022); new dated folders, never merged with 2026-09-16; no CAPTCHA/WAF bypass.

## Tier 1 · primary / official

| Source | Used | Access | Content | Vintage | Caveats |
|---|---|---|---|---|---|
| **EURES portal** (europa.eu/eures) · AMS "PES Austria" feed | Yes (postings) | Public JSON API of the portal (`/eures/api/jv-searchengine/public/jv-search/search`, `/jv/id/{id}`) | Full AMS job ads for Austria (plus a small share from private boards flagged by connection point), NUTS-3 location, ESCO occupation codes assigned by AMS, schedule/offering codes, employer name (often anonymised as "siehe Beschreibung"), creation/modification dates | live; collected 2026-09-16 | Title search is token-based; AMS ads skew towards German-language, mid-market and public-sector employers; employer anonymised in ~most rows; ESCO mapping sparse |
| **AMS JobBarometer** (jobbarometer.ams.at) | Yes (aggregate) | server-rendered HTML per occupation × Bundesland | Yearly online-ad counts 2020–2025 per AMS occupation class, 3-year trend, share, similar occupations, competencies (Austria-wide) | 2025 data, trend 2026–2028 | Occupation classes are coarse (e.g. "Data Scientist (m/w)" bundles analyst/scientist titles); "<20" censored; methodology = AMS web-ad crawl |
| AMS "alle jobs" API (jobs.ams.at) | **No – blocked** | `/public/emps/api/search` returns 401 without an OAuth bearer token from the AMS auth service | – | – | Same postings reached via EURES |
| AMS Gehaltskompass / Berufslexikon | Reference only | HTML | Collective-agreement entry salary ranges per occupation | Stand 2025 | Not posting evidence; cited in docs/salary-context.md |
| Statistik Austria Offene-Stellen-Erhebung; Eurostat JVS; WKO Fachkräfteradar; Cedefop Skills-OVATE | Reference only | see docs/research-landscape.md | Vacancy rates, AMS-registered vacancies by occupation group, EU online-ad statistics (NUTS-2) | quarterly / 2025 | Coarse occupation classes; Skills-OVATE has no download |
| **ESCO** (ec.europa.eu/esco/api) | Yes (taxonomy lookup) | public API / CSV (CC BY 4.0) | occupation & skill taxonomy | v1.2 | used to read AMS-assigned occupation codes |
| **Eurostat Job Vacancy Statistics** `jvs_q_nace2` (Statistik Austria Offene-Stellen-Erhebung) | Yes (seasonality) | documented public REST API, no key, no restriction on automated access; reusable with attribution (Decision 2011/833/EU) | quarterly open-vacancy counts for Austria by NACE aggregate, non-seasonally-adjusted, 2009-Q1…2025-Q4 | 2025-Q4, fetched 2026-09-16 | Stock of vacancies under active recruitment, not new postings; **no occupation detail and no NUTS-2**, so neither data roles nor Styria are separable; the ICT-containing aggregate G-N also contains tourism and retail. Public-reproducible collectors also include JobBarometer, GitHub supply, Eurostat supply, Arbeitnow API code (raw private). |

## Tier 2 · job platforms

| Platform | Used | Access | Per-posting fields | Caveats |
|---|---|---|---|---|
| **karriere.at** | Yes | listing JSON (`/jobs?keywords&locations&page`, header X-Requested-With) + detail page JSON-LD | title, company, company size, locations, salary string & structured baseSalary, home-office flag, employment type, date, full description | Largest Austrian board; strong SME/industry coverage; hokify is a karriere.at subsidiary (its ads partly appear here) |
| **LinkedIn** (job postings only) | Yes | logged-out guest endpoints (list + jobPosting) with `collect_linkedin.py` on 2026-09-16 (private collector); a second, dated collection of job listings on 2026-09-18 by the private python-jobspy hunter (same `jobs-guest` search endpoint; T19 only, never merged). **LinkedIn members/people are never collected by automation** — that is a separate, private Layer 2 slot (Tier 4) whose `FORBIDDEN_METHODS` (guest endpoint, jobspy, …) apply to member data, not to job postings | title, company, location, date, full description, seniority level, employment type, function, industry, applicants | Skews to multinationals, English postings, senior roles; 1,000-result cap per query; posting dates are relative for older ads; terms: robots.txt `Disallow: /jobs-guest/`, User Agreement 8.2 (legal audit §2, §11.2) |
| **willhaben Jobs** | Yes | `__NEXT_DATA__` JSON in search/detail pages | title, company, locations, salary (monthly gross), employment modes, dates, description | Mixed classifieds/board; many cross-posts from karriere.at/hokify-type feeds |
| **jobs.at** | Yes | HTML cards + detail HTML | title, company, meta, description | Smaller board; substantial overlap with karriere.at |
| StepStone.at | Not in the 2026-09-16 published snapshot (live 403 from the collection network) | Gitignored hunter: JSON-LD + search cards; saved-HTML if 403; never published | title, company, location, JD via JobPosting JSON-LD | Hunter 2026-09-18: live harvest stopped on HTTP 403; T19 volume did not come from StepStone |
| Indeed.at | Not in the 2026-09-16 published snapshot (Cloudflare 403 from the collection network) | Gitignored hunter: jobspy / direct / saved-HTML; skip live on challenge | title, company, location, description when unblocked | Hunter 2026-09-18: direct Indeed.at HTTP 403; jobspy Indeed contributed 1 non-core row |
| Arbeitnow Job Board API | Supplement only (not merged into 720) | Documented public API, no key (`collect_arbeitnow.py`); raw gitignored; API terms not yet fetched (legal audit §11.1) | ATS-sourced title, company, location, HTML description, tags | Probe 2026-09-18: 1,500 listings, 1 Austria location, 0 core data roles. T19 `published_aggregates` n=109 is python-jobspy LinkedIn jobs, not Arbeitnow |
| hokify.at | **No – AWS WAF JS challenge** | – | – | karriere.at subsidiary |
| Glassdoor | No | login wall | – | – |
| devjobs.at | Deferred | listing = streamed React Router payload; robots.txt disallows search/API paths | – | ~365 tech ads Austria-wide; publishes "Marktdaten" (advertised salaries per search) |
| metajob.at | No | aggregator | – | duplicates |
| derStandard Jobs, university career portals, company career pages | Not collected | – | – | Company career pages of Styrian employers are a documented follow-up (see limitations) |


<!-- BQ30_source_coverage:start (figure generated by src/analysis/make_visual_layer.py - do not edit by hand) -->
**Q. How much of the Austrian market can this dataset simply not see?**

LinkedIn and EURES/AMS carry most of the 720 core postings, and the corporate white-collar segment is missing entirely: StepStone.at and Indeed.at returned HTTP 403, and company career pages, university portals and hokify were never collected - so the corporate share of Austrian data demand is an unmeasured gap, not a measured absence.

[![BQ30_source_coverage](../outputs/figures/BQ30_source_coverage.png)](../outputs/figures/BQ30_source_coverage.png)

<sub>**Figure BQ30** · comparison across categories shown as `horizontal_bar` (bivariate-simple) · built from `T01_source_coverage.csv`, `T01b_source_overlap_in_scope.csv` · units: rows / postings. **Read with:** Only 20 % of core postings were seen on more than one source, so the boards are largely disjoint universes; a missing board is a missing slice, not a redundant one.</sub>
<!-- BQ30_source_coverage:end -->

## Tier 3 · research / secondary

See `docs/research-landscape.md` for the verified inventory (salary reports, AMS/WIFO/WKO studies, datasets, tools) and `docs/salary-context.md` for the salary references actually cited.

## Retention

Raw responses are stored verbatim (JSON records; HTML for LinkedIn, jobs.at and JobBarometer) under `data/raw/<source>/<collection-date>/`, with `query_log.jsonl` per source — **in the private repository only**, and since 2026-09-30 untracked in its git history as well (D-026; only the published Eurostat folders stay tracked).

**Collection runs and resumption.** Collection folders are named by the collection day in Austrian local time (Europe/Vienna); `collected_at` envelopes stay UTC timestamps. Every collector accepts `--date YYYY-MM-DD` and then continues the existing folder of that day, so a run interrupted before midnight can be finished on a later day instead of opening a new, empty folder. The query log marks the last logged page of every sweep with `complete: true`, plus `truncated: true` when the collector's page cap rather than the source ended the sweep; a resumed run skips sweeps already marked complete, and `truncated` flags where coverage is capped. The GitHub supply collector writes transient failures (403/429 throttling, 5xx, network errors) to `retry.jsonl` in its dated folder instead of marking the unit done; the next run of the same stage fetches them again.

**EURES sweeps.** `collect_eures.py` runs title searches only (the former `mode` parameter was removed; the mode is fixed and logged for provenance). The full-text ("EVERYWHERE") sweep is a separate script, `collect_eures_styria_text.py`, over three NUTS-2 regions — at22 Styria, at13 Vienna and at31 Upper Austria (not all of Austria) — stored as `data/raw/eures_textsearch/<date>/` (source `eures_textsearch`), used only by `src/analysis/adjacent_demand.py` and never merged into the core set.

**Private hunter layout (D-022/D-023; not in the public repository).** The git-ignored hunter in `src/private/radar/` has no collector under `src/acquisition/`. It writes `data/raw/radar/<date>/jobspy.jsonl` (python-jobspy results) and `arbeitnow.jsonl` (the Arbeitnow rows it upserted), and keeps its working set in `src/private/radar/jobs.db`, which is what `src/analysis/supplement_radar.py` reads for T19 (without the database the script leaves the T19 tables untouched and says so). `data/raw/arbeitnow/<date>/` (`listings.jsonl`, `query_log.jsonl`) is the separate output of the public `collect_arbeitnow.py`; the two Arbeitnow copies of 2026-09-18 overlap (1 Austrian row in the hunter vs. the full 1,500-listing feed in `data/raw/arbeitnow/`), and T19 does not double-count them (the hunter database takes precedence, the Arbeitnow raw folder is the fallback). Nothing is deleted downstream; out-of-scope rows remain in the processed files with `role_family = out_of_scope`. The public repository contains no source records, no advertisement text and no contact data (PUBLICATION_DECISION.md).


## Tier 4 · candidate-supply sources (Layer 2, added 2026-09-17; DECISION_LOG D-017/D-018)

| Source | Used | Access | Content | Vintage | Quality | Caveats |
|---|---|---|---|---|---|---|
| **GitHub REST API** (`api.github.com`) | Yes (profile-level supply) | documented API, owner token via `gh`, rate limits respected, descriptive User-Agent; AUP §7 research clause, open-access publication | public profiles (bio, location, company, website, hireable, counters) and owner repositories; README text and top-level trees for data repositories; social-account link types; **no names, no e-mails** | 2026-09-17/18 | B | public-code population only; raw records private (personal information) |
| **Eurostat** `educ_uoe_grad02`, `lfsa_egai2d`, `isoc_sks_itspt` | Yes (official supply context) | open API | graduates by ISCED level × detailed field (AT, 2005–2024); employment by ISCO-08 2-digit (AT, 2011–2025); ICT specialists | fetched 2026-09-17 | A | no regional grain |
| **Stack Overflow Developer Survey 2025** | Yes (self-reported lens) | ODbL 1.0; official URL 404 on 2026-09-17, identical zip from a public GitHub mirror (sha256 in manifest) | 410 Austrian respondents; ≈ 29 in data roles | 2025 | B | self-selected; tiny data-role n; extract private, aggregates public |
| LinkedIn (people search, profiles) | **No automated collection** (User Agreement 8.2, robots.txt) | manual offline slot: `src/acquisition/ingest_linkedin_manual.py`, protocol in docs/supply-methodology.md §7 | search-result counts, hand-coded public profiles under pseudonymous ids | — | B/C when filled | never exported |
| Kaggle | No | API needs account credentials (not created); scraping prohibited; Meta Kaggle has no location | — | — | — | Kaggle presence measured only as link type on GitHub profiles/READMEs |
| Personal portfolio sites, Medium, Tableau Public, Hugging Face | Link presence only | from GitHub website fields / social accounts / README links | domain type counts | 2026-09-17 | C | content not fetched |
| Job-board candidate databases, Meetup, search-engine-indexed profiles | No | employer-only access / not machine-readable / not reproducible | — | — | — | documented in docs/supply-research-audit.md |
