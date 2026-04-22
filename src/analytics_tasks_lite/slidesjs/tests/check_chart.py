"""
check_chart.py — SlideJS Chart Compliance Checker
===================================================
Validates that a chart HTML file is compatible with the SlideJS pipeline
BEFORE you embed it in a presentation.

Usage:
    python check_chart.py chart.html
    python check_chart.py chart1.html chart2.html chart3.html
    python check_chart.py charts/          ← checks all .html files in a folder

Each check is labelled PASS / WARN / FAIL:
  PASS  — requirement met
  WARN  — not required but recommended (won't break slidejs, but may look wrong)
  FAIL  — will break slidejs or theme toggle

Exit code: 0 if all charts pass (no FAILs), 1 if any chart has FAILs.
"""

import sys
import re
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# ANSI colours (disabled automatically when output is piped)
# ─────────────────────────────────────────────────────────────
USE_COLOR = sys.stdout.isatty()


def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def green(t):
    return _c("32", t)


def yellow(t):
    return _c("33", t)


def red(t):
    return _c("31", t)


def bold(t):
    return _c("1", t)


def dim(t):
    return _c("2", t)


# ─────────────────────────────────────────────────────────────
# Result helpers
# ─────────────────────────────────────────────────────────────
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


def result_line(status, message, detail=None):
    icon = {PASS: green("✔"), WARN: yellow("⚠"), FAIL: red("✘")}[status]
    label = {
        PASS: green(f"[{PASS}]"),
        WARN: yellow(f"[{WARN}]"),
        FAIL: red(f"[{FAIL}]"),
    }[status]
    line = f"  {icon} {label}  {message}"
    if detail:
        line += f"\n         {dim(detail)}"
    return line, status


# ─────────────────────────────────────────────────────────────
# Individual checks
# ─────────────────────────────────────────────────────────────


def check_container_id(script: str):
    """Chart must use a recognised container ID that slidejs will remap."""
    known = ["container", "chart", "main"]
    patterns = [
        r"""getElementById\s*\(\s*['"](\w+)['"]\s*\)""",
        r"""querySelector\s*\(\s*['"]#(\w+)['"]\s*\)""",
        r"""d3\.select\s*\(\s*['"]#(\w+)['"]\s*\)""",
    ]
    found = []
    for pat in patterns:
        found += re.findall(pat, script)
    found = list(dict.fromkeys(found))  # deduplicate, preserve order

    recognised = [f for f in found if f in known]
    unknown = [
        f for f in found if f not in known and f not in ("customTooltip",)
    ]  # customTooltip is handled separately

    if recognised:
        return result_line(
            PASS,
            f"Container ID recognised: {recognised[0]!r}",
            "slidejs will remap to a namespaced ID at embed time",
        )
    elif found:
        return result_line(
            FAIL,
            f"Unrecognised container ID(s): {unknown}",
            "slidejs remaps 'container', 'chart', or 'main' — rename your div/getElementById call",
        )
    else:
        return result_line(
            WARN,
            "No container ID found (getElementById / querySelector / d3.select)",
            "If this is not an ECharts chart, this may be expected",
        )


def check_set_option(script: str):
    """myChart.setOption() must be called to initialise the chart."""
    if re.search(r"myChart\.setOption\s*\(", script):
        return result_line(PASS, "myChart.setOption() call found")
    return result_line(
        FAIL,
        "No myChart.setOption() call found",
        "The chart will never render — ensure your option object is passed to setOption()",
    )


def check_set_chart_theme(script: str):
    """window.setChartTheme must be defined for theme toggle to work."""
    if "window.setChartTheme" in script:
        return result_line(PASS, "window.setChartTheme defined")
    return result_line(
        FAIL,
        "window.setChartTheme is not defined",
        "Add:  window.setChartTheme = function(isDark) { ... }  — see slidejs_chart_template.html",
    )


