# Career map: from the observed market to this profile

Profile (config/profile.json): ~20 years marketing/growth/performance marketing/CRO/experimentation/analytics/automation; English fluent; German A2–B1; Greater Graz; developing Python, SQL, R, statistics, ML, visualisation. This page derives pathways from the tables in `docs/market-guide.md`; the scoring is in `docs/decision-framework.md` and `outputs/tables/D01–D04`. Nothing here is a hiring forecast; "share" means share of ads that mention an item (n = 719 unless stated). Numbers are from the post-audit run (720 core postings, 58 Styria).

## 1. Already-have advantages (what ads repeatedly ask for and the profile already carries)

| Market signal | Evidence | Profile fit |
|---|---|---|
| Business/stakeholder orientation is in more than half of all ads | stakeholder/business-partner wording 55 %, communication 63 %, analytical thinking 55 % (T05_soft) | 20 years of stakeholder-facing marketing work |
| Finance/controlling, sales and consulting contexts dominate analyst ads | finance/controlling, sales and consulting are the top business contexts in data_analytics ads (T14) | commercial/growth background maps onto "business analytics" wording |
| Marketing/CRM/web-analytics wording exists but is scarce as a title | marketing 10 % (71 ads), CRM/customer/web analytics ≤ 7 % of all core ads; cluster 0 (marketing/CRM/customer data) = 11.5 % of postings (T15) | direct domain match for a ~10 % niche, mostly Vienna and hybrid-friendly |
| Excel and dashboards are still the analyst baseline | Excel 47 % and visualisation 64 % of data_analytics ads | present |
| Experimentation is rarely named but is a differentiator | A/B testing 3 % of ads overall, 4 of 24 marketing_analytics ads | rare on the supply side too; a credible edge in product/marketing analytics |
| Seniority is expected, not penalised | 57.5 % of ads unlabelled (median 3 years stated), senior ≈ 5 years; junior labels only 4 % | senior business experience is usable, technical years are what is missing |

## 2. Near-term gaps (frequent in ads, realistically acquirable, already in progress)

| Skill | Share of core ads | In the target families | Status |
|---|---|---|---|
| **SQL** | 40 % (Styria 27 of 58) | data_analytics 38 %, bi 52 %, data_engineering 69 %, marketing_analytics 54 % | NOW – the single most transferable item |
| **Python** | 35 % (Styria 29 of 58) | data_science 73 %, data_engineering 55 %, data_analytics 26 % | NOW – mandatory for data science/engineering, optional for analyst/BI |
| Data quality / governance wording | 31 % | present in every family (44 % in engineering) | NOW – vocabulary and practice (validation, definitions, lineage) |
| ETL/ELT & data modelling | 22 % / 16 % | data_engineering 60 % / 38 %, bi 33 % (modelling) | NOW/NEXT – dimensional modelling + SQL pipelines; not full data engineering |
| **Power BI** | 18 % (Styria 8 of 58) | data_analytics 34 %, bi 51 %, marketing_analytics 33 % | NEXT – the BI tool of the Austrian market; Tableau is 3 % |
| Generative AI / LLM wording | 16 % | data_science 53 %, marketing 25 % | NEXT – applied use (RAG, prompt-based analysis), not model training |
| Statistics named explicitly | 14 % (regression 1 %, causal 1 %) | data_science 29 %, data_analytics 19 % | continue; ads rarely spell methods out, so demonstrate them in projects |
| Git, REST/APIs | 10 %, 12 % | data_engineering, data_science | NEXT – baseline engineering hygiene |

## 3. Structural gaps (frequent in some families; substantial time or formal background)

| Requirement | Evidence | Which paths it affects |
|---|---|---|
| **German at a demonstrable B2/C1** | 40 % of ads state a German requirement; C1-equivalent wording (mostly "sehr gut") in 36 % of all ads, B2 in 12 %; BI 51 %, data_analytics 42 %; Styria 28 of 58 vs 39 % elsewhere; only 8 of 58 Styrian ads are English-written without a stated requirement | Stated requirements exclude the profile from most Styrian analyst/BI ads as advertised; English-written ads are 24 % overall (Styria 13 of 58, data science 44 %). Negotiability is not measured. |
| Azure/Databricks/Fabric platform engineering | Azure 19 % (Styria 20 of 58), Databricks 12 % (Styria 11 of 58), CI/CD 15 %, Fabric 6 % | data_engineering as a primary target (8 of its 15 top skills structural for this profile) |
| ML engineering depth (Docker/Kubernetes/MLOps/PyTorch) | each 4–6 % overall, concentrated in data_science/ML-engineer ads (cluster 4) | ML/AI-engineer titles (76 postings) |
| CS/engineering degree wording | computer science 38 %, engineering/physics 33 % of ads; degree-required wording 32 % (data_analytics 38 %) but "or equivalent" in 33 % | a soft barrier; PhD is 2 %, Master 10 % |
| Industrial domain knowledge (manufacturing, automotive, semiconductors) | operations/manufacturing 20 % of ads; Styrian employers are KNAPP, Magna, Anton Paar, ams OSRAM-type industry | Styrian data engineering/science postings |

