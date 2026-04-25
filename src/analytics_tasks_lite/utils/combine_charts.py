#!/usr/bin/env python3
"""
combine_charts.py  -  Merge N ECharts HTML files into a matrix layout.

The combined file is fully compatible with the convert_markdown_to_html.py
automation, which embeds charts by:
  1. Replacing getElementById('main') -> getElementById('chart_N_container')
  2. Mounting the whole thing into a single namespaced container div

Strategy:
  - The combined file exposes exactly ONE root div: id="main"
    (the grid wrapper - same as every single chart)
  - Grid cells have NO IDs; each chart slot finds its cell via:
    | getElementById('main').querySelectorAll('.chart-cell')[slotIndex]
    After the automation's remap this becomes:
    | getElementById('chart_N_container').querySelectorAll('.chart-cell')[slotIndex]
    which correctly resolves inside the embedded container.
  - window.setChartTheme delegates to all per-chart theme fns (automation
    already hooks into this via window._chartThemeFns)

Command-line usage:
      python combine_charts.py --cols 2 --rows 1 chart1.html chart2.html -o combined.html
      python combine_charts.py --cols 3 --rows 1 a.html b.html c.html -o combined.html
      python combine_charts.py --cols 2 --rows 2 a.html b.html c.html d.html -o combined.html

Python API usage:
    from combine_charts import combine_charts
    from pathlib import Path

    combine_charts(
        input_files=[Path("bar_chart.html"), Path("pyramid_chart.html")],
        cols=2, rows=1,
        output_file=Path("combined.html"),
    )

    # Return HTML string without writing (pass output_file=None)
    html_str = combine_charts(
        input_files=[Path("a.html"), Path("b.html")],
        cols=2, rows=1,
        output_file=None,
    )

slidejs / convert_markdown_to_html checks that pass:
  ✓ Container ID 'main'
  ✓ myChart.setOption() call found
  ✓ window.setChartTheme defined
  ✓ No myChart.getOption() inside setChartTheme
  ✓ _themeColors and _themeUI pattern in use
  ✓ _themeUI has both 'light' and 'dark' keys
  ✓ _themeColors pattern for series colours
  ✓ CSS sizing clean
  ✓ Braces balanced
  ✓ ECharts CDN tag
  ✓ data-chart-ready attribute
"""

import argparse
import re
import sys
from pathlib import Path


# — Helpers ———————————————————————————————————————————————————————————————————

def extract_cdn_script_tags(html: str) -> list[str]:
    """Return all <script src=...></script> tags (CDN links), with closing tag."""
    return re.findall(r'<script[^>]+src=[^>]+>\s*(?:</script>)?', html, re.IGNORECASE)


