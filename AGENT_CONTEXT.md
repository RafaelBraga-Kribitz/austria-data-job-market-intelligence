# AGENT_CONTEXT — Austrian data-job market intelligence (canonical context for AI agents)

> This document is derived from the underlying evidence in this repository and should be updated when the market dataset changes. **Last updated: 2026-09-16 (post-audit run, DECISION_LOG D-012/D-013).** Data collected 2026-09-16 17:00–18:40 UTC; AMS JobBarometer series through 2025. If today is later than 2026-12-16, treat the snapshot numbers as stale and ask for a pipeline re-run (README → Reproduction; note the collection restrictions in §21).

## 0. How to use this file

* Use it as the single context for CV, LinkedIn, GitHub, project, learning, certification, job-search and geography decisions for the profile in §2.
* Every number is copied from `outputs/tables/` (ids in brackets). In the private repository each row can be traced to a source record via `data/processed/postings_dedup.jsonl` (`posting_uid`, `source_url`); in the public repository only the aggregated tables exist (§21). Machine-readable versions: `outputs/{market_summary,skills,roles,locations,languages,salaries,career_paths,jobbarometer,adjacent_demand,clusters,data_quality}.json`.
* Vocabulary: **share** = share of postings that *mention* an item (not "require"); **core postings** = 720 deduplicated postings whose title falls into eight data role families; **719** = those with a description (denominator of all text-derived shares); **Styria** = Bundesland Steiermark (n = 58 incl. multi-site ads); **Graz area** = Graz plus commuting municipalities (config/geo.json, n = 52).
* Robustness: *robust* = n ≥ 200, same direction in AMS and board/LinkedIn data, CI clear; *tentative* = otherwise. **Every Styria-only number is tentative (n = 58).** Always quote Styrian figures as counts ("8 of 58"), not only as percentages.
* Calibration: this dataset measures what advertisements *say*. It does not measure hiring, interviews, negotiability of stated requirements, or pay. Use "postings mention", "ads state", "advertised floor" — never "employers hire", "jobs per year", "salary".

## 1. Market snapshot (T01, T02, market_summary.json)

* 12,429 raw rows from EURES/AMS (4,569), karriere.at (2,114), LinkedIn guest pages (4,133), willhaben (1,508), jobs.at (105) → 10,945 unique postings → **720 core data-role postings** (+311 AI-software-engineering titles and 235 unclassifiable data-ish titles, reported separately). In-scope duplicate rate 24 %; 20 % of core groups were seen on ≥ 2 sources.
* Core postings by source: LinkedIn 300, AMS/EURES 202, karriere.at 134, jobs.at 58, willhaben 26.
* Missing sources (blocked): StepStone.at, Indeed.at, hokify, Glassdoor; company career pages not crawled. Corporate white-collar ads are under-covered.
* **Stock vs flow:** 720 is the number of ads open on one day. AMS counted 2,207 online ads in 2025 for its "Data Scientist (m/w)" class alone (JB05). Never present the snapshot as annual demand, vacancies or hires.
* Title-classification precision measured on 177 hand-labelled titles: 83 % strict / 95 % lenient after the audit (Q03c). Recall unmeasured.

## 2. Profile this context serves (config/profile.json)

≈20 years marketing/growth/performance marketing/CRO/experimentation/analytics/automation; English fluent; Portuguese native; German A2–B1; based Greater Graz; developing Python, SQL, R, statistics, ML, visualisation; open to hybrid/remote/relocation if justified. The have/developing/structural skill lists are self-declared and drive the decision matrix (§13); they are the main subjective input.

## 3. Role taxonomy (docs/role-taxonomy.md, T02, T02b)

