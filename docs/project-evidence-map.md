# Project evidence map (portfolio architecture from evidence)

Per target role family: what employers require (Layer 1, T14/T02), what the observable candidate supply shows (Layer 2, C04/C10b/C18b/C17), which evidence is common and which is rare, and where a public project would be both relevant and unusual (DS10, DS09). Machine-readable twin: `outputs/project_evidence_map.json`. No number of projects is prescribed; the observable median is 2 projects (1 substantive) per data-signal account and 1 per bio-declared account (C16).

**Cross-family evidence facts (P_data, projects):** common formats — notebooks (43 % of projects), Python source/package (41 %), licence (34 %), data included (30 %), environment files (29 %); rare — SQL files (1.2 %), deployed apps (6.5 %), pipelines (7 %), dashboards (8 %), APIs (9 %), Docker (9 %), CI (11 %), tests (12 %). Common README sections — how-to-run 66 %, methodology 51 %, data 42 %; rare — results 26 %, limitations 12 %, business context 11 %. Capabilities demanded but rarely project-demonstrated — SQL (41 % of ads / 10 % of candidates), data quality (31 % / 5 %), requirements/BA (29 % / 1 %), warehouse/modelling (25 % / 2 %), cloud (35 % / 12 %), Azure (19 % / 3 %), Power BI (19 % / 2 %), Excel (18 % / 2 %), Databricks/Spark (14 % / 3 %).

## Data analytics

* **Employer requirements (107 ads; Styria 11).** Visualisation 64 %, Excel 47 %, SQL 38 %, Power BI 34 %, Python 26 %; finance/controlling, sales and marketing contexts; German required/level-stated 42 %; degree wording required 38 %; median advertised floor €47.8 k.
* **Candidate supply (129 bio-declared; Styria 7; 1.0× demand).** Python 50 %, visualisation 40 %, Jupyter 39 %, **SQL 26 %**, pandas 22 %, JavaScript 19 %, statistics 17 %, ML 17 %; education wording Master 15 %, student 12 %; certificates ≤ 5 %.
* **Common candidate evidence.** Notebook analyses; project topics classification 13 %, NLP 10 %, EDA 9 %, sales 9 %, marketing 8 %, customer 7 %, regression 7 %, forecasting 7 % (C18b).
* **Rare candidate evidence.** SQL files, Power BI/Tableau models (Power BI 3 % of candidates), star schemas, business-context READMEs, dashboards with a stated question.
* **Potential evidence gaps.** SQL, data quality, Power BI/dashboarding with modelling, Excel-to-SQL migration stories, business framing.
* **Suggested evidence categories.** A SQL-first analysis over a modelled dataset with the questions and results in the README; a Power BI (or Streamlit) dashboard with screenshots, the data model and the KPI definitions; one decision readout (experiment/forecast) on business data with limitations.

## Data science

* **Employer requirements (158 ads; Styria 13).** Python 73 %, ML 55 %, GenAI 53 %, cloud 48 %, SQL 36 %, Azure 34 %, statistics 29 %; 44 % English-written; 34 % degree-required; floor €55.4 k.
* **Candidate supply (638 bio-declared; Styria 38; 3.3× demand; 17 % students).** Python 67 %, Jupyter 52 %, ML 43 %, visualisation 39 %, Bash 38 %, AI 37 %, JavaScript 34 %, research context 26 %, R 21 %.
* **Common candidate evidence.** ML notebooks: classification 15 %, NLP 14 %, LLM apps 9 %, CV 7 %, healthcare 6 %, clustering 5 % of their projects; ML projects have the best README structure (results 38 %, methodology 68 %, metrics 34 %).
* **Rare candidate evidence.** SQL (project 9 %), cloud deployment (Azure 3 %), data-quality layers, business decision framing (business context 16 % in ML READMEs), evaluated LLM systems (evaluation 1.3 % of projects), causal/experimental readouts (< 1 %).
* **Potential evidence gaps.** SQL, cloud, statistics stated explicitly, business framing.
* **Suggested evidence categories.** A model with baseline, evaluation and a stated decision; the same model deployed as a small API or app on a cloud free tier; an experimentation/causal readout; an evaluated RAG over business documents.

## Data engineering / analytics engineering

* **Employer requirements (160 ads; Styria 20, the largest Styrian family).** SQL 69 %, ETL 60 %, Python 55 %, cloud 45 %, Azure 38 %, modelling 38 %, CI/CD 34 %, Databricks 29 %; German 36 %; floor €55.4 k.
* **Candidate supply (58 bio-declared; Styria 4; 0.3× demand).** Python 53 %, Jupyter 38 %, Bash 29 %, JavaScript 29 %, visualisation 28 %, SQL 28 %, Java 21 %, ETL 19 %, Docker 19 %.
* **Common candidate evidence.** Their projects: ETL 18 %, warehouse modelling 17 %, infrastructure 15 %, NLP 10 %, orchestration 8 %, streaming 7 %.
* **Rare candidate evidence.** dbt (1 % of candidates), Airflow (2.6 %), Databricks (1 %), warehouse modelling (2.4 % project-demonstrated), tests+CI+package together (1.8 % of projects), data-quality tests (5 %), Azure components (3 %).
* **Potential evidence gaps.** Everything the family's ads list except Python: SQL, ETL with tests, modelling, Azure/Databricks, CI/CD.
* **Suggested evidence categories.** An ingestion pipeline with schedule, retries, data checks and a run log; a dimensional model (dbt or SQL) with documented grain; one cloud-deployed component with cost/architecture notes; GitHub Actions running the tests.

