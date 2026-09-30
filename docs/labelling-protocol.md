# Labelling protocol: recall, extractor and project-quality audits

Covers OQ-09 (title-taxonomy recall), OQ-16 plus the German-language and salary extractors (audit findings H6, M22, M23, M42), and OQ-12 (project quality, L40). Tooling: `src/analysis/labelling_audit.py`. The labelling is done by hand; the sampling and the scoring are scripted.

**Privacy.** Sheets, keys and ad texts live in `data/labels/<date>/`. The tool creates `data/labels/.gitignore` containing `*`, so git ignores everything in that folder. Public output is limited to the aggregate `Q10`–`Q12` tables in `outputs/tables/`. The writer refuses any table that has a posting id, title, employer, repository or per-row column. Repository URLs appear only in the private projects sheet (see `docs/legal-and-publication-audit.md` §10: no individual rows and no ranking of individuals, D-020).

**Blindness.** Do not open `*_key.csv` until labelling is finished. The key holds the pipeline's predictions. Rows are shuffled, so a row's position does not reveal its sampling stratum.

## 1. Workflow

| Step | Command / action | Time |
|---|---|---|
| 1 | Samples for 2026-09-30 are already drawn in `data/labels/2026-09-30/` (seed 20260930). To draw a new set: `python src/analysis/labelling_audit.py sample --date YYYY-MM-DD` and `... sample-projects --date YYYY-MM-DD`. The tool never overwrites a filled sheet unless you pass `--force`. | – |
| 2 | Recall: fill `recall_sheet.csv` (300 rows). Decide from the title and excerpt; open `recall_texts.html#r<row_id>` only when unsure. | **1.5–2 h** (≈ 20 s/row) |
| 3a | Extractor, language and salary blocks: fill all 100 rows of `extractor_sheet.csv`. In the full text (`extractor_texts.html#r<row_id>`), Ctrl+F for "Deutsch/German" and "€/EUR/brutto". | **≈ 1.5 h** (≈ 50 s/ad) |
| 3b | Extractor, skills block: read each ad in full for the 17 audited skills. Do at least the first 50 rows (the OQ-16 minimum), then all 100 if time allows. | **2 h per 50 ads** (≈ 2.5 min/ad) |
| 4 | Projects: rate the 40 repositories in `projects_sheet.csv`. | **≈ 3.5 h** (≈ 5 min/repo) |
| 5 | Save each sheet as **CSV UTF-8** (Excel: "CSV UTF-8 (durch Trennzeichen getrennt)"), then run `python src/analysis/labelling_audit.py score --date 2026-09-30`. Use `--only recall|extractor|projects` to score one audit. | 1 min |

Partial work scores correctly. A row counts only when its label is filled in (recall) or when its block is ticked done: `skills_done`, `lang_done`, `sal_done` or `rated_done` = 1.

## 2. Recall (OQ-09): what counts as a data role

**Sample design.** The default is a stratified probability sample drawn from **all 10,945 canonical postings** (count checked against `postings_dedup.parquet` on 2026-09-30: 12,429 rows, 10,945 `is_canonical`):

| Stratum | Population N | Sampled n | Weight N/n |
|---|---|---|---|
| S1 predicted core (8 families) | 720 | 60 | 12 |
| S2 not core, title/text carries a data word (SQL, Python, Power BI, Daten…, reporting, KPI…) or adjacent family | 5,905 | 180 | 32.8 |
| S3 not core, no data word | 4,320 | 60 | 72 |

**Why stratified.** Core postings are 6.6 % of the corpus, so a simple random sample of 300 would contain only about 20 data roles, and the recall interval would be about ±18 points wide. Stratifying over-samples the stratum where missed data roles are plausible. Every posting still has a known inclusion probability, and the estimates are weighted back. `--design srs` draws the simple random sample described in OQ-09 instead.

**Label codes (`label_data_role`).** Judge the job itself, not the wording of its title.

| Code | Meaning | Examples |
|---|---|---|
| `Y` | A data role in one of the eight core families of `docs/role-taxonomy.md`: the job's main content is analysing, modelling, engineering, governing or reporting data | "Sachbearbeiter Controlling" whose tasks are Power BI dashboards and SQL; "Kennzahlenanalyst"; "Referent Datenmanagement" |
| `A` | Adjacent: AI/ML software engineering, actuary/mathematician, a generic "Analyst" whose content is unclear | "AI Software Developer", "Aktuar" |
| `N` | Not a data role. Data tools may be mentioned, but they are not the job | cook; SAP MM clerk; lab analyst (HPLC); data-protection officer; "Datenerfassung" (data entry) |
| `?` | Cannot decide even from the full text | – |

