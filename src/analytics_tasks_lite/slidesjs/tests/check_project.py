"""
check_project.py — SlideJS Unified Project Checker
====================================================
Pre-flight validator for a slidejs Excel config file.
Runs four sequential stages before you generate a presentation.

Usage:
    python check_project.py path/to/slidejs_config.xlsm
    python check_project.py path/to/slidejs_config.xlsm --test-id test_1
    python check_project.py path/to/slidejs_config.xlsm --skip-dry-run

Each check is labelled PASS / WARN / FAIL:
  PASS  — requirement met
  WARN  — not required but may cause visual issues
  FAIL  — will break the run or produce incorrect output

Exit code: 0 if no FAILs, 1 if any FAILs found.

Stages:
  1. Excel File & Sheet Integrity     (critical — stops if failed)
  2. Config Values & Consistency      (cross-sheet checks)
  3. Chart File Resolution            (path + inline chart compliance)
  4. Dry Run                          (actual slidejs() call to temp file)
"""

import sys
import re
import tempfile
import traceback
from pathlib import Path

import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# ANSI colours
# ─────────────────────────────────────────────────────────────────────────────
USE_COLOR = sys.stdout.isatty()

def _c(code, text):  return f"\033[{code}m{text}\033[0m" if USE_COLOR else text
def green(t):  return _c("32", t)
def yellow(t): return _c("33", t)
def red(t):    return _c("31", t)
def bold(t):   return _c("1",  t)
def dim(t):    return _c("2",  t)
def cyan(t):   return _c("36", t)

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

def result_line(status, message, detail=None):
    icon  = {PASS: green("✔"), WARN: yellow("⚠"), FAIL: red("✘")}[status]
    label = {PASS: green(f"[{PASS}]"), WARN: yellow(f"[{WARN}]"), FAIL: red(f"[{FAIL}]")}[status]
    line  = f"  {icon} {label}  {message}"
    if detail:
        line += f"\n         {dim(detail)}"
    return line, status

def stage_header(n, title):
    print(f"\n{bold(cyan(f'── Stage {n}: {title} ' + '─' * max(0, 50 - len(title))))}")

def section(title):
    print(f"\n  {dim('▸ ' + title)}")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe(val):
    """Return None if val is NaN/None/empty string, else string."""
    if val is None:
        return None
    if isinstance(val, float) and np.isnan(val):
        return None
    s = str(val).strip()
    return s if s else None

def _is_valid_css_color(value: str) -> bool:
    """
    Lightweight check: is this a recognisable CSS color string?
    Accepts: hex (#xxx, #xxxxxx, #xxxxxxxx), rgb/rgba, hsl/hsla, oklch, named colors.
    """
    v = value.strip().lower()
    if re.match(r'^#[0-9a-f]{3}([0-9a-f]{3}([0-9a-f]{2})?)?$', v):
        return True
    if re.match(r'^(rgb|rgba|hsl|hsla|oklch|oklab|lch|lab|color)\s*\(', v):
        return True
    # Named colors — just check it's alphabetic and reasonably short
    if re.match(r'^[a-z]{2,30}$', v) and v not in ('nan', 'none', 'auto', 'true', 'false'):
        return True
    return False

def _is_valid_css_size(value: str) -> bool:
    """Check if value looks like a CSS font/dimension size."""
    v = value.strip().lower()
    return bool(re.match(r'^\d+(\.\d+)?(px|em|rem|%|pt|vh|vw)$', v))

def _load_excel(excel_path: Path) -> dict | None:
    """Load all sheets from the Excel file. Returns dict or None on failure."""
    try:
        data = {}
        with pd.ExcelFile(excel_path) as xf:
            for sheet in xf.sheet_names:
                data[sheet] = pd.read_excel(xf, sheet_name=sheet, dtype=str)
        return data
    except Exception as e:
        print(red(f"\n  ✘ Cannot load Excel file: {e}"))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — File & Sheet Integrity
# ─────────────────────────────────────────────────────────────────────────────

# Sheets that MUST be present for any run to succeed
REQUIRED_SHEETS = ["Global_Config", "Slide_Config", "Chart_Config"]

# Sheets that are strongly expected — warn if missing
EXPECTED_SHEETS = [
    "Theme_Config", "Font_Config", "Agenda_Config",
    "Summary_Config", "Reference_Config", "Custom_Box_config", "Help",
]

