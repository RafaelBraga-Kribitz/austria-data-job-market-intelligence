# Role taxonomy

Source of truth: `config/role_taxonomy.json` (ordered regex rules on the cleaned title). This page explains the families, why they were drawn this way, and how the taxonomy was validated against actual Austrian postings. Counts per family and per normalized title are in `outputs/tables/T02*.csv` and are quoted in `docs/market-guide.md`. The rules were revised on 2026-09-16 after a hand-labelled precision audit (DECISION_LOG D-012, `outputs/tables/Q03c_*`).

## Families

| Family | Normalized titles inside | Rationale |
|---|---|---|
| **data_analytics** | Data Analyst; Financial / Risk / Controlling Analyst (data-heavy) | The user's most direct target. "Data-heavy" analyst variants (risk, pricing, supply chain, people analytics, market-research analysts) are kept in the family but retain their own normalized title so they can be separated. |
| **bi** | BI Analyst; BI Developer / BI Engineer; BI Consultant / Analytics Consultant | Business Intelligence is a distinct Austrian label (Power BI, SAP BW, Qlik). Developer vs analyst vs consultant matters for the transition path. Consultant titles now require a data/analytics/BI word (generic SAP/banking/AI consultants were the largest false-positive group). |
| **data_science** | Data Scientist; Machine Learning / AI Engineer; Statistician / Biostatistician | ML engineers are kept inside data_science (the "modelling" end); **"AI Engineer" titles are counted with them and the label says so**. Actuaries and mathematicians were moved to an adjacent rule (not core). |
| **data_engineering** | Data Engineer; Analytics Engineer; Data Architect / Data Platform | Pipeline/platform roles. Analytics Engineer is listed separately because it is the SQL/dbt bridge role. |
| **data_governance** | Data Governance / Data Steward / Data Manager; **Master / Product Data Management (operational)** | Non-technical-to-semi-technical data roles. Since D-012 the operational master-/product-data roles (Stammdaten, PIM, engineering data) have their own normalized title (34 of 65) so that governance proper (31) is visible. Privacy-officer titles are excluded. |
| **marketing_analytics** | Marketing Data Scientist; Marketing/Growth/CRM Analyst (incl. web/digital analyst) | The user's domain. Very few Austrian postings use these titles (24); the family exists so that its rarity is visible. |
| **product_analytics** | Product Analyst | Same reason; essentially absent in Austrian titles (1). Product owners and laboratory "Produktanalytiker" are excluded. |
| **business_analysis** | Business Analyst (incl. requirements engineer, IT/system analyst, business process analyst/owner) | Adjacent, frequently advertised, less technical; a possible entry channel. Generic process managers and "IT business applications" titles were removed. |
| **ai_software_engineering** *(adjacent)* | AI/ML-focused Software, Platform or DevOps Engineer; AI consultant/manager titles; generic "Künstliche Intelligenz" titles | Numerous in 2026 but software-engineering profiles; reported separately so they neither inflate data_science nor disappear. |
| **other_data** *(adjacent)* | Actuary / Mathematician (adjacent); any title with a data/analytics/BI/statistics word that matched no specific rule | Retained for audit; not scored. |
| **out_of_scope** | everything else | Retained in raw and processed files only. |

## Rule order

Rules are evaluated top-down; the first match wins. Marketing and product families come first so that "Marketing Data Scientist" lands in marketing_analytics; ML/AI engineer before Data Scientist; Analytics Engineer before Data Engineer; master-data before governance; BI developer/consultant before BI analyst; the generic Data Analyst rule last among the specific families; AI-software and the actuary rule before other_data.

Hard exclusions (always, `normalize.py` HARD_OOS): data entry / Datenerfassung / data center / Rechenzentrum / data typist; security / cyber / SOC / threat; embedded / FPGA / firmware / microcontroller; laboratory / HPLC / Qualitätskontrolle / chemistry; regulatory, financial, ESG, EDI, treasury, IFRS or Konzern reporting without a data/BI/analytics word; thesis titles; "Bi-Static"; data protection / privacy / DSGVO.
Soft exclusions (only when no specific family matched, `config/role_taxonomy.json`): lab and biomedical "Analytiker", IFRS/accounting reporting, generic software/backend/platform/cloud engineers without a data or AI word, product managers/owners without a data word, managers without a data word, and a long list of non-office occupations.

## Validation against postings

* **Q03c (2026-09-16):** 25 random canonical titles per family (177 in total) were hand-labelled TP / borderline / FP against the definitions above and re-classified with the revised rules. Strict precision rose from 71 % to 83 % (lenient 84 % → 95 %); 22 false positives left the core set, one true positive was lost. Per-family values are in `docs/data-quality.md` §4 and `outputs/tables/Q03c_precision_summary.csv`; the labelled sample (titles only) is in `Q03c_manual_precision_audit.csv`.
* Effect on the core set: 824 → 720 postings; bi 135 → 85, data_governance 69 → 65 (re-labelled), data_science 178 → 158, business_analysis 139 → 120, data_analytics 116 → 107, product_analytics 3 → 1; data_engineering and marketing_analytics unchanged.
* Remaining known ambiguities:
  * "Analyst" alone (no qualifier) → other_data unless the AMS occupation label says otherwise.
  * "Controller" with data/BI words → Financial/Controlling Analyst (data-heavy); without → out of scope.
  * "Data Manager" → data_governance even when the job is really a project-management role; "Stammdaten" maintenance clerks → the operational master-data title.
  * "AI Engineer" → Machine Learning / AI Engineer (data_science) while "AI Developer"/"AI Consultant" → ai_software_engineering; the boundary is a judgement.
  * German "Analytiker:in" is ambiguous (lab vs. data); lab contexts are excluded by keyword, so a few clinical-data analysts may be lost.
  * Recall is not measured: data roles with unusual titles sit in `other_data` (235) or `out_of_scope`.
* The AMS occupation label attached to EURES titles (e.g. "(Data-Warehouse-Analyst/in)") is kept in `ams_occupation_label` and cross-tabulated with our family in `T02d`/`Q03` to show where the two classifications disagree.

## German compounds and synonyms

Cleaning removes gender markers ("(m/w/d)", ":in", "*in", "/in"), hours and location noise, and splits hyphenated compounds ("Daten-Analyst" → "daten analyst"). Patterns are bilingual (Datenanalyst/Data Analyst, Datenbankentwickler/Database Developer, Statistiker/Statistician, Datenmanagement/Data Management, Anforderungsmanagement/Requirements Engineering, KI/AI). Known gap: compounds without a separator ("Datenanalytik", "Datenwissenschaft") are covered, but rarer ones ("Kennzahlenanalyst") are not.

## Seniority

From the title only (intern_student, trainee_junior, senior, lead_head); LinkedIn's "seniority level" is used as a fallback; everything else is `unspecified`. Years of experience are extracted separately from the text and cross-tabulated (T08d) so that "what does senior mean" is answered by data, not by the label.
