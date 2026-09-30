# Schema: Layer 2 candidate-supply tables (private, individual level)

Built by `src/pipeline/build_supply.py` from the private raw collection `data/raw/github_supply/<date>/` and, when present, the LinkedIn slot tables `data/processed/supply_linkedin_profiles.csv` and `supply_linkedin_counts.csv` written by `src/acquisition/ingest_linkedin_manual.py` (section "LinkedIn slot records" below). Files: `data/processed/supply_candidates.{jsonl,parquet}`, `supply_projects.{jsonl,parquet}`, `supply_skill_evidence.parquet`, `supply_build_manifest.json`. **None of these files is exported**; the public repository carries only the aggregated `C*`, `O*`, `DS*` tables, figures and JSON summaries. Field names are stable; new fields may be appended. Lists/dicts are JSON strings in the parquet files.

Unit of observation: **one public GitHub user account with a profile fetched on the collection date**, or **one coded LinkedIn slot record** (`source = linkedin_manual`) (`candidate`), **one owned, non-fork repository classified as a data repository** (`project` table; `is_project` marks those meeting the project definition), and **one (candidate, canonical skill) pair** (`skill_evidence`). A candidate is not a person in the census sense: accounts can be inactive, non-professional, or belong to people who have since left Austria (see docs/supply-data-quality.md).

## candidate

| field | type | description |
|---|---|---|
| candidate_id | str | sha1 of `github:<numeric id>` or `linkedin_manual:<pseudo_id>` (16 hex); the only identifier that may appear in aggregate outputs (it never does at row level) |
| source | str | `github` · `linkedin_manual` |
| source_quality | str | A–E (docs/supply-methodology.md §2): GitHub API = B; LinkedIn slot rows carry the resolved grade of their row (`manual_ui` = C) |
| login | str | GitHub login (private only; traceability) |
| collection_date | date | folder date of the raw collection |
| frames | list[str] | sampling frames the account was found in: A bio-signal · B Styrian complete · C base-rate sample (· L manual LinkedIn) |
| n_search_hits | int | number of search rows that returned this account (coverage signal) |
| bio, bio_chars, has_bio | str/int/bool | profile bio as stored (private) |
| company, has_company | str/bool | free-text company field (private); presence only in aggregates |
| blog, has_blog, hireable, twitter | str/bool | website field (private) and its presence flag (kept after redaction), GitHub "available for hire" flag, has X/Twitter handle |
| public_repos, public_gists, followers, following | int | profile counters |
| account_created, account_age_years, profile_updated | ISO/float | account chronology (collection date minus creation) |
| location_text | str | free-text location (private) |
| state, city | str | Bundesland / city via config/geo.json + supplementary city list; `unspecified (Austria)` when only the country is named |
| is_styria, is_graz_area, is_graz_city, is_vienna | bool | geography flags (Graz area = config/geo.json graz_commute) |
| austria_named, foreign_place_named, multi_location, geo_confidence | bool/str | location evidence; `geo_confidence` ∈ state_and_city · state_only · austria_only · none |
| bio_role_family, bio_normalized_title, bio_role_rule | str | Layer 1 role family/title assigned from the bio (bio overrides in config/supply_taxonomy.json, then config/role_taxonomy.json rules); rule provenance incl. `after_transition:` when the bio states a career change |
| seniority_bio | str | student · junior · unlabelled · senior · lead_head · unknown (no bio); explicit wording only |
| is_student, is_academic | bool | bio wording |
| transition_explicit, prior_domains | bool/list | career-transition wording; prior domain groups named in the bio (marketing, business, finance, engineering, science, economics, statistics, software, social) |
| bio_language | str | de/en from the Layer 1 stop-word classifier (bios > 40 chars) |
| bio_edu_levels, bio_edu_fields, bio_edu_institutions | list | education wording in the bio |
| bio_certifications, project_certifications, certifications_any | list | certification wording in bio / project metadata+README / union |
| bio_skills, bio_soft | list | Layer 1 vocabulary hits in the bio (technical / soft) |
| links_profile, links_any, has_personal_site, social_accounts_fetched | list/bool | cross-platform link *types* (linkedin, kaggle, personal site, medium, tableau public, huggingface, …) from website field, GitHub social accounts and project READMEs; URLs stay private |
| n_repos_listed, n_repos_owned, n_forks, repos_truncated | int/bool | repository counts (owner repos, up to 300 fetched) |
| repo_languages | dict | primary-language counts over owned repos |
| last_push, n_active_12m, stars_total, max_stars | ISO/int | activity and popularity of owned repos |
| n_data_repos | int | owned non-fork repos classified as data repositories (config/supply_taxonomy.json data_repo_lexicon) |
| n_projects | int | data repos meeting the project definition (README ≥ 300 chars, or ≥ 1 star, or a description) |
| n_documented_projects | int | projects with README ≥ 1,000 chars |
| n_substantive_projects | int | documented and not flagged educational |
| n_educational_repos | int | data repos flagged as course/tutorial/learning work |
| archetypes, project_themes, project_formats, readme_languages | dict | counts over the candidate's data repos |
| subst_themes, subst_formats | dict | as project_themes / project_formats, over substantive projects only |
| edu_levels_any, edu_fields_any, edu_institutions_any | list | union of bio and README education wording |
| skills_used, skills_demonstrated, skills_project_demonstrated, skills_any | list | canonical skills by evidence strength (see skill_evidence) |
| data_tier | str | T1_bio_declared · T2_repo_evidenced · T3_weak_repo_signal · T0_none (rules in config/supply_taxonomy.json evidence_rules) |
| is_data_signal | bool | tier T1 or T2 — the "observed data-signal candidate" population used for supply shares |
| redacted | bool | set by `src/pipeline/redact_supply_raw.py` (jsonl and parquet) when the personal fields above were nulled; absent/false otherwise |

