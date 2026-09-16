# Market guide: the Austrian data-job market as observed on 2026-09-16

Evidence layer for `CAREER_DECISION_MAP.md`. Every number names its table in `outputs/tables/` (T = posting snapshot, JB = AMS JobBarometer, Q = quality, D = decision matrix). Numbers are from the run after the 2026-09-16 audit (DECISION_LOG D-012); the pre-audit run counted 824 core postings and is superseded.

**Denominators used throughout.** "Core postings" = **720** deduplicated canonical postings whose *title* falls into one of eight data role families (T02). Text-derived shares (skills, languages, education, remote, experience) use the **719** core postings with a description > 300 characters (T05 header). Family-level and Styria-level shares carry their own n. A "share" is the share of postings that *mention* an item, never the share that *requires* it. Percentages are rounded; Wilson 95 % intervals are in the tables. Read `docs/limitations.md` before quoting anything as "the market".

**Snapshot, not flow.** Everything in T-tables is the *stock* of advertisements open on one day. It is not a number of jobs per year, not a number of vacancies (one ad may cover several posts, one vacancy may be posted on several boards) and not a number of hires. Yearly *flow* comes only from the AMS JobBarometer (§12).

## 1. Size and sources (T01, T01b, dedupe_summary, market_summary.json)

| Quantity | Value |
|---|---|
| Raw rows collected (5 sources, 45 title keywords, one day) | 12,429 |
| Unique postings after within- and cross-source dedupe | 10,945 |
| Core data-role postings (canonical) | **720** (719 with description) |
| Adjacent: AI-software-engineering titles / other data-ish titles | 311 / 235 |
| Core postings located in Styria / Graz commuting area / Graz city | **58 / 52 / 34** (54 by primary state; 58 incl. multi-site ads) |
| Core postings in Vienna | 350 (343 by primary state) |
| Named employers, Austria / Styria / Graz area | 387 / 32 / 28 |
| Core postings without a named employer (AMS/EURES "siehe Beschreibung") | 140 of 720 (19 %); Styria 10 of 58 |
| In-scope duplicate rate before dedupe | 24.2 % (1,670 rows → 1,266 groups) |

Per source (core canonical after dedupe): LinkedIn 300, EURES/AMS 202, karriere.at 134, jobs.at 58, willhaben 26. 145 of the 720 core groups (20 %) were seen on more than one of our sources; the dominant single-source groups are LinkedIn-only (290) and AMS-only (186), i.e. the professional-network side and the public-employment-service side of the market barely overlap. jobs.at is largely a karriere.at mirror (33 jobs.at+karriere groups). StepStone.at and Indeed.at are absent (blocked), so the corporate white-collar segment is under-covered (docs/limitations.md).

## 2. Role families and titles (T02, T02b, T02c, Q03c)

| Family | Postings | Share of 720 | Styria | Vienna |
|---|---|---|---|---|
| data_engineering (Data Engineer 134, Data Architect/Platform 21, Analytics Engineer 5) | 160 | 22 % | 20 | 80 |
| data_science (Data Scientist 79, Machine Learning / AI Engineer 76, Statistician 3) | 158 | 22 % | 13 | 81 |
| business_analysis (Business Analyst / requirements 120) | 120 | 17 % | 4 | 75 |
| data_analytics (Data Analyst 77, data-heavy Finance/Risk/Ops Analyst 30) | 107 | 15 % | 11 | 42 |
| bi (BI Developer 33, BI Analyst 32, BI Consultant 20) | 85 | 12 % | 5 | 35 |
| data_governance (Governance/Steward/Data Manager 31, Master/Product Data Management 34) | 65 | 9 % | 5 | 23 |
| marketing_analytics (Marketing/Growth/CRM Analyst 22, Marketing Data Scientist 2) | 24 | 3 % | 0 | 13 |
| product_analytics (Product Analyst) | 1 | 0.1 % | 0 | 1 |