# Minimum required columns per sheet (matches ConfigValidator.REQUIRED_COLUMNS)
REQUIRED_COLUMNS = {
    "Global_Config":    ["Parameter", "Type", "Default Value"],
    "Slide_Config":     ["Test_ID", "Slide_Num", "layout"],
    "Chart_Config":     ["Test_ID", "Slide_Num", "Chart_Pos", "Source_Path"],
    "Theme_Config":     ["Test_ID"],
    "Font_Config":      ["Test_ID"],
    "Summary_Config":   ["Test_ID", "summary_text"],
    "Reference_Config": ["Test_ID", "text", "hyperlink", "group", "group_column_number"],
    "Custom_Box_config":["Test_ID", "Slide_Num", "Box_ID", "Source_Type", "Source_Path", "Top", "Left"],
    "Help":             ["help_text"],
}

VALID_LAYOUTS = ["single", "two-column", "three-column", "grid-2x2"]
LAYOUT_CHART_COUNT = {"single": 1, "two-column": 2, "three-column": 3, "grid-2x2": 4}


def stage1_file_integrity(excel_path: Path) -> tuple[bool, dict | None]:
    """
    Stage 1: file existence, lock file, sheet presence, column structure.
    Returns (critical_ok, loaded_data).
    If critical_ok is False the caller should stop.
    """
    stage_header(1, "Excel File & Sheet Integrity")
    results = []
    data = None

    # ── File checks ──────────────────────────────────────────────────────────
    section("File")

    if not excel_path.exists():
        r = result_line(FAIL, f"File not found: {excel_path}")
        print(r[0])
        print(red("\n  ✘ Cannot continue — file does not exist."))
        return False, None
    results.append(result_line(PASS, f"File exists: {excel_path.name}"))

    if excel_path.name.startswith("~$"):
        results.append(result_line(
            FAIL, "File appears to be a temporary lock file (~$...)",
            "Close the file in Excel and retry"))
    else:
        results.append(result_line(PASS, "File is not a lock file"))

    if excel_path.suffix.lower() not in (".xlsm", ".xlsx"):
        results.append(result_line(
            WARN, f"Unexpected file extension: {excel_path.suffix}",
            "Expected .xlsm or .xlsx"))
    else:
        results.append(result_line(PASS, f"File extension OK: {excel_path.suffix}"))

    for r in results:
        print(r[0])

    # ── Load ─────────────────────────────────────────────────────────────────
    section("Loading sheets")
    data = _load_excel(excel_path)
    if data is None:
        print(red("  ✘ Cannot continue — failed to read Excel file."))
        return False, None

    load_results = []
    load_results.append(result_line(PASS, f"Loaded {len(data)} sheet(s): {list(data.keys())}"))
    for r in load_results:
        print(r[0])

    # ── Required sheets ───────────────────────────────────────────────────────
    section("Required sheets")
    sheet_results = []
    critical_fail = False
    for sheet in REQUIRED_SHEETS:
        if sheet in data:
            sheet_results.append(result_line(PASS, f"Required sheet present: '{sheet}'"))
        else:
            sheet_results.append(result_line(
                FAIL, f"Required sheet MISSING: '{sheet}'",
                "This sheet is mandatory — the run will fail without it"))
            critical_fail = True

    for sheet in EXPECTED_SHEETS:
        if sheet in data:
            sheet_results.append(result_line(PASS, f"Optional sheet present: '{sheet}'"))
        else:
            sheet_results.append(result_line(
                WARN, f"Optional sheet not found: '{sheet}'",
                "Features using this sheet will use defaults or be skipped"))

    for r in sheet_results:
        print(r[0])

    if critical_fail:
        print(red("\n  ✘ Critical sheets missing — stopping Stage 1."))
        return False, data

    # ── Empty sheet check ─────────────────────────────────────────────────────
    section("Sheet row counts")
    for sheet in REQUIRED_SHEETS:
        df = data[sheet]
        if len(df) == 0:
            print(result_line(FAIL, f"'{sheet}' has no data rows (header only)")[0])
            critical_fail = True
        else:
            print(result_line(PASS, f"'{sheet}': {len(df)} data row(s)")[0])

    # ── Column structure ──────────────────────────────────────────────────────
    section("Column structure")
    for sheet, required_cols in REQUIRED_COLUMNS.items():
        if sheet not in data:
            continue
        df = data[sheet]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            print(result_line(
                FAIL, f"'{sheet}' missing columns: {missing}")[0])
            if sheet in REQUIRED_SHEETS:
                critical_fail = True
        else:
            print(result_line(PASS, f"'{sheet}' columns OK")[0])

    if critical_fail:
        print(red("\n  ✘ Critical column errors — stopping here."))
        return False, data

    print(green(f"\n  ✔ Stage 1 passed"))
    return True, data


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Config Values & Cross-Sheet Consistency
# ─────────────────────────────────────────────────────────────────────────────