## project

| field | type | description |
|---|---|---|
| project_id, candidate_id | str | sha1 of the repository id; owner |
| repo_full_name, name, description, topics, language, homepage flags | mixed | repository metadata (private) |
| stars, forks, size_kb, archived, license, has_pages | mixed | popularity / packaging |
| created_at, pushed_at, months_since_push, is_active_12m | mixed | activity |
| data_reason | str | why it was classified as a data repo: language · topic · keyword:<word> |
| readme_fetched, readme_status, readme_chars, readme_words, readme_headings, readme_length_bucket, readme_language, readme_heading_list | mixed | README size and structure (after redaction `readme_heading_list` keeps only headings used ≥ 5 times in the table) |
| tree_entries | int | number of top-level tree entries fetched (null when no tree was fetched) |
| rd_h_* | bool | heading-based README sections: objective_overview, business_context, data_source, methodology, results, limitations, reproducibility, tech_stack, structure, author_contact, visuals_section |
| rd_* | bool | README content features: has_image, has_badge, has_code_block, has_table, has_link_dashboard, has_link_kaggle, has_link_linkedin, has_link_medium_blog, has_link_colab_binder, has_doi_arxiv, mentions_metrics, mentions_business_terms, mentions_limitations, mentions_tests_ci, mentions_docker, mentions_deployment, mentions_reproduce_cmd, german_text, first_person_narrative |
| formats | list | packaging formats (notebook, r_markdown_quarto, python_package_or_src, streamlit_gradio_app, web_app, api, dashboard_bi, pipeline_project, docker, tests, ci, reproducible_env, data_included, docs_folder, report_pdf_slides, sql_files, license, makefile_scripts, model_artifacts, paper_academic, competition_kaggle, gh_pages_site) |
| themes_analytics_domain, themes_ds_method, themes_engineering, themes_ai | list | project topics (config/supply_taxonomy.json project_topics) |
| skills, certifications, readme_edu_levels, readme_edu_institutions, links_readme | list | Layer 1 vocabulary hits on name+description+topics+README; certification/education wording; link types |
| is_educational, is_project, is_documented, is_substantive | bool | flags (definitions above) |
| is_contribution_like | bool | reserved for contribution-style repositories; always false in the current build (owned non-fork repos only) |
| redacted | bool | set by the redaction: `repo_full_name` pseudonymised (sha1 of `github_repo:<full name>`), `name` / `description` nulled |
| archetype | str | inactive_archive · open_source_contribution · educational_tutorial · production_style_application · data_engineering_project · ml_project · dashboard_project · analytics_project · notebook_portfolio · other_data |

## skill_evidence (long)

| field | type | description |
|---|---|---|
| candidate_id, skill, category | str | Layer 1 canonical skill and its taxonomy category |
| mentioned | bool | in the bio |
| used | bool | in the name/description/topics or primary language of an owned non-fork repository |
| demonstrated | bool | in a documented data project (README ≥ 1,000 chars) or its primary language |
| project_demonstrated | bool | as above and the project is not educational |
| data_tier | str | candidate tier |

