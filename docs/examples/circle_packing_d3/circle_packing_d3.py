"""
circle_packing_d3.py  —  builds a standalone zoomable circle-packing HTML
from a pre-aggregated pandas DataFrame + color_map dict.

Mirrors the conventions of sankey_d3_stacked_report.py:
  • Accepts a pre-aggregated DataFrame (one row per leaf).
  • Accepts a color_map dict: { "key": { light, dark, display, order } }
  • Returns a standalone HTML string (or writes to a file).

──────────────────────────────────────────────────────────────────────────────
DATAFRAME CONTRACT
──────────────────────────────────────────────────────────────────────────────
The input DataFrame must have:
  • One or more HIERARCHY columns  (e.g. ["diagnosis", "drug_class", "drug"])
    — these become the nested circle levels, outermost → innermost.
  • One SIZE column                (e.g. "patient_count")
    — drives circle area at the leaf level; aggregated upward automatically.
  • Zero or more KPI columns       (e.g. ["avg_age", "pct_female"])
    — shown in tooltip; aggregated upward with a weighted mean by size_col.

Example:
    diagnosis          | drug_class      | drug       | patient_count | avg_age
    Type 2 Diabetes    | GLP-1 Agonist   | Ozempic    | 8500          | 59.8
    Type 2 Diabetes    | GLP-1 Agonist   | Mounjaro   | 5700          | 60.5
    ...

──────────────────────────────────────────────────────────────────────────────
COLOR MAP CONTRACT  (same shape as Sankey)
──────────────────────────────────────────────────────────────────────────────
{
    "Type 2 Diabetes": { "light": "#4f9cf6", "dark": "#2c6fc9",
                         "display": "T2 Diabetes", "order": 1 },
    ...
}
Keys can be any level in the hierarchy.  Unrecognised nodes get auto-colors.

──────────────────────────────────────────────────────────────────────────────
QUICK START
──────────────────────────────────────────────────────────────────────────────
    from circle_packing_d3 import create_circle_packing_html

    html = create_circle_packing_html(
        df              = summary_df,
        hierarchy_cols  = ["diagnosis", "drug_class", "drug"],
        size_col        = "patient_count",
        kpi_cols        = ["patient_count", "avg_age", "pct_female"],
        kpi_labels      = {"patient_count": "Patients",
                           "avg_age":       "Avg Age",
                           "pct_female":    "% Female"},
        kpi_format      = {"patient_count": "integer",
                           "avg_age":       "decimal1",
                           "pct_female":    "pct"},
        color_map       = COLOR_MAP,
        title           = "Patient Universe — Diagnosis × Drug",
        output_path     = "patient_universe.html",   # optional
    )
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def create_circle_packing_html(
    df:              pd.DataFrame,
    hierarchy_cols:  List[str],
    size_col:        str,
    color_map:       Dict[str, Any],
    kpi_cols:        Optional[List[str]]        = None,
    kpi_labels:      Optional[Dict[str, str]]   = None,
    kpi_format:      Optional[Dict[str, str]]   = None,
    title:           str                        = "Market Universe",
    subtitle:        str                        = "Click any circle to zoom in · Click background to zoom out",
    root_label:      str                        = "All",
    output_path:     Optional[str]              = None,
    template_path:   Optional[str]              = None,
) -> str:
    """
    Build a standalone circle-packing HTML file.

    Parameters
    ----------
    df              Pre-aggregated DataFrame (one row = one leaf node).
    hierarchy_cols  Ordered list of column names forming the hierarchy
                    (outermost first).  Depth = len(hierarchy_cols).
    size_col        Column whose value drives circle area.  Must be numeric.
    color_map       Dict mapping any node name → {light, dark, display, order}.
                    Nodes absent from the map receive auto-assigned colors.
    kpi_cols        Columns to display in tooltip (and stats bar).
                    Defaults to [size_col].
    kpi_labels      Human-readable labels for kpi_cols.
    kpi_format      Format specifiers per kpi_col.  Supported values:
                        "integer"   → 1,234
                        "decimal1"  → 12.3
                        "decimal2"  → 12.34
                        "pct"       → 12.3%
    title           Chart title shown at the top.
    subtitle        Sub-heading (zoom hint).
    root_label      Label for the invisible root node.
    output_path     If given, write HTML to this path and return it as well.
    template_path   Path to the HTML template.  If None, uses the default
                    template co-located with this module.

    Returns
    -------
    str  Complete standalone HTML.
    """
    # ── defaults ──────────────────────────────────────────────────────────────
    kpi_cols   = kpi_cols   or [size_col]
    kpi_labels = kpi_labels or {c: c.replace("_", " ").title() for c in kpi_cols}
    kpi_format = kpi_format or {c: "integer" for c in kpi_cols}

    # Ensure size_col is in kpi_cols so the root stats bar shows it
    if size_col not in kpi_cols:
        kpi_cols = [size_col] + kpi_cols
        kpi_labels.setdefault(size_col, size_col.replace("_", " ").title())
        kpi_format.setdefault(size_col, "integer")

    # ── validate ───────────────────────────────────────────────────────────────
    _validate_inputs(df, hierarchy_cols, size_col, kpi_cols)

    # ── build JSON hierarchy ───────────────────────────────────────────────────
    hierarchy_json = _build_hierarchy_json(
        df, hierarchy_cols, size_col, kpi_cols, root_label
    )

    # ── load template ──────────────────────────────────────────────────────────
    html = _load_template(template_path)

    # ── inject data ────────────────────────────────────────────────────────────
    html = _inject_chart_config(html, title, subtitle, size_col, kpi_cols, kpi_labels, kpi_format)
    html = _inject_color_map(html, color_map)
    html = _inject_hierarchy_data(html, hierarchy_json)

    # ── write ──────────────────────────────────────────────────────────────────
    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")
        print(f"✅ Circle packing HTML written → {output_path}")

    return html


# ──────────────────────────────────────────────────────────────────────────────
# HIERARCHY BUILDER
# ──────────────────────────────────────────────────────────────────────────────

def _build_hierarchy_json(
    df:             pd.DataFrame,
    hierarchy_cols: List[str],
    size_col:       str,
    kpi_cols:       List[str],
    root_label:     str,
) -> Dict[str, Any]:
    """
    Recursively build a D3-compatible nested dict from a flat DataFrame.

    At each level the KPI values are aggregated upward as:
      • size_col   → sum
      • other kpis → weighted mean (weight = size_col), rounded to 1dp
    """
    numeric_kpis = [c for c in kpi_cols if c != size_col and pd.api.types.is_numeric_dtype(df[c])]

    def _recurse(sub: pd.DataFrame, depth: int) -> Dict[str, Any]:
        col = hierarchy_cols[depth]
        groups = sub.groupby(col, sort=False)

        children = []
        for name, group in groups.__iter__():
            kpis = _aggregate_kpis(group, size_col, kpi_cols, numeric_kpis)

            if depth < len(hierarchy_cols) - 1:
                node = {
                    "name":     name,
                    "kpis":     kpis,
                    "children": _recurse(group, depth + 1),
                }
            else:
                # Leaf — must have a numeric size value
                node = {
                    "name": name,
                    "kpis": kpis,
                }
            children.append(node)

        # Sort by size descending so largest circles lead
        children.sort(key=lambda n: n["kpis"].get(size_col, 0), reverse=True)
        return children

    root_kpis = _aggregate_kpis(df, size_col, kpi_cols, numeric_kpis)

    return {
        "name":     root_label,
        "kpis":     root_kpis,
        "children": _recurse(df, 0),
    }


def _aggregate_kpis(
    group:        pd.DataFrame,
    size_col:     str,
    kpi_cols:     List[str],
    numeric_kpis: List[str],
) -> Dict[str, Any]:
    """Aggregate KPI values for a group; weighted mean for non-size metrics."""
    kpis: Dict[str, Any] = {}

    total_size = float(group[size_col].sum())
    kpis[size_col] = int(round(total_size))

    weights = group[size_col].values.astype(float)
    for col in numeric_kpis:
        vals = group[col].values.astype(float)
        if total_size > 0:
            wmean = float(np.average(vals, weights=weights))
        else:
            wmean = float(vals.mean()) if len(vals) > 0 else 0.0
        kpis[col] = round(wmean, 2)

    return kpis


# ──────────────────────────────────────────────────────────────────────────────
# TEMPLATE LOADING & INJECTION
# ──────────────────────────────────────────────────────────────────────────────

def _load_template(template_path: Optional[str]) -> str:
    if template_path:
        return Path(template_path).read_text(encoding="utf-8")
    # Default: same directory as this module
    default = Path(__file__).with_name("circle_packing_d3_template.html")
    if default.exists():
        return default.read_text(encoding="utf-8")
    raise FileNotFoundError(
        "No template found.  Pass template_path= or place "
        "circle_packing_d3_template.html next to circle_packing_d3.py"
    )


def _safe_sub(pattern: str, replacement: str, html: str) -> str:
    """re.sub wrapper that avoids backslash interpretation in replacement."""
    return re.sub(pattern, lambda _: replacement, html, flags=re.DOTALL)


def _inject_chart_config(
    html:        str,
    title:       str,
    subtitle:    str,
    size_col:    str,
    kpi_cols:    List[str],
    kpi_labels:  Dict[str, str],
    kpi_format:  Dict[str, str],
) -> str:
    config = {
        "title":       title,
        "subtitle":    subtitle,
        "size_metric": size_col,
        "kpi_cols":    kpi_cols,
        "kpi_labels":  kpi_labels,
        "kpi_format":  kpi_format,
    }
    replacement = (
        "// __CHART_CONFIG_START__\n"
        f"const CHART_CONFIG = {json.dumps(config, indent=4)};\n"
        "// __CHART_CONFIG_END__"
    )
    return _safe_sub(
        r"// __CHART_CONFIG_START__.*?// __CHART_CONFIG_END__",
        replacement, html,
    )


def _inject_color_map(html: str, color_map: Dict[str, Any]) -> str:
    clean_map = {}
    for key, val in color_map.items():
        clean_map[key] = {
            "light":   val.get("light",   "#4f7cff"),
            "dark":    val.get("dark",    "#2a4fc2"),
            "display": val.get("display", key),
            "order":   val.get("order",   999),
        }
    replacement = (
        "// __COLOR_MAP_START__\n"
        f"const COLOR_MAP = {json.dumps(clean_map, indent=4)};\n"
        "// __COLOR_MAP_END__"
    )
    return _safe_sub(
        r"// __COLOR_MAP_START__.*?// __COLOR_MAP_END__",
        replacement, html,
    )


def _inject_hierarchy_data(html: str, hierarchy: Dict[str, Any]) -> str:
    replacement = (
        "// __HIERARCHY_DATA_START__\n"
        f"const HIERARCHY_DATA = {json.dumps(hierarchy, indent=4)};\n"
        "// __HIERARCHY_DATA_END__"
    )
    return _safe_sub(
        r"// __HIERARCHY_DATA_START__.*?// __HIERARCHY_DATA_END__",
        replacement, html,
    )


# ──────────────────────────────────────────────────────────────────────────────
# VALIDATION
# ──────────────────────────────────────────────────────────────────────────────

def _validate_inputs(
    df:             pd.DataFrame,
    hierarchy_cols: List[str],
    size_col:       str,
    kpi_cols:       List[str],
) -> None:
    missing_h = [c for c in hierarchy_cols if c not in df.columns]
    if missing_h:
        raise ValueError(f"hierarchy_cols not found in DataFrame: {missing_h}")

    if size_col not in df.columns:
        raise ValueError(f"size_col '{size_col}' not found in DataFrame")

    if not pd.api.types.is_numeric_dtype(df[size_col]):
        raise ValueError(f"size_col '{size_col}' must be numeric")

    missing_k = [c for c in kpi_cols if c not in df.columns and c != size_col]
    if missing_k:
        raise ValueError(f"kpi_cols not found in DataFrame: {missing_k}")

    if df[hierarchy_cols].isnull().any().any():
        raise ValueError("hierarchy_cols contain null values — please fill or drop them")

    if len(hierarchy_cols) < 1:
        raise ValueError("hierarchy_cols must have at least one entry")


# ──────────────────────────────────────────────────────────────────────────────
# CONVENIENCE: build hierarchy dict directly (no HTML)  — useful for testing
# ──────────────────────────────────────────────────────────────────────────────

def df_to_hierarchy_dict(
    df:             pd.DataFrame,
    hierarchy_cols: List[str],
    size_col:       str,
    kpi_cols:       Optional[List[str]] = None,
    root_label:     str                 = "All",
) -> Dict[str, Any]:
    """
    Convert a DataFrame to a nested dict suitable for D3 circle packing.
    Useful for inspection / unit testing without generating HTML.
    """
    kpi_cols = kpi_cols or [size_col]
    numeric_kpis = [c for c in kpi_cols if c != size_col and pd.api.types.is_numeric_dtype(df[c])]
    return _build_hierarchy_json(df, hierarchy_cols, size_col, kpi_cols, root_label)


# ──────────────────────────────────────────────────────────────────────────────
# DEMO / QUICK TEST
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Run this file directly to generate a demo HTML:
        python circle_packing_d3.py
    """

    # ── Simulated summary DataFrame ────────────────────────────────────────────
    rows = [
        # diagnosis              drug_class         drug            count   age    months  pct_f
        ("Type 2 Diabetes",     "GLP-1 Agonist",   "Ozempic",      8500,   59.8,  21.3,   45.5),
        ("Type 2 Diabetes",     "GLP-1 Agonist",   "Mounjaro",     5700,   60.5,  18.6,   47.2),
        ("Type 2 Diabetes",     "SGLT2 Inhibitor", "Jardiance",    8200,   62.1,  17.2,   48.8),
        ("Type 2 Diabetes",     "SGLT2 Inhibitor", "Forxiga",      4600,   62.9,  16.1,   49.6),
        ("Type 2 Diabetes",     "Beta Blocker",    "Metoprolol",  11420,   61.8,  19.2,   48.0),
        ("Hypertension",        "ACE Inhibitor",   "Lisinopril",  17200,   57.2,  24.1,   51.4),
        ("Hypertension",        "Beta Blocker",    "Metoprolol",  14450,   58.1,  20.3,   53.5),
        ("Heart Failure",       "Beta Blocker",    "Metoprolol",  12300,   67.8,  30.2,   43.2),
        ("Heart Failure",       "ACE Inhibitor",   "Lisinopril",   9880,   66.9,  26.7,   45.3),
        ("COPD",                "Beta Blocker",    "Metoprolol",   8900,   64.1,  32.0,   47.9),
        ("COPD",                "ACE Inhibitor",   "Lisinopril",   6020,   63.4,  30.1,   49.8),
        ("Depression",          "SSRI",            "Sertraline",  10840,   44.2,  11.8,   64.2),
        ("Atrial Fibrillation", "Anticoagulant",   "Apixaban",     6840,   69.1,  35.4,   41.8),
    ]

    demo_df = pd.DataFrame(rows, columns=[
        "diagnosis", "drug_class", "drug",
        "patient_count", "avg_age", "avg_treatment_months", "pct_female"
    ])

    COLOR_MAP = {
        "Type 2 Diabetes":     {"light": "#4f9cf6", "dark": "#2c6fc9", "display": "T2 Diabetes",   "order": 1},
        "Hypertension":        {"light": "#f97b5a", "dark": "#c74e32", "display": "Hypertension",  "order": 2},
        "Heart Failure":       {"light": "#a78bfa", "dark": "#7c5cc4", "display": "Heart Failure", "order": 3},
        "COPD":                {"light": "#34d399", "dark": "#1a9c6e", "display": "COPD",          "order": 4},
        "Depression":          {"light": "#fbbf24", "dark": "#c48e0a", "display": "Depression",    "order": 5},
        "Atrial Fibrillation": {"light": "#f472b6", "dark": "#be4a8a", "display": "AFib",          "order": 6},
        "GLP-1 Agonist":       {"light": "#60adf8", "dark": "#3a83d4", "display": "GLP-1",         "order": 1},
        "SGLT2 Inhibitor":     {"light": "#4ade92", "dark": "#22a865", "display": "SGLT2i",        "order": 2},
        "ACE Inhibitor":       {"light": "#fb8e70", "dark": "#d4613e", "display": "ACEi",          "order": 3},
        "Beta Blocker":        {"light": "#b99cfb", "dark": "#9070d6", "display": "Beta Blocker",  "order": 4},
        "SSRI":                {"light": "#fccf55", "dark": "#d49e1e", "display": "SSRI",          "order": 5},
        "Anticoagulant":       {"light": "#f687c5", "dark": "#c95d9a", "display": "Anticoagulant", "order": 6},
        "Ozempic":             {"light": "#93c5fd", "dark": "#4f9cf6", "display": "Ozempic",       "order": 1},
        "Mounjaro":            {"light": "#6ee7f7", "dark": "#2bb8cf", "display": "Mounjaro",      "order": 2},
        "Jardiance":           {"light": "#6efbbf", "dark": "#1fa86e", "display": "Jardiance",     "order": 3},
        "Forxiga":             {"light": "#86efac", "dark": "#22a865", "display": "Forxiga",       "order": 4},
        "Lisinopril":          {"light": "#fca98a", "dark": "#d4613e", "display": "Lisinopril",    "order": 5},
        "Metoprolol":          {"light": "#c4b5fd", "dark": "#9070d6", "display": "Metoprolol",    "order": 6},
        "Sertraline":          {"light": "#fde68a", "dark": "#d49e1e", "display": "Sertraline",    "order": 7},
        "Apixaban":            {"light": "#fbcfe8", "dark": "#c95d9a", "display": "Apixaban",      "order": 8},
    }

    html = create_circle_packing_html(
        df             = demo_df,
        hierarchy_cols = ["diagnosis", "drug_class", "drug"],
        size_col       = "patient_count",
        kpi_cols       = ["patient_count", "avg_age", "avg_treatment_months", "pct_female"],
        kpi_labels     = {
            "patient_count":          "Patients",
            "avg_age":                "Avg Age",
            "avg_treatment_months":   "Avg Treatment (mo)",
            "pct_female":             "% Female",
        },
        kpi_format     = {
            "patient_count":          "integer",
            "avg_age":                "decimal1",
            "avg_treatment_months":   "decimal1",
            "pct_female":             "pct",
        },
        color_map      = COLOR_MAP,
        title          = "Patient Universe — Diagnosis × Drug",
        root_label     = "All Patients",
        output_path    = "patient_universe_demo.html",
    )

    print(f"\n📊 Demo HTML generated: patient_universe_demo.html")
    print(f"   Rows in DataFrame : {len(demo_df)}")
    print(f"   Hierarchy depth   : 3 (diagnosis → drug_class → drug)")
    print(f"   Total patients    : {demo_df['patient_count'].sum():,}")
