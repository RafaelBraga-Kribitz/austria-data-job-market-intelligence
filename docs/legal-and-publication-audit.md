# Legal, liability and publication audit

**Status:** audit performed 2026-09-16 on the repository state after the completeness audit (DECISION_LOG D-012/D-013). **This is a documented legal-risk and publication-readiness analysis by the repository author with AI assistance. It is not legal advice.** Every clause quoted below was fetched from the named URL on 2026-09-16; items that could not be verified are marked as such. The decision this audit feeds is recorded in `PUBLICATION_DECISION.md`. Addenda: §10 (Layer 2/3, 2026-09-17) and §11 (private hunter, Arbeitnow, radar-derived tables and the 2026-09-30 export changes). Counts in §0–§9 describe the repository as it was on 2026-09-16 and are not updated in place.

## 0. Summary

| Question | Finding |
|---|---|
| Does the repository contain personal data? | **Yes.** The raw and processed posting files contain named contact persons, e-mail addresses (≈2,400 distinct) and phone numbers from job advertisements, plus willhaben `contact` objects with first/last names. Nothing about the author's own credentials or accounts. |
| Does it contain secrets? | **No.** No API keys, cookies, session tokens or credentials of the author. Two benign false positives (a LinkedIn login-form CSRF field in stored HTML; `jsessionid` inside application URLs quoted in ad texts). |
| Does it contain third-party text? | **Yes.** ≈12,400 verbatim advertisement texts (HTML and plain), raw LinkedIn/jobs.at HTML pages and 590 AMS JobBarometer HTML pages, all under `data/raw` and `data/processed`, and in the single git commit `299045b`. |
| Can the current git history be published? | **No**, for two independent reasons: it contains the material above, and six tracked files exceed GitHub's 100 MB file limit. |
| Do the source terms permit the collection that was done? | **Not for the five posting sources.** EURES, karriere.at, jobs.at, LinkedIn and willhaben all restrict automated extraction in their terms; LinkedIn and willhaben additionally disallow the used paths in robots.txt. Only the AMS JobBarometer pages carry no found restriction. |
| Do the terms/statutes prohibit publishing *aggregated statistics*? | No fetched clause prohibits it; aggregated shares over a one-day sample are neither a substantial part of any source database nor personal data. Residual contractual/reputational risk is discussed in §6. |
| Resulting model | **Split publication**: code (excluding posting collectors), configs, methodology, decision documents, figures, aggregated tables and JSON summaries public; all source records, texts, per-posting tables with text/URLs, and the posting collectors private. |

## 1. What was inspected

* Complete file tree, `git ls-files` (251 tracked files on 2026-09-16), git history (one commit on 2026-09-16), remotes (none), `.gitignore`, ignored folders (`logs/`, `data/raw/_probe/`, `notebooks/`).
* Raw JSONL envelopes of every source (`data/raw/<source>/2026-09-16/*.jsonl`): record keys, stored HTML, hidden fields.
* Processed files, all 146 output tables, 11 JSON summaries, docs, code and configs, scanned with regular expressions for e-mail addresses, Austrian phone numbers, secret-like keywords (`api_key`, `bearer`, `cookie`, `csrf`, `jsessionid`, `token=`, `authorization`) and contact-field names (`contact*`, `firstName`, `lastName`, `recruiter*`).
* Acquisition code for headers, cookies, tokens, user-agent, throttling and the endpoints used.

### 1.1 Personal-data findings (GDPR Art 4(1))

| Location | What | Count (approx.) |
|---|---|---|
| `data/raw/eures/*/listings.jsonl`, `details.jsonl` | AMS/EURES ad texts with contact blocks: named AMS advisers and employer HR contacts, personal e-mail addresses in the first-name.last-name pattern at ams.at and company domains, phone numbers | 13,500 e-mail occurrences, 1,300–1,600 distinct addresses; 10,000+ phone patterns |
| `data/raw/eures_textsearch/*/listings.jsonl` | same, regional full-text sweep | 9,600 e-mail occurrences, 3,200 distinct |
| `data/raw/karriere/*/details.jsonl` | ad texts (JSON-LD `description`) with HR contact names/e-mails; listing cards with recruiter e-mails (e.g. agency contacts) | 2,200 occurrences, 260 distinct |
| `data/raw/linkedin/*/details.jsonl` | ad texts and full HTML; contact e-mails inside descriptions; no "hiring team" profiles (guest pages do not show them) | 2,500 occurrences, 370 distinct |
| `data/raw/willhaben/*/details.jsonl` | `contact` object with `firstName`/`lastName`/`email` of the advertiser's contact person | 1,508 records, 76 with e-mail, 55 with first name |
| `data/raw/jobsat/*/details.jsonl` | ad texts + raw HTML | 470 occurrences, 16 distinct |
| `data/processed/*.jsonl/.parquet` | all of the above carried through (`description_text`, `description_html`, `willhaben_detail`) | 2,434 distinct addresses |
| `outputs/tables/T09e_salary_observations.csv`, `Q07a`, `Q07b`, `Q09` | salary/skill snippets that include contact lines | 13 / 1 / 1 / 0 addresses |
| `outputs/tables/T16a_adjacent_titles_styria.csv`, `Q09`, `outputs/adjacent_demand.json` | per-posting source URLs / identifiers | 80–100 rows |

These are business contact data of natural persons (HR staff, AMS advisers, recruiters). They are personal data under GDPR regardless of being publicly available (EDPB ChatGPT Taskforce report, 23 May 2024, paras 15–18: public accessibility does not mean the data subject "manifestly made the data public"). They were not needed for any analysis and are stripped from every public artefact (§7).

### 1.2 Secrets and access findings

* Collectors use a fixed browser-like `User-Agent` string and `Accept-Language` header (`src/acquisition/common.py`); karriere.at requests add `X-Requested-With: XMLHttpRequest` to receive the JSON the site's own front-end uses. No cookies, logins, tokens or CAPTCHA solving anywhere. Delays 0.6–2 s per request with exponential backoff on 429/5xx; every request logged.
* The stored LinkedIn HTML contains a `loginCsrfParam` hidden-form value generated for anonymous visitors; it is not a credential of the author. `jsessionid` strings occur only inside employer application URLs quoted in ad texts.
* Nothing in the untracked `logs/` or `data/raw/_probe/` folders contains credentials (they hold run logs, probe scripts and four JobBarometer HTML pages).

## 2. Access-control audit (per source)