| Family | Open postings AT | Share of 720 | Styria (of 58) | Main normalized titles |
|---|---|---|---|---|
| data_engineering | 160 | 22 % | 20 | Data Engineer 134, Data Architect/Platform 21, Analytics Engineer 5 |
| data_science | 158 | 22 % | 13 | Data Scientist 79, Machine Learning / AI Engineer 76, Statistician 3 |
| business_analysis | 120 | 17 % | 4 | Business Analyst / requirements 120 |
| data_analytics | 107 | 15 % | 11 | Data Analyst 77, data-heavy Finance/Risk/Ops Analyst 30 |
| bi | 85 | 12 % | 5 | BI Developer 33, BI Analyst 32, BI Consultant 20 |
| data_governance | 65 | 9 % | 5 | Governance/Steward/Data Manager 31, Master/Product Data Management 34 |
| marketing_analytics | 24 | 3 % | 0 | Marketing/Growth/CRM Analyst 22, Marketing Data Scientist 2 |
| product_analytics | 1 | 0.1 % | 0 | Product Analyst 1 |

## 4. Geographic snapshot (T03, JB05)

Vienna 48 % (343; 350 incl. multi-site), Upper Austria 17 % (122), **Styria 7.5 % (54; 58 incl. multi-site)**, Vorarlberg 6 %, Lower Austria 6 %, Salzburg 5 %, Tyrol 4 %, Carinthia 3 %, unspecified 3 %. Styria = Graz (34 city, 52 commuting area). Official yearly series: Styria 13.6 % of the national "Data Scientist"-class ads (300 of 2,207, 2025). Styrian family mix (of 58): engineering 20, science 13, analytics 11, BI 5, governance 5, business analysis 4, marketing/product 0. Styrian employers with ≥ 2 postings: KNAPP 7, adesso 4, Tieto 3, CANCOM, niceshops, Anton Paar, Mercedes-Benz G, Magna 2.

## 5. Key skill frequencies (T05, share of 719 core ads with description)

SQL 40 % (incl. SQL Server; 37 % without) · dashboards/visualisation 38 % · generic AI wording 38 % · Python 35 % · data-quality/governance wording 31 % · cloud 29 % · ETL/ELT 22 % · Azure 19 % · Power BI 18 % · Excel 18 % · data modelling 16 % · ML 16 % · GenAI/LLM 16 % · CI/CD 15 % · statistics 14 % · Databricks 12 % · REST/APIs 12 % · mathematics 11 % · data warehouse 10 % · Git 10 % · AWS 9 % · R 7 % · Java 7 % · Spark 6.5 % · Docker 6 % · GCP 6 % · Snowflake 6 % · Fabric 6 % · Kubernetes 6 % · SAP BW/BO 5 % · scikit-learn 4 % · PyTorch 4 % · Tableau 3 % · Qlik 3 % · pandas 3 % · dbt 3 % · A/B testing 3 % · regression 1 % · causal inference 1 %.
Per family: T14 / docs/market-guide.md §5. Styria (58) vs rest (661), indicative: Python 50/34, Azure 34/18, cloud 41/28, ETL 34/21, Databricks 19/11, Git 19/9, Excel 12/18, Power BI 14/19, statistics 5/14.
Co-occurrence: SQL+Python 24 % of ads (59 % of SQL ads mention Python); SQL+Power BI 12 % (64 % of Power BI ads mention SQL); Azure+Databricks 9 %; Power BI+DAX 3 %; dbt+SQL 3 %. Top stacks: ETL+Python+SQL 12 %, Cloud+Python+SQL 12 %, AI+GenAI+Python 11 %, Visualisation+Power BI+SQL 10 %, Azure+Python+SQL 10 %.
Business context: consulting 31 %, requirements/BA 29 %, finance/controlling 25 %, project management 21 %, manufacturing 20 %, public/research 19 %, SAP 19 %, banking/insurance 17 %, sales 16 %, risk 12 %, marketing 10 %, CRM/customer/web analytics ≤ 7 %.
Soft (indicative): teamwork 66 %, self-organisation 63 %, communication 63 %, analytical thinking 55 %, stakeholder wording 55 %.

## 6. Language findings (T07, T07e)