def _get_global_param(data: dict, param: str) -> str | None:
    """Read a parameter value from Global_Config by Parameter name."""
    df = data.get("Global_Config")
    if df is None or "Parameter" not in df.columns:
        return None
    match = df[df["Parameter"].astype(str).str.strip() == param]
    if len(match) == 0:
        return None
    # Value lives in the column named 'Value' or 'Default Value'
    for col in ["Value", "Default Value"]:
        if col in match.columns:
            val = _safe(match.iloc[0][col])
            if val:
                return val
    return None


def stage2_config_values(data: dict, test_id: str) -> bool:
    """
    Stage 2: Global_Config mandatory fields, output path, Test_ID cross-sheet
    consistency, Theme/Font values, layout-chart-count match, Agenda references.
    Returns True if no FAILs.
    """
    stage_header(2, "Config Values & Cross-Sheet Consistency")
    fail_count = 0

    # ── Global_Config mandatory fields ────────────────────────────────────────
    section("Global_Config mandatory fields")
    mandatory_params = ["page_title", "company_name", "output_file"]
    for param in mandatory_params:
        val = _get_global_param(data, param)
        if val:
            print(result_line(PASS, f"{param} = '{val[:80]}'")[0])
        else:
            print(result_line(FAIL, f"Global_Config: '{param}' is missing or empty")[0])
            fail_count += 1

    # ── Output file directory ─────────────────────────────────────────────────
    section("Output path")
    output_file = _get_global_param(data, "output_file")
    if output_file:
        out_path = Path(output_file)
        if not out_path.parent.exists():
            print(result_line(
                FAIL, f"Output directory does not exist: {out_path.parent}",
                "Create the directory or fix the output_file path in Global_Config")[0])
            fail_count += 1
        else:
            print(result_line(PASS, f"Output directory exists: {out_path.parent}")[0])
        if out_path.suffix.lower() != ".html":
            print(result_line(
                WARN, f"Output file extension is '{out_path.suffix}' — expected .html")[0])
        else:
            print(result_line(PASS, f"Output file: {out_path.name}")[0])

    # ── Test_ID cross-sheet consistency ───────────────────────────────────────
    section(f"Test_ID '{test_id}' present across sheets")
    sheets_with_test_id = [
        "Slide_Config", "Chart_Config", "Theme_Config",
        "Font_Config", "Agenda_Config", "Summary_Config",
    ]
    for sheet in sheets_with_test_id:
        if sheet not in data:
            continue
        df = data[sheet]
        if "Test_ID" not in df.columns:
            continue
        ids_in_sheet = set(df["Test_ID"].astype(str).str.strip().unique())
        if test_id in ids_in_sheet:
            print(result_line(PASS, f"Test_ID found in '{sheet}'")[0])
        else:
            severity = FAIL if sheet in ("Slide_Config", "Chart_Config") else WARN
            print(result_line(
                severity,
                f"Test_ID '{test_id}' not found in '{sheet}'",
                f"Sheet contains: {sorted(ids_in_sheet)[:5]}")[0])
            if severity == FAIL:
                fail_count += 1

    # ── Theme_Config: light + dark rows ───────────────────────────────────────
    section("Theme_Config light/dark rows")
    if "Theme_Config" in data:
        df = data["Theme_Config"]
        if "Theme_Name" in df.columns and "Test_ID" in df.columns:
            test_rows = df[df["Test_ID"].astype(str).str.strip() == test_id]
            theme_names = set(test_rows["Theme_Name"].astype(str).str.strip().str.lower())
            for mode in ("light", "dark"):
                if mode in theme_names:
                    print(result_line(PASS, f"Theme_Config has '{mode}' row")[0])
                else:
                    print(result_line(
                        WARN, f"Theme_Config missing '{mode}' row",
                        "Dark/light mode toggle may use defaults")[0])
        else:
            print(result_line(
                WARN, "Theme_Config does not have 'Theme_Name' column — single-row theme assumed")[0])

    # ── Theme_Config: color value format ─────────────────────────────────────
    section("Theme_Config color values")
    if "Theme_Config" in data:
        df = data["Theme_Config"]
        color_cols = [
            "primary", "text", "muted", "light", "content_bg", "slide_bg",
            "header_border", "bg_dark", "bg", "bg_light", "text_muted",
            "highlight", "border", "border_muted", "secondary",
            "danger", "warning", "success", "info",
        ]
        existing_color_cols = [c for c in color_cols if c in df.columns]
        bad_values = []
        for _, row in df.iterrows():
            for col in existing_color_cols:
                val = _safe(row.get(col))
                if val and not _is_valid_css_color(val):
                    bad_values.append(f"{col}='{val}'")
        if bad_values:
            print(result_line(
                WARN, f"Possible invalid CSS color values: {bad_values[:5]}",
                "Check these values render correctly in the browser")[0])
        else:
            print(result_line(PASS, f"Color values checked ({len(existing_color_cols)} columns)")[0])

    # ── Font_Config: size format ───────────────────────────────────────────────
    section("Font_Config size values")
    if "Font_Config" in data:
        df = data["Font_Config"]
        font_cols = ["title", "subtitle", "body", "overlay", "footnote",
                     "footer", "agenda_group_heading", "agenda_item",
                     "index_group_heading", "index_item"]
        existing_font_cols = [c for c in font_cols if c in df.columns]
        bad_fonts = []
        for _, row in df.iterrows():
            for col in existing_font_cols:
                val = _safe(row.get(col))
                if val and not _is_valid_css_size(val):
                    bad_fonts.append(f"{col}='{val}'")
        if bad_fonts:
            print(result_line(
                WARN, f"Possible invalid CSS font sizes: {bad_fonts[:5]}",
                "Expected format: 14px, 1.2em, 120%, etc.")[0])
        else:
            if existing_font_cols:
                print(result_line(PASS, f"Font size values checked ({len(existing_font_cols)} columns)")[0])
            else:
                print(result_line(WARN, "No recognised font columns found in Font_Config")[0])

    # ── Slide layout values ───────────────────────────────────────────────────
    section("Slide_Config layout values")
    if "Slide_Config" in data:
        df = data["Slide_Config"]
        test_slides = df[df["Test_ID"].astype(str).str.strip() == test_id]
        invalid_layouts = []
        for _, row in test_slides.iterrows():
            layout = _safe(row.get("layout"))
            if layout and layout not in VALID_LAYOUTS:
                invalid_layouts.append(f"Slide {row.get('Slide_Num')}: '{layout}'")
        if invalid_layouts:
            print(result_line(
                FAIL, f"Invalid layout values: {invalid_layouts}",
                f"Valid layouts: {VALID_LAYOUTS}")[0])
            fail_count += 1
        else:
            print(result_line(PASS, f"{len(test_slides)} slides, all layouts valid")[0])

    # ── Layout ↔ chart count match ────────────────────────────────────────────
    section("Layout vs chart count per slide")
    if "Slide_Config" in data and "Chart_Config" in data:
        slide_df = data["Slide_Config"]
        chart_df = data["Chart_Config"]
        test_slides = slide_df[slide_df["Test_ID"].astype(str).str.strip() == test_id]
        test_charts = chart_df[chart_df["Test_ID"].astype(str).str.strip() == test_id]

        for _, slide_row in test_slides.iterrows():
            slide_num = _safe(slide_row.get("Slide_Num"))
            layout    = _safe(slide_row.get("layout"))
            if not layout or layout not in LAYOUT_CHART_COUNT:
                continue
            expected = LAYOUT_CHART_COUNT[layout]
            actual = len(test_charts[
                test_charts["Slide_Num"].astype(str).str.strip() == str(slide_num)
            ])
            if actual < expected:
                print(result_line(
                    FAIL,
                    f"Slide {slide_num} ({layout}): needs {expected} chart(s), found {actual}",
                    "Add the missing chart rows to Chart_Config")[0])
                fail_count += 1
            elif actual > expected:
                print(result_line(
                    WARN,
                    f"Slide {slide_num} ({layout}): has {actual} charts, layout uses {expected}",
                    "Extra charts will be ignored")[0])
            else:
                print(result_line(PASS, f"Slide {slide_num} ({layout}): {actual}/{expected} charts")[0])

    # ── Agenda_Config slide references ────────────────────────────────────────
    section("Agenda_Config slide references")
    if "Agenda_Config" in data and "Slide_Config" in data:
        agenda_df = data["Agenda_Config"]
        slide_df  = data["Slide_Config"]
        valid_slides = set(
            slide_df[slide_df["Test_ID"].astype(str).str.strip() == test_id]["Slide_Num"]
            .astype(str).str.strip()
        )
        if "Test_ID" in agenda_df.columns:
            test_agenda = agenda_df[agenda_df["Test_ID"].astype(str).str.strip() == test_id]
        else:
            test_agenda = agenda_df
        bad_refs = []
        for _, row in test_agenda.iterrows():
            sn = _safe(row.get("Slide_Num"))
            if sn and sn not in valid_slides:
                bad_refs.append(sn)
        if bad_refs:
            print(result_line(
                WARN, f"Agenda_Config references non-existent slides: {bad_refs}",
                "Agenda links to these slides will be broken")[0])
        else:
            print(result_line(PASS, "All Agenda slide references are valid")[0])
    elif "Agenda_Config" not in data:
        print(result_line(WARN, "Agenda_Config not present — skipped")[0])

    # ── Custom_Box_config: duplicate Box_IDs ──────────────────────────────────
    section("Custom_Box_config duplicate Box_IDs")
    if "Custom_Box_config" in data:
        cb_df = data["Custom_Box_config"]
        if "Test_ID" in cb_df.columns:
            test_cb = cb_df[cb_df["Test_ID"].astype(str).str.strip() == test_id]
            if "Slide_Num" in test_cb.columns and "Box_ID" in test_cb.columns:
                for sn, grp in test_cb.groupby("Slide_Num"):
                    dupes = grp["Box_ID"][grp["Box_ID"].duplicated()].tolist()
                    if dupes:
                        print(result_line(
                            FAIL, f"Slide {sn}: duplicate Box_IDs: {dupes}")[0])
                        fail_count += 1
                if fail_count == 0:
                    print(result_line(PASS, "No duplicate Box_IDs found")[0])

    ok = fail_count == 0
    if ok:
        print(green(f"\n  ✔ Stage 2 passed"))
    else:
        print(red(f"\n  ✘ Stage 2: {fail_count} failure(s)"))
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — Chart File Resolution + Inline Compliance
# ─────────────────────────────────────────────────────────────────────────────

