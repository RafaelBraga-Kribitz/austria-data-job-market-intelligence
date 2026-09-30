"""Figure engine for the visual decision layer (DSX house style).

Every figure in `outputs/figures/BQ*` is built through this module so that the
whole layer shares one grammar:

* **House style.** `src/viz/styles/dsx-urban.mplstyle` (vendored from GSD-DSX,
  WCAG-AA verified palette, Lato) is applied at import time.
* **Takeaway titles.** `finalise()` wraps the DSX `finalise_figure` helper: the
  title is a sentence with a magnitude, never a chart name, and the source line
  is a mandatory keyword (a figure without provenance is a `TypeError`).
* **One highlight colour.** `HILITE` marks the element that concerns *this*
  reader's decision (Graz/Styria, the target family, the reachable set). It is
  never the only channel — the highlighted element is always also labelled.
* **Deterministic output.** SVG is written with the DSX recipe (fixed hashsalt,
  glyphs as paths, no render timestamp) and sealed with stdlib SHA-256 into
  `outputs/figures/FIGURE-MANIFEST.yaml`; PNG is written alongside for markdown.

Chart selection follows `references/chart-selection.md` of GSD-DSX: name the
relationship first, then take an admissible mark from the catalogue. The
relationship and mark of every figure are recorded in the manifest.
"""
from __future__ import annotations

import hashlib
import json
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

# Flat-script layout (no packages), as everywhere else in src/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dsx_plotstyle import finalise_figure, save_deterministic  # noqa: E402,F401

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
STYLE = Path(__file__).resolve().parent / "styles" / "dsx-urban.mplstyle"

plt.style.use(str(STYLE))
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "font.size": 11})

# ---- palette ---------------------------------------------------------------------------------
# From the vendored dsx-urban cycle; named here so the grammar is explicit.
BASE = "#1696d2"      # the market / the reference set
HILITE = "#ec008b"    # the part that bears on this reader's decision
THIRD = "#1b7837"     # a second comparison series
FOURTH = "#b35806"    # a third comparison series
MUTED = "#5c5859"     # context, de-emphasised
GRID = "#d2d2d2"


# ---- data vintages ---------------------------------------------------------------------------
# Read from the run's own metadata so that captions follow a re-collection; the literals are the
# 2026-09 vintages and only apply when a metadata file is absent (e.g. a public clone without
# data/processed/).
def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _demand_vintage(default: str = "2026-09-16") -> str:
    summary = _read_json(ROOT / "outputs" / "market_summary.json") or {}
    first = str((summary.get("collected_at_range") or {}).get("min") or "")[:10]
    return first or default


def _supply_vintage(default: str = "2026-09-17/18") -> str:
    manifest = _read_json(ROOT / "data" / "processed" / "supply_build_manifest.json") or {}
    collected = str(manifest.get("collection_date") or "")[:10]
    built = str(manifest.get("built_at") or "")[:10]
    if not collected:
        return default
    # the README/profile fetch runs past midnight: "2026-09-17/18" = collected on the 17th, built on the 18th
    if built and built != collected and built[:8] == collected[:8]:
        return f"{collected}/{built[8:]}"
    return collected


def _year_span(table_name: str, default: str) -> str:
    try:
        with open(TABLES / table_name, encoding="utf-8") as handle:
            header = handle.readline().rstrip().split(",")
            col = header.index("year")
            years = {int(line.split(",")[col]) for line in handle if line.strip()}
        return f"{min(years)}-{max(years)}"
    except (OSError, ValueError, IndexError):
        return default


DEMAND_VINTAGE = _demand_vintage()
SUPPLY_VINTAGE = _supply_vintage()
DEMAND_SOURCE = (f"Austrian data-role postings, snapshot {DEMAND_VINTAGE} "
                 "(EURES/AMS, karriere.at, LinkedIn, willhaben, jobs.at, deduplicated)")
SUPPLY_SOURCE = f"Public GitHub accounts with an Austrian location signal, {SUPPLY_VINTAGE}"
AMS_SOURCE = (f"AMS JobBarometer yearly ad counts {_year_span('JB01_yearly_counts_long.csv', '2020-2025')}, "
              "occupation class 'Data Scientist (m/w)'")