* German requirement (n 719): required 8.5 % + level-stated 31 % = **40 %**; preferred 12 %; mentioned 6 %; not mentioned 41 %; explicitly not needed 0.3 %. Level wording bucketed as C1-equivalent in 36 % of all ads — but that bucket is mostly "sehr gut/very good" (172 ads) plus "verhandlungssicher/fluent" (56) and explicit C1 (30); B2/"gut" 12 %; native 1 %.
* Ads written in English 24 % (data science 44 %, data analytics 23 %, data engineering 22 %, governance 20 %, business analysis 17 %, BI 8 %); Styria 13 of 58 (22 %). **English-written ≠ German-free:** 19 % of English ads still state a German requirement and 19 % call German an advantage.
* German required/level-stated by family: BI 51 %, business analysis 44 %, data analytics 42 %, governance 40 %, engineering 36 %, data science 33 %. Styria 28 of 58 (48 %) vs 39 % elsewhere.
* Addressable-set scenarios (T07e) — bracketing readings, not measurements of what a candidate can obtain: English-written & no stated German requirement = 141/719 nationally (20 %), **8/58 Styria**, 86/349 Vienna; no explicit German requirement (silence included) = 434/719, 30/58 Styria; not requiring C1-equivalent = 512/719, 37/58 Styria. Data science 55/157 English-no-stated-German; data analytics 20/107.
* English: level-stated 32 %, required 8 %, preferred 15 % — rarely the binding constraint.

## 7. Technology findings (T05, T06)

Microsoft-centred: Azure 19 % vs AWS 9 % vs GCP 6 %; Power BI 18 % vs Tableau 3 %; Databricks 12 %, Fabric 6 %, Snowflake 6 %. Python libraries almost never named. Styrian ads lean engineering (Python/Azure/ETL/Databricks/Git/CI-CD above national, Excel/Power BI/statistics below).

## 8. Salary findings (T09; advertised minimums, annual gross, monthly × 14)

79 % of ads state a figure; only 15 % a range; 81 % of figures are a single collective-agreement minimum; 53 % mention overpay; 10 % "all-in"; 9 % bonus. Median advertised minimum: data engineering €55.4k, data science €55.4k, business analysis €55.0k, BI €52.6k, data analytics €47.8k, governance €45.5k, marketing analytics €42.0k. Titles: Data Architect €60.0k, ML/AI Engineer €56.7k, BI Developer €56.5k, Data Scientist €52.2k, Data Analyst €47.8k, BI Analyst €47.5k, Marketing/CRM Analyst €42.0k. Seniority: intern €35.7k, junior €42.0k, unlabelled €52.2k, senior €60.0k, lead €60.1k (stated upper ends up to €95k median). Styria €53.2k (n 49), Vienna €55.4k (272). Skills: Databricks/GenAI €60k, cloud €58k, Azure €57.4k, Python €55.4k, SQL €53.9k, Power BI €49.0k, Excel €43.7k. External anchors (docs/salary-context.md): AMS entry range Data Scientist €2,800–4,350/month; karriere.at "Analyst" €2,640–4,400/month. **These are legal floors on ads; actual compensation is not measurable here.**

## 9. Education & certification findings (T11, T11e)

Degree wording: required 32 %, preferred 2.5 %, mentioned only 30 %, none 35 %; "or equivalent" 33 %; Master 10 %, PhD 2 %, HTL/Matura 17 %; fields: informatics 38 %, engineering 33 %, business 26 %, data science 17.5 %, statistics/maths 12.5 %, marketing 2 %. Degree-required wording: data analytics 38 %, data science 34 %, BI 33 %, engineering 25 %. Certifications: any wording 13 %; specific ≤ 3 % each even after adding exam codes (IREB/IIBA 3 % in business analysis, Scrum/PM 1 %, ITIL 1 %, Azure 0.3 %, Google 0.3 %; none for Tableau/Databricks/Power BI/AWS).

## 10. Seniority & work model (T08, T10, T12)

Titles: unlabelled 57.5 %, senior 19 %, lead/head 13.5 %, intern 6 %, junior 4 %. Years stated in 19 % of ads: senior median 5 (IQR 4–5), lead 4, unlabelled 3 (2–5), junior 2. Hybrid/home-office mentioned 53 % (explicit hybrid 27 %), on-site 5 %, fully remote 2 %, silent 40 %; engineering 62 %, analysts 43 %, marketing 80 % (n 24); Styria 32 of 58. Full-time 85 %; internships 6 %; temporary/contract 10 %.