# Inline chart checks (adapted from check_chart.py, without subprocess dependency)

def _chart_check_container(script):
    known = {"container", "chart", "main"}
    found = []
    for pat in [
        r"""getElementById\s*\(\s*['"](\w+)['"]\s*\)""",
        r"""querySelector\s*\(\s*['"]#(\w+)['"]\s*\)""",
        r"""d3\.select\s*\(\s*['"]#(\w+)['"]\s*\)""",
    ]:
        found += re.findall(pat, script)
    found = list(dict.fromkeys(found))
    recognised = [f for f in found if f in known]
    unknown = [f for f in found if f not in known and f != "customTooltip"]
    if recognised:
        return result_line(PASS, f"Container ID: {recognised[0]!r}")
    elif unknown:
        return result_line(FAIL, f"Unrecognised container ID(s): {unknown}",
            "slidejs remaps 'container', 'chart', or 'main'")
    return result_line(WARN, "No container ID found (may be expected for D3/SVG charts)")

def _chart_check_set_chart_theme(script):
    if "window.setChartTheme" in script:
        return result_line(PASS, "window.setChartTheme defined")
    return result_line(FAIL, "window.setChartTheme not defined",
        "Theme toggle will silently skip this chart")

def _chart_check_get_option(script):
    match = re.search(r'window\.setChartTheme\s*=\s*function\b(.+)', script, re.DOTALL)
    if not match:
        return result_line(WARN, "setChartTheme not found — skipping getOption() check")
    if "myChart.getOption()" in match.group(1):
        return result_line(FAIL, "myChart.getOption() inside setChartTheme",
            "ECharts strips _darkColor/_lightColor on getOption(). Use _themeColors instead")
    return result_line(PASS, "No myChart.getOption() inside setChartTheme")

