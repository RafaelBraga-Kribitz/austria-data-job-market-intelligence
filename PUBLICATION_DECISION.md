# PUBLICATION_DECISION

**Decision (2026-09-16): PUBLICATION RECOMMENDED — for the sanitised research version only.**

The full repository (raw source records, processed posting files, posting collectors, private hunter, private history) stays private. What is published is the version built by `src/publish/export_public.py`: code without the posting collectors and without `src/private/`, configurations (with a neutral example profile instead of the owner's `config/profile.json`), schemas, tests, documentation, decision documents, figures, aggregated tables and JSON summaries, with a fresh git history. **Private research collection is intended** — collectors are dark so they are not a portfolio or GDPR liability, not because the author is forbidden to run them offline (D-022). This is a publication-readiness conclusion, not legal advice; the analysis behind it is `docs/legal-and-publication-audit.md`.

## 1. What was audited

* Repository structure, git tracking (on 2026-09-16: 251 tracked files, one commit, no remote), file sizes (six tracked files above GitHub's 100 MB limit), `.gitignore`, ignored folders.
* Every raw JSONL envelope, the processed files, all output tables and JSON files, docs, code and configs — scanned for e-mail addresses, phone numbers, contact fields, secret-like tokens and credentials.
* The acquisition code (headers, cookies, tokens, throttling, endpoints) against each source's robots.txt and terms of use, fetched on 2026-09-16.
* GDPR, Austrian UrhG (§§ 42, 42h, 76c–76e), Directive 96/9/EC, Directive (EU) 2019/790, the CJEU database-right cases (C-203/02, C-202/12, C-30/14, C-762/19), C-101/01 *Lindqvist*, EDPB scraping guidance, Commission Decision 2011/833/EU, GitHub's terms and acceptable-use policy.
* The completeness of the original specification (`docs/original-specification-audit.md`) and the correctness of the headline claims (taxonomy precision audit, denominators, language and salary definitions).

## 2. What was found and removed from the public version

| Finding | Treatment |
|---|---|
| ≈2,400 distinct e-mail addresses, thousands of phone numbers and named contact persons of HR staff/AMS advisers inside advertisement texts; willhaben `contact` objects with first/last names | Personal data under GDPR. Never exported. Snippet columns that carried some of them removed from all public tables; export aborts if any address or phone pattern survives. |
| ≈12,400 verbatim advertisement texts, raw LinkedIn/jobs.at HTML pages, JobBarometer HTML | Third-party text and database contents. Never exported. |
| Per-posting tables with employer + salary + snippet (`T09e`), audit samples with snippets (`Q07a`, `Q07b`, `Q09`), per-posting URLs (`T16a`) | Excluded; every snippet/description column and every column whose name contains a `url` or `html` part dropped elsewhere; `posting_uid` (private value `source:source_id`) replaced by a keyed hash since 2026-09-30. |
| The six posting-collector scripts for the five posting sources (EURES with its regional sweep, karriere.at, jobs.at, LinkedIn, willhaben) | All five posting sources restrict automated extraction in their terms; LinkedIn's User Agreement prohibits developing or supporting scraping software; willhaben and LinkedIn disallow the used paths in robots.txt. Collectors stay private; the methodology is documented in prose. |
| Fetched salary reference pages (`data/external`) | Third-party pages; excluded, figures cited with URLs instead. |
| The private git history (contains all of the above) | Never pushed; the public repository starts from the exported tree. |
| No credentials, cookies, tokens or secrets of the author were found | Nothing to remove; two benign false positives documented. |

## 3. What remains public and why it is materially lower risk

* **Code, configs, tests, schemas, docs** are the author's own work (MIT / CC BY 4.0).
* **Aggregated tables and JSON**: shares, counts, medians and confidence intervals over 720 postings; job titles (facts, needed to audit the taxonomy); employer names of legal entities with posting counts. None of it is advertisement text, personal data, or a substantial part of any source's database; a reader cannot reconstruct any source record from it (C-762/19 investment-harm test; § 76d UrhG re-utilisation of substantial parts; GDPR Art 4(1)).
* **Figures and the digest** are derived from those tables.

## 4. Risk levels after sanitisation (definitions in the legal audit §5)

| Category | Public version |
|---|---|
| Privacy (GDPR) | LOW — no personal data; employer names are legal persons |
| Copyright in ad texts | LOW — no text republished; titles and extracted terms are facts |
| Database right | LOW — statistics only; no extraction/re-utilisation of a substantial part; no substitute product |
| Contractual / terms of service | MEDIUM (residual) — the *collection* ran against the sources' terms; publishing statistics is not itself restricted by any fetched clause, but the methodology discloses the collection. This includes the private hunter's python-jobspy collection of LinkedIn *job listings* on 2026-09-18 behind the T19 aggregates (same `jobs-guest` endpoints; legal audit §11.2). Mitigated by not distributing the collectors, by stating the restriction openly (D-013) and by the non-commercial, non-substituting character. |
| Technical access | LOW — no circumvention; documented politely |
| Source republication | LOW — none |
| Reputational / professional | LOW–MEDIUM — the honest disclosure of the terms conflict is the credible posture; a scraper published under the author's name would not be. Public statements distinguish LinkedIn *job listings* (collected by automation on 2026-09-16 and 2026-09-18, aggregates published) from LinkedIn *member/people* data (never collected by automation). |
| GitHub policy / size | LOW — no third-party content, no personal data, largest public file < 1 MB |

No BLOCKER remains in the public version. Three BLOCKERs apply to the private material (personal data, third-party text/database contents, oversized files) and are the reason the full repository must not be published.

## 5. Limitations that still apply

* The public repository is auditable but not regenerable: without the private raw data the aggregates cannot be recomputed by outsiders. This is stated in README and `docs/limitations.md` §13.
* The legal analysis relies on clauses and statutes as fetched on 2026-09-16; terms change. It could not verify an Austrian court decision on copyright in job advertisements, the exact AMS open-data licence identifier, or whether browse-wrap terms bind logged-out visitors under Austrian law.
* The residual contractual/reputational exposure (§4) is disclosed, not eliminated.
* Should the project ever become commercial, or should any source object to the publication of statistics derived from its listings, this decision must be revisited (the derived tables can be removed source by source; the source column exists in T01, T03e, T07 and T09a).

## 6. What could change this decision

* A source stating that publishing aggregated statistics derived from its listings is not permitted → remove that source's rows from the affected tables or take the repository private.
* A change in the author's purpose from personal research to commercial use → re-audit (non-commercial character underpins several conclusions).
* A permitted data channel (AMS/EURES permission, data partner) → the acquisition layer could become public and reproducible.
* New authoritative guidance (EDPB/DSB) on publishing scraped data → re-audit the personal-data section.

## 7. Validation before publication — release checklist

The 2026-09-16 release was validated as follows (recorded in the final report of that day): full pipeline re-run after the taxonomy fix with 67 tests passing; digest consistency check; `src/publish/export_public.py` with zero problems; independent scan of the exported tree; size check; fresh git history; push; visibility, README rendering and tree checked; clean clone in a temporary directory with `pip install -r requirements.txt`, `python -m pytest tests -q` and `python src/reporting/digest.py`.

From 2026-09-30 every release is recorded as a dated checklist; nothing is ticked without its evidence in the line.

**Release 2026-09-30 (Layers 1–3 + visual layer; D-026, D-029)**

- [x] Tests pass in the private repository: `python -m pytest tests -q` → 400 passed (2026-09-30, after the redaction; `run_all.py all` before it: 399 passed)
- [x] Digest regenerated with `--strict` (no missing input) as the last `run_all.py all` step; prose numbers reconciled against it on 2026-09-30
- [ ] Export completes with zero problems (staged; the public tree is replaced only on success): `python src/publish/export_public.py ../austria-data-job-market-intelligence-public` → <<EXPORT_OUTPUT>>
- [ ] Suppression thresholds re-verified by the export (C02 `count` ≥ 3, C19e `projects` ≥ 5) — part of the export output above
- [ ] Private paths absent from the public tree: `config/profile.json` is the neutral example; no `library_strategy/`, `docs/linkedin-slot-interface.md`, `src/private/` or posting collector — part of the export output above
- [ ] Clean clone of the public tree in a temporary directory: `pip install -r requirements.txt`, `python -m pytest tests -q`, `python src/reporting/digest.py`
- [ ] Public commit pushed and visible: <<PUBLIC_COMMIT>>

Decision recorded in `DECISION_LOG.md` D-014.


## 8. Layer 2 / Layer 3 addendum (2026-09-18)

**Decision: the split model is retained and extended. PUBLICATION RECOMMENDED for the Layer 2/3 code, configurations, schema, methodology, audits, aggregated tables (C*, DS*, SQ*, O*), figures (S*, DSF*) and JSON summaries; the individual-level candidate material stays private.** Analysis: `docs/legal-and-publication-audit.md` §10; decisions D-017, D-018, D-021.

### 8.1 What was audited

The GitHub API collection (`data/raw/github_supply/2026-09-17/`: 9,464 profiles with bio, free-text location, company, website, hireable flag, counters; 126,013 repository records; 11,798 README texts and file trees; social-account links for 4,625 accounts), the processed candidate/project/evidence tables and the private review samples, the Stack Overflow 2025 extract (ODbL), the Eurostat series, the manual LinkedIn slot (empty at the time of this audit), and every new public artefact — scanned with the same e-mail/phone/URL/free-text guard as Layer 1 (`src/publish/export_public.py`, extended for the new paths and columns).

### 8.2 Classification

| Artefact | Status |
|---|---|
| Collectors and ingestion scripts (GitHub API, Eurostat, Stack Overflow, manual LinkedIn), pipeline, analysis, tests, configs, schema | **PUBLIC-SAFE** — author's code; documented APIs; no source records |
| `data/raw/eurostat_supply/` | **PUBLIC-SAFE** — open official statistics |
| Aggregated tables C*, DS*, SQ*, O*; figures S*, DSF*; `outputs/supply_*.json`, `demand_supply_*.json`, `project_evidence_map.json`, `operational_career_context.json`; digest | **PUBLIC-SAFE** — counts, shares, intervals; raw-bio phrases only with ≥ 3 accounts (C02); README headings only with ≥ 5 projects (C19e); no logins, names, URLs or free text |
| `data/raw/github_supply/`, `data/processed/supply_*`, `data/external/stackoverflow_survey/`, `data/raw/linkedin_supply/`, `logs/github_supply.log` | **PRIVATE-ONLY** — personal information of account holders (bios, locations, logins), third-party README texts, ODbL extract, review samples with labels |
| `docs/profile-specific-demand-supply-analysis.md`, `CAREER_ASSUMPTIONS_REVIEW.md`, `library_strategy/`, `config/profile.json` | **PRIVATE-ONLY** — the owner's personal strategy (not in the export list; D-026 (c)); the public tree gets the neutral `config/profile.example.json` as `config/profile.json` |
| `docs/linkedin-slot-interface.md` (LinkedIn slot channel contract, 2026-09-30) | **PRIVATE-ONLY** — private collection method (D-026 (c)); excluded by `EXCLUDE_DOCS` |
| Manual LinkedIn protocol (`docs/supply-methodology.md` §7), empty templates | **PUBLIC-SAFE** — procedure only; any filled records are private by path |

### 8.3 Risk levels after sanitisation (definitions in the legal audit §5)

| Category | Public version |
|---|---|
| Privacy (GDPR) | LOW — no individual rows, identifiers, names, locations or bios; aggregates with suppression thresholds |
| Copyright in READMEs / bios | LOW — no text republished beyond generic headings shared by ≥ 5 projects |
| Database right (GitHub) | LOW — statistics over a few thousand accounts; no substitute product |
| Contractual (GitHub AUP §7 research clause; API terms) | LOW–MEDIUM — research use, open-access publication, no recruiting/selling use; personal fields used privately only |
| ODbL (Stack Overflow) | LOW — produced works with attribution; extract not redistributed |
| LinkedIn (people / members) | LOW — no member or people data collected by automation; the slot accepts only permitted channels (D-026 (a)) and is private |
| LinkedIn (job listings) | not a Layer 2 item: job listings *were* collected by automation (2026-09-16 Layer 1; 2026-09-18 private hunter → T19); assessed in §4 and legal audit §11.2 — contractual MEDIUM (residual), disclosed |
| Reputational | LOW — no individual is named, ranked or scored; the collection method is stated openly |

No BLOCKER remains in the public version. BLOCKERs (personal information, third-party text) apply to the private raw/processed material, as in Layer 1.

### 8.4 Validation before publication

Layer 2/3 is validated by the release checklist in §7 (release 2026-09-30). The earlier prose claim of 2026-09-18 ("tests pass; export completes with zero problems; thresholds enforced in code") had no recorded output and was not followed by a public push. Since 2026-09-30 the two suppression thresholds are re-verified by the export itself (`SUPPRESSION_RULES` in `src/publish/export_public.py`), not only by the analysis code.

### 8.5 What could change this decision

Any indication from GitHub that the research clause does not cover this use; a request from an account holder (the private data can be deleted account by account: `candidate_id` → `login` in the private files only); a change of purpose to commercial use; filling the LinkedIn slot with anything but manual observations.

## 9. Addendum (2026-09-30): private hunter, Arbeitnow, T19, private documents

**Decision: the split model is unchanged; the additions of D-022/D-023 and D-026 are classified as follows.** Analysis: `docs/legal-and-publication-audit.md` §11.

| Artefact | Status |
|---|---|
| `src/acquisition/collect_arbeitnow.py` | **PUBLIC** (documented, key-less API); the API's terms are not yet fetched (open item, legal audit §11.1); raw `data/raw/arbeitnow/` private |
| `src/private/` (hunter incl. python-jobspy LinkedIn job listings and StepStone/Indeed attempts; LinkedIn slot cockpit), `data/raw/radar/`, `jobs.db`, fit scores | **PRIVATE-ONLY** |
| `outputs/tables/T19_supplement_*.csv` (109 core LinkedIn job titles of 2026-09-18, aggregates only) | **PUBLIC**: privacy and database right LOW, contractual MEDIUM (residual, as for the Layer 1 LinkedIn aggregates), disclosed in `docs/methodology.md` §1 |
| `outputs/tables/T04c_linkedin_industry_raw.csv` (LinkedIn industry category labels × counts per source) | **PUBLIC**: category vocabulary and counts, no text |
| StepStone.at, Indeed.at | nothing usable collected (HTTP 403); nothing published |
| `docs/linkedin-slot-interface.md`, `config/profile.json`, `library_strategy/` | **PRIVATE-ONLY** (D-026 (c)) |
| `posting_uid` in `Q03b`, `Q03c` | **PUBLIC as keyed hash** (the raw value is a source posting id) |