## BI

* **Employer requirements (85 ads; Styria 5).** Visualisation 86 %, SQL 52 %, Power BI 51 %, data modelling 33 %, SAP BW 28 %; German required 51 %, English ads 8 %; floor €52.6 k.
* **Candidate supply (15 bio-declared; Styria 3; 0.15× demand).** Visualisation 47 %, SQL 47 %, Python 40 %, Power BI 33 %, DAX 13 %. The BI supply is essentially invisible on GitHub.
* **Common candidate evidence.** Their few projects: LLM apps 19 %, customer 12 %, sales 12 %.
* **Rare candidate evidence.** Power BI files/models, DAX, SAP BW anything, star schemas, KPI definitions.
* **Potential evidence gaps.** All of the family's core tools (they leave no code trace).
* **Suggested evidence categories.** A repository holding the data model, the DAX measures, screenshots and a KPI dictionary for a published report; a SQL layer feeding it; a short case study on the business questions answered.

## Business analysis

* **Employer requirements (120 ads; Styria 4).** Requirements/BA 82 %, project management 51 %, consulting 37 %, SAP 27 %; AI wording 24 %, visualisation 17 %, Excel 14 %, SQL 13 %; German 44 %.
* **Candidate supply (21 bio-declared; 0.14× demand).** Requirements wording 86 %, visualisation 24 %, JavaScript 24 %, consulting 19 %.
* **Common / rare evidence.** Almost no public artefacts; requirements work is not a repository. Rare evidence that maps to the family: a requirements/case-study document alongside a data project; BPMN/user stories; a KPI dictionary.
* **Suggested evidence categories.** Case studies and documentation rather than code; SQL and dashboards as secondary proof.

## Data governance

* **Employer requirements (65 ads; Styria 5).** Data quality/governance wording, master data, SAP; German 40 %.
* **Candidate supply (7 bio-declared).** Data governance wording 71 %, Python 57 %.
* **Rare evidence that maps.** Validation rules and data-quality tests, lineage/catalogue notes, a documented data model — < 5 % of candidates show any of these.

## Marketing analytics / product analytics

* **Employer requirements (24 + 1 ads; 0 Styria).** Marketing/CRM/web analytics context, SQL, Python, Excel, Power BI, GA; A/B testing in 4 of 24 marketing ads; 80 % hybrid; German 33 %; floor €42 k.
* **Candidate supply (2 + 2 bio-declared).** As a *project domain*: 273 marketing/customer/e-commerce projects by 192 accounts (11 % of P_data), methods clustering 71, classification 59, experimentation 12; 29 with SQL+Python, 25 with Power BI/Tableau.
* **Common candidate evidence.** Customer segmentation / churn classification notebooks on public datasets.
* **Rare candidate evidence.** Experiment or causal readouts on marketing data (17 accounts), attribution/MMM, funnel/retention/cohort analyses (< 1 % of projects), SQL-based marketing analytics with a business decision.
* **Suggested evidence categories.** A marketing/customer dataset project framed as a decision (campaign, pricing, retention) with an experiment or causal readout, SQL over a modelled schema and a dashboard — the combination shown by fewer than 20 public Austrian accounts.

## AI / LLM applications (adjacent to data science)

* **Demand.** GenAI wording 16 % of core ads; 311 adjacent AI-software-engineering titles.
* **Supply.** LLM-app projects 10 % of projects, RAG 3 %, agents 2 %; LLM-builder cluster 175 accounts; evaluation 1.3 %.
* **Rare evidence.** Evaluated systems over business documents with a stated use case; cost/latency notes; anything beyond a chat demo.

## How to use this map

Pick the family (or two) being targeted; take the "potential evidence gaps" row; choose the project category whose demanded capability is *least* demonstrated by the pool *and* feasible for the profile (`docs/profile-specific-demand-supply-analysis.md` §3); write the README in the minority pattern (question → data → method → result → limitation → decision → author context). Re-run this map after the next collection; the gaps move.


<!-- BQ21_evidence_gap:start (figure generated by src/analysis/make_visual_layer.py - do not edit by hand) -->
**Q. Where is a month of portfolio work worth most - what is demanded often and demonstrated rarely?**

SQL (41% of ads vs 10% of candidates with project evidence), data quality/validation, dimensional modelling and Azure pipelines sit furthest below the diagonal among the capabilities GitHub can actually see - and business framing sits with them. Power BI, Excel and SAP are equally demanded but cannot be closed with public code.

[![BQ21_evidence_gap](../outputs/figures/BQ21_evidence_gap.png)](../outputs/figures/BQ21_evidence_gap.png)

<sub>**Figure BQ21** · correlation shown as `scatter` (bivariate-simple) · built from `DS10_demand_supply_capability_evidence.csv` · units: share of ads / share of candidates. **Read with:** Two universes, one taxonomy: the axes are not the same denominator and the diagonal is a reading aid, not an identity. A capability marked not-observable is invisible to this measurement.</sub>
<!-- BQ21_evidence_gap:end -->

