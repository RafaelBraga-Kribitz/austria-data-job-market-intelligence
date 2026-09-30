# Kaggle terms review (OQ-14; audit findings L41, L62)

**Question.** Can the Kaggle side of the candidate supply be collected, meaning profile and notebook aggregates for Austrian users, and if so, through which channel?

**Status.** Terms read on **2026-09-30** by the repository author with AI assistance. This is a documented reading of the terms, not legal advice. Everything below is paraphrased except one short quoted phrase. Nothing was collected, and no Kaggle account or API token was used.

## Sources read (all fetched 2026-09-30)

| Document | URL | Version shown |
|---|---|---|
| Kaggle Terms of Use | https://www.kaggle.com/terms | effective 22 June 2025 ("active") |
| Kaggle Acceptable Use Policy | https://www.kaggle.com/aup | effective 22 June 2025 |
| Public API documentation | https://www.kaggle.com/docs/api | undated |
| Datasets documentation (licences) | https://www.kaggle.com/docs/datasets | undated |
| Kaggle API / CLI client | https://github.com/Kaggle/kaggle-api | Apache 2.0 client code |
| Meta Kaggle dataset page | https://www.kaggle.com/datasets/kaggle/meta-kaggle | updated daily; licence Apache 2.0 |

The pages are rendered with JavaScript. A plain HTTP fetch returns an empty shell, so the text was read from a browser rendering.

## Relevant clauses (paraphrased)

**Automated and manual collection (Terms of Use, "additional restrictions").** Users must not crawl, scrape or spider any page, data or part of the Services or their Content. The prohibition applies "through use of manual or automated means". Users also must not copy or store any significant portion of the Content. Unlike GitHub's terms, the clause has no research exception. It also covers *manual* copying, so the owner-run manual route used for LinkedIn (D-018) is not available on Kaggle either.

**Acceptable Use Policy.** Resources must not be used for excessive crawling of the Services, for activity unrelated to ML/data science, for circumventing any part of the Services, or in ways that infringe other people's privacy rights.

**Personal and non-commercial use.** The Services may be used only for the user's own internal, personal, non-commercial use and in compliance with applicable law. This project is non-commercial, but the scraping clause applies regardless of purpose.

**Content rights and redistribution ("What are my rights in Kaggle?").** Everything on the site, including data and User Submissions, is protected content. Content not owned by the user may not be copied, reproduced, published, distributed or otherwise exploited without the owner's consent or in breach of someone's rights. The terms state that the existence of a download function does not lift these restrictions.

**User Submissions and dataset licences.** Publicly shared submissions, such as a public dataset, are licensed to other users only as far as the Services' functionality permits. Each public dataset carries its own licence, chosen by its uploader from a list (CC0, CC BY, CC BY-SA, CC BY-NC-SA, ODbL, GPL, "other", …). Reuse of a dataset is governed by that licence.

**API.** The official API and CLI cover competitions, datasets, notebooks (kernels), models and discussion forums, and they need an account-bound API token. The documentation describes dynamic rate limiting and an OAuth flow for third-party apps. No endpoint lists or searches users by location or country, so the API cannot enumerate "Austrian Kaggle users".

**Meta Kaggle.** Kaggle's own published dataset is the sanctioned bulk source about the platform. It is licensed Apache 2.0 and updated daily. Its Users table carries a user id, user name, display name, registration date and performance tier. According to its documented columns it has **no location field**, so Austrian users cannot be identified from it.

**Governing law.** California law, with Santa Clara County courts. Google Ireland is the Digital Services Act representative for the EEA.

## Reading for this project

| Route | Terms | Other constraints | Verdict |
|---|---|---|---|
| Scrape Kaggle profile pages of Austrian users (web) | prohibited (crawl/scrape clause, manual or automated) | personal data (GDPR) | **no** |
| Follow the Kaggle links found in GitHub profiles (9 % of candidates) and read those profiles | prohibited (the manual copying of profile data is still covered) | cross-platform identity linkage, excluded by D-020 / OQ-10 | **no** |
| Official API: list users by country | not possible, no such endpoint | – | **not available** |
| Meta Kaggle via the official API or download (Apache 2.0) | permitted under its licence, with attribution | no location, so it cannot answer an Austria question; a global context only, and individual rows are still personal data (user names), so aggregates only | possible, but **does not answer OQ-14** |
| Public datasets under their own licences | per dataset licence | unrelated to candidate supply | not relevant |

## Recommendation

**Do not collect Kaggle profile or notebook data.** OQ-14 should be closed as *contractual and structural*. The Terms of Use forbid crawling and scraping by manual or automated means with no research exception. The official channels (the API and Meta Kaggle under Apache 2.0) are permitted, but neither carries user location, so no permitted route can produce Austrian Kaggle aggregates. The supply-side finding therefore stays as measured: **"9 % of GitHub candidates link a Kaggle profile"** (a link *type* only, with no visit to the profile). If a global benchmark is ever wanted, Meta Kaggle may be downloaded through the official API under Apache 2.0 and used for aggregates only. That would be context, not Austrian supply, and it needs its own DECISION_LOG entry.

Suggested DECISION_LOG wording: *"OQ-14 closed 2026-09-30: Kaggle ToU (22 Jun 2025) prohibit manual or automated scraping; API/Meta Kaggle carry no location. Kaggle is not collected; the 9 % link-type share is the only Kaggle measure (docs/kaggle-terms-review.md)."*
