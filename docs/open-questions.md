# Open questions

Questions the two original briefs asked (or that the answers themselves raised) which **cannot be answered with the data this project holds**. Registered rather than dropped, because an unanswered question that is written down is a research plan, and one that is not is a silent hole a future reader will mistake for a finding.

Each entry states: its status, what is being asked, why the current data cannot answer it, what evidence is missing, what would close it, and whether anything hard blocks that path.

**Status values.** **open** — a closing path exists and has not been taken · **structural** — the observation cannot contain the answer; only bounding or external context is possible · **will-not-do** — closable in principle, deliberately not done · **closed** — resolved, with the decision named.

**Barrier classes used below**

| Class | Meaning |
|---|---|
| **effort** | No legal or technical obstacle; needs time, labelling or a second collection |
| **technical** | A source refuses automated access (403, WAF, login wall) and this project does not bypass such barriers (D-013, D-022) |
| **contractual** | A platform's terms forbid automated collection; manual, owner-run entry may remain permitted |
| **regulatory** | GDPR or another legal regime constrains what may be collected, linked, retained or published |
| **structural** | The question asks for something the observation itself cannot contain, whatever the sample size |

Added 2026-09-21 (DECISION_LOG D-025); OQ-20–OQ-24 added and statuses assigned 2026-09-30. Cross-referenced from `docs/question-coverage-audit.md`.

**Register as of 2026-09-30: 24 entries — 17 open, 4 structural, 1 will-not-do, 2 closed (OQ-14, OQ-19).**

| ID | Question (short) | Group | Status | Barrier |
|---|---|---|---|---|
| OQ-01 | Does German change my hiring probability? | 1 outcome | open | effort |
| OQ-04 | Are stated requirements negotiable? | 1 outcome | open | effort |
| OQ-06 | Which portfolio evidence changes interview rates? | 1 outcome | open | effort / structural |
| OQ-02 | Candidate language levels | 2 blocked source | open | contractual, regulatory |
| OQ-03 | Share of demand invisible to the dataset | 2 blocked source | open | technical, contractual |
| OQ-13 | LinkedIn positioning | 2 blocked source | open | contractual, regulatory |
| OQ-14 | Kaggle supply | 2 blocked source | closed (D-030) | contractual, structural |
| OQ-17 | Research licence from a board | 2 blocked source | open | effort |
| OQ-09 | Recall of the title taxonomy | 3 cheap to close | open | effort |
| OQ-12 | Quality of candidate projects | 3 cheap to close | open | effort |
| OQ-16 | Skill-extractor false negatives | 3 cheap to close | open | effort |
| OQ-20 | Industry concentration of demand | 3 cheap to close | open | effort |
| OQ-22 | Accuracy of German-requirement and salary extraction | 3 cheap to close | open | effort |
| OQ-23 | Multinational vs Austrian employers | 3 cheap to close | open | effort |
| OQ-05 | Actual compensation | 4 structural | structural | structural |
| OQ-07 | Market change over time | 4 structural | open | effort (second snapshot) |
| OQ-08 | The actual candidate workforce | 4 structural | structural | structural, regulatory |
| OQ-10 | Same people across platforms | 4 structural | will-not-do | regulatory, project rule (D-020) |
| OQ-11 | Seniority vs actual experience | 4 structural | open | contractual, regulatory |
| OQ-15 | Repeat hiring, employer dynamics | 4 structural | open | effort (second snapshot) |
| OQ-18 | Owners of the 140 anonymous postings | 4 structural | structural | structural |
| OQ-21 | Agency ads double-counting client vacancies | 4 structural | structural | structural |
| OQ-24 | GitHub collaboration evidence | 4 structural | open | effort (next GitHub collection) |
| OQ-19 | Styrian bio-declared denominator | 5 definitions | closed (D-027) | — |

---

## Group 1 — Outcome questions: the project observes requirements and evidence, never results

### OQ-01 · Does German proficiency change my probability of being hired?

**Status.** open.

**Why open.** Every language finding in this project (BQ12, BQ34) measures what advertisements *state*. Nothing in the corpus records what happened to an applicant. The strongest supportable claim is the one the decision map makes: German is the most frequently stated non-technical barrier in Styrian ads. "Most frequently stated barrier" is not "the single largest lever", and this project must not upgrade the one to the other.