| Source | Mechanism used | Public page? | Guest endpoint? | Auth/CAPTCHA bypass? | Rate limits respected? | Undocumented/internal endpoint? | robots.txt for the used paths | Terms clause on automated access (fetched 2026-09-16) |
|---|---|---|---|---|---|---|---|---|
| EURES portal | `POST /eures/api/jv-searchengine/public/jv-search/search`, `GET .../jv/id/{id}` | yes (portal SPA) | yes | no | yes (0.6–0.8 s) | internal JSON API of the portal front-end | `europa.eu/robots.txt` has no directive for `/eures`; `/eures/robots.txt` 404 | "Find a job" terms shown in the portal: *"You are not permitted to use 'screen scraping' or any other automated or manual system to extract job vacancy data in order to further process or re-publish the information."* and *"Only EURES partner organisations, recognised by a EURES National Coordination Office, are allowed to extract data using our API or similar technologies."* (read in a browser session 2026-09-16; the page is a JavaScript application) |
| karriere.at | `GET /jobs?keywords&locations&page` with `X-Requested-With` (JSON), `GET /jobs/{id}` (HTML + JSON-LD) | yes | n/a | no | yes (1 s) | JSON payload of the site's own SPA | `User-agent: * / Disallow:` (everything allowed); jobs sitemap published | Nutzungsbedingungen 2.8.3: *"Du darfst die Informationen auf unserer Website bloß für deine persönliche Jobsuche und den privaten Gebrauch verwenden. Sämtliche Formen der automatisierten Auswertung unserer Plattform sind verboten."* (karriere.at/nutzungsbedingungen, no version date shown) |
| jobs.at | `GET /j/{keyword}?page`, `GET /i/{id}` (HTML) | yes | n/a | no | yes (1.2 s) | no | `User-agent: * / Disallow:`; jobs sitemaps published | AGB für Bewerber (Stand 19.01.2026) 2.3.3: identical wording to karriere.at (same group): *"Sämtliche Formen der automatisierten Auswertung unserer Plattform sind verboten."* |
| LinkedIn | `GET /jobs-guest/jobs/api/seeMoreJobPostings/search`, `GET /jobs-guest/jobs/api/jobPosting/{id}` | logged-out pages | yes | no | yes (2 s, backoff) | endpoints of the logged-out job pages | robots.txt header: *"The use of robots or other automated means to access LinkedIn without the express permission of LinkedIn is strictly prohibited."*; `Disallow: /jobs-guest/` for every listed user-agent; catch-all `User-agent: * / Disallow: /` | User Agreement (effective 3 Nov 2025) applies to *"Members and Visitors"*; 8.2: *"Develop, support or use software, devices, scripts, robots or any other means or processes (such as crawlers, browser plugins and add-ons or any other technology) to scrape or copy the Services"*; *"Copy, use, display or distribute any information (including content) obtained from the Services … without the consent of the content owner"* |
| willhaben | `GET /jobs/suche?keyword&page` (`__NEXT_DATA__` JSON), `GET /jobs/job/{slug}/{id}` | yes | n/a | no | yes (1.2 s) | Next.js page data | robots.txt header: *"It is expressively forbidden to use spiders, search robots or other automatic methods to access willhaben.at."*; `Disallow: /jobs/suche?*` (the search path used) and `/jobs/webapi/`; detail pages `/jobs/job/` not disallowed | AGB (Stand 01.09.2026) Pkt 8: rights in *"Texte, Marken, Fotos, Datenbanken, Layout"* reserved; *"Nutzungsvorbehalt gem. § 42h Abs 6 UrhG: Die Nutzung der Inhalte … für Text- und Data Mining iSd § 42h Abs 6 UrhG für die Zwecke der Anlernung bzw. des Trainings von KI-Modellen … ist ausdrücklich verboten."* Nutzungsbedingungen: copying *"durch 'Robot/Crawler' Suchmaschinentechnologien oder durch sonstige automatische Mechanismen"* without consent prohibited |
| AMS JobBarometer | `GET /berufe/{group}/{beruf}/{NUTS2}` (server-rendered HTML) | yes | n/a | no | yes | no | robots.txt 404 (no directives) | No Nutzungsbedingungen, copyright or licence statement on jobbarometer.ams.at; ams.at Impressum has no reuse clause; AMS AGB für Arbeitsuchende (27.01.2026) contain no website-use clause. AMS publishes aggregate labour-market data as open data (OTS 02.12.2021: *"Daten in maschinenlesbarer Form mit Lizenz zur uneingeschränkten Weiterverwendung"*), licence identifier not verifiable from data.gv.at (JavaScript catalogue). |
| AMS "alle jobs" API | not used (401 without OAuth token) | – | – | **not bypassed** | – | – | – | – |
| StepStone, Indeed, hokify, Glassdoor | not used for the 2026-09-16 snapshot (403 / WAF / login) | – | – | **not bypassed** | – | – | – | not fetched (not used on 2026-09-16); StepStone/Indeed attempts of the private hunter on 2026-09-18 are covered in §11 |

**Reading.** The collection did not bypass any technical barrier and behaved politely, but it *did* run against explicit contractual prohibitions on automated extraction at all five posting sources, and against robots.txt disallow rules at two (LinkedIn `/jobs-guest/`, willhaben `/jobs/suche`). The original project brief ruled out bypassing access controls; it did not require a terms-of-service review, which is why this audit is the first place these clauses are recorded. The consequence for the *future* is stated in §8; the consequence for *publication* is that no collector for a restricted source and no source record is distributed.

## 3. Jurisdictions and instruments considered

| Instrument | Relevant? | Why |
|---|---|---|
| **GDPR** (Regulation (EU) 2016/679) — Art 2(2)(c), 4(1), 6(1)(f), 14, 89 | Yes | Named contact persons in ads are personal data; private collection vs. public re-publication differ (CJEU C-101/01 *Lindqvist*: putting personal data on an internet page is processing outside the household exemption). |
| **Austrian DSG** | Marginal | National implementation; no DSB guidance on scraping/publishing scraped data was found (dsb.gv.at mentions web scraping only in its AI page, noting that legitimate interest "in Frage kommen könnte"). |
| **Directive 96/9/EC** (database right) Art 7, 8, 9; **UrhG §§ 76c–76e** | Yes, central | Job boards are paradigm sui generis databases; the question is extraction/re-utilisation of substantial parts and repeated systematic extraction. |
| **UrhG § 42 (private copy), § 42h (TDM), § 76d(5)** | Yes | Determines whether the private analysis copies were permitted; § 76d(5) applies § 42h to databases (verified on RIS, Fassung 01.01.2022). |
| **Directive (EU) 2019/790** Art 2(1), 3, 4, 7(1) | Yes | Source of § 42h; defines who is a research organisation; Art 4 opt-out and its contractual overridability. |
| **CJEU** C-203/02 *BHB v William Hill*, C-202/12 *Innoweb*, C-30/14 *Ryanair v PR Aviation*, C-762/19 *CV-Online Latvia v Melons* | Yes | Substantial investment, re-utilisation by meta-search, contractual limits where no database right exists, and the 2021 job-ad-aggregator balancing test. |
| **UrhG § 1/§ 2 copyright in ad texts** | Secondary | Most ads are functional texts; protection uncertain; the database right is the more reliable exposure. |
| **Commission Decision 2011/833/EU**, ELA/Commission legal notices (CC BY 4.0) | Yes, for EURES | Establishes that EU-owned content is reusable but third-party content (national PES vacancies) is not covered. |
| **EU AI Act, Data Act, Digital Services Act** | Not relevant | No AI system placed on the market; no data-holder obligations; the repository is not an intermediary service. Mentioned only to record that they were considered. |
| **UWG (unfair competition)** | Not analysed in depth | The project is non-commercial and does not compete with any source; noted as a residual consideration if the project were ever commercialised. |
| **GitHub Terms of Service / Acceptable Use Policies** (effective 27 Apr 2026) | Yes | Uploader bears all rights (D.1/D.3); AUP prohibits content infringing proprietary rights or "posting another person's personal information without consent". |

