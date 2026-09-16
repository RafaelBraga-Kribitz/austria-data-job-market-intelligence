# CAREER_DECISION_MAP

**Purpose.** The one document to open before a major career decision. Every statement below is traced to a table in `outputs/tables/` (T/JB/D/Q ids) via `docs/market-guide.md`; robustness labels follow the rule in `docs/limitations.md` (robust = holds on n ≥ 200, in both the AMS and the LinkedIn/karriere side, with confidence interval clear of the comparison; tentative otherwise). **All Styrian figures are tentative (n = 58) and are given as counts.**

**Data vintage.** Snapshot of open postings collected 2026-09-16 (12,429 raw rows from EURES/AMS, karriere.at, LinkedIn, willhaben, jobs.at → 720 deduplicated core data-role postings after the 2026-09-16 taxonomy audit, 58 in Styria); AMS JobBarometer yearly series 2020–2025. Re-run before relying on this after ~2026-12 (see collection restrictions in AGENT_CONTEXT §21).

**Reading rules.** "Share" = share of ads that *mention* something. A one-day snapshot is a stock of open ads, not yearly demand, not vacancies, not hires. Nothing here measures hiring outcomes; every "lever" below is an observed requirement pattern, not a causal effect on getting hired.

---

## WHERE IS THE MARKET?

* **Vienna: 48 % of open core data postings (343 of 720). Upper Austria 17 %. Styria 7.5 % (54; 58 incl. multi-site ads).** Robust for the ranking; the Styrian share is tentative (official yearly data puts it at 13.6 %, JB05).
* Styria = Graz: 34 of 58 Styrian postings are in Graz city, 52 in the commuting area; the rest are single ads in Weiz, Leoben, Liezen (T03c).
* On the official flow measure, Austria's "Data Scientist"-class ads fell from 5,032 (2022) to 2,207 (2025), −28 % vs 2020; **Styria is the only large region above its 2020 level (224 → 300, +34 %)**; Vienna −48 % from its peak (JB01). AMS rates the 2026–28 outlook "positiv" in every Bundesland. Robust as an official series; it counts a coarse occupation class, not our titles.

## WHAT ROLES EXIST?

Ranked by open postings (T02): data engineering 22 % (Data Engineer 134) · data science 22 % (Data Scientist 79, ML/AI Engineer 76) · business analysis 17 % · data analytics 15 % (Data Analyst 77, data-heavy finance/risk analysts 30) · BI 12 % (developer 33, analyst 32, consultant 20) · data governance 9 % (of which 34 are operational master-data roles) · **marketing analytics 3 % (24 postings, 0 in Styria) · product analytics 1 posting**. Robust for the ranking. Plus 311 AI-software-engineering titles (software roles, excluded) and 235 unclassifiable data-ish titles. Title precision measured at 83 % strict / 95 % lenient (Q03c).

## WHERE ARE THEY? (Styria specifically)

Styria's 58: data engineering 20, data science 13, data analytics 11, BI 5, governance 5, business analysis 4, marketing/product 0 (T02). Named employers (32; 10 postings unnamed): KNAPP 7, adesso 4, Tieto 3, CANCOM, niceshops, Anton Paar, Mercedes-Benz G, Magna 2 each, then Netconomy, KERN, ÖGK, ams OSRAM, Kapsch, Merkur, Easelink and others with one (T04a). Tentative (small n), but the industrial/consultancy pattern matches the JobBarometer picture.

## WHAT DO THEY REQUIRE?