**Missing.** Application-level outcomes paired with the stated requirement: posting id, stated German level, channel, application date, response, interview, offer.

**How to close.** An application log kept by the owner (fields: `schemas/application_log_schema.md`; private template `data/private/application_log.csv`) — one row per application, the posting's stated requirement copied from the ad, the outcome updated as it arrives. Roughly 50-100 applications gives a directional read on response rates by stated requirement; it will never give a clean causal estimate, because the applicant is not randomised across ads.

**Barrier.** effort. The log is the owner's own data about their own applications, so no third-party constraint applies. The limitation that survives is structural: a single applicant cannot separate the effect of German from the effect of everything else on their CV.

### OQ-04 · Are stated requirements negotiable?

**Status.** open.

**Why open.** An advertisement states a requirement; it does not reveal whether the employer would proceed without it. The 40 % of ads stating a German requirement and the 32 % requiring a degree may or may not be applied as written in screening.

**Missing.** Recruiter or hiring-manager statements about how requirements are applied, or outcomes from applications that did not meet a stated requirement.

**How to close.** Structured informational conversations with Austrian recruiters in the target families, recorded as aggregate notes; or the outcome log from OQ-01 (`schemas/application_log_schema.md`) filtered to applications that did not meet a stated requirement.

**Barrier.** effort. Conversations are small-n and self-selected; treat as context, not measurement.

### OQ-06 · Which portfolio evidence changes interview rates?

**Status.** open.

**Why open.** BQ21, BQ23 and BQ24 establish what is demanded and what is rarely demonstrated. They cannot establish that closing that gap changes an outcome — the supply side is cross-sectional and outcome-free.

**Missing.** Applications paired with the state of the portfolio at the time of applying.

**How to close.** The OQ-01 log (`schemas/application_log_schema.md`), with a portfolio-version field (which projects existed, which were documented).

**Barrier.** effort, and structural: confounding with everything else that changes over a job search.

---

## Group 2 — Blocked-source questions: the evidence exists but cannot be collected automatically

### OQ-02 · What languages, at what levels, does the competing candidate pool actually hold?

**Status.** open.

**Why open.** This is the single largest hole in Layer 3. The demand side of the language question is measured in detail (BQ12, BQ34, BQ13); the supply side is empty. GitHub bios are 99 % English regardless of the author's German, and public code carries no CEFR level. The intersection the brief asked for — "English-only candidates competing for English-only Styrian ads" — therefore cannot be computed.

**Missing.** Candidate-level language declarations with levels, plus location and role, for the Graz and Vienna pools.

**How to close.** The private LinkedIn slot built for exactly this: `src/acquisition/ingest_linkedin_manual.py` writes and validates the templates, `docs/supply-methodology.md` §7 defines the protocol, and since D-026 the slot accepts any permitted channel tagged by `acquisition_method` (hand-coding, or a licensed export such as Talent Insights, which would fill the Graz/Vienna language counts at once; contract in `docs/linkedin-slot-interface.md`, private). Aggregates only, no member-site automation (rejected by the ingest), no individual publication. Even 100-200 hand-entered Graz-area profiles would turn this from unmeasured into bounded. The slot is still empty (2026-09-30).

**Barrier.** contractual and regulatory. LinkedIn's User Agreement 8.2 forbids automated collection, and profile data is personal data under GDPR, so the manual, aggregate-only route is the *only* permitted one (D-018). This is a hard barrier against automation and a soft one (effort) against the manual path.

### OQ-03 · What share of Austrian data demand is invisible to this dataset?

**Status.** open.

**Why open.** BQ30 names the missing sources; it cannot size them. StepStone.at and Indeed.at returned HTTP 403 to a plain client, and company career pages, hokify, university and public-sector portals were never collected. The corporate white-collar segment is therefore under-covered by an unknown amount. The one external anchor available — the AMS yearly series — suggests the Styrian share may be understated (13.6 % of official flow against 7.5 % here).

**Missing.** At least one corporate-heavy board, or a sample of employers' own career pages, collected through a permitted channel and measured for overlap with the 720.