Findings. (a) Data engineering and data science are the two largest families and "Data Engineer" (134) is the largest single title; "Data Scientist" (79) and "Machine Learning / AI Engineer" (76) are nearly equal — note that "AI Engineer" titles are counted in the latter. (b) Marketing-analytics and product-analytics *titles* are rare (25 of 720, none in Styria); marketing-analytical work is advertised inside marketing or CRM titles (T16). (c) Half of the governance family is operational master/product-data management (34), not governance proper (31); the split is visible in T02b. (d) 311 AI-flavoured *software* titles ("AI Engineer / Softwareentwickler", "AI Consultant") are reported as an adjacent family, not as data science.

**Measured precision.** A hand-labelled sample of 177 titles (25 per family, Q03c) gave a strict precision of 71 % before and 83 % after the D-012 rule revision (lenient, counting borderline titles as correct: 84 % → 95 %). Remaining weak spots: business_analysis (76 % strict; IT-analyst and process-owner titles) and data_governance (64 % strict; master-data maintenance titles are kept but labelled). Recall is not measured (docs/limitations.md).

## 3. Geography (T03a–T03e, JB05)

* Vienna holds **48 %** of core postings (343 by primary state; 350 incl. multi-site), Upper Austria 17 % (122), **Styria 7.5 % (54; 58 incl. multi-site)**, Vorarlberg 6 %, Lower Austria 6 %, Salzburg 5 %, Tyrol 4 %, Carinthia 3 %; 3 % (22) are Austria-wide/unspecified.
* Inside Styria: Graz city 34, Hart bei Graz 6, Lieboch/Raaba-Grambach 1 each (Graz commuting area 52 of 58), Weiz 3, Liezen 1. Styria's data market is Graz.
* The official yearly series gives Styria a larger share: 300 of 2,207 "Data Scientist"-class ads in 2025 = **13.6 %** (JB05), against 7–8 % in our snapshot. Both are plausible: AMS counts more SME/industrial ads than LinkedIn and our Styrian sample is small. Treat Styria's true share as roughly 8–14 % of the national data market.
* Family mix in Styria (n = 58, indicative): data engineering 20 (34 %), data science 13 (22 %), data analytics 11 (19 %), BI 5, governance 5, business analysis 4, marketing/product 0. Compared with Austria: engineering over-represented (34 % vs 22 %), business analysis under-represented (7 % vs 17 %).
* Platform geography (T03e): LinkedIn and karriere.at are Vienna-heavy; AMS/EURES contributes most Upper-Austrian and Styrian industrial postings.

## 4. Employers (T04, T04a, T04b)

* **Named vs represented.** 580 of 720 core postings name an employer; 140 (all AMS/EURES rows) do not. The 387 unique named employers are therefore a lower bound on employers represented; Styria: 32 named, 10 postings unnamed.
* Concentration is low: the top 10 named employers hold 11 % of named postings, the top 25 hold 20 %. Recruitment agencies account for 4.5 % of named postings.
* Most frequent nationally: Red Bull 10 (Salzburg), Qualysoft 7, Liebherr 7, KNAPP 7 (Styria), Hirebuddy 6 (agency-like platform), KERN engineering careers 6, PwC 5, ÖBB 5 (+5 as ÖBB-Konzern), Accenture 5, then msg, Tieto, smart Energy Services, TOWA, RHI Magnesita with 4.
* Styria (32 named employers, 58 postings): KNAPP 7 (business analysis, data analytics, engineering, science), adesso Austria 4, Tieto 3, CANCOM, niceshops, Anton Paar, Mercedes-Benz G, Magna 2 each, and single postings from Netconomy, KERN, ÖGK, ASE, ams OSRAM, All for One, EPIG, Easelink, Kapsch, Maco, OMNINET, Merkur Versicherung and others. Archetypes: intralogistics/automotive/semiconductor industry, IT consultancies, e-commerce, insurance/health.