For `Y` rows, `label_family` is optional: `DA` data analytics · `BI` · `DS` data science · `DE` data engineering · `DG` data governance · `MA` marketing analytics · `PA` product analytics · `BA` business analysis.

**Scoring (`Q10_title_recall.csv`).** `recall_core` is the weighted share of true data roles that the classifier put in a core family, with a stratified bootstrap 95 % CI. The table also reports `recall_core_or_adjacent`, `precision_core` (S1), `est_data_roles_in_corpus`, `est_missed_data_roles`, and `family_agreement_among_found`. As a sensitivity check, it recomputes each metric with `?` counted as a data role. `Q10b` shows which predicted family the missed data roles fell into. The missed titles themselves stay private in `data/labels/<date>/recall_misses_private.csv`, where they serve as input for new title rules.

## 3. Extractors (OQ-16, M23, M42): 100 core postings

A simple random sample of the 719 canonical core postings with a description (seed 20260930 + 7).

**Skills (`sk_<CODE>`).** Enter 1 if the role requires, uses or prefers the skill. Enter 0 or leave blank if it does not, or if the skill appears only in the company self-description, benefits or a legal footer. Tick `skills_done` = 1 when the row is finished; blanks then count as 0. Code the construct a reader of "X % of ads ask for …" would understand, not the extractor's regex:

| Code | Skill | Count it when… | Do not count |
|---|---|---|---|
| SQL, PY, R | SQL, Python, R | the language is named (T-SQL, PL/SQL count as SQL) | "R&D", "R" as a list letter |
| DGQ | Data Governance/Quality | governance, data quality, master data/Stammdaten, catalog, lineage, stewardship is a task | "Qualität" in general quality management |
| ETL | ETL/ELT | ETL/ELT or building/maintaining data pipelines | generic "Prozesse" |
| AZURE, AWS, DBX | Azure, AWS, Databricks | named as a platform used in the role | only in "our partners include …" |
| PBI | Power BI | Power BI (Power Query counts) | – |
| EXCEL | Excel | Excel named or clearly implied (pivot tables, VBA in Excel) | "MS Office" alone (the extractor counts it; this audit measures that choice) |
| DMOD | Data Modeling | data/dimensional modelling, star schema, Data Vault | "Modelle" meaning ML models |
| GENAI | Generative AI / LLM | GenAI, LLMs, RAG, prompt engineering, GPT/Copilot *as a technology to work with* | MS Copilot as an office perk |
| CICD | CI/CD | CI/CD, Jenkins, Azure DevOps pipelines, a DevOps practice in the role | – |
| REST | REST APIs | building/consuming APIs or interfaces (Schnittstellen) | "API" only in an app name |
| MATH | Mathematics | mathematics as a subject/degree/skill requirement | – |
| DWH | Data Warehouse | data warehouse / DWH named | – |
| GIT | Git | Git/GitHub/GitLab/Bitbucket or version control | – |

**German requirement (`de_class`).** This is the class for the whole ad, taken from its strongest statement:

| Code | Meaning | Pipeline values mapped to it |
|---|---|---|
| `REQ` | German is required: explicit requirement wording, or a level stated without hedging ("fließend Deutsch", "Deutsch C1") | required, required_implied |
| `PREF` | Nice to have: von Vorteil, wünschenswert, plus, ideally | preferred |
| `ALT` | German **or** English accepted | german_or_english |
| `NOTREQ` | Explicitly not required, or English is the working language | explicitly_not_required |
| `NONE` | Not mentioned, or mentioned only about the company or market | mentioned, not_mentioned |

`de_level` (only for REQ): `A`, `B1`, `B2`, `C1` (fluent / verhandlungssicher / sehr gut), `C2` (native / Muttersprache), or blank if no level is given. Tick `lang_done` = 1.