def _chart_check_theme_pattern(script):
    has_get_option  = "myChart.getOption()" in script
    has_theme_colors = "_themeColors" in script or "_themeUI" in script
    if has_theme_colors:
        return result_line(PASS, "_themeColors/_themeUI pattern in use (robust)")
    if has_get_option:
        return result_line(FAIL, "Uses myChart.getOption() — fragile theme pattern",
            "Replace with pre-baked _themeColors / _themeUI dicts")
    return result_line(WARN, "No explicit theme-color pattern detected",
        "Verify setChartTheme switches all colors correctly")

def _chart_check_brace_balance(script):
    opens, closes = script.count("{"), script.count("}")
    if opens == closes:
        return result_line(PASS, f"Braces balanced ({opens}/{closes})")
    excess = "opening" if opens > closes else "closing"
    return result_line(FAIL, f"Unbalanced braces: {opens} open, {closes} close",
        f"{abs(opens-closes)} extra {excess} brace(s) — will cause JS syntax error")

def _chart_check_echarts_cdn(html):
    if "echarts" in html.lower():
        if re.search(r'<script[^>]+src=["\'][^"\']*echarts[^"\']*["\']', html, re.IGNORECASE):
            return result_line(PASS, "ECharts CDN <script> tag found")
        return result_line(WARN, "ECharts referenced but no CDN <script src> tag",
            "Without the tag echarts will not load")
    return result_line(PASS, "Not an ECharts chart — CDN check skipped")