**How to close.** In ascending order of cost: (a) compare family and regional shares against AMS JobBarometer classes as an external anchor — partially done (BQ02, JB05); (b) request research or API access from a board (see OQ-17); (c) sample N Austrian employers' own career pages where their robots policy and terms permit, and measure how many of their open data roles appear in the 720; (d) devjobs.at and derStandard Jobs, marked "deferred" in the 2026-09-16 source probe (D-001, `PROGRESS.md`) and never revisited — an include/exclude decision is still owed.

**Barrier.** technical (403/WAF, which this project does not bypass) and contractual (board terms restrict automated extraction). Path (c) is governed employer by employer.

### OQ-13 · What does LinkedIn positioning actually look like?

**Status.** open.

**Why open.** Brief 2 §19 asked for headline, About-section, skills-section and transition-signal patterns. None was collected: LinkedIn people data is out of scope by decision (D-018).

**Missing.** Aggregate patterns over public professional profiles.

**How to close.** The same slot as OQ-02, with the profile-structure fields (`headline`, `transition_wording`, `skills_listed`) recorded alongside the language fields. Only `manual_ui` yields free-text positioning; aggregate exports do not carry it (`docs/linkedin-slot-interface.md` §1, private).

**Barrier.** contractual and regulatory, as OQ-02.

### OQ-14 · What does the Kaggle side of the supply look like?

**Status.** closed 2026-09-30 (D-030) — contractual and structural.

**Resolution.** Kaggle's Terms of Use (22 June 2025) forbid crawling or scraping by manual or automated means, with no research exception; the official API and Meta Kaggle are permitted but carry no user location, so no permitted route yields Austrian aggregates. Kaggle is not collected; "9 % of GitHub candidates link a Kaggle profile" (a link type, no profile visited) is the only Kaggle measure. Reading: `docs/kaggle-terms-review.md`.

**Why it was open.** Kaggle was named in brief 2 §38 and never collected; only the *links* to Kaggle from GitHub profiles are observed (9 % of candidates).

**Missing.** Kaggle profile and notebook aggregates for Austrian users.

**How to close.** A terms review of the Kaggle API followed by an aggregate-only collection, if it clears; otherwise leave measured as "9 % of GitHub candidates link a Kaggle profile" and nothing more.

**Barrier.** contractual (terms review done 2026-09-30) and structural (no location in any permitted channel).

### OQ-17 · Would a rights-holder grant a research licence?

**Status.** open.

**Why open.** The publication analysis treats the boards' terms as fixed constraints. Nobody has asked any of them for permission.

**Missing.** A written request and a written answer.

**How to close.** Write to karriere.at, StepStone.at and jobs.at describing the non-commercial research use, the aggregate-only publication model and the retention policy, and ask for an exception or an API key.

**Barrier.** effort only. The worst outcome is a "no" that is itself documentable evidence for the limitations section. Letter drafts exist privately (`data/private/letters/`); none has been sent (2026-09-30).

---

## Group 3 — Cheap to close: answerable with data already held

Sampling and scoring for OQ-09, OQ-12, OQ-16 and OQ-22 is scripted in `src/analysis/labelling_audit.py` (blind samples to `data/labels/<date>/`); protocol, label codes and time estimates in `docs/labelling-protocol.md`. The aggregate result tables `Q10`–`Q12` appear once the owner's labels are scored.

### OQ-09 · What is the recall of the title taxonomy?

**Status.** open.

**Why open.** Q03c measured **precision** — of the titles the classifier put into a family, how many belong. It never measured **recall** — of the data roles in the corpus, how many the classifier found. A systematically missed title pattern (an unusual German compound, an internal job-title convention) would shrink the 720 without leaving any trace in the precision audit.

**Missing.** A hand-labelled random sample of postings drawn from *all* 10,945 canonical rows, including out-of-scope ones.

**How to close.** Draw 300 canonical postings at random, label each "is this a data role in the project's sense", and compute recall against the classifier's decision. The data is already retained privately; the work is a few hours of labelling and a small script. This is the single cheapest improvement to the evidence base and it bounds the one error direction currently unbounded.

**Tooling.** `docs/labelling-protocol.md`, `src/analysis/labelling_audit.py`; results land in `Q10`–`Q12` once labels are scored.

**Barrier.** effort only.

### OQ-12 · What is the quality of candidate projects, not just their structure?

**Status.** open.