EUROSTAT_SOURCE = (f"Eurostat Job Vacancy Statistics, Austria, quarterly "
                   f"{_year_span('S02_quarter_ratios_by_year.csv', '2009-2025')}")
SNAPSHOT = f"demand {DEMAND_VINTAGE} / supply {SUPPLY_VINTAGE}"


# ---- headline Layer 1 counts with their geographic basis (OQ-19) ----------------------------------
# Two regional bases exist and must never be mixed in one sentence without a label:
#   primary state  - one state per ad (the `state` field; T03a_state_counts.csv): Styria 54, Vienna 343
#   any listed site - every ad that lists at least one site in the region (the is_styria / is_vienna /
#                     is_graz_area flags; market_summary.json styria_core / vienna_core / graz_area_core):
#                     Styria 58, Vienna 350. T02 styria_count, T03c, T04a `styria`, T07e and every
#                     *_by_styria table use this basis. The Graz commuting area is flag-only (52).
PRIMARY_BASIS = "by primary state"
ANY_SITE_BASIS = "listing at least one site in the region"


def market_counts() -> dict:
    """Headline counts from market_summary.json and T03a, keyed by basis (see the note above)."""
    summary = _read_json(ROOT / "outputs" / "market_summary.json")
    if summary is None:
        raise FileNotFoundError("outputs/market_summary.json is missing - run src/analysis/run_analysis.py first")
    c = summary["counts"]
    primary = {}
    with open(TABLES / "T03a_state_counts.csv", encoding="utf-8") as handle:
        header = handle.readline().rstrip().split(",")
        i_state, i_count = header.index("state"), header.index("count")
        for line in handle:
            cells = line.rstrip().split(",")
            if len(cells) > max(i_state, i_count):
                primary[cells[i_state]] = int(cells[i_count])
    return {
        "raw_rows": int(c["raw_rows_all_sources"]),
        "canonical": int(c["canonical_groups_all"]),
        "core": int(c["core_canonical"]),
        "core_with_description": int(c["core_with_description"]),
        "styria_primary": primary.get("Steiermark", int(c.get("styria_core_primary_state", 0))),
        "styria_any_site": int(c["styria_core"]),
        "vienna_primary": primary.get("Wien", int(c.get("vienna_core_primary_state", 0))),
        "vienna_any_site": int(c["vienna_core"]),
        "graz_area_any_site": int(c["graz_area_core"]),
        # Graz-area ads whose primary state is Styria; only present in market_summary.json from 2026-09-30 on
        "graz_area_primary_styria": (int(c["graz_area_core_primary_styria"])
                                     if c.get("graz_area_core_primary_styria") is not None else None),
    }


def styria_basis_note(counts: dict | None = None) -> str:
    """One clause that reconciles the two Styria totals, for captions and caveats."""
    c = counts or market_counts()
    extra = c["styria_any_site"] - c["styria_primary"]
    return (f"Styria = {c['styria_primary']} ads {PRIMARY_BASIS}, {c['styria_any_site']} listing at least one "
            f"Styrian site (+{extra} multi-site ads whose primary state is elsewhere)")


@dataclass
class Spec:
    """The declaration a figure is judged against (DSX visuals[] row)."""

    chart_id: str
    question: str            # the business question, in the reader's own terms
    answer: str              # the one-sentence answer, numbers included
    relationship: str        # DSX relationship vocabulary
    mark: str                # DSX chart-catalogue mark
    data_signature: str      # DSX data-input-type
    tables: list[str]        # source tables in outputs/tables/
    units: str
    anchors: list[tuple[str, str, str]] = field(default_factory=list)
    caveat: str = ""
    svg_sha256: str = ""

    @property
    def png(self) -> str:
        return f"{self.chart_id}.png"

    @property
    def svg(self) -> str:
        return f"{self.chart_id}.svg"


def wrap(text: str, width: int = 74) -> str:
    return "\n".join(textwrap.wrap(text, width=width))


def new_figure(height: float = 5.0, width: float = 9.5) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots(figsize=(width, height))
    return fig, ax