**Salary.** `sal_basis` is `RANGE` (lower and upper figure), `MIN` (one figure, including the collective-agreement minimum "mind. € … lt. KV") or `NONE`. `sal_amount` is the lowest figure stated for full-time work, exactly as written. `sal_period` is `M` (per month), `Y` (per year) or `H` (per hour; hourly figures are excluded from value accuracy). If the texts file shows a *structured salary field*, count it as part of the ad. Tick `sal_done` = 1.

**Scoring (`Q11_extractor_precision_recall.csv`, long format: field × class × metric).** Reports precision and recall per skill plus a micro-average; precision and recall per German class plus 5-class accuracy; level-bucket agreement where both sides say REQ; salary detection precision and recall; range-vs-minimum agreement; annual-minimum accuracy within ±2 % (monthly × 14, as in `normalize.py`); and period agreement. All intervals are Wilson 95 %.

## 4. Project quality (OQ-12): five-criterion rubric

40 projects are drawn at random from the 2,865 `is_substantive` projects in `supply_projects.parquet` (seed 20260930 + 13). The private sheet shows only a row id and the repository URL. The key holds the hashed `project_id` and the rule-detected README structure. Score each criterion from the README and a quick look at the code or notebook:

| Column | Criterion | 0 = absent | 1 = partial | 2 = clear |
|---|---|---|---|---|
| `q_question` | Question or objective stated | no statement of what is asked | topic named, no question | an answerable question or decision the work serves |
| `q_method` | Method appropriate | no method visible, or clearly wrong | method named but not justified or checked (e.g. accuracy on imbalanced data) | method fits the question and data, with a baseline or validation |
| `q_result` | Result quantified | no result | qualitative or figures without numbers | numbers with a comparison (metric vs baseline, effect size, error) |
| `q_limitations` | Limitations acknowledged | none | a generic sentence | specific limitations of data or method |
| `q_reproducible` | Reproducible | data unavailable and no run instructions | data or instructions, not both | data access (or a documented source) + environment + run steps |

Total = sum, 0–10. Set `unavailable` = 1 if the repository is gone, private or empty (it is then excluded and counted). Tick `rated_done` = 1. Rate the project, never the person, and do not look up the owner.

**Scoring.** `Q12_project_quality_rubric.csv` gives, per criterion, the mean score, the share rated clear (Wilson CI) and the share rated absent, plus the total. `Q12b_project_structure_vs_quality.csv` gives:

- the mean total with and without each rule-detected README section, suppressed below 5 projects per cell;
- detector precision and recall of each rule against a human rating ≥ 1, which calibrates the structural findings of BQ23/BQ24/BQ42;
- the Spearman correlation between the 0–5 structure index and the rated total, with a bootstrap CI.

With n = 40, read these as calibration, not as a ranking.

## 5. Where results go

| Result | Update |
|---|---|
| `Q10` recall + CI, `est_missed_data_roles` | `docs/open-questions.md` OQ-09 → answered (move to a "closed" note with the figures); `docs/data-quality.md` §4 next to the Q03c precision figures; `docs/role-taxonomy.md` "Recall is not measured" bullet; `docs/limitations.md` lines on title recall; `AGENT_CONTEXT.md` §1 "Recall unmeasured" |
| `Q11` | `docs/open-questions.md` OQ-16 (skills) and the language/salary follow-up (M23); `docs/data-quality.md` new section "Extractor precision and recall"; `docs/limitations.md` "formal precision/recall … not measured"; `docs/original-specification-audit.md` follow-up row |
| `Q12`, `Q12b` | `docs/open-questions.md` OQ-12; `docs/supply-data-quality.md` / `docs/supply-findings.md` wherever README structure is used as a quality proxy |
| Missed titles (private) | candidate rules for `config/role_taxonomy.json`; any rule change is a DECISION_LOG entry and requires a fresh sample (do not re-score the same sample after tuning on it) |

Record each scoring run in `DECISION_LOG.md`: the date, the labels folder, n labelled, and the headline figure.

## 6. Related private logs

- **Application-outcome log (OQ-01/04/06).** Schema: `schemas/application_log_schema.md`. Template: `data/private/application_log.csv`. Summarise with `python src/analysis/labelling_audit.py score-applications`, which writes a private summary to `data/private/application_log_summary.csv`.
- **Research-licence requests (OQ-17).** Drafts are in `data/private/letters/`. Record each reply in `data/private/letters/licence_requests_log.csv`.