Mention shares among 719 core ads (T05): SQL 40 %, dashboards/visualisation 38 %, Python 35 %, data-quality/governance wording 31 %, cloud 29 %, ETL 22 %, Azure 19 %, Power BI 18 %, Excel 18 %, data modelling 16 %, ML 16 %, GenAI/LLM 16 %, CI/CD 15 %, statistics 14 %. Robust for the ranking and levels of the top ten.
Per family (T14): analysts (n 107) = visualisation 64 %, Excel 47 %, SQL 38 %, Power BI 34 %, Python 26 %; BI (85) = visualisation 86 %, SQL 52 %, Power BI 51 %, data modelling 33 %, SAP BW 28 %; data scientists (157) = Python 73 %, ML 55 %, GenAI 53 %, cloud 48 %, SQL 36 %, Azure 34 %, statistics 29 %; data engineers (160) = SQL 69 %, ETL 60 %, Python 55 %, cloud 45 %, Azure 38 %, modelling 38 %, CI/CD 34 %, Databricks 29 %.
Soft/business wording (indicative): stakeholder/business-partner 55 %, communication 63 %, analytical thinking 55 %; consulting context 31 %, finance/controlling 25 %, marketing 10 %.

## WHAT LANGUAGES DO THEY REQUIRE?

* **40 % of ads state a German requirement (8.5 % explicit, 31 % by level); when a level is stated it is wording we bucket as C1-equivalent in 36 % of all ads (mostly "sehr gut", an assumption) and B2 in 12 %.** 41 % are silent (and German-written silence usually implies German). 24 % of ads are written in English; **in those, German is still required/level-stated in 19 % and preferred in 19 %** (T07, T07d). Robust.
* By family: BI 51 % German required/level-stated, business analysis 44 %, data analytics 42 %, governance 40 %, data engineering 36 %, **data science 33 % and 44 % English-written**. Robust for the ordering.
* **Styria: 28 of 58 state a German requirement (48 %) vs 39 % elsewhere; 13 of 58 are English-written** (tentative).
* Addressable-set scenarios (T07e), three readings that bracket rather than pin the truth: English-written *and* no stated German requirement — 141 of 719 nationally (20 %), **8 of 58 in Styria**, 86 of 349 in Vienna; no explicit German requirement (silence included) — 434 nationally, 30 of 58 in Styria; German not required at C1-equivalent — 512 nationally, 37 of 58 in Styria. "English-written, no stated requirement" is not "English-only": German may still be preferred or expected.

## WHAT TECHNOLOGIES DO THEY REQUIRE?

Microsoft-centred stack: Azure 19 % vs AWS 9 % vs GCP 6 %; Power BI 18 % vs Tableau 3 %; Databricks 12 %, Fabric 6 %, Snowflake 6 % (T05). Stacks: ETL+Python+SQL 12 %, Cloud+Python+SQL 12 %, AI+GenAI+Python 11 %, Visualisation+Power BI+SQL 10 %, Azure+Python+SQL 10 % (T06b). SQL and Python co-occur in 24 % of ads; 59 % of SQL ads also mention Python; 64 % of Power BI ads mention SQL; 80 % of Databricks ads are Azure ads; DAX is named in only 15 % of Power BI ads; dbt in 25 ads (T06). Python libraries are almost never named (pandas 3 %, scikit-learn 4 %). **Styrian ads lean engineering: Python 29 of 58, Azure 20, cloud 24, ETL 20, Databricks 11 (50/34/41/34/19 % vs 34/18/28/21/11 % elsewhere); Excel and Power BI lower** (tentative). Robust nationally.

## WHAT EDUCATION DO THEY REQUIRE?

Degree wording is *required* in 32 % of ads, *preferred* in 2.5 %, merely mentioned in 30 %, absent in 35 % (T11e); "or equivalent experience" in 33 %; fields named: informatics 38 %, engineering 33 %, business/economics 26 %, data science 17.5 %, statistics/mathematics 12.5 %; **Master 10 %, PhD 2 %**. **Certifications: any wording 13 %, specific ones ≤ 3 % each** even after adding exam codes (IREB/IIBA 3 % — in business-analysis ads; Azure 0.3 %; Google 0.3 %; Tableau/Databricks/Power BI/AWS 0) (T11). Robust.

## WHAT DO THEY PAY? (advertised minimums, annual gross, monthly × 14)