def _run_chart_compliance(html_path: Path, slide_num, chart_pos) -> tuple[int, int]:
    """
    Run inline chart compliance checks on a single chart file.
    Returns (fail_count, warn_count).
    """
    context = f"Slide {slide_num}, Pos {chart_pos}: {html_path.name}"
    print(f"\n    {dim('Chart: ' + context)}")

    try:
        html = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(result_line(FAIL, f"Cannot read chart file: {e}")[0])
        return 1, 0

    script_blocks = re.findall(
        r'<script(?!\s+src)[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE
    )
    script = "\n".join(script_blocks)

    if not script.strip():
        print(f"    {result_line(WARN, 'No inline script — possibly a pure image/SVG chart')[0]}")
        return 0, 1

    checks = [
        _chart_check_container(script),
        _chart_check_set_chart_theme(script),
        _chart_check_get_option(script),
        _chart_check_theme_pattern(script),
        _chart_check_brace_balance(script),
        _chart_check_echarts_cdn(html),
    ]

    fail_count = warn_count = 0
    for line, status in checks:
        print(f"    {line}")
        if status == FAIL: fail_count += 1
        if status == WARN: warn_count += 1

    return fail_count, warn_count


def stage3_chart_files(data: dict, test_id: str) -> bool:
    """
    Stage 3: verify every chart path exists, is an HTML file, is non-empty,
    then run inline compliance checks.
    Returns True if no FAILs.
    """
    stage_header(3, "Chart File Resolution & Compliance")
    fail_count = 0

    if "Chart_Config" not in data:
        print(result_line(WARN, "Chart_Config not found — skipping")[0])
        return True

    df = data["Chart_Config"]
    test_charts = df[df["Test_ID"].astype(str).str.strip() == test_id]

    if len(test_charts) == 0:
        print(result_line(WARN, f"No charts found for Test_ID '{test_id}'")[0])
        return True

    total_charts = len(test_charts)
    html_charts  = []

    section(f"Path existence ({total_charts} chart entries)")

    for _, row in test_charts.iterrows():
        slide_num  = _safe(row.get("Slide_Num"))  or "?"
        chart_pos  = _safe(row.get("Chart_Pos"))  or "?"
        source     = _safe(row.get("Source_Path"))

        if not source:
            print(result_line(
                FAIL, f"Slide {slide_num} Pos {chart_pos}: Source_Path is empty")[0])
            fail_count += 1
            continue

        # TEXT: inline content — skip file checks
        if source.upper().startswith("TEXT:"):
            print(result_line(
                PASS, f"Slide {slide_num} Pos {chart_pos}: inline TEXT content")[0])
            continue

        p = Path(source)

        # Extension check
        if p.suffix.lower() not in (".html", ".png", ".jpg", ".jpeg", ".gif", ".svg"):
            print(result_line(
                WARN,
                f"Slide {slide_num} Pos {chart_pos}: unexpected extension '{p.suffix}'",
                f"Path: {source}")[0])

        # Existence
        if not p.exists():
            print(result_line(
                FAIL,
                f"Slide {slide_num} Pos {chart_pos}: file not found",
                str(source))[0])
            fail_count += 1
            continue

        # Non-empty
        if p.stat().st_size == 0:
            print(result_line(
                FAIL,
                f"Slide {slide_num} Pos {chart_pos}: file is empty (0 bytes)",
                str(source))[0])
            fail_count += 1
            continue

        print(result_line(PASS, f"Slide {slide_num} Pos {chart_pos}: {p.name} ({p.stat().st_size:,} bytes)")[0])

        if p.suffix.lower() == ".html":
            html_charts.append((p, slide_num, chart_pos))

    # ── Inline compliance checks ──────────────────────────────────────────────
    if html_charts:
        section(f"Chart compliance ({len(html_charts)} HTML charts)")
        for html_path, slide_num, chart_pos in html_charts:
            fc, wc = _run_chart_compliance(html_path, slide_num, chart_pos)
            fail_count += fc

    ok = fail_count == 0
    if ok:
        print(green(f"\n  ✔ Stage 3 passed"))
    else:
        print(red(f"\n  ✘ Stage 3: {fail_count} failure(s)"))
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 — Dry Run
# ─────────────────────────────────────────────────────────────────────────────

