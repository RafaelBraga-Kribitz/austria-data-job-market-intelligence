"""Metrics registry: every number the living documents quote, built FROM the pipeline outputs -> outputs/metrics.json

    python src/reporting/metrics_registry.py                       write outputs/metrics.json
    python src/reporting/metrics_registry.py --run-date 2026-10-18 stamp the run (week_id, generated_at); default: today
    python src/reporting/metrics_registry.py --run-manifest PATH   accepted for the weekly orchestrator, ignored
    python src/reporting/metrics_registry.py --out PATH            write somewhere else
    python src/reporting/metrics_registry.py --history PATH        salary-floor history file (default <root>/data/private/metrics_history/history.csv)
    python src/reporting/metrics_registry.py --stdout              print the registry summary

With --run-date it also upserts this run's salary-floor rows into the private history file (src/reporting/metrics_history.py) and the
registry carries the derived keys `<floor key>__hist_min|max|median|mode|n|first_date` and `__trend` (lowest / highest / median / most
frequent value over all stored runs, the number of runs, the first run date and a trend text).

Also writes outputs/metrics_watch.json next to the registry (src/reporting/metrics_watch.py): the qualitative claims whose
wording could become false if the numbers move, evaluated against this run, with the places they appear.

Why this exists. The project refreshes weekly. A number typed into prose ("720 core postings", "Vienna 48 %",
"SQL 40 %", "stale after 2026-12-16") is silently wrong after the next snapshot. The registry is the single place
where each such number is *computed* from outputs/*.json and outputs/tables/*.csv; src/reporting/render_docs.py then
writes the registry's display value into the markers embedded in the living documents
(`<!--m:core_n-->720<!--/m-->`). The registry contains NO data literals: only definitions (what a key means, which
table/field it comes from, which denominator it uses).

Registry shape (flat dict, key -> entry):
    value         the raw value (int / float / ISO date / text); shares are fractions 0..1, money is euros
    display       the default text written into documents ("48 %", "720", "€55.4k", "2026-09-16")
    unit          count | share | eur | ratio | pp | years | days | date | text | number
    n             the numerator's population size where the value is a share/count of something (else null)
    denominator   words: what the share is a share of
    source        outputs file + field, e.g. "outputs/tables/T03a_state_counts.csv:count/n[state=Wien]"
    definition    one sentence
    caveat        what the number does not mean ("" when none)
    basis         which counting basis it follows (primary state / any listed site / text-derived / ...) — D-027
and a `_meta` block: demand_vintage, supply_vintage, generated_at, stale_after_demand, stale_after_supply,
week_id, run_date, key_count, missing_inputs.

Formats (the optional `:fmt` of a marker, `<!--m:key:pct1-->`; default = `display`):
    pct0 "48 %"  pct1 "7.5 %"  pct2  pctc0 "48%"  pctn0 "48"  pctn1 "40.5"  (number without the percent sign)
    tpct0 tpct1 tpctn0 tpctn1  same, rounded from the table's published 3-decimal share
    epct0 epct1  round-half-even (Python's round(): 62.5 -> 62), where a document was written that way
    int "12,429"  int0 "12429"  f1 "3.3"  f2 "0.64"  x1 "3.3×"  eur_k "€55.4k"  eur_k0 "€60k"  k1 "55.4k"  eur "€2,800"  apct0 "28 %" (absolute value, for 'fell 28 %')  int100 "33,700"
    date "2026-09-16"  ym "2026-09"  dmon "16 Dec"  +Nd (date plus N days)  text
Percentages are rounded half-up from the full-precision value; the tpct* variants round the table's published
three-decimal share instead (for places where a document quotes the table, e.g. 0.035 -> 4 %).

Key naming. Hand-named headline keys (core_n, vienna_share_core, styria_core_primary_state, sql_share,
german_stated_share, english_no_german_n_styria, floor_analytics_eur, ...) plus systematic families built from
whole tables: skill_share__<slug> (T05_*), family_n__<family>, state_n__<state>, skill_family_share__<family>__<slug>,
... Systematic keys are stable as long as the table's row labels are.

Two Styrian bases exist and are never mixed (D-027, OQ-19): `*_primary_state` (one state per ad: 54) and `*_flag`
(any listed site, multi-site ads count in every state they list: 58). Every Styria key carries its basis in `basis`.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics_history  # noqa: E402  (sibling module: the weekly salary-floor history)
STALE_AFTER_DAYS = 91            # definition: a snapshot older than 13 weeks is stale (AGENT_CONTEXT: "stale after ...")
SUPPLY_COLLECTION_SPAN_DAYS = 1  # definition: the GitHub README fetch runs past midnight, so the supply vintage is "d/d+1"

# --------------------------------------------------------------------------------------------------------------
# formatting (shared with render_docs.py)
# --------------------------------------------------------------------------------------------------------------


def _q(value: float, places: int) -> Decimal:
    """Half-up rounding of the decimal repr (7.5 -> '8' at 0 places is what a document reader expects)."""
    quant = Decimal(1).scaleb(-places)
    return Decimal(repr(float(value))).quantize(quant, rounding=ROUND_HALF_UP)


def _pct(value: float, places: int, table_precision: bool = False, even: bool = False) -> Decimal:
    """Percentage, half-up. Default: rounded from the full-precision value (385/720 = 53.47 -> 53 %).
    `table_precision=True` (formats tpct*): the share is first rounded to three decimals as in outputs/tables/*.csv `share`
    (0.145), then to `places` with round-half-even like Python's round() (14.5 -> 14) - for the places where a document quotes
    the published table share (scikit-learn 0.035 -> 4 %, CI/CD 0.145 -> 14 %)."""
    v = Decimal(repr(float(value)))
    if table_precision:
        v = v.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return (v * 100).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN if (even or table_precision) else ROUND_HALF_UP)


def _num(value: float, places: int, thousands: bool = False) -> str:
    q = _q(value, places)
    return f"{q:,}" if thousands else f"{q}"


def _add_days(iso: str, days: int) -> str:
    return (dt.date.fromisoformat(str(iso)[:10]) + dt.timedelta(days=days)).isoformat()


def fmt_value(value, unit: str, fmt: str | None = None) -> str:
    """Render `value` as text. `fmt` None = the unit's default (what the registry stores as `display`)."""
    if fmt is None:
        fmt = {"share": "pct0", "count": "int", "eur": "eur_k", "ratio": "x1", "number": "f1", "pp": "f1",
               "years": "f1", "days": "int", "date": "date", "text": "text"}.get(unit, "text")
    if fmt == "text":
        return str(value)
    m = re.fullmatch(r"\+(\d+)d", fmt)
    if m:
        return _add_days(value, int(m.group(1)))
    if fmt == "date":
        return str(value)[:10]
    if fmt == "ym":
        return str(value)[:7]
    if fmt == "dmon":  # "16 Dec"
        d = dt.date.fromisoformat(str(value)[:10])
        return f"{d.day} {d.strftime('%b')}"
    if fmt in ("pct0", "pct1", "pct2"):
        return f"{_pct(value, int(fmt[-1]))} %"
    if fmt in ("epct0", "epct1"):
        return f"{_pct(value, int(fmt[-1]), even=True)} %"
    if fmt in ("epctn0", "epctn1"):
        return f"{_pct(value, int(fmt[-1]), even=True)}"
    if fmt in ("tpct0", "tpct1"):
        return f"{_pct(value, int(fmt[-1]), True)} %"
    if fmt in ("tpctn0", "tpctn1"):
        return f"{_pct(value, int(fmt[-1]), True)}"
    if fmt == "pctc0":
        return f"{_pct(value, 0)}%"
    if fmt in ("pctn0", "pctn1"):
        return f"{_pct(value, int(fmt[-1]))}"
    if fmt == "int":
        return _num(float(value), 0, thousands=True)
    if fmt == "int0":
        return _num(float(value), 0)
    if fmt in ("f1", "f2", "f3"):
        return _num(float(value), int(fmt[-1]))
    if fmt == "x1":
        return f"{_num(float(value), 1)}×"
    if fmt == "x2":
        return f"{_num(float(value), 2)}×"
    if fmt == "k1":
        return f"{_num(float(value) / 1000, 1)}k"
    if fmt == "apct0":
        return f"{_pct(abs(float(value)), 0)} %"
    if fmt == "apct1":
        return f"{_pct(abs(float(value)), 1)} %"
    if fmt == "int100":
        return f"{int(_q(float(value) / 100, 0)) * 100:,}"
    if fmt == "eur_k0":
        return f"€{_num(float(value) / 1000, 0)}k"
    if fmt == "eur_k":
        return f"€{_num(float(value) / 1000, 1)}k"
    if fmt == "eur":
        return f"€{_num(float(value), 0, thousands=True)}"
    raise ValueError(f"unknown format {fmt!r}")


KNOWN_FORMATS = ("text date ym dmon pct0 pct1 pct2 pctc0 pctn0 pctn1 tpct0 tpct1 tpctn0 tpctn1 epct0 epct1 epctn0 epctn1 int int0 f1 f2 f3 x1 x2 k1 eur_k eur_k0 apct0 apct1 int100 eur").split()


def slug(text: str) -> str:
    s = str(text).strip().lower()
    for a, b in (("c#", "c_sharp"), ("c/c++", "c_cpp"), ("+", "_plus_"), ("&", "_and_"), ("ä", "ae"), ("ö", "oe"),
                 ("ü", "ue"), ("ß", "ss"), ("≥", "ge_"), ("<", "lt_"), (">", "gt_"), ("%", "pct")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "x"


# --------------------------------------------------------------------------------------------------------------
# the registry container
# --------------------------------------------------------------------------------------------------------------


class Registry:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.items: dict[str, dict] = {}
        self.missing: list[str] = []
        self._csv: dict[str, list[dict]] = {}
        self._json: dict[str, dict | None] = {}

    # ----- inputs -----
    def table(self, name: str) -> list[dict]:
        """Rows of outputs/tables/<name>.csv ([] and a note in `missing` when absent)."""
        if name not in self._csv:
            path = self.root / "outputs" / "tables" / f"{name}.csv"
            if not path.exists():
                self.missing.append(f"outputs/tables/{name}.csv")
                self._csv[name] = []
            else:
                with open(path, encoding="utf-8", newline="") as handle:
                    self._csv[name] = list(csv.DictReader(handle))
        return self._csv[name]

    def json(self, name: str) -> dict:
        if name not in self._json:
            path = self.root / "outputs" / f"{name}.json"
            try:
                self._json[name] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.missing.append(f"outputs/{name}.json")
                self._json[name] = None
        return self._json[name] or {}

    # ----- outputs -----
    def add(self, key: str, value, unit: str, *, source: str, definition: str, n=None, denominator: str = "",
            caveat: str = "", basis: str = "", display: str | None = None) -> None:
        if value is None:
            return
        if isinstance(value, float) and value != value:  # NaN
            return
        if key in self.items:
            old = self.items[key]["value"]
            if old != value:
                raise ValueError(f"registry key {key!r} defined twice with different values ({old!r} vs {value!r})")
            return
        if unit == "count" and isinstance(value, float) and value == int(value):
            value = int(value)
        self.items[key] = {
            "value": value,
            "display": display if display is not None else fmt_value(value, unit),
            "unit": unit,
            "n": int(n) if n is not None else None,
            "denominator": denominator,
            "source": source,
            "definition": definition,
            "caveat": caveat,
            "basis": basis,
        }

    def alias(self, key: str, target: str, definition: str | None = None, **over) -> None:
        """A hand-named key for an existing systematic key (same value, same provenance)."""
        if target not in self.items:
            return  # the systematic key is absent (input missing); the alias is absent too
        entry = dict(self.items[target])
        entry["definition"] = definition or entry["definition"]
        entry.update(over)
        entry["source"] = entry["source"] + f" (= {target})"
        if key in self.items:
            raise ValueError(f"registry key {key!r} defined twice")
        self.items[key] = entry


def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _rowget(rows: list[dict], col: str, val: str) -> dict | None:
    for r in rows:
        if r.get(col) == val:
            return r
    return None


# --------------------------------------------------------------------------------------------------------------
# generic table readers
# --------------------------------------------------------------------------------------------------------------


def share_table(reg: Registry, table: str, idcols, prefix: str, *, unit_label: str, denominator: str, basis: str = "",
                caveat: str = "", count_col: str = "count", n_col: str = "n", skip=(), filt=None, count_prefix: str | None = None, known=()):
    """For tables with count / n columns: `<prefix>__<id>` = count/n (share) and `<count_prefix>__<id>` = count.

    `known` (single id column only): the closed set of categories the pipeline can emit. A category with no row this run
    (count 0, so the pipeline's value_counts drops it) is still registered as 0 / 0 %, so a document marker that quotes it
    keeps resolving instead of failing the whole render when the category is empty for one week."""
    idcols = [idcols] if isinstance(idcols, str) else list(idcols)
    rows_all = [r for r in reg.table(table) if not filt or filt(r)]
    if rows_all and "population" in rows_all[0] and "population" not in idcols and len({r["population"] for r in rows_all}) > 1:
        idcols = ["population"] + idcols  # a table that mixes populations must not collide keys
    cprefix = count_prefix or prefix.replace("_share", "") + "_n"
    for r in reg.table(table):
        if filt and not filt(r):
            continue
        ident = [r[c] for c in idcols]
        if any(i in skip for i in ident):
            continue
        cnt, n = _f(r.get(count_col)), _f(r.get(n_col))
        if cnt is None or not n:
            continue
        tag = "__".join(slug(i) for i in ident)
        where = ", ".join(f"{c}={r[c]}" for c in idcols)
        src = f"outputs/tables/{table}.csv:{count_col}/{n_col}[{where}]"
        reg.add(f"{prefix}__{tag}", cnt / n, "share", source=src, n=n, denominator=denominator, basis=basis, caveat=caveat,
                definition=f"{unit_label}: {where}")
        reg.add(f"{cprefix}__{tag}", cnt, "count", source=src.replace("count/n", "count"), n=n, denominator=denominator,
                basis=basis, caveat=caveat, definition=f"number of {unit_label}: {where}")
    if known and len(idcols) == 1:
        rows = [r for r in rows_all if _f(r.get(n_col))]
        seen = {r[idcols[0]] for r in rows}
        n0 = _f(rows[0].get(n_col)) if rows else None
        for cat in known:
            if n0 and cat not in seen and not any(c in skip for c in (cat,)):
                tag = slug(cat)
                src = f"outputs/tables/{table}.csv:{count_col}/{n_col}[{idcols[0]}={cat}] (no row this run: count 0)"
                reg.add(f"{prefix}__{tag}", 0.0, "share", source=src, n=n0, denominator=denominator, basis=basis, caveat=caveat,
                        definition=f"{unit_label}: {idcols[0]}={cat}")
                reg.add(f"{cprefix}__{tag}", 0, "count", source=src.replace("count/n", "count"), n=n0, denominator=denominator, basis=basis, caveat=caveat,
                        definition=f"number of {unit_label}: {idcols[0]}={cat}")


def wide_table(reg: Registry, table: str, idcol: str | None, prefix: str, columns: dict, *, unit_label: str = "",
               basis: str = "", caveat: str = "", denominator: str = "", n_col: str | None = None, id_values=None):
    """columns: {csv_column: (key_suffix, unit)}; one key per row x column: `<prefix>__<id>__<suffix>`."""
    for i, r in enumerate(reg.table(table)):
        ident = slug(r[idcol]) if idcol else str(i)
        if id_values is not None and r.get(idcol) not in id_values:
            continue
        n = _f(r.get(n_col)) if n_col else None
        for col, (suffix, unit) in columns.items():
            val = _f(r.get(col))
            if val is None:
                continue
            reg.add(f"{prefix}__{ident}__{suffix}" if suffix else f"{prefix}__{ident}", val, unit,
                    source=f"outputs/tables/{table}.csv:{col}[{idcol}={r[idcol]}]" if idcol else f"outputs/tables/{table}.csv:{col}[row {i}]",
                    n=n, denominator=denominator, basis=basis, caveat=caveat,
                    definition=f"{unit_label or col}: {r[idcol] if idcol else i}")


# --------------------------------------------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------------------------------------------

PRIMARY = "primary state (one state per ad; D-027)"
ANYSITE = "any listed site (multi-site ads count in every state they list; D-027)"
TEXT = "text-derived share of the core postings with a description"
CORE_DEN = "core data-role postings (deduplicated)"
DESC_DEN = "core postings with a description"
# Closed set of src/pipeline/normalize.py `german_requirement` values (definition, not data): all seven stay registered at 0 when empty.
GERMAN_REQUIREMENT_BUCKETS = ("required", "required_implied", "preferred", "mentioned", "not_mentioned", "german_or_english", "explicitly_not_required")
CAVEAT_MENTION = "a share of ads that mention the item, not of jobs that require it; one-day stock, not annual demand"


def vintages(reg: Registry, run_date: dt.date) -> dict:
    ms = reg.json("market_summary")
    first = str((ms.get("collected_at_range") or {}).get("min") or "")[:10]
    last = str((ms.get("collected_at_range") or {}).get("max") or "")[:10]
    ss = reg.json("supply_summary")
    s_first = str(ss.get("collection_date") or "")[:10]
    meta: dict = {}
    if first:
        meta["demand_vintage"] = first
        meta["demand_collected_to"] = last or first
        meta["stale_after_demand"] = _add_days(first, STALE_AFTER_DAYS)
    if s_first:
        s_last = _add_days(s_first, SUPPLY_COLLECTION_SPAN_DAYS)
        meta["supply_vintage"] = s_first
        meta["supply_vintage_span"] = f"{s_first}/{s_last[8:]}" if s_last[:7] == s_first[:7] else f"{s_first}/{s_last}"
        meta["stale_after_supply"] = _add_days(s_last, STALE_AFTER_DAYS)
    iso = run_date.isocalendar()
    meta["week_id"] = f"{iso[0]}-W{iso[1]:02d}"
    meta["run_date"] = run_date.isoformat()
    jb = [int(r["year"]) for r in reg.table("JB01_yearly_counts_long") if r.get("year", "").isdigit()]
    if jb:
        meta["jobbarometer_year_first"], meta["jobbarometer_year_last"] = min(jb), max(jb)
    sq = [int(r["year"]) for r in reg.table("S02_quarter_ratios_by_year") if r.get("year", "").isdigit()]
    if sq:
        meta["eurostat_year_first"], meta["eurostat_year_last"] = min(sq), max(sq)
    return meta


def add_vintage_keys(reg: Registry, meta: dict) -> None:
    src = "outputs/market_summary.json:collected_at_range.min"
    if "demand_vintage" in meta:
        reg.add("demand_vintage", meta["demand_vintage"], "date", source=src, definition="date of the posting snapshot (first collection timestamp)")
        reg.add("stale_after_demand", meta["stale_after_demand"], "date", source=src + f" + {STALE_AFTER_DAYS} days",
                definition=f"demand vintage + {STALE_AFTER_DAYS} days: after this date the snapshot numbers are stale")
        reg.add("demand_collected_to", meta["demand_collected_to"], "date", source="outputs/market_summary.json:collected_at_range.max",
                definition="last day of the collection window")
    if "supply_vintage" in meta:
        reg.add("supply_vintage", meta["supply_vintage"], "date", source="outputs/supply_summary.json:collection_date",
                definition="date of the GitHub supply collection")
        reg.add("supply_vintage_span", meta["supply_vintage_span"], "text", source="outputs/supply_summary.json:collection_date",
                definition=f"collection day and the next day (the README fetch runs past midnight, +{SUPPLY_COLLECTION_SPAN_DAYS} d)")
        reg.add("stale_after_supply", meta["stale_after_supply"], "date",
                source=f"outputs/supply_summary.json:collection_date + {SUPPLY_COLLECTION_SPAN_DAYS} + {STALE_AFTER_DAYS} days",
                definition="supply vintage end + 91 days")
    for k, label in (("jobbarometer_year_first", "first year of the AMS JobBarometer series"),
                     ("jobbarometer_year_last", "last year of the AMS JobBarometer series"),
                     ("eurostat_year_first", "first year of the Eurostat vacancy series"),
                     ("eurostat_year_last", "last year of the Eurostat vacancy series")):
        if k in meta:
            tbl = "JB01_yearly_counts_long.csv:year" if k.startswith("job") else "S02_quarter_ratios_by_year.csv:year"
            reg.add(k, meta[k], "number", source=f"outputs/tables/{tbl}", definition=label, display=str(meta[k]))


def layer1_counts(reg: Registry) -> None:
    ms = reg.json("market_summary")
    c = ms.get("counts") or {}
    s = "outputs/market_summary.json:counts."

    def cnt(key, field, definition, *, basis="", caveat="", denominator=""):
        reg.add(key, c.get(field), "count", source=s + field, definition=definition, basis=basis, caveat=caveat, denominator=denominator)

    cnt("raw_rows_n", "raw_rows_all_sources", "raw rows collected from the five posting sources, before deduplication")
    cnt("unique_postings_n", "canonical_groups_all", "unique postings after within- and cross-source deduplication (all families)")
    cnt("core_n", "core_canonical", "core data-role postings (canonical rows whose title falls into the eight core families)",
        caveat="one-day stock of open ads, not annual demand, vacancies or hires")
    cnt("core_n_text_basis", "core_with_description", "core postings with a description: the denominator of every text-derived share",
        caveat="Wilson intervals are in the tables")
    cnt("adjacent_n", "adjacent_canonical", "adjacent canonical postings (AI-software-engineering + other data-ish titles), reported separately")
    cnt("styria_core_flag", "styria_core", "core postings listing at least one site in Styria", basis=ANYSITE,
        caveat="tentative: every Styria-only figure rests on a small n")
    cnt("styria_core_primary_state", "styria_core_primary_state", "core postings whose primary state is Steiermark", basis=PRIMARY,
        caveat="tentative: every Styria-only figure rests on a small n")
    cnt("vienna_core_flag", "vienna_core", "core postings listing at least one site in Vienna", basis=ANYSITE)
    cnt("vienna_core_primary_state", "vienna_core_primary_state", "core postings whose primary state is Wien", basis=PRIMARY)
    cnt("graz_area_core_flag", "graz_area_core", "core postings listing a site in the Graz commuting area (flag-only; subset of the Styria flag count)", basis=ANYSITE)
    cnt("graz_area_core_primary_state", "graz_area_core_primary_styria", "Graz-area postings whose primary state is Steiermark", basis=PRIMARY)
    cnt("employers_named_n", "unique_employers_core", "unique named employers among the core postings", caveat="a lower bound: 140 AMS/EURES rows carry no employer name")
    cnt("employers_styria_n", "unique_employers_styria", "unique named employers among Styrian core postings", basis=ANYSITE)
    # derived
    core, desc = c.get("core_canonical"), c.get("core_with_description")
    if core and c.get("raw_rows_all_sources"):
        reg.add("core_share_of_unique", core / c["canonical_groups_all"], "share", n=c["canonical_groups_all"], denominator="unique postings",
                source="outputs/market_summary.json:counts.core_canonical/canonical_groups_all", definition="core postings as a share of all unique postings")
    if core and c.get("styria_core_primary_state"):
        reg.add("styria_share_core_primary_state", c["styria_core_primary_state"] / core, "share", n=core, denominator=CORE_DEN, basis=PRIMARY,
                source="outputs/market_summary.json:counts.styria_core_primary_state/core_canonical", definition="Styria's share of the core postings, primary-state basis",
                caveat="tentative; the official yearly flow gives 13.6 % (JB05)")
        reg.add("styria_share_core_flag", c["styria_core"] / core, "share", n=core, denominator=CORE_DEN, basis=ANYSITE,
                source="outputs/market_summary.json:counts.styria_core/core_canonical", definition="Styria's share of the core postings, any-site basis")
    if core and c.get("vienna_core_primary_state"):
        reg.add("vienna_share_core", c["vienna_core_primary_state"] / core, "share", n=core, denominator=CORE_DEN, basis=PRIMARY,
                source="outputs/market_summary.json:counts.vienna_core_primary_state/core_canonical",
                definition="Vienna's share of the core postings, primary-state basis (T03a)", caveat="robust for the ranking")
        reg.add("vienna_share_core_flag", c["vienna_core"] / core, "share", n=core, denominator=CORE_DEN, basis=ANYSITE,
                source="outputs/market_summary.json:counts.vienna_core/core_canonical", definition="Vienna's share of the core postings, any-site basis")
    if core and desc:
        reg.add("core_no_description_n", core - desc, "count", source="outputs/market_summary.json:counts.core_canonical-core_with_description",
                definition="core postings without a description")
    # adjacent families
    for r in reg.table("T02a_adjacent_family_counts"):
        reg.add(f"adjacent_n__{slug(r['role_family'])}", _f(r["count"]), "count", source="outputs/tables/T02a_adjacent_family_counts.csv:count",
                definition=f"adjacent canonical postings, family {r['role_family']} (reported separately, not in the core)")
    # sources
    for r in reg.table("T01_source_coverage"):
        t = slug(r["source"])
        for col, key, label in (("rows", "raw_rows", "raw rows"), ("in_scope_canonical", "core_n", "core canonical postings")):
            reg.add(f"source_{key}__{t}", _f(r[col]), "count", source=f"outputs/tables/T01_source_coverage.csv:{col}[source={r['source']}]",
                    definition=f"{label} from source {r['source']}")
    for r in reg.table("T01_source_coverage"):
        tag = slug(r["source"])
        reg.add(f"source_in_scope_rows__{tag}", _f(r["in_scope_rows"]), "count", source=f"outputs/tables/T01_source_coverage.csv:in_scope_rows[source={r['source']}]", definition=f"in-scope rows (before dedupe) from source {r['source']}")
        reg.add(f"source_adjacent_rows__{tag}", _f(r["adjacent_rows"]), "count", source=f"outputs/tables/T01_source_coverage.csv:adjacent_rows[source={r['source']}]", definition=f"adjacent-family rows from source {r['source']}")
        if _f(r["rows"]):
            reg.add(f"source_with_description_share__{tag}", _f(r["with_description"]) / _f(r["rows"]), "share", n=_f(r["rows"]), denominator=f"raw rows of source {r['source']}",
                    source=f"outputs/tables/T01_source_coverage.csv:with_description/rows[source={r['source']}]", definition=f"share of raw rows of source {r['source']} that carry a description")
    det: dict = {}
    for r in reg.table("Q06_detail_fetch_status"):
        det[r["source"]] = det.get(r["source"], 0) + (_f(r["count"]) or 0)
    for src, v in det.items():
        reg.add(f"detail_fetch_n__{slug(src)}", v, "count", source=f"outputs/tables/Q06_detail_fetch_status.csv:count[source={src}] summed", definition=f"detail records fetched for source {src}")
    for r in reg.table("Q03a_normalization_confidence"):
        reg.add(f"norm__{slug(r['metric'])}", _f(r["count"]), "count", source=f"outputs/tables/Q03a_normalization_confidence.csv:count[metric={r['metric']}]", definition=f"title normalisation: {r['metric']}")
    for r in reg.table("Q02_coverage_by_source_core"):
        tag = slug(r["source"])
        reg.add(f"coverage_in_scope_n__{tag}", _f(r["n"]), "count", source=f"outputs/tables/Q02_coverage_by_source_core.csv:n[source={r['source']}]", definition=f"in-scope rows of source {r['source']} (Q02 denominator)")
        for col in ("description_gt300", "salary_figure", "salary_range", "german_mentioned", "state_known", "city_known", "date_known", "seniority_in_title", "remote_known"):
            if _f(r.get(col)) is not None:
                reg.add(f"coverage__{tag}__{col}", _f(r[col]), "share", n=_f(r["n"]), denominator=f"in-scope rows of source {r['source']}", source=f"outputs/tables/Q02_coverage_by_source_core.csv:{col}[source={r['source']}]",
                        definition=f"share of source {r['source']} in-scope rows with usable value: {col}", caveat="field availability differs by source; downstream tables are weighted by what each source reports")
    # dedupe
    d = reg.table("dedupe_summary")
    if d:
        r = d[0]
        reg.add("dedupe_rows_in_scope", _f(r["rows_in_scope"]), "count", source="outputs/tables/dedupe_summary.csv:rows_in_scope", definition="in-scope rows before deduplication")
        reg.add("dedupe_groups_in_scope", _f(r["unique_groups_in_scope"]), "count", source="outputs/tables/dedupe_summary.csv:unique_groups_in_scope", definition="in-scope duplicate groups")
        reg.add("dedupe_duplicate_rate_in_scope", _f(r["duplicate_rate_in_scope"]), "share", source="outputs/tables/dedupe_summary.csv:duplicate_rate_in_scope",
                n=_f(r["rows_in_scope"]), denominator="in-scope rows", definition="in-scope duplicate rate before dedupe")
    q04 = {r["metric"]: _f(r["value"]) for r in reg.table("Q04_duplicates")}
    if q04.get("core_groups"):
        reg.add("core_groups_size_gt1_n", q04.get("core_groups_size>1"), "count", source="outputs/tables/Q04_duplicates.csv:core_groups_size>1",
                definition="core duplicate groups with more than one row")
    ov = reg.table("T01b_source_overlap_in_scope")
    if ov and c.get("core_canonical"):
        multi = sum(_f(r["groups"]) for r in ov if "," in r["sources_in_group"])
        reg.add("core_multi_source_groups_n", multi, "count", source="outputs/tables/T01b_source_overlap_in_scope.csv:groups[sources contains ','] summed",
                definition="core groups seen on more than one of our sources", denominator=CORE_DEN, n=c["core_canonical"])
        reg.add("core_multi_source_groups_share", multi / c["core_canonical"], "share", source="outputs/tables/T01b_source_overlap_in_scope.csv / market_summary core_canonical",
                n=c["core_canonical"], denominator=CORE_DEN, definition="share of core groups seen on more than one of our sources")
        for r in ov:
            reg.add(f"source_overlap_groups__{slug(r['sources_in_group'])}", _f(r["groups"]), "count", source=f"outputs/tables/T01b_source_overlap_in_scope.csv:groups[sources_in_group={r['sources_in_group']}]",
                    definition=f"core groups seen only on / exactly on: {r['sources_in_group']}")
    # employers
    emp = {r["metric"]: _f(r["value"]) for r in reg.table("T04b_employer_concentration")}
    for k, label, unit in (("postings_with_named_employer", "core postings that name an employer", "count"),
                           ("postings_without_named_employer", "core postings without a named employer (AMS/EURES anonymised)", "count"),
                           ("unique_named_employers_graz_area", "unique named employers in the Graz area", "count"),
                           ("styria_postings_without_named_employer", "Styrian core postings without a named employer", "count"),
                           ("top10_share_of_named", "share of named postings held by the top 10 employers", "share"),
                           ("top25_share_of_named", "share of named postings held by the top 25 employers", "share"),
                           ("agency_share_of_named_postings", "share of named postings from recruitment agencies", "share")):
        if k in emp:
            reg.add(f"employer__{k}", emp[k], unit, source=f"outputs/tables/T04b_employer_concentration.csv:value[metric={k}]", definition=label)
    eu_core = None
    for r in reg.table("T01_source_coverage"):
        if r["source"] == "eures":
            eu_core = _f(r["in_scope_canonical"])
    if emp.get("eures_anonymised_employer_rows") is not None and eu_core:
        reg.add("employer_eures_anonymised_share", emp["eures_anonymised_employer_rows"] / eu_core, "share", n=eu_core, denominator="EURES/AMS core canonical postings",
                source="outputs/tables/T04b_employer_concentration.csv:eures_anonymised_employer_rows / T01_source_coverage in_scope_canonical[eures]",
                definition="share of EURES/AMS core postings whose employer is anonymised ('siehe Beschreibung')")
        reg.add("employer_eures_named_share", 1 - emp["eures_anonymised_employer_rows"] / eu_core, "share", n=eu_core, denominator="EURES/AMS core canonical postings",
                source="outputs/tables/T04b_employer_concentration.csv:1 - eures_anonymised_employer_rows / in_scope_canonical[eures]", definition="share of EURES/AMS core postings that name their employer")
    if emp.get("postings_without_named_employer") and core:
        reg.add("employer_unnamed_share_core", emp["postings_without_named_employer"] / core, "share", n=core, denominator=CORE_DEN,
                source="outputs/tables/T04b_employer_concentration.csv:postings_without_named_employer / core_canonical",
                definition="share of core postings without a named employer")
    for r in reg.table("T04_employers")[:0]:
        pass
    emp_rows = reg.table("T04a_employers_styria")
    for r in emp_rows:
        if _f(r.get("styria")) is not None:
            reg.add(f"employer_styria_postings__{slug(r['company_norm'])}", _f(r["styria"]), "count",
                    source=f"outputs/tables/T04a_employers_styria.csv:styria[company_norm={r['company_norm']}]", basis=ANYSITE,
                    definition=f"core postings of {r['example_company']} listing a Styrian site")
    # age / stale
    ages = {r["source"]: r for r in reg.table("T13b_posting_age_by_source")}
    for src, r in ages.items():
        reg.add(f"posting_age_median_days__{slug(src)}", _f(r["50%"]), "days", source=f"outputs/tables/T13b_posting_age_by_source.csv:50%[source={src}]",
                definition=f"median age (days) of core postings from {src} at collection time")
    if ages:
        meds = [_f(r["50%"]) for r in ages.values() if _f(r["50%"]) is not None]
        reg.add("posting_age_median_days_min", min(meds), "days", source="outputs/tables/T13b_posting_age_by_source.csv:min(50%) over sources", definition="smallest per-source median posting age (days)")
        reg.add("posting_age_median_days_max", max(meds), "days", source="outputs/tables/T13b_posting_age_by_source.csv:max(50%) over sources", definition="largest per-source median posting age (days)")
    stale = {r["metric"]: _f(r["count"]) for r in reg.table("Q05a_stale")}
    for k, v in stale.items():
        reg.add(f"stale__{slug(k)}", v, "count", source=f"outputs/tables/Q05a_stale.csv:count[metric={k}]", definition=f"core rows: {k}")
    for r in reg.table("S05_snapshot_age_distribution"):
        reg.add(f"snapshot_age_share_within_{int(float(r['within_days']))}d", _f(r["share_of_core"]), "share", n=core, denominator=CORE_DEN,
                source=f"outputs/tables/S05_snapshot_age_distribution.csv:share_of_core[within_days={r['within_days']}]",
                definition=f"share of core ads first published within {int(float(r['within_days']))} days of the collection")
    for r in reg.table("S05_snapshot_age_distribution"):
        reg.add(f"snapshot_age_n_within_{int(float(r['within_days']))}d", _f(r["postings"]), "count", source=f"outputs/tables/S05_snapshot_age_distribution.csv:postings[within_days={r['within_days']}]",
                definition=f"core ads first published within {int(float(r['within_days']))} days of the collection")
    first_month = str((ms.get("collected_at_range") or {}).get("min") or "")[:7]
    if first_month and reg.table("T13a_posted_by_month_source"):
        by_month: dict = {}
        for r in reg.table("T13a_posted_by_month_source"):
            by_month[r["posted_date"]] = by_month.get(r["posted_date"], 0) + (_f(r["count"]) or 0)
        y, m = int(first_month[:4]), int(first_month[5:7])
        for off, lab in ((0, "collection_month"), (1, "previous_month"), (2, "month_before_previous")):
            mm, yy = m - off, y
            while mm < 1:
                mm += 12
                yy -= 1
            reg.add(f"first_published_n__{lab}", by_month.get(f"{yy:04d}-{mm:02d}", 0), "count", n=core, denominator=CORE_DEN,
                    source=f"outputs/tables/T13a_posted_by_month_source.csv:count[posted_date={yy:04d}-{mm:02d}] summed over sources",
                    definition=f"core ads first published in the {lab.replace('_', ' ')} ({yy:04d}-{mm:02d})", caveat="survival decay of a one-day snapshot, not seasonality")
    pdr = ms.get("posted_date_range") or {}
    if pdr.get("min"):
        reg.add("core_posted_date_min", pdr["min"], "date", source="outputs/market_summary.json:posted_date_range.min", definition="earliest first-publish date among core postings")


def zero_fill_titles(reg: Registry) -> None:
    """Keep `title_n__*` / `title_styria_n__*` stable for every normalised title of a core family in config/role_taxonomy.json.

    T02b lists only titles with at least one core posting, so a title that is empty this week (e.g. Statistician) would
    lose its keys and break every document marker that quotes it. Such a title is registered with value 0."""
    path = reg.root / "config" / "role_taxonomy.json"
    try:
        rules = json.loads(path.read_text(encoding="utf-8")).get("rules") or []
    except (OSError, ValueError):
        return
    core_families = {r["role_family"] for r in reg.table("T02_role_family_counts")}
    for rule in rules:
        title, family = rule.get("normalized"), rule.get("family")
        if not title or family not in core_families:
            continue
        t = slug(title)
        if f"title_n__{t}" in reg.items:
            continue  # the title has postings this run: the T02b value stands
        src = f"config/role_taxonomy.json:rules[normalized={title}] (no T02b row this run: count 0)"
        reg.add(f"title_n__{t}", 0, "count", source=src, definition=f"core postings with normalised title {title} (family {family})")
        reg.add(f"title_styria_n__{t}", 0, "count", basis=ANYSITE, source=src, definition=f"Styrian core postings with normalised title {title}")


def zero_fill_cities(reg: Registry) -> None:
    """Keep `styria_city_n__*` stable for the cities declared in config/registry_declared_categories.json (T03c lists only cities present this run)."""
    path = reg.root / "config" / "registry_declared_categories.json"
    try:
        cities = (json.loads(path.read_text(encoding="utf-8")).get("styria_city_n") or [])
    except (OSError, ValueError):
        return
    for city in cities:
        if f"styria_city_n__{slug(city)}" in reg.items:
            continue  # the city has postings this run: the T03c value stands
        reg.add(f"styria_city_n__{slug(city)}", 0, "count", basis=ANYSITE, source=f"config/registry_declared_categories.json:styria_city_n[{city}] (no T03c row this run: count 0)",
                definition=f"Styrian core postings located in {city}")


def families_and_geo(reg: Registry) -> None:
    ms = (reg.json("market_summary").get("counts") or {})
    core = ms.get("core_canonical")
    for r in reg.table("T02_role_family_counts"):
        f, t = r["role_family"], slug(r["role_family"])
        src = f"outputs/tables/T02_role_family_counts.csv:%s[role_family={f}]"
        reg.add(f"family_n__{t}", _f(r["count"]), "count", source=src % "count", n=_f(r["n"]), denominator=CORE_DEN, definition=f"core postings in family {f}")
        reg.add(f"family_share__{t}", _f(r["count"]) / _f(r["n"]), "share", source=src % "count/n", n=_f(r["n"]), denominator=CORE_DEN, definition=f"share of core postings in family {f}")
        reg.add(f"family_styria_n__{t}", _f(r["styria_count"]), "count", source=src % "styria_count", basis=ANYSITE, n=ms.get("styria_core"),
                denominator="Styrian core postings (any-site)", definition=f"Styrian core postings in family {f}", caveat="tentative: small n")
        reg.add(f"family_vienna_n__{t}", _f(r["vienna_count"]), "count", source=src % "vienna_count", basis=ANYSITE, definition=f"Viennese core postings in family {f}")
        reg.add(f"family_graz_area_n__{t}", _f(r["graz_area_count"]), "count", source=src % "graz_area_count", basis=ANYSITE, definition=f"Graz-area core postings in family {f}")
        if ms.get("styria_core"):
            reg.add(f"family_styria_share__{t}", _f(r["styria_count"]) / ms["styria_core"], "share", source=src % "styria_count/market_summary styria_core",
                    basis=ANYSITE, n=ms["styria_core"], denominator="Styrian core postings (any-site)", definition=f"family {f} as a share of Styrian core postings", caveat="tentative")
    fam = {r["role_family"]: r for r in reg.table("T02_role_family_counts")}
    if fam:
        big = max(fam.values(), key=lambda r: _f(r["styria_count"]))
        reg.add("styria_largest_family_n", _f(big["styria_count"]), "count", n=ms.get("styria_core"), basis=ANYSITE, denominator="Styrian core postings (any-site)",
                source="outputs/tables/T02_role_family_counts.csv:max(styria_count)", definition=f"largest Styrian family cell ({big['role_family']}); the robustness rule needs n >= 30", caveat="tentative: every Styrian cell is below the n = 30 rule")
    # named aliases for the hand-written headline keys
    for f, short in (("marketing_analytics", "marketing_analytics"), ("product_analytics", "product_analytics"),
                     ("data_engineering", "data_engineering"), ("data_science", "data_science"), ("data_analytics", "data_analytics"),
                     ("business_analysis", "business_analysis"), ("bi", "bi"), ("data_governance", "data_governance")):
        reg.alias(f"{short}_n", f"family_n__{slug(f)}")
        reg.alias(f"{short}_share", f"family_share__{slug(f)}")
        reg.alias(f"{short}_styria_n", f"family_styria_n__{slug(f)}")
    reg.alias("marketing_analytics_n_styria", "family_styria_n__marketing_analytics")
    # titles
    for r in reg.table("T02b_normalized_title_counts"):
        t = slug(r["normalized_title"])
        reg.add(f"title_n__{t}", _f(r["count"]), "count", source=f"outputs/tables/T02b_normalized_title_counts.csv:count[normalized_title={r['normalized_title']}]",
                definition=f"core postings with normalised title {r['normalized_title']} (family {r['role_family']})")
        reg.add(f"title_styria_n__{t}", _f(r["styria"]), "count", basis=ANYSITE,
                source=f"outputs/tables/T02b_normalized_title_counts.csv:styria[normalized_title={r['normalized_title']}]",
                definition=f"Styrian core postings with normalised title {r['normalized_title']}")
    zero_fill_titles(reg)
    # states (primary-state basis, T03a)
    share_table(reg, "T03a_state_counts", "state", "state_share", unit_label="share of core postings by primary state", denominator=CORE_DEN, basis=PRIMARY,
                count_prefix="state_n")
    reg.alias("vienna_share_core_t03a", "state_share__wien")
    reg.alias("upper_austria_share_core", "state_share__oberoesterreich")
    reg.alias("upper_austria_n", "state_n__oberoesterreich")
    reg.alias("styria_share_primary_state", "state_share__steiermark")
    reg.alias("vorarlberg_share_core", "state_share__vorarlberg")
    reg.alias("lower_austria_share_core", "state_share__niederoesterreich")
    reg.alias("salzburg_share_core", "state_share__salzburg")
    reg.alias("tyrol_share_core", "state_share__tirol")
    reg.alias("carinthia_share_core", "state_share__kaernten")
    reg.alias("unspecified_state_share_core", "state_share__unspecified")
    reg.alias("unspecified_state_n", "state_n__unspecified")
    unsp = reg.items.get("state_n__unspecified")
    if unsp and core:
        reg.add("state_known_share", 1 - unsp["value"] / core, "share", n=core, denominator=CORE_DEN, basis=PRIMARY,
                source="outputs/tables/T03a_state_counts.csv:1 - count[state=unspecified]/n", definition="share of core postings whose primary state is known")
    # flag-basis summary (T03d)
    for r in reg.table("T03d_geo_summary"):
        k = r["metric"]
        reg.add(f"geo_flag__{slug(k)}", _f(r["count"]), "count", source=f"outputs/tables/T03d_geo_summary.csv:count[metric={k}]", basis=ANYSITE if k in ("styria", "graz_area", "graz_city", "vienna") else "",
                definition=f"core postings: {k}")
    reg.alias("graz_city_n", "geo_flag__graz_city")
    reg.alias("austria_wide_flag_n", "geo_flag__austria_wide_flag")
    reg.alias("multi_location_n", "geo_flag__multi_location")
    reg.alias("location_unspecified_n", "geo_flag__location_unspecified")
    for r in reg.table("T03b_geo_scope"):
        reg.add(f"geo_scope_n__{slug(r['geo_scope'])}", _f(r["count"]), "count", source=f"outputs/tables/T03b_geo_scope.csv:count[geo_scope={r['geo_scope']}]", definition=f"core postings, geo scope {r['geo_scope']}")
    for r in reg.table("T03c_styria_cities"):
        reg.add(f"styria_city_n__{slug(r['city'])}", _f(r["count"]), "count", source=f"outputs/tables/T03c_styria_cities.csv:count[city={r['city']}]", basis=ANYSITE,
                definition=f"Styrian core postings located in {r['city']}")
    zero_fill_cities(reg)
    g = reg.json("market_summary").get("counts") or {}
    gcity = _f((_rowget(reg.table("T03d_geo_summary"), "metric", "graz_city") or {}).get("count"))
    if gcity is not None and g.get("styria_core"):
        reg.add("graz_city_share_of_styria", gcity / g["styria_core"], "share", n=g["styria_core"], denominator="Styrian core postings (any-site)", basis=ANYSITE,
                source="outputs/tables/T03d_geo_summary.csv:graz_city / market_summary styria_core", definition="Graz-city postings as a share of the Styrian postings")
    # primary-state Graz area subshare
    if g.get("graz_area_core_primary_styria") and g.get("styria_core_primary_state"):
        reg.add("graz_area_share_of_styria_primary_state", g["graz_area_core_primary_styria"] / g["styria_core_primary_state"], "share", n=g["styria_core_primary_state"],
                denominator="Styrian core postings (primary state)", basis=PRIMARY, source="outputs/market_summary.json:counts.graz_area_core_primary_styria/styria_core_primary_state",
                definition="Graz-area postings as a share of Styrian postings, primary-state basis")
    if g.get("graz_area_core") and g.get("styria_core"):
        reg.add("graz_area_share_of_styria_flag", g["graz_area_core"] / g["styria_core"], "share", n=g["styria_core"], denominator="Styrian core postings (any-site)", basis=ANYSITE,
                source="outputs/market_summary.json:counts.graz_area_core/styria_core", definition="Graz-area postings as a share of Styrian postings, any-site basis")
    # Styria vs Austria family mix
    if g.get("styria_core"):
        for fam_key in ("data_engineering", "business_analysis"):
            r = _rowget(reg.table("T02_role_family_counts"), "role_family", fam_key)
            if r:
                reg.add(f"family_share_of_styria_flag__{fam_key}", _f(r["styria_count"]) / g["styria_core"], "share", n=g["styria_core"], basis=ANYSITE,
                        denominator="Styrian core postings (any-site)", source=f"outputs/tables/T02_role_family_counts.csv:styria_count/styria_core[{fam_key}]",
                        definition=f"{fam_key} as a share of the Styrian core postings", caveat="tentative")
    # employer tables Styria
    # Vienna family share etc. covered above
    _ = core


def skills(reg: Registry) -> None:
    cats = ["all_tech", "bi_tools", "business_domain", "certifications", "cloud_platforms", "data_engineering", "data_platforms",
            "ml_ai", "programming_languages", "python_ecosystem", "soft_skills", "statistics_methods", "work_model"]
    for cat in cats:
        share_table(reg, f"T05_skills_{cat}", "skill", "skill_share", unit_label=f"share of the core postings with a description that mention the skill ({cat})",
                    denominator=DESC_DEN, basis=TEXT, caveat=CAVEAT_MENTION, count_prefix="skill_n")
        share_table(reg, f"T05_skills_{cat}_by_family", ("role_family", "skill"), "skill_family_share",
                    unit_label=f"share of a family's postings with a description that mention the skill ({cat})", denominator="family postings with a description",
                    basis=TEXT, caveat=CAVEAT_MENTION + "; family n is small for several families", count_prefix="skill_family_n")
        share_table(reg, f"T05_skills_{cat}_by_styria", ("styria_flag", "skill"), "skill_styria_share",
                    unit_label=f"share of Styrian (any-site) vs rest-of-Austria postings that mention the skill ({cat})", denominator="postings with a description in the group",
                    basis=ANYSITE + "; " + TEXT, caveat=CAVEAT_MENTION + "; Styria n = 58, indicative", count_prefix="skill_styria_n")
    share_table(reg, "T05_skills_all_tech_by_seniority", ("seniority", "skill"), "skill_seniority_share", unit_label="share of a seniority group's postings that mention the skill",
                denominator="postings with a description in the seniority group", basis=TEXT, caveat=CAVEAT_MENTION, count_prefix="skill_seniority_n")
    for r in reg.table("T05_skills_all_tech"):
        for col, key in (("ci_low", "skill_ci_low"), ("ci_high", "skill_ci_high")):
            if _f(r.get(col)) is not None:
                reg.add(f"{key}__{slug(r['skill'])}", _f(r[col]), "share", n=_f(r["n"]), denominator=DESC_DEN, basis=TEXT,
                        source=f"outputs/tables/T05_skills_all_tech.csv:{col}[skill={r['skill']}]", definition=f"{'lower' if col == 'ci_low' else 'upper'} 95 % Wilson bound of the share mentioning {r['skill']}")
    # headline aliases (hand-named keys used in the documents)
    for key, skill in (("sql", "SQL"), ("python", "Python"), ("azure", "Azure"), ("power_bi", "Power BI"), ("excel", "Excel"), ("cloud", "Cloud (generic)"),
                       ("etl", "ETL/ELT"), ("data_quality", "Data Governance/Quality"), ("genai", "Generative AI / LLM"), ("statistics", "Statistics (general)"),
                       ("aws", "AWS"), ("gcp", "GCP"), ("tableau", "Tableau"), ("databricks", "Databricks"), ("ml", "Machine Learning"),
                       ("data_modelling", "Data Modeling"), ("ci_cd", "CI/CD"), ("visualisation", "Data Visualization"), ("generic_ai", "AI (generic)"),
                       ("git", "Git"), ("rest", "REST APIs"), ("qlik", "Qlik"), ("pandas", "pandas"), ("dbt", "dbt"), ("scikit_learn", "scikit-learn"),
                       ("pytorch", "PyTorch"), ("fabric", "Microsoft Fabric"), ("snowflake", "Snowflake"), ("docker", "Docker"), ("kubernetes", "Kubernetes"),
                       ("spark", "Spark"), ("r", "R"), ("java", "Java"), ("ab_testing", "A/B Testing / Experimentation"), ("dax", "DAX/M"),
                       ("data_warehouse", "Data Warehouse (generic)"), ("mathematics", "Mathematics"), ("looker", "Looker"), ("sap_bw_bo", "SAP BW/BO"),
                       ("sql_server", "SQL Server"), ("mlops", "MLOps"), ("streaming", "Streaming"), ("oracle", "Oracle"), ("rag", "RAG"),
                       ("agents", "AI agents / tool-calling"), ("causal_inference", "Causal Inference"), ("regression", "Regression")):
        reg.alias(f"{key}_share", f"skill_share__{slug(skill)}")
        reg.alias(f"{key}_n", f"skill_n__{slug(skill)}")
    for key, skill in (("python", "Python"), ("sql", "SQL"), ("azure", "Azure"), ("cloud", "Cloud (generic)"), ("etl", "ETL/ELT"), ("databricks", "Databricks"),
                       ("git", "Git"), ("excel", "Excel"), ("power_bi", "Power BI"), ("statistics", "Statistics (general)"), ("ci_cd", "CI/CD"), ("gcp", "GCP"),
                       ("genai", "Generative AI / LLM")):
        reg.alias(f"{key}_share_styria", f"skill_styria_share__styria__{slug(skill)}")
        reg.alias(f"{key}_n_styria", f"skill_styria_n__styria__{slug(skill)}")
        reg.alias(f"{key}_share_rest", f"skill_styria_share__rest_of_austria__{slug(skill)}")
    # SQL excluding SQL Server mentions: not tabulated -> no key (the documents keep it literal)
    # cooccurrence
    for r in reg.table("T06_cooccurrence_pairs"):
        a, b = r["skill_a"], r["skill_b"]
        tag = f"{slug(a)}__{slug(b)}"
        src = f"outputs/tables/T06_cooccurrence_pairs.csv:%s[{a} x {b}]"
        reg.add(f"cooc_share__{tag}", _f(r["share_of_postings"]), "share", n=_f(r["n"]), denominator=DESC_DEN, basis=TEXT, source=src % "share_of_postings",
                definition=f"share of postings that mention both {a} and {b}")
        reg.add(f"cooc_n__{tag}", _f(r["both"]), "count", n=_f(r["n"]), source=src % "both", definition=f"postings that mention both {a} and {b}")
        reg.add(f"cooc_b_given_a__{tag}", _f(r["p_b_given_a"]), "share", source=src % "p_b_given_a", definition=f"share of {a} postings that also mention {b}")
        reg.add(f"cooc_a_given_b__{tag}", _f(r["p_a_given_b"]), "share", source=src % "p_a_given_b", definition=f"share of {b} postings that also mention {a}")
        reg.add(f"cooc_lift__{tag}", _f(r["lift"]), "ratio", source=src % "lift", definition=f"lift of {a} with {b}", display=fmt_value(_f(r["lift"]), "number"))
    for r in reg.table("T06b_top_stacks_size3"):
        reg.add(f"stack_share__{slug(r['stack'])}", _f(r["share"]) if False else _f(r["count"]) / _f(r["n"]), "share", n=_f(r["n"]), denominator=DESC_DEN,
                basis=TEXT, source=f"outputs/tables/T06b_top_stacks_size3.csv:count/n[stack={r['stack']}]", definition=f"share of postings that mention the three-item stack {r['stack']}")
    # topic slices and entry-track
    for r in reg.table("T05f_topic_demand"):
        t = slug(r["skill"])
        for col, prefix in (("share", "topic_share"),):
            pass
        reg.add(f"topic_share__{t}", _f(r["count"]) / _f(r["n"]), "share", n=_f(r["n"]), denominator=DESC_DEN, basis=TEXT,
                source=f"outputs/tables/T05f_topic_demand.csv:count/n[skill={r['skill']}]", definition=f"share of postings that mention topic {r['skill']} (T05f)", caveat=CAVEAT_MENTION)
        if _f(r.get("intern_student_n")):
            reg.add(f"topic_intern_share__{t}", _f(r["intern_student_count"]) / _f(r["intern_student_n"]), "share", n=_f(r["intern_student_n"]), denominator="intern/student ads with a description",
                    source=f"outputs/tables/T05f_topic_demand.csv:intern_student_count/intern_student_n[skill={r['skill']}]", definition=f"share of intern ads that mention {r['skill']}")
        if _f(r.get("trainee_junior_n")):
            reg.add(f"topic_junior_share__{t}", _f(r["trainee_junior_count"]) / _f(r["trainee_junior_n"]), "share", n=_f(r["trainee_junior_n"]), denominator="junior/trainee ads with a description",
                    source=f"outputs/tables/T05f_topic_demand.csv:trainee_junior_count/trainee_junior_n[skill={r['skill']}]", definition=f"share of junior ads that mention {r['skill']}")
    share_table(reg, "T17_skills_by_entry_track", ("entry_track", "skill"), "skill_entry_share", unit_label="share of an entry-track group's ads that mention the skill",
                denominator="ads with a description in the entry-track group", basis=TEXT, caveat="small entry-track denominators (see entry_track_denominators_vs_30): directional only", count_prefix="skill_entry_n")
    share_table(reg, "T17b_german_by_entry_track", ("entry_track", "german_requirement"), "german_entry_share", unit_label="German requirement bucket within an entry-track group",
                denominator="ads with a description in the entry-track group", basis=TEXT, count_prefix="german_entry_n")
    # family profile (T14) numeric columns
    for r in reg.table("T14_family_profiles"):
        t = slug(r["role_family"])
        for col, key, unit in (("n_with_description", "family_desc_n", "count"), ("german_required_share", "family_german_stated_share", "share"),
                               ("english_posting_share", "family_english_posting_share", "share"), ("degree_required_share", "family_degree_required_share", "share"),
                               ("median_min_salary", "family_salary_floor_median_eur", "eur"), ("n_salary", "family_salary_n", "count"),
                               ("senior_or_lead_share", "family_senior_or_lead_share", "share")):
            reg.add(f"{key}__{t}", _f(r[col]), unit, source=f"outputs/tables/T14_family_profiles.csv:{col}[role_family={r['role_family']}]",
                    definition=f"{col} for family {r['role_family']}", n=_f(r["n_with_description"]), basis=TEXT if unit == "share" else "")


def language(reg: Registry) -> None:
    gr = {r["german_requirement"]: r for r in reg.table("T07_german_requirement_by_overall")}
    n = _f(next(iter(gr.values()))["n"]) if gr else None
    share_table(reg, "T07_german_requirement_by_overall", "german_requirement", "german_share", unit_label="German requirement wording bucket",
                denominator=DESC_DEN, basis=TEXT, caveat="'stated' = required (explicit) + required_implied (a level is named); silence in a German-written ad usually still means German",
                count_prefix="german_n", known=GERMAN_REQUIREMENT_BUCKETS)
    if gr and n:
        stated = _f(gr["required"]["count"]) + _f(gr["required_implied"]["count"])
        reg.add("german_stated_share", stated / n, "share", n=n, denominator=DESC_DEN, basis=TEXT, source="outputs/tables/T07_german_requirement_by_overall.csv:(required+required_implied)/n",
                definition="share of ads that state a German requirement (explicit 'required' or a stated level)", caveat="a share of ads that state it, not of jobs that require it")
        reg.add("german_stated_n", stated, "count", n=n, denominator=DESC_DEN, basis=TEXT, source="outputs/tables/T07_german_requirement_by_overall.csv:required+required_implied",
                definition="ads that state a German requirement")
        reg.alias("german_required_explicit_share", "german_share__required")
        reg.alias("german_level_stated_share", "german_share__required_implied")
        reg.alias("german_preferred_share", "german_share__preferred")
        reg.alias("german_mentioned_share", "german_share__mentioned")
        reg.alias("german_not_mentioned_share", "german_share__not_mentioned")
        reg.alias("german_not_needed_share", "german_share__explicitly_not_required")
    share_table(reg, "T07a_german_level_overall", "german_level_bucket", "german_level_share", unit_label="German level bucket in the ad", denominator=DESC_DEN, basis=TEXT,
                caveat="'C1/fluent' is mostly 'sehr gut'/'very good' wording: read as 'high level demanded', not a certified C1", count_prefix="german_level_n")
    reg.alias("german_c1_bucket_share", "german_level_share__c1_fluent")
    reg.alias("german_b2_share", "german_level_share__b2_good")
    reg.alias("german_c2_native_share", "german_level_share__c2_native")
    gl = reg.table("T07a_german_level_overall")
    b1_or_below = sum(_f(r["count"]) for r in gl if r["german_level_bucket"] in ("B1", "A1-A2"))
    if gl and n:
        reg.add("german_b1_or_below_n", b1_or_below, "count", n=n, denominator=DESC_DEN, basis=TEXT, source="outputs/tables/T07a_german_level_overall.csv:count[bucket in B1, A1-A2]",
                definition="ads whose German wording names B1 or below", caveat="B1 or below is named in so few ads that moving from A2 to B1 unlocks nothing measurable")
    share_table(reg, "T07b_english_requirement", "english_requirement", "english_req_share", unit_label="English requirement wording bucket", denominator=DESC_DEN, basis=TEXT, count_prefix="english_req_n")
    er = {r["english_requirement"]: r for r in reg.table("T07b_english_requirement")}
    if er and n:
        reg.add("english_stated_share", (_f(er["required"]["count"]) + _f(er["required_implied"]["count"])) / n, "share", n=n, denominator=DESC_DEN, basis=TEXT,
                source="outputs/tables/T07b_english_requirement.csv:(required+required_implied)/n", definition="share of ads that state an English requirement/level")
    share_table(reg, "T07b_english_level", "english_level_bucket", "english_level_share", unit_label="English level bucket in the ad", denominator=DESC_DEN, basis=TEXT, count_prefix="english_level_n")
    share_table(reg, "T07c_posting_language", "posting_language", "posting_language_share", unit_label="language the ad is written in", denominator=DESC_DEN, basis=TEXT, count_prefix="posting_language_n")
    reg.alias("english_posting_share", "posting_language_share__en")
    reg.alias("english_posting_n", "posting_language_n__en")
    reg.alias("german_posting_share", "posting_language_share__de")
    reg.alias("german_posting_n", "posting_language_n__de")
    share_table(reg, "T07c_posting_language_by_family", ("role_family", "posting_language"), "posting_language_family_share", unit_label="posting language within a family",
                denominator="family postings with a description", basis=TEXT, count_prefix="posting_language_family_n")
    share_table(reg, "T07c_posting_language_by_styria", ("styria_flag", "posting_language"), "posting_language_styria_share", unit_label="posting language, Styria vs rest",
                denominator="postings with a description in the group", basis=ANYSITE + "; " + TEXT, caveat="Styria n = 58, tentative", count_prefix="posting_language_styria_n")
    reg.alias("english_posting_n_styria", "posting_language_styria_n__styria__en")
    reg.alias("english_posting_share_styria", "posting_language_styria_share__styria__en")
    share_table(reg, "T07_german_requirement_by_role_family", ("role_family", "german_requirement"), "german_family_share", unit_label="German requirement bucket within a family",
                denominator="family postings with a description", basis=TEXT, count_prefix="german_family_n")
    share_table(reg, "T07_german_requirement_by_styria_flag", ("styria_flag", "german_requirement"), "german_styria_share", unit_label="German requirement bucket, Styria vs rest",
                denominator="postings with a description in the group", basis=ANYSITE + "; " + TEXT, caveat="Styria n = 58, tentative", count_prefix="german_styria_n")
    # stated per family / Styria
    for fam in sorted({r["role_family"] for r in reg.table("T07_german_requirement_by_role_family")}):
        rows = {r["german_requirement"]: r for r in reg.table("T07_german_requirement_by_role_family") if r["role_family"] == fam}
        if "required" in rows or "required_implied" in rows:
            nn = _f(next(iter(rows.values()))["n"])
            cnt = sum(_f(rows[k]["count"]) for k in ("required", "required_implied") if k in rows)
            reg.add(f"german_stated_share__{slug(fam)}", cnt / nn, "share", n=nn, denominator="family postings with a description", basis=TEXT,
                    source=f"outputs/tables/T07_german_requirement_by_role_family.csv:(required+required_implied)/n[{fam}]", definition=f"share of {fam} ads that state a German requirement")
            reg.add(f"german_stated_n__{slug(fam)}", cnt, "count", n=nn, source=f"outputs/tables/T07_german_requirement_by_role_family.csv:required+required_implied[{fam}]",
                    definition=f"{fam} ads that state a German requirement")
    for grp in ("Styria", "Rest of Austria"):
        rows = {r["german_requirement"]: r for r in reg.table("T07_german_requirement_by_styria_flag") if r["styria_flag"] == grp}
        if rows:
            nn = _f(next(iter(rows.values()))["n"])
            cnt = sum(_f(rows[k]["count"]) for k in ("required", "required_implied") if k in rows)
            tag = slug(grp)
            reg.add(f"german_stated_share__{tag}", cnt / nn, "share", n=nn, denominator="postings with a description in the group", basis=ANYSITE + "; " + TEXT,
                    source=f"outputs/tables/T07_german_requirement_by_styria_flag.csv:(required+required_implied)/n[{grp}]", definition=f"share of {grp} ads that state a German requirement",
                    caveat="Styria n = 58, tentative" if grp == "Styria" else "")
            reg.add(f"german_stated_n__{tag}", cnt, "count", n=nn, basis=ANYSITE, source=f"outputs/tables/T07_german_requirement_by_styria_flag.csv:required+required_implied[{grp}]",
                    definition=f"{grp} ads that state a German requirement")
    reg.alias("german_stated_share_styria", "german_stated_share__styria")
    reg.alias("german_stated_n_styria", "german_stated_n__styria")
    reg.alias("german_stated_share_elsewhere", "german_stated_share__rest_of_austria")
    # english-written ads: German status (T07d)
    d = {r["posting_language"]: r for r in reg.table("T07d_posting_language_x_german_req")}
    if "en" in d:
        r = d["en"]
        tot = sum(_f(r[k]) for k in r if k != "posting_language")
        stated = _f(r["required"]) + _f(r["required_implied"])
        for key, cnt, label in (("english_ads_german_stated", stated, "German requirement stated"), ("english_ads_german_preferred", _f(r["preferred"]), "German preferred"),
                                ("english_ads_german_silent", _f(r["not_mentioned"]), "German not mentioned")):
            reg.add(f"{key}_share", cnt / tot, "share", n=tot, denominator="English-written ads with a description", basis=TEXT,
                    source=f"outputs/tables/T07d_posting_language_x_german_req.csv[posting_language=en]", definition=f"share of English-written ads with: {label}")
    if "de" in d:
        r = d["de"]
        tot = sum(_f(r[k]) for k in r if k != "posting_language")
        stated = _f(r["required"]) + _f(r["required_implied"])
        reg.add("german_ads_german_stated_share", stated / tot, "share", n=tot, denominator="German-written ads with a description", basis=TEXT,
                source="outputs/tables/T07d_posting_language_x_german_req.csv[posting_language=de]", definition="share of German-written ads that state a German requirement")
    # addressable scenarios T07e
    for r in reg.table("T07e_addressable_market_scenarios"):
        sc = r["scope"]
        tag = slug(sc.replace("family:", "family_"))
        nn = _f(r["n"])
        basis = ANYSITE if sc in ("Styria", "Graz area", "Vienna") else TEXT
        for col, key, label in (("english_posting_no_german_req", "english_no_german", "English-written and no stated German requirement"),
                                ("no_explicit_german_requirement", "no_explicit_german", "no explicit German requirement (silence included)"),
                                ("german_not_required_at_C1_or_above", "not_c1", "German not required at C1-equivalent")):
            src = f"outputs/tables/T07e_addressable_market_scenarios.csv:{col}[scope={sc}]"
            reg.add(f"{key}_n__{tag}", _f(r[col]), "count", n=nn, denominator=f"{sc} postings with a description", basis=basis, source=src,
                    definition=f"{sc}: ads that are {label}",
                    caveat="a bracketing reading, not a measurement of what a candidate can obtain; German may still be preferred or expected")
            reg.add(f"{key}_share__{tag}", _f(r[col]) / nn, "share", n=nn, denominator=f"{sc} postings with a description", basis=basis, source=src,
                    definition=f"{sc}: share of ads that are {label}")
        reg.add(f"addressable_scope_n__{tag}", nn, "count", source=f"outputs/tables/T07e_addressable_market_scenarios.csv:n[scope={sc}]", basis=basis,
                definition=f"{sc}: postings in the T07e denominator")
    nat, vie = reg.items.get("english_no_german_n__austria"), reg.items.get("english_no_german_n__vienna")
    if nat and vie:
        reg.add("english_no_german_vienna_share_of_national", vie["value"] / nat["value"], "share", n=nat["value"], denominator="English-written ads without a stated German requirement, Austria",
                source="outputs/tables/T07e_addressable_market_scenarios.csv:english_posting_no_german_req[Vienna]/[Austria]", basis=ANYSITE,
                definition="Vienna's share of the national English-written, no-stated-German ads (the addressable set at A2)")
    for scope, tag in (("Austria", "national"), ("Styria", "styria"), ("Graz area", "graz_area"), ("Vienna", "vienna")):
        for key in ("english_no_german_n", "english_no_german_share", "no_explicit_german_n", "not_c1_n", "addressable_scope_n"):
            reg.alias(f"{key}_{tag}", f"{key}__{slug(scope)}")


def pay_and_work(reg: Registry) -> None:
    cov = {r["metric"]: _f(r["count"]) for r in reg.table("T09_salary_coverage")}
    core = (reg.json("market_summary").get("counts") or {}).get("core_canonical")
    if cov.get("with_salary_figure") and core:
        for k, label in (("with_salary_figure", "core ads that state a salary figure"), ("with_range", "core ads that state a range"),
                         ("kv_minimum_mention", "core ads that mention the collective-agreement minimum"), ("overpay_mention", "core ads that mention overpay (Überzahlung)")):
            reg.add(f"salary_{k}_n", cov[k], "count", source=f"outputs/tables/T09_salary_coverage.csv:count[metric={k}]", n=core, denominator=CORE_DEN, definition=label)
            reg.add(f"salary_{k}_share", cov[k] / core, "share", source=f"outputs/tables/T09_salary_coverage.csv:count[metric={k}]/core_canonical", n=core, denominator=CORE_DEN, definition=label.replace("core ads", "share of core ads"),
                    caveat="advertised legal floors (KV minimum), not offers and not pay")
        n_fig = cov["with_salary_figure"]
    for k, v in cov.items():
        if k != "core_postings":
            reg.add(f"salary_coverage__{slug(k)}", v, "count", source=f"outputs/tables/T09_salary_coverage.csv:count[metric={k}]", definition=f"salary coverage: {k}")
    imp = sum(_f(r["implausible"]) or 0 for r in reg.table("T09a_salary_basis_by_source"))
    if reg.table("T09a_salary_basis_by_source"):
        reg.add("salary_implausible_n", imp, "count", source="outputs/tables/T09a_salary_basis_by_source.csv:implausible summed", definition="salary figures discarded as implausible")
    # basis by source: minimum_only / range (Q07 basis)
    bs = reg.table("T09a_salary_basis_by_source")
    if bs:
        mn = sum(_f(r["minimum_only"]) for r in bs)
        rg = sum(_f(r["range"]) for r in bs)
        none = sum(_f(r["none"]) for r in bs)
        parsed = mn + rg
        if parsed:
            reg.add("salary_minimum_only_n", mn, "count", source="outputs/tables/T09a_salary_basis_by_source.csv:minimum_only summed", definition="parsed salary figures that are a single minimum", n=parsed, denominator="parsed figures (minimum_only + range)")
            reg.add("salary_minimum_only_share_of_parsed", mn / parsed, "share", n=parsed, denominator="parsed figures (minimum_only + range)",
                    source="outputs/tables/T09a_salary_basis_by_source.csv:minimum_only/(minimum_only+range)", definition="share of the parsed figures that are a single minimum")
            reg.add("salary_parsed_figures_n", parsed, "count", source="outputs/tables/T09a_salary_basis_by_source.csv:minimum_only+range", definition="parsed salary figures (minimum_only + range)")
        li = _rowget(bs, "source", "linkedin")
        if li:
            tot = sum(_f(li[k]) for k in ("implausible", "minimum_only", "none", "range"))
            reg.add("salary_linkedin_no_figure_share", (_f(li["none"]) + _f(li["implausible"])) / tot, "share", n=tot, denominator="LinkedIn core rows",
                    source="outputs/tables/T09a_salary_basis_by_source.csv:(none+implausible)/total[source=linkedin]",
                    definition="share of LinkedIn rows without a usable salary figure (none or implausible)")
        _ = none
    wide = {"min_median": ("floor_median_eur", "eur"), "n": ("n", "count"), "min_p25": ("floor_p25_eur", "eur"), "min_p75": ("floor_p75_eur", "eur"), "max_median": ("max_median_eur", "eur")}
    for table, idc, prefix, label in (("T09b_salary_by_role_family", "role_family", "salary_family", "family"), ("T09b_salary_by_seniority", "seniority", "salary_seniority", "seniority"),
                                       ("T09b_salary_by_state", "state", "salary_state", "state (primary)"), ("T09b_salary_by_normalized_title", "normalized_title", "salary_title", "title"),
                                       ("T09b_salary_by_source", "source", "salary_source", "source"), ("T09b_salary_by_posting_language", "posting_language", "salary_language", "posting language"),
                                       ("T09b_salary_by_remote_type", "remote_type", "salary_remote", "remote type"), ("T09b_salary_by_styria_flag", "styria_flag", "salary_styria", "Styria flag")):
        wide_table(reg, table, idc, prefix, wide, unit_label=f"advertised minimum, by {label}", n_col="n", basis="advertised legal floor (collective-agreement minimum), annual gross, monthly x 14",
                   caveat="advertised floors, not offers and not pay; only ads that state a figure")
    for r in reg.table("T09d_salary_by_skill"):
        t = slug(r["skill"])
        reg.add(f"salary_skill_floor_median_eur__{t}", _f(r["min_median"]), "eur", n=_f(r["n"]), source=f"outputs/tables/T09d_salary_by_skill.csv:min_median[skill={r['skill']}]",
                definition=f"median advertised floor of ads that mention {r['skill']}", caveat="raw, uncontrolled: 14 of 16 premiums stop separating from zero under controls (D05/BQ45) — quote both")
        reg.add(f"salary_skill_n__{t}", _f(r["n"]), "count", source=f"outputs/tables/T09d_salary_by_skill.csv:n[skill={r['skill']}]", definition=f"ads with a figure that mention {r['skill']}")
    # floor aliases (the 'Floors' of the knowledge base)
    for fam, key in (("data_analytics", "analytics"), ("data_science", "data_science"), ("data_engineering", "data_engineering"), ("business_analysis", "business_analysis"),
                     ("bi", "bi"), ("data_governance", "governance"), ("marketing_analytics", "marketing_analytics")):
        reg.alias(f"floor_{key}_eur", f"salary_family__{slug(fam)}__floor_median_eur", definition=f"median advertised minimum (legal floor) in family {fam}")
        reg.alias(f"floor_{key}_n", f"salary_family__{slug(fam)}__n")
    reg.alias("floor_junior_eur", "salary_seniority__trainee_junior__floor_median_eur", definition="median advertised minimum of junior/trainee-titled ads")
    reg.alias("floor_junior_n", "salary_seniority__trainee_junior__n")
    reg.alias("floor_intern_eur", "salary_seniority__intern_student__floor_median_eur")
    reg.alias("floor_intern_n", "salary_seniority__intern_student__n")
    reg.alias("floor_unlabelled_eur", "salary_seniority__unspecified__floor_median_eur")
    reg.alias("floor_unlabelled_n", "salary_seniority__unspecified__n")
    reg.alias("floor_senior_eur", "salary_seniority__senior__floor_median_eur")
    reg.alias("floor_senior_n", "salary_seniority__senior__n")
    reg.alias("floor_lead_eur", "salary_seniority__lead_head__floor_median_eur")
    reg.alias("floor_lead_n", "salary_seniority__lead_head__n")
    reg.alias("floor_lead_max_median_eur", "salary_seniority__lead_head__max_median_eur", definition="median of the stated upper ends of ranges, lead/head ads")
    reg.alias("floor_styria_eur", "salary_state__steiermark__floor_median_eur", basis=PRIMARY)
    reg.alias("floor_styria_n", "salary_state__steiermark__n", basis=PRIMARY)
    reg.alias("floor_vienna_eur", "salary_state__wien__floor_median_eur", basis=PRIMARY)
    reg.alias("floor_vienna_n", "salary_state__wien__n", basis=PRIMARY)
    reg.alias("floor_upper_austria_eur", "salary_state__oberoesterreich__floor_median_eur", basis=PRIMARY)
    reg.alias("floor_upper_austria_n", "salary_state__oberoesterreich__n", basis=PRIMARY)
    reg.alias("floor_salzburg_eur", "salary_state__salzburg__floor_median_eur", basis=PRIMARY)
    reg.alias("floor_salzburg_n", "salary_state__salzburg__n", basis=PRIMARY)
    reg.alias("floor_english_ads_eur", "salary_language__en__floor_median_eur")
    reg.alias("floor_german_ads_eur", "salary_language__de__floor_median_eur")
    # the legal-floor guard rail: the lowest family/seniority floor that a "never ask below" rule may cite
    junior = _rowget(reg.table("T09b_salary_by_seniority"), "seniority", "trainee_junior")
    if junior:
        reg.add("never_ask_below_eur", _f(junior["min_median"]), "eur", n=_f(junior["n"]), source="outputs/tables/T09b_salary_by_seniority.csv:min_median[seniority=trainee_junior]",
                definition="working rule: never state expectations below the median advertised floor of junior/trainee ads", caveat="a decision rule derived from the data, not a market price")
    # seniority overall
    share_table(reg, "T08_seniority_overall", "seniority", "seniority_share", unit_label="seniority wording in the title", denominator=CORE_DEN, count_prefix="seniority_n")
    share_table(reg, "T08_seniority_by_styria", ("styria_flag", "seniority"), "seniority_styria_share", unit_label="seniority wording in the title, Styria vs rest",
                denominator="core postings in the group", basis=ANYSITE, caveat="Styria n = 58, tentative", count_prefix="seniority_styria_n")
    s = reg.table("T08_seniority_overall")
    sl = [r for r in s if r["seniority"] in ("senior", "lead_head")]
    if len(sl) == 2:
        nn = _f(sl[0]["n"])
        reg.add("seniority_senior_or_lead_share", (_f(sl[0]["count"]) + _f(sl[1]["count"])) / nn, "share", n=nn, denominator=CORE_DEN,
                source="outputs/tables/T08_seniority_overall.csv:(senior+lead_head)/n", definition="share of core titles with a senior or lead/head word")
    for r in reg.table("T08a_experience_years_by_seniority"):
        t = slug(r["seniority"])
        reg.add(f"experience_years_median__{t}", _f(r["50%"]), "years", source=f"outputs/tables/T08a_experience_years_by_seniority.csv:50%[seniority={r['seniority']}]",
                n=_f(r["count"]), denominator="ads that state years", definition=f"median years of experience stated, {r['seniority']}", display=fmt_value(_f(r["50%"]), "number").rstrip("0").rstrip(".") if _f(r["50%"]) is not None else None)
        reg.add(f"experience_years_p25__{t}", _f(r["25%"]), "years", source=f"outputs/tables/T08a_experience_years_by_seniority.csv:25%[seniority={r['seniority']}]", definition=f"25th percentile of stated years, {r['seniority']}",
                display=fmt_value(_f(r["25%"]), "number").rstrip("0").rstrip(".") if _f(r["25%"]) is not None else None)
        reg.add(f"experience_years_p75__{t}", _f(r["75%"]), "years", source=f"outputs/tables/T08a_experience_years_by_seniority.csv:75%[seniority={r['seniority']}]", definition=f"75th percentile of stated years, {r['seniority']}",
                display=fmt_value(_f(r["75%"]), "number").rstrip("0").rstrip(".") if _f(r["75%"]) is not None else None)
        reg.add(f"experience_years_n__{t}", _f(r["count"]), "count", source=f"outputs/tables/T08a_experience_years_by_seniority.csv:count[seniority={r['seniority']}]", definition=f"ads with stated years, {r['seniority']}")
    ec = {r["metric"]: _f(r["count"]) for r in reg.table("T08c_experience_coverage")}
    d = ec.get("with_description")
    for k in ("explicit_years_stated", "multi_year_phrase", "entry_level_phrase"):
        if d and k in ec:
            reg.add(f"experience_{k}_n", ec[k], "count", n=d, denominator=DESC_DEN, source=f"outputs/tables/T08c_experience_coverage.csv:count[metric={k}]", definition=f"ads with: {k}")
            reg.add(f"experience_{k}_share", ec[k] / d, "share", n=d, denominator=DESC_DEN, basis=TEXT, source=f"outputs/tables/T08c_experience_coverage.csv:count[metric={k}]/with_description", definition=f"share of ads with: {k}")
    # remote / work model
    share_table(reg, "T10_remote_overall", "remote_type", "remote_share", unit_label="work-model wording", denominator=DESC_DEN, basis=TEXT, count_prefix="remote_n")
    ro = {r["remote_type"]: r for r in reg.table("T10_remote_overall")}
    if ro:
        nn = _f(next(iter(ro.values()))["n"])
        reg.add("remote_full_share", _f(ro["remote"]["count"]) / nn, "share", n=nn, denominator=DESC_DEN, basis=TEXT, source="outputs/tables/T10_remote_overall.csv:count/n[remote_type=remote]",
                definition="share of ads that say fully remote", caveat=CAVEAT_MENTION)
        reg.add("remote_full_n", _f(ro["remote"]["count"]), "count", n=nn, source="outputs/tables/T10_remote_overall.csv:count[remote_type=remote]", definition="ads that say fully remote")
        reg.add("remote_silent_share", _f(ro["unknown"]["count"]) / nn, "share", n=nn, denominator=DESC_DEN, basis=TEXT, source="outputs/tables/T10_remote_overall.csv:count/n[remote_type=unknown]",
                definition="share of ads that say nothing about the work model", caveat=CAVEAT_MENTION)
        reg.add("remote_onsite_share", _f(ro["on_site"]["count"]) / nn, "share", n=nn, denominator=DESC_DEN, basis=TEXT, source="outputs/tables/T10_remote_overall.csv:count/n[remote_type=on_site]", definition="share of ads that say on-site")
        hy = _f(ro["hybrid"]["count"]) + _f(ro["hybrid_or_flexible"]["count"])
        reg.add("remote_hybrid_any_share", hy / nn, "share", n=nn, denominator=DESC_DEN, basis=TEXT, source="outputs/tables/T10_remote_overall.csv:(hybrid+hybrid_or_flexible)/n",
                definition="share of ads that mention some home-office / hybrid arrangement")
        reg.alias("remote_hybrid_explicit_share", "remote_share__hybrid", definition="share of ads with an explicit hybrid pattern or day/percentage")
        reg.alias("remote_hybrid_general_share", "remote_share__hybrid_or_flexible", definition="share of ads with a general home-office / flexible mention")
    share_table(reg, "T10_remote_by_family", ("role_family", "remote_type"), "remote_family_share", unit_label="work-model wording within a family", denominator="family postings with a description", basis=TEXT, count_prefix="remote_family_n")
    share_table(reg, "T10_remote_by_styria", ("styria_flag", "remote_type"), "remote_styria_share", unit_label="work-model wording, Styria vs rest", denominator="postings with a description in the group",
                basis=ANYSITE + "; " + TEXT, caveat="Styria n = 58, tentative", count_prefix="remote_styria_n")
    for fam in sorted({r["role_family"] for r in reg.table("T10_remote_by_family")}):
        rows = {r["remote_type"]: r for r in reg.table("T10_remote_by_family") if r["role_family"] == fam}
        if "hybrid" in rows or "hybrid_or_flexible" in rows:
            nn = _f(next(iter(rows.values()))["n"])
            cnt = sum(_f(rows[k]["count"]) for k in ("hybrid", "hybrid_or_flexible") if k in rows)
            reg.add(f"remote_hybrid_any_share__{slug(fam)}", cnt / nn, "share", n=nn, denominator="family postings with a description", basis=TEXT,
                    source=f"outputs/tables/T10_remote_by_family.csv:(hybrid+hybrid_or_flexible)/n[{fam}]", definition=f"share of {fam} ads that mention a hybrid/home-office arrangement")
    sty = {r["remote_type"]: r for r in reg.table("T10_remote_by_styria") if r["styria_flag"] == "Styria"}
    if sty:
        nn = _f(next(iter(sty.values()))["n"])
        cnt = sum(_f(sty[k]["count"]) for k in ("hybrid", "hybrid_or_flexible") if k in sty)
        reg.add("remote_hybrid_any_n_styria", cnt, "count", n=nn, basis=ANYSITE, source="outputs/tables/T10_remote_by_styria.csv:hybrid+hybrid_or_flexible[Styria]", definition="Styrian ads that mention a hybrid/home-office arrangement")
        reg.add("remote_hybrid_any_share_styria", cnt / nn, "share", n=nn, basis=ANYSITE, denominator="Styrian postings with a description", source="outputs/tables/T10_remote_by_styria.csv:(hybrid+hybrid_or_flexible)/n[Styria]",
                definition="share of Styrian ads that mention a hybrid/home-office arrangement")
    ha = reg.table("T10a_home_office_days")
    if ha:
        reg.add("home_office_days_stated_n", sum(_f(r.get("count")) or 0 for r in ha), "count", source="outputs/tables/T10a_home_office_days.csv:count summed", definition="ads that state home-office days per week")
    share_table(reg, "T12_employment_type", "employment_type", "employment_share", unit_label="employment type", denominator=CORE_DEN, count_prefix="employment_n")
    # education
    share_table(reg, "T11e_degree_requirement_strength", "degree_requirement", "degree_strength_share", unit_label="strength of the degree wording", denominator=DESC_DEN, basis=TEXT, count_prefix="degree_strength_n")
    share_table(reg, "T11a_degree_levels", "degree_level", "degree_level_share", unit_label="degree level named", denominator=DESC_DEN, basis=TEXT, count_prefix="degree_level_n")
    share_table(reg, "T11b_degree_fields", "degree_field", "degree_field_share", unit_label="degree field named near education words", denominator=DESC_DEN, basis=TEXT, count_prefix="degree_field_n")
    share_table(reg, "T11e_degree_requirement_strength_by_family", ("role_family", "degree_requirement"), "degree_strength_family_share", unit_label="strength of the degree wording within a family",
                denominator="family postings with a description", basis=TEXT, count_prefix="degree_strength_family_n")
    share_table(reg, "T11c_degree_required_by_family", ("role_family", "degree_required"), "degree_required_family_share", unit_label="degree-required wording within a family (True = required)",
                denominator="family postings with a description", basis=TEXT, count_prefix="degree_required_family_n")
    share_table(reg, "T11d_certifications", "certification", "cert_share", unit_label="certification wording", denominator=DESC_DEN, basis=TEXT, caveat="specific certificates are rare; the vocabulary was extended with exam codes", count_prefix="cert_n")
    certs = [r for r in reg.table("T11d_certifications") if not r["certification"].startswith("Certification (any")]
    if certs:
        top = max(certs, key=lambda r: _f(r["count"]))
        nn = _f(top["n"])
        reg.add("cert_max_share", _f(top["count"]) / nn, "share", n=nn, denominator=DESC_DEN, basis=TEXT, source="outputs/tables/T11d_certifications.csv:max(count)/n over specific certificates",
                definition=f"share of the most frequent SPECIFIC certificate ({top['certification']})", caveat="the largest specific certificate share: 'no specific certificate appears in more than this share of ads'")
    reg.alias("cert_any_share", "cert_share__certification_any_mention")
    reg.alias("cert_any_n", "cert_n__certification_any_mention")
    reg.alias("degree_required_share", "degree_strength_share__required")
    reg.alias("degree_preferred_share", "degree_strength_share__preferred")
    reg.alias("degree_mentioned_only_share", "degree_strength_share__mentioned")
    reg.alias("degree_none_share", "degree_strength_share__none")
    de = {r["metric"]: _f(r["count"]) for r in reg.table("T11_education_summary")}
    if de.get("with_description") and "degree_or_equivalent_phrase" in de:
        reg.add("degree_or_equivalent_share", de["degree_or_equivalent_phrase"] / de["with_description"], "share", n=de["with_description"], denominator=DESC_DEN, basis=TEXT,
                source="outputs/tables/T11_education_summary.csv:degree_or_equivalent_phrase/with_description", definition="share of ads that add 'or equivalent experience' to the degree wording")
        for k in ("master_mention", "phd_mention", "bachelor_mention"):
            if k in de:
                reg.add(f"education_{k}_share", de[k] / de["with_description"], "share", n=de["with_description"], denominator=DESC_DEN, basis=TEXT,
                        source=f"outputs/tables/T11_education_summary.csv:{k}/with_description", definition=f"share of ads with: {k}")
    for fam_src in ("T12_employment_type_by_family",):
        pass
    # employer wording: business domain etc are in skills
    _ = core


def official_and_seasonality(reg: Registry) -> None:
    rows = reg.table("JB01_yearly_counts_long")
    ds = [r for r in rows if r["beruf"] == "Data Scientist (m/w)"]

    def val(bl: str, year: int):
        for r in ds:
            if r["bl"] == bl and int(r["year"]) == year:
                return _f(r["ads"])
        return None
    years = sorted({int(r["year"]) for r in ds})
    if years:
        y0, y1 = years[0], years[-1]
        for bl, tag in (("AT", "austria"), ("AT13", "vienna"), ("AT22", "styria"), ("AT31", "upper_austria")):
            for y in years:
                v = val(bl, y)
                if v is not None:
                    reg.add(f"jb_data_scientist_ads__{tag}__{y}", v, "count", source=f"outputs/tables/JB01_yearly_counts_long.csv:ads[beruf=Data Scientist (m/w), bl={bl}, year={y}]",
                            definition=f"AMS online ads in the 'Data Scientist (m/w)' occupation class, {tag}, {y}", caveat="a coarse AMS occupation class, not our titles; yearly flow, not the snapshot stock")
            for yy, lab in ((y0, "first"), (y1, "latest")):
                v = val(bl, yy)
                if v is not None:
                    reg.add(f"jb_data_scientist_ads_{lab}__{tag}", v, "count", source=f"outputs/tables/JB01_yearly_counts_long.csv:ads[Data Scientist (m/w), {bl}, {lab} year {yy}]",
                            definition=f"AMS online ads in the 'Data Scientist (m/w)' class, {tag}, {lab} year of the series ({yy})",
                            caveat="a coarse AMS occupation class, not our titles; yearly flow, not the snapshot stock")
            a, b = val(bl, y0), val(bl, y1)
            if a and b:
                reg.add(f"jb_data_scientist_change__{tag}", b / a - 1, "share", source=f"outputs/tables/JB01_yearly_counts_long.csv:ads[{y1}]/ads[{y0}]-1 [Data Scientist, {bl}]",
                        definition=f"change of the class's online ads {y0}->{y1}, {tag}", display=f"{'+' if b/a-1 >= 0 else '−'}{_num(abs(b/a-1)*100, 0)} %")
            vals = [val(bl, y) for y in years if val(bl, y) is not None]
            if vals:
                peak = max(vals)
                peak_y = [y for y in years if val(bl, y) == peak][0]
                reg.add(f"jb_data_scientist_peak__{tag}", peak, "count", source=f"outputs/tables/JB01_yearly_counts_long.csv:max(ads) [Data Scientist, {bl}]", definition=f"peak yearly ads, {tag}")
                reg.add(f"jb_data_scientist_peak_year__{tag}", peak_y, "number", source=f"outputs/tables/JB01_yearly_counts_long.csv:argmax(year) [Data Scientist, {bl}]", definition=f"year of the peak, {tag}", display=str(peak_y))
                latest = val(bl, y1)
                if latest is not None and peak:
                    reg.add(f"jb_data_scientist_change_from_peak__{tag}", latest / peak - 1, "share", source=f"outputs/tables/JB01_yearly_counts_long.csv:ads[{y1}]/max(ads)-1 [Data Scientist, {bl}]",
                            definition=f"change of the latest year vs the peak year, {tag}", display=f"{'+' if latest/peak-1 >= 0 else '−'}{_num(abs(latest/peak-1)*100, 0)} %")
        reg.add("jb_data_scientist_styria_share_of_austria", (val("AT22", y1) or 0) / val("AT", y1) if val("AT", y1) else None, "share",
                source=f"outputs/tables/JB01_yearly_counts_long.csv:ads[AT22]/ads[AT][{y1}]", n=val("AT", y1), denominator="Austria's online ads in the class, latest year",
                definition="Styria's share of the official yearly flow of 'Data Scientist' ads (JB05)", caveat="official yearly flow; compare with the snapshot share only with the basis stated", display=None)
    # JB05 for the class: related classes (latest year, change vs 2020)
    for r in reg.table("JB05_styria_vs_austria"):
        t = slug(r["beruf"])
        reg.add(f"jb_class_ads_latest__{t}", _f(r["austria"]), "count", source=f"outputs/tables/JB05_styria_vs_austria.csv:austria[beruf={r['beruf']}]", definition=f"online ads, Austria, latest year: {r['beruf']}")
        g = _f(r["growth_2020_to_latest"])
        if g is not None:
            reg.add(f"jb_class_change_vs_first__{t}", g, "share", source=f"outputs/tables/JB05_styria_vs_austria.csv:growth_2020_to_latest[beruf={r['beruf']}]", definition=f"change of online ads first -> latest year, Austria: {r['beruf']}",
                    display=f"{'+' if g >= 0 else '−'}{_num(abs(g)*100, 0)} %")
        ss = _f(r["styria_share"])
        if ss is not None:
            reg.add(f"jb_class_styria_share__{t}", ss, "share", source=f"outputs/tables/JB05_styria_vs_austria.csv:styria_share[beruf={r['beruf']}]", definition=f"Styria's share of the class's online ads, latest year: {r['beruf']}", display=fmt_value(ss, "share", "pct1"))
    # trends / competencies (outlook)
    # seasonality
    for r in reg.table("S01_seasonal_index"):
        if r.get("sample") != "full":
            continue
        reg.add(f"season_index__{slug(r['sector'])}__{r['quarter'].lower()}", _f(r["index_a_own_year_mean"]), "number", source=f"outputs/tables/S01_seasonal_index.csv:index_a_own_year_mean[sector={r['sector']}, sample=full, quarter={r['quarter']}]",
                definition=f"seasonal index (1.00 = average quarter), {r['sector_label']}, {r['quarter']}", display=fmt_value(_f(r["index_a_own_year_mean"]), "number", "f3"),
                caveat="Eurostat vacancies, whole economy aggregates, not data roles; no occupation or regional grain")
        reg.add(f"season_years_above_avg__{slug(r['sector'])}__{r['quarter'].lower()}", _f(r["years_above_average"]), "count", n=_f(r["n_years"]),
                source=f"outputs/tables/S01_seasonal_index.csv:years_above_average[sector={r['sector']}, sample=full, quarter={r['quarter']}]", definition=f"years in which {r['quarter']} was above average, {r['sector_label']}")
        reg.add(f"season_n_years__{slug(r['sector'])}", _f(r["n_years"]), "count", source=f"outputs/tables/S01_seasonal_index.csv:n_years[sector={r['sector']}]", definition=f"years in the Eurostat series, {r['sector_label']}")
    for r in reg.table("S01_seasonal_index"):
        if r.get("sample") != "full":
            continue
        tag = f"{slug(r['sector'])}__{r['quarter'].lower()}"
        for col, key, label, f in (("index_b_moving_average", "season_index_b", "seasonal index, method B (centred moving average)", "f3"), ("ci_low", "season_ci_low", "lower 95 % bound of the method-A index", "f3"),
                                   ("ci_high", "season_ci_high", "upper 95 % bound of the method-A index", "f3")):
            v = _f(r.get(col))
            if v is not None:
                reg.add(f"{key}__{tag}", v, "number", source=f"outputs/tables/S01_seasonal_index.csv:{col}[sector={r['sector']}, sample=full, quarter={r['quarter']}]",
                        definition=f"{label}, {r['sector_label']}, {r['quarter']}", display=fmt_value(v, "number", f),
                        caveat="Eurostat vacancies, whole-economy aggregates, not data roles; no occupation or regional grain")
    q4 = [_f(r[c]) for r in reg.table("S01_seasonal_index") if r.get("sample") == "full" and r.get("quarter") == "Q4" for c in ("index_a_own_year_mean",) if _f(r.get(c)) is not None]
    if q4:
        reg.add("season_q4_index_min", min(q4), "number", source="outputs/tables/S01_seasonal_index.csv:min(index_a)[quarter=Q4, sample=full]", definition="lowest Q4 seasonal index (method A) across the four aggregates", display=fmt_value(min(q4), "number", "f2"))
        reg.add("season_q4_index_max", max(q4), "number", source="outputs/tables/S01_seasonal_index.csv:max(index_a)[quarter=Q4, sample=full]", definition="highest Q4 seasonal index (method A) across the four aggregates", display=fmt_value(max(q4), "number", "f2"))
    # year-by-year modal weakest / strongest quarter (S02, method A)
    by: dict = {}
    for r in reg.table("S02_quarter_ratios_by_year"):
        if _f(r.get("ratio_own_year_mean")) is not None:
            by.setdefault((r["sector"], r["year"]), {})[r["quarter"]] = _f(r["ratio_own_year_mean"])
    sectors = sorted({s for s, _ in by})
    for sec in sectors:
        full = [q for (s, y), q in by.items() if s == sec and len(q) == 4]
        for kind, fn in (("peak", max), ("trough", min)):
            counts = {f"Q{i}": 0 for i in range(1, 5)}
            for q in full:
                counts[fn(q, key=q.get)] += 1
            for qn, c in counts.items():
                reg.add(f"season_{kind}_years__{slug(sec)}__{qn.lower()}", c, "count", n=len(full), denominator="complete years in the Eurostat series",
                        source=f"outputs/tables/S02_quarter_ratios_by_year.csv: years in which {qn} is the {'strongest' if kind == 'peak' else 'weakest'} quarter (method A)[sector={sec}]",
                        definition=f"years in which {qn} was the {'strongest' if kind == 'peak' else 'weakest'} quarter, sector {sec}", caveat="Eurostat vacancies, whole-economy aggregates, not data roles")
    q4w = [reg.items.get(f"season_trough_years__{slug(s)}__q4") for s in sectors]
    q4w = [e["value"] for e in q4w if e]
    if q4w:
        reg.add("season_q4_weakest_years_min", min(q4w), "count", source="outputs/tables/S02_quarter_ratios_by_year.csv: min over sectors of years Q4 is weakest", definition="fewest years (across sectors) in which Q4 was the weakest quarter")
        reg.add("season_q4_weakest_years_max", max(q4w), "count", source="outputs/tables/S02_quarter_ratios_by_year.csv: max over sectors of years Q4 is weakest", definition="most years (across sectors) in which Q4 was the weakest quarter")
    ny = [reg.items.get(f"season_n_years__{slug(s)}") for s in sectors]
    ny = [e["value"] for e in ny if e]
    if ny:
        reg.add("season_n_years_min", min(ny), "count", source="outputs/tables/S01_seasonal_index.csv:n_years min over sectors", definition="fewest complete years among the aggregates")
        reg.add("season_n_years_max", max(ny), "count", source="outputs/tables/S01_seasonal_index.csv:n_years max over sectors", definition="most complete years among the aggregates")
    # latest yearly mean of the market-services aggregate and the fall from its peak
    gn = [r for r in reg.table("S02_quarter_ratios_by_year") if r["sector"] == "G-N"]
    if gn:
        last_year = max(int(r["year"]) for r in gn)
        ym = next(_f(r["year_mean"]) for r in gn if int(r["year"]) == last_year)
        reg.add("eurostat_year_mean_latest__g_n", ym, "count", source=f"outputs/tables/S02_quarter_ratios_by_year.csv:year_mean[sector=G-N, year={last_year}]",
                definition=f"mean vacancies per quarter in market services (G-N), {last_year}")
        s06gn = _rowget(reg.table("S06_season_vs_cycle"), "sector", "G-N")
        peak = {"value": _f(s06gn["max_val"])} if s06gn else None
        if peak:
            reg.add("eurostat_change_from_peak__g_n", ym / peak["value"] - 1, "share", source="outputs/tables/S02_quarter_ratios_by_year.csv: latest year mean / peak year mean - 1 [G-N]",
                    definition="change of the latest yearly mean vacancies vs the peak year, market services (G-N)", display=f"−{_num(abs(ym / peak['value'] - 1) * 100, 0)} %")
    for r in reg.table("S06_season_vs_cycle"):
        t = slug(r["sector"])
        reg.add(f"season_spread_pct__{t}", _f(r["seasonal_spread_pct"]), "number", source=f"outputs/tables/S06_season_vs_cycle.csv:seasonal_spread_pct[sector={r['sector']}]", definition=f"best-vs-worst quarter spread (%), {r['sector']}")
        reg.add(f"cycle_spread_pct__{t}", _f(r["between_year_spread_pct"]), "number", source=f"outputs/tables/S06_season_vs_cycle.csv:between_year_spread_pct[sector={r['sector']}]", definition=f"best-vs-worst year spread (%), {r['sector']}")
        reg.add(f"cycle_ratio__{t}", _f(r["ratio"]), "ratio", source=f"outputs/tables/S06_season_vs_cycle.csv:ratio[sector={r['sector']}]", definition=f"cycle-to-season ratio, {r['sector']}", display=fmt_value(_f(r["ratio"]), "number", "f1"))
        reg.add(f"eurostat_year_mean_min_year__{t}", _f(r["min_year"]), "number", source=f"outputs/tables/S06_season_vs_cycle.csv:min_year[sector={r['sector']}]", definition=f"year of the lowest yearly mean vacancies, {r['sector']}", display=str(int(_f(r["min_year"]))))
        reg.add(f"eurostat_year_mean_max_year__{t}", _f(r["max_year"]), "number", source=f"outputs/tables/S06_season_vs_cycle.csv:max_year[sector={r['sector']}]", definition=f"year of the highest yearly mean vacancies, {r['sector']}", display=str(int(_f(r["max_year"]))))
        reg.add(f"eurostat_year_mean_min__{t}", _f(r["min_val"]), "count", source=f"outputs/tables/S06_season_vs_cycle.csv:min_val[sector={r['sector']}]", definition=f"lowest yearly mean vacancies per quarter, {r['sector']} ({r['min_year']})")
        reg.add(f"eurostat_year_mean_max__{t}", _f(r["max_val"]), "count", source=f"outputs/tables/S06_season_vs_cycle.csv:max_val[sector={r['sector']}]", definition=f"highest yearly mean vacancies per quarter, {r['sector']} ({r['max_year']})")


    s06 = reg.table("S06_season_vs_cycle")
    for col, key, label in (("seasonal_spread_pct", "season_spread_pct", "best-vs-worst quarter spread (%)"), ("between_year_spread_pct", "cycle_spread_pct", "best-vs-worst year spread (%)"),
                            ("ratio", "cycle_ratio", "cycle-to-season ratio (x)")):
        vals = [_f(r[col]) for r in s06 if _f(r[col]) is not None]
        if vals:
            for fn, nm in ((min, "min"), (max, "max")):
                v = fn(vals)
                reg.add(f"{key}_{nm}", v, "number", source=f"outputs/tables/S06_season_vs_cycle.csv:{nm}({col}) over the four aggregates", definition=f"{nm} of the {label} across aggregates",
                        display=fmt_value(v, "number", "int0"))

def quality(reg: Registry) -> None:
    for r in reg.table("Q03c_precision_summary"):
        t = slug(r["family"])
        for col, key in (("precision_after_strict", "precision_strict"), ("precision_after_lenient", "precision_lenient"), ("precision_before_strict", "precision_before_strict"),
                         ("precision_before_lenient", "precision_before_lenient")):
            reg.add(f"title_{key}__{t}", _f(r[col]), "share", n=_f(r["n_sampled"]), denominator=f"hand-labelled titles sampled in the family",
                    source=f"outputs/tables/Q03c_precision_summary.csv:{col}[family={r['family']}]", definition=f"title-classification {key.replace('_', ' ')} precision, {r['family']}", caveat="recall is not measured")
    for r in reg.table("Q03c_precision_summary"):
        t2 = slug(r["family"])
        for col, key, label in (("n_sampled", "title_audit_n", "titles sampled"), ("FP_removed", "title_fp_removed", "false positives removed by the D-012 revision"),
                                ("TP_lost", "title_tp_lost", "true positives lost by the D-012 revision")):
            if _f(r.get(col)) is not None:
                reg.add(f"{key}__{t2}", _f(r[col]), "count", source=f"outputs/tables/Q03c_precision_summary.csv:{col}[family={r['family']}]", definition=f"title audit, family {r['family']}: {label}")
    for r in reg.table("Q01_missingness"):
        if r.get("set") == "core" and _f(r.get("missing_share")) is not None:
            reg.add(f"present_share__core__{slug(r['source'])}__{slug(r['field'])}", 1 - _f(r["missing_share"]), "share", n=_f(r["n"]), denominator=f"core rows of source {r['source']}",
                    source=f"outputs/tables/Q01_missingness.csv:1-missing_share[set=core, source={r['source']}, field={r['field']}]", definition=f"share of core rows of source {r['source']} with a value in field {r['field']}")
    allrow = _rowget(reg.table("Q03c_precision_summary"), "family", "ALL")
    if allrow:
        n_s = _f(allrow["n_sampled"])
        reg.add("title_audit_sample_n", n_s, "count", source="outputs/tables/Q03c_precision_summary.csv:n_sampled[family=ALL]", definition="hand-labelled titles in the precision audit")
        reg.add("title_audit_kept_n", _f(allrow["n_kept_after"]), "count", source="outputs/tables/Q03c_precision_summary.csv:n_kept_after[family=ALL]", definition="audited titles kept in a core family after the D-012 rule revision")
        for col, key, label in (("precision_after_strict", "title_precision_strict_after", "strict precision after the D-012 rule revision"),
                                ("precision_after_lenient", "title_precision_lenient_after", "lenient precision (borderline counted as correct) after the D-012 rule revision"),
                                ("precision_before_strict", "title_precision_strict_before", "strict precision before the D-012 revision"),
                                ("precision_before_lenient", "title_precision_lenient_before", "lenient precision before the D-012 revision")):
            reg.add(key, _f(allrow[col]), "share", n=n_s, denominator="hand-labelled titles (25 per family, fewer where the family is small)",
                    source=f"outputs/tables/Q03c_precision_summary.csv:{col}[family=ALL]", definition=f"title-classification {label}", caveat="recall is not measured")


def layer2_3(reg: Registry) -> None:
    ss = reg.json("supply_summary")
    pops = ss.get("populations") or {}
    for k, label in (("P_all", "Austrian-located public GitHub accounts, all frames"), ("P_data", "accounts with a data signal (bio-declared or repo-evidenced)"),
                     ("P_T1", "accounts whose bio declares a core data role (the only rows with a family)")):
        reg.add(f"supply_{k.lower()}_n", pops.get(k), "count", source=f"outputs/supply_summary.json:populations.{k}", definition=label,
                caveat="a public-profile sample, not a census of the workforce")
    for t in reg.table("C01_candidate_source_coverage"):
        f = t["frame"]
        for col, key in (("accounts", "accounts"), ("austrian_location", "austrian_location"), ("data_signal", "data_signal"), ("bio_declared", "bio_declared")):
            reg.add(f"supply_frame_{f.lower()}_{key}", _f(t[col]), "count", source=f"outputs/tables/C01_candidate_source_coverage.csv:{col}[frame={f}]", definition=f"frame {f}: {key}")
    tot = lambda col: sum(_f(r[col]) for r in reg.table("C01_candidate_source_coverage"))  # noqa: E731
    for col, key, label in (("n_search_rows", "search_rows", "GitHub search rows"), ("n_repos_listed", "repos_listed", "repositories listed"), ("n_readmes_fetched", "readmes_fetched", "READMEs and file trees fetched"),
                            ("n_data_repos", "data_repos", "data repositories")):
        rows = reg.table("C01_candidate_source_coverage")
        if rows:
            reg.add(f"supply_{key}_n", _f(rows[0][col]), "count", source=f"outputs/tables/C01_candidate_source_coverage.csv:{col}", definition=label)
    sq = reg.table("SQ01_search_coverage_and_caps")
    if sq:
        for col, key, label in (("queries_run", "queries_run", "user searches run"), ("profiles_fetched", "profiles_fetched", "profiles fetched"), ("organisations_or_bots_dropped", "orgs_dropped", "organisation/bot logins dropped")):
            reg.add(f"supply_{key}_n", _f(sq[0][col]), "count", source=f"outputs/tables/SQ01_search_coverage_and_caps.csv:{col}", definition=label)
    mf = reg.json("supply_summary")
    tiers = mf.get("tiers") or {}
    # tiers table
    share_table(reg, "C01a_data_tier_distribution", "data_tier", "supply_tier_share", unit_label="data tier of the account", denominator="P_all", count_prefix="supply_tier_n")
    # families (P_T1)
    share_table(reg, "C04_role_family_distribution", "role_family", "supply_family_share", unit_label="family of the bio-declared role", denominator="P_T1 (bio-declared)", count_prefix="supply_family_n",
                caveat="bio-declared, not employment; supply share is not a workforce share")
    wide_table(reg, "C04_role_family_distribution", "role_family", "supply_family", {"styria": ("styria_n", "count"), "graz_area": ("graz_area_n", "count"), "vienna": ("vienna_n", "count"), "students": ("students_n", "count")},
               unit_label="bio-declared accounts by region (location-resolved)", basis="location-resolved (D-027)", caveat="Styria is the only complete frame; Vienna is a lower bound")
    share_table(reg, "C03_normalized_title_distribution", "normalized_title", "supply_title_share", unit_label="normalised bio title", denominator="P_T1", count_prefix="supply_title_n")
    share_table(reg, "C05_geography_by_state", "state", "supply_state_share", unit_label="location-resolved accounts by state", denominator="P_all", count_prefix="supply_state_n",
                caveat="frames are not proportional: compare within-frame shares only", filt=lambda r: r.get("population") == "P_all")
    for r in reg.table("C05a_geo_summary"):
        p = slug(r["population"])
        for col in ("vienna", "styria", "graz_area", "graz_city", "austria_only", "hireable_flag"):
            reg.add(f"supply_geo__{p}__{col}", _f(r[col]), "count", n=_f(r["n"]), source=f"outputs/tables/C05a_geo_summary.csv:{col}[population={r['population']}]", basis="location-resolved (D-027)",
                    definition=f"{r['population']} accounts: {col}", caveat="Styria complete; Vienna a lower bound")
        reg.add(f"supply_geo__{p}__hireable_share", _f(r["hireable_share"]), "share", n=_f(r["n"]), source=f"outputs/tables/C05a_geo_summary.csv:hireable_share[population={r['population']}]", definition=f"{r['population']}: share with the hireable flag")
    c5c = reg.table("C05c_styria_complete_frame")
    if c5c:
        r = c5c[0]
        for col in ("n", "T1_bio_declared", "T2_repo_evidenced", "T3_weak", "graz_area", "hireable"):
            reg.add(f"supply_styria_frame_b__{slug(col)}", _f(r[col]), "count", source=f"outputs/tables/C05c_styria_complete_frame.csv:{col}", basis="frame-B complete-Styria subset (D-027)", definition=f"frame-B complete-Styria subset: {col}")
        reg.add("supply_styria_frame_b__data_signal_n", (_f(r["T1_bio_declared"]) or 0) + (_f(r["T2_repo_evidenced"]) or 0), "count", source="outputs/tables/C05c_styria_complete_frame.csv:T1+T2", basis="frame-B complete-Styria subset (D-027)",
                definition="frame-B complete-Styria subset: data-signal accounts (T1 + T2)")
        reg.add("supply_styria_frame_b__active_12m_share", _f(r["active_12m_share"]), "share", source="outputs/tables/C05c_styria_complete_frame.csv:active_12m_share", basis="frame-B complete-Styria subset (D-027)", definition="share active in the last 12 months")
    share_table(reg, "C06_seniority_distribution", "seniority", "supply_seniority_share", unit_label="seniority wording in bios (P_T1)", denominator="P_T1", count_prefix="supply_seniority_n",
                filt=lambda r: r.get("population", "P_T1") == "P_T1")
    share_table(reg, "C07_language_presentation", ("population", "signal", "value"), "supply_language_share", unit_label="language presentation of bios/READMEs (what candidates WRITE, not proficiency)",
                denominator="population in the row", count_prefix="supply_language_n", caveat="language proficiency is not observable on GitHub")
    share_table(reg, "C08_education_levels", ("population", "education_level"), "supply_education_share", unit_label="education wording in bios/READMEs", denominator="population in the row",
                count_prefix="supply_education_n", caveat="absence of wording is not absence of a degree")
    # technologies (C10): any / project-demonstrated
    for r in reg.table("C10_technologies_evidence"):
        t = slug(r["skill"])
        nn = _f(r["n"])
        src = f"outputs/tables/C10_technologies_evidence.csv:%s[skill={r['skill']}]"
        reg.add(f"supply_tech_any_share__{t}", _f(r["any_evidence"]) / nn, "share", n=nn, denominator="P_data", source=src % "any_evidence/n", definition=f"share of data-signal accounts with any evidence of {r['skill']}",
                caveat="a missing public trace is not a missing skill (Power BI/Excel/SAP/SQL leave little code)")
        reg.add(f"supply_tech_project_share__{t}", _f(r["project_demonstrated"]) / nn, "share", n=nn, denominator="P_data", source=src % "project_demonstrated/n",
                definition=f"share of data-signal accounts with {r['skill']} evidence in a documented, non-educational project")
    # DS tables
    wide_table(reg, "DS01_demand_supply_role_families", "category", "ds_family", {"relative_representation": ("relative_representation", "ratio"), "candidate_density_T1_per_posting": ("per_posting", "number"),
                                                                              "supply_count": ("supply_n", "count"), "demand_count": ("demand_n", "count"), "density_styria": ("per_posting_styria", "number")},
               unit_label="demand x supply by family", caveat="relative representation = supply share / demand share; not candidates per posting; different universes",
               id_values=None)
    # DS05 geography
    for r in reg.table("DS05_demand_supply_geography"):
        if r.get("dimension") != "state":
            continue
        t = slug(r["category"])
        for col, key, unit in (("supply_count", "supply_data_n", "count"), ("supply_T1", "supply_t1_n", "count"), ("candidate_density_data_per_posting", "data_per_posting", "number"),
                               ("candidate_density_T1_per_posting", "declared_per_posting", "number"), ("supply_all_accounts", "supply_all_n", "count")):
            v = _f(r[col])
            reg.add(f"ds_geo__{t}__{key}", v, unit, source=f"outputs/tables/DS05_demand_supply_geography.csv:{col}[category={r['category']}]", basis=PRIMARY + " (demand); location-resolved (supply)",
                    definition=f"{r['category']}: {key}", caveat="supply shares across states are not comparable (frames differ); densities are comparable only for Styria (complete)",
                    display=None if unit == "count" else fmt_value(v, "number", "f2"))
    for r in reg.table("DS13_styria_graz_demand_supply"):
        v = _f(r["value"])
        reg.add(f"ds13__{slug(r['measure'])[:60]}", v, "count" if v is not None and v == int(v) else "number", source="outputs/tables/DS13_styria_graz_demand_supply.csv:value[measure=" + r["measure"][:60] + "]",
                definition=r["measure"], basis="see measure label (any-site / primary / location-resolved / frame-B subset)", display=None if v is not None and v == int(v) else fmt_value(v, "number", "f2")) if v is not None else None
    # DS03 skill demand vs supply (relative representation) and DS10 capability buckets
    for r in reg.table("DS03_demand_supply_skills"):
        t = slug(r["category"])
        reg.add(f"ds_skill_supply_share__{t}", _f(r["supply_share"]), "share", n=_f(r["supply_n"]), denominator="P_data", source=f"outputs/tables/DS03_demand_supply_skills.csv:supply_share[category={r['category']}]",
                definition=f"{r['category']}: any-evidence share of data-signal accounts")
        reg.add(f"ds_skill_project_share__{t}", _f(r["project_share"]), "share", n=_f(r["project_n"]), denominator="P_data", source=f"outputs/tables/DS03_demand_supply_skills.csv:project_share[category={r['category']}]",
                definition=f"{r['category']}: project-demonstrated share of data-signal accounts")
    for r in reg.table("DS10_demand_supply_capability_evidence"):
        t = slug(r["category"])
        reg.add(f"cap_demand_share__{t}", _f(r["demand_share"]), "share", n=_f(r["demand_n"]), denominator=DESC_DEN, source=f"outputs/tables/DS10_demand_supply_capability_evidence.csv:demand_share[category={r['category']}]",
                definition=f"capability bucket {r['category']}: share of ads (union of member skills)", caveat="a bucket is a union of member skills, so shares exceed the single-skill figures")
        reg.add(f"cap_supply_any_share__{t}", _f(r["supply_any_share"]), "share", n=_f(r["supply_n"]), denominator="P_data", source=f"outputs/tables/DS10_demand_supply_capability_evidence.csv:supply_any_share[category={r['category']}]",
                definition=f"capability bucket {r['category']}: any-evidence share of data-signal accounts")
        reg.add(f"cap_supply_project_share__{t}", _f(r["supply_project_share"]), "share", n=_f(r["n_substantive_projects"]), denominator="substantive projects / P_data (see DS10 note)",
                source=f"outputs/tables/DS10_demand_supply_capability_evidence.csv:supply_project_share[category={r['category']}]", definition=f"capability bucket {r['category']}: project-demonstrated share")
    # README patterns, formats, projects
    share_table(reg, "C19_readme_patterns", ("population", "feature"), "readme_share", unit_label="README feature", denominator="population in the row (documented projects / projects)", count_prefix="readme_n")
    share_table(reg, "C17_project_formats", "format", "format_share", unit_label="project format", denominator="projects", count_prefix="format_n")
    share_table(reg, "C14_github_evidence", ("population", "signal"), "github_evidence_share", unit_label="GitHub evidence signal", denominator="population in the row", count_prefix="github_evidence_n")
    share_table(reg, "C09_certifications", ("population", "certification"), "supply_cert_share", unit_label="certification wording in bios/READMEs", denominator="population in the row", count_prefix="supply_cert_n")
    # clusters
    for r in reg.table("C23_positioning_clusters"):
        reg.add(f"supply_cluster_size__{r['cluster']}", _f(r["size"]), "count", source=f"outputs/tables/C23_positioning_clusters.csv:size[cluster={r['cluster']}]", definition=f"positioning cluster {r['cluster']} size", caveat="descriptive archetypes, not professions")


def extras(reg: Registry) -> None:
    """Employers, entry tracks, hunter supplement, decision matrix, adjacent demand, official outlook."""
    for r in reg.table("T04_employers"):
        reg.add(f"employer_postings__{slug(r['company_norm'])}", _f(r["postings"]), "count", source=f"outputs/tables/T04_employers.csv:postings[company_norm={r['company_norm']}]",
                definition=f"core postings of {r['example_company']} (all states)")
    for r in reg.table("T04d_dual_track_employers"):
        t = slug(r["company_norm"])
        reg.add(f"dual_track_intern_n__{t}", _f(r["intern_student_postings"]), "count", source=f"outputs/tables/T04d_dual_track_employers.csv:intern_student_postings[{r['company_norm']}]",
                definition=f"intern/student ads of {r['example_company']}")
        reg.add(f"dual_track_junior_n__{t}", _f(r["trainee_junior_postings"]), "count", source=f"outputs/tables/T04d_dual_track_employers.csv:trainee_junior_postings[{r['company_norm']}]",
                definition=f"junior/trainee ads of {r['example_company']}")
    for r in reg.table("T04d_dual_track_summary"):
        reg.add(f"entry_track__{slug(r['metric'])}", _f(r["value"]), "count", source=f"outputs/tables/T04d_dual_track_summary.csv:value[metric={r['metric']}]",
                definition=f"entry-track summary: {r['metric']}")
    share_table(reg, "T17c_family_mix_by_entry_track", ("entry_track", "role_family"), "entry_family_share", unit_label="family mix within an entry-track group",
                denominator="titles in the entry-track group", caveat="small entry-track denominators (see entry_track_denominators_vs_30): directional only", count_prefix="entry_family_n")
    ent = reg.table("T17_skills_by_entry_track")
    for tr in ("intern_student", "trainee_junior", "rest"):
        rows = [r for r in ent if r["entry_track"] == tr]
        if rows:
            reg.add(f"entry_track_desc_n__{tr}", _f(rows[0]["n"]), "count", source=f"outputs/tables/T17_skills_by_entry_track.csv:n[entry_track={tr}]",
                    definition=f"ads with a description in entry track {tr}")
    sh = reg.table("T08_seniority_overall")
    for r in sh:
        if r["seniority"] in ("intern_student", "trainee_junior"):
            reg.add(f"entry_track_titles_n__{r['seniority']}", _f(r["count"]), "count", source=f"outputs/tables/T08_seniority_overall.csv:count[seniority={r['seniority']}]",
                    definition=f"core titles with seniority wording {r['seniority']}")
    ms_core = (reg.json("market_summary").get("counts") or {}).get("core_canonical")
    if sh and ms_core:
        rest = ms_core - sum(_f(r["count"]) for r in sh if r["seniority"] in ("intern_student", "trainee_junior"))
        reg.add("entry_track_titles_n__rest", rest, "count", source="outputs/market_summary.json:core_canonical minus intern/junior titles",
                definition="core titles that are neither intern nor junior")
    # hunter supplement T19 (a separate universe, never merged)
    for r in reg.table("T19_supplement_status")[:1]:
        for col, label in (("core_data_role_rows", "core data-role titles"), ("core_with_description", "core titles with JD text"), ("arbeitnow_austria_rows", "Arbeitnow Austria rows"),
                           ("radar_austria_rows", "hunter Austria rows"), ("radar_db_rows", "hunter DB rows")):
            reg.add(f"t19__{col}", _f(r[col]), "count", source=f"outputs/tables/T19_supplement_status.csv:{col}", definition=f"T19 hunter supplement: {label}",
                    caveat="a separate universe from the core snapshot; title-query mix, not a census; never merged")
        reg.add("t19__collected_date", r["collected_date"], "date", source="outputs/tables/T19_supplement_status.csv:collected_date", definition="date of the T19 hunter supplement")
    share_table(reg, "T19_supplement_families", "role_family", "t19_family_share", unit_label="T19 hunter supplement: family share of core titles",
                denominator="T19 core titles", count_prefix="t19_family_n", caveat="a separate universe: do not compare with the core census")
    share_table(reg, "T19_supplement_states", "state", "t19_state_share", unit_label="T19 hunter supplement: state share of core titles",
                denominator="T19 core titles", count_prefix="t19_state_n", caveat="a separate universe: do not compare with the core census")
    share_table(reg, "T19_supplement_sources", "source", "t19_source_share", unit_label="T19 hunter supplement: source share",
                denominator="T19 core titles", count_prefix="t19_source_n")
    # decision matrix
    for r in reg.table("D01_decision_matrix"):
        t = slug(r["role_family"])
        for col, key in (("V5_profile_overlap_top15", "profile_overlap_n_of15"), ("V6_structural_gap_top15", "structural_gap_n_of15")):
            v = _f(r.get(col))
            if v is not None:
                what = ("number of the family's 15 most-mentioned skills that are in the profile's self-declared have/developing lists" if key.startswith("profile")
                        else "number of the family's 15 most-mentioned skills that are structural gaps for the profile")
                reg.add(f"{key}__{t}", round(v * 15), "count", n=15, denominator="the family's 15 most-mentioned skills",
                        source=f"outputs/tables/D01_decision_matrix.csv:{col}*15[role_family={r['role_family']}]", definition=what,
                        caveat="an ordinal indicator from self-declared lists, not a fit probability")
    for r in reg.table("D02_sensitivity"):
        t = slug(r["role_family"])
        for col in ("rank_default", "rank_geography_first", "rank_language_first", "rank_equal"):
            reg.add(f"decision_{col}__{t}", _f(r[col]), "number", source=f"outputs/tables/D02_sensitivity.csv:{col}[role_family={r['role_family']}]",
                    definition=f"decision-matrix rank ({col}) of {r['role_family']}", display=str(int(_f(r[col]))),
                    caveat="the ranking measures market size, English openness and advertised floors, not ease of entry")
    # adjacent demand (AMS feed sweep)
    for r in reg.table("T16_adjacent_demand_by_region"):
        rg, tool = slug(r["region"]), slug(r["tool"])
        reg.add(f"adjacent_mentions__{rg}__{tool}", _f(r["postings_mentioning"]), "count",
                source=f"outputs/tables/T16_adjacent_demand_by_region.csv:postings_mentioning[{r['region']}, {r['tool']}]",
                definition=f"AMS-feed ads in {r['region']} that mention {r['tool']} (full-text sweep, not by title)", caveat="AMS feed only; three regions")
        reg.add(f"adjacent_non_data_share__{rg}__{tool}", _f(r["share_non_data_title"]), "share", n=_f(r["postings_mentioning"]),
                source=f"outputs/tables/T16_adjacent_demand_by_region.csv:share_non_data_title[{r['region']}, {r['tool']}]",
                definition=f"share of {r['tool']} mentions in {r['region']} that sit under non-data titles")
        reg.add(f"adjacent_sweep_n__{rg}", _f(r["sweep_postings_region"]), "count", source=f"outputs/tables/T16_adjacent_demand_by_region.csv:sweep_postings_region[{r['region']}]",
                definition=f"postings retrieved by the full-text sweep in {r['region']}")

    fl = {r["metric"]: _f(r["count"]) for r in reg.table("T12a_flags")}
    if fl.get("core_postings"):
        for k, label in (("internship_or_student", "internship / student-job wording"), ("temporary_or_contract", "temporary / contract wording")):
            if k in fl:
                reg.add(f"flag_{k}_n", fl[k], "count", n=fl["core_postings"], denominator=CORE_DEN, source=f"outputs/tables/T12a_flags.csv:count[metric={k}]", definition=f"core postings with {label}")
                reg.add(f"flag_{k}_share", fl[k] / fl["core_postings"], "share", n=fl["core_postings"], denominator=CORE_DEN, source=f"outputs/tables/T12a_flags.csv:count[metric={k}]/core_postings",
                        definition=f"share of core postings with {label}")
    first = (reg.json("market_summary").get("collected_at_range") or {}).get("min", "")[:7]
    months = reg.table("T13a_posted_by_month_source")
    core_n = (reg.json("market_summary").get("counts") or {}).get("core_canonical")
    if first and months and core_n:
        in_month = sum(_f(r["count"]) for r in months if r["posted_date"] == first)
        reg.add("snapshot_first_published_in_collection_month_share", in_month / core_n, "share", n=core_n, denominator=CORE_DEN,
                source="outputs/tables/T13a_posted_by_month_source.csv:count[posted_date=collection month]/core_canonical",
                definition="share of core ads first published in the month of the collection (survival decay, not seasonality)")
    # official outlook and competencies
    jb3 = [r for r in reg.table("JB03_trends") if r["beruf"] == "Data Scientist (m/w)"]
    if jb3:
        reg.add("jb_outlook_positive_regions_n", sum(1 for r in jb3 if r["trend_3y"] == "positiv"), "count", n=len(jb3), denominator="Bundesländer + Austria rows",
                source="outputs/tables/JB03_trends.csv:trend_3y='positiv' [Data Scientist (m/w)]",
                definition="regions (incl. Austria) with a 'positiv' AMS outlook for the Data Scientist class")
        reg.add("jb_outlook_regions_n", len(jb3), "count", source="outputs/tables/JB03_trends.csv: rows [Data Scientist (m/w)]",
                definition="regions (incl. Austria) with an AMS outlook for the Data Scientist class")
        reg.add("jb_outlook_window", jb3[0]["trend_window"], "text", source="outputs/tables/JB03_trends.csv:trend_window", definition="AMS outlook window")
    for r in reg.table("JB04_competencies"):
        if r["beruf"] == "Data Scientist (m/w)" and r["kind"] == "growing" and _f(r["growth_pp"]) is not None:
            reg.add(f"jb_competency_growth_pp__{slug(r['competency'])}", _f(r["growth_pp"]), "pp",
                    source=f"outputs/tables/JB04_competencies.csv:growth_pp[{r['competency']}]",
                    definition=f"growth in percentage points of the share of Data Scientist ads naming: {r['competency']}",
                    display=f"+{fmt_value(_f(r['growth_pp']), 'number', 'f1')}")
    # text-basis n of the two Styria groups
    seen = {}
    for r in reg.table("T05_skills_all_tech_by_styria"):
        seen[r["styria_flag"]] = _f(r["n"])
    if "Styria" in seen:
        reg.add("styria_n_text_basis", seen["Styria"], "count", source="outputs/tables/T05_skills_all_tech_by_styria.csv:n[styria_flag=Styria]", basis=ANYSITE,
                definition="Styrian core postings with a description (denominator of Styrian text-derived shares)")
    if "Rest of Austria" in seen:
        reg.add("rest_n_text_basis", seen["Rest of Austria"], "count", source="outputs/tables/T05_skills_all_tech_by_styria.csv:n[styria_flag=Rest of Austria]", basis=ANYSITE,
                definition="non-Styrian core postings with a description")


def _dig(obj, path: str):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def supply_json(reg: Registry) -> None:
    """Layer 2/3 counts that live in outputs/*.json (collection coverage, project populations, Stack Overflow, precision audits)."""
    flat = (
        # (json, path, key, unit, definition, caveat)
        ("supply_data_quality", "search.queries_run", "supply_queries_run_n", "count", "GitHub user searches run", ""),
        ("supply_data_quality", "search.profiles_fetched", "supply_profiles_fetched_n", "count", "GitHub profiles fetched", ""),
        ("supply_data_quality", "search.search_rows", "supply_search_rows_n", "count", "GitHub search result rows", ""),
        ("supply_data_quality", "search.frame_C_retrieved", "supply_frame_c_retrieved_n", "count", "frame-C accounts retrieved (capped per created-year slice)", ""),
        ("supply_data_quality", "search.frame_C_total_available", "supply_frame_c_available_n", "count", "frame-C accounts available at the search endpoint", ""),
        ("supply_data_quality", "geography.n", "supply_accounts_n", "count", "GitHub accounts after dropping organisation/bot logins", ""),
        ("supply_data_quality", "geography.austrian_signal", "supply_austrian_signal_n", "count", "accounts with an Austrian location signal (= P_all)", ""),
        ("supply_data_quality", "geography.dropped_no_austrian_signal", "supply_dropped_no_austrian_n", "count", "accounts dropped for lack of an Austrian location signal", ""),
        ("supply_data_quality", "projects.data_repos", "supply_data_repos_n", "count", "data repositories listed", ""),
        ("supply_data_quality", "projects.readme_fetched", "supply_data_repo_readmes_fetched_n", "count", "READMEs fetched for data repositories", ""),
        ("supply_data_quality", "projects.documented", "supply_documented_repos_n", "count", "documented repositories (README >= 1k) incl. non-project", ""),
        ("supply_projects", "populations.projects", "supply_projects_n", "count", "projects (owned non-fork data repository with README >= 300 chars, >= 1 star or a description)", "repositories are not projects"),
        ("supply_projects", "populations.documented_projects", "supply_documented_projects_n", "count", "documented projects (README >= 1k)", ""),
        ("supply_projects", "populations.substantive_projects", "supply_substantive_projects_n", "count", "substantive projects (documented and not course/tutorial work)", ""),
        ("supply_projects", "populations.data_repos", "supply_data_repos_p_data_n", "count", "data repositories of P_data accounts", ""),
        ("supply_official", "stackoverflow_2025.rows_austria", "so_at_respondents_n", "count", "Stack Overflow Developer Survey 2025: Austrian respondents", "survey sample, not a census"),
        ("supply_official", "stackoverflow_2025.austria_data_role_respondents", "so_at_data_role_n", "count", "Stack Overflow 2025: Austrian respondents in a data role", "very small n"),
        ("supply_official", "stackoverflow_2025.professional_developers_austria", "so_at_professional_developers_n", "count", "Stack Overflow 2025: Austrian professional developers", ""),
        ("supply_summary", "concentration.raw_titles.distinct", "supply_raw_bio_titles_distinct_n", "count", "distinct raw bio titles among bio-declared accounts", ""),
        ("supply_summary", "concentration.raw_titles.total", "supply_raw_bio_titles_total_n", "count", "bio-declared accounts with a raw bio title", ""),
        ("supply_summary", "concentration.normalized_titles.distinct", "supply_normalized_titles_distinct_n", "count", "distinct normalised bio titles", ""),
        ("supply_summary", "transitions.explicit_transition_wording", "supply_transition_wording_n", "count", "P_T1 bios with explicit career-transition wording", "public GitHub does not narrate career changes"),
        ("supply_summary", "transitions.any_prior_domain_named", "supply_prior_domain_named_n", "count", "P_T1 bios naming any prior domain", ""),
    )
    for name, path, key, unit, definition, caveat in flat:
        v = _dig(reg.json(name), path)
        if isinstance(v, (int, float)):
            reg.add(key, v, unit, source=f"outputs/{name}.json:{path}", definition=definition, caveat=caveat)
    for name, path, key, definition in (
            ("supply_summary", "concentration.raw_titles.top1_share", "supply_raw_bio_title_top1_share", "share of the most common raw bio title among bio-declared accounts"),
            ("supply_summary", "concentration.normalized_titles.top1_share", "supply_normalized_title_top1_share", "share of the most common normalised bio title"),
            ("supply_summary", "transitions.share_explicit", "supply_transition_wording_share", "share of P_T1 bios with explicit career-transition wording"),
            ("supply_summary", "transitions.share_prior_domain", "supply_prior_domain_named_share", "share of P_T1 bios naming any prior domain"),
            ("supply_official", "stackoverflow_2025.austria_data_role_share", "so_at_data_role_share", "share of Stack Overflow 2025 Austrian respondents in a data role")):
        v = _dig(reg.json(name), path)
        if isinstance(v, (int, float)):
            reg.add(key, v, "share", source=f"outputs/{name}.json:{path}", definition=definition)

    for key, start, unit in (("supply_styria_accounts_location_resolved_n", "Styrian GitHub accounts, location-resolved", "count"),
                             ("supply_styria_data_signal_location_resolved_n", "  of which data-signal (T1+T2), location-resolved", "count"),
                             ("supply_styria_t1_location_resolved_n", "  of which bio-declared data role (T1), location-resolved", "count"),
                             ("supply_styria_t1_graz_area_location_resolved_n", "  of which T1 in Graz area, location-resolved", "count"),
                             ("supply_styria_frame_b_accounts_n", "Styrian GitHub accounts with", "count"),
                             ("supply_styria_frame_b_data_signal_n", "  of which data-signal (T1+T2), frame-B subset", "count"),
                             ("supply_styria_frame_b_t1_n", "  of which bio-declared data role (T1), frame-B subset", "count"),
                             ("supply_styria_frame_b_t1_graz_area_n", "  of which T1 in Graz area, frame-B subset", "count"),
                             ("supply_styria_frame_b_t1_students_n", "  T1 students, frame-B subset", "count"),
                             ("supply_styria_frame_b_t1_documented_n", "  T1 with", "count"),
                             ("supply_styria_frame_b_active_12m_n", "  data-signal with any push in 12 months, frame-B subset", "count"),
                             ("supply_styria_frame_b_english_bio_n", "  data-signal with English bio, frame-B subset", "count"),
                             ("supply_styria_frame_b_hireable_n", "  data-signal with hireable flag, frame-B subset", "count")):
        for r in reg.table("DS13_styria_graz_demand_supply"):
            if r["measure"].startswith(start) and _f(r["value"]) is not None:
                reg.add(key, _f(r["value"]), unit, source=f"outputs/tables/DS13_styria_graz_demand_supply.csv:value[measure={r['measure'].strip()[:70]}]", definition=r["measure"].strip(),
                        basis="location-resolved (canonical)" if "location-resolved" in r["measure"] else "frame-B complete-Styria subset (D-027)", caveat="Styria is the only complete GitHub frame")
                break
    for r in reg.table("DS01_demand_supply_role_families"):
        if _f(r.get("demand_vienna")) and _f(r.get("supply_vienna_T1")) is not None:
            reg.add(f"ds_family__{slug(r['category'])}__per_posting_vienna", _f(r["supply_vienna_T1"]) / _f(r["demand_vienna"]), "number",
                    source=f"outputs/tables/DS01_demand_supply_role_families.csv:supply_vienna_T1/demand_vienna[category={r['category']}]",
                    definition=f"bio-declared candidates per core posting in Vienna (a lower bound: Vienna supply is a sample), family {r['category']}", display=fmt_value(_f(r["supply_vienna_T1"]) / _f(r["demand_vienna"]), "number", "f2"),
                    caveat="Vienna supply is a lower bound (sampled frames); an order of magnitude, not a ratio of people to jobs")
    five = [reg.items.get(f"ds_family__{f}__relative_representation") for f in ("data_engineering", "bi", "business_analysis", "data_governance", "marketing_analytics")]
    if all(five):
        vals5 = [u["value"] for u in five]
        reg.add("ds_family_underrepresented5_min", min(vals5), "ratio", source="outputs/tables/DS01_demand_supply_role_families.csv:relative_representation (engineering, BI, business analysis, governance, marketing analytics)",
                definition="smallest relative representation among the five under-represented families", display=fmt_value(min(vals5), "number", "f2"))
        reg.add("ds_family_underrepresented5_max", max(vals5), "ratio", source="outputs/tables/DS01_demand_supply_role_families.csv:relative_representation (engineering, BI, business analysis, governance, marketing analytics)",
                definition="largest relative representation among the five under-represented families", display=fmt_value(max(vals5), "number", "f2"))
    d10 = reg.table("DS10_demand_supply_capability_evidence")
    if d10:
        reg.add("cap_threshold_demand", _f(d10[0]["threshold_demand"]), "share", source="outputs/tables/DS10_demand_supply_capability_evidence.csv:threshold_demand", definition="DS10 quadrant threshold on the demand axis (median of demand shares)")
        reg.add("cap_threshold_supply", _f(d10[0]["threshold_supply"]), "share", source="outputs/tables/DS10_demand_supply_capability_evidence.csv:threshold_supply", definition="DS10 quadrant threshold on the supply axis (median of project-demonstrated shares)")
    for key, start, label in (("supply_t1_per_posting_styria_flag", "T1 candidates (location-resolved) per core posting", "bio-declared candidates per core posting listing a Styrian site"),
                              ("supply_data_signal_per_posting_styria_flag", "data-signal candidates (location-resolved) per core posting", "data-signal candidates per core posting listing a Styrian site")):
        for r in reg.table("DS13_styria_graz_demand_supply"):
            if r["measure"].startswith(start) and _f(r["value"]) is not None:
                reg.add(key, _f(r["value"]), "number", source="outputs/tables/DS13_styria_graz_demand_supply.csv:value", definition=label, basis=ANYSITE + " (demand) / location-resolved (supply)",
                        display=fmt_value(_f(r["value"]), "number", "f2"), caveat="supply / demand are different universes; an order of magnitude, not a ratio of people to jobs")
                break
    under = [reg.items.get(f"ds_family__{f}__relative_representation") for f in ("data_engineering", "bi", "business_analysis", "data_governance")]
    if all(under):
        vals = [u["value"] for u in under]
        reg.add("ds_family_underrepresented_min", min(vals), "ratio", source="outputs/tables/DS01_demand_supply_role_families.csv:relative_representation (engineering, BI, business analysis, governance)",
                definition="smallest relative representation among data engineering, BI, business analysis and governance", display=fmt_value(min(vals), "number", "f1"))
        reg.add("ds_family_underrepresented_max", max(vals), "ratio", source="outputs/tables/DS01_demand_supply_role_families.csv:relative_representation (engineering, BI, business analysis, governance)",
                definition="largest relative representation among data engineering, BI, business analysis and governance", display=fmt_value(max(vals), "number", "f1"))
    pf, ac = reg.items.get("supply_profiles_fetched_n"), reg.items.get("supply_accounts_n")
    if pf and ac:
        reg.add("supply_org_bot_dropped_n", pf["value"] - ac["value"], "count", source="outputs/supply_data_quality.json:search.profiles_fetched - geography.n",
                definition="organisation / bot logins dropped between the fetched profiles and the accounts")
    # frame-level shares from C01 (data_signal / accounts, bio_declared / accounts)
    for r in reg.table("C01_candidate_source_coverage"):
        f = r["frame"].lower()
        acc = _f(r["accounts"])
        for col, key, label in (("data_signal", "data_signal_share", "data-signal accounts"), ("bio_declared", "bio_declared_share", "bio-declared data-role accounts")):
            if acc:
                reg.add(f"supply_frame_{f}_{key}", _f(r[col]) / acc, "share", n=acc, denominator=f"frame {r['frame']} accounts",
                        source=f"outputs/tables/C01_candidate_source_coverage.csv:{col}/accounts[frame={r['frame']}]",
                        definition=f"frame {r['frame']}: share of accounts that are {label}", caveat="frames differ by region; compare within frame only")
    # precision of the supply classifiers (hand review, fixed audit samples)
    for tbl, key in (("SQ10_bio_classification_precision", "bio_family"), ("SQ11_project_classification_precision", "project")):
        rows = reg.table(tbl)
        if rows:
            r = rows[0]
            reg.add(f"supply_precision_{key}_strict", _f(r["strict_precision"]), "share", n=_f(r["n"]), denominator="hand-reviewed sample", source=f"outputs/tables/{tbl}.csv:strict_precision",
                    definition=f"strict precision of the {key.replace('_', ' ')} classifier on the fixed review sample", caveat="fixed audit sample; precision only, recall not measured")
            reg.add(f"supply_precision_{key}_lenient", _f(r["lenient_precision"]), "share", n=_f(r["n"]), denominator="hand-reviewed sample", source=f"outputs/tables/{tbl}.csv:lenient_precision",
                    definition=f"lenient precision of the {key.replace('_', ' ')} classifier on the fixed review sample", display=fmt_value(_f(r["lenient_precision"]), "share", "pct1") if key == "project" else None)
    vq = reg.json("visual_questions")
    figs = vq.get("figures") if isinstance(vq, dict) else None
    if figs:
        reg.add("visual_questions_n", len(figs), "count", source="outputs/visual_questions.json:figures", definition="business questions answered by one chart each (BQ01 ...)")
        last = max(figs, key=lambda f: int(re.match(r"BQ(\d+)", f["chart_id"]).group(1)))
        reg.add("visual_questions_last_id", last["chart_id"].split("_")[0], "text", source="outputs/visual_questions.json:figures[-1].chart_id", definition="id of the last business-question figure")


def supply_tables(reg: Registry) -> None:
    """Remaining Layer 2 / Layer 3 tables, systematically keyed (label slugs are stable as long as the labels are)."""
    cave = "a public-profile sample, not a workforce census; a missing public trace is not a missing skill"
    share_table(reg, "C14d_data_repo_activity", "last_push", "data_repo_push_share", unit_label="last push of data repositories", denominator="data repositories", count_prefix="data_repo_push_n")
    share_table(reg, "C14e_data_repo_stars", "stars", "data_repo_stars_share", unit_label="stars on data repositories", denominator="data repositories", count_prefix="data_repo_stars_n")
    share_table(reg, "C15_portfolio_evidence", ("population", "evidence"), "portfolio_share", unit_label="cross-platform / portfolio evidence", denominator="population in the row", caveat=cave, count_prefix="portfolio_n")
    share_table(reg, "C18_project_topics", ("population", "group", "theme"), "project_topic_share", unit_label="project topic / theme", denominator="projects or substantive projects (population in the row)", count_prefix="project_topic_n")
    share_table(reg, "C20_project_technologies", ("population", "skill"), "project_tech_share", unit_label="technology mentioned/used in a project", denominator="projects", count_prefix="project_tech_n")
    share_table(reg, "C22b_prior_domains", "prior_domain", "prior_domain_share", unit_label="prior domain named in a P_T1 bio", denominator="P_T1", count_prefix="prior_domain_n")
    share_table(reg, "C19b_readme_length", ("population", "readme_length"), "readme_length_share", unit_label="README length class", denominator="projects", count_prefix="readme_length_n")
    share_table(reg, "C19e_common_readme_headings", "heading", "readme_heading_share", unit_label="common README heading", denominator="documented projects", count_col="projects", count_prefix="readme_heading_n")
    share_table(reg, "C17b_format_combinations", "format_combination", "format_combo_share", unit_label="project format combination", denominator="projects", count_col="projects", count_prefix="format_combo_n")
    share_table(reg, "C10b_technologies_by_family", ("family", "item"), "supply_tech_family_share", unit_label="technology evidence within a bio-declared family (small n)", denominator="family accounts (P_T1)", count_prefix="supply_tech_family_n")
    wide_table(reg, "C14b_github_medians", "population", "github_median", {"median_projects": ("projects", "number"), "median_documented": ("documented", "number"), "median_data_repos": ("data_repos", "number"),
               "p90_projects": ("p90_projects", "number"), "median_account_age_years": ("account_age_years", "number")}, unit_label="GitHub activity median", n_col="n", caveat=cave)
    wide_table(reg, "C14c_repository_archetypes", "archetype", "repo_archetype", {"projects": ("n", "count"), "share_of_data_repos": ("share", "share"), "candidate_share": ("candidate_share", "share")},
               unit_label="data-repository archetype", denominator="data repositories", caveat="descriptive archetypes of repositories, not of people")
    wide_table(reg, "C11_capabilities_evidence", "capability", "supply_capability", {"share_any": ("any_share", "share"), "share_project_demonstrated": ("project_share", "share"), "candidates_any": ("any_n", "count")},
               unit_label="capability evidence among data-signal accounts", n_col="n", denominator="P_data", caveat=cave)
    wide_table(reg, "C21_project_capabilities", "capability", "project_capability", {"project_share": ("project_share", "share"), "substantive_share": ("substantive_share", "share"), "candidate_share": ("candidate_share", "share")},
               unit_label="capability evidence in projects", caveat=cave)
    share_table(reg, "C08b_education_fields", "education_field", "supply_education_field_share", unit_label="education field named in P_T1 bios", denominator="P_T1", count_prefix="supply_education_field_n")
    share_table(reg, "C16_project_count_distribution", ("population", "variable", "bucket"), "project_count_share", unit_label="distribution of the number of projects per account", denominator="population in the row",
                count_prefix="project_count_n", caveat="repositories are not projects")
    c18c = reg.table("C18c_project_theme_coverage")
    if c18c:
        r = c18c[0]
        for col in ("share_without_theme", "share_with_business_domain", "share_with_ds_method", "share_with_engineering", "share_with_ai"):
            if _f(r.get(col)) is not None:
                reg.add(f"project_theme__{col}", _f(r[col]), "share", n=_f(r["projects"]), denominator="projects", source=f"outputs/tables/C18c_project_theme_coverage.csv:{col}", definition=f"project themes: {col}")
    ij = [reg.items.get("seniority_share__intern_student"), reg.items.get("seniority_share__trainee_junior")]
    if all(ij):
        reg.add("seniority_intern_or_junior_share", ij[0]["value"] + ij[1]["value"], "share", n=ij[0]["n"], denominator=CORE_DEN, source="outputs/tables/T08_seniority_overall.csv: intern_student + trainee_junior",
                definition="share of core titles with an intern/student or junior/trainee word")
    sl = [reg.items.get("supply_seniority_share__senior"), reg.items.get("supply_seniority_share__lead_head")]
    if all(sl):
        reg.add("supply_seniority_senior_or_lead_share", sl[0]["value"] + sl[1]["value"], "share", n=sl[0]["n"], denominator="P_T1", source="outputs/tables/C06_seniority_distribution.csv: senior + lead_head [P_T1]",
                definition="share of bio-declared accounts with senior or lead/head wording")
    ne = reg.items.get("supply_education_share__p_data__no_education_wording_observable")
    if ne:
        reg.add("supply_education_wording_share_p_data", 1 - ne["value"], "share", n=ne["n"], denominator="P_data", source="outputs/tables/C08_education_levels.csv: 1 - no education wording [P_data]",
                definition="share of data-signal accounts with any education wording in bio/READMEs", caveat="absence of wording is not absence of a degree")
    c19c = reg.table("C19c_readme_structure_summary")
    if c19c:
        r = c19c[0]
        for col in ("share_results_AND_method", "share_results_AND_limitations", "share_business_context_OR_terms", "share_reproducibility_section_AND_cmd", "share_≥4_sections"):
            if _f(r.get(col)) is not None:
                reg.add(f"readme_structure__{slug(col)}", _f(r[col]), "share", n=_f(r["n"]), denominator="documented projects", source=f"outputs/tables/C19c_readme_structure_summary.csv:{col}", definition=f"README structure: {col}")
        for col in ("median_chars", "median_words", "median_headings", "median_sections_detected"):
            if _f(r.get(col)) is not None:
                reg.add(f"readme_structure__{slug(col)}", _f(r[col]), "count", n=_f(r["n"]), denominator="documented projects", source=f"outputs/tables/C19c_readme_structure_summary.csv:{col}", definition=f"README structure: {col}")
    c24 = reg.table("C24_marketing_data_intersection")
    if c24:
        r = c24[0]
        for col, key, unit in (("marketing/customer/e-commerce projects", "marketing_projects_n", "count"), ("share_of_projects", "marketing_projects_share", "share"), ("substantive", "marketing_projects_substantive_n", "count"),
                               ("candidates_with_such_project", "marketing_project_candidates_n", "count"), ("share_of_P_data", "marketing_project_candidates_share", "share"), ("of_which_T1_bio_declared", "marketing_project_candidates_t1_n", "count"),
                               ("styria", "marketing_project_candidates_styria_n", "count")):
            if _f(r.get(col)) is not None:
                reg.add(key, _f(r[col]), unit, source=f"outputs/tables/C24_marketing_data_intersection.csv:{col}", definition=f"marketing / customer / e-commerce project intersection: {col}", caveat=cave)
    # Layer 3
    wide_table(reg, "DS02_demand_supply_titles", "category", "ds_title", {"demand_count": ("demand_n", "count"), "supply_count": ("supply_n", "count"), "relative_representation": ("relative_representation", "ratio")},
               unit_label="demand x supply by normalised title", caveat="different universes; rankings and orders of magnitude, not exact ratios")
    wide_table(reg, "DS04_demand_supply_technologies", "category", "ds_tech", {"demand_share": ("demand_share", "share"), "supply_share": ("supply_share", "share"), "project_share": ("project_share", "share"),
               "relative_representation": ("relative_representation", "ratio")}, unit_label="demand x supply by technology", caveat="different universes; rankings and orders of magnitude, not exact ratios")
    wide_table(reg, "DS07_demand_supply_seniority", "category", "ds_seniority", {"demand_share": ("demand_share", "share"), "supply_share": ("supply_share", "share")}, unit_label="demand x supply by seniority wording")
    wide_table(reg, "DS08_demand_supply_education", "category", "ds_education", {"demand_share": ("demand_share", "share"), "supply_share": ("supply_share", "share")}, unit_label="demand x supply by education wording")
    for r in reg.table("DS08_demand_supply_education"):
        pass
    # official / survey context
    for r in reg.table("O01_graduates_by_field_level_at"):
        t = slug(f"{r['field_code']} {r['level']}")
        reg.add(f"graduates_latest__{t}", _f(r["graduates_latest"]), "count", source=f"outputs/tables/O01_graduates_by_field_level_at.csv:graduates_latest[{r['field']}, {r['level']}]",
                definition=f"Austrian graduates, {r['field']}, {r['level']}, latest year ({r['latest_year']})", caveat="Eurostat educ_uoe_grad02-type counts; graduates are not data-job candidates")
        if _f(r.get("change_5y_pct")) is not None:
            reg.add(f"graduates_change_5y__{t}", _f(r["change_5y_pct"]) / 100, "share", source=f"outputs/tables/O01_graduates_by_field_level_at.csv:change_5y_pct[{r['field']}, {r['level']}]",
                    definition=f"change of graduates over five years, {r['field']}, {r['level']}", display=f"{'+' if _f(r['change_5y_pct']) >= 0 else '−'}{_num(abs(_f(r['change_5y_pct'])), 0)} %")
    o03 = reg.table("O03_ict_specialists_at")
    if o03:
        last = max(o03, key=lambda r: int(r["year"]))
        first_ref = min(o03, key=lambda r: int(r["year"]))
        reg.add("ict_specialists_thousand_latest", _f(last["ict_specialists_thousand"]), "number", source="outputs/tables/O03_ict_specialists_at.csv:ict_specialists_thousand[latest year]",
                definition=f"ICT specialists employed in Austria (thousand), {last['year']}", display=fmt_value(_f(last["ict_specialists_thousand"]), "number", "int0"))
        reg.add("ict_specialists_year_latest", int(last["year"]), "number", source="outputs/tables/O03_ict_specialists_at.csv:year[latest]", definition="latest year of the Eurostat ICT-specialist series", display=last["year"])
        y11 = _rowget(o03, "year", "2011")
        if y11:
            reg.add("ict_specialists_change_since_2011", _f(last["ict_specialists_thousand"]) / _f(y11["ict_specialists_thousand"]) - 1, "share",
                    source="outputs/tables/O03_ict_specialists_at.csv:ict_specialists_thousand[latest]/[2011]-1", definition="growth of ICT specialists employed in Austria since 2011",
                    display=f"+{_num((_f(last['ict_specialists_thousand']) / _f(y11['ict_specialists_thousand']) - 1) * 100, 0)} %")
        _ = first_ref
    o02 = reg.table("O02_employment_by_isco_at")
    for r in o02:
        years = sorted(int(k) for k in r if k.isdigit())
        if not years:
            continue
        ly = years[-1]
        code = slug(r["isco08"])
        v = _f(r.get(str(ly)))
        if v is not None:
            reg.add(f"isco_employed_thousand_latest__{code}", v, "number", source=f"outputs/tables/O02_employment_by_isco_at.csv:{ly}[isco08={r['isco08']}]",
                    definition=f"persons employed (thousand, 15-64), Austria, {r['isco08_label']}, {ly}", display=fmt_value(v, "number", "int0"), caveat="Eurostat LFS aggregate; employed ICT professionals are not job openings")
            reg.add(f"isco_year_latest__{code}", ly, "number", source=f"outputs/tables/O02_employment_by_isco_at.csv: last year column", definition=f"latest year of the ISCO employment series", display=str(ly))
        ch = _f(r.get("change_since_2011_pct"))
        if ch is not None:
            reg.add(f"isco_change_since_2011__{code}", ch / 100, "share", source=f"outputs/tables/O02_employment_by_isco_at.csv:change_since_2011_pct[isco08={r['isco08']}]",
                    definition=f"change in persons employed since 2011, {r['isco08_label']}", display=f"+{_num(ch, 0)} %" if ch >= 0 else f"−{_num(abs(ch), 0)} %")
    for r in reg.table("O04_so2025_at_devtype"):
        reg.add(f"so_at_devtype_share__{slug(r['item'])}", _f(r["count"]) / _f(r["n"]), "share", n=_f(r["n"]), denominator="Austrian respondents with DevType",
                source=f"outputs/tables/O04_so2025_at_devtype.csv:count/n[item={r['item']}]", definition=f"Stack Overflow 2025 Austria: share in DevType {r['item']}", caveat="survey sample, not a census")
    for r in reg.table("O07_so2025_at_experience"):
        reg.add(f"so_at_median__{slug(r['variable'])}__{slug(r['population'])[:40]}", _f(r["median"]), "number", source=f"outputs/tables/O07_so2025_at_experience.csv:median[variable={r['variable']}, population={r['population']}]",
                definition=f"Stack Overflow 2025 Austria: median {r['variable']} ({r['population']})", n=_f(r["n"]), display=fmt_value(_f(r["median"]), "number", "int0"))
    for r in reg.table("O05_so2025_at_technologies"):
        pass


def extras2(reg: Registry) -> None:
    """Family x seniority, family x seniority pay, clusters, derived entry-track German counts, adjacent non-data counts."""
    share_table(reg, "T08_seniority_by_family", ("role_family", "seniority"), "seniority_family_share", unit_label="seniority wording in the title within a family",
                denominator="family core postings", count_prefix="seniority_family_n")
    for r in reg.table("T09c_salary_by_family_seniority"):
        tag = f"{slug(r['role_family'])}__{slug(r['seniority'])}"
        reg.add(f"salary_family_seniority_floor_median_eur__{tag}", _f(r["min_median"]), "eur", n=_f(r["n"]),
                source=f"outputs/tables/T09c_salary_by_family_seniority.csv:min_median[{r['role_family']}, {r['seniority']}]",
                definition=f"median advertised minimum, {r['role_family']} x {r['seniority']}", caveat="advertised legal floors; small n in most cells",
                basis="advertised legal floor, annual gross, monthly x 14")
        reg.add(f"salary_family_seniority_n__{tag}", _f(r["n"]), "count", source=f"outputs/tables/T09c_salary_by_family_seniority.csv:n[{r['role_family']}, {r['seniority']}]",
                definition=f"ads with a figure, {r['role_family']} x {r['seniority']}")
    for r in reg.table("T15_clusters_kmeans"):
        c = r["cluster"]
        for col, key, unit in (("n", "cluster_n", "count"), ("share", "cluster_share", "share"), ("styria_share", "cluster_styria_share", "share"),
                               ("english_posting_share", "cluster_english_share", "share"), ("german_required_share", "cluster_german_share", "share")):
            if _f(r.get(col)) is not None:
                reg.add(f"{key}__c{c}", _f(r[col]), unit, source=f"outputs/tables/T15_clusters_kmeans.csv:{col}[cluster={c}]", definition=f"requirement archetype (k-means cluster {c}): {col}",
                        caveat="descriptive groupings of skill co-occurrence, not professions; silhouette is weak")
    cl = reg.json("clusters")
    for key, path, unit, label in (("cluster_k", "k", "count", "k chosen by silhouette"), ("cluster_silhouette", "silhouette", "number", "silhouette of the chosen k (weak structure below 0.25)"),
                                   ("cluster_postings_n", "n_postings", "count", "postings clustered")):
        if isinstance(cl.get(path), (int, float)):
            reg.add(key, cl[path], unit, source=f"outputs/clusters.json:{path}", definition=label, display=fmt_value(cl[path], "number", "f3") if key == "cluster_silhouette" else None)
    # entry track: German requirement stated (required + required_implied)
    for tr in ("intern_student", "trainee_junior", "rest"):
        rows = {r["german_requirement"]: r for r in reg.table("T17b_german_by_entry_track") if r["entry_track"] == tr}
        if rows:
            n = _f(next(iter(rows.values()))["n"])
            cnt = sum(_f(rows[k]["count"]) for k in ("required", "required_implied") if k in rows)
            reg.add(f"german_stated_entry_n__{tr}", cnt, "count", n=n, basis=TEXT, source=f"outputs/tables/T17b_german_by_entry_track.csv:required+required_implied[entry_track={tr}]",
                    definition=f"ads in entry track {tr} that state a German requirement", denominator="ads with a description in the entry-track group")
            reg.add(f"german_stated_entry_share__{tr}", cnt / n, "share", n=n, basis=TEXT, source=f"outputs/tables/T17b_german_by_entry_track.csv:(required+required_implied)/n[entry_track={tr}]",
                    definition=f"share of entry track {tr} ads that state a German requirement", denominator="ads with a description in the entry-track group")
    for r in reg.table("T16_adjacent_demand_by_region"):
        reg.add(f"adjacent_non_data_n__{slug(r['region'])}__{slug(r['tool'])}", _f(r["in_non_data_title"]), "count",
                source=f"outputs/tables/T16_adjacent_demand_by_region.csv:in_non_data_title[{r['region']}, {r['tool']}]",
                definition=f"AMS-feed ads in {r['region']} that mention {r['tool']} under a non-data title", caveat="AMS feed only; three regions")
    fm = {k: reg.items.get(f"family_n__{k}") for k in ("marketing_analytics", "product_analytics")}
    if all(fm.values()):
        reg.add("marketing_and_product_analytics_n", fm["marketing_analytics"]["value"] + fm["product_analytics"]["value"], "count",
                source="outputs/tables/T02_role_family_counts.csv:count[marketing_analytics]+[product_analytics]", definition="core postings in the marketing-analytics and product-analytics families together",
                n=(reg.json("market_summary").get("counts") or {}).get("core_canonical"), denominator=CORE_DEN)


# --------------------------------------------------------------------------------------------------------------
# claim keys: the variable parts of qualitative sentences (names, ranks, lists, ratios), so a sentence is written once
# with markers and stays true when the numbers move. Closed lists below are definitions, not data; a key is always
# registered when its inputs exist, also when a category is empty this run.
# --------------------------------------------------------------------------------------------------------------
JB_LARGE_REGIONS = (("styria", "Styria"), ("vienna", "Vienna"), ("upper_austria", "Upper Austria"))   # regions of the official series (JB01)
RANK_SKILLS = (("sql", "SQL"), ("python", "Python"), ("visualisation", "data visualisation"), ("generic_ai", "generic AI"),
               ("data_quality", "data governance/quality"), ("cloud", "cloud"), ("etl", "ETL/ELT"), ("azure", "Azure"), ("power_bi", "Power BI"),
               ("excel", "Excel"), ("data_modelling", "data modelling"), ("ml", "machine learning"), ("genai", "generative AI/LLM"), ("ci_cd", "CI/CD"))
DECISION_WEIGHTINGS = (("default", "default"), ("geography_first", "geography-first"), ("language_first", "language-first"), ("equal", "equal"))
FAMILY_NAME = {"bi": "BI"}
ENTRY_TRACK_NAME = (("intern_student", "intern"), ("trainee_junior", "junior"))
ROBUSTNESS_N = 30   # the project's n = 30 robustness rule (D01)
DECISION_MIN_N = 20  # src/analysis/build_decision_matrix.py: families with fewer Austrian postings are reported but not ranked


def ordinal(n: int) -> str:
    n = int(n)
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def join_words(items: list[str]) -> str:
    items = [str(i) for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def family_name(slug_: str) -> str:
    return FAMILY_NAME.get(slug_, slug_.replace("_", " "))


def claim_keys(reg: Registry) -> None:
    """Derived keys for sentences whose variable parts (a list of regions, a ratio, a rank, a count against a rule) used to be typed."""
    items = reg.items
    # (1) official series: which large regions are above the first-year level
    ch = [(label, items[f"jb_data_scientist_change__{tag}"]) for tag, label in JB_LARGE_REGIONS if f"jb_data_scientist_change__{tag}" in items]
    if ch:
        src = "outputs/tables/JB01_yearly_counts_long.csv: jb_data_scientist_change__styria|vienna|upper_austria"
        cav = "official yearly flow of a coarse AMS occupation class, not our titles"
        grow = sorted((c for c in ch if c[1]["value"] > 0), key=lambda c: -c[1]["value"])
        reg.add("jb_growing_regions", join_words([f"{lab} ({e['display']})" for lab, e in grow]) if grow else "none of Styria, Vienna and Upper Austria",
                "text", source=src, caveat=cav,
                definition="large regions (Styria, Vienna, Upper Austria) whose online ads in the 'Data Scientist' class are above the first-year level, largest change first")
        reg.add("jb_growing_regions_n", len(grow), "count", source=src, caveat=cav, definition="number of large regions above the first-year level on the official series")
        reg.add("jb_regions_change_text", ", ".join(f"{lab} {e['display']}" for lab, e in sorted(ch, key=lambda c: -c[1]["value"])), "text", source=src, caveat=cav,
                definition="change vs the first year for each large region, largest first")
    # (2) Vienna vs the Graz commuting area
    v, g = items.get("vienna_core_flag"), items.get("graz_area_core_flag")
    if v and g:
        ratio = v["value"] / g["value"] if g["value"] else None
        reg.add("vienna_to_graz_core_ratio", ratio if ratio is not None else "n/a (no Graz-area postings)", "ratio" if ratio is not None else "text",
                source="outputs/market_summary.json:counts.vienna_core/graz_area_core", basis=ANYSITE,
                definition="Vienna's core postings divided by the Graz commuting-area core postings (any listed site)",
                caveat="both counts are one-day stocks; the Graz-area count is small")
    # (3) rank of the headline skills among the headline skills
    shares = [(k, name, items[f"{k}_share"]) for k, name in RANK_SKILLS if f"{k}_share" in items]
    if shares:
        src = "outputs/tables/T05_skills_all_tech.csv: share of the headline skills (RANK_SKILLS)"
        for k, _name, e in shares:
            rank = 1 + sum(1 for _k, _n, o in shares if o["value"] > e["value"] + 1e-12)
            reg.add(f"tech_skill_rank__{k}", ordinal(rank), "text", n=e["n"], denominator=DESC_DEN, basis=TEXT, source=src, caveat=CAVEAT_MENTION,
                    definition=f"rank of {k} by share of ads among the {len(shares)} headline skills (ties share the better rank)")
        top = sorted(shares, key=lambda t: -t[2]["value"])[:3]
        reg.add("tech_skill_rank_set_n", len(shares), "count", source=src, definition="number of headline skills ranked against each other")
        reg.add("tech_skills_top3_text", join_words([f"{n} {fmt_value(e['value'], 'share')}" for _k, n, e in top]), "text", basis=TEXT, source=src, caveat=CAVEAT_MENTION,
                definition="the three headline skills with the highest share of ads")
        reg.add("tech_skill_top1_name", top[0][1], "text", basis=TEXT, source=src, caveat=CAVEAT_MENTION, definition="the headline skill with the highest share of ads")
    # (4) decision-matrix ranks
    fams = sorted({k.split("__", 1)[1] for k in items if k.startswith("decision_rank_default__")})
    rank = {(w, f): int(items[f"decision_rank_{w}__{f}"]["value"]) for w, _l in DECISION_WEIGHTINGS for f in fams if f"decision_rank_{w}__{f}" in items}
    if fams and rank:
        src = "outputs/tables/D02_sensitivity.csv: rank_default|rank_geography_first|rank_language_first|rank_equal"
        cav = "the ranking measures market size, English openness and advertised floors, not ease of entry"
        if all(("data_analytics" in {f for (w2, f) in rank if w2 == w}) for w, _l in DECISION_WEIGHTINGS):
            reg.add("analytics_decision_ranks_text", join_words([f"{ordinal(rank[(w, 'data_analytics')])} ({lab})" for w, lab in DECISION_WEIGHTINGS]), "text",
                    source=src, caveat=cav, definition="rank of data analytics under the four weightings, in the order default, geography-first, language-first, equal")
        ranked = sorted((f for f in fams if ("default", f) in rank), key=lambda f: rank[("default", f)])
        top3_default = ranked[:3]
        reg.add("decision_ranking_default_text", ", ".join(f"{family_name(f)} {ordinal(rank[('default', f)])}" for f in ranked), "text", source=src, caveat=cav,
                definition="all ranked families under the default weighting, best first, with their ranks")
        unranked = sorted((k[len("family_n__"):], items[k]["value"]) for k in items if k.startswith("family_n__") and k[len("family_n__"):] not in fams)
        reg.add("decision_unranked_text", join_words([f"{family_name(f)} (n = {int(n)})" for f, n in unranked]) if unranked else "none", "text", source=src, caveat=cav,
                definition=f"core families the decision matrix reports but does not rank (fewer than {DECISION_MIN_N} Austrian postings), with their posting counts")
        reg.add("decision_top3_default_text", ", ".join(f"{family_name(f)} {ordinal(rank[('default', f)])}" for f in top3_default), "text", source=src, caveat=cav,
                definition="the three best-ranked families under the default weighting, with their ranks")
        leaders = []
        for f in fams:
            ws = [lab for w, lab in DECISION_WEIGHTINGS if rank.get((w, f)) == 1]
            if ws:
                leaders.append((f, ws))
        reg.add("decision_leaders_text", "; ".join(f"{family_name(f)} under {join_words(ws)} weights" for f, ws in leaders), "text", source=src, caveat=cav,
                definition="which family ranks first under which weighting")
        diffs = []
        for w, lab in DECISION_WEIGHTINGS[1:]:
            top3 = sorted((f for f in fams if (w, f) in rank), key=lambda f: rank[(w, f)])[:3]
            if set(top3) != set(top3_default):
                came, went = sorted(set(top3) - set(top3_default)), sorted(set(top3_default) - set(top3))
                diffs.append((lab, f"{join_words([family_name(f) for f in came])} replaces {join_words([family_name(f) for f in went])}"))
        same = len(DECISION_WEIGHTINGS) - len(diffs)
        reg.add("decision_top3_stability_text",
                "unchanged under all four weightings" if not diffs else f"unchanged under {same} of {len(DECISION_WEIGHTINGS)} weightings (" + "; ".join(f"{lab} weights: {t}" for lab, t in diffs) + ")",
                "text", source=src, caveat=cav,
                definition="whether the set of the three best-ranked families under the default weighting also holds under the other three weightings")
    # (5) entry-track denominators against the n = 30 rule
    parts = [(lab, int(items[f"entry_track_desc_n__{tr}"]["value"])) for tr, lab in ENTRY_TRACK_NAME if f"entry_track_desc_n__{tr}" in items]
    if parts:
        src = "outputs/tables/T17_skills_by_entry_track.csv:n"
        reg.add("entry_track_denominators_vs_30", ", ".join(f"{lab} {n} ({'at or above' if n >= ROBUSTNESS_N else 'below'})" for lab, n in parts), "text", source=src,
                definition=f"entry-track denominators (ads with a description) against the n = {ROBUSTNESS_N} robustness rule", caveat="directional only; not a second market")
        reg.add("entry_track_min_n", min(n for _l, n in parts), "count", source=src, definition="smallest entry-track denominator (intern, junior)")


def add_history_keys(reg: Registry, history_path, run_date: dt.date, meta: dict) -> None:
    """Derived history keys for every tracked salary-floor key (see metrics_history.py). The stored history is read as of `run_date`;
    this run's own values replace any stored rows of the same run date, so a re-run gives the same keys."""
    rd = run_date.isoformat()
    base = dict(reg.items)
    base["_meta"] = {"week_id": meta.get("week_id"), "demand_vintage": meta.get("demand_vintage")}
    rows = metrics_history.upsert(metrics_history.read_history(history_path), metrics_history.tracked_rows(base, rd), rd)
    where = "data/private/metrics_history/history.csv"
    for key in sorted(base):
        entry = base[key]
        if key == "_meta" or not metrics_history.is_tracked(key, entry) or not metrics_history.has_derived_keys(entry):
            continue
        pts = metrics_history.series(rows, key, up_to=rd)
        if not pts:
            continue
        st = metrics_history.series_stats(pts)
        common = dict(source=f"{where}: {key} over {st['n']} run(s) up to {rd}", caveat="advertised legal floors, one value per weekly run; a short history is not a trend")
        what = entry.get("definition") or key
        for stat, word in (("min", "lowest"), ("max", "highest"), ("median", "median"), ("mode", "most frequent")):
            reg.add(f"{key}__hist_{stat}", st[stat], "eur", definition=f"{word} value over all weekly runs: {what}", **common)
        reg.add(f"{key}__hist_n", st["n"], "count", definition=f"number of weekly runs that have this key: {what}", **common)
        reg.add(f"{key}__hist_first_date", st["first_date"], "date", definition=f"run date of the first stored value: {what}", **common)
        reg.add(f"{key}__trend", trend_text(st), "text", definition=f"trend over the stored runs: {what}", **common)


def _signed_k(value: float) -> str:
    """'+€3.7k' / '−€0.4k' (U+2212): euro in thousands, one decimal."""
    return f"{'+' if value >= 0 else '−'}{fmt_value(abs(value), 'eur', 'eur_k')}"


def trend_text(st: dict) -> str:
    """Words for the change of a floor key over the stored runs. Below metrics_history.TREND_MIN_RUNS runs: the plain change, flagged as no trend."""
    n, first = st["n"], st["first_date"]
    if st["slope_per_week"] is None:
        if n < 2:
            return f"too few runs for a trend (n={n})"
        d = st["change"]
        if fmt_value(abs(d), "eur", "eur_k") == "€0.0k":
            change = f"unchanged since {first} ({n} runs)"
        else:
            change = f"{'up' if d > 0 else 'down'} {_signed_k(d)} since {first} ({n} runs)"
        return f"too few runs for a trend (n={n}); {change}"
    sl = st["slope_per_week"]
    word = "flat" if abs(sl) < metrics_history.FLAT_EUR_PER_WEEK else ("rising" if sl > 0 else "falling")
    return f"{word} {_signed_k(sl)}/week (OLS over {n} runs since {first}); total change {_signed_k(st['change'])}"


def build_registry(root: Path | str = ROOT, run_date: dt.date | None = None, *, generated_at: str | None = None, history_path=None) -> dict:
    """`history_path`: the private salary-floor history file; None = no stored history (the `__hist_*` keys then rest on this run alone)."""
    root = Path(root)
    run_date = run_date or dt.date.today()
    reg = Registry(root)
    meta = vintages(reg, run_date)
    add_vintage_keys(reg, meta)
    for step in (layer1_counts, families_and_geo, skills, language, pay_and_work, official_and_seasonality, quality, layer2_3, supply_json, supply_tables, extras, extras2, claim_keys):
        step(reg)
    add_history_keys(reg, history_path, run_date, meta)
    return finalize(reg, meta, run_date, generated_at)


def finalize(reg: Registry, meta: dict, run_date: dt.date, generated_at: str | None) -> dict:
    out = {k: reg.items[k] for k in sorted(reg.items)}
    meta = dict(meta)
    meta["generated_at"] = generated_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    meta["key_count"] = len(out)
    meta["missing_inputs"] = sorted(set(reg.missing))
    meta["stale_rule"] = f"stale_after = vintage + {STALE_AFTER_DAYS} days"
    return {"_meta": meta, **out}


def write_registry(registry: dict, out: Path) -> None:
    """Atomic, LF, UTF-8, stable key order (so a re-run on unchanged data changes only generated_at)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    keys = [k for k in registry if k != "_meta"]
    lines = ["{", f'"_meta": {json.dumps(registry["_meta"], ensure_ascii=False)},']
    for i, key in enumerate(keys):
        lines.append(f"{json.dumps(key)}: {json.dumps(registry[key], ensure_ascii=False)}" + ("," if i < len(keys) - 1 else ""))
    lines.append("}")
    text = "\n".join(lines) + "\n"  # one entry per line: diff-friendly and about a quarter smaller than indent=1
    tmp = out.with_suffix(out.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    tmp.replace(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build outputs/metrics.json: every number the living documents quote, computed from outputs/*.json and outputs/tables/*.csv.")
    ap.add_argument("--run-date", help="ISO date of the weekly run (sets week_id, generated_at); default today")
    ap.add_argument("--run-manifest", help="accepted for the weekly orchestrator; ignored")
    ap.add_argument("--out", default=str(ROOT / "outputs" / "metrics.json"), help="output path (default outputs/metrics.json)")
    ap.add_argument("--root", default=str(ROOT), help="repository root to read outputs from (default: this repository)")
    ap.add_argument("--history", default=None, help="salary-floor history file (default <root>/data/private/metrics_history/history.csv)")
    ap.add_argument("--no-history", action="store_true", help="neither read nor write the salary-floor history")
    ap.add_argument("--stdout", action="store_true", help="print a summary")
    args = ap.parse_args(argv)
    run_date = dt.date.fromisoformat(args.run_date) if args.run_date else dt.date.today()
    generated_at = f"{run_date.isoformat()}T00:00:00+00:00" if args.run_date else None
    history_path = None if args.no_history else Path(args.history) if args.history else Path(args.root) / metrics_history.HISTORY_REL
    registry = build_registry(Path(args.root), run_date, generated_at=generated_at, history_path=history_path)
    write_registry(registry, Path(args.out))
    if history_path is not None and args.run_date:       # only a stamped (weekly) run is stored; an ad-hoc run never adds a history row
        rows = metrics_history.update_history_file(history_path, registry, run_date.isoformat())
        print(f"metrics history: {len(rows)} rows, {len({r['run_date'] for r in rows})} run(s) -> {history_path}")
    import metrics_watch  # sibling module; evaluates the claim watch list against the fresh registry
    watch = metrics_watch.build_watch(registry)
    watch_path = Path(args.out).with_name("metrics_watch.json")
    watch_path.write_text(json.dumps(watch, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    meta = registry["_meta"]
    print(f"metrics registry: {meta['key_count']} keys -> {args.out}  (week {meta['week_id']}, demand {meta.get('demand_vintage')}, supply {meta.get('supply_vintage')})")
    if watch["claims_failing"]:
        print(f"  claims that may no longer hold ({len(watch['claims_failing'])}): " + ", ".join(watch["claims_failing"]) + f"  -> {watch_path.name}", file=sys.stderr)
    if meta["missing_inputs"]:
        print("  missing inputs (their keys are absent): " + ", ".join(meta["missing_inputs"]), file=sys.stderr)
    if args.stdout:
        for k, v in registry.items():
            if k != "_meta":
                print(f"{k:60s} {v['display']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