## 4. Analysis by risk category

### 4.1 Privacy (GDPR)

* **Private collection and retention.** Processing of the contact data by a natural person for personal career research plausibly falls within the household exemption (Art 2(2)(c)) as long as it is not shared; even if it did not, Art 6(1)(f) with data minimisation would apply. The contact fields were never used by any analysis step. **Recommendation (private repo):** keep as-is or, better, run a redaction pass over `description_text` in the processed files when the raw data is next rebuilt; the raw envelopes can stay for provenance as long as the repository remains private and access-controlled.
* **Publication.** Publishing those fields would be processing outside the household exemption (*Lindqvist*), for which no lawful basis was established, no Art 14 information was given, and no necessity exists (the statistics do not need them). Aggregated tables contain no personal data; employer names are legal persons. Table columns that carried verbatim snippets are removed from every public artefact (§7), and the export script aborts if any e-mail or phone pattern survives.
* **Risk level:** raw/processed public = **BLOCKER**; aggregates public = **LOW**.

### 4.2 Copyright in advertisement texts

* Austrian protection requires an "eigentümliche geistige Schöpfung" (§ 1 UrhG). Requirement lists and duty descriptions follow functional constraints; a German court (KG Berlin 18.07.2016, 24 W 57/16) denied protection to such lists, but no Austrian decision on job advertisements could be verified (RIS Rechtssatz searches on "Inseratentext", "Werbetext", "Sprachwerk" returned only unfair-competition and trade-mark cases). Employer-branding paragraphs may reach the threshold.
* Private copies of protected texts for analysis are covered by § 42h(6) (TDM for own use) where access was lawful and no machine-readable reservation exists, and by § 42(4) private copy — but § 42(5) excludes private copies made in order to make the work available to the public.
* **Risk level:** full texts public = **HIGH**; titles, extracted skill terms, counts and statistics public = **LOW** (facts, not expression).

### 4.3 Database right (Directive 96/9/EC, UrhG §§ 76c–76e)

* Each job board invests substantially in *obtaining, verifying and presenting* advertisements (C-203/02: investment in collecting existing material counts). The boards therefore hold sui generis rights; willhaben states this expressly (AGB Pkt 8).
* **Extraction.** 12,429 detail records plus ~64,000 listing rows across five sources on one day. Relative to each source's database (EURES lists 64,654 Austrian vacancies on the day of the audit; karriere.at and LinkedIn are larger) the extracted share is small, but "repeated and systematic extraction of insubstantial parts" (Art 7(5); § 76d(1) second sentence) is captured when it conflicts with normal exploitation. The 2021 test (C-762/19, para 44) is whether the acts "constitute a risk to the possibility of redeeming that investment". A one-day, non-commercial, non-substituting statistical extraction is at the favourable end of that test; a monthly re-run over years would move it towards "repeated and systematic".
* **Exceptions.** § 76d(3) Z1 (private purposes) *does not apply* to databases whose elements are individually accessible electronically — i.e. it does not cover online job boards. § 76d(3) Z2 (science/teaching, non-commercial, source stated) covers reproduction, not publication. § 42h applies to databases via § 76d(5) (verified), but § 42h(6) yields to a machine-readable reservation (LinkedIn robots.txt `Disallow: /`; willhaben robots header and AGB Pkt 8), and Art 4 DSM is not protected against contractual override (Art 7(1) lists Arts 3, 5, 6 only), so the karriere.at / jobs.at / EURES terms can validly reserve it. § 42h(1) (research) is written for research organisations and "einzelne Forscher" pursuing non-commercial research; whether an unaffiliated individual qualifies is contested and was not relied on.
* **Re-utilisation by publication.** Publishing the raw records or the per-posting tables would be re-utilisation of extracted content and would create exactly the substitute product that C-762/19 and C-202/12 sanction. Publishing aggregated shares (e.g. "SQL is mentioned in 35 % of 720 postings") re-utilises no part of any database.
* **Risk level:** raw/processed public = **BLOCKER**; per-posting tables with titles+employer+URL public = **MEDIUM** (removed); aggregates public = **LOW**.

### 4.4 Text-and-data-mining exceptions — what they do and do not cover

| Question | Answer (with source) |
|---|---|
| Which exception? | Art 3 DSM / § 42h(1)–(5) UrhG (research organisations, cultural-heritage institutions, individual researchers for non-commercial purposes); Art 4 DSM / § 42h(6) UrhG (anyone, own use, opt-out possible). |
| Does the author qualify as a "research organisation"? | **No.** Art 2(1) DSM defines it as a university, research institute or entity whose primary goal is scientific research on a not-for-profit or public-interest basis. A private individual does not qualify. § 42h(1) second sentence extends the reproduction right to "einzelne Forscher" for non-commercial purposes; the author is not affiliated with a research institution, so reliance on it is uncertain and was not relied on. |
| Does commercial/non-commercial status matter? | Yes for § 42h(1) (non-commercial only) and § 76d(3) Z2; the project is non-commercial. |
| Do rights-holder opt-outs matter? | Yes for § 42h(6)/Art 4: LinkedIn's robots.txt and willhaben's robots.txt header + AGB Pkt 8 are reservations; karriere.at/jobs.at/EURES reserve in prose terms, which Art 4 does not override. |
| Must access be lawful? | Yes (§ 42h(1) and (6): "rechtmäßig Zugang"). All pages were publicly served without login; no technical barrier was bypassed. Whether access contrary to terms is still "lawful access" is unsettled. |
| Is retention allowed? | § 42h(6): "solange dies für die Zwecke der Datenauswertung und Informationsgewinnung notwendig ist"; § 42h(2): with adequate security, as long as justified by the research purpose. Indefinite retention of full texts after the analysis is complete is weakly supported → see §8 recommendation. |
| Does TDM permission cover publication/republication? | **No.** Both exceptions permit *reproduction/extraction for analysis*. Neither authorises making the copied works or extracted database contents available to the public. |
| Does the database right remain relevant? | Yes; § 76d(5) applies § 42h to databases, with the same opt-out limits. |
| Do contractual restrictions matter? | Yes for Art 4/§ 42h(6) (overridable); no for Art 3/§ 42h(1)–(5) (§ 42h(5): "kann vertraglich nicht abbedungen werden") — but the author cannot rely on Art 3. |