**Why open.** BQ23, BQ24 and BQ42 detect structure — formats, sections, activity, archetype. Whether a project is *good* is not rule-detectable, so "66 % have a how-to-run section" says nothing about whether the analysis underneath it is sound.

**Missing.** Human judgement on a sample, against a fixed rubric.

**How to close.** Hand-rate 40 substantive projects drawn at random against a short rubric (question stated, method appropriate, result quantified, limitations acknowledged, reproducible), and report the association between detectable structure and rated quality. That also calibrates how much the structural findings can be trusted as quality proxies.

**Tooling.** `docs/labelling-protocol.md`, `src/analysis/labelling_audit.py`; results land in `Q10`–`Q12` once labels are scored.

**Barrier.** effort, plus a publication constraint: ratings of identifiable third-party repositories stay private and only aggregates are published (D-020 forbids ranking individuals).

### OQ-16 · How many skill mentions does the extractor miss?

**Status.** open.

**Why open.** The skill vocabulary was revised twice (D-012 demand side, D-021 supply side) and false *positives* were measured both times. False *negatives* — a skill present in the text but absent from the vocabulary, or written in a form the pattern does not match — were never measured.

**Missing.** A hand-labelled sample of descriptions read for skills that the extractor did not flag.

**How to close.** Take 50 core postings, read them for the D04 skill set, compare against the extractor's output, and report per-skill recall. Same pattern as OQ-09 and can be done in the same sitting.

**Tooling.** `docs/labelling-protocol.md`, `src/analysis/labelling_audit.py`; results land in `Q10`–`Q12` once labels are scored.

**Barrier.** effort only.

### OQ-20 · Which industries carry the data demand?

**Status.** open.

**Why open.** An industry field exists only on LinkedIn rows (`T04c`); AMS/EURES, karriere.at, willhaben and jobs.at rows carry none, so industry concentration rests on business-domain wording in the ad text (`T05` business_domain). Registered from `docs/original-specification-audit.md` §B (PARTIALLY COMPLETE).

**Missing.** An industry code per posting.

**How to close.** Code the 387 named employers to a NACE section once (one employer-attribute table, shared with OQ-23), or use the EURES NACE facets where present; report the 140 unnamed postings as their own bucket.

**Barrier.** effort.

### OQ-22 · How accurate are the German-requirement and salary extractors?

**Status.** open.

**Why open.** Title precision (Q03c) and skill false positives (D-012, D-021) were measured; the German-requirement class (`T07`) and salary parsing (`T09`) were checked by spot checks only (`docs/original-specification-audit.md` §B, §D). OQ-16 covers skills only.

**Missing.** A hand-labelled sample for requirement class and parsed salary figure.

**How to close.** Label 100 core descriptions for German requirement class (required / level-stated / preferred / mentioned / none) and the salary minimum and period; report precision and recall per class. Same sitting as OQ-09 and OQ-16.

**Barrier.** effort only.

### OQ-23 · Do multinational and Austrian employers ask for different things?

**Status.** open.

**Why open.** Rated WEAK in `docs/original-specification-audit.md`: no ownership attribute exists; posting language and the LinkedIn industry field are only proxies.

**Missing.** Ownership / headquarters country per named employer.

**How to close.** The employer-attribute table of OQ-20 with an ownership column, coded by hand for the 387 named employers, joined on employer name; compare `T05`/`T07` shares. Unnamed postings stay unassigned.

**Barrier.** effort.

---

## Group 4 — Structural: the observation cannot contain the answer

### OQ-05 · What is actual compensation, as opposed to the advertised floor?

**Status.** structural.

**Why open.** 81 % of parsed figures are a single collective-agreement minimum (BQ32), and 53 % of ads say they pay above it without saying how much. BQ45 shows that even the *relative* differences between skills mostly dissolve once family and seniority are controlled. Advertisements cannot yield offers.

**Missing.** Offer-level data, or a salary survey for Austrian data roles with a published methodology and role granularity.

**How to close.** Keep third-party survey context strictly separate (`docs/salary-context.md` already does this), and treat own offers, when they exist, as the only first-party evidence.

**Barrier.** structural. No advertisement contains the answer.

### OQ-07 · How is the market changing?

**Status.** open.

**Why open.** Layer 1 is a one-day stock; Layer 2 is one collection. The only time series in the project is the AMS yearly series (BQ02), which uses a coarser occupation class than this taxonomy. Every "is X growing" question — LLM project saturation, German requirements, Power BI in Styria, candidate crowding — is currently unanswerable.

