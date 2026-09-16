# PUBLICATION_DECISION

**Decision (2026-09-16): PUBLICATION RECOMMENDED — for the sanitised research version only.**

The full repository (raw source records, processed posting files, posting collectors, private history) stays private. What is published is the version built by `src/publish/export_public.py`: code without the posting collectors, configurations, schemas, tests, documentation, decision documents, figures, aggregated tables and JSON summaries, with a fresh git history. This is a publication-readiness conclusion, not legal advice; the analysis behind it is `docs/legal-and-publication-audit.md`.

## 1. What was audited

* Repository structure, git tracking (251 files, one commit, no remote), file sizes (six tracked files above GitHub's 100 MB limit), `.gitignore`, ignored folders.
* Every raw JSONL envelope, the processed files, all output tables and JSON files, docs, code and configs — scanned for e-mail addresses, phone numbers, contact fields, secret-like tokens and credentials.
* The acquisition code (headers, cookies, tokens, throttling, endpoints) against each source's robots.txt and terms of use, fetched on 2026-09-16.
* GDPR, Austrian UrhG (§§ 42, 42h, 76c–76e), Directive 96/9/EC, Directive (EU) 2019/790, the CJEU database-right cases (C-203/02, C-202/12, C-30/14, C-762/19), C-101/01 *Lindqvist*, EDPB scraping guidance, Commission Decision 2011/833/EU, GitHub's terms and acceptable-use policy.
* The completeness of the original specification (`docs/original-specification-audit.md`) and the correctness of the headline claims (taxonomy precision audit, denominators, language and salary definitions).

## 2. What was found and removed from the public version

| Finding | Treatment |
|---|---|
| ≈2,400 distinct e-mail addresses, thousands of phone numbers and named contact persons of HR staff/AMS advisers inside advertisement texts; willhaben `contact` objects with first/last names | Personal data under GDPR. Never exported. Snippet columns that carried some of them removed from all public tables; export aborts if any address or phone pattern survives. |
| ≈12,400 verbatim advertisement texts, raw LinkedIn/jobs.at HTML pages, JobBarometer HTML | Third-party text and database contents. Never exported. |
| Per-posting tables with employer + salary + snippet (`T09e`), audit samples with snippets (`Q07a`, `Q07b`, `Q09`), per-posting URLs (`T16a`) | Excluded; every column matching `snippet|description|url|html` dropped elsewhere. |
| The six posting collectors (EURES, EURES regional sweep, karriere.at, jobs.at, LinkedIn, willhaben) | All five posting sources restrict automated extraction in their terms; LinkedIn's User Agreement prohibits developing or supporting scraping software; willhaben and LinkedIn disallow the used paths in robots.txt. Collectors stay private; the methodology is documented in prose. |
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
| Contractual / terms of service | MEDIUM (residual) — the *collection* ran against the sources' terms; publishing statistics is not itself restricted by any fetched clause, but the methodology discloses the collection. Mitigated by not distributing the collectors, by stating the restriction openly (D-013) and by the non-commercial, non-substituting character. |
| Technical access | LOW — no circumvention; documented politely |
| Source republication | LOW — none |
| Reputational / professional | LOW–MEDIUM — the honest disclosure of the terms conflict is the credible posture; a scraper published under the author's name would not be |
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

## 7. Validation performed before publication (recorded in the final report)

* Full pipeline re-run after the taxonomy fix; 67 tests pass.
* Digest consistency check: every figure quoted in the documents matches `outputs/`.
* `src/publish/export_public.py` completes with zero problems (no e-mail, phone, secret-like token or free-text cell in the export).
* Independent scan of the exported tree; size check; fresh git history; push; verification of visibility, README rendering and tree; clean clone in a temporary directory with `pip install -r requirements.txt`, `python -m pytest tests -q` and `python src/reporting/digest.py`.

Decision recorded in `DECISION_LOG.md` D-014.