79 % of ads state a figure, but 81 % of those figures are a single collective-agreement minimum; only 15 % state a range; 53 % say they pay above the minimum; 10 % are "all-in" (T09). Median advertised minimum: data engineering €55.4k (n 132), data science €55.4k (122), business analysis €55.0k (93), BI €52.6k (67), **data analytics €47.8k (83)**, data governance €45.5k (50), marketing analytics €42.0k (21). Seniority: junior €42.0k, unlabelled €52.2k, senior €60.0k, lead €60.1k (upper ends of stated ranges reach €75–95k). Styria €53.2k (49) vs Vienna €55.4k (272). Ads mentioning Databricks/GenAI €60k, Power BI €49.0k, Excel €43.7k. **These are legal floors, not offers; actual compensation cannot be estimated from ads**; third-party context in docs/salary-context.md (AMS entry range for Data Scientist €39–61k). Robust as floors.

## WHAT WORK MODE DO THEY OFFER?

Hybrid or home-office mentioned in 53 % (explicit hybrid pattern 27 %), on-site 5 %, **fully remote 2 %**, 40 % silent (T10). Data engineering 62 %, data science 55 %, analysts 43 %, marketing analytics 80 % (n 24). Styria 32 of 58. Days per week almost never stated (6 ads). Robust for "hybrid is the norm, remote is rare".

## WHEN IN THE YEAR SHOULD I APPLY, AND WHEN IS IT QUIET?

Answered from Eurostat's Austrian Job Vacancy Statistics (quarterly, 2009–2025, 17 years), **not** from our snapshot: a one-day snapshot cannot measure seasonality, and `docs/seasonality.md` §1 shows why (52 % of the 720 core ads were first published in the collection month; 90 % within 90 days — that is survival decay, not a calendar).

* **Q4 (Oct–Dec) is the reliably thinnest quarter**, in all four sector aggregates, under both estimation methods and in every sub-sample: index 0.93–0.98 against an average quarter, and the weakest quarter in 8–10 of the 16–17 years (S01, S02). Robust as a direction.
* **Q1 (Jan–Mar) is most often the strongest single quarter** — 9 of 17 years in industry & construction (index 1.072), 7 of 16 in the total economy. That is the aggregate Styria's industrial employers sit in.
* **The Q3 peak in market services (1.038) must not be read as data-job demand:** the NACE G-N aggregate also contains accommodation, food service and retail, and Austria does not report ICT separately here. Summer is, however, clearly not a dead period (Q3 above average in 12 of 17 years).
* **Amplitude is small and the cycle dominates:** best-vs-worst quarter is 5–14 %, best-vs-worst *year* is 255–567 % — a factor of 19–49 (S06). Market-services vacancies ran at ~33,700 per quarter in 2009, peaked at ~137,700 in 2022 and were ~82,200 in 2025.
* **Practical reading:** do not time applications by month; use **Oct–Dec as the build/study block** and be **application-ready in January**; keep applying continuously, because half of the open ads in the snapshot were under 14 days old (median 5 days on karriere.at). No occupation or regional grain, so nothing here is Styria- or data-role-specific (docs/seasonality.md §7).

## WHAT DO I ALREADY HAVE?

Stakeholder/business/communication wording is the most universal requirement (55–63 %); finance/controlling, sales, consulting and marketing contexts frame most analyst ads; Excel and dashboards remain the analyst baseline (47 % / 64 %); seniority is expected (57.5 % unlabelled ads, "senior" ≈ 5 years); experimentation is a rare, credible edge (A/B testing 3 % overall, 4 of 24 marketing-analytics ads) (career-map §1).

## WHAT SKILLS AM I MISSING?

Demonstrable SQL and Python at professional level (40 % / 35 % of ads; 69 % / 55 % of data-engineering ads; 73 % Python in data science); Power BI with data modelling (18 %; 34–51 % in analyst/BI ads); data-quality/ETL practice (31 % / 22 %); applied GenAI wording (16 %); statistics made explicit in projects (14 %, but 29 % in data science) (D03, D04).

## WHICH GAPS ARE SMALL?

SQL, Python-for-analysis, data-quality/ETL practice, Power BI/data modelling, Git, applied GenAI: all already "developing", each ≥ 10 % of ads, each unlocking several families (D04 "NOW"/"NEXT").