def finalise(
    fig: Figure,
    *,
    title: str,
    source: str,
    units: str,
    n: str,
    note: str = "",
) -> Figure:
    """Takeaway title + mandatory source, with the layout reserved first.

    Both texts are wrapped to the figure's own width and the axes rectangle is
    computed from the resulting line counts, so a long takeaway sentence or a long
    provenance line pushes the plot down instead of being clipped by it. The
    source note carries provenance, n and units together, because a chart that is
    screenshotted out of this repository has to defend itself alone.
    """
    width_in = fig.get_size_inches()[0]
    title_cols = int(width_in * 9.0)      # bold, x-large: calibrated against Lato at 13.2 pt
    source_cols = int(width_in * 15.4)    # small: calibrated against Lato at 8.8 pt
    title_text = wrap(title, title_cols)
    source_text = wrap(
        f"Source: {source}. {n}. Units: {units}." + (f" {note}" if note else ""),
        source_cols,
    )
    title_lines = title_text.count("\n") + 1
    source_lines = source_text.count("\n") + 1
    height_in = fig.get_size_inches()[1]
    top = 1.0 - (0.30 * title_lines + 0.12) / height_in
    bottom = (0.20 * source_lines + 0.12) / height_in
    fig.tight_layout(rect=(0.0, bottom, 1.0, top))
    # finalise_figure prefixes "Source: " itself; the prefix is already in source_text,
    # so the label is passed through the subtitle-free path with the prefix stripped.
    finalise_figure(
        fig,
        title=title_text,
        subtitle=None,
        source=source_text.removeprefix("Source: "),
    )
    return fig


def spread_labels(
    positions: list[float],
    *,
    min_gap: float,
    lo: float | None = None,
    hi: float | None = None,
) -> list[float]:
    """Push overlapping label positions apart along one axis, inside [lo, hi].

    A forward pass opens each label to at least `min_gap` above its predecessor, a
    backward pass pulls the overflow back under `hi`, and both stay in rank order -
    so a label never crosses another and never leaves the axes. Labels keep their
    own position wherever the crowding allows, which is what keeps the leader lines
    short in the sparse parts of the plot.
    """
    if not positions:
        return []
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    placed = {}
    previous = None
    for i in order:
        value = positions[i]
        if lo is not None:
            value = max(value, lo)
        if previous is not None:
            value = max(value, previous + min_gap)
        placed[i] = value
        previous = value
    if hi is not None and previous is not None and previous > hi:
        previous = None
        for i in reversed(order):
            value = min(placed[i], hi if previous is None else previous - min_gap)
            if lo is not None:
                value = max(value, lo)
            placed[i] = value
            previous = value
    return [placed[i] for i in range(len(positions))]


def label_bars(ax: Axes, values, labels, *, horizontal: bool = True, pad: float = 0.01, color=None) -> None:
    """Direct value labels — they replace a legend and survive a screenshot."""
    span = (max(values) - min(0, min(values))) or 1
    for i, (v, text) in enumerate(zip(values, labels)):
        offset = span * pad
        if horizontal:
            ax.text(v + (offset if v >= 0 else -offset), i, text, va="center",
                    ha="left" if v >= 0 else "right", fontsize=9, color=color or "#222222")
        else:
            ax.text(i, v + offset, text, ha="center", va="bottom", fontsize=9, color=color or "#222222")


def seal(path: Path) -> str:
    """stdlib SHA-256 of the written bytes, in `dsx seal` form."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def save(fig: Figure, spec: Spec) -> Spec:
    """Write the deterministic SVG plus a PNG for markdown, and seal the SVG."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    svg_path = save_deterministic(fig, FIGURES / spec.svg, metadata={"Date": None})
    fig.savefig(FIGURES / spec.png, format="png", metadata={"Software": None})
    plt.close(fig)
    spec.svg_sha256 = seal(svg_path)
    return spec


def pct(x: float, digits: int = 0) -> str:
    return f"{x * 100:.{digits}f}%"


def eur_k(x: float) -> str:
    return f"€{x / 1000:.1f}k"
