# Job-posting bias: what employers advertise vs. what they require

Job advertisements are a proxy for hiring demand, not a record of hiring decisions. This page lists the biases that affect this repository's evidence, how (and whether) each is measured here, and how to read the findings in light of it.

| Bias | Direction of distortion | Measured / mitigated here | Where |
|---|---|---|---|
| **Duplicated postings** (same job on several boards, reposts, multi-location copies) | inflates counts, over-weights employers that multi-post | Cross-source dedupe (union-find on company+title+state and description fingerprint); in-scope duplicate rate reported; residual duplicates likely where employer is anonymised (AMS) | `dedupe_summary.csv`, `T01b` |
| **Recruitment agencies** | same vacancy advertised by several agencies; agency wish-lists are longer and vaguer | `is_agency` flag from company-name patterns; agency share reported; not removed from counts | `T04b` |
| **Exaggerated wish lists** | requirement lists exceed what a hire actually needs; "nice to have" merged with "must" | Only partially separable: language and degree extraction distinguish required / preferred / mentioned; skills are counted as *mentioned*, never as *required* | `T07`, `T11`, `T05` (read as "mention share") |
| **Legal boilerplate** | Austrian ads must state a minimum salary → almost every ad has a salary figure that is a legal floor, not an offer | Salary basis labelled (minimum_only vs range); overpay mention flagged; third-party surveys kept separate | `T09`, docs/salary-context.md |
| **SEO keyword stuffing / tool lists** | technologies listed because they exist in the company, not because the role uses them | Not solvable from text; mitigated by reporting co-occurrence and family-specific profiles rather than raw top-N; generic terms kept as "(generic)" entries | `T06`, `T14` |
| **Multinational recruiting templates** | English postings from global templates over-state "English-only" openness; local team language may still be German | `posting_language` reported separately from `german_requirement`; addressable-market scenarios use both | `T07c`, `T07e` |
| **Seniority inflation** ("Senior" for 3 years) | seniority labels not comparable across employers | Years-of-experience extracted independently of title label; cross-tab reported | `T08d` |
| **Missing salary / structural fields** | non-random missingness (large multinationals on LinkedIn omit figures; AMS ads always include them) | coverage by source reported; salary tables show n and source mix | `T09a` |
| **Platform selection bias** | each board attracts different employer types (AMS: public/mid-market, German; LinkedIn: multinational, English, senior; karriere.at: broad SME/industry) | state-by-source, family-by-source, language-by-source tables; StepStone/Indeed/hokify missing (403) so white-collar corporate ads are under-covered | `T03e`, `T01`, `T07_german_requirement_by_source` |
| **Negotiable language requirements** | "sehr gute Deutschkenntnisse" is sometimes waived for strong candidates | Cannot be measured from ads; scenarios in `T07e` bracket the range (strict vs. lenient reading) | `T07e` |
| **Requirements copied from older postings** | stale technology lists (e.g. legacy tools) | Not measurable; JobBarometer competency-trend table gives an external growth signal | `JB04` |
| **Jobs open after hiring / evergreen ads** | inflates the apparent stock, esp. AMS/willhaben long-running ads | posting age by source reported; old first-publish dates retained, not deleted | `T13b` |
| **Jobs not advertised publicly** (internal moves, referrals, agencies' hidden mandates) | the visible market under-represents senior and niche hires | Not measurable here; noted as a limit of any posting-based analysis | docs/limitations.md |
| **Snapshot vs flow** | a one-day snapshot counts the *stock* of open ads, which over-weights hard-to-fill roles (long-open ads) | Snapshot clearly dated; JobBarometer yearly *flow* counts provided as the flow reference | `market_summary.json`, `JB01` |

## Reading rules used in the decision documents

1. A skill "share" means *share of postings that mention it*, on the stated denominator; it is neither "required by" nor "used daily in".
2. Rankings are more robust than levels: the ordering of Python/SQL/Power BI is stable across sources even where the absolute share differs.
3. Findings that hold on both the AMS/EURES and the LinkedIn/karriere.at sides are treated as robust; findings that appear in only one source are labelled "platform-specific".
4. Nothing here measures hiring outcomes. Where the decision documents say "the market asks for X", read "advertised postings mention X".