def check_theme_colours(script: str):
    """
    setChartTheme should update colours via _themeColors / _themeUI
    (the robust pattern), not via myChart.getOption() (the fragile pattern).
    """
    has_get_option = "myChart.getOption()" in script
    has_theme_colors = "_themeColors" in script
    has_theme_ui = "_themeUI" in script

    if has_theme_colors and has_theme_ui:
        return result_line(PASS, "_themeColors and _themeUI pattern in use (robust)")
    elif has_get_option:
        return result_line(
            FAIL,
            "setChartTheme uses myChart.getOption() — this will break after slidejs transforms",
            "ECharts strips custom fields (_darkColor etc) on getOption(). "
            "Use _themeColors / _themeUI pre-baked dicts instead",
        )
    else:
        return result_line(
            WARN,
            "Neither _themeColors/_themeUI nor myChart.getOption() detected",
            "If setChartTheme doesn't switch series/label colours, check your theme implementation",
        )


def check_theme_ui_keys(script: str):
    """_themeUI should contain both 'light' and 'dark' keys."""
    if "_themeUI" not in script:
        return result_line(
            WARN,
            "_themeUI not present — skipping key check",
            "Expected if chart has no theme-aware UI elements (axes, legend, tooltip)",
        )

    has_light = re.search(r'["\']light["\']\s*:', script)
    has_dark = re.search(r'["\']dark["\']\s*:', script)

    if has_light and has_dark:
        return result_line(PASS, "_themeUI has both 'light' and 'dark' keys")
    missing = []
    if not has_light:
        missing.append("'light'")
    if not has_dark:
        missing.append("'dark'")
    return result_line(
        FAIL,
        f"_themeUI is missing keys: {', '.join(missing)}",
        "Both light and dark must be defined or the toggle will crash at runtime",
    )


def check_no_get_option_in_theme(script: str):
    """
    getOption() inside setChartTheme is the #1 cause of theme failures.
    Check specifically inside the setChartTheme function body.
    """
    # Extract everything after window.setChartTheme = function
    match = re.search(r"window\.setChartTheme\s*=\s*function\b(.+)", script, re.DOTALL)
    if not match:
        return result_line(WARN, "setChartTheme not found — skipping getOption() check")

    theme_body = match.group(1)
    if "myChart.getOption()" in theme_body:
        return result_line(
            FAIL,
            "myChart.getOption() inside setChartTheme body",
            "This is the #1 theme bug. ECharts normalises option on getOption(), "
            "stripping _darkColor/_lightColor. Replace with pre-baked _themeColors / _themeUI",
        )
    return result_line(PASS, "No myChart.getOption() inside setChartTheme")


def check_resize_handler(script: str):
    """
    window.addEventListener('resize') will be STRIPPED by slidejs.
    This is expected — just warn so the developer knows.
    """
    has_resize = (
        "window.addEventListener('resize'" in script
        or 'window.addEventListener("resize"' in script
    )
    if has_resize:
        return result_line(
            WARN,
            "window.addEventListener('resize') found",
            "slidejs strips this automatically — chart resizing is handled by the presentation. "
            "This is fine; just confirm the chart works without it",
        )
    return result_line(
        PASS, "No resize handler (not required — slidejs handles resize)"
    )


def check_brace_balance(script: str):
    """JS braces must be balanced or the chart will fail to parse."""
    opens = script.count("{")
    closes = script.count("}")
    if opens == closes:
        return result_line(PASS, f"Braces balanced ({opens} open, {closes} close)")
    diff = abs(opens - closes)
    excess = "opening" if opens > closes else "closing"
    return result_line(
        FAIL,
        f"Unbalanced braces: {opens} open, {closes} close ({diff} extra {excess})",
        "This WILL cause a JS syntax error when embedded — check for missing/extra {{ }}",
    )


def check_no_fstring_set_literal(raw_python_source: str | None):
    """
    Detect {{ }} inside f-string expressions in Python chart builders.
    Only runs if the .py source file is supplied alongside the HTML.
    Pattern: f"...{some_expr: {{ ... }} }..." — the {{ }} inside an expression
    creates a set literal instead of a dict, causing TypeError at build time.
    """
    if not raw_python_source:
        return None  # skip — no Python source available

    # Look for f-string lines that contain {expr: {{ something }} }
    # Heuristic: line that is inside an f-string AND contains {{ at least once
    # alongside a json.dumps or similar call
    bad_lines = []
    in_fstring = False
    for i, line in enumerate(raw_python_source.splitlines(), 1):
        # Very simple heuristic — look for json.dumps({  followed by {{ on same line
        if re.search(r"json\.dumps\s*\(\s*\{[^}]*\{\{", line):
            bad_lines.append((i, line.strip()))

    if bad_lines:
        detail = "; ".join(f"line {ln}: {txt[:60]}" for ln, txt in bad_lines[:3])
        return result_line(
            FAIL,
            "Possible {{ }} set-literal bug inside f-string json.dumps()",
            f"Found: {detail} — pre-build the dict as a Python variable first",
        )
    return result_line(
        PASS, "No f-string {{ }} set-literal pattern detected in Python source"
    )


