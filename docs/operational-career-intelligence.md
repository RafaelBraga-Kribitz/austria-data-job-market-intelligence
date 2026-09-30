# Operational career intelligence (Layer 3 → practice)

Translates the demand × supply evidence into operational questions. Every line is traceable: (T*) Layer 1 tables, (C*/DS*/O*) Layer 2/3 tables in `outputs/tables/`, or the JSON in `outputs/`. Market-neutral: it says what the *observable* Austrian pool commonly and rarely shows against what ads mention; the profile-specific reading is in `docs/profile-specific-demand-supply-analysis.md`. It does not write CVs, headlines or READMEs — it is the evidence those artefacts should be built from.

## 1. Profile

**Which titles should be tested?** Titles that ads use *and* that few public candidates declare are where a title is not competing with 486 identical bios: Data Analyst (77 ads / 124 bios, 1.3×), Data Engineer (134 / 55), Business Analyst (120 / 21), BI Analyst / BI Developer (32+33 / 15), Analytics Engineer (5 / 3). "Data Scientist" is the most crowded label (79 ads / 486 bios, 5×) and "Machine Learning / AI Engineer" the second (76 / 140). "Marketing Data Scientist" (2 ads / 0 bios) and "Product Analyst" (1 / 2) are not searchable titles in Austria (DS02).

**Which skills should appear prominently?** In employer frequency order (T05) with the public-supply reading in brackets: SQL (rarely shown: 16 % any / 9 % project), data visualisation & dashboards (common), Python (very common), data quality/governance (rare: 8 %), cloud/Azure (rare: 11 % / 5 %), ETL/ELT (rare in projects: 11 %), Power BI (rare: 3 %), Excel (rare: 4 %), data modelling (rare: 1 %), machine learning (common), GenAI/LLM (common), statistics (moderate). The skills that are demanded *and* rare on the supply side carry more information per word than those everybody lists (DS03, DS10).

**Which technologies should be emphasised?** Those the ads name and public candidates seldom evidence: SQL, Azure, Databricks, Power BI, data modelling/warehouse, CI/CD. Those that are everywhere in public code and rarely in ads (Jupyter 54 % vs 4 %; JavaScript 42 % vs 4 %; PyTorch 18 % vs 4.5 %; Docker 21 % vs 6 %) do not differentiate (DS04).

**Which capabilities need evidence?** DS10 "demanded, rarely project-demonstrated": SQL, data quality/governance, data warehouse/modelling, Azure, Databricks/Spark, Power BI, Excel (the last three cannot be shown as code — show models, screenshots, DAX). Also business-framing: project management/consulting wording in 44 % of ads and stakeholder/communication in 80 % — not observable on GitHub, hence the README/case-study sections are the only public carrier.

## 2. Projects

**What should the next project demonstrate?** The intersection of high demand and low public evidence (DS10, C21): (1) SQL over a modelled schema (star schema/dbt) with data-quality checks — demanded by 41 % / 31 % / 25 % of ads, demonstrated by 10 % / 5 % / 4 % of candidates; (2) a documented pipeline with tests and CI into a warehouse — ETL 22 % of ads, pipeline-format projects 7 %, CI + tests + package together 1.8 % of projects, warehouse modelling 2.4 % of candidates; (3) a dashboard (Power BI/Streamlit) with a business question and screenshots — dashboards 38 % of ads, dashboard-format projects 8 %, dashboard links in 1.7 % of READMEs; (4) a decision readout (experiment/forecast/causal) on business data — < 1 % of projects each. A further ML notebook adds nothing the pool lacks (ML projects 23 % of data repos).

**What project formats are common?** Notebook-only (22.5 % of projects; notebooks in 43 %), Python source/package layouts (41 %), licence files (34 %), included data (30 %), environment files (29 %), web apps (13 %), reports/slides (13 %) (C17, C17b).

**Which formats are uncommon?** SQL files (1.2 %), R Markdown/Quarto (3 %), model artefacts (6 %), deployed apps (6.5 %), pipelines (7 %), dashboards (8 %), Docker (9 %), APIs (9 %), CI (11 %), tests (12 %), tests+CI+package together (1.8 %) (C17, C17b).

**What project structures recur?** Install → usage → features → project structure; data → methodology → results in ML projects (results 38 %, methodology 68 %); business context almost never (7–17 % by archetype) (C19d, C19e).

**How many projects are typically visible?** Data-signal accounts: median 2 projects (p90 8), 17 % none; substantive: median 1, 38 % none; bio-declared accounts: median 1, 36 % none. Two or three substantive, documented projects exceed the median of the observable pool (C16, C14b). No number is prescribed: the evidence says depth and business framing are rarer than count.

**What documentation patterns exist?** 66 % how-to-run, 51 % methodology, 42 % data, 26 % results, 12 % limitations, 11 % business context; results *and* limitations together 5.6 %; a reproduce command 58 %; images 48 %; metrics words 21 %; business terms 22 % (C19, C19c).

## 3. GitHub