## WHICH GAPS ARE STRUCTURAL?

**German at a demonstrable B2/C1.** Observed pattern: only 8 of 58 Styrian ads are English-written without a stated German requirement; 30 of 58 state no requirement; 37 of 58 do not state C1-equivalent (T07e). Whether stated requirements are negotiable, and whether German proficiency changes hiring outcomes, is not measured — the data shows that German appears to be the most frequently stated non-technical barrier in Styrian ads, larger than any single tool. Also structural: Azure/Databricks/CI-CD platform engineering (8 of the 15 top data-engineering skills are structural for this profile); ML-engineering depth (Docker/Kubernetes/MLOps/PyTorch, 4–6 % each); informatics/engineering degree wording (38 % / 33 %; softened by "or equivalent" 33 %); industrial domain knowledge for Styrian manufacturing employers (D03, career-map §3).

## WHAT CAREER PATHS ARE SUPPORTED BY THE EVIDENCE?

1. **Data / business analytics (entry family).** 107 AT, 11 Styria; highest profile overlap (13 of the 15 most-mentioned skills are in the self-declared have/developing lists), smallest structural gap (2 of 15); German 42 %; floors lowest (€47.8k). Decision-matrix rank 3 under all four weightings (D02).
2. **Applied data science (second step).** 158 AT, 13 Styria; most English-friendly (44 % English ads; 55 of 157 English without stated German requirement); rank 1–2 under all weightings; but 8 of its 15 top skills are structural and 34 % carry degree-required wording — realistic as an applied/business data scientist, not ML engineer.
3. **BI (tool angle).** 85 AT, 5 Styria; Power BI + SQL + modelling; **highest German requirement (51 %)**, lowest English share (8 %); consultancies (adesso, CANCOM) recruit in Graz.
4. **Marketing/CRM/web analytics (domain angle).** Best domain fit (12 of 15 top skills), but 24 postings nationally, 0 in Styria, 80 % hybrid; pursue as the analytics side of marketing titles and remote/hybrid Vienna roles, not as a local title.
5. **Data engineering.** Styria's largest family (20 of 58) with the best floors and hybrid share, rank 1 under default/geography/equal weights, but the largest structural gap (8 of 15); only via the SQL/modelling (analytics-engineer) end, which is 5 titles nationally.
6. Data governance: 65 AT (half operational master-data roles), 5 Styria; senior/lateral option, thin locally.
No path is "robust" by the framework's rule because every Styrian family count is below 30 (D01). The *ordering* of the top three (engineering/science/analytics) is stable across weightings; the ranking measures market size, English openness and salary floors, not ease of entry — which is why analytics, not engineering, is the evidence-derived entry family for this profile.

## WHAT SHOULD I LEARN?

Now: SQL; Python for data work; data-quality/validation practice; ETL/ELT basics; statistics applied in projects. Next: Power BI + dimensional modelling (+ DAX basics); applied GenAI/LLM; REST/API basics; Git. Later: Azure fundamentals and one Databricks/Fabric project; CI/CD basics. Do not prioritise: Tableau, Looker, Qlik, GCP/BigQuery, Spark/Kafka, Java/Scala, Kubernetes/MLOps, deep-learning frameworks, vendor certifications, PhD (D04; career-map §7).

## WHAT SHOULD I BUILD?

(1) A SQL + Power BI dashboard on a properly modelled star schema over marketing/e-commerce data (covers the single most requested analyst combination). (2) A Python ETL pipeline into a warehouse with tests and Git/CI (covers the Styrian engineering flavour). (3) An experimentation/causal analysis of a marketing or product change (rare differentiator). (4) A forecasting or churn/CLV model on business data (bridges domain and ML wording). (5) An applied RAG/LLM assistant over business reports (fastest-growing wording). Not: Tableau, streaming demos, deep-learning showcases, certification labs (career-map §8).

## WHAT SHOULD I PUT ON MY CV?

