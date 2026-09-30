# Supply research audit (Layer 2 / Layer 3, run of 2026-09-17/18)

Audit of what the candidate-supply research covered, what it could not cover, and how reliable each dimension is. Companion documents: `docs/supply-methodology.md` (design), `docs/supply-data-quality.md` (measured quality), `docs/supply-completeness-audit.md` (section-by-section checklist against the brief), `docs/legal-and-publication-audit.md` §10 (publication).

## Scope

| Requested dimension (brief §) | Covered? | How | Reliability |
|---|---|---|---|
| Candidate population per family (§4) | Yes, for GitHub | bio-declared (T1) families; repo-evidenced (T2) without family | family precision 78 % strict / 90 % lenient (SQ10) |
| Titles, raw and normalised, fragmentation (§5) | Yes | C02 (raw bio phrases ≥ 3 accounts), C03, C04b | raw phrases are bio openings, not job titles |
| Seniority (§6) | Partly | explicit bio words only; no years of experience | 68 % of bios carry no seniority word |
| Geography (§7) | Yes, frame-aware | state/city from free text; Styria complete, other regions sampled | 16.7 % of data-signal accounts name only "Austria" |
| Language supply (§8) | **Proxy only** | language written in bio/README | CEFR proficiency not observable; manual LinkedIn slot required |
| Technologies (§9) | Yes | bio + repo metadata + README with evidence strength | README rules tightened (D-021); proprietary tools under-observed |
| Capabilities (§10) | Yes | capability map with mentioned/used/demonstrated/project-demonstrated | professional experience not observable |
| Education (§11) | Partly | wording in bios/READMEs (level, field, institution) | 69 % of data-signal accounts show no education wording |
| Certifications (§12) | Partly | wording, capstone repos | absence ≠ none |
| Project supply, counts (§13) | Yes | project definition, per-candidate buckets | private repositories invisible |
| Project structure and metadata (§14) | Yes | topics, formats, README features, activity, stars, license, tree | contributors not fetched |
| Project topics (§15) | Yes | 4 theme groups, two-hit README rule | 38 % of projects carry no theme |
| Project formats (§16) | Yes | 22 formats from tree/text/homepage | text-triggered formats can over-count |
| README / writing patterns (§17) | Yes | 11 section types, 19 content features, common headings ≥ 5 projects | headings are English-centric |
| GitHub analysis (§18) | Yes | activity, stars, forks, archetypes, per-candidate medians | contributions to others' repos not fetched |
| LinkedIn positioning (§19) | **Not collected** | dark manual slot + LinkedIn-link share (20 %) | — |
| Vocabulary alignment (§20) | Yes | bio phrases vs employer titles; skill terms both sides; quadrants | different universes |
| Candidate density (§21) | Yes | candidates per open posting by family/state; Styria complete | one-day demand stock |
| Demand × supply matrix, quadrants, evidence (§22–24) | Yes | DS01–DS10 | medians as thresholds |
| Language / location / seniority / education joins (§25–28) | Yes | DS05–DS08, DS06b, DS13 | supply language = presentation |
| Project portfolio join (§29) | Yes | DS09, project_evidence_map.json | — |
| Positioning clusters (§30) | Yes | k-means, 8 clusters (C23, DS11) | descriptive |
| Transition candidates (§31) | Partly | explicit wording 3.4 %, prior-domain wording 38 % | weak signal |
| Marketing × data (§32) | Yes | C22d, C24, DS12 | small counts |
| Project opportunity engine (§33) | Yes | DS10 labels + project_evidence_map.json + operational-career-intelligence.md | evidence-based, not scored |
| Portfolio architecture (§34) | Yes | project-evidence-map.md | — |
| Writing intelligence (§35) | Yes | operational-career-intelligence.md §LinkedIn/CV/README | LinkedIn side missing |
| Raw data, data model, sources, quality hierarchy (§36–39) | Yes | private raw, schema, source table with quality tags | — |
| Temporal analysis (§40) | Single snapshot | push dates and account ages only | no time series |
| Sample bias, duplication (§41–42) | Yes | SQ tables, frames | cross-platform matching not attempted |
| Privacy/legal/publication (§43, §56) | Yes | legal audit §10, export guard | — |