Conclusion: TDM law supports *analysing* lawfully accessible material for own use where no reservation exists; it never supports *redistributing* it. The claim "educational research is protected by EU TDM exceptions" is therefore only partly true for this project and is not used as a justification for publishing anything beyond statistics.

### 4.5 Contractual / terms-of-service risk

* All five posting sources restrict automated extraction (table in §2). Whether browse-wrap terms bind a logged-out visitor under Austrian law was not researched; C-30/14 *Ryanair* confirms that, where no database right applies, contractual limits are not pre-empted by the Directive — i.e. terms can bite even where the database right does not.
* LinkedIn's clause "Develop, support or use software … to scrape" would be engaged by *publishing* the LinkedIn collector as much as by using it. karriere.at/jobs.at prohibit "automatisierte Auswertung" by the user; EURES prohibits extraction "in order to further process or re-publish".
* Publishing derived statistics is not itself an act of automated access, and no fetched clause prohibits publishing statistics *about* a platform. The risk is reputational and indirect (the methodology openly states how data was obtained).
* **Risk level:** publishing collectors for restricted sources = **HIGH** (not done); publishing raw = **BLOCKER**; publishing aggregates + methodology = **MEDIUM** (residual, disclosed).

### 4.6 Technical-access risk

No circumvention. Undocumented front-end JSON endpoints were used at EURES, karriere.at and LinkedIn; these are the same requests a browser issues, but they are not published APIs and (EURES) are reserved to partner organisations. Rate limiting was respected. **Risk level:** LOW technically; the contractual side is covered in 4.5.

### 4.7 Source-republication risk

Covered in 4.3/4.5: **BLOCKER** for raw text and per-posting records; **LOW** for statistics.

### 4.8 Reputational / professional risk

The public repository will be read by recruiters, hiring managers and possibly the sources' legal staff. The credible posture is (a) no source content redistributed, (b) the collection method and its terms conflicts stated plainly rather than hidden, (c) a stated intention to use permitted channels for future collection (§8). Publishing a scraper for LinkedIn or EURES under the author's name would be the opposite of that posture. **Risk level after sanitisation:** LOW–MEDIUM.

## 5. Risk-level definitions

| Level | Meaning used in this audit |
|---|---|
| **LOW** | No fetched clause or statute is engaged, or the exposure is theoretical and the artefact is clearly outside the protected subject matter (statistics, code written by the author). |
| **MEDIUM** | A clause or statute is arguably engaged but the artefact is non-substituting, non-commercial and contains no protected text or personal data; exposure is mainly reputational or a cease-and-desist scenario. |
| **HIGH** | A fetched clause or statute is directly engaged and a rights-holder would have a straightforward claim (e.g. publishing scrapers for a site whose terms forbid them). |
| **BLOCKER** | Publication would republish personal data without a lawful basis, or re-utilise substantial source content, or exceed GitHub's own limits; the artefact must not be public regardless of other factors. A single BLOCKER prevents publication of that artefact. |

## 6. Source-by-source publication matrix

| Source | Raw data public? | Derived aggregates public? | Full text public? | Collector code public? | Terms risk | Database-right risk | Privacy risk | Recommended treatment |
|---|---|---|---|---|---|---|---|---|
| EURES portal (AMS feed) | No (BLOCKER: contact data, third-party text, terms) | Yes (LOW) | No | **No** (terms reserve extraction to partners) | HIGH for extraction; MEDIUM for aggregates | MEDIUM | HIGH in raw | **PUBLIC AGGREGATES ONLY + PUBLIC METHODOLOGY** |
| karriere.at | No | Yes (LOW) | No | No (Nutzungsbedingungen 2.8.3) | MEDIUM | MEDIUM | HIGH in raw | **PUBLIC AGGREGATES ONLY** |
| jobs.at | No | Yes (LOW) | No | No (AGB 2.3.3) | MEDIUM | LOW (105 records) | MEDIUM in raw | **PUBLIC AGGREGATES ONLY** |
| LinkedIn | No | Yes (LOW) | No | **No** (User Agreement 8.2; robots.txt) | HIGH | MEDIUM | HIGH in raw (HTML pages) | **PUBLIC AGGREGATES ONLY** |
| willhaben | No | Yes (LOW; 27 core postings) | No | **No** (robots header, AGB Pkt 8, § 42h(6) reservation) | HIGH | MEDIUM | HIGH in raw (`contact` objects) | **PUBLIC AGGREGATES ONLY** |
| AMS JobBarometer | No (stored HTML pages are AMS works; not needed publicly) | Yes (LOW; AMS publishes these figures openly) | No | **Yes** (public body statistics page, no terms found, no robots directives) | LOW | LOW | none | **PUBLIC (code + aggregates)** |
| ESCO | n/a (CC BY 4.0 taxonomy lookups only) | Yes | n/a | Yes | LOW | LOW | none | PUBLIC |
| Eurostat JVS (added 2026-09-16) | **Yes** (48 KB JSON, openly licensed, published) | Yes | n/a | **Yes** | LOW (documented open API, no restriction found) | LOW (official statistics, reuse permitted with attribution) | none (aggregate statistics only) | **PUBLIC (code + raw + aggregates)** |
| Salary reference pages (`data/external`) | No (third-party HTML pages) | Cited figures only | No | n/a | LOW | LOW | none | PUBLIC METHODOLOGY ONLY (citations) |
| Arbeitnow Job Board API (added 2026-09-18, §11.1) | No (ATS job texts) | Yes, via T19 only when ≥ 20 core rows (2026-09-18: 0 core rows, below threshold) | No | **Yes** (documented API, no key) | not verified (terms not fetched; open item §11.1) | LOW | LOW (employer ads) | **PUBLIC CODE + THRESHOLDED AGGREGATES; RAW PRIVATE** |
| LinkedIn job listings via python-jobspy (private hunter, 2026-09-18, §11.2) | No | Yes (T19, 109 core titles, aggregates only) | No | **No** (`src/private/`) | HIGH for the collection (same `jobs-guest` endpoints as the LinkedIn row above) | LOW | LOW (hunter DB holds title, company, location, URL; 2 of 337 rows carry a description) | **PUBLIC AGGREGATES ONLY (T19) + DISCLOSED METHOD** |
| StepStone.at, Indeed.at (private hunter, 2026-09-18, §11.3) | No (nothing usable collected: live HTTP 403; one non-core jobspy Indeed row) | No table carries their rows | No | **No** | not fetched | – | – | **PRIVATE; nothing published** |