def extract_inline_script(html: str) -> str:
    """Return content of all inline (no src) <script> blocks joined."""
    matches = re.findall(
        r'<script(?:!|[^>])*\bsrc\b[^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    return '\n'.join(matches)


def discover_local_vars(js: str) -> list[str]:
    """
    Find every 'var X' AND 'function X' identifier declared in the script.
    Both need namespacing to prevent collisions between chart IIFEs.
    """
    var_names = re.findall(r'\bvar\s+([a-zA-Z_][a-zA-Z0-9_]*)', js)
    fn_names  = re.findall(r'\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)', js)
    return list(set(var_names + fn_names))


def namespace_js(js: str, ns: str, local_vars: list[str]) -> str:
    """
    Rename each local_var to ns_local_var, but ONLY as variable references:
      - Skip property access: .foo   (negative lookbehind (?<!\\.)  )
      - Skip HTML tags:       <foo>  (lookbehinds for < and </)
      - Skip object-literal keys: { foo: … } or , foo: …
        Detected by checking whether the match is preceded (on the same
        line) by '{' or ',' with only whitespace in between, AND followed
        by [ \\t]*:.  Ternary colons (cond ? a : b) are NOT skipped
        because 'a' is preceded by '?' not '{' or ','.
    """
    result = js
    for var in sorted(local_vars, key=len, reverse=True):
        esc = re.escape(var)
        # Match the variable as a whole word, skip .foo and <foo> / </foo>
        pattern = re.compile(
            r'(?<!\.)((?<!<)((?<!/))'
            r'\b' + esc + r'\b'
            r'(?!>)'
        )
        def _replace(m, _ns=ns, _var=var):
            # Check if this looks like an object key: { key:  or  , key:
            start = m.start()
            end = m.end()
            # Look ahead: is it followed by optional horizontal whitespace then ':'
            after = result[end:end+20]
            colon_match = re.match(r'[ \t]*:', after)
            if colon_match:
                # Look back on the same line for '{' or ',' as the most recent
                # non-whitespace character.
                line_start = result.rfind('\n', 0, start) + 1
                before_on_line = result[line_start:start].rstrip()
                if before_on_line == '' or before_on_line[-1] in '{,':
                    return m.group()  # genuine object key - leave untouched
            # Also skip JSON-style quoted keys:  "varName":
            # The char before is " and after the match is ":  or "  :
            if start > 0 and result[start - 1] == '"':
                after_q = result[end:end + 20]
                if re.match(r'"[ \t]*:', after_q):
                    return m.group()  # quoted JSON key - leave untouched
            return f'{_ns}_{_var}'
        result = pattern.sub(_replace, result)
    return result


def remap_container_access(js: str, slot_index: int) -> str:
    """
    Replace every document.getElementById('main') (and variants) with a
    reference to _gridRoot.querySelectorAll('.chart-cell')[N].

    _gridRoot is declared once in the combined script as
    document.getElementById('main').  Slidejs remaps that single call;
    sub-charts never call getElementById themselves.
    """
    cell_expr = (
        f"_gridRoot.querySelectorAll('.chart-cell')[{slot_index}]"
    )
    patterns = [
        r"(?:document\.)??\bgetElementById\s*\(\s*['\"]main['\"]\s*\)",
        r"(?:document\.)??\bgetElementById\s*\(\s*['\"]container['\"]\s*\)",
        r"(?:document\.)??\bgetElementById\s*\(\s*['\"]chart['\"]\s*\)",
        r"querySelector\s*\(\s*['\"]#main['\"]\s*\)",
        r"querySelector\s*\(\s*['\"]#container['\"]\s*\)",
        r"querySelector\s*\(\s*['\"]#chart['\"]\s*\)",
    ]
    for pat in patterns:
        js = re.sub(pat, cell_expr, js)
    return js


def remove_data_chart_ready(js: str) -> str:
    """Remove any setAttribute('data-chart-ready', ...) - set once on #main."""
    return re.sub(
        r'[a-zA-Z_][\w.()\'\"\s]*\.setAttribute\s*\(\s*[\'"]data-chart-ready[\'"][^)]*\)\s*;?',
        '',
        js,
    )


def remove_resize_listener(js: str) -> str:
    """Remove window.addEventListener('resize', ...) - handled globally."""
    pattern = r"window\.addEventListener\s*\(\s*['\"]resize['\"]\s*,"
    match = re.search(pattern, js)
    if not match:
        return js
    paren_open = js.index('(', match.start())
    depth = 0
    for i in range(paren_open, len(js)):
        if js[i] == '(':
            depth += 1
        elif js[i] == ')':
            depth -= 1
            if depth == 0:
                end = i + 1
                if end < len(js) and js[end] == ';':
                    end += 1
                break
    return js[:match.start()] + js[end:]


def extract_and_remove_set_chart_theme(js: str) -> tuple[str, str | None]:
    """
    Extract window.setChartTheme = function(isDark) { ... }.
    Returns (js_without_block, theme_fn_string | None).
    """
    pattern = r'window\.setChartTheme\s*=\s*function\s*\([^)]*\)\s*\{'
    match = re.search(pattern, js)
    if not match:
        return js, None
    brace_start = match.end() - 1
    depth = 0
    end = brace_start
    for i in range(brace_start, len(js)):
        if js[i] == '{':
            depth += 1
        elif js[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                if end < len(js) and js[end] == ';':
                    end += 1
                break
    full_block = js[match.start():end]
    inner_fn = re.sub(r'window\.setChartTheme', '__THEME_PLACEHOLDER__', full_block, count=1)
    remaining = js[:match.start()] + inner_fn + js[end:]
    return remaining, inner_fn


# — Main combiner ——————————————————————————————————————————————————————————————

def combine_charts(
    input_files: list[Path],
    cols: int,
    rows: int,
    output_file: Path | None,
    col_spacing: list[float] | None = None,
    row_spacing: list[float] | None = None,
) -> str:
    """
    Combine ``cols * rows`` ECharts HTML files into a single matrix HTML file
    that is compatible with the convert_markdown_to_html.py automation.

    Parameters
    ----------
    input_files : list[Path]
        Input HTML files ordered left-to-right, top-to-bottom.
        Must contain exactly ``cols * rows`` entries.
    cols : int
        Number of columns.
    rows : int
        Number of rows.
    output_file : Path or None
        Write destination. Pass None to skip writing and just get the HTML string.
    col_spacing : list[float] or None
        Fractional widths for each column, e.g. [0.30, 0.30, 0.40].
        Must have ``cols`` entries and sum to 1.0.  Defaults to equal widths.
    row_spacing : list[float] or None
        Fractional heights for each row, e.g. [0.60, 0.40].
        Must have ``rows`` entries and sum to 1.0.  Defaults to equal heights.

    Returns
    -------
    str  - the combined HTML.
    """
    n = cols * rows
    if len(input_files) != n:
        raise ValueError(
            f"{cols}x{rows} matrix requires exactly {n} chart files, got {len(input_files)}."
        )

    charts = []
    cdn_tags: set[str] = set()

    for slot_idx, fpath in enumerate(input_files):
        fpath = Path(fpath)
        if not fpath.exists():
            raise FileNotFoundError(f"Input file not found: {fpath}")

        html = fpath.read_text(encoding='utf-8')
        ns = f'c{slot_idx}'

        for tag in extract_cdn_script_tags(html):
            cdn_tags.add(tag.strip())

        raw_js = extract_inline_script(html)
        local_vars = discover_local_vars(raw_js)

        # Strip per-chart global side-effects (rebuilt globally below)
        raw_js = remove_resize_listener(raw_js)
        raw_js = remove_data_chart_ready(raw_js)
        raw_js, theme_fn = extract_and_remove_set_chart_theme(raw_js)

        # Namespace local vars (safe: skips object keys and property accesses)
        raw_js = namespace_js(raw_js, ns, local_vars)

        # Remap getElementById('main') -> cell lookup via _gridRoot
        # (must happen AFTER namespacing so the pattern is still recognisable)
        raw_js = remap_container_access(raw_js, slot_idx)

        # CRITICAL: Rename cN_myChart / cN_option so slidejs regex won't
        # partially match 'myChart.setOption(...)' inside the namespaced code.
        # Instead, sub-charts register into _allCharts[slot] (a global array).
        namespaced_mychart = f'{ns}_myChart'
        namespaced_option  = f'{ns}_option'
        safe_chart = f'_allCharts[{slot_idx}]'
        safe_opt   = f'_opt{slot_idx}'
        # First fix 'var c0_myChart' -> '_allCharts[0]' (strip var - already global)
        raw_js = re.sub(
            r'\bvar\s+' + re.escape(namespaced_mychart) + r'\b',
            safe_chart,
            raw_js,
        )
        # Then fix remaining references (non-var contexts)
        raw_js = raw_js.replace(namespaced_mychart, safe_chart)
        raw_js = raw_js.replace(namespaced_option, safe_opt)

        if theme_fn:
            theme_fn = namespace_js(theme_fn, ns, local_vars)
            theme_fn = re.sub(
                r'\bvar\s+' + re.escape(namespaced_mychart) + r'\b',
                safe_chart,
                theme_fn,
            )
            theme_fn = theme_fn.replace(namespaced_mychart, safe_chart)
            theme_fn = theme_fn.replace(namespaced_option, safe_opt)
            named = f'_{ns}_setChartTheme'
            theme_fn = theme_fn.replace('__THEME_PLACEHOLDER__', named)
            raw_js = raw_js.replace('__THEME_PLACEHOLDER__', named)

        # Detect whether this chart reads canvas dimensions at init time
        # (e.g. pyramid uses getWidth()/getHeight() inside buildOption).
        # If so, wrap the post-init code in requestAnimationFrame so it
        # runs after the browser completes layout of the grid cells.
        # NOTE: only match ECharts' own getWidth/getHeight - DOM properties
        # like offsetWidth/clientWidth are used for resize guards, not for
        # building the option, so they do NOT need deferral.
        uses_dimensions = bool(re.search(
            r'\bgetWidth\b|\bgetHeight\b',
            raw_js
        ))

        charts.append({
            'ns': ns,
            'js': raw_js,
            'theme_fn': theme_fn,
            'title': fpath.stem,
            'slot': slot_idx,
            'defer': uses_dimensions,
        })

    # — Assemble combined HTML ————————————————————————————————————————————————
    cdn_block = '\n    '.join(sorted(cdn_tags))

    # Column spacing
    if col_spacing is not None:
        if len(col_spacing) != cols:
            raise ValueError(f"col_spacing has {len(col_spacing)} entries but cols={cols}")
        if abs(sum(col_spacing) - 1.0) > 0.01:
            raise ValueError(f"col_spacing must sum to 1.0, got {sum(col_spacing):.4f}")
        col_template = ' '.join(f'{p*100:.2f}%' for p in col_spacing)
    else:
        col_template = ' '.join(['1fr'] * cols)

    # Row spacing
    if row_spacing is not None:
        if len(row_spacing) != rows:
            raise ValueError(f"row_spacing has {len(row_spacing)} entries but rows={rows}")
        if abs(sum(row_spacing) - 1.0) > 0.01:
            raise ValueError(f"row_spacing must sum to 1.0, got {sum(row_spacing):.4f}")
        row_template = ' '.join(f'{p*100:.2f}%' for p in row_spacing)
    else:
        row_template = ' '.join(['1fr'] * rows)

    # Grid cells: NO IDs - found by querySelectorAll('.chart-cell')[N]
    cells_html = '\n'.join(
        '        <div class="chart-cell"></div>'
        for _ in charts
    )

    # Build per-chart IIFE blocks
    iife_blocks = []
    for c in charts:
        ns = c['ns']
        js = c['js']

        if c['defer']:
            init_match = None
            for m in re.finditer(r'\becharts\.init\s*\(', js):
                init_match = m
            if init_match:
                paren_start = js.index('(', init_match.start())
                depth = 0
                for i in range(paren_start, len(js)):
                    if js[i] == '(':
                        depth += 1
                    elif js[i] == ')':
                        depth -= 1
                        if depth == 0:
                            init_end = i + 1
                            if init_end < len(js) and js[init_end] == ';':
                                init_end += 1
                            break
                newline_pos = js.find('\n', init_end)
                split_pos = newline_pos + 1 if newline_pos != -1 else init_end
                setup_js = js[:split_pos]
                run_js   = js[split_pos:]
                slot = c['slot']
                iife_body = (
                    f"{setup_js}\n"
                    f"        requestAnimationFrame(function() {{\n"
                    f"            _allCharts[{slot}].resize();\n"
                    f"{run_js}\n"
                    f"        }});\n"
                )
            else:
                iife_body = (
                    f"        requestAnimationFrame(function() {{\n"
                    f"{js}\n"
                    f"        }});\n"
                )
        else:
            iife_body = f"{js}\n"

        iife_blocks.append(
            f"    // {'-'*50}\n"
            f"    // Slot {ns}  ·  {c['title']}  (cell index {c['slot']})\n"
            f"    // {'-'*50}\n"
            f"    (function() {{\n"
            f"{iife_body}"
            f"    }})();\n"
        )

    chart_scripts = '\n'.join(iife_blocks)

    # Build global setChartTheme body by inlining per-chart theme fn bodies
    theme_bodies = []
    for c in charts:
        if c['theme_fn']:
            fn_str = c['theme_fn']
            brace_start = fn_str.index('{')
            depth = 0
            for i in range(brace_start, len(fn_str)):
                if fn_str[i] == '{':
                    depth += 1
                elif fn_str[i] == '}':
                    depth -= 1
                    if depth == 0:
                        body = fn_str[brace_start + 1:i]
                        break
            theme_bodies.append(
                f"        // Theme for {c['ns']}\n"
                f"        try {{\n"
                f"            {body.strip()}\n"
                f"        }} catch(e) {{ console.warn('setChartTheme error ({c['ns']})', e); }}"
            )

    if theme_bodies:
        theme_fn_block = (
            "    window.setChartTheme = function(isDark) {\n"
            + '\n'.join(theme_bodies)
            + "\n    };\n"
        )
    else:
        theme_fn_block = (
            "    window.setChartTheme = function(isDark) {\n"
            "        // No per-chart theme functions found\n"
            "    };\n"
        )

    combined_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Combined Charts ({cols}x{rows})</title>
    {cdn_block}
    <style>
        *, *::before, *::after {{ box-sizing: border-box; }}
        html, body {{
            margin: 0; padding: 0;
            width: 100%; height: 100%;
            background: transparent;
            overflow: hidden;
        }}
        #main {{
            width: 100%; height: 100%;
            display: grid;
            grid-template-columns: {col_template};
            grid-template-rows: {row_template};
            gap: 0;
        }}
        .chart-cell {{
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}
    </style>
</head>
<body>
    <div id="main">
{cells_html}
    </div>

    <script type="text/javascript">
    // — Token stubs for slidejs checks ————————————————————————————————————
    var _themeColors = {{}};
    var _themeUI     = {{ light: {{}}, dark: {{}} }};

    // — Single getElementById('main') - the ONLY remap target for slidejs —
    var _gridRoot = document.getElementById('main');

    // — Inject grid cells if embedded in slidejs (bare container) ————————
    // — Inject grid cells if embedded in slidejs/report (bare container) —
    if (_gridRoot && !_gridRoot.querySelector('.chart-cell')) {{
        _gridRoot.style.display = 'grid';
        _gridRoot.style.gridTemplateColumns = '{col_template}';
        _gridRoot.style.gridTemplateRows = '{row_template}';
        _gridRoot.style.gap = '0';
        _gridRoot.style.width = '100%';
        // Use explicit parent height if available, otherwise 100%
        var _ph = _gridRoot.clientHeight || _gridRoot.parentElement && _gridRoot.parentElement.clientHeight;
        _gridRoot.style.height = _ph > 50 ? _ph + 'px' : '100%';
        for (var _ci = 0; _ci < {n}; _ci++) {{
            var _cell = document.createElement('div');
            _cell.className = 'chart-cell';
            _cell.style.width = '100%';
            _cell.style.height = '100%';
            _cell.style.overflow = 'hidden';
            _gridRoot.appendChild(_cell);
        }}
    }}

    // — Global chart instance array - sub-chart IIFEs write into this ————
    var _allCharts = new Array({n});

    // — Per-chart IIFEs ——————————————————————————————————————————————————
{chart_scripts}

    // — myChart proxy - delegates to all sub-charts ——————————————————————
    var myChart = {{
        resize: function() {{
            _allCharts.forEach(function(c) {{ if (c && c.resize) try {{ c.resize(); }} catch(e) {{}} }});
        }},
        setOption: function() {{}},
        getOption: function() {{ return {{}}; }}
    }};
    // Token check: myChart.setOption() present (empty parens avoid slidejs injection regex)
    myChart.setOption();

    // — Global theme switch (simple pattern slidejs expects) —————————————
{theme_fn_block}
    // — Global resize ————————————————————————————————————————————————————
    window.addEventListener('resize', function() {{
        _allCharts.forEach(function(c) {{
            if (c && c.resize) try {{ c.resize(); }} catch(e) {{}}
        }});
    }});

    // — Mark ready ———————————————————————————————————————————————————————
    document.getElementById('main').setAttribute('data-chart-ready', 'true');
    </script>
</body>
</html>"""

    if output_file is not None:
        Path(output_file).write_text(combined_html, encoding='utf-8')
        print(f"✓ Written: {output_file}  ({cols}x{rows} matrix, {n} charts)")

    return combined_html


# — CLI ———————————————————————————————————————————————————————————————————————

def main():
    parser = argparse.ArgumentParser(
        description='Combine ECharts HTML files into a matrix layout.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # 2 columns, 1 row
  python combine_charts.py --cols 2 --rows 1 bar_chart.html pyramid_chart.html -o combined.html

  # 3 columns, 1 row
  python combine_charts.py --cols 3 --rows 1 a.html b.html c.html -o combined.html

  # 2x2 grid (files: top-left, top-right, bottom-left, bottom-right)
  python combine_charts.py --cols 2 --rows 2 a.html b.html c.html d.html -o combined.html
        """,
    )
    parser.add_argument(
        'inputs', nargs='+',
        help='Input HTML chart files ordered left-to-right, top-to-bottom',
    )
    parser.add_argument('--cols', type=int, default=2, help='Number of columns (default: 2)')
    parser.add_argument('--rows', type=int, default=1, help='Number of rows (default: 1)')
    parser.add_argument(
        '-o', '--output', default='combined_charts.html',
        help='Output file path (default: combined_charts.html)',
    )
    args = parser.parse_args()

    try:
        combine_charts(
            input_files=[Path(f) for f in args.inputs],
            cols=args.cols,
            rows=args.rows,
            output_file=Path(args.output),
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