## 5. Skills and technologies (T05, T06, T14)

Share of the 719 core postings with description that *mention* the item:

| Tier | Item (share) |
|---|---|
| Core trio | **SQL 40 %** (incl. SQL Server mentions; 37 % without) · **Python 35 %** · data visualisation/dashboards/reporting 38 % |
| Common | generic "AI/KI" wording 38 % · data governance/quality wording 31 % · "cloud" 29 % · ETL/ELT/pipelines 22 % · **Azure 19 %** · **Power BI 18 %** · Excel 18 % · data modelling 16 % · machine learning 16 % · generative AI/LLM 16 % · CI/CD 15 % · statistics 14 % |
| Occasional | Databricks 12 % · REST/APIs 12 % · mathematics 11 % · data warehouse 10 % · Git 10 % · AWS 9 % · **R 7 %** · Java 7 % · streaming 7 % · Spark 6.5 % · MLOps 6 % · Docker 6 % · GCP 6 % · Snowflake 6 % · Microsoft Fabric 6 % · Oracle 6 % · Kubernetes 6 % · SAP BW/BO 5 % · SQL Server 5 % |
| Rare | scikit-learn 4 % · PyTorch 4 % · **Tableau 3 %** · Qlik 3 % · pandas 3 % · dbt 3 % · A/B testing 3 % · Looker 2 % · regression 1 % · causal inference 1 % |

Interpretation. The Austrian data stack is **Microsoft-centred** (Azure 19 % vs AWS 9 % vs GCP 6 %; Power BI 18 % vs Tableau 3 %; Databricks 12 %, Fabric 6 %). Python libraries are almost never named; ads name "Python" and "SQL". Statistical methods are rarely spelled out ("Statistik" 14 %, A/B testing 3 %).

**Co-occurrence (T06, T06b).** SQL and Python appear together in 24 % of postings (59 % of SQL ads also mention Python; 68 % of Python ads mention SQL). SQL + Power BI 12 % (64 % of Power BI ads mention SQL); Python + Azure 14 %; SQL + data modelling 12 %; Python + machine learning 13 % (79 % of ML ads name Python); Python + GenAI 11 %; Azure + Databricks 9 % (80 % of Databricks ads sit in an Azure context); Power BI + DAX only 3 % (15 % of Power BI ads name DAX); dbt + SQL 3 % (dbt is 25 ads). Most frequent three-item stacks: ETL + Python + SQL 12 %, Cloud + Python + SQL 12 %, AI + GenAI + Python 11 %, AI + ML + Python 11 %, Visualisation + Power BI + SQL 10 %, Azure + Python + SQL 10 %. Power BI's strongest partner is reporting/visualisation wording (lift 2.3), not Python.

**Per family (T14).** data_analytics (n 107) = visualisation 64 %, Excel 47 %, SQL 38 %, Power BI 34 %, data quality 28 %, Python 26 %, statistics 19 %, forecasting 18 %, R 10 %. bi (85) = visualisation 86 %, SQL 52 %, Power BI 51 %, data modelling 33 %, SAP BW/BO 28 %. data_science (157) = Python 73 %, ML 55 %, GenAI/LLM 53 %, cloud 48 %, SQL 36 %, Azure 34 %, CI/CD 31 %, statistics 29 %, REST 29 %, AWS 24 %. data_engineering (160) = SQL 69 %, ETL 60 %, Python 55 %, cloud 45 %, data quality 44 %, Azure 38 %, data modelling 38 %, CI/CD 34 %, Databricks 29 %. marketing_analytics (n = 24) = SQL 54 %, visualisation 50 %, Google Analytics 46 %, Excel 38 %, Power BI 33 %, BigQuery 25 %, Matomo 25 %, A/B testing 4 of 24. business_analysis (120) = generic AI 24 %, visualisation 17 %, Excel 14 %, SQL 13 % — a requirements profile, not a tool profile.

