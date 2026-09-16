# Legal, liability and publication audit

**Status:** audit performed 2026-09-16 on the repository state after the completeness audit (DECISION_LOG D-012/D-013). **This is a documented legal-risk and publication-readiness analysis by the repository author with AI assistance. It is not legal advice.** Every clause quoted below was fetched from the named URL on 2026-09-16; items that could not be verified are marked as such. The decision this audit feeds is recorded in `PUBLICATION_DECISION.md`.

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

* Complete file tree, `git ls-files` (251 tracked files), git history (one commit), remotes (none), `.gitignore`, ignored folders (`logs/`, `data/raw/_probe/`, `notebooks/`).
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
| StepStone, Indeed, hokify, Glassdoor | not used (403 / WAF / login) | – | – | **not bypassed** | – | – | – | – |

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
| Salary reference pages (`data/external`) | No (third-party HTML pages) | Cited figures only | No | n/a | LOW | LOW | none | PUBLIC METHODOLOGY ONLY (citations) |

## 7. What the public export contains and excludes (implemented in `src/publish/export_public.py`)

**Public:** `README.md`, `AGENT_CONTEXT.md`, `CAREER_DECISION_MAP.md`, `DECISION_LOG.md`, `PUBLICATION_DECISION.md`, `LICENSE`, `CITATION.cff`, `docs/`, `config/`, `schemas/`, `tests/`, `src/pipeline`, `src/analysis`, `src/reporting`, `src/publish`, `src/acquisition/common.py`, `src/acquisition/collect_jobbarometer.py`, `outputs/figures/`, `outputs/*.json` (scrubbed of any `url`/`snippet`/`description` keys), `outputs/reports/digest.txt`, and all `outputs/tables/*.csv` except the five per-posting tables listed below, with every column matching `snippet|description|source_url|url|company_url|raw_html|html` dropped.

**Private (never exported):** `data/raw/`, `data/processed/`, `data/external/`, `logs/`, `notebooks/`, `PROGRESS.md`, the five posting collectors (`collect_eures.py`, `collect_eures_styria_text.py`, `collect_karriere.py`, `collect_jobsat.py`, `collect_linkedin.py`, `collect_willhaben.py`), and the tables `T09e_salary_observations.csv`, `Q07a_salary_audit_sample.csv`, `Q07b_salary_implausible.csv`, `Q09_skill_spotcheck_sample.csv`, `T16a_adjacent_titles_styria.csv`.

**Retained in public tables:** job titles (facts; used in `T02c`, `Q03b`, `Q03c` for auditability of the taxonomy), employer names of legal entities (`T04`, `T04a`), internal `posting_uid` values (opaque hashes; they let the private owner trace any public row back to a source record without exposing the record).

**Guard:** the export aborts if any exported file contains an e-mail address, an Austrian phone-number pattern, a secret-like token, or a CSV cell longer than 200 characters (free text).

**Git:** the public repository is initialised with a fresh history from the exported tree; the private history (commit `299045b` and later) is never pushed.

## 8. Recommendations for the private repository and for future collection

1. **Retention.** Keep the raw envelopes private and access-controlled. Once the monthly re-collection design is settled, consider a redaction pass that removes contact blocks from `description_text` in processed files and stores raw HTML only for the JobBarometer; § 42h(6) supports retention only "as long as necessary for the analysis".
2. **Future collection.** Do not re-run the LinkedIn and willhaben collectors (explicit robots.txt disallow + terms). For EURES, the portal terms reserve API extraction to EURES partners; the permitted alternatives are the AMS open-data aggregates (data.gv.at), the AMS JobBarometer, and — if posting-level data is needed — a written permission request to AMS/EURES or the use of a licensed job-ad data provider. karriere.at/jobs.at: request permission or restrict to manual, personal job search. This is recorded in `DECISION_LOG.md` D-013.
3. **If the project were ever commercialised** the analysis above would need to be redone; several conclusions (non-commercial TDM, C-762/19 balancing) depend on the non-commercial character.

## 9. Sources fetched for this audit (all 2026-09-16)

Platform terms: linkedin.com/legal/user-agreement (effective 3 Nov 2025); linkedin.com/robots.txt; karriere.at/nutzungsbedingungen; karriere.at/agb; karriere.at/robots.txt; jobs.at/agb (Stand 19.01.2026); jobs.at/robots.txt; willhaben.at/iad/agb (Stand 01.09.2026); willhaben.at/iad/nutzungsbedingungen; willhaben.at/robots.txt; europa.eu/eures/portal/jv-se/home ("Specific data quality disclaimer and terms of use for job vacancies"); eures.europa.eu/legal-notice_en; commission.europa.eu/legal-notice_en; europa.eu/robots.txt; jobbarometer.ams.at (+ /Datenschutz.html, /Quellenverzeichnis.html, robots.txt 404); ams.at/organisation/ueber-ams/impressum; ams.at/organisation/ueber-ams/allgemeine-geschaeftsbedingungen (+ AGB für Arbeitsuchende PDF 27.01.2026); ots.at OTS_20211202_OTS0030; docs.github.com terms-of-service and acceptable-use-policies.

Law and guidance: EUR-Lex CELEX 31996L0009 (Directive 96/9/EC), 32019L0790 (Directive (EU) 2019/790), 32016R0679 (GDPR), 32011D0833 (Commission Decision 2011/833/EU); RIS UrhG (Gesetzesnummer 10001848, Fassung 01.01.2022) §§ 42, 42h, 76c, 76d, 76e; CJEU ECLI:EU:C:2004:695 (C-203/02), ECLI:EU:C:2013:1038 (C-202/12), ECLI:EU:C:2015:10 (C-30/14), ECLI:EU:C:2021:434 (C-762/19), ECLI:EU:C:2003:596 (C-101/01); EDPB "Report of the work undertaken by the ChatGPT Taskforce" (23 May 2024); EDPB Opinion 28/2024 (Dec 2024); "Concluding joint statement on data scraping and the protection of privacy" (28 Oct 2024, 16 authorities; Austria's DSB not a signatory); dsb.gv.at page on AI and data protection.

Could not verify: an Austrian court decision on the copyright status of job advertisements; the exact data.gv.at licence identifier of the AMS open-data sets; whether browse-wrap terms bind logged-out visitors under Austrian law.