## 4. Low-value learning (attractive, weak Austrian evidence)

Tableau (3 %), Looker (2 %), Qlik (3 %), GCP/BigQuery (6 % / 4 %), Spark (6.5 %), Kafka/streaming (7 %), Java/Scala (7 % / <1 %), individual Python libraries as CV items (pandas 3 %, scikit-learn 4 %), vendor certifications of any kind (specific ones ≤ 3 %; data-vendor certificates ≤ 0.3 %), R as a primary language (7 %; 10 % of data_analytics ads), PhD-level credentials (2 %). "Do not prioritise" in D04 means low evidence of Austrian demand, not that the skill is useless.

## 5. Pathways supported by the evidence

```text
Current profile (senior marketing/growth + developing Python/SQL/stats)
 │
 ├─► A. Data Analyst / Business-Analytics (data_analytics, 107 AT / 11 Styria)
 │      fit: highest profile overlap (13 of 15 top skills have/developing), smallest structural gap (2 of 15)
 │      cost: German required/level-stated in 42 %; Excel/Power BI/SQL baseline; advertised floors lowest (median €47.8k)
 │      entry channel: finance/controlling, sales and e-commerce analyst variants (30 of 107 are data-heavy business analysts)
 │
 ├─► B. Marketing / CRM / Web Analytics (24 AT / 0 Styria)  — the domain fit is strong but the market is tiny and Vienna/hybrid
 │      tools named: SQL 54 %, Google Analytics 46 %, Power BI 33 %, BigQuery 25 %, Matomo 25 %; 80 % hybrid mentions; median floor €42k
 │      realistic as: remote/hybrid Vienna roles, or the analytics side of marketing titles (adjacent demand, T16)
 │
 ├─► C. BI Analyst / BI Consultant / BI Developer (85 AT / 5 Styria)
 │      fit: 9 of 15 overlap; German is the highest of all families (51 %) and English ads the rarest (8 %); Power BI + SQL + data modelling
 │
 ├─► D. Data Scientist (158 AT / 13 Styria)
 │      fit: most English-friendly family (44 % English ads; 55 of 157 English without stated German requirement); Python 73 %, ML 55 %, GenAI 53 %
 │      cost: 8 of 15 top skills structural (cloud, CI/CD, MLOps, AWS); degree-required wording 34 %; statistics 29 %
 │      realistic as: "applied/business data scientist" in marketing-, customer- or pricing-heavy teams, not ML engineering
 │
 ├─► E. Data Engineer / Analytics Engineer (160 AT / 20 Styria = Styria's largest family)
 │      fit: 7 of 15 overlap; 8 of 15 structural (Azure, Databricks, CI/CD, ETL tooling); German 36 %; best floors (€55.4k) and hybrid share (62 %)
 │      realistic only via the Analytics-Engineer end (SQL + dbt-style modelling) — but "Analytics Engineer" is 5 postings nationally
 │
 └─► F. Data Governance / Data Manager (65 AT / 5 Styria; half are operational master-data roles) — a possible senior lateral move, thin in Styria
```

Decision-matrix ranking (D01/D02; product analytics excluded, n = 1): data_engineering 1st, data_science 2nd, data_analytics 3rd under default weights; science leads under language-first weights; data_analytics is 3rd in all four. **No family is "robust" by the framework's rule because Styrian counts are all below 30.** The ranking says: engineering scores on Styrian volume, floors and hybrid share, data science on English openness and salary, data analytics on fit; it does not say engineering or science is easiest to enter.

Read together with the evidence: the most defensible sequence is **A (data/business analytics) as the entry family, using B (marketing analytics) as the domain angle and C (BI/Power BI) as the tool angle, with D (applied data science) as the second step once Python/statistics are demonstrable**, and E as an option only through the SQL/modelling end. This is derived, not assumed: A has the smallest gap, D has the largest English-language market, E has the largest Styrian market but the largest structural gap.

## 6. Geography and language decisions

* Graz alone holds on the order of 30–50 open core postings at any time (34 in Graz city, 52 in the commuting area on 2026-09-16); Vienna holds ~7× that. Styria's official yearly flow is ~300 "Data Scientist"-class ads and rising relative to 2020 while Austria as a whole fell 28 %.
* Stated German requirements: 8 of 58 Styrian ads are English-written with no stated requirement; 30 of 58 state none; 37 of 58 do not state C1-equivalent (T07e). Nationally 141 / 434 / 512 of 719. A demonstrable B2/C1 therefore removes the most frequently stated non-technical barrier in Styrian ads — larger than any tool — but the data cannot say how often stated levels are negotiable or how German changes hiring odds.
* Hybrid is the norm in the ads that say anything (53 % mention hybrid/home office); fully remote is 2 %. A Graz base with a Vienna employer is plausible only for hybrid roles with occasional presence; the ads rarely state days.