**Styria vs rest of Austria (T05_by_styria, n = 58 vs 661; indicative, intervals overlap).** Styrian ads mention Python (50 % vs 34 %), SQL (47 % vs 40 %), cloud (41 % vs 28 %), Azure (34 % vs 18 %), ETL (34 % vs 21 %), Databricks (19 % vs 11 %), Git (19 % vs 9 %), CI/CD (22 % vs 14 %) and GCP (17 % vs 6 %) *more* often, and Excel (12 % vs 18 %), Power BI (14 % vs 19 %), GenAI (12 % vs 17 %) and statistics (5 % vs 14 %) *less* often. Consistent with the family mix: Styria's visible demand is engineering-flavoured.

**Business context (T05_business_domain).** consulting wording 31 %, requirements/business analysis 29 %, finance/controlling 25 %, project management 21 %, manufacturing/operations 20 %, public sector/research 19 %, SAP 19 %, banking/insurance 17 %, sales 16 %, risk 12 %, supply chain 10 %, **marketing 10 % (71 postings)**, CRM/customer/web analytics each ≤ 7 %.

**Soft skills (indicative wording counts).** teamwork 66 %, self-organisation 63 %, communication 63 %, analytical thinking 55 %, stakeholder/business-partner wording 55 %, curiosity/learning 46 %, leadership 15 %.

## 6. Requirement archetypes (T15, clusters.json)

k-means on the binary skill matrix (k = 8 by silhouette; silhouette 0.07 = weak structure) yields readable but overlapping archetypes: (4) Python + GenAI/ML engineering with Docker/Kubernetes/MLOps 16.5 %; (2) Excel/finance/controlling analytics 13 %; (5) requirements/business analysis 13 %; (6) Python + SQL pipelines 13 %; (3) Azure/Databricks/Fabric data platform 12 % (17 % of it in Styria); (0) marketing/CRM/customer-data management 11.5 %; (1) Oracle/SQL-Server data warehouse, public sector 11 %; (7) manufacturing/operations data 9 %. NMF topics agree. These are descriptive groupings, not professions.

## 7. Languages (T07 family, T07e)

* **German requirement (n = 719):** explicit "required" 8.5 % + level stated 31 % = **40 % state a German requirement**; 12 % call it an advantage; 6 % mention it without level; **41 % do not mention German at all**; 0.3 % say it is not needed.
* **Levels.** 36 % of all ads carry wording we bucket as "C1-equivalent": explicit C1 (30 ads), "verhandlungssicher/fließend/fluent" (56), and "sehr gut/very good/excellent" (172). Mapping "sehr gut" to C1 follows common Austrian HR usage but is an assumption; read the bucket as "high level demanded", not as a certified C1. B2/"gut" 12 %, native 1 %; B1 or below is essentially never accepted explicitly.
* **Posting language:** 75 % German, **24 % English** (174 ads). Data science 44 % English, data analytics 23 %, data engineering 22 %, governance 20 %, business analysis 17 %, marketing analytics 17 %, BI 8 %.
* **English-written ads are not German-free.** Of the 174 English ads, 19 % still require/state a German level, 19 % call German an advantage and 55 % are silent. Of the 542 German-written ads, 46 % require/state a level; silence in a German-written ad usually implies German (T07d).
* By family, required-or-level-stated German: BI 51 %, business analysis 44 %, data analytics 42 %, governance 40 %, data engineering 36 %, data science 33 %, marketing analytics 33 % (n 24).
* **Styria (n = 58):** 28 (48 %) require/state a level vs 39 % elsewhere; 21 of those at C1-equivalent; 13 ads (22 %) are English-written; 22 are silent.
* English: 32 % state a level, 8 % "required", 15 % preferred — near-universal, rarely the binding constraint.
* **Addressable-market scenarios (T07e)**, three explicit readings, none of which is "the truth":

