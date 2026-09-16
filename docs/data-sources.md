# Data-source inventory

Status as tested on 2026-09-16 from a plain HTTP client (no login). "Blocked" means an explicit technical barrier that this project does not bypass.

**Terms of use (audit of 2026-09-16).** Every posting source below restricts automated extraction in its terms: EURES "Find a job" terms (no screen scraping/automated extraction; API reserved to EURES partners), karriere.at Nutzungsbedingungen 2.8.3 and jobs.at AGB 2.3.3 ("Sämtliche Formen der automatisierten Auswertung unserer Plattform sind verboten"), LinkedIn User Agreement 8.2 and robots.txt (`Disallow: /jobs-guest/`), willhaben robots.txt (`Disallow: /jobs/suche?*`) and AGB Pkt 8. The AMS JobBarometer carries no found restriction. Quotes, URLs and consequences: docs/legal-and-publication-audit.md §2 and §6; DECISION_LOG D-013. The collection of 2026-09-16 is a one-off private research dataset; the public repository does not distribute the posting collectors or any source record.

## Tier 1 · primary / official

| Source | Used | Access | Content | Vintage | Caveats |
|---|---|---|---|---|---|
| **EURES portal** (europa.eu/eures) · AMS "PES Austria" feed | Yes (postings) | Public JSON API of the portal (`/eures/api/jv-searchengine/public/jv-search/search`, `/jv/id/{id}`) | Full AMS job ads for Austria (plus a small share from private boards flagged by connection point), NUTS-3 location, ESCO occupation codes assigned by AMS, schedule/offering codes, employer name (often anonymised as "siehe Beschreibung"), creation/modification dates | live; collected 2026-09-16 | Title search is token-based; AMS ads skew towards German-language, mid-market and public-sector employers; employer anonymised in ~most rows; ESCO mapping sparse |
| **AMS JobBarometer** (jobbarometer.ams.at) | Yes (aggregate) | server-rendered HTML per occupation × Bundesland | Yearly online-ad counts 2020–2025 per AMS occupation class, 3-year trend, share, similar occupations, competencies (Austria-wide) | 2025 data, trend 2026–2028 | Occupation classes are coarse (e.g. "Data Scientist (m/w)" bundles analyst/scientist titles); "<20" censored; methodology = AMS web-ad crawl |
| AMS "alle jobs" API (jobs.ams.at) | **No – blocked** | `/public/emps/api/search` returns 401 without an OAuth bearer token from the AMS auth service | – | – | Same postings reached via EURES |
| AMS Gehaltskompass / Berufslexikon | Reference only | HTML | Collective-agreement entry salary ranges per occupation | Stand 2025 | Not posting evidence; cited in docs/salary-context.md |
| Statistik Austria Offene-Stellen-Erhebung; Eurostat JVS; WKO Fachkräfteradar; Cedefop Skills-OVATE | Reference only | see docs/research-landscape.md | Vacancy rates, AMS-registered vacancies by occupation group, EU online-ad statistics (NUTS-2) | quarterly / 2025 | Coarse occupation classes; Skills-OVATE has no download |
| **ESCO** (ec.europa.eu/esco/api) | Yes (taxonomy lookup) | public API / CSV (CC BY 4.0) | occupation & skill taxonomy | v1.2 | used to read AMS-assigned occupation codes |
| **Eurostat Job Vacancy Statistics** `jvs_q_nace2` (Statistik Austria Offene-Stellen-Erhebung) | Yes (seasonality) | documented public REST API, no key, no restriction on automated access; reusable with attribution (Decision 2011/833/EU) | quarterly open-vacancy counts for Austria by NACE aggregate, non-seasonally-adjusted, 2009-Q1…2025-Q4 | 2025-Q4, fetched 2026-09-16 | Stock of vacancies under active recruitment, not new postings; **no occupation detail and no NUTS-2**, so neither data roles nor Styria are separable; the ICT-containing aggregate G-N also contains tourism and retail. The only collector in this project that anyone may re-run (docs/seasonality.md) |

## Tier 2 · job platforms

| Platform | Used | Access | Per-posting fields | Caveats |
|---|---|---|---|---|
| **karriere.at** | Yes | listing JSON (`/jobs?keywords&locations&page`, header X-Requested-With) + detail page JSON-LD | title, company, company size, locations, salary string & structured baseSalary, home-office flag, employment type, date, full description | Largest Austrian board; strong SME/industry coverage; hokify is a karriere.at subsidiary (its ads partly appear here) |
| **LinkedIn** | Yes | logged-out guest endpoints (list + jobPosting) | title, company, location, date, full description, seniority level, employment type, function, industry, applicants | Skews to multinationals, English postings, senior roles; 1,000-result cap per query; posting dates are relative for older ads |
| **willhaben Jobs** | Yes | `__NEXT_DATA__` JSON in search/detail pages | title, company, locations, salary (monthly gross), employment modes, dates, description | Mixed classifieds/board; many cross-posts from karriere.at/hokify-type feeds |
| **jobs.at** | Yes | HTML cards + detail HTML | title, company, meta, description | Smaller board; substantial overlap with karriere.at |
| StepStone.at | **No – 403** | bot protection | – | Major white-collar board; its exclusion is the largest coverage gap (see limitations) |
| Indeed.at | **No – 403 (Cloudflare)** | – | – | Aggregator; would mostly duplicate |
| hokify.at | **No – AWS WAF JS challenge** | – | – | karriere.at subsidiary |
| Glassdoor | No | login wall | – | – |
| devjobs.at | Deferred | listing = streamed React Router payload; robots.txt disallows search/API paths | – | ~365 tech ads Austria-wide; publishes "Marktdaten" (advertised salaries per search) |
| metajob.at | No | aggregator | – | duplicates |
| derStandard Jobs, university career portals, company career pages | Not collected | – | – | Company career pages of Styrian employers are a documented follow-up (see limitations) |

## Tier 3 · research / secondary

See `docs/research-landscape.md` for the verified inventory (salary reports, AMS/WIFO/WKO studies, datasets, tools) and `docs/salary-context.md` for the salary references actually cited.

## Retention

Raw responses are stored verbatim (JSON records; HTML for LinkedIn, jobs.at and JobBarometer) under `data/raw/<source>/<collection-date>/`, with `query_log.jsonl` per source — **in the private repository only**. Nothing is deleted downstream; out-of-scope rows remain in the processed files with `role_family = out_of_scope`. The public repository contains no source records, no advertisement text and no contact data (PUBLICATION_DECISION.md).