def check_series_color_meta(script: str):
    """
    Series with _lightColor/_darkColor should use _themeColors pattern,
    not rely on the old _seriesColorMeta injection from slidejs.py.
    """
    has_old_pattern = "_lightColor" in script or "_darkColor" in script
    has_new_pattern = "_themeColors" in script

    if has_old_pattern and not has_new_pattern:
        return result_line(
            WARN,
            "Series use _lightColor/_darkColor but no _themeColors dict",
            "slidejs injects a _seriesColorMeta snapshot as a fallback, but this is fragile. "
            "Consider migrating to the _themeColors pre-baked pattern",
        )
    if has_new_pattern:
        return result_line(PASS, "_themeColors pattern in use for series colours")
    return result_line(
        PASS, "No series colour metadata (not required for non-series-colour charts)"
    )


def check_css_sizing(html: str):
    """
    html/body must not carry min-height constraints, and should declare
    background:transparent + overflow:hidden so the chart respects the
    dimensions slidejs assigns to the embed container.

    Specifically catches the pattern that causes bar charts (and similar)
    to retain their own viewport-based size instead of fitting the slide slot:
      - min-height: 100vh  on html, body, or #main  → FAIL
      - background not set to transparent            → WARN
      - overflow: hidden missing                     → WARN
    """
    style_blocks = re.findall(
        r"<style[^>]*>(.*?)</style>", html, re.DOTALL | re.IGNORECASE
    )
    css = "\n".join(style_blocks)

    if not css.strip():
        return result_line(
            WARN,
            "No <style> block found — CSS sizing could not be checked",
            "Ensure html/body have no min-height and carry background:transparent + overflow:hidden",
        )

    # FAIL: any min-height that could override the embed container's height
    min_height_match = re.search(r"min-height\s*:\s*100vh", css, re.IGNORECASE)
    if min_height_match:
        return result_line(
            FAIL,
            "min-height: 100vh found in CSS",
            "Remove min-height from html, body, and #main — it overrides the slide container "
            "height and prevents the chart from fitting the embedded slot",
        )

    # WARN: background transparency
    has_bg_transparent = re.search(r"background\s*:\s*transparent", css, re.IGNORECASE)
    # WARN: overflow hidden
    has_overflow_hidden = re.search(r"overflow\s*:\s*hidden", css, re.IGNORECASE)

    if has_bg_transparent and has_overflow_hidden:
        return result_line(
            PASS,
            "CSS sizing clean: no min-height, background transparent, overflow hidden",
        )

    missing = []
    if not has_bg_transparent:
        missing.append("background: transparent")
    if not has_overflow_hidden:
        missing.append("overflow: hidden")
    return result_line(
        WARN,
        f"CSS missing on html/body: {', '.join(missing)}",
        "Add these to html, body {{ }} to prevent background bleed and scroll bars in the embed",
    )


def check_echarts_cdn(html: str):
    """ECharts CDN script tag should be present for ECharts charts."""
    if "echarts" in html.lower():
        cdn_match = re.search(
            r'<script[^>]+src=["\'][^"\']*echarts[^"\']*["\']', html, re.IGNORECASE
        )
        if cdn_match:
            return result_line(PASS, f"ECharts CDN tag found")
        return result_line(
            WARN,
            "ECharts referenced in script but no CDN <script src> tag found",
            "slidejs collects CDN tags automatically — without the tag echarts won't be loaded",
        )
    return result_line(PASS, "Not an ECharts chart — CDN check skipped")