| Scope | n | English-written **and** no stated German requirement (German may still be "preferred" or expected) | No explicit German requirement (silence included) | German not required at C1-equivalent |
|---|---|---|---|---|
| Austria | 719 | 141 (20 %) | 434 (60 %) | 512 (71 %) |
| Styria | 58 | **8** | 30 | 37 |
| Graz area | 52 | 6 | 25 | 32 |
| Vienna | 349 | 86 | 205 | 233 |
| data_science | 157 | 55 | 105 | 119 |
| data_analytics | 107 | 20 | 62 | 79 |

## 8. Seniority and experience (T08)

* Title labels (n 720): 57.5 % no seniority word; senior 19 %; lead/head 13.5 %; intern/student 6 %; junior/trainee 4 %. Junior labels are rarest in data engineering (4 %) and most common in marketing analytics (21 %, n 24); data analytics has 5 % junior + 13 % intern.
* Only 19 % of ads (137) state years. Where stated: "senior" median 5 (IQR 4–5, n 29); "lead/head" 4 (3–5, n 26); unlabelled 3 (2–5, n 75); junior 2 (n 5). "Mehrjährig/several years" wording 33 %; explicit entry-level wording 13.5 %. Thresholds of 9+ years: 4 ads.
* Styria (n 58): unlabelled 31, senior 12, junior 6, intern 5, lead 4.

## 9. Advertised salary (T09, docs/salary-context.md)

What the figures are: Austrian ads must state the collective-agreement (KV) minimum; **81 % of parsed figures are a single minimum** (460 of 569), 59 % of core ads mention the KV explicitly and 53 % say they will pay above it ("Überzahlung"). Only 15 % (109) state a range. 10 % mention "all-in" contracts and 9 % a bonus/variable component (not separable from the figure). LinkedIn omits a figure in 41 % of its core ads; AMS/karriere/jobs.at almost always state one. **These are advertised floors, not offers and not pay.** Actual compensation cannot be estimated from this data; third-party context is kept separate in docs/salary-context.md.

* Median advertised **minimum** (annual gross, monthly × 14): data engineering €55.4k (n 132), data science €55.4k (122), business analysis €55.0k (93), BI €52.6k (67), **data analytics €47.8k (83)**, data governance €45.5k (50), marketing analytics €42.0k (21). By title: Data Architect €60.0k (17), ML/AI Engineer €56.7k (56), BI Developer €56.5k (28), Business Analyst €55.0k, Data Engineer €54.5k (112), Data Scientist €52.2k (66), Data Analyst €47.8k (62), BI Analyst €47.5k (25), BI Consultant €47.5k (14), Marketing/CRM Analyst €42.0k (19).
* By seniority label: intern €35.7k (38), junior €42.0k (22), unlabelled €52.2k (336), senior €60.0k (105), lead €60.1k (68; where ranges exist their upper end reaches a median €95k). Data science senior €64k / lead €75k; data analytics senior €50k (n 12) / lead €61.6k (n 9).
* By state: Vienna €55.4k (272), Upper Austria €53.2k (106), **Styria €53.2k (49)**, Salzburg €41.4k (34). English-written ads €55.4k vs German €53.2k.
* By skill mentioned: Databricks / GenAI / lakehouse €60k, cloud €58k, ML €57.4k, Azure €57.4k, Python €55.4k, SQL €53.9k, Power BI €49.0k, Excel €43.7k — engineering/ML wording carries higher floors than reporting wording.
* External anchors: AMS Berufslexikon entry range for Data Scientist €2,800–4,350/month (≈ €39–61k), karriere.at "Analyst" €2,640–4,400/month. Our medians sit inside/above these floors, as expected. Never mix these floors with survey medians.

## 10. Work model (T10)

