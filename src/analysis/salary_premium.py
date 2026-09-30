"""Step D05: does a skill still carry a higher advertised floor once the obvious
confounders are held constant?

`T09d_salary_by_skill.csv` reports the median advertised minimum of the ads that
*mention* a skill. That comparison is confounded: Databricks is named in
engineering ads, Excel in analyst ads, and the two families advertise different
floors regardless of the tool. This step estimates the association that survives
controlling for role family, seniority and federal state.

Model
-----
    log(advertised annual minimum) ~ skill dummies + role family + seniority + state

Ordinary least squares with HC1 heteroskedasticity-robust standard errors
(numpy only - no new dependency). A coefficient b is reported as exp(b) - 1, the
percentage difference in the advertised floor associated with the skill being
mentioned, holding the controls constant.

What this is not
----------------
* Not causal. Learning a skill does not move an advertisement's floor; the
  estimate says that ads mentioning it advertise differently.
* Not a wage estimate. The dependent variable is the collective-agreement
  minimum most Austrian ads are obliged to state, not pay (docs/salary-context.md).
* Multiple coefficients are estimated at once. The 95 % intervals are per
  coefficient (uncorrected); the table therefore also carries the Wald p-value
  and two multiplicity-adjusted p-values over the skill family: Holm (controls
  the family-wise error rate) and Benjamini-Hochberg (controls the false
  discovery rate). `survives_holm` / `survives_bh` are the adjusted readings at
  alpha = 0.05; a premium that only clears zero uncorrected is weak evidence.
* Unobserved confounders remain: employer size, industry, hours basis, and
  whether the ad is a range or a single minimum.

Input is the private per-posting file; the output table is an aggregate and is
published, so the figure built on it (BQ45) stays reproducible from public data
even though the estimation is not.

Run: python src/analysis/salary_premium.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed" / "postings_dedup.jsonl"
OUT = ROOT / "outputs" / "tables" / "D05_skill_salary_premium.csv"

CORE_FAMILIES = {"data_analytics", "bi", "data_science", "data_engineering",
                 "data_governance", "marketing_analytics", "product_analytics", "business_analysis"}
SKILL_COLUMNS = ["skills_programming_languages", "skills_bi_tools", "skills_cloud_platforms",
                 "skills_ml_ai", "skills_data_engineering", "skills_statistics_methods",
                 "skills_data_platforms", "skills_business_domain", "skills_python_ecosystem"]
# Decision-relevant skills only: every one of these appears in the learning roadmap (D04)
# or the "stop spending time on" list, and each needs at least ~30 ads to be estimable.
SKILLS = ["SQL", "Python", "Power BI", "Excel", "Azure", "Databricks", "Machine Learning",
          "Generative AI / LLM", "ETL/ELT", "Data Modeling", "Data Governance/Quality",
          "Cloud (generic)", "Statistics (general)", "Data Visualization", "R", "CI/CD"]
MIN_ADS_PER_SKILL = 30
BIG_STATES = ["Wien", "Oberösterreich", "Steiermark"]
ALPHA = 0.05


def load() -> pd.DataFrame:
    rows = []
    with open(PROCESSED, encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if not record.get("is_canonical") or record.get("role_family") not in CORE_FAMILIES:
                continue
            salary = record.get("salary_min_annual_eur")
            if not salary or record.get("salary_basis") == "implausible":
                continue
            skills = set()
            for column in SKILL_COLUMNS:
                value = record.get(column) or []
                skills.update([value] if isinstance(value, str) else value)
            rows.append({
                "salary": float(salary),
                "role_family": record.get("role_family"),
                "seniority": record.get("seniority") or "unspecified",
                "state": record.get("state") if record.get("state") in BIG_STATES else "other/unspecified",
                **{skill: int(skill in skills) for skill in SKILLS},
            })
    return pd.DataFrame(rows)


def ols_hc1(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Coefficients and HC1 robust standard errors."""
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    n, k = X.shape
    meat = X.T @ np.diag(resid ** 2) @ X
    cov = xtx_inv @ meat @ xtx_inv * (n / (n - k))  # HC1 small-sample correction
    return beta, np.sqrt(np.diag(cov))


def wald_p(b: float, se: float) -> float:
    """Two-sided p-value of b / se under the normal approximation (HC1 Wald test)."""
    return math.erfc(abs(b / se) / math.sqrt(2)) if se > 0 else float("nan")