def check_data_chart_ready(script: str):
    """
    chartDom.setAttribute('data-chart-ready', 'true') signals to slidejs
    that initialisation completed. Absence won't break anything but is good practice.
    """
    if "data-chart-ready" in script:
        return result_line(PASS, "data-chart-ready attribute set (good practice)")
    return result_line(
        WARN,
        "data-chart-ready attribute not set",
        "Add:  chartDom.setAttribute('data-chart-ready', 'true')  at the end of your script",
    )


# ─────────────────────────────────────────────────────────────
# Main checker
# ─────────────────────────────────────────────────────────────


def check_file(html_path: Path, py_path: Path | None = None) -> bool:
    """
    Run all checks on a single HTML file.
    Returns True if there are no FAILs.
    """
    print(bold(f"\n{'═' * 62}"))
    print(bold(f"  Checking: {html_path.name}"))
    print(bold(f"{'═' * 62}"))

    # ── Read HTML ─────────────────────────────────────────────
    try:
        html = html_path.read_text(encoding="utf-8")
    except Exception as e:
        print(red(f"  ✘ Cannot read file: {e}"))
        return False

    # ── Extract inline script block(s) ───────────────────────
    script_blocks = re.findall(
        r"<script(?!\s+src)[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE
    )
    script = "\n".join(script_blocks)

    if not script.strip():
        print(red("  ✘ [FAIL]  No inline <script> block found — nothing to check"))
        return False

    # ── Read optional Python source ───────────────────────────
    py_source = None
    if py_path and py_path.exists():
        try:
            py_source = py_path.read_text(encoding="utf-8")
            print(dim(f"  (Python source: {py_path.name})"))
        except Exception:
            pass

    # ── Run checks ────────────────────────────────────────────
    checks = [
        check_container_id(script),
        check_set_option(script),
        check_set_chart_theme(script),
        check_no_get_option_in_theme(script),
        check_theme_colours(script),
        check_theme_ui_keys(script),
        check_series_color_meta(script),
        check_resize_handler(script),
        check_css_sizing(html),
        check_brace_balance(script),
        check_echarts_cdn(html),
        check_data_chart_ready(script),
    ]

    # Add Python-source-only check if available
    fstring_check = check_no_fstring_set_literal(py_source)
    if fstring_check:
        checks.append(fstring_check)

    # Filter None (skipped checks)
    checks = [c for c in checks if c is not None]

    # ── Print results ─────────────────────────────────────────
    statuses = []
    for line, status in checks:
        print(line)
        statuses.append(status)

    # ── Summary ───────────────────────────────────────────────
    n_pass = statuses.count(PASS)
    n_warn = statuses.count(WARN)
    n_fail = statuses.count(FAIL)

    print()
    if n_fail == 0:
        verdict = green(f"✔  READY  —  {n_pass} passed, {n_warn} warnings, 0 failures")
    else:
        verdict = red(
            f"✘  NOT READY  —  {n_fail} failure(s), {n_warn} warning(s), {n_pass} passed"
        )
    print(f"  {verdict}")

    return n_fail == 0


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    # Collect HTML files
    html_files: list[Path] = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            html_files.extend(sorted(p.glob("*.html")))
        elif p.suffix.lower() == ".html":
            html_files.append(p)
        else:
            print(yellow(f"Skipping non-HTML argument: {arg}"))

    if not html_files:
        print(red("No .html files found to check."))
        sys.exit(1)

    print(bold("\nSlideJS Chart Compliance Checker"))
    print(dim(f"Checking {len(html_files)} file(s)...\n"))

    all_passed = True
    results = {}

    for html_path in html_files:
        # Look for a matching .py file with the same stem
        py_path = html_path.with_suffix(".py")
        passed = check_file(html_path, py_path if py_path.exists() else None)
        results[html_path.name] = passed
        if not passed:
            all_passed = False

    # ── Final summary across all files ───────────────────────
    if len(html_files) > 1:
        print(bold(f"\n{'═' * 62}"))
        print(bold("  SUMMARY"))
        print(bold(f"{'═' * 62}"))
        for name, passed in results.items():
            icon = green("✔") if passed else red("✘")
            label = green("READY") if passed else red("NOT READY")
            print(f"  {icon}  {name:<45} {label}")
        print()

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