def _import_run_test():
    """
    Try to import run_test from the package, then fall back to a direct
    file-based import walking up from this script's location.
    Returns the callable or raises ImportError.
    """
    # 1. Package import (normal installed usage)
    try:
        from analytics_tasks.slidesjs.slidejs_excel_runner import run_test
        return run_test, "analytics_tasks.slidesjs"
    except ImportError:
        pass

    # 2. Direct file import — walk up from this script looking for the runner
    import importlib.util
    here = Path(__file__).resolve().parent
    for candidate in [here, here.parent, here.parent.parent]:
        runner_file = candidate / "slidejs_excel_runner.py"
        if runner_file.exists():
            spec = importlib.util.spec_from_file_location("slidejs_excel_runner", runner_file)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.run_test, str(runner_file)

    raise ImportError("Cannot find slidejs_excel_runner.py — run from inside the package")


def stage4_dry_run(excel_path: Path, test_id: str) -> bool:
    """
    Stage 4: call run_test with a temp output_dir so the real output_file
    in Global_Config is never touched. Validates the produced HTML, then
    cleans up the temp dir.
    Returns True if no FAILs.
    """
    stage_header(4, "Dry Run")
    section("Importing slidejs runner")

    try:
        run_test, source = _import_run_test()
        print(result_line(PASS, f"Imported run_test from: {source}")[0])
    except Exception as e:
        print(result_line(FAIL, f"Import failed: {e}",
            "Ensure the package is installed or run from the project root")[0])
        return False

    # ── run_test into a temp directory ────────────────────────────────────────
    # run_test(test_id, excel_file) reads output_file from Global_Config.
    # Passing output_dir redirects the write to that directory while keeping
    # the original filename — so Global_Config is never modified.
    section("Running slidejs into temp directory")

    import io, contextlib

    tmp_dir = None
    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="slidejs_dryrun_"))
        print(dim(f"    Temp dir: {tmp_dir}"))

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = run_test(
                test_id=test_id,
                excel_file=excel_path,
                output_dir=tmp_dir,          # redirects output without touching Global_Config
            )

        runner_output = buf.getvalue()

        # ── Interpret result ──────────────────────────────────────────────────
        # run_test returns a dict: {"status": "PASS"|"FAIL", "output_file": ..., "error": ...}
        if not isinstance(result, dict):
            print(result_line(FAIL, f"run_test returned unexpected type: {type(result).__name__}")[0])
            return False

        status = result.get("status", "")
        if status != "PASS":
            error = result.get("error", "unknown error")
            print(result_line(FAIL, f"run_test returned status='{status}': {error}")[0])
            # Surface the most useful lines from suppressed runner output
            for line in runner_output.splitlines():
                if any(kw in line for kw in ("❌", "Error", "Traceback", "raise", "Exception")):
                    print(f"    {dim(line)}")
            return False

        print(result_line(PASS, f"run_test completed: status=PASS")[0])

        # ── Find the output file ──────────────────────────────────────────────
        out_path_str = result.get("output_file")
        if out_path_str:
            out_path = Path(out_path_str)
        else:
            # Fallback: find any .html in the temp dir
            html_files = list(tmp_dir.glob("*.html"))
            if not html_files:
                print(result_line(FAIL, "No HTML file found in temp output directory")[0])
                return False
            out_path = html_files[0]

        # ── Validate HTML output ──────────────────────────────────────────────
        section("Validating HTML output")

        if not out_path.exists():
            print(result_line(FAIL, f"Output file not found: {out_path}")[0])
            return False

        size = out_path.stat().st_size
        if size == 0:
            print(result_line(FAIL, "Output HTML is empty (0 bytes)")[0])
            return False
        print(result_line(PASS, f"Output file: {out_path.name} ({size:,} bytes)")[0])

        html = out_path.read_text(encoding="utf-8", errors="replace")

        markers = [
            ("<!doctype html" in html.lower() or "<html" in html.lower(),
             "Valid HTML document structure"),
            ('<div class="slide' in html,
             "Slide <div> elements present"),
            ("--color-primary" in html,
             "CSS theme variables injected"),
            ("body.dark-mode" in html,
             "Dark mode CSS present"),
            ("window.toggleTheme" in html,
             "Theme toggle JS present"),
            ("window.syncAllChartsTheme" in html,
             "Chart theme sync JS present"),
        ]

        for passed, description in markers:
            print(result_line(PASS if passed else WARN, description)[0])

        print(result_line(PASS, "Dry run complete — HTML output looks valid")[0])

        slides_count = result.get("slides_count", 0)
        charts_count = result.get("charts_count", 0)
        duration     = result.get("duration_seconds", 0)
        print(dim(f"\n    {slides_count} slides · {charts_count} charts · {duration:.1f}s"))

        return True

    except Exception as e:
        print(result_line(FAIL, f"Dry run exception: {type(e).__name__}: {e}")[0])
        print(f"\n{dim(traceback.format_exc())}")
        return False

    finally:
        if tmp_dir and tmp_dir.exists():
            import shutil
            try:
                shutil.rmtree(tmp_dir)
                print(dim("    Temp directory cleaned up"))
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="SlideJS unified pre-flight project checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("excel_file", help="Path to slidejs .xlsm config file")
    parser.add_argument(
        "--test-id", "-t", default=None,
        help="Test ID to validate (default: auto-detect from Slide_Config)"
    )
    parser.add_argument(
        "--skip-dry-run", action="store_true",
        help="Skip Stage 4 (dry run) — useful for quick structural checks"
    )
    args = parser.parse_args()

    excel_path = Path(args.excel_file)

    print(bold("\n" + "═" * 62))
    print(bold("  SlideJS Project Checker"))
    print(bold("═" * 62))
    print(dim(f"  File: {excel_path}"))

    # ── Stage 1 ───────────────────────────────────────────────────────────────
    ok1, data = stage1_file_integrity(excel_path)
    if not ok1:
        print(red("\n✘ Stopped at Stage 1 — fix critical errors before continuing."))
        sys.exit(1)

    # ── Resolve test_id ───────────────────────────────────────────────────────
    if args.test_id:
        test_id = args.test_id
    else:
        # Auto-detect: take the first (and typically only) Test_ID from Slide_Config
        slide_df = data.get("Slide_Config", pd.DataFrame())
        ids = slide_df["Test_ID"].dropna().astype(str).str.strip().unique() \
              if "Test_ID" in slide_df.columns else []
        if len(ids) == 0:
            print(red("\n✘ No Test_ID found in Slide_Config — cannot continue."))
            sys.exit(1)
        test_id = ids[0]
        if len(ids) > 1:
            print(yellow(f"\n  ⚠ Multiple Test_IDs found: {list(ids)} — using '{test_id}'"))
            print(yellow("    Use --test-id to specify one explicitly."))
        else:
            print(dim(f"\n  Auto-detected Test_ID: '{test_id}'"))

    # ── Stage 2 ───────────────────────────────────────────────────────────────
    ok2 = stage2_config_values(data, test_id)

    # ── Stage 3 ───────────────────────────────────────────────────────────────
    ok3 = stage3_chart_files(data, test_id)

    # ── Stage 4 ───────────────────────────────────────────────────────────────
    ok4 = True
    if not args.skip_dry_run:
        ok4 = stage4_dry_run(excel_path, test_id)
    else:
        stage_header(4, "Dry Run")
        print(yellow("  ⚠ Skipped (--skip-dry-run)"))

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"\n{bold('═' * 62)}")
    print(bold("  SUMMARY"))
    print(bold("═" * 62))

    stages = [
        ("Stage 1: File & Sheet Integrity",    ok1),
        ("Stage 2: Config Values",              ok2),
        ("Stage 3: Chart Files & Compliance",   ok3),
        ("Stage 4: Dry Run",                    ok4 if not args.skip_dry_run else None),
    ]

    all_ok = True
    for name, passed in stages:
        if passed is None:
            print(f"  {yellow('⚠')}  {name:<45} {yellow('SKIPPED')}")
        elif passed:
            print(f"  {green('✔')}  {name:<45} {green('PASS')}")
        else:
            print(f"  {red('✘')}  {name:<45} {red('FAIL')}")
            all_ok = False

    print()
    if all_ok:
        print(green(bold("  ✔  ALL STAGES PASSED — safe to generate presentation")))
    else:
        print(red(bold("  ✘  FAILURES FOUND — fix issues above before generating")))
    print()

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
