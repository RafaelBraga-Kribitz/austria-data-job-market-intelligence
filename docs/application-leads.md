# Application leads — the private outreach file

`src/pipeline/build_application_leads.py` turns the posting dataset into one machine-readable
file for the application funnel: **`data/private/application_leads.json`**, git-ignored
(`data/private/`), never exported by `src/publish/export_public.py`.

It is the only artifact in this project that carries contact data. Everything else in
`outputs/` is aggregated. See `PUBLICATION_DECISION.md` for why that boundary exists.

```bash
python src/pipeline/build_application_leads.py                    # auto-detects what is available
python src/pipeline/build_application_leads.py --include-adjacent # + AI-software-engineering titles
python src/pipeline/build_application_leads.py --min-score 55     # triage: high-priority leads only
```

## Two modes

| Mode | Input | Record | Contacts |
|---|---|---|---|
| `postings` | `data/processed/postings_dedup.jsonl` (private) | one canonical posting | e-mail, person, position, phone, apply URLs — extracted from the advertisement text |
| `employers` | `outputs/tables/T04_employers.csv` (public) | one employer (387) | none; the ad text that holds them is not in a public checkout |

`--mode auto` (default) picks `postings` when the private file exists, `employers` otherwise. The
chosen mode and the reason are written into `meta.mode_explanation`, so a downstream agent can
tell an empty contact list from a missing one.

## What a lead contains

`company` · `contacts[]` · `contact_summary` · `job` (title, family, seniority, full ad text) ·
`status` (open / expired / unknown + `reverify_url`) · `source` (board, URL, also-seen-on,
collected_at) · `location` (city, Bundesland, Styria/Graz flags, remote type) · `salary`
(advertised minimum, basis, KV/all-in/bonus flags) · `requirements` (German and English wording,
experience, degree, skills by category) · `fit` · `outreach` · `scoring` · `pipeline`.

**`fit`** is the CV-tailoring block: matched `have` / `developing` skills from `config/profile.json`,
structural gaps, `cv_keywords_ranked` (the employer's own wording, ordered by how often Austrian ads
use it — T05), `german_risk`, `location_fit`, salary against the family median.

**`outreach`** is the cold-e-mail block: `channel`, `language` (de/en from the ad), `salutation`
(correct German form when the ad states one), `personalization_hooks`, and `template_slots` to fill
a letter template from.

**`scoring.apply_priority_score`** is a transparent weighted sum out of 100 — skills 30, language 25,
location 20, family priority 15 (D01 ranking), contactability 10 — with every component exposed in
`score_components`. It is an ordinal triage aid, in the spirit of `docs/decision-framework.md`: it
orders a worklist, it does not estimate a hiring probability. Tiers: A ≥ 65, B ≥ 48, C below.

**`pipeline`** is your own tracking state (status, stage, applied_at, cv_variant, follow_up_due,
notes). Re-running the builder **preserves it by `lead_id`** and only initialises new leads, so the
file can be both regenerated and used as the funnel's state.

## How contacts are extracted, and how far to trust them

Rules only, run over `description_text` and `description_html` (`find_emails`, `find_persons`,
`find_phones`, `build_contacts`), tested in `tests/test_application_leads.py`:

* e-mails from plain text, `mailto:` links and obfuscated forms (`name (at) firma (dot) at`);
* classified `personal` / `generic` (`bewerbung@`, `office@`, `hr@`, …) / `unknown`, with
  `domain_matches_company`;
* contact persons from salutations (`Frau`/`Herr`), academic titles and contact triggers
  (`Ansprechpartnerin`, `Bei Fragen`, `Your contact`, `send your application`), with the position
  next to the name (`HR Managerin`, `Talent Acquisition Manager`, `Leiterin …`);
* an e-mail is linked to a person when the local part matches the name, otherwise when both sit in
  the same text block (≤ 400 characters);
* Austrian phone numbers normalised to `+43…`.

Every contact keeps `evidence` (the snippet it was read from), a `confidence` label and
`verified: false`. **Read the evidence before you send anything**, then set `verified` yourself.
Nothing is inferred or guessed: no address, name or position appears that was not in the ad text.

## Boundaries

* The snapshot is **one day** (2026-09-16). `status.is_open` is `null` whenever the data cannot
  tell, and `requires_reverification` is true once the snapshot is over a week old — check
  `status.reverify_url` before applying. Do not re-run the posting collectors to refresh it
  (`DECISION_LOG.md` D-013).
* Advertised salary is a collective-agreement floor, not pay (`AGENT_CONTEXT.md` §8).
* The addresses were published so that candidates could apply — that is what they may be used for.
  A bulk unsolicited commercial mailing to them is a different act under DSGVO and TKG §174, and is
  not what this file is for.
* Never commit, sync or publish `data/private/`.
