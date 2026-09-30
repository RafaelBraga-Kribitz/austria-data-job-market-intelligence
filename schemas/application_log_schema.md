# Schema: private application-outcome log (OQ-01, OQ-04, OQ-06)

File: `data/private/application_log.csv` (private, git-ignored via `data/private/.gitignore`; never exported). Template created by `python src/analysis/labelling_audit.py init-application-log` (never overwrites). Semicolon-separated, UTF-8; one row per application; update the outcome fields as answers arrive and set `last_updated`.

This page is public: it describes fields only and contains no application data. The log is the owner's own data about their own applications; employer names, contacts and offer figures in it stay private. Only the rate summary produced by `score-applications` (`data/private/application_log_summary.csv`, by owner decision) may ever be published, and only as aggregates with n.

| Field | Type | Codes / format | Purpose |
|---|---|---|---|
| app_id | str | `A001`, `A002`, … | row key |
| posting_uid | str | `<source>:<source_id>` if the ad is in a Layer 1 snapshot, else blank | link to the corpus (requirement fields can be cross-checked) |
| posting_ref | str | URL or board reference (private) | find the ad again |
| employer | str | as advertised (private) | – |
| role_title | str | as advertised | – |
| role_family | str | family code of `docs/role-taxonomy.md` (`data_analytics`, `bi`, …) | stratify outcomes |
| region | str | Bundesland or `remote` | – |
| posting_language | str | `de` / `en` | – |
| stated_german_class | str | `REQ` / `PREF` / `ALT` / `NOTREQ` / `NONE` (same codes as the extractor audit, `docs/labelling-protocol.md` §3), copied from the ad **at application time** | OQ-01 exposure |
| stated_german_level | str | `A` / `B1` / `B2` / `C1` / `C2` / blank | OQ-01 exposure |
| own_german_meets_stated | str | `Y` / `N` / blank if not stated | OQ-01, OQ-04 |
| unmet_requirements | str | `;`-separated short codes, e.g. `degree;5y_experience;SAP` | OQ-04 (were unmet requirements negotiable?) |
| channel | str | `company_site` / `karriere` / `stepstone` / `jobs_at` / `ams_eures` / `linkedin` / `referral` / `recruiter_inbound` / `other` | response rate by channel |
| application_language | str | `de` / `en` | – |
| referral | str | `Y` / `N` | confounder |
| cover_letter | str | `Y` / `N` | confounder |
| cv_version | str | owner's CV version tag, e.g. `cv-2026-10a` | confounder |
| portfolio_version | str | owner's portfolio tag, e.g. `pf-v3` (which projects were public and documented; keep a one-line changelog per tag in your notes) | OQ-06 |
| application_date | date | `YYYY-MM-DD` | required; rows without it are ignored |
| response | str | `none` / `rejection` / `screening` / `interview` / `offer` (furthest stage reached so far) | outcome |
| response_date | date | first reply of any kind | time to response |
| interview | str | `Y` / blank | outcome |
| first_interview_date | date | | |
| n_interview_rounds | int | | |
| offer | str | `Y` / blank | outcome |
| offer_date | date | | |
| offer_annual_gross_eur | int | private; the only first-party salary evidence (OQ-05) | never published individually |
| outcome_final | str | `open` / `rejected` / `withdrawn` / `ghosted_60d` / `offer_declined` / `offer_accepted` | closes the row |
| last_updated | date | | staleness check |
| notes | str | free text (private) | e.g. recruiter remarks on whether German was negotiable (OQ-04) |

**Minimum discipline:** fill everything up to `application_date` when you apply (≈ 2 min). Update `response`/`interview`/`offer` on each reply (≈ 30 s). After 60 days with no reply, set `outcome_final = ghosted_60d`.

**Reading the summary.** `score-applications` reports response, positive-response, interview and offer rates with Wilson intervals, broken down by `stated_german_class`, `own_german_meets_stated`, `channel`, `application_language`, `portfolio_version` and `referral`. Applications are not randomised across ads, so every contrast is confounded with everything else that changes during a search (OQ-01 "structural" limitation). About 50–100 applications give a directional read, never a causal one.