## 11. Official trend (AMS JobBarometer, JB01–JB05)

"Data Scientist (m/w)" class, online ads per year: Austria 3,049 (2020) → 5,032 (2022) → 3,471 → 2,680 → 2,207 (2025), −28 % vs 2020; Vienna 811 → 1,809 → 935; Upper Austria 336 → 885 → 299; **Styria 224 → 423 → 300 (+34 % vs 2020)**. Related classes 2025: Datenbankentwickler 1,198 (−40 %), Wirtschaftsinformatiker 1,307 (−35 %), Systemanalytiker 731 (+84 %). AMS 2026–28 outlook "positiv" everywhere; fastest-growing competencies: programming languages (+2.1 pp), communication (+1.2 pp). Unit = AMS occupation class per year, not our titles.

## 12. Adjacent demand (T16, EURES full-text sweep)

In Styria's AMS feed, Python appears in 53 ads (83 % under non-data titles), SQL in 81 (88 % non-data), Power BI in 21 (100 % non-data), Excel in 182. Data skills are demanded far more widely than data titles — entry channels through controlling, engineering and marketing roles exist (AMS feed only, three regions).

## 13. Major career pathways (docs/career-map.md, D01/D02)

Decision-matrix ranking (default weights): 1 data_engineering, 2 data_science, 3 data_analytics, then marketing_analytics, business_analysis, governance, BI. Data analytics is 3rd under all four weightings; engineering and science swap 1st/2nd (science leads under language-first weights). **No family is "robust"** by the framework's rule because every Styrian family count is below 30. Skill overlap (V5) is the share of a family's 15 most-mentioned skills that are in the profile's self-declared have/developing lists: data analytics 13 of 15, marketing analytics 12 of 15, governance 10, BI 9, business analysis 8, data science 7, data engineering 7 — an ordinal indicator, not a fit probability. Evidence-derived sequence for this profile: **data/business analytics as entry family → applied data science as second step; marketing analytics as domain angle (tiny, Vienna/hybrid); BI/Power BI as tool angle (highest German requirement); data engineering only via the SQL/modelling end.**

## 14. Identified gaps

Near-term (developing, ≥ 10 % of ads): SQL, Python, data-quality/ETL practice, Power BI + data modelling, applied GenAI, REST basics, Git, statistics made explicit.
Structural: **German at a demonstrable B2/C1** — the observation is that stated German requirements exclude the profile from most Styrian ads (8 of 58 are English-written without a stated requirement; 30 of 58 state none; 37 of 58 do not state C1-equivalent). This is an observed *requirement* pattern, not evidence that German proficiency causes hiring success. Also structural: Azure/Databricks/CI-CD platform engineering; ML-engineering depth; informatics/engineering degree wording; industrial domain knowledge.
Already have: stakeholder/business/communication (55–63 % of ads), finance/sales/marketing context, Excel/dashboards, seniority, experimentation (rare edge: A/B testing 3 % overall, 4 of 24 marketing-analytics ads).

## 15. Learning priorities (D04)

NOW: SQL; Python for data; data-quality/governance practice; ETL/ELT basics; applied statistics. NEXT: Power BI + dimensional modelling; applied GenAI/LLM; REST/APIs; Git. LATER: Azure fundamentals + one Databricks/Fabric project; CI/CD. DO NOT PRIORITISE (low Austrian evidence): Tableau, Looker, Qlik, GCP/BigQuery, Spark/Kafka, Java/Scala, Kubernetes/MLOps, deep-learning frameworks, vendor certifications, PhD.

## 16. Project implications (career-map §8)

Build: (1) SQL + Power BI dashboard on a modelled star schema (marketing/e-commerce); (2) Python ETL pipeline into a warehouse with tests, Git, CI; (3) experimentation/causal analysis of a marketing or product change; (4) forecasting or churn/CLV model on business data; (5) applied RAG/LLM assistant over business reports. Avoid Tableau, streaming demos, deep-learning showcases, certification labs.

## 17. CV / LinkedIn / GitHub vocabulary (career-map §9)