**Missing.** A second snapshot of each layer, collected the same way.

**How to close.** Re-run Layer 1 through permitted channels and Layer 2 through the GitHub API on the cadence the README already recommends (3-6 months), into new dated folders, never merged with 2026-09. The schemas and the `run_id`/vintage fields already support this; `src/pipeline/snapshot_tracking.py` folds each Layer 1 snapshot into a first-seen/last-seen history keyed on `posting_uid` (stable across runs; `dedupe_group_id` is not and must never be used as a key).

**Barrier.** effort, within the collection rules of D-013/D-022.

### OQ-08 · What does the actual Austrian candidate workforce look like?

**Status.** structural.

**Why open.** The supply side is a public-profile sample, not a census. GitHub over-represents engineers, researchers and students, and is structurally blind to BI, Excel and SAP practitioners — the very families where demand is thick and observed supply looks thin (BQ20, BQ21). A low observed density is therefore part real scarcity and part invisibility, and this project cannot separate the two.

**Missing.** A frame that covers people who do not publish code.

**How to close.** Official aggregates as an external anchor: AMS registered-jobseeker counts by occupation (AMDB / AMIS), the Statistik Austria Mikrozensus labour-force survey (AKE; ISCO 25, 2120, 3314 by Bundesland), the Abgestimmte Erwerbsstatistik and university statistics, plus the Stack Overflow Austrian subsample already ingested (n = 410, O04-O08). None of the official anchors has been fetched (2026-09-30). None resolves the question; together they bound it.

**Barrier.** structural, plus regulatory for anything individual-level: AMS jobseeker microdata is not public.

### OQ-10 · Are the same people counted across platforms?

**Status.** will-not-do.

**Why open.** Deduplication is GitHub-internal. Linking a GitHub account to a LinkedIn or Kaggle profile is identity resolution on personal data.

**Why it will stay open.** D-020 forbids ranking or scoring individuals, and cross-platform linkage is exactly the profiling step that would make that possible. The decision is not to do it.

**Barrier.** regulatory, and a deliberate project rule. This one is closed by choice, not by lack of means.

### OQ-11 · How does candidate seniority relate to actual experience?

**Status.** open.

**Why open.** BQ25 compares seniority *wording* on both sides. GitHub shows account age, not career length, so a bio saying "senior" cannot be checked and the title-to-experience mismatch the brief asked about cannot be measured.

**Missing.** Career chronology per candidate.

**How to close.** The manual LinkedIn slot (OQ-02) carries employment history; account age can serve as a weak public proxy if its limitations are stated.

**Barrier.** contractual/regulatory, as OQ-02.

### OQ-15 · Which employers hire repeatedly, and how does employer demand move?

**Status.** open.

**Why open.** BQ33 shows employer structure on one day. Repeat hiring, replacement cycles and hard-to-fill roles all need first-seen/last-seen dates per posting.

**Missing.** Longitudinal posting identity across snapshots.

**How to close.** The repeat collection of OQ-07, keyed on `posting_uid` and employer, gives first-seen/last-seen and therefore time-to-fill signals; `src/pipeline/snapshot_tracking.py` builds that history (with left/right-censoring flags) once a second snapshot exists.

**Barrier.** effort.

### OQ-18 · Do the 140 anonymous postings belong to the 387 named employers?

**Status.** structural.

**Why open.** All 140 employer-less postings are AMS/EURES rows where the employer is deliberately withheld. They may be the same firms already counted, or firms absent from the named list entirely. Nothing in the record distinguishes the two, which is why "387 named employers" is reported as a lower bound on employers represented (BQ33).

**Missing.** Employer identity on the anonymous rows.

**How to close.** Nothing available: the anonymisation is the source's own policy. Text-similarity matching against named ads would be inference dressed as measurement and is not worth the false precision.

**Barrier.** structural.

### OQ-21 · Do agency ads double-count client vacancies?

**Status.** structural.

**Why open.** Agency ads are flagged (4.5 % of named postings, BQ33) but not linked to the client's own ad; deduplication keys on company + title + state and a description fingerprint, which does not match across agency and client wording. Registered from `docs/original-specification-audit.md` ("agency-client linkage impossible").