## demand_supply_join (aggregate, public: DS* tables)

| field | description |
|---|---|
| dimension, category | e.g. `skill`, `SQL` · `role_family`, `data_science` · `state`, `Steiermark` |
| demand_count, demand_n, demand_share | Layer 1 posting count, denominator and share (T* table quoted in `demand_table`) |
| supply_count, supply_n, supply_share | Layer 2 candidate count, denominator (population named in `supply_population`) and share |
| project_count, project_n, project_share | candidates with project-demonstrated evidence / candidates in population |
| difference_pp, relative_representation | supply_share − demand_share (percentage points); supply_share / demand_share |
| quadrant | A high-demand/high-supply · B high-demand/lower-supply · C lower-demand/high-supply · D lower/lower (thresholds stated in the table) |
| supply_ci_low, supply_ci_high | Wilson 95 % interval on the supply share |
| source_quality, interpretation | quality tags of both sides; short reading rule |

## LinkedIn slot records (dark slot)

Full contract, value domains, per-channel coverage and validation rules: the private `docs/linkedin-slot-interface.md` (not in the public export). `acquisition_method` records which permitted channel produced the row (`manual_ui`, `talent_insights`, `ads_audience_estimate`, `recruiter_export`, `official_api`, `member_data_export`, `licensed_vendor`, `economic_graph`, `survey_self_report`) and defaults `source_quality`; automated member-site methods are rejected by the ingest (D-013/D-018). `manual` in the file and source names is a legacy label for the whole slot.

Inputs, `data/raw/linkedin_supply/<date>/` (private):
`search_counts.csv` — observed_at, observer, acquisition_method, evidence_ref, query_title, location_filter, extra_filters, language_filter, result_count, count_is_capped, source_quality, notes.
`profiles_manual.csv` — pseudo_id (assigned by the observer; no names, no URLs), observed_at, observer, acquisition_method, evidence_ref, headline, current_title, location_text, seniority_label, years_experience_explicit, education_level, education_field, certifications, languages_stated, skills_listed, has_featured_section, n_projects_listed, has_github_link, has_kaggle_link, has_portfolio_link, open_to_work_signal, transition_wording, prior_domain, industry_stated, consultant_freelance_signal, source_quality, notes.

Processed, `data/processed/` (private; one collection date per file):
`supply_linkedin_counts.csv` — the search_counts columns + `collection_date`; acquisition_method lower-case, count_is_capped `true`/`false`, result_count integer, source_quality resolved.
`supply_linkedin_profiles.csv` — the profiles_manual columns + `collection_date`, `source` (= `linkedin_manual`); booleans `true`/`false`/blank, source_quality resolved.

Candidate rows with `source = linkedin_manual` (built by `linkedin_candidates()` in build_supply.py): `frames = ["L"]`; `bio` = the coded current_title (the headline, transition wording and notes are never copied); `bio_role_family` / `bio_normalized_title` from it (`bio_role_rule = linkedin_current_title`); geography from location_text; `seniority_bio` = seniority_label (`unknown` when blank), `is_student`; `transition_explicit` (transition wording present), `prior_domains`; `bio_edu_levels`/`edu_levels_any`, `bio_edu_fields`/`edu_fields_any`, `bio_certifications`/`certifications_any`, `bio_skills`/`skills_any`, `bio_soft`; `links_profile`/`links_any` (github, kaggle, personal_site_custom) and `has_personal_site`. Slot-only columns (null on GitHub rows): `acquisition_method`, `languages_stated` (raw coded string, e.g. `de:C1;en:C2`), `years_experience_explicit`, `n_projects_listed`, `industry_stated`, `has_featured_section`, `open_to_work_signal`, `consultant_freelance_signal` (bool, null = not stated). GitHub-only fields are fixed for these rows: `login`, `company`, `blog`, `account_*`, `profile_updated`, `last_push`, `bio_language` null; counters (`n_search_hits`, repository, project, star and follower counts) 0; `hireable`, `twitter`, `has_company`, `has_blog`, `social_accounts_fetched`, `repos_truncated`, `is_academic` false; repository/project dicts and lists empty. GitHub-evidence tables (C14–C24) therefore filter `source == "github"`.