**What repository structure is common?** Notebooks and/or a `src` package with `requirements.txt`, `LICENSE`, a `data` folder; `README.md` with installation/usage headings (C17, C19e).

**What engineering evidence is rare?** Tests (12 % of projects; 25 % of candidates have one project with tests), CI (11 % / 22 %), Docker (9 % / 19 %), APIs (9 % / 22 %), pipelines (7 % / 17.5 %), model artefacts/MLflow (6 %), tests+CI+package in one project (1.8 %) (C15, C17).

**What documentation is common?** Software-style READMEs; median 3,257 characters, 8 headings; 48 % have ≥ 4 detected sections (C19c).

**What testing/CI evidence exists?** Mentions of tests/CI in 14 % of documented READMEs; CI workflows in 11 % of projects, tests in 12 %; as a capability, 24 % of data-signal candidates show CI/CD or tests in a substantive project (C11); production-style applications (Docker/tests/CI/app) are 5 % of data repositories and 14 % of candidates own one (C14c, C19).

**Activity signals employers could see:** 65 % of data-signal accounts pushed in the last 12 months; 44 % of data repositories are older than three years; 67 % have no stars (C14, C14d/e). Recency is a cheap differentiator.

## 4. LinkedIn (dark slot; GitHub-side proxies only)

**What terminology is common?** Not observable from LinkedIn itself (D-018). On GitHub, bio openings are highly fragmented (574 distinct phrases among 764; "data scientist" 6 %, "data science student" 2 %, "data analyst" 2 %, "ai engineer" 2 %, "machine learning engineer" 1.4 %) (C02, C04b). Employer titles are concentrated (Data Engineer, Business Analyst, Data Scientist, Data Analyst, ML/AI Engineer = 68 % of ads) (T02b).

**What titles map to employer vocabulary?** The Layer 1 normalized titles (T02b): Data Analyst, Data Engineer, Business Analyst, BI Analyst/Developer, Data Scientist, Machine Learning / AI Engineer, Analytics Engineer, Data Architect. German forms in ads: Datenanalyst:in, Data Engineer (unchanged), Business-Intelligence-Entwickler:in, Datenwissenschaftler:in (rare).

**How do candidates describe transitions?** Rarely and not publicly: 3.4 % of bio-declared accounts use transition wording; prior domains named are business, software, science, statistics; marketing appears in 10 bios with no explicit transition narrative (C22, C22b). Any explicit, well-framed transition story is unusual in the observable pool.

**Cross-links:** 36 % of data-signal accounts link LinkedIn from GitHub, 36 % a custom-domain site, 19 % a GitHub Pages site, 9 % Kaggle, 6 % a blog, 0.6 % Tableau Public (C15).

## 5. CV / ATS

**Which terms are common in demand and supply?** Python, machine learning, data visualisation/dashboards, GenAI/LLM, statistics, cloud, ETL (DS10 quadrant A). Use them; they are membership terms.

**Which terms are important for ATS matching?** The employer wording order from Layer 1 (career-map §9 / AGENT_CONTEXT §17): SQL · Python · Power BI · Excel · Datenanalyse/Data Analytics · Dashboard/Reporting · Datenqualität/Data Governance · ETL · Azure · Machine Learning · KI/AI · Statistik · Datenmodellierung · Stakeholder/Fachbereich · Kommunikationsstärke · analytisches Denken; domain: Controlling, KPIs, Forecast, Vertrieb, CRM, E-Commerce, Kundendaten, Segmentierung, Kampagnen. Layer 2 adds: the *first six* are also the ones public candidates rarely evidence, so a CV line that points to a repository for each is unusual.

**Which capabilities require stronger evidence?** SQL, data quality, modelling, Azure/Databricks, Power BI models, business framing, experimentation readouts (DS10; §1 above).

## 6. Geography, language, seniority, education (operational reading)

* **Geography.** Styria: 58 open ads (engineering 20) vs 56 bio-declared public candidates by resolved location (data science 38, engineering 4, analytics 7, BI 3): engineering-flavoured analyst/BI evidence is the scarcest public evidence relative to Styrian ads; Vienna has the same shape at 6× the size (DS05b, DS13).
* **Language.** Supply side unmeasurable on GitHub (99 % English bios); the Layer 1 constraint stands (Styria 8 of 58 English-written without stated German). State the CEFR level explicitly; the pool does not (DS06).
* **Seniority.** Ads: 32 % senior/lead wording; bios: 10 %, students 17 %. Explicit seniority and business ownership wording is rare in the pool (DS07).
* **Education.** Ads name informatics/engineering; bios name data-science degrees; 69 % of candidates show no education wording. Certificates: ≤ 6 % of candidates, ≤ 3 % of ads per certificate — not a lever either way (DS08).

## 7. Future research this document depends on

Fill the LinkedIn slot (titles, languages with levels, years, transitions); repeat the GitHub collection in 3–6 months for change; log application outcomes; raise the Vienna base-rate cap. Until then, every "rare" above is "rare among Austrian public GitHub accounts".