**Missing.** The client's identity on agency ads.

**How to close.** Nothing reliable: the agency withholds the client. The agency share bounds the possible double count from above.

**Barrier.** structural.

### OQ-24 · Do candidates show collaboration evidence (contributors, issues, releases, contributions to others' repositories)?

**Status.** open.

**Why open.** The 2026-09-17 API budget covered profiles, owned repositories, READMEs and social links only (`docs/supply-completeness-audit.md` §14, §18). Team work and open-source contribution are therefore unmeasured.

**Missing.** Contributor, issue and release counts per data repository; contribution events per account.

**How to close.** Add these endpoints to the next GitHub collection (OQ-07 cadence), for P_data repositories only.

**Barrier.** effort (API rate limits; GitHub AUP §7 re-check as for any collection).

---

## Group 5 — Definitions

### OQ-19 · Which Styrian bio-declared count is the intended denominator, 52 or 56?

**Status.** closed 2026-09-30 (D-027).

**Resolution (2026-09-30, D-027).** The canonical Styrian bio-declared count is **56** (location-resolved: `C05a`, `DS01`, `DS05`). **52** is the complete-Styria frame-B subset (`C05c`, `DS13`) and is quoted only with that label. The same rule applies to data-signal accounts (**248** location-resolved vs **247** frame B) and all accounts (**2,033** vs **2,023**). Postings: 54 Styria / 343 Vienna by primary state (`T03a`) vs 58 / 350 by the location flag (`market_summary.json`); count and share are quoted on the same basis. No table was recomputed; the prose in README, AGENT_CONTEXT, `CAREER_SUPPLY_DEMAND_MAP.md` and `docs/supply-findings.md` was corrected.

**Why it was open.** An unresolved definition, found while building BQ20 and BQ37. Two published tables count the Styrian bio-declared population differently:

| Table | Styrian T1 count | What it counts |
|---|---|---|
| `C05c_styria_complete_frame.csv` | **52** | T1 accounts inside the complete Styrian frame (frame B: every Styrian account with a public repository) |
| `C05a_geo_summary.csv`, `DS01`, `DS05` | **56** | every P_T1 account whose resolved location is Styria, whichever frame found it |

The four-account difference is Styria-located accounts discovered through the bio-keyword frame rather than the complete-Styria frame. Both counts are defensible; only one can be "the" Styrian denominator.

**Where it showed (before D-027).** `README.md` and `CAREER_SUPPLY_DEMAND_MAP.md` §10 quoted **52**, and `docs/supply-findings.md` §3 quoted 52 in its sentence while enumerating families that sum to **56** ("data science 38, analytics 7, engineering 4, BI 3, business analysis 2, governance 1, marketing 1"). That sentence was internally inconsistent whichever definition was chosen. The DS tables, and therefore BQ20 and BQ37, use 56 because that is what the joined tables contain.

**How it was to be closed.** An owner decision recorded in `DECISION_LOG.md`: either (a) the Styrian T1 denominator is the complete-frame count (52) and `C05a`/`DS01`/`DS05` should be recomputed to match, or (b) it is the location-resolved count (56) and the prose in the three documents should be corrected. Then re-run the digest so the quoted numbers and the tables agree again.

**Barrier.** effort, and small: one definition, one recomputation, one prose pass. It is registered here rather than fixed silently because choosing a denominator is a methodological decision, not a typo, and D-020's discipline is that such decisions are recorded before they are applied.

**Why it matters more than four accounts.** Every Styrian density in Layer 3 divides by this number. At n = 56 the data-science density is 2.9 per posting (38 of the 56 are data scientists); on the frame-B basis it moves, and the Styrian statements are already the most fragile in the project (BQ29).


## What to do first

The smallest fix, OQ-19, was closed by D-027 and OQ-14 by D-030, both on 2026-09-30. Of the open entries, if only three are ever closed, these three change the most:

1. **OQ-09 (recall)** — the only unbounded error direction in the demand layer, closable in an afternoon with data already held.
2. **OQ-02 (candidate language)** — the largest structural hole in Layer 3, and the one the manual LinkedIn slot was built for.
3. **OQ-01 (outcomes)** — converts the whole project from a map of stated requirements into evidence about what actually works, and costs nothing but a disciplined log from the first application onwards.
