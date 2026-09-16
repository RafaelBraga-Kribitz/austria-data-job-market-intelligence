# Research Landscape: Austrian Data-Job Market Intelligence

Survey date: 2026-09-16. Purpose: catalogue existing data, tools and reports before we build our own analysis, so that we reuse what is solved and only collect what nobody else provides.

Verification legend used below:
- **Fetched** = page loaded and content read in this survey.
- **Search-only** = existence confirmed via search results / snippets, page itself not fetched (blocked, timeout, 404 on guessed URL).
- **Not found** = could not locate or verify.

Numbers are quoted only where the page (or an explicit search snippet) showed them; the source is given each time.

---

## 1. Austrian official labour-market data

### 1.1 AMS Open Government Data on data.gv.at
- URL: https://www.data.gv.at/datasets?publisher=AMS+%C3%96sterreich&locale=de (link taken from the AMS Arbeitsmarktdaten page, fetched); announcement of "11 neue offene Datensätze zu Arbeitslosigkeit und offenen Stellen" (2023-07-24): https://www.data.gv.at/2023/07/24/daten-fuer-alle-ams-veroeffentlicht-11-neue-offene-datensaetze-zu-arbeitslosigkeit-und-offenen-stellen/
- Status: **Search-only**. Both data.gv.at fetch attempts returned empty bodies (JS-rendered catalogue). The AMS page itself (fetched, updated 2026-09-03) confirms that AMS publishes "Arbeitsmarktdaten ... in maschinenlesbarem Format ... regelmäßig aktualisiert" via data.gv.at, with monthly reports (latest August 2026).
- What we could not confirm: the exact dataset names, whether the vacancy series is by AMS-Beruf x Bundesland at monthly grain, and whether the resource format is CSV. This needs a manual browser check of the catalogue (5 minutes) — high priority.
- Related official products (fetched): AMS Arbeitsmarktdaten portal https://www.ams.at/arbeitsmarktdaten-und-medien/arbeitsmarkt-daten-und-arbeitsmarkt-forschung/arbeitsmarktdaten (monthly standard tables incl. offene Stellen); Arbeitsmarktdatenbank https://arbeitsmarktdatenbank.at (micro-data, fee-based, research institutions).
- Licence: data.gv.at datasets are normally CC BY 4.0 (not verified for these specific datasets).
- Coverage: Austria, by Bundesland (Steiermark included in AMS standard tables).
- Suitability: **High** (if the Beruf x Bundesland vacancy CSV exists as announced) — it is the only administrative vacancy series with occupation and regional grain. Caveat: AMS-registered vacancies under-represent data roles, which are mostly advertised privately.

