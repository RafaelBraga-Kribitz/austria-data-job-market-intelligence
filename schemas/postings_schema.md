# Schema: data/processed/postings_dedup.jsonl (one row per source posting)

Also available as `.parquet` (list/dict columns serialised as JSON strings). Field names are stable across runs; new fields may be appended.

## Identity & provenance
| field | type | description |
|---|---|---|
| posting_uid | str | `<source>:<source_id>`, unique |
| source | str | eures · karriere · linkedin · willhaben · jobsat |
| source_id | str | id on the source |
| source_url | str | canonical URL of the ad |
| source_type | str | public_employment_service_mirror · job_board · professional_network |
| source_feed / source_connection_point / source_reference | str/int | EURES only: "PES Austria" feed, connection point id, AMS reference number |
| queries | list[str] | search keywords that surfaced this posting (coverage audit) |
| query_locations | list[str] | LinkedIn only |
| collected_at | ISO datetime | collection timestamp (UTC) |
| dedupe_group_id, dedupe_group_size, is_canonical, dedupe_method, sources_in_group | str/int/bool | duplicate handling (docs/methodology.md §4) |

## Original content (never modified)
| field | type | description |
|---|---|---|
| title | str | original title |
| company, company_raw | str | employer as stated (null when anonymised) |
| company_size_raw, company_main_location, company_url | str | source extras |
| location_text, location_regions, nuts_codes, country_codes | str/list | original location data |
| posted_date, modified_date, valid_through | date | as stated by source |
| description_html, description_text | str | full ad text (text = HTML stripped) |
| employment_type_raw, contract_type_raw, seniority_raw, job_function_raw, industry_raw, position_raw | str | source fields |
| salary_text_raw, salary_min_raw, salary_max_raw, salary_period_raw, salary_currency_raw, salary_overpay_flag | mixed | source salary fields |
| remote_flag_raw, job_location_type_raw | str | source flags |
| esco_occupation_uris | list[str] | EURES: ESCO occupation URIs assigned by AMS |
| applicants_text | str | LinkedIn |
| willhaben_detail | dict | willhaben detail payload |

## Derived: role
| field | type | description |
|---|---|---|
| title_clean | str | cleaned lower-case title used for rules |
| ams_occupation_label | str | AMS occupation label found in parentheses |
| normalized_title | str | canonical title (20 values since D-012, incl. "Machine Learning / AI Engineer", "Master / Product Data Management (operational)", "Actuary / Mathematician (adjacent)") |
| role_family | str | see docs/role-taxonomy.md |
| role_rule, role_oos_reason, role_family_prelim | str | which rule fired / why excluded |
| seniority, seniority_source | str | intern_student · trainee_junior · senior · lead_head · unspecified (+ LinkedIn-derived variants) |
| is_academic | bool | PhD/postdoc/professorship titles |

## Derived: geography & work model
| field | type | description |
|---|---|---|
| locations | list[str] | cities found |
| city, state, states_all, region_labels | str/list | primary city, Bundesland, NUTS-3 labels |
| is_styria, is_graz_area, is_graz_city, is_vienna, is_austria_wide, multi_location | bool | flags |
| location_evidence, location_confidence | str | how location was derived |
| remote_type | str | remote · hybrid · hybrid_or_flexible · on_site · unknown |
| remote_evidence, home_office_days_per_week, remote_austria_restricted | str/int/bool | |
| employment_type | str | full_time · part_time · full_or_part_time · unknown |
| is_internship_student, is_temporary_or_contract | bool | |

## Derived: salary (advertised only)
| field | type | description |
|---|---|---|
| salary_min_annual_eur, salary_max_annual_eur | int | annual gross EUR; monthly ×14 |
| salary_period | str | month · year (as detected) |
| salary_source | str | structured · text |
| salary_basis | str | range · minimum_only · implausible · none |
| salary_transparency | str | range · kv_minimum · single_figure · unparsed · none |
| salary_kv_mention, salary_overpay_mention | bool | collective-agreement / overpay wording present |
| salary_all_in_mention, salary_bonus_mention, salary_part_time_basis_risk | bool | D-012: "all-in" contract wording; bonus/variable wording; salary snippet next to part-time/hours wording (figure may be a part-time basis) |
| salary_snippet, salary_conversion_note | str | audit trail |

## Derived: languages, experience, education
| field | type | description |
|---|---|---|
| posting_language, posting_language_confidence | str/float | de · en · mixed · unknown |
| german_requirement, german_level_stated, german_level_bucket, german_snippet | str | see outputs/languages.json definitions |
| english_requirement, english_level_stated, english_level_bucket, english_snippet | str | |
| language_german_or_english, explicit_no_german, other_languages | bool/list | |
| experience_min_years, experience_max_years, experience_text, experience_multi_year_phrase, experience_entry_level_phrase | int/str/bool | |
| degree_required, degree_or_equivalent, degree_levels, degree_fields, education_snippet | bool/list/str | |
| degree_requirement | str | D-012: required / preferred / mentioned / none (strength of the degree wording) |

## Derived: skills (controlled vocabulary)
`skills_programming_languages, skills_bi_tools, skills_cloud_platforms, skills_data_platforms, skills_python_ecosystem, skills_data_engineering, skills_ml_ai, skills_statistics_methods, skills_business_domain, skills_soft_skills, skills_certifications, skills_work_model` — list[str] of canonical names; plus booleans `has_python, has_sql, has_r, has_power_bi, has_tableau, has_excel`; `description_length`, `has_full_description`.