Search & headline titles: Data Analyst, Business Analyst, BI Analyst/Business Intelligence, Data Scientist, Analytics, Reporting, Controlling (data-heavy). Keywords (employer wording, by frequency): SQL, Python, Power BI, Excel, Datenanalyse/Data Analytics, Dashboard/Reporting, Datenqualität/Data Governance, ETL, Azure, Machine Learning, KI/AI, Statistik, Datenmodellierung, Stakeholder/Fachbereich, Kommunikationsstärke, analytisches Denken, selbstständig; domain: Controlling, KPIs, Forecast, Vertrieb, CRM, E-Commerce, Kundendaten, Segmentierung, Kampagnen. State German level with CEFR.

## 18. Methodology in one paragraph (docs/methodology.md)

Five sources queried Austria-wide with 45 title keywords on one day (no login/CAPTCHA/paywall bypass; StepStone/Indeed/hokify blocked and excluded); raw responses stored verbatim (private); one row per source posting; rule-based title normalisation into families (config/role_taxonomy.json, precision measured in Q03c); geography from explicit fields/NUTS-3/text; salary from structured fields or text near salary words (monthly × 14, plausibility bounds, minimum vs range labelled); language requirements from context windows; degree wording in four strengths; skills from a ~260-item bilingual controlled vocabulary; union-find dedupe; statistics on canonical core rows with Wilson CIs; k-means/NMF as descriptive archetypes; AMS JobBarometer parsed from HTML for yearly counts; decision matrix = transparent weighted sum with sensitivity (docs/decision-framework.md).

## 19. Source coverage & confidence (docs/data-quality.md, docs/limitations.md)

Robust: family/title ranking; top-10 technology ranking and levels; German/English split; certification and PhD rarity; Vienna dominance; advertised floors by family/seniority; JobBarometer trend and Styria share. Tentative: every Styria-only figure (n 58); marketing/product analytics profiles (n ≤ 24); remote-day norms (6 ads); anything about StepStone-only employers; business_analysis and data_governance composition (precision 76 % / 64 % strict). Not measured: hiring outcomes, negotiability of language requirements, extraction recall, actual pay.

## 20. Limitations to keep in mind when advising

One-day stock, not yearly flow; title-based inclusion misses data-heavy non-data titles (§12); 19 % of core postings have no named employer; salary = legal minimum; German "not mentioned" in German-written ads usually implies German; "C1-equivalent" mostly means "sehr gut"; small Styrian cells; posting ≠ vacancy ≠ hire; no causal claims about language or any skill.

## 21. Publication status, data boundary and update procedure

* **Public repository** (GitHub, MIT code / CC BY 4.0 documents and aggregates): code except the posting collectors, configs, schemas, docs, decision documents, figures, aggregated tables, JSON summaries. **Private only:** `data/raw`, `data/processed`, `data/external`, logs, the six posting collectors, per-posting tables with text or URLs. See `PUBLICATION_DECISION.md` and `docs/legal-and-publication-audit.md`.
* **Collection restrictions found in the audit:** all five posting sources restrict automated extraction in their terms (EURES reserves API extraction to EURES partners; karriere.at/jobs.at forbid "automatisierte Auswertung"; LinkedIn's User Agreement and robots.txt forbid scraping of `/jobs-guest/`; willhaben's robots.txt disallows `/jobs/suche` and its AGB reserve TDM). The 2026-09-16 collection is retained privately; **an agent must not re-run the LinkedIn or willhaben collectors, and should treat re-running the EURES/karriere.at/jobs.at collectors as requiring the owner's explicit decision** (DECISION_LOG D-013). Permitted refresh paths: AMS JobBarometer (`collect_jobbarometer.py`), AMS open-data aggregates, or a permission request to the sources.
* **Update procedure:** after any new collection, run steps 2–4 of README → Reproduction, then `python src/reporting/digest.py`, then update the numbers in `docs/market-guide.md`, `CAREER_DECISION_MAP.md` and this file from the digest, and record rule changes in `DECISION_LOG.md`. Re-run `src/analysis/precision_audit.py` if the taxonomy changes and re-label the sample.