## 7. Learning roadmap (D04, evidence-derived)

| Bucket | Items | Evidence rule |
|---|---|---|
| **Now** | SQL; Python (pandas-level data work); data-quality/governance practice; ETL/ELT basics; statistics applied in projects | share ≥ 20 % and already developing |
| **Next** | Power BI (incl. data modelling, DAX basics); applied GenAI/LLM use; REST/API basics; Git | share 10–20 %, developing |
| **Later** | Azure fundamentals + one Databricks/Fabric project; CI/CD basics; cloud data-warehouse concepts | share ≥ 10 % but structural for the profile; matters for Styrian engineering-flavoured ads |
| **Do not prioritise** | Tableau, Looker, Qlik, GCP/BigQuery, Spark/Kafka, Java/Scala, Kubernetes/MLOps, deep learning frameworks, vendor certifications, PhD | share < 8 % or certification demand ≤ 3 % |

## 8. Project-selection intelligence (what ads actually ask for)

| Project type | Requirements it demonstrates (share of core ads) | Families it supports | Gap it fills |
|---|---|---|---|
| **SQL + Power BI business dashboard on a modelled star schema** (e.g. marketing/e-commerce funnel) | SQL 40 %, visualisation 38 %, Power BI 18 %, data modelling 16 %, data quality 31 % | data_analytics, bi, marketing_analytics | the most frequently requested analyst combination (stack "Visualisation + Power BI + SQL", 10 %) |
| **Python ETL/ELT pipeline into a warehouse (DuckDB/Postgres → Azure or Databricks community)** | ETL 22 %, Python 35 %, SQL 40 %, Azure 19 %, Git 10 %, CI/CD 15 % | data_engineering, data_science | the Styrian engineering flavour (Python 29, Azure 20, ETL 20 of 58 Styrian ads) |
| **Experimentation/causal analysis of a marketing or product change** (A/B test design, uplift, incrementality) | statistics 14 %, A/B 3 %, causal 1 %, customer analytics ≤ 7 % | marketing_analytics, applied data science | rare in ads *and* in candidate pools — differentiator, not volume play |
| **Forecasting/segmentation on business data** (demand, churn, CLV) | forecasting 6 %, segmentation 6 %, ML 16 %, Python 35 % | data_science (applied), data_analytics | bridges marketing domain and ML wording |
| **Applied GenAI/LLM assistant over business data (RAG on reports)** | GenAI/LLM 16 %, Python 35 %, REST 12 % | data_science, bi | fastest-growing wording; demonstrates modern tooling without ML-engineering depth |
| This repository itself (acquisition, normalisation, analysis, audit) | Python, SQL-like transformations, data quality, documentation, methodology | data_analytics, data_engineering | already exists; the public version is citable |

Do not build: Tableau dashboards, Spark/Kafka streaming demos, deep-learning image models, certification-driven cloud labs without a data product.

## 9. CV / LinkedIn / GitHub implications (terminology employers use)

* Titles to search and to use as headline vocabulary: "Data Analyst", "Business Analyst", "BI Analyst / Business Intelligence", "Data Scientist", "Analytics", "Reporting", "Controlling" (data-heavy), "Marketing Analytics/CRM Analytics" (rare, Vienna). Avoid "Marketing Data Scientist" as a search term (2 postings).
* Keywords with the highest frequency in ads, in employer wording: SQL, Python, Power BI, Excel, Datenanalyse/Data Analytics, Dashboard/Reporting, Datenqualität/Data Governance, ETL, Azure, Machine Learning, KI/AI, Statistik, Datenmodellierung, Stakeholder, Fachbereich, Kommunikationsstärke, analytisches Denken, selbstständig, Teamplayer.
* Domain wording that the analyst market uses: Controlling, Kennzahlen/KPIs, Forecast, Vertrieb, CRM, E-Commerce, Kundendaten, Segmentierung, Kampagnen.
* Language line: state German level honestly with CEFR; ads read levels, and 36 % of all ads use C1-equivalent wording. English-only positioning addresses ~20 % of the national ads and 8 of 58 in Styria as advertised.
* GitHub: two to three finished, documented projects matching the table above beat many notebooks; ads name tools, not libraries.

## 10. What would change these conclusions

See `CAREER_DECISION_MAP.md` → "What would change this map?" (larger Styrian sample, StepStone/Indeed data, longitudinal data, changes in stated German requirements, technology or salary shifts, new title categories, actual interview/hiring outcomes, JobBarometer 2026, a measured extraction audit).