Employer vocabulary in order of frequency: SQL · Python · Power BI · Excel · Datenanalyse/Data Analytics · Dashboard/Reporting · Datenqualität/Data Governance · ETL · Azure · Machine Learning · KI/AI · Statistik · Datenmodellierung · Stakeholder/Fachbereich · Kommunikationsstärke · analytisches Denken · selbstständig. Domain words: Controlling, KPIs/Kennzahlen, Forecast, Vertrieb, CRM, E-Commerce, Kundendaten, Segmentierung, Kampagnen. State the German level with CEFR. Title lines that exist in the market: Data Analyst, Business Analyst, BI Analyst, Data Scientist; "Marketing Data Scientist" is 2 postings.

## WHAT SHOULD I EMPHASIZE ON LINKEDIN?

LinkedIn is the English/multinational side of the market (24 % of ads English; data science 44 %): headline with "Data Analyst | Marketing & Customer Analytics | SQL · Python · Power BI"; senior business ownership (stakeholder wording 55 %); experimentation and causal work as differentiators; hybrid/Graz-Vienna availability. LinkedIn ads carried the most seniority words after jobs.at (40 % with a seniority word in the title) and 41 % omit salary.

## WHAT SHOULD MY GITHUB DEMONSTRATE?

Two to three finished, documented projects from "What should I build", each showing SQL, Python, a modelled dataset, data-quality checks and a dashboard or decision output; the README should use the employer vocabulary above. Ads name tools, not libraries — library lists do not move the needle.

## WHAT SHOULD I STOP SPENDING TIME ON?

Tableau/Looker/Qlik (≤ 3 %); GCP/BigQuery (6 % / 4 %); Spark/Kafka/streaming (6–7 %); Java/Scala; Kubernetes/MLOps/deep-learning frameworks (4–6 %); collecting certifications (specific certs ≤ 3 % of ads, vendor data certs ≤ 0.3 %); positioning as "Marketing Data Scientist" or "Product Analyst" as a local Graz title (2 and 1 postings nationally); chasing fully-remote roles (2 %).

## WHAT WOULD CHANGE THIS MAP?

For every recommendation above the supporting table, denominator and assumption are named in `docs/market-guide.md`. The observations that would change the conclusions:

| Observation | Would change |
|---|---|
| A larger Styrian sample (monthly re-collection through permitted channels, or company career pages) moving any Styrian family count above 30 | the "tentative" label on all Styrian statements; possibly the entry-family ranking if analytics postings in Graz turn out rarer or commoner than 11 of 58 |
| StepStone.at / Indeed data (largest coverage gap) with a different family, language or salary mix | family shares, the German-requirement share (StepStone is corporate/white-collar), advertised floors |
| Longitudinal data (first-seen/last-seen per posting) | the stock-based view; would reveal hard-to-fill roles and true monthly flow |
| A change in stated German requirements (e.g. English-written share in Styria rising above ~25 %, or C1 wording falling) | the "German is the largest stated barrier" conclusion and the addressable-set counts |
| Evidence on negotiability (interview outcomes for ads that stated "sehr gute Deutschkenntnisse") | the weight given to stated language levels |
| Technology demand shifts (Fabric/Databricks share, GenAI wording, Tableau/Looker reappearing, Analytics-Engineer titles growing beyond 5) | the learning roadmap and project list |
| Advertised floors moving (e.g. analyst floors converging with engineering floors) or third-party survey data with methodology | the salary section and the V7 weight |
| New role categories in Austrian titles (e.g. "Analytics Engineer", "AI Product Analyst") | the taxonomy and the family ranking |
| A quarterly re-run of the Eurostat vacancy series showing Austrian vacancies turning back up after the 2022–2025 decline, or falling further | the urgency of applying now versus building first; the cycle moves 19–49× more than the season (docs/seasonality.md §5) |
| Actual interview/hiring outcomes for this profile (applications sent, responses, offers by family and language) | everything above — this is the only observation that can turn requirement patterns into evidence about hiring |
| JobBarometer 2026 reversing Styria's relative resilience | the geographic conclusion |
| A manual extraction audit showing precision below ~90 % for language or salary fields | the language and salary sections |