### 1.2 AMS JobBarometer (jobbarometer.ams.at)
- URL: https://jobbarometer.ams.at/ ; example page fetched: Data Scientist (m/w) in Steiermark https://jobbarometer.ams.at/berufe/295/1268/AT22
- Content (fetched): per occupation x Bundesland: number of online job ads ("Inserate aus dem Internet"), share of all ads, 3-year trend forecast. For Data Scientist / Steiermark it showed **300 Inserate (2025)**, trend "positiv" (Prognose 2026-2028), and an "Als CSV speichern" export option.
- Data basis: AMS-scraped online job ads (the AMS's own OJA pipeline), yearly figures.
- Freshness: 2025 data with 2026-2028 forecast.
- Coverage: Austria, all Bundesländer (NUTS-2 codes in URL, AT22 = Steiermark), AMS occupation IDs (1268 = Data Scientist).
- Reusable: **as-is** as an external benchmark for our own posting counts (both per Beruf and per Bundesland). Licence not stated on the page; treat as citable public information, not bulk-redistributable.
- Suitability: **High** — the single best official yardstick for "how many data-scientist ads per year in Styria".

### 1.3 AMS Qualifikations-Barometer
- URL: https://www.ams.at/qualifikationsbarometer (redirects to the BIS qualibarometer); occupation pages such as Data-Warehouse-ManagerIn https://bis.ams.or.at/qualibarometer/beruf.php?id=602 and Kompetenz "Datenbankentwicklungs- und -betreuungskenntnisse" https://www.ams.at/bis/qualibarometer/kompetenz.php?alphabetisch=1&filter=M&id=129
- Status: **Search-only** for individual pages; the system exists and has occupation-level trend text and competence-trend pages (e.g. Big Data, KI, Data Mining, SQL listed for Data Scientists per search snippet).
- Format: HTML prose, no structured download. Update cycle: roughly annual per Berufsfeld.
- Suitability: **Medium** — good for qualitative "trend statements" to cite; not usable as quantitative data.

### 1.4 AMS Berufslexikon / Karrierekompass
- URL (fetched): https://www.berufslexikon.at/berufe/3852-DataScientist/ (mirror: https://www.karrierekompass.at/berufe/3852-DataScientist/ ; BIS: https://bis.ams.or.at/bis/beruf/1268-Data%20Scientist%20%28mw%29)
- Content: occupation profile, skills, and an **Einstiegsgehalt of EUR 2,800 to 4,350 gross per month** (basis: Kollektivvertrag minimums, Stand 2025), plus a "very good" Berufsaussichten statement.
- Suitability: **Medium** — reusable as the official entry-salary anchor and skill list; no regional grain.

### 1.5 AMS Gehaltskompass
- URL (fetched): https://www.gehaltskompass.at/
- Content: entry salaries for "fast 1.800 Berufe", basis "Mindestgehälter in Kollektivverträgen (Stand: 2025)", updated roughly every three years. Searchable by Beruf, sector, A-Z; no API or bulk download.
- The guessed occupation URL https://www.gehaltskompass.at/berufe/3852-DataScientist/ returned 404, so the exact Data-Scientist page URL is unverified; the Berufslexikon page (1.4) shows the same KV-based figure (EUR 2,800-4,350 / month) and links to Gehaltskompass.
- No structured data exposure. Suitability: **Medium** (single anchor figure; monthly gross, 14x for annual); not a market-salary source.

### 1.6 Statistik Austria - Offene-Stellen-Erhebung (Job Vacancy Survey)
- URL (fetched): https://www.statistik.at/statistiken/arbeitsmarkt/arbeitskraeftenachfrage/offene-stellen ; methodology: https://www.statistik.at/ueber-uns/erhebungen/unternehmen/offene-stellen-erhebung ; latest release PDF: https://www.statistik.at/fileadmin/announcement/2026/07/20260805OffeneStellen2026Q2.pdf
- Content: quarterly, ~6,500 firms sampled. Q2 2026: **123,400 offene Stellen (-7.3% vs Q1 2026), vacancy rate 2.9%**. Breakdowns: economic sector (ÖNACE 2025 groups); annual averages by occupation, education, hours, AMS registration; plus a file "AMS-registrierte offene Stellen nach Beruf und Bundesland".
- Format: **ODS files only** on that page (no CSV / OGD noted). Licence: Statistik Austria standard (CC BY 4.0 for OGD; ODS tables citable).
- Suitability: **Medium** — macro context and a Bundesland x Beruf table for AMS-registered vacancies; occupation classes are coarse, data roles not separately identifiable.

### 1.7 Statistik Austria - Verdienststrukturerhebung (Structure of Earnings Survey) 2022
- URL: https://www.statistik.at/statistiken/bevoelkerung-und-soziales/einkommen-und-soziale-lage/verdienststruktur ; publication PDF https://www.statistik.at/fileadmin/publications/Verdienststrukturerhebung_2022_barr.pdf ; OGD dataset (fetched): https://data.statistik.gv.at/web/meta.jsp?dataset=OGD_veste402_Veste402_1
- Content: 4-yearly survey, firms with 10+ employees, ISCO-08 occupations (ÖISCO-08) in the publication. The fetched OGD dataset "SES 2022 gross hourly earnings by enterprise characteristics" has dimensions gender x NUTS-1 region x ÖNACE x firm size (no ISCO in that file); CSV, **CC BY 4.0**, last updated 2024-11-19. Sibling OGD files by ISCO were not confirmed in this survey.
- Suitability: **Medium** — ISCO 2-digit earnings (e.g. 25 ICT professionals) as an official salary benchmark; too coarse for "Data Analyst" and only NUTS-1 in OGD form.

### 1.8 Statistik Austria open data portal (data.statistik.gv.at)
- URL: https://data.statistik.gv.at/ (catalogue https://data.statistik.gv.at/web/catalog.jsp returned "Request Rejected" to the search crawler; meta pages work). ÖISCO-08 code list as OGD: https://www.data.gv.at/datasets/2bf2a6eb-69b8-39b6-917d-42fdc1dfebf3?locale=de
- Format: CSV + JSON metadata, CC BY 4.0. Suitability: **Medium** (reference code lists, earnings, labour-force aggregates).

### 1.9 WKO Fachkräfte-Radar - Stellenandrang
- URL (fetched): https://content.wko.at/statistik/fachkraefte/themen/stellenandrang.html ; overview https://www.wko.at/fachkraefte/fachkraefteradar
- Content: unemployed per AMS vacancy by Beruf and Bundesland, source "AMDB des AMS und BMASGK", periods shown: August 2026 and annual average 2025. Interactive; no explicit CSV download seen.
- Suitability: **Medium** — ready-made Stellenandrang for Steiermark; based on AMS-registered stock, so IT/data occupations are under-covered.

---

## 2. EU sources

### 2.1 Cedefop Skills-OVATE / Skills in online job advertisements
- URLs (fetched): https://www.cedefop.europa.eu/en/tools/skills-online-vacancies and https://www.cedefop.europa.eu/en/tools/skills-intelligence/skills-online-job-advertisements ; expansion news (fetched, 2019-09-12): https://www.cedefop.europa.eu/en/news/cedefops-skills-online-vacancy-analysis-tool-expanding
- Austria coverage: **Yes** — Austria was explicitly added in the 2019 expansion; the tool now covers 32 European countries, OJAs collected since July 2018.
- Breakdowns: country and **NUTS-2 region** (so Steiermark is a selectable region), ISCO-08 occupation (down to 4-digit in the dashboard), ESCO skills, NACE sector. Last 4 quarters in Skills-OVATE (updated quarterly); yearly averages on the Skills Intelligence platform.
- Download: **No direct CSV/API.** Dashboards are Tableau Public (Tableau's own "download data/crosstab" may work per view but is not an official bulk export). The page states detailed data access is "organised through Eurostat's Microdata access portal" (research application required).
- Licence: Cedefop copyright; dashboard figures citable with attribution.
- Suitability: **High for benchmarking, Low for reuse as data** — best external check for our skill-frequency and occupation-share results for AT / AT22, but cannot be bulk-loaded.

### 2.2 Eurostat Job Vacancy Statistics
- URL: https://ec.europa.eu/eurostat/databrowser/view/jvs_q_nace2/default/table?lang=en (quarterly by NACE, from 2001); Austrian quality report https://ec.europa.eu/eurostat/cache/metadata/EN/jvs_esqrs_at.htm ; mirrored on DBnomics https://db.nomics.world/Eurostat/jvs_q_nace2
- Content (search snippets): Austria vacancy rate **3.2% in Q3 2025**, **2.9% in Q2 2026**. National level and NACE section only; no occupation, no region.
- Format: Eurostat API / TSV / CSV, free reuse (Eurostat licence, attribution). Suitability: **Low-Medium** (macro context line only).

### 2.3 ESCO
- URL: https://esco.ec.europa.eu/en/use-esco/download ; copyright notice https://esco.ec.europa.eu/en/copyright-notice-esco-skills-competences ; current version v1.2.
- Format: CSV, RDF/TTL, ODS, XML, JSON-LD in 28 languages incl. German; licence **CC BY 4.0** (EU Europa standard). Status: Search-only (download page requires accepting terms in a form; not fetched).
- Suitability: **High** — the skills/occupation taxonomy we should map extracted skills onto (German labels available); consistent with Cedefop.

---

## 3. Job-posting datasets (Kaggle / Hugging Face / GitHub / Zenodo)

- Searches for Austrian / DACH / "Stellenanzeigen" posting datasets returned only generic international sets: e.g. Kaggle "Job Postings in Europe" https://www.kaggle.com/datasets/thedevastator/job-postings-in-europe (page fetched but body not rendered; country coverage unverified), Hugging Face `lukebarousse/data_jobs` https://huggingface.co/datasets/lukebarousse/data_jobs (global data-role postings from a Google-Jobs scrape, English), `xanderios/linkedin-job-postings`, Kaggle `moyukhbiswas/job-postings-dataset`.
- **No Austria-specific or DACH-specific posting-level dataset for data roles was found** on Kaggle, Hugging Face, GitHub or Zenodo in this survey. The well-known "data science jobs" datasets are US/India-centric or global scrapes with, at best, a handful of Austrian rows.
- Suitability: **None** for Austrian analysis; `lukebarousse/data_jobs` is at most useful as a schema/label reference (title normalisation categories, skill lists).

---

## 4. Job APIs

| API | Auth | Austria coverage | Notes | Suitability |
|---|---|---|---|---|
| Arbeitnow Job Board API, `https://www.arbeitnow.com/api/job-board-api` (fetched blog: https://www.arbeitnow.com/blog/job-board-api) | **No key** | Europe/DACH-focused (Germany-heavy); location field per job, no documented country filter | JSON, sourced from ATS feeds (Greenhouse, Personio, etc.); no stated licence/terms, rate limits undocumented | Medium (small extra supply of ATS-sourced tech jobs; filter location client-side) |
| Adzuna API, https://developer.adzuna.com/ | Free App ID + App Key (registration) | **Yes** ("at" country code; Austria listed among supported countries) | Aggregator incl. salary estimates; terms restrict redistribution | Medium (needs account; cross-check volumes and salary_min/max) |
| Jooble API, `POST https://jooble.org/api/{key}` | Key (free request) | Aggregator, Austria searchable | Terms limit storage/redistribution | Low-Medium |
| EURES public API (AMS mirror), karriere.at, LinkedIn guest, willhaben, jobs.at | already in use by us | — | — | (already covered) |

---

## 5. Open-source tools

- **python-jobspy** (https://github.com/speedyapply/JobSpy, PyPI `python-jobspy`, MIT, 4.3k stars, 353 commits, actively maintained): scrapes LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter, Bayt, Naukri, BDJobs. **Austria is a supported `country_indeed` value** and Glassdoor also lists Austria; LinkedIn via `location`. Indeed is bot-blocked for us, so JobSpy's Indeed path may fail from our IP; its LinkedIn scraper duplicates what we already do. Suitability: Medium (adaptable, e.g. Glassdoor/Google Jobs paths).
- **Nesta ojd_daps_skills** (https://github.com/nestauk/ojd_daps_skills, docs https://nestauk.github.io/ojd_daps_skills/, `pip install ojd-daps-skills`): spaCy NER for skills/experience/benefits + mapping to ESCO or Lightcast. **English-only**; licence not shown on docs page (repo is MIT per GitHub - verify). Suitability: Medium-adaptable (mapping-to-ESCO logic reusable; NER must be swapped for a German/multilingual model).
- **SkillSpan (jjzha)** (https://github.com/kris927b/SkillSpan, NAACL 2022; models/collections at https://huggingface.co/jjzha, demo https://huggingface.co/spaces/jjzha/skill_extraction_demo): 14.5K sentences / 12.5K annotated hard+soft skill spans, English. jjzha also published multilingual/ESCO-linked models (e.g. `jjzha/esco-xlm-roberta-large`) — worth testing on German text. Suitability: Medium.
- **SkillNER** (PyPI `skillNer`): rule/NER extractor keyed to EMSI/Lightcast skills, English. Not verified in this survey (no fetch); Low-Medium.
- **Nesta Open Jobs Observatory** (UK OJA pipeline; nestauk/ojd_daps_language_models https://github.com/nestauk/ojd_daps_language_models): UK-only data, but the architecture (dedup, title normalisation, skill mapping) is a reusable design template. Suitability: Low as data, Medium as design reference.
- Job-title normalisation: no dedicated open German tool found; ESCO occupation labels (DE) + embedding similarity (sentence-transformers) is the practical route.

---

## 6. Austrian / DACH salary reports for data roles

| Source | URL | Status | What it reports | Figures seen | Suitability |
|---|---|---|---|---|---|
| AMS Berufslexikon / Gehaltskompass (KV-based) | https://www.berufslexikon.at/berufe/3852-DataScientist/ | Fetched | Entry salary, KV minimums 2025, monthly gross | Data Scientist: **EUR 2,800-4,350 / month** | Medium (official floor, not market) |
| Hays Austria job profile | https://www.hays.at/jobprofile/data-scientist | Fetched | Annual gross, no method/date stated | Data Scientist AT: **~EUR 54,800 avg; junior ~50,000; senior 10+ yrs from 70,000** | Low-Medium (undated, no sample) |
| StepStone Gehaltsreport 2025 (AT) | https://www.stepstone.at/Ueber-StepStone/pressebereich/fur-mehr-gehaltstransparenz-stepstone-veroffentlicht-gehaltsreport-2025/ | Fetch timed out | Report exists (2025); per-role AT figures not verified. Note: stepstone.at/gehalt/... role pages now **301-redirect to stepstone.de** (German figures) — do not cite those as Austrian | Search snippet only: "Data Analyst Wien 50,400 EUR (43,800-60,400)" — unverified | Medium if PDF obtained |
| karriere.at Gehalt pages | https://www.karriere.at/gehalt/analyst | Search-only (/gehalt/data-analyst = 404) | Monthly gross range by Bundesland/experience | Analyst*in AT: **EUR 2,634-4,389 / month** (snippet) | Medium (Bundesland split exists on page) |
| Glassdoor AT | https://www.glassdoor.at/Geh%C3%A4lter/data-analyst-gehalt-SRCH_KO0,12.htm | 403 blocked | Self-reported | snippet: Data Analyst AT ~61,750 / yr; Vienna DS ~62,000 (52,000-71,350) — unverified | Low (self-reported, blocked) |
| Indeed AT salaries | https://at.indeed.com/career/data-scientist/salaries | Search-only | Ad-derived | snippet: DS avg 40,290 / yr — implausibly low, likely mixed part-time; do not use | Low |
| Robert Half Gehaltsübersicht 2026 | https://www.roberthalf.com/de/de/ueber-uns/presse/gehaltsuebersicht-2026-erfahrung-und-fachkenntnisse-zahlen-sich-aus (DE); CH pages exist | Search-only | DACH bands, Germany- and Switzerland-specific pages found; **no Austria-specific page located** | none for AT | Low for AT |
| devjobs.at "Welche IT-Berufe 2026 in Österreich am besten zahlen" | https://devjobs.at/artikel/welche-it-berufe-2026-in-oesterreich-am-besten-zahlen | 429 blocked | Secondary article citing StepStone/Robert Half | none seen | Low |
| kununu Gehaltscheck, Michael Page AT, Statista | not fetched | Not verified | — | — | Unknown / Low |

Note on units: Austrian sources mix monthly gross (x14) and annual gross; StepStone DE pages are annual x12-13. Always record unit + basis alongside any figure.

---

## 7. Research on the Austrian / DACH data & AI labour market

- **AMS Standing Committee on New Skills** (Cedefop instrument page, search-only): https://www.cedefop.europa.eu/en/tools/matching-skills/all-instruments/ams-standing-committee-new-skills — since 2017, AMS + social partners publish skill-needs findings per sector (AMS Forschungsnetzwerk e-library: https://forschungsnetzwerk.ams.at/). Suitability: Medium (qualitative, citable).
- **AMS Spezialthema "Stellenmarkt"** reports (PDF, search-only): e.g. https://www.ams.at/content/dam/download/arbeitsmarktdaten/%C3%B6sterreich/berichte-auswertungen/001_spezialthema_1121.pdf and 001_spezialthema_0823.pdf — AMS analyses of the vacancy market. Medium.
- **Cedefop/Eurydice skills forecasting for Austria**: https://national-policies.eacea.ec.europa.eu/youthwiki/chapters/austria/33-skills-forecasting (overview of AMS Qualifikations-Barometer, WIFO/IHS forecasting roles). Low-Medium.
- **WKO Fachkräfte-Radar** (see 1.9) and WKO Fachkräftebedarf page https://www.wko.at/service/zahlen-daten-fakten/Fachkraeftebedarf.html. Medium.
- **WIFO / IHS, Industriellenvereinigung, SFG, Green Tech Valley, Silicon Alps**: Silicon Alps cluster partner page confirms WKO Steiermark membership (https://www.silicon-alps.at/partner/wirtschaftskammer-steiermark/); **no specific Styrian data/AI-labour study was found** in this survey. Not found / Low.

---

## 8. Austrian job-platform market figures

- karriere.at (Wikipedia, fetched): "etwa 20.000 Jobangebote" (undated); Jan 2018 traffic 3.76 M visits / 1.31 M unique clients; founded 2004 Linz; 240 employees (Apr 2025); **hokify 100% owned since 2024**; **jobs.at is a karriere.at spin-off**; minority stakes eRecruiter, Gronda; JobCloud AG holds a minority stake in karriere.at.
- hrweb.at Jobbörsen-Ranking 2015 (search-only): karriere.at + willhaben.at "über 41% Marktanteil" — 2015, obsolete.
- StepStone AT, willhaben Jobs, Indeed AT, LinkedIn, devjobs.at: **no current published posting-volume or market-share figures found** in this survey. Practical implication: our own daily counts per platform (already collected) will be the only fresh volume evidence; treat platform overlap (karriere.at/jobs.at/hokify same group) when deduplicating.

---

## Recommendations for this project

**(a) Reuse directly**
- AMS JobBarometer per Beruf x Bundesland (CSV export) as the official annual OJA benchmark (e.g. Data Scientist Steiermark 300 ads in 2025).
- ESCO v1.2 CSV (DE + EN) as skills/occupation taxonomy, CC BY 4.0.
- Statistik Austria Offene-Stellen-Erhebung ODS + Eurostat jvs_q_nace2 for macro vacancy context.
- AMS Berufslexikon/Gehaltskompass KV entry-salary anchor (EUR 2,800-4,350 / month for Data Scientist, 2025) as the official floor.
- Cedefop Skills-OVATE dashboards (AT / AT22, ISCO 2511/2519/2521, ESCO skills) as a sanity check of our skill and occupation shares — read-only.

**(b) Adapt**
- Nesta ojd_daps_skills mapping logic (skill span -> ESCO) with a multilingual NER (test jjzha ESCO-linked XLM-R models on German ads).
- python-jobspy for any additional board we decide to add (Glassdoor/Google Jobs), MIT licence; not for Indeed from our network.
- Arbeitnow API as a low-cost supplemental feed (filter `location` for Austrian cities); Adzuna "at" if we accept account creation, mainly for salary_min/max on ads.
- Verdienststrukturerhebung 2022 ISCO tables as the official earnings benchmark for ICT professionals (need the ISCO table from the publication PDF, not the fetched OGD file).

**(c) Ignore**
- Kaggle/HF "data science jobs" datasets (no Austrian coverage).
- StepStone AT role salary pages (they redirect to German data), Indeed AT salary page (implausible aggregate), 2015 platform-share figures.
- Robert Half / Michael Page unless an Austria-specific edition is obtained.

**(d) Gaps our own collection must fill**
- Posting-level Austrian data-role dataset with title, skills, seniority, region (Graz/Styria), salary-on-ad, platform, first-seen/last-seen — nothing public provides this.
- Monthly (not yearly) volume series per platform and per Bundesland; platform overlap/deduplication rates.
- Skill co-occurrence and seniority mix specific to Styria; Cedefop gives only NUTS-2 aggregates without download.
- Advertised salary ranges in Austrian ads (mandatory KV-minimum statements) as a market-salary signal, since the public salary reports are either KV floors or unverifiable self-reports.
- Open follow-ups: (1) manually inspect data.gv.at AMS datasets for a Beruf x Bundesland vacancy CSV; (2) obtain the StepStone Gehaltsreport 2025 AT PDF; (3) confirm Gehaltskompass page URL for "Datenanalytiker/in"; (4) test Tableau crosstab export from Skills-OVATE for AT22.

---

## Sources

- https://www.ams.at/arbeitsmarktdaten-und-medien/arbeitsmarkt-daten-und-arbeitsmarkt-forschung/arbeitsmarktdaten (fetched)
- https://www.data.gv.at/datasets?publisher=AMS+%C3%96sterreich&locale=de (linked from AMS; not rendered)
- https://www.data.gv.at/2023/07/24/daten-fuer-alle-ams-veroeffentlicht-11-neue-offene-datensaetze-zu-arbeitslosigkeit-und-offenen-stellen/ (search-only)
- https://jobbarometer.ams.at/berufe/295/1268/AT22 (fetched)
- https://www.berufslexikon.at/berufe/3852-DataScientist/ (fetched)
- https://www.gehaltskompass.at/ (fetched)
- https://www.ams.at/qualifikationsbarometer ; https://bis.ams.or.at/qualibarometer/beruf.php?id=602 (search-only)
- https://www.statistik.at/statistiken/arbeitsmarkt/arbeitskraeftenachfrage/offene-stellen (fetched)
- https://www.statistik.at/fileadmin/announcement/2026/07/20260805OffeneStellen2026Q2.pdf (search-only)
- https://www.statistik.at/statistiken/bevoelkerung-und-soziales/einkommen-und-soziale-lage/verdienststruktur (search-only)
- https://data.statistik.gv.at/web/meta.jsp?dataset=OGD_veste402_Veste402_1 (fetched)
- https://www.data.gv.at/datasets/2bf2a6eb-69b8-39b6-917d-42fdc1dfebf3?locale=de (search-only)
- https://content.wko.at/statistik/fachkraefte/themen/stellenandrang.html (fetched)
- https://www.cedefop.europa.eu/en/tools/skills-online-vacancies (fetched)
- https://www.cedefop.europa.eu/en/tools/skills-intelligence/skills-online-job-advertisements (fetched)
- https://www.cedefop.europa.eu/en/news/cedefops-skills-online-vacancy-analysis-tool-expanding (fetched)
- https://ec.europa.eu/eurostat/databrowser/view/jvs_q_nace2/default/table?lang=en ; https://ec.europa.eu/eurostat/cache/metadata/EN/jvs_esqrs_at.htm (search-only)
- https://esco.ec.europa.eu/en/use-esco/download ; https://esco.ec.europa.eu/en/copyright-notice-esco-skills-competences (search-only)
- https://www.kaggle.com/datasets/thedevastator/job-postings-in-europe ; https://huggingface.co/datasets/lukebarousse/data_jobs (search-only)
- https://www.arbeitnow.com/blog/job-board-api (fetched)
- https://developer.adzuna.com/ ; https://publicapis.io/jooble-api (search-only)
- https://github.com/speedyapply/JobSpy (fetched)
- https://nestauk.github.io/ojd_daps_skills/ (fetched); https://github.com/nestauk/ojd_daps_skills
- https://github.com/kris927b/SkillSpan ; https://huggingface.co/jjzha (search-only)
- https://www.hays.at/jobprofile/data-scientist (fetched)
- https://www.stepstone.at/Ueber-StepStone/pressebereich/fur-mehr-gehaltstransparenz-stepstone-veroffentlicht-gehaltsreport-2025/ (timeout)
- https://www.stepstone.at/gehalt/Data-Analyst/city/Wien.html (301 -> stepstone.de)
- https://www.karriere.at/gehalt/analyst (search-only)
- https://www.glassdoor.at/Geh%C3%A4lter/data-analyst-gehalt-SRCH_KO0,12.htm (403)
- https://devjobs.at/artikel/welche-it-berufe-2026-in-oesterreich-am-besten-zahlen (429)
- https://www.roberthalf.com/de/de/ueber-uns/presse/gehaltsuebersicht-2026-erfahrung-und-fachkenntnisse-zahlen-sich-aus (search-only)
- https://www.cedefop.europa.eu/en/tools/matching-skills/all-instruments/ams-standing-committee-new-skills (search-only)
- https://national-policies.eacea.ec.europa.eu/youthwiki/chapters/austria/33-skills-forecasting (search-only)
- https://de.wikipedia.org/wiki/Karriere.at (fetched)
- https://www.hrweb.at/2015/02/jobboersen-oesterreich-ranking/ (search-only)