def holm(p: list[float]) -> list[float]:
    """Holm step-down adjusted p-values (family-wise error rate)."""
    m = len(p)
    order = sorted(range(m), key=lambda i: p[i])
    adj, running = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj


def benjamini_hochberg(p: list[float]) -> list[float]:
    """Benjamini-Hochberg step-up adjusted p-values (false discovery rate)."""
    m = len(p)
    order = sorted(range(m), key=lambda i: p[i], reverse=True)
    adj, running = [0.0] * m, 1.0
    for k, i in enumerate(order):
        rank = m - k
        running = min(running, p[i] * m / rank)
        adj[i] = min(1.0, running)
    return adj


def estimate(frame: pd.DataFrame) -> tuple[pd.DataFrame, float, list[str]]:
    """Fit the model on a per-posting frame (see load()); returns the D05 table, R² and the skills dropped for low n."""
    usable = [s for s in SKILLS if frame[s].sum() >= MIN_ADS_PER_SKILL]
    dropped = sorted(set(SKILLS) - set(usable))

    controls = pd.get_dummies(frame[["role_family", "seniority", "state"]], drop_first=True, dtype=float)
    design = pd.concat([pd.Series(1.0, index=frame.index, name="const"),
                        frame[usable].astype(float), controls], axis=1)
    X = design.to_numpy(dtype=float)
    y = np.log(frame["salary"].to_numpy(dtype=float))
    beta, se = ols_hc1(X, y)

    fitted = X @ beta
    r2 = 1 - ((y - fitted) ** 2).sum() / ((y - y.mean()) ** 2).sum()

    records = []
    for skill in usable:
        i = list(design.columns).index(skill)
        low, high = beta[i] - 1.96 * se[i], beta[i] + 1.96 * se[i]
        raw_with = frame.loc[frame[skill] == 1, "salary"].median()
        raw_without = frame.loc[frame[skill] == 0, "salary"].median()
        records.append({
            "skill": skill,
            "ads_mentioning": int(frame[skill].sum()),
            "n_model": len(frame),
            "raw_median_with": round(float(raw_with)),
            "raw_median_without": round(float(raw_without)),
            "raw_difference_pct": round(float(raw_with / raw_without - 1) * 100, 1),
            "adjusted_premium_pct": round((np.exp(beta[i]) - 1) * 100, 1),
            "ci_low_pct": round((np.exp(low) - 1) * 100, 1),
            "ci_high_pct": round((np.exp(high) - 1) * 100, 1),
            "clears_zero": bool(low > 0 or high < 0),
            "p_value": wald_p(beta[i], se[i]),
        })
    table = pd.DataFrame(records)
    table["p_holm"] = holm(table.p_value.tolist())
    table["p_bh"] = benjamini_hochberg(table.p_value.tolist())
    table["survives_holm"] = table.p_holm < ALPHA
    table["survives_bh"] = table.p_bh < ALPHA
    for col in ("p_value", "p_holm", "p_bh"):
        table[col] = table[col].round(4)
    table = table.sort_values("adjusted_premium_pct", ascending=False)
    table["model"] = ("OLS on log(advertised annual minimum); controls = role family, seniority, state; "
                      f"HC1 robust SE; 95 % Wald CI per coefficient (uncorrected); p_holm / p_bh adjust over the "
                      f"{len(usable)} skills (Holm FWER, Benjamini-Hochberg FDR, alpha {ALPHA}); association, not causation")
    table["model_r2"] = round(float(r2), 3)
    table["controls"] = "role_family, seniority, state (" + ", ".join(BIG_STATES) + ", other/unspecified)"
    table["excluded_low_n"] = "; ".join(dropped) if dropped else ""
    return table, float(r2), dropped


def main() -> None:
    frame = load()
    table, r2, dropped = estimate(frame)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False)

    print(f"n = {len(frame)} core postings with a parsed advertised minimum; R² = {r2:.3f}")
    if dropped:
        print(f"excluded (fewer than {MIN_ADS_PER_SKILL} ads): {', '.join(dropped)}")
    print(table[["skill", "ads_mentioning", "raw_difference_pct", "adjusted_premium_pct",
                 "ci_low_pct", "ci_high_pct", "clears_zero", "p_value", "p_holm", "p_bh"]].to_string(index=False))
    print(f"\n-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