Layer 2 sources (GitHub API, Stack Overflow survey, Eurostat supply, the LinkedIn member slot) are classified in §10.6.

## 7. What the public export contains and excludes (implemented in `src/publish/export_public.py`)

*List regenerated on 2026-09-30 from the `INCLUDE_*` / `EXCLUDE_*` constants of the export script; the script is authoritative if the two ever differ.*

**Public:**
* Files (`INCLUDE_FILES`): `README.md`, `AGENT_CONTEXT.md`, `CAREER_DECISION_MAP.md`, `CAREER_SUPPLY_DEMAND_MAP.md`, `DECISION_LOG.md`, `PUBLICATION_DECISION.md`, `LICENSE`, `CITATION.cff`, `requirements.txt`, `.gitattributes`; `pyproject.toml` and `.github/` when present (`OPTIONAL_FILES`, `OPTIONAL_DIRS`). The public `.gitignore` is a purpose-written template (`src/publish/public.gitignore`); the private `.gitignore` is not exported because it names private tools and folders.
* Folders (`INCLUDE_DIRS`): `docs/` (except the documents in `EXCLUDE_DOCS`, below), `config/` (with `config/profile.json` replaced by the neutral `config/profile.example.json`, `SUBSTITUTE_FILES`), `schemas/`, `tests/` (except `tests/fixtures/radar/`), `outputs/figures/`, `src/pipeline/`, `src/analysis/`, `src/reporting/`, `src/publish/`, `src/viz/` (house style, figure engine, vendored Lato fonts under SIL OFL 1.1).
* Acquisition code (`INCLUDE_ACQUISITION`): `common.py`, `collect_jobbarometer.py`, `collect_eurostat_jvs.py`, `collect_github_supply.py`, `collect_eurostat_supply.py`, `ingest_stackoverflow_survey.py`, `ingest_linkedin_manual.py`, `collect_arbeitnow.py`.
* Raw data (`INCLUDE_RAW_DIRS`): `data/raw/eurostat_jvs/`, `data/raw/eurostat_supply/` (openly licensed official statistics). `data/raw/`, `data/processed/`, `data/external/` otherwise exist only as empty folders with a `.gitkeep`.
* Outputs: `outputs/*.json` (every key matching the drop pattern removed), `outputs/reports/digest.txt`, `outputs/PUBLIC_EXPORT_MANIFEST.txt`, and all `outputs/tables/*.csv` except the five tables in `EXCLUDE_TABLES`, with every column matching `snippet|^description$|description_text|description_html|(^|_)urls?($|_)|(^|_)html($|_)` dropped (this covers `source_url`, `company_url`, `html_url`, `repo_url` and `raw_html`; count columns such as `with_description` are kept) and `posting_uid` replaced by a keyed hash.

**Private (never exported):** `data/raw/` (except the two Eurostat folders), `data/processed/`, `data/external/`, `data/labels/`, `data/private/`, `logs/`, `PROGRESS.md`; the owner's personal strategy and private-method documents `CAREER_ASSUMPTIONS_REVIEW.md`, `library_strategy/`, `docs/profile-specific-demand-supply-analysis.md`, `docs/linkedin-slot-interface.md` and `config/profile.json` (D-026); `src/private/` (the hunter and the LinkedIn slot cockpit); `tests/fixtures/radar/` (hand-written fixtures that only exercise the private radar parsers); the six posting-collector scripts for the five posting sources (`collect_eures.py` and `collect_eures_styria_text.py` for EURES, `collect_karriere.py`, `collect_jobsat.py`, `collect_linkedin.py`, `collect_willhaben.py`); and the tables `T09e_salary_observations.csv`, `Q07a_salary_audit_sample.csv`, `Q07b_salary_implausible.csv`, `Q09_skill_spotcheck_sample.csv`, `T16a_adjacent_titles_styria.csv`. The export blocks if any `PRIVATE_NEVER` path or excluded collector appears in the built tree.

**Retained in public tables:** job titles (facts; used in `T02c`, `Q03b`, `Q03c` for auditability of the taxonomy); employer names of legal entities (`T04`, `T04a`); `posting_uid` as a **keyed hash** (`p_` + 16 hex characters). *Correction 2026-09-30:* the private `posting_uid` is not an opaque hash but `source:source_id` (for LinkedIn the job id that forms the posting URL), so publishing it raw would publish a source posting identifier; the export now replaces it with an HMAC-SHA256 under a private key (`EXPORT_UID_KEY`) and blocks any `source:id` value that survives in a table. `T04c_linkedin_industry_raw.csv`: LinkedIn's own industry category labels (a fixed vocabulary, not advertisement text) with posting counts per source — facts about the sample, no personal data, no substantial part of any database; LOW. `T19_supplement_*.csv`: dated aggregates of the private hunter (families, sources, states, skills with counts and Wilson intervals; status row) over 109 core titles of python-jobspy LinkedIn job listings of 2026-09-18 — no titles, companies, URLs or texts; privacy and database right LOW, the contractual/reputational position is that of the Layer 1 LinkedIn aggregates (§4.5, §11.2).

**Guard:** the export builds into a staging folder and replaces the public tree only if nothing is found. It blocks on: an e-mail address (reserved placeholder domains such as `example.com` excepted); a phone number in international (+43/0043) or Austrian domestic format; a link to an individual job advertisement (LinkedIn, karriere.at, willhaben, jobs.at, EURES, Indeed, StepStone); a secret-like token (also in `.md` files); a GitHub login from the private candidate list (the login itself is never printed); a URL, a raw `source:id` value or a cell longer than 200 characters (free text, outside a list of aggregate columns) in a table or JSON summary; a row below the suppression thresholds in `C02` (`count` ≥ 3) or `C19e` (`projects` ≥ 5); the owner's own `config/profile.json`; any private path or posting collector; a module-level import of an unexported collector in exported code (the public tests would fail on import).

**Git:** the public repository is initialised with a fresh history from the exported tree; the private history (commit `299045b` and later) is never pushed.

## 8. Recommendations for the private repository and for future collection