* 53 % of ads mention some home-office/hybrid arrangement (27 % with an explicit hybrid pattern or day/percentage, 26 % a general home-office mention); 5 % say on-site; **2 % fully remote**; 40 % say nothing. Data engineering (62 %) and marketing analytics (80 %, n 24) mention hybrid most; data governance (37 %) and data analytics (43 %) least. Styria matches the national pattern (32 of 58 = 55 %). Only 6 ads state days per week (mostly 2).
* Employment: 85 % full-time, 9 % full-or-part-time, 1 % part-time; 6 % internships/student jobs (45); 10 % temporary/contract (74).

## 11. Education and certifications (T11, T11e)

* Strength of the degree wording (T11e, n 719): **required 32 %** (a "completed degree" / "degree required" phrase), **preferred 2.5 %** (degree wording next to "von Vorteil/ideally"), mentioned only 30 %, no education wording 35 %. 33 % add "or equivalent experience". So roughly one ad in three treats a degree as a condition, one in three does not mention one, and explicit "nice to have" wording is rare.
* Levels named: generic degree 58 %, HTL/Matura 17 %, Master 10 %, Bachelor 6 %, **PhD 2 %**. Fields named near education words: computer science/informatics 38 %, engineering/physics 33 %, economics/business 26 %, data science 17.5 %, statistics/mathematics 12.5 %, marketing/communication 2 %.
* Degree-required wording by family: data analytics 38 %, data science 34 %, BI 33 %, business analysis 33 %, governance 32 %, data engineering 25 %, marketing analytics 21 %.
* **Certifications are almost never requested.** Any certification wording 13 %; specific certifications after extending the vocabulary with exam codes (DP-/AZ-/PL-, Google Professional, CDMP/DAMA, IREB/IIBA/CBAP, Scrum/PMP/IPMA, ITIL): requirements-engineering certificates 3 % (20, almost all business-analysis ads), Scrum/PM 1 %, ITIL 1 %, CDMP/DAMA 0.4 %, Azure 0.3 %, Google 0.3 %; Tableau, Databricks, Power BI and AWS certifications 0. The low numbers survive the vocabulary extension.

## 12. Time dimension (T13, JB01)

* Snapshot ages: karriere.at ads show a median age of 5 days (the board refreshes dates), LinkedIn 14, jobs.at 19, willhaben 34, AMS/EURES 41 days; 34 core rows are older than 180 days, 6 older than a year (evergreen ads). Earliest first-publish date 2023-08-17.
* Official flow (AMS JobBarometer, occupation class "Data Scientist (m/w)" — a coarse AMS class, not our titles): Austria 3,049 (2020) → 5,032 (2022 peak) → 3,471 → 2,680 → **2,207 (2025)**: −28 % vs 2020 and −56 % from the 2022 peak. Vienna 811 → 1,809 → 935 (−48 % from peak). Upper Austria 336 → 885 → 299. **Styria 224 → 423 → 300: +34 % vs 2020 and the only large region above its 2020 level.** Related classes 2025: Datenbankentwickler 1,198 (−40 % vs 2020), Wirtschaftsinformatiker 1,307 (−35 %), Systemanalytiker 731 (+84 %). AMS rates the 2026–2028 outlook for the Data-Scientist class "positiv" in every Bundesland; fastest-growing competencies in these ads: programming languages (+2.1 pp), communication (+1.2 pp) (JB03, JB04).
* Our single snapshot cannot measure change; the monthly re-run design in README turns it into a flow.

## 13. Adjacent demand (T16)

In the AMS feed for Styria (3,867 postings retrieved by full-text keywords, not by title), Python appears in 53 ads, of which 44 (83 %) carry non-data titles (engineering, controlling, research); SQL in 81 (88 % non-data titles); Power BI in 21 (all non-data titles); Excel in 182. Vienna and Upper Austria show the same pattern (70–88 % of tool mentions sit under non-data titles). Data skills are demanded far more widely than data titles — the entry channels through controlling, engineering and marketing roles are real, but this sweep covers only the AMS feed of three regions.