## Source coverage

| Source | Status | Coverage consequence |
|---|---|---|
| GitHub | collected: 1,075 searches, 9,464 profiles (9,457 candidate accounts after dropping 7 organisation/bot logins), 126,013 repositories, 11,798 READMEs/trees, social accounts for data-signal users | only people who publish code; BI/Excel/SAP profiles largely invisible |
| Stack Overflow 2025 | collected: 410 Austrian respondents, ~29 data roles | tiny data-role n; self-selected |
| Eurostat | collected: graduates by field 2005–2024, employment by ISCO 2011–2025, ICT specialists | no regional grain |
| LinkedIn | not collected (terms) | positioning, languages with levels, experience years, transitions in career histories missing |
| Kaggle | not collected (credentials, terms) | competition activity only via GitHub links (9 % of P_data link Kaggle) |
| Portfolio sites | link presence only (35 % custom domain, 19 % GitHub Pages) | site content unread |
| Job-board candidate databases, Meetup, search-engine indexes | not used | — |

## Sampling

Three GitHub frames (A bio-signal, B complete Styria, C base-rate). Frame C offered 34,813 accounts in its slices but retrieved 6,187 (capped at 120 per slice): Vienna and the other cities are **samples**, Styria is complete. Ten queries hit the 1,000-result API cap (all in frame A/C large-token slices). Represented population: public GitHub accounts with an Austrian location string, not the Austrian data workforce; frame A over-represents accounts that describe themselves with data words (94 % have a bio vs 41 % in frames B/C).

## Deduplication

GitHub accounts are unique by id (0 duplicate ids, 0 duplicate repositories). 662 accounts were found in more than one frame and counted once. No cross-platform matching (single automated source); manual LinkedIn records would carry observer pseudo-ids and are not linkable by design.

## Classification

Bio → family: 78 % strict / 90 % lenient on 40 (SQ10). Repository → data project: 75 % strict / 92.5 % lenient on 40 substantive projects (SQ11). Skills: README rules tightened after review (D-021); "any evidence" figures remain inclusive, "project-demonstrated" figures are the conservative reading. Theme precision after the two-hit rule was not separately measured (spot checks only).

## Geographic coverage (Styria/Graz)

Styria is the only complete frame: 2,023 accounts with ≥ 1 repository, of which 247 data-signal (T1+T2) and 52 bio-declared; 50 of the 52 are in the Graz area (frame-B complete-Styria subset, C05c). The canonical Styrian counts are location-resolved across all frames: 248 data-signal, 56 bio-declared (C05a; D-027). Frame-B tokens also matched 11 accounts whose location resolved to another state (excluded from Styrian counts). Reliability: good for GitHub; unknown for the non-GitHub supply.

## Seniority, education, projects, GitHub, LinkedIn — observability

See the table in §Scope; the honest summary is: seniority and education are *partly* observable and only as wording; projects and GitHub activity are *fully* observable for public repositories; LinkedIn is *not* observable; language proficiency is *not* observable.

## Demand × supply denominators

Demand: 720 core postings (719 with description) of one day. Supply: 1,818 data-signal accounts / 872 bio-declared accounts. Both sides use the same taxonomies, so rankings and orders of magnitude are comparable; absolute ratios (candidates per posting) are comparable only within a frame and are dominated by the one-day demand stock (yearly Styrian flow ≈ 5 × the stock). No composite score is computed.

## Legal/privacy

Publishable: aggregates, code, methodology, Eurostat raw. Private: GitHub raw/processed rows, Stack Overflow extract, review samples, any LinkedIn manual records. Details: legal audit §10.

## What would most improve the evidence

1. Filling the manual LinkedIn slot for Graz/Vienna (languages with levels, years of experience, titles as employers see them).
2. A permitted re-collection in 3–6 months (same frames) for a first time series.
3. Larger Vienna base-rate slices (raise `per_slice_cap`) to turn Vienna lower bounds into estimates.
4. Extending the theme review to a labelled sample of 100 projects.