1. **Retention.** Keep the raw envelopes private and access-controlled. Once the monthly re-collection design is settled, consider a redaction pass that removes contact blocks from `description_text` in processed files and stores raw HTML only for the JobBarometer; § 42h(6) supports retention only "as long as necessary for the analysis".
2. **Future collection (superseded operationally by D-022).** The 2026-09-16 recommendation not to re-run LinkedIn/willhaben was a *publication* control, not a ban on private research. Collectors, raw records, URLs and JD text stay unpublished. Since 2026-09-30 (D-026 (b), commit `826b6b9`) the Layer 1 raw scrapes, processed postings and fetched third-party pages are also untracked in the private git repository and git-ignored (the files remain on the owner's disk; Eurostat raw data stays tracked because it is published); the hunter (`src/private/`) and its raw folders were git-ignored from the start (D-022). The posting-collector scripts remain tracked in the private repository only and are excluded from the export. Private, non-commercial, research/study collection (including StepStone, Indeed, LinkedIn *job listings*, saved HTML, Arbeitnow) is in-scope when the owner asks, with polite delays, dated folders, no snapshot merging, and **no** CAPTCHA/login/WAF/paywall bypass. LinkedIn *people/member* data is never collected by automation: the member slot accepts only permitted channels (manual observation, official exports, licensed data; D-018 as narrowed by D-026 (a)). Public-reproducible refresh stays JobBarometer, Eurostat, GitHub API, and the Arbeitnow API collector code (raw private). Commercial use would require a re-audit.
3. **If the project were ever commercialised** the analysis above would need to be redone; several conclusions (non-commercial TDM, C-762/19 balancing) depend on the non-commercial character.

## 9. Sources fetched for this audit (all 2026-09-16)

Platform terms: linkedin.com/legal/user-agreement (effective 3 Nov 2025); linkedin.com/robots.txt; karriere.at/nutzungsbedingungen; karriere.at/agb; karriere.at/robots.txt; jobs.at/agb (Stand 19.01.2026); jobs.at/robots.txt; willhaben.at/iad/agb (Stand 01.09.2026); willhaben.at/iad/nutzungsbedingungen; willhaben.at/robots.txt; europa.eu/eures/portal/jv-se/home ("Specific data quality disclaimer and terms of use for job vacancies"); eures.europa.eu/legal-notice_en; commission.europa.eu/legal-notice_en; europa.eu/robots.txt; jobbarometer.ams.at (+ /Datenschutz.html, /Quellenverzeichnis.html, robots.txt 404); ams.at/organisation/ueber-ams/impressum; ams.at/organisation/ueber-ams/allgemeine-geschaeftsbedingungen (+ AGB für Arbeitsuchende PDF 27.01.2026); ots.at OTS_20211202_OTS0030; docs.github.com terms-of-service and acceptable-use-policies.

Law and guidance: EUR-Lex CELEX 31996L0009 (Directive 96/9/EC), 32019L0790 (Directive (EU) 2019/790), 32016R0679 (GDPR), 32011D0833 (Commission Decision 2011/833/EU); RIS UrhG (Gesetzesnummer 10001848, Fassung 01.01.2022) §§ 42, 42h, 76c, 76d, 76e; CJEU ECLI:EU:C:2004:695 (C-203/02), ECLI:EU:C:2013:1038 (C-202/12), ECLI:EU:C:2015:10 (C-30/14), ECLI:EU:C:2021:434 (C-762/19), ECLI:EU:C:2003:596 (C-101/01); EDPB "Report of the work undertaken by the ChatGPT Taskforce" (23 May 2024); EDPB Opinion 28/2024 (Dec 2024); "Concluding joint statement on data scraping and the protection of privacy" (28 Oct 2024, 16 authorities; Austria's DSB not a signatory); dsb.gv.at page on AI and data protection.

Could not verify: an Austrian court decision on the copyright status of job advertisements; the exact data.gv.at licence identifier of the AMS open-data sets; whether browse-wrap terms bind logged-out visitors under Austrian law.

## 10. Layer 2 addendum (2026-09-17): candidate-supply sources — collection, retention and publication

**Scope.** This section audits the material added for Layer 2 (observed candidate supply) and Layer 3 (demand × supply): the GitHub API collection, the Eurostat supply series, the Stack Overflow survey extract, the manual LinkedIn slot, and the derived tables/JSON/figures. Same standard as §0–§9: a publication-readiness analysis by the author with AI assistance, not legal advice; clauses fetched 2026-09-17.

### 10.1 What was collected and what it contains

| Material | Personal data? | Third-party content? | Retention |
|---|---|---|---|
| `data/raw/github_supply/<date>/users_search.jsonl`, `profiles.jsonl` | **Yes**: login, bio, free-text location, company field, website URL, X handle, hireable flag, counters, dates (names and e-mail addresses were never requested) | bios are user text | private, access-controlled; needed for reproducibility and the review samples; no analysis needs names |
| `repos.jsonl` | login as owner; repository descriptions | metadata of user repositories | private |
| `readmes.jsonl` | README texts may contain names/contact lines of their authors | **Yes**: README texts (copyrightable prose, under the repository licence if any) | private; read for features only; max 40 k chars each; recommendation: purge README bodies after the analysis is frozen (§10.5) |
| `social.jsonl` | social-account URLs (LinkedIn/X/…) | — | private; only link *types* are derived |
| `data/raw/eurostat_supply/` | none | official statistics, reuse permitted | public |
| `data/external/stackoverflow_survey/2025/` | anonymous respondent rows (ODbL) | ODbL database extract | private (share-alike scope, size); aggregates public with attribution |
| `data/raw/linkedin_supply/<date>/` (manual) | pseudonymous coded observations, search counts | none (hand-coded) | private, git-ignored, never exported |
| `data/processed/supply_*` | candidate/project rows with login, bio, location, README-derived features; review samples with bios and repo descriptions | — | private |
| `outputs/tables/C*`, `DS*`, `SQ*`, `O*`, `outputs/supply_*.json`, `demand_supply_*.json`, figures | **No**: counts, shares, intervals; raw-bio *phrases* only when ≥ 3 accounts share them; README *headings* only when ≥ 5 projects share them | none reproduced beyond generic phrases/headings | public |

### 10.2 GitHub: terms and law

* **Terms.** GitHub Terms of Service (effective 27 Apr 2026), section H "API Terms" (rate-limit and abuse clauses) and the Acceptable Use Policies §7 "Information Usage Restrictions" (fetched 2026-09-17): *"Scraping refers to extracting information from our Service via an automated process, such as a bot or webcrawler."* — *"Researchers may use public, non-personal information from the Service for research purposes, only if any publications resulting from that research are open access."* — *"You may not use information from the Service (whether scraped, collected through our API, or obtained otherwise) for spamming purposes, including for the purposes of sending unsolicited emails to users or selling personal information, such as to recruiters, headhunters, and job boards."* — *"Your use of information from the Service must comply with the GitHub Privacy Statement."* The Privacy Statement (fetched 2026-09-17) states that users control what profile data is public and contains no further restriction on research use.
* **Reading.** The collection is research, non-commercial, publishes open-access (CC BY 4.0) aggregates and sells nothing. The clause permits *non-personal* information; bio and location are personal information, which is why they are used only privately for classification and are never published, and why names/e-mails were not requested at all (data minimisation). Residual risk: MEDIUM-LOW (the research clause is narrower than the collection; mitigated by minimisation, private retention, aggregate-only publication and open-access output).
* **GDPR.** Processing of public profile text by a natural person for personal career research, kept offline, plausibly falls under Art 2(2)(c); if not, Art 6(1)(f) legitimate interest with minimisation applies (no names, no contact data, no individual outputs, no decisions about individuals, no profiling in the Art 22 sense: nobody is scored). Publishing individual rows would be processing outside the household exemption (C-101/01 *Lindqvist*) without a basis → **BLOCKER** for raw/processed; aggregates contain no personal data → LOW. Art 14 information is not provided to the account holders; this is proportionate only because nothing individual is derived or published and the data are retained privately for a limited time (§10.5).
* **Copyright / database right.** README texts are the authors' prose (often under the repository's licence, often none). Reading them for statistical features is TDM for own use (§ 42h(6) UrhG; GitHub's robots.txt does not reserve API access, and the API is the sanctioned channel). No README text is republished; the public tables carry only feature shares and headings shared by ≥ 5 projects. GitHub's own database right is not engaged by aggregate statistics over a few thousand accounts (C-762/19 investment-harm test). Risk LOW.

### 10.3 Stack Overflow survey

ODbL 1.0 as stated on survey.stackoverflow.co/2025. The official download URL returned HTTP 404 on 2026-09-17; the identical archive (16.8 MB, sha256 in the manifest) was obtained from a public GitHub mirror committed 2025-11-06. ODbL permits use and redistribution with attribution; a *derivative database* (the Austrian extract) would have to be offered under ODbL, so the extract is kept private and only *produced works* (aggregate tables, figures) are published with attribution. Respondents are anonymous. Risk LOW.

### 10.4 Eurostat, LinkedIn, Kaggle

Eurostat: open API, Decision 2011/833/EU reuse, raw published (as in D-015). LinkedIn *members/people*: no automated access (D-013, D-018, narrowed by D-026 (a) to "any permitted channel, never member-site automation"); LinkedIn *job listings* were collected by automation for Layer 1 (2026-09-16) and by the private hunter (2026-09-18) and are covered in §2, §4.5 and §11, not here. The manual slot records the owner's own manual observations under pseudonymous ids, which is ordinary member use; the coded fields are limited to what is visible without connecting; the folder is git-ignored; risk of the *slot design* LOW, but any filled records are personal data and must never be published. Kaggle: nothing collected (no account, no scraping); the terms review of 2026-09-30 (`docs/kaggle-terms-review.md`) confirms the decision not to collect: the Terms of Use forbid scraping and the official API carries no user location, so it cannot identify Austrian candidates.

### 10.5 Recommendations (private repository)

1. Keep the GitHub raw folder access-controlled; do not add names/e-mails in future runs.
2. After the analysis is frozen, replace `readme_text` in `readmes.jsonl` with the derived features (a redaction pass), and drop `bio`/`location_text`/`company`/`blog` from `supply_candidates.*` once the review samples have been audited; keep only hashed ids and derived fields. (Same principle as §8.1 for advertisement texts.)
3. Any re-collection must re-check GitHub AUP §7 and the rate-limit terms; keep the descriptive User-Agent.
4. Never fill the LinkedIn slot by member-site automation or scripted output (only the permitted channels of D-026 (a)); never export its folder.

**Implemented 2026-09-30 (D-028).** The Layer 2 analysis was frozen and recommendation 2 was carried out with `python src/pipeline/redact_supply_raw.py --source github --date 2026-09-17 --confirm`. The raw GitHub files and the processed supply files are **pseudonymised, not deleted**:

* GitHub logins and repository names are replaced by `sha1("<kind>:<value>")[:16]`, the same scheme as `candidate_id`;
* `bio`, `blog`, `company`, free-text location, `twitter` and README text are set to null;
* social-account URLs are reduced to the provider name (the link *type* the analysis uses);
* README headings used by fewer than 5 projects are dropped (the public C19e threshold);
* the individual-level review samples are blanked, and `supply_quality_frameB_nonstyria_locations.csv` is deleted;
* a `REDACTED.json` marker records the run in the redacted folder.

This is **pseudonymisation, not anonymisation**: an unsalted hash of a public login can be reversed by looking the login up (or by hashing candidate logins), so the files remain personal data under GDPR Art 4(5) and stay private, access-controlled and excluded from the export. The derived counters, flags and classifications are kept for reproducibility of the frozen outputs; any later Layer 2 analysis starts from a new dated collection (D-016, D-028), not from the redacted files.

### 10.6 Publication matrix (Layer 2 material)

| Artefact | Status |
|---|---|
| `src/acquisition/collect_github_supply.py`, `collect_eurostat_supply.py`, `ingest_stackoverflow_survey.py`, `ingest_linkedin_manual.py`, `src/pipeline/build_supply.py`, `src/analysis/*supply*`, `demand_supply.py`, `project_analysis.py`, configs, schema, tests | **PUBLIC-SAFE** (author's code; documented APIs; no records) |
| `data/raw/eurostat_supply/` | **PUBLIC-SAFE** |
| `outputs/tables/C*`, `DS*`, `SQ*`, `O*`, `outputs/supply_*.json`, `demand_supply_*.json`, `project_evidence_map.json`, `operational_career_context.json`, figures `S*`, `DSF*` | **PUBLIC-SAFE** after the export scan (no e-mail/phone/URL/free text; raw-bio phrases ≥ 3 accounts; headings ≥ 5 projects) |
| `data/raw/github_supply/`, `data/processed/supply_*`, `data/external/stackoverflow_survey/`, `data/raw/linkedin_supply/`, `logs/github_supply.log` | **PRIVATE-ONLY** |
| `CAREER_ASSUMPTIONS_REVIEW.md`, `docs/profile-specific-demand-supply-analysis.md`, `library_strategy/`, `config/profile.json` | **PRIVATE-ONLY** (personal strategy; D-026 (c)) — excluded from the export; the public tree receives the neutral `config/profile.example.json` as `config/profile.json` |
| `docs/linkedin-slot-interface.md` (LinkedIn slot channel contract, added 2026-09-30) | **PRIVATE-ONLY** (D-026 (c)) — in `EXCLUDE_DOCS`; it describes the private member-slot channels and count grid |
| `docs/supply-methodology.md` §7 (manual LinkedIn protocol) | **PUBLIC-SAFE** (procedure only) |
| `outputs/tables/C02_raw_bio_title_distribution.csv`, `C19e_common_readme_headings.csv` | **NEEDS-REDACTION rule applied**: suppression thresholds (≥ 3 accounts / ≥ 5 projects) applied by the analysis code and re-verified by the export since 2026-09-30 (`SUPPRESSION_RULES`: `C02.count` ≥ 3, `C19e.projects` ≥ 5; a breach blocks the export) |
| Individual-level review samples `data/processed/supply_quality_*_sample.csv` | **PRIVATE-ONLY** |
| `data/labels/` (hand labels of the measurement scaffolding) and `data/private/` (the owner's application log and letters) | **PRIVATE-ONLY** — git-ignored, never in an `INCLUDE_*` list, guarded by `PRIVATE_NEVER` (added 2026-09-30) |
| `src/analysis/labelling_audit.py`, `src/pipeline/snapshot_tracking.py`, `docs/labelling-protocol.md`, `docs/kaggle-terms-review.md`, `schemas/application_log_schema.md` | **PUBLIC-SAFE** (author's code, procedures and schema; no records) — added 2026-09-30 |
| `outputs/tables/Q10_*`, `Q10b_*`, `Q11_*`, `Q12_*`, `Q12b_*` (labelling/measurement aggregates, when produced) | **PUBLIC-SAFE** after the export scan (aggregates only; the same column, identifier and free-text guard applies) |

## 11. Addendum (2026-09-30): private hunter, Arbeitnow, radar-derived tables, export changes

**Scope.** Material added by D-022/D-023 (2026-09-18) that §0–§10 did not cover, and the export changes of 2026-09-30 (D-026). Same standard as above: a publication-readiness analysis by the author with AI assistance, not legal advice. **No source was fetched for this addendum** (the 2026-09-30 review ran without network access); clauses quoted are those fetched on 2026-09-16 (§9), and items that would need a fresh fetch are listed as open.

### 11.1 Arbeitnow Job Board API (`collect_arbeitnow.py`, public code)

* **What.** A documented, key-less JSON API that the operator describes publicly (blog post fetched 2026-09-18); it carries job advertisements fed from applicant-tracking systems, Germany-heavy. The collector filters Austrian locations client-side. Run of 2026-09-18: 1,500 listings, 1 Austria-located, 0 core data roles (`T19_supplement_status.csv`).
* **Terms.** The API's usage terms were **not fetched or quoted** in any audit (open item). The same class of reasoning as for GitHub and Eurostat (documented API, sanctioned channel) supports publishing the *collector code*; it does not establish that redistribution of derived statistics is permitted.
* **Treatment.** Code public; raw records private (`data/raw/arbeitnow/`, ATS job texts with possible contact lines); aggregates only through T19 and only above the 20-core-row threshold (not reached). Risk: LOW for code and aggregates *if* the terms contain no restriction. **Open item:** fetch and quote the Arbeitnow terms before the next run; if they restrict automated use or publication of derived data, move `collect_arbeitnow.py` out of `INCLUDE_ACQUISITION`.

### 11.2 Private hunter: LinkedIn job listings via python-jobspy (T19)

* **What.** The git-ignored hunter (`src/private/radar/`, D-022/D-023) collected on 2026-09-18 job *listings* through python-jobspy: 337 rows in its database (335 LinkedIn, 1 Indeed, 1 Arbeitnow), 325 with an Austrian location, 109 classified as core data roles; title, company, location and URL, with a description in 2 rows. python-jobspy's LinkedIn scraper requests LinkedIn's logged-out `jobs-guest` search endpoint (checked in the installed library source on 2026-09-30) — the same endpoint class as `collect_linkedin.py` (§2).
* **Terms.** Therefore the LinkedIn row of §2 applies unchanged: robots.txt `Disallow: /jobs-guest/` and User Agreement 8.2. Contractual exposure of the *collection*: **HIGH**, as for 2026-09-16. No login, cookie or CAPTCHA was involved.
* **People vs jobs.** No member profile, people search, hiring-team data or member activity was collected, by the hunter or by any other script. The statement "LinkedIn: nothing collected by automation" in earlier versions of the publication documents refers to *people/member* data only; LinkedIn *job listings* were collected by automation twice (2026-09-16, 2026-09-18). `FORBIDDEN_METHODS` in `ingest_linkedin_manual.py` (guest endpoint, jobspy, …) governs the *member* slot, not the job-listing collection.
* **Publication.** Collector code, database, raw folder (`data/raw/radar/`), URLs and fit scores stay private. Public: the T19 aggregates (§7). Privacy LOW (aggregates of employer ads); database right LOW (109 titles, non-substituting); contractual/reputational **MEDIUM (residual)** — the same position as the Layer 1 LinkedIn aggregates (§4.5), disclosed in `docs/methodology.md` §1 rather than hidden. Should LinkedIn object, the T19 tables are removed as a set (they are a separate universe, never merged into the 720).
* **Rebuild.** `src/analysis/supplement_radar.py` is public but reads the private database; without it (public tree, fresh clone) it prints a notice and leaves the published T19 tables untouched (reported as not refreshed) instead of overwriting them.

### 11.3 StepStone.at and Indeed.at

The hunter's live StepStone.at harvest and a direct Indeed.at request stopped on HTTP 403 on 2026-09-18 and were not retried around the block; python-jobspy returned one Indeed row (not a core role); no browser-saved page was imported (`saved_pages/` holds only a README). No StepStone or Indeed row reaches any public table. Their terms were not fetched (open item if collection is ever resumed). The §2 row "not used (403 / WAF / login)" remains true for the 2026-09-16 snapshot.

### 11.4 Export and classification changes of 2026-09-30

* **Private by owner decision (D-026 (c)).** `docs/linkedin-slot-interface.md`, `config/profile.json`, `library_strategy/` (the latter was never in an `INCLUDE_*` list; now also guarded by `PRIVATE_NEVER`). The public tree receives the neutral `config/profile.example.json` under the name `config/profile.json`, so the public code and tests run; the published D01–D04 tables were computed from the private profile and are not reproduced by the example.
* **Layer 1 data out of git (D-026 (b)).** §8.2 now states the private-repository status exactly.
* **`posting_uid`.** Found to be `source:source_id`, not an opaque hash (§7 correction); replaced by a keyed hash at export.
* **Guard.** Staged, atomic export; URL-part column matching (`(^|_)url`); domestic phone formats; posting-URL, URL-in-table, secret (incl. `.md`), GitHub-login and raw-source-id checks; C02/C19e thresholds re-verified; public `.gitignore` template; collector exclusion checked as a blocking problem rather than an `assert` (§7).
* **Fixtures.** `tests/fixtures/radar/*.html` are hand-written (placeholder employers "Acme", "Example GmbH"), not saved pages; they are excluded anyway because they only exercise the private parsers, whose test skips without them.

### 11.5 Open items

1. Fetch and quote the Arbeitnow API terms (§11.1).
2. Fetch StepStone.at / Indeed.at terms before any further hunter run against them (§11.3).
3. Re-assess §4.5/§11.2 if LinkedIn job listings are collected again (a repeated run moves the database-right analysis towards "repeated and systematic", §4.3).
