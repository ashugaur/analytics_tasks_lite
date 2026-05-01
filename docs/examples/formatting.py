import pandas as pd
from pathlib import Path
from datetime import datetime
import re
import base64
import os


def data_explorer(
    sql_file_path=None,
    sql_file_paths=None,
    database_connection=None,
    direct_files=None,
    cache_folder="query_cache",
    cache=False,
    global_column_formats=None,
    override_column_formats=None,
    force_refresh=False,
    show_queries="collapsible",
    output_file="data_explorer.html",
    sidebar_width="250px",
    light_mode_colors=None,
    dark_mode_colors=None,
    default_theme="light",
    include_images=True,
    max_image_width="100%",
    max_rows=50,
    stored_rows=500,
    include_column_search=True,
    column_search_threshold=5,
    include_row_search=True,
    row_search_threshold=10,
    section_names=None,
    page_title="Data Explorer",
    embed_full_data=True,
    js_folder=None,
    report_header=None,
    report_footer=None,
    enable_multiword_search=False,
    max_table_height="600px",
    table_scroll_threshold=20,
    truncate_cell_text=True,
    max_cell_chars=100,
    enable_cell_expansion=True,
    include_code_blocks=True,
    style_output_blocks=False,
    theme_config_file=None,
    theme=None,
    default_embed_height=500,
    table_font_family="'SF Mono', Monaco, 'Inconsolata', 'Fira Code', monospace",
    table_font_size="11px",
    freeze_columns=None,
    row_density="normal",
    default_code_height="200px",
    nav_font_sizes=None,
    heading_font_sizes=None,
    page_font=None,
    page_font_size=None,
    sidebar_collapsible=False,
    format_file=None,
    format_sheet_name="Formats",
):
    """
    Create an interactive HTML data explorer with custom sections for direct files.

    Parameters:
    ----------
    sql_file_path : str, optional
        Path to a single SQL file (kept for backwards compatibility).
    sql_file_paths : list, optional
        List of SQL file paths to process. Each file becomes its own sidebar section
        named after the file stem. Takes precedence over sql_file_path when provided.
        Example: ["queries/sales.sql", "queries/ops.sql"]
    direct_files : list or dict
        Files to include. Can now specify custom sections:

        List format with sections:
        {"path": "file1.parquet", "title": "File 1", "section": "Group A"},
        {"path": "file2.parquet", "title": "File 2", "section": "Group B"},
        {"path": "file3.parquet", "title": "File 3"} # Uses default section

        Dict format (backwards compatible):
        {"file1.parquet": "File 1",
         "file2.parquet": {"title": "File 2", "section": "Custom Section"}}

    section_names : dict
        Rename default sections. Keys: "sql_queries", "direct_files"
        The "direct_files" name is used for files without a custom section.
    max_table_height : str
        CSS max-height for the table wrapper (default "600px"). Tables taller than
        this get a vertical scrollbar. Set to None to disable height capping.
    table_scroll_threshold : int
        Number of visible rows above which the vertical scrollbar is applied
        (default 20). Tables with fewer rows are shown in full regardless of
        max_table_height.
    truncate_cell_text : bool
        Whether to truncate long cell values in the display (default True).
    max_cell_chars : int
        Maximum characters to show in a cell before truncating (default 100).
        Only applies when truncate_cell_text=True.
    enable_cell_expansion : bool
        If True, clicking a truncated cell shows a modal/tooltip with the full
        value (default True). Only applies when truncate_cell_text=True.
    include_code_blocks : bool
        Whether to render code blocks in the SQL query viewer (default True).
    style_output_blocks : bool
        Whether to apply border/background styling to output reference blocks
        (default False).
    theme_config_file : str or Path, optional
        UNC or local path to a .xlsm/.xlsx workbook containing a 'Theme_Config'
        sheet. When provided together with theme=, colors are loaded from that
        sheet and override light_mode_colors / dark_mode_colors.
    theme : str, optional
        Test_ID value from the Theme_Config sheet to apply (e.g. 'test_1').
        Requires theme_config_file to also be set.
    default_embed_height : int
        Default height in pixels for ##-add-html / --@ embedded charts (default 500).
        Can be overridden per-chart with height=N in the directive.
    table_font_family : str
        Font family applied to all table cells (default: monospace stack).
    table_font_size : str
        Font size for table cells (default: '11px').
    freeze_columns : list
        Column names whose header is highlighted with the accent colour and whose
        cells are lightly tinted so they're always visually anchored.
    row_density : str
        Row spacing: 'normal' (default), 'compact', or 'ultracompact'.
    default_code_height : str
        CSS max-height for the SQL code block pre element (default: '200px').
        Set to 'none' to disable the cap.

    Supports a skip-block directive:
        --skip-start
        select * from heavy_table;
        --skip-end

        Any -- query titles and SQL lines between --skip-start and --skip-end
        are completely ignored — they never reach the database.

    Insert image:
        -- # C:/my_disk/projects/visual_library/bar/bar_chart_stacked.png

    Embed HTML chart (two equivalent syntaxes):
        --@ C:/path/to/chart.html
        --@ C:/path/to/chart.html height=600
    """

    # Validate inputs

    # Normalise sql_file_paths: merge legacy sql_file_path into the list
    if sql_file_paths is None:
        sql_file_paths = []
    if sql_file_path is not None and sql_file_path not in sql_file_paths:
        sql_file_paths = [sql_file_path] + list(sql_file_paths)

    if not sql_file_paths and direct_files is None:
        raise ValueError(
            "Must provide either sql_file_path / sql_file_paths or direct_files (or both)"
        )

    if sql_file_paths and database_connection is None:
        raise ValueError(
            "database_connection required when sql_file_path / sql_file_paths is provided"
        )

    if global_column_formats is None:
        global_column_formats = {}

    if override_column_formats is None:
        override_column_formats = {}

    # ── Load column formats from Excel sheet ────────────────────────────
    if format_file is not None:
        try:
            import openpyxl as _xl_fmt
            import io as _io_fmt

            _fmt_path = Path(format_file)
            if _fmt_path.exists():
                with open(_fmt_path, "rb") as _fh:
                    _buf = _io_fmt.BytesIO(_fh.read())
                _wb = _xl_fmt.load_workbook(_buf, read_only=True, data_only=True, keep_vba=False)
                if format_sheet_name in _wb.sheetnames:
                    _ws = _wb[format_sheet_name]
                    _rows = list(_ws.iter_rows(values_only=True))
                    if _rows:
                        _hdr = [str(c).strip().lower() if c else "" for c in _rows[0]]
                        _ci = {name: _hdr.index(name) for name in _hdr if name}
                        _loaded_g = 0
                        _loaded_o = 0
                        for _r in _rows[1:]:
                            if not _r or not _r[_ci.get("column_pattern", 0)]:
                                continue
                            
                            _col_pat = str(_r[_ci["column_pattern"]]).strip().lower()
                            _fmt_str = str(_r[_ci["format_string"]]).strip() if _r[_ci.get("format_string", 1)] else ""
                            _scope = str(_r[_ci.get("scope", 2)]).strip().lower() if _r[_ci.get("scope", 2)] else "global"
                            _tbl_pat = str(_r[_ci.get("table_pattern", 3)]).strip().lower() if _ci.get("table_pattern") is not None and _r[_ci["table_pattern"]] else ""
                            
                            if not _fmt_str:
                                continue
                            
                            if _scope == "override" and _tbl_pat:
                                _override_column_formats[(_tbl_pat, _col_pat)] = _fmt_str
                                _loaded_o += 1
                            else:
                                _global_column_formats[_col_pat] = _fmt_str
                                _loaded_g += 1
                        
                        print(f"✅ Loaded formats from '{format_sheet_name}': {_loaded_g} global, {_loaded_o} override")
                    _wb.close()
                else:
                    print(f"⚠️  format_sheet_name '{format_sheet_name}' not found in {_fmt_path.name}")
            else:
                print(f"⚠️  format_file not found: {_fmt_path}")
        except Exception as _e:
            print(f"⚠️  Failed to load format config: {_e}")

    if direct_files is None:
        direct_files = {}

    if section_names is None:
        section_names = {"sql_queries": "SQL Queries", "direct_files": "Direct Files"}
    else:
        default_names = {"sql_queries": "SQL Queries", "direct_files": "Direct Files"}
        default_names.update(section_names)
        section_names = default_names

    # Table styling defaults
    if freeze_columns is None:
        freeze_columns = []

    density_settings = {
        "normal": {"th_padding": "12px 8px", "td_padding": "10px 12px"},
        "compact": {"th_padding": "8px 6px", "td_padding": "4px 6px"},
        "ultracompact": {"th_padding": "4px 4px", "td_padding": "2px 4px"},
    }
    density = density_settings.get(row_density.lower(), density_settings["normal"])

    # ── Theme config loading ───────────────────────────────────────────────────
    def load_theme_config(theme_config_file, theme_id):
        """Load light + dark color dicts from the Theme_Config sheet of an Excel workbook."""
        try:
            import io as _io
            import openpyxl as _xl
        except ImportError:
            print("❌ load_theme_config: openpyxl is required — pip install openpyxl")
            return None, None
        try:
            _path = Path(theme_config_file)
            if not _path.exists():
                print(f"❌ load_theme_config: file not found — {_path}")
                return None, None
            # Read into memory so the file is never OS-locked
            with open(_path, "rb") as _fh:
                _buf = _io.BytesIO(_fh.read())
            _wb = _xl.load_workbook(
                _buf, read_only=True, data_only=True, keep_vba=False
            )
            _sheet = "Theme_Config"
            if _sheet not in _wb.sheetnames:
                print(f"❌ load_theme_config: sheet '{_sheet}' not found")
                return None, None
            _ws = _wb[_sheet]
            _rows = list(_ws.iter_rows(values_only=True))
            if not _rows:
                return None, None
            _hdr = [str(c).strip().lower() if c is not None else "" for c in _rows[0]]

            def _col(n):
                k = n.strip().lower()
                if k not in _hdr:
                    raise KeyError(f"Column '{n}' missing in Theme_Config")
                return _hdr.index(k)

            _idx = {
                k: _col(k)
                for k in (
                    "test_id",
                    "theme_name",
                    "primary",
                    "text",
                    "muted",
                    "content_bg",
                    "slide_bg",
                    "bg",
                    "bg_light",
                    "border",
                    "border_muted",
                )
            }
            _light = _dark = None
            for _r in _rows[1:]:
                _tid = (
                    str(_r[_idx["test_id"]]).strip()
                    if _r[_idx["test_id"]] is not None
                    else ""
                )
                _tname = (
                    str(_r[_idx["theme_name"]]).strip().lower()
                    if _r[_idx["theme_name"]] is not None
                    else ""
                )
                if _tid == str(theme_id).strip():

                    def _v(row, key):
                        val = row[_idx[key]]
                        return str(val).strip() if val is not None else ""

                    _colors = {
                        "bg": _v(_r, "bg"),
                        "text": _v(_r, "text"),
                        "sidebar_bg": _v(_r, "slide_bg"),
                        "table_header": _v(_r, "content_bg"),
                        "accent": _v(_r, "primary"),
                        "border": _v(_r, "border"),
                        "hover": _v(_r, "bg_light"),
                    }
                    if _tname == "light":
                        _light = _colors
                    elif _tname == "dark":
                        _dark = _colors
            if _light is None and _dark is None:
                print(f"❌ load_theme_config: theme_id '{theme_id}' not found")
                return None, None
            _modes = [m for m, c in [("light", _light), ("dark", _dark)] if c]
            print(
                f"✅ load_theme_config: loaded '{theme_id}' ({' + '.join(_modes)} modes)"
            )
            return _light, _dark
        except Exception as _e:
            import traceback

            traceback.print_exc()
            print(f"❌ load_theme_config error: {_e}")
            return None, None

    if theme is not None and theme_config_file is not None:
        _lc, _dc = load_theme_config(theme_config_file, theme)
        if _lc is not None:
            light_mode_colors = _lc
        if _dc is not None:
            dark_mode_colors = _dc
    elif theme is not None:
        print(
            "⚠️  theme= provided but theme_config_file= is missing — using default colors"
        )

    # Apply defaults for any color keys still missing after theme load
    _light_defaults = {
        "bg": "#ffffff",
        "text": "#333333",
        "sidebar_bg": "#f8f9fa",
        "table_header": "#e9ecef",
        "accent": "#007bff",
        "border": "#dee2e6",
        "hover": "#f1f3f5",
    }
    _dark_defaults = {
        "bg": "#1e1e1e",
        "text": "#e0e0e0",
        "sidebar_bg": "#2d2d2d",
        "table_header": "#3d3d3d",
        "accent": "#4a9eff",
        "border": "#444444",
        "hover": "#383838",
    }
    if light_mode_colors is None:
        light_mode_colors = _light_defaults
    else:
        for _k, _v in _light_defaults.items():
            light_mode_colors.setdefault(_k, _v)
    if dark_mode_colors is None:
        dark_mode_colors = _dark_defaults
    else:
        for _k, _v in _dark_defaults.items():
            dark_mode_colors.setdefault(_k, _v)

    # Helper functions
    def generate_query_id(section_type, index):
        """Generate simple numeric ID for queries"""
        return f"{section_type}_{index}"

    def embed_pako_js(js_folder_path):
        """Embed pako.min.js from local folder"""
        if not js_folder_path:
            print("⚠️  js_folder not provided - compression disabled")
            return None

        js_path = Path(js_folder_path)
        pako_file = js_path / "pako.min.js"

        if not pako_file.exists():
            print(f"⚠️  pako.min.js not found in {js_path}")
            print(
                "    Download from: https://cdnjs.cloudflare.com/ajax/libs/pako/2.1.0/pako.min.js"
            )
            return None

        try:
            with open(pako_file, "r", encoding="utf-8") as f:
                pako_content = f.read()

            file_size_kb = len(pako_content) / 1024
            print(f"📦 Embedded pako.js: {file_size_kb:.1f} KB")
            return pako_content

        except Exception as e:
            print(f"⚠️  Failed to read pako.min.js: {e}")
            return None

    def embed_html_chart(html_path, height, chart_index):
        """Embed a D3 or ECharts HTML file inline.

        Identical contract to convert_markdown_to_html.embed_html_chart:
        - Namespaces container ID to avoid clashes between multiple charts
        - Wraps inline JS in an IIFE with try/catch
        - Re-emits CDN <script src> tags before the IIFE
        - Scopes CSS to the namespaced container
        - Removes overflow:hidden from the chart's own #container rule so
          axis/stage labels below the SVG are never clipped
        - Adds a ResizeObserver that re-renders D3 charts and calls
          myChart.resize() for ECharts on container width changes
        - Detects window.setChartTheme and registers it for the theme toggle
        """
        try:
            from bs4 import BeautifulSoup as _BS
            import re as _re

            html_path = Path(html_path)
            if not html_path.exists():
                msg = f"⚠ Chart not found: {html_path}"
                print(f"❌ embed_html_chart: {msg}")
                return f'<div style="color:red;padding:1rem;border:1px solid red;">{msg}</div>'

            print(f"\n  📊 embed_html_chart [{chart_index}]: {html_path.name}")
            raw = html_path.read_text(encoding="utf-8")
            soup = _BS(raw, "html.parser")
            cid = f"chart_{chart_index}_container"

            # ── 1. CDN script tags ────────────────────────────────────────────
            cdns = [t["src"] for t in soup.find_all("script", src=True)]
            is_d3 = any("d3" in c.lower() for c in cdns)
            is_echarts = any("echarts" in c.lower() for c in cdns)
            if is_d3:
                print("    🔵 D3 chart detected")
            if is_echarts:
                print("    🟢 ECharts chart detected")

            # ── 2. Inline scripts ─────────────────────────────────────────────
            inline_scripts = [
                t.string
                for t in soup.find_all("script", src=False)
                if t.string and t.string.strip()
            ]
            if not inline_scripts:
                body = soup.find("body")
                inner = str(body) if body else raw
                return (
                    f'<div id="{cid}" style="width:100%;min-height:{height}px;'
                    f'padding-bottom:60px;overflow:visible;margin:1.5rem 0;">'
                    f"\n{inner}\n</div>"
                )

            script = "\n\n// --- next block ---\n\n".join(inline_scripts)

            # ── 3. Container ID substitution ──────────────────────────────────
            for pat, rep in [
                (
                    r"getElementById\s*\(\s*['\"]container['\"]\s*\)",
                    f"getElementById('{cid}')",
                ),
                (
                    r"getElementById\s*\(\s*['\"]chart['\"]\s*\)",
                    f"getElementById('{cid}')",
                ),
                (
                    r"getElementById\s*\(\s*['\"]main['\"]\s*\)",
                    f"getElementById('{cid}')",
                ),
                (
                    r"querySelector\s*\(\s*['\"]#container['\"]\s*\)",
                    f"querySelector('#{cid}')",
                ),
                (
                    r"querySelector\s*\(\s*['\"]#chart['\"]\s*\)",
                    f"querySelector('#{cid}')",
                ),
                (
                    r"querySelector\s*\(\s*['\"]#main['\"]\s*\)",
                    f"querySelector('#{cid}')",
                ),
                (
                    r'd3\.select\s*\(\s*["\']#container["\']\s*\)',
                    f'd3.select("#{cid}")',
                ),
                (r'd3\.select\s*\(\s*["\']#chart["\']\s*\)', f'd3.select("#{cid}")'),
                (r'd3\.select\s*\(\s*["\']#main["\']\s*\)', f'd3.select("#{cid}")'),
            ]:
                script = _re.sub(pat, rep, script)

            # ── 4. Custom tooltip scoping ─────────────────────────────────────
            has_custom_tooltip = "customTooltip" in script or "custom-tooltip" in script
            tooltip_id = None
            if has_custom_tooltip:
                tooltip_id = f"customTooltip_{chart_index}"
                script = _re.sub(
                    r"getElementById\s*\(\s*['\"]customTooltip['\"]\s*\)",
                    f"getElementById('{tooltip_id}')",
                    script,
                )
                script = _re.sub(
                    r"querySelector\s*\(\s*['\"]#customTooltip['\"]\s*\)",
                    f"querySelector('#{tooltip_id}')",
                    script,
                )

            # ── 5. Remove window resize listeners (ResizeObserver replaces them)
            lines_buf = script.split("\n")
            filtered = []
            skip, depth = False, 0
            for line in lines_buf:
                if (
                    "window.addEventListener('resize'" in line
                    or 'window.addEventListener("resize"' in line
                ):
                    if line.count("(") == line.count(")") and ");" in line:
                        continue
                    skip, depth = True, line.count("{") - line.count("}")
                    continue
                if skip:
                    depth += line.count("{") - line.count("}")
                    if depth <= 0 and line.strip() in ["});", "};"]:
                        skip, depth = False, 0
                    continue
                filtered.append(line)
            script = "\n".join(filtered).strip()

            # ── 6. Theme support ──────────────────────────────────────────────
            has_theme = "window.setChartTheme" in script
            if has_theme:
                script = script.replace(
                    "window.setChartTheme", f"window.setChartTheme_{chart_index}"
                )
                print(f"    🎨 Theme support detected → setChartTheme_{chart_index}")

            # ── 7. CSS — scoped, overflow:hidden removed ──────────────────────
            style_blocks = []
            for st in soup.find_all("style"):
                if st.string and st.string.strip():
                    css = st.string
                    css = _re.sub(r"\bbody\b", f"#{cid}", css)
                    css = _re.sub(
                        rf"#{_re.escape(cid)}\[data-theme", "[data-theme", css
                    )
                    css = _re.sub(r"\bhtml\b", f"#{cid}", css)
                    css = _re.sub(
                        r"(#container\s*\{[^}]*?)overflow\s*:\s*hidden\s*;",
                        r"\1overflow: visible;",
                        css,
                        flags=_re.DOTALL,
                    )
                    style_blocks.append(css)

            scoped_css = (
                f"<style>\n#{cid}{{width:100%;height:{height}px;overflow:visible;}}\n"
                + ("\n".join(style_blocks) if style_blocks else "")
                + "\n</style>\n"
            )

            # ── 8. Custom tooltip div ─────────────────────────────────────────
            tooltip_div = (
                f'<div id="{tooltip_id}" style="display:none;position:absolute;"></div>\n'
                if tooltip_id
                else ""
            )

            # ── 9. ResizeObserver snippet ─────────────────────────────────────
            resize_observer = (
                f"\n        // ResizeObserver — re-render on width change\n"
                f"        (function(){{\n"
                f"            if(typeof ResizeObserver==='undefined')return;\n"
                f"            var _el=document.getElementById('{cid}');\n"
                f"            if(!_el)return;\n"
                f"            var _lw=_el.clientWidth,_t=null;\n"
                f"            new ResizeObserver(function(e){{\n"
                f"                var w=e[0].contentRect.width;\n"
                f"                if(Math.abs(w-_lw)<2)return;\n"
                f"                _lw=w;clearTimeout(_t);\n"
                f"                _t=setTimeout(function(){{\n"
                f"                    try{{\n"
                f"                        if(typeof myChart!=='undefined'&&myChart&&myChart.resize){{myChart.resize();return;}}\n"
                f"                        var fns=['createSankeyChart','createChart','drawChart','renderChart','draw','render','init'];\n"
                f"                        for(var i=0;i<fns.length;i++){{if(typeof window[fns[i]]==='function'){{window[fns[i]]();return;}}}}\n"
                f"                    }}catch(e){{console.warn('Chart {chart_index} resize:',e);}}\n"
                f"                }},150);\n"
                f"            }}).observe(_el);\n"
                f"        }})();\n"
            )

            # ── 10. Theme registration ────────────────────────────────────────
            theme_reg = (
                (
                    f"\n        if(!window._chartThemeFns)window._chartThemeFns=[];\n"
                    f"        window._chartThemeFns.push(window.setChartTheme_{chart_index});\n"
                )
                if has_theme
                else ""
            )

            # ── 11. IIFE ──────────────────────────────────────────────────────
            indented = "\n".join("        " + l for l in script.split("\n"))
            iife = (
                f"// ===== CHART {chart_index} START ({cid}) =====\n"
                f"(function(){{\n    try{{\n"
                f"{indented}\n{theme_reg}"
                f"\n        // Post-init resize\n"
                f"        setTimeout(function(){{\n"
                f"            try{{var _c=document.getElementById('{cid}');\n"
                f"            if(_c&&typeof myChart!=='undefined'&&myChart.resize)myChart.resize();}}\n"
                f"            catch(e){{}}}},300);\n"
                f"{resize_observer}"
                f"    }}catch(err){{console.error('❌ Chart {chart_index}:',err);}}\n}})();\n"
                f"// ===== CHART {chart_index} END =====\n"
            )

            # ── 12. Assemble snippet ──────────────────────────────────────────
            cdn_tags = "\n".join(f'<script src="{c}"></script>' for c in cdns)
            label_clearance = 60
            snippet = (
                f'<div class="embedded-chart" '
                f'style="width:100%;min-height:{height}px;padding-bottom:{label_clearance}px;'
                f'overflow:visible;margin:1.5rem 0;position:relative;">\n'
                f"{scoped_css}{cdn_tags}\n"
                f'<div id="{cid}" style="width:100%;max-width:100%;height:{height}px;overflow:visible;"></div>\n'
                f"{tooltip_div}"
                f"<script>\n{iife}\n</script>\n</div>"
            )
            print(f"    ✅ Chart {chart_index} embedded ({len(snippet):,} chars)")
            return snippet

        except ImportError:
            return '<div style="color:orange;padding:1rem;">⚠ beautifulsoup4 required: pip install beautifulsoup4</div>'
        except Exception as exc:
            import traceback

            traceback.print_exc()
            return f'<div style="color:red;padding:1rem;">⚠ Error embedding chart {chart_index}: {exc}</div>'

    def df_to_json_base64(df):
        """Convert DataFrame to compressed JSON base64 using split orientation.

        split format: {"columns": ["a","b",...], "data": [[v1,v2,...], ...]}
        Column names are stored once instead of repeated per row (records format),
        which gives meaningfully smaller output — especially for wide tables.
        The JS side reconstructs row objects from columns + data arrays.
        """
        try:
            import gzip

            # Convert to split format — column names appear once, rows are plain arrays
            json_str = df.to_json(
                orient="split", date_format="iso", double_precision=4, index=False
            )
            json_bytes = json_str.encode("utf-8")

            # Compress with gzip
            compressed = gzip.compress(json_bytes, compresslevel=9)

            # Encode to base64
            base64_data = base64.b64encode(compressed).decode("utf-8")

            original_mb = len(json_bytes) / (1024 * 1024)
            compressed_mb = len(compressed) / (1024 * 1024)
            ratio = (1 - len(compressed) / len(json_bytes)) * 100

            print(
                f"  💾 Compressed data (split): {original_mb:.2f} MB → {compressed_mb:.2f} MB (saved {ratio:.1f}%)"
            )
            return base64_data

        except Exception as e:
            print(f"⚠️  Failed to compress data: {e}")
            return None

    def normalize_direct_files(direct_files):
        """Convert direct_files to uniform list format with section support.
        Accepted file types: .parquet, .html (embedded charts).
        """
        _allowed = {".parquet", ".html"}

        if isinstance(direct_files, dict):
            normalized = []
            for file_path, file_entry in direct_files.items():
                ext = Path(file_path).suffix.lower()
                if ext not in _allowed:
                    print(f"⚠️  Skipping unsupported file type: {file_path}")
                    continue
                if isinstance(file_entry, str):
                    normalized.append(
                        {
                            "path": file_path,
                            "title": file_entry,
                            "section": section_names["direct_files"],
                        }
                    )
                elif isinstance(file_entry, dict):
                    normalized.append(
                        {
                            "path": file_path,
                            "title": file_entry.get("title", Path(file_path).stem),
                            "section": file_entry.get(
                                "section", section_names["direct_files"]
                            ),
                            "height": file_entry.get("height", default_embed_height),
                        }
                    )
            return normalized

        elif isinstance(direct_files, list):
            normalized = []
            for entry in direct_files:
                if not isinstance(entry, dict):
                    raise ValueError("List entries must be dictionaries")
                if "path" not in entry:
                    raise ValueError("Each list entry must have a 'path' key")
                ext = Path(entry["path"]).suffix.lower()
                if ext not in _allowed:
                    print(f"⚠️  Skipping unsupported file type: {entry['path']}")
                    continue
                if "title" not in entry:
                    entry["title"] = Path(entry["path"]).stem
                if "section" not in entry:
                    entry["section"] = section_names["direct_files"]
                if "height" not in entry:
                    entry["height"] = default_embed_height
                normalized.append(entry)
            return normalized
        else:
            raise ValueError("direct_files must be dict or list")

    def image_to_base64(image_path, sql_file_dir):
        """Convert image file to base64 data URI"""
        try:
            if not Path(image_path).is_absolute():
                image_path = sql_file_dir / image_path
            image_path = Path(image_path)
            if not image_path.exists():
                return None
            ext = image_path.suffix.lower()
            mime_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".svg": "image/svg+xml",
            }
            mime_type = mime_types.get(ext, "image/png")
            with open(image_path, "rb") as f:
                image_data = f.read()
            base64_data = base64.b64encode(image_data).decode("utf-8")
            return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            return None

    def read_file_to_dataframe(file_path):
        return pd.read_parquet(file_path)

    def get_cache_filename(query_id):
        """Get cache filename using numeric ID"""
        return f"{query_id}.parquet"

    def load_or_read_file(file_path, query_id, cache_path):
        cache_file = cache_path / get_cache_filename(query_id)
        if cache and cache_file.exists() and not force_refresh:
            print(f"📦 Cache hit: {query_id}")
            try:
                return pd.read_parquet(cache_file), None
            except Exception as e:
                print(f"⚠️  Cache read error: {e}")
        print(f"📁 Reading file: {file_path}")
        try:
            df = read_file_to_dataframe(file_path)
            if cache:
                df.to_parquet(cache_file, index=False)
            return df, None
        except Exception as e:
            return None, str(e)

    def parse_sql_file(file_path):
        """Parse SQL file.

        Supports a skip-block directive:
            --skip-start
            select * from heavy_table;
            --skip-end
        Any -- query titles and SQL lines between --skip-start and --skip-end
        are completely ignored — they never reach the database.
        """
        sql_path = Path(file_path)
        sql_file_dir = sql_path.parent
        with open(sql_path, "r", encoding="utf-8") as f:
            content = f.read()
        queries = {}
        current_table = None
        current_query_title = None
        current_query = []
        current_image = None
        pending_image = None
        skip_mode = False  # True when inside --skip-start / --skip-end
        lines = content.split("\n")
        lines.append("__END__")
        for line in lines:
            line_stripped = line.strip()

            # ── skip-block directives ──────────────────────────────────────────
            if line_stripped.lower() == "--skip-start":
                # Flush any query collected before the skip block
                if current_table and current_query_title and current_query:
                    query_text = "\n".join(current_query).strip()
                    if query_text:
                        queries[current_table].append(
                            {
                                "title": current_query_title,
                                "query": query_text,
                                "image": current_image,
                            }
                        )
                current_query_title = None
                current_query = []
                current_image = None
                skip_mode = True
                print(f"  ⏭️  Skip block start")
                continue

            if line_stripped.lower() == "--skip-end":
                skip_mode = False
                print(f"  ✅  Skip block end")
                continue

            # Drop everything inside a skip block
            if skip_mode:
                continue

            # ── normal parsing ─────────────────────────────────────────────────
            if line_stripped == "__END__":
                if current_table and current_query_title and current_query:
                    query_text = "\n".join(current_query).strip()
                    if query_text:
                        queries[current_table].append(
                            {
                                "title": current_query_title,
                                "query": query_text,
                                "image": current_image,
                            }
                        )
                break

            table_match = re.match(r"/\*\s*(.+?)\s*\*/", line_stripped)
            if table_match:
                if current_table and current_query_title and current_query:
                    query_text = "\n".join(current_query).strip()
                    if query_text:
                        queries[current_table].append(
                            {
                                "title": current_query_title,
                                "query": query_text,
                                "image": current_image,
                            }
                        )
                current_table = table_match.group(1).strip()
                queries[current_table] = []
                current_query_title = None
                current_query = []
                current_image = None
                pending_image = None
                continue

            image_match = re.match(r"--\s*#\s*(.+)", line_stripped)
            if image_match and current_table:
                if current_query_title and current_query:
                    query_text = "\n".join(current_query).strip()
                    if query_text:
                        queries[current_table].append(
                            {
                                "title": current_query_title,
                                "query": query_text,
                                "image": current_image,
                            }
                        )
                image_path = image_match.group(1).strip()
                pending_image = (
                    image_to_base64(image_path, sql_file_dir)
                    if include_images
                    else None
                )
                current_query_title = None
                current_query = []
                current_image = None
                continue

            if (
                line_stripped.startswith("--")
                and current_table
                and not line_stripped.startswith("-- #")
            ):
                # ── chart embed directives ─────────────────────────────────────
                # Pattern 1 (legacy):  -- ##-add-html-"path" [height=N]
                # Pattern 2 (new):     --@ path/to/chart.html [height=N]
                #   mirrors the image directive (-- # path) — no quotes needed
                add_html_match = re.match(
                    r'--\s*##-add-html-["\'](.+?)["\'](?:\s+height=(\d+))?',
                    line_stripped,
                    re.IGNORECASE,
                ) or re.match(
                    r'--@\s+["\']?(.+?\.html)["\']?(?:\s+height=(\d+))?$',
                    line_stripped,
                    re.IGNORECASE,
                )
                if add_html_match:
                    # Flush current query first
                    if current_query_title and current_query:
                        query_text = "\n".join(current_query).strip()
                        if query_text:
                            queries[current_table].append(
                                {
                                    "title": current_query_title,
                                    "query": query_text,
                                    "image": current_image,
                                }
                            )
                    current_query_title = None
                    current_query = []
                    current_image = None
                    chart_path = add_html_match.group(1).strip()
                    chart_height = (
                        int(add_html_match.group(2))
                        if add_html_match.group(2)
                        else default_embed_height
                    )
                    queries[current_table].append(
                        {
                            "title": Path(chart_path).stem,
                            "query": None,
                            "image": None,
                            "chart_html": embed_html_chart(
                                chart_path, chart_height, chart_counter[0]
                            ),
                        }
                    )
                    chart_counter[0] += 1
                    continue
                # ── regular -- query title ─────────────────────────────────────
                if current_query_title and current_query:
                    query_text = "\n".join(current_query).strip()
                    if query_text:
                        queries[current_table].append(
                            {
                                "title": current_query_title,
                                "query": query_text,
                                "image": current_image,
                            }
                        )
                current_query_title = line_stripped[2:].strip()
                current_query = []
                current_image = pending_image
                pending_image = None
                continue

            if current_table and current_query_title:
                if ";" in line:
                    before_semicolon = line.split(";")[0]
                    if before_semicolon.strip():
                        current_query.append(before_semicolon)
                    query_text = "\n".join(current_query).strip()
                    if query_text:
                        queries[current_table].append(
                            {
                                "title": current_query_title,
                                "query": query_text,
                                "image": current_image,
                            }
                        )
                    current_query_title = None
                    current_query = []
                    current_image = None
                else:
                    current_query.append(line.rstrip())
        return queries

    def setup_cache_folder():
        today = datetime.now().strftime("%Y%m%d")
        cache_path = Path(cache_folder) / today
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    def execute_or_load_query(query_id, query_title, query, cache_path):
        cache_file = cache_path / get_cache_filename(query_id)
        if cache and cache_file.exists() and not force_refresh:
            print(f"📦 Cache hit: {query_id} ({query_title})")
            try:
                return pd.read_parquet(cache_file), None
            except Exception as e:
                print(f"⚠️  Cache error: {e}")
        print(f"⏳ Executing: {query_id} ({query_title})")
        try:
            # df = pd.read_sql(query, database_connection)
            df = database_connection.execute(query).fetchdf()
            if cache:
                df.to_parquet(cache_file, index=False)
            return df, None
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return None, str(e)

    def format_value(value, format_string):
        if pd.isna(value):
            return ""
        try:
            if format_string.startswith("%"):
                return pd.to_datetime(value).strftime(format_string)
            else:
                return format_string.format(value)
        except Exception:
            return str(value)

    def format_dataframe_for_display(df, table_name):
        df_display = df.copy()
        global_formats_lower = {k.lower(): v for k, v in global_column_formats.items()}
        override_formats_lower = {
            (k[0].lower(), k[1].lower()): v for k, v in override_column_formats.items()
        }
        for col in df_display.columns:
            col_str = str(col)
            col_lower = col_str.lower()
            override_key = (table_name.lower(), col_lower)
            if override_key in override_formats_lower:
                fmt = override_formats_lower[override_key]
                df_display[col] = df_display[col].apply(lambda x: format_value(x, fmt))
                continue
            if col_lower in global_formats_lower:
                fmt = global_formats_lower[col_lower]
                df_display[col] = df_display[col].apply(lambda x: format_value(x, fmt))
        return df_display

    def df_to_html_table(
        df, table_name, query_id, max_rows, stored_rows, full_data_json=None
    ):
        """Convert DataFrame to HTML with optional full data embedding,
        height capping, and cell text truncation."""
        total_rows = len(df)

        actual_stored_rows = min(stored_rows, total_rows)
        rows_to_render = actual_stored_rows
        actual_max_rows = min(max_rows, rows_to_render)
        total_cols = len(df.columns)

        df_display = df.head(rows_to_render)
        df_formatted = format_dataframe_for_display(df_display, table_name)

        html = ""

        # Embed compressed full data if available
        if embed_full_data and full_data_json:
            columns_json = [str(col) for col in df.columns]
            columns_js = "[" + ", ".join([f"'{col}'" for col in columns_json]) + "]"

            html += f"""
            <script>
            // Embedded full dataset for {query_id}
            window.fullDataCompressed_{query_id} = '{full_data_json}';
            window.fullDataColumns_{query_id} = {columns_js};
            window.fullDataRows_{query_id} = {total_rows};
            console.log('☑️ Embedded compressed data for {query_id}: {total_rows:,} rows');
            </script>"""

        show_col_search = include_column_search and total_cols > column_search_threshold
        show_row_search = include_row_search and rows_to_render > row_search_threshold

        if show_col_search or show_row_search:
            html += (
                '<div class="search-container" id="search-container-'
                + query_id
                + '">\n'
            )
            if show_col_search:
                html += f"""    <div class="column-search-box">
        <input type="text" class="search-input" id="col-search-{query_id}"
                    placeholder="🔍 Filter columns..."
                    onkeyup="filterColumns('{query_id}')">
        <span class="search-count" id="col-count-{query_id}">Showing {total_cols} of {total_cols} columns</span>
                </div>"""
            if show_row_search:
                if embed_full_data and full_data_json:
                    search_info = f"all {total_rows:,}"
                    row_info = f"Showing {actual_max_rows:,} of {total_rows:,} rows"
                else:
                    search_info = f"{actual_stored_rows:,}"
                    row_info = (
                        f"Showing {actual_max_rows:,} of {actual_stored_rows:,} rows"
                    )

                html += f"""    <div class="row-search-box" id="row-search-{query_id}">
        <input type="text" class="search-input"
                    placeholder="▼ Search {search_info} rows..."
                    onkeyup="filterRows('{query_id}', {actual_max_rows})">
        <span class="search-count" id="row-count-{query_id}">{row_info}</span>
                </div>"""
            html += "</div>\n"

        # Decide whether to apply height cap for this table
        apply_height_cap = (
            max_table_height is not None and actual_stored_rows > table_scroll_threshold
        )
        wrapper_style = ""
        if apply_height_cap:
            wrapper_style = f' style="max-height:{max_table_height}; overflow-y:auto;"'

        html += f"""<div class="table-wrapper"{wrapper_style} id="table-wrapper-{query_id}">
            <table class="data-table {row_density}-density" id="table-{query_id}" style="font-family:{table_font_family};font-size:{table_font_size};">
                <thead><tr>"""

        _freeze_set = set(c.lower() for c in freeze_columns)
        for col in df_formatted.columns:
            freeze_attr = (
                ' data-freeze-column="true"' if str(col).lower() in _freeze_set else ""
            )
            html += f"""<th data-column="{str(col).lower()}"{freeze_attr}>{col}<span class="sort-indicator">⇅</span></th>"""

        html += """</tr></thead><tbody>"""

        for idx, row in df_formatted.iterrows():
            row_class = ' class="initially-hidden"' if idx >= actual_max_rows else ""
            html += f'<tr data-row-id="{idx}"{row_class}>\n'
            for col, val in zip(df_formatted.columns, row):
                col_lower = str(col).lower()
                freeze_attr = (
                    ' data-freeze-column="true"' if col_lower in _freeze_set else ""
                )
                cell_str = (
                    str(val)
                    if val is not None and not (isinstance(val, float) and pd.isna(val))
                    else ""
                )
                if truncate_cell_text and len(cell_str) > max_cell_chars:
                    truncated = cell_str[:max_cell_chars]
                    if enable_cell_expansion:
                        escaped_full = (
                            cell_str.replace("&", "&amp;")
                            .replace('"', "&quot;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )
                        html += (
                            f'<td data-column="{col_lower}"{freeze_attr} '
                            f'class="cell-truncated" '
                            f'data-full-text="{escaped_full}" '
                            f'onclick="expandCell(this)" '
                            f'title="Click to expand">'
                            f'{truncated}<span class="truncation-indicator">…</span></td>\n'
                        )
                    else:
                        html += f'<td data-column="{col_lower}"{freeze_attr}>{truncated}<span class="truncation-indicator">…</span></td>\n'
                else:
                    html += (
                        f'<td data-column="{col_lower}"{freeze_attr}>{cell_str}</td>\n'
                    )
            html += "<tr>\n"

        html += """</tbody></table></div>"""
        return html

    def generate_report_header_html(report_header):
        """Generate HTML for report header section"""
        if not report_header:
            return ""

        html = """<div class="report-header">"""

        if report_header.get("title"):
            html += f"""<h1 class="report-title">{report_header["title"]}</h1>"""

        if report_header.get("subtitle"):
            html += f"""<h2 class="report-subtitle">{report_header["subtitle"]}</h2>"""

        if report_header.get("metadata"):
            html += """<div class="report-metadata">"""
            for key, value in report_header["metadata"].items():
                html += f"""<span class="metadata-badge"><strong>{key}:</strong> {value}</span>"""
            html += """</div>"""

        if report_header.get("description"):
            description = report_header["description"]
            paragraphs = description.split("\n\n")
            html += """<div class="report-description">"""
            for para in paragraphs:
                if para.strip():
                    html += f"""<p>{para.strip()}</p>"""
            html += """</div>"""

        html += """</div>"""
        return html

    def generate_report_footer_html(report_footer):
        """Generate HTML for report footer section"""
        if not report_footer:
            return ""

        html = """<div class="report-footer">"""

        if report_footer.get("title"):
            html += f"""<h3 class="footer-title">{report_footer["title"]}</h3>"""

        if report_footer.get("content"):
            content = report_footer["content"]
            paragraphs = content.split("\n\n")
            html += """<div class="footer-content">"""
            for para in paragraphs:
                if para.strip():
                    html += f"""<p>{para.strip()}</p>"""
            html += """</div>"""

        html += """</div>"""
        return html

    def generate_html(query_results, pako_js_content, report_header):
        """Generate complete HTML"""
        pako_script = ""
        if pako_js_content:
            pako_script = f"<script>\n{pako_js_content}\n</script>"
        else:
            print(
                "⚠️️  WARNING: pako.js not embedded - full search will NOT work for large datasets"
            )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        *{{margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg-color: {light_mode_colors["bg"]};
            --text-color: {light_mode_colors["text"]};
            --sidebar-bg: {light_mode_colors["sidebar_bg"]};
            --table-header-bg: {light_mode_colors["table_header"]};
            --accent-color: {light_mode_colors["accent"]};
            --border-color: {light_mode_colors["border"]};
            --hover-color: {light_mode_colors["hover"]};
            --button-bg: #4a90e2;
            --button-text: #ffffff;
            --button-hover: #357abd;
            --success-bg: #28a745;
            --error-bg: #dc3545;
        }}

        [data-theme="dark"] {{
            --bg-color: {dark_mode_colors["bg"]};
            --text-color: {dark_mode_colors["text"]};
            --sidebar-bg: {dark_mode_colors["sidebar_bg"]};
            --table-header-bg: {dark_mode_colors["table_header"]};
            --accent-color: {dark_mode_colors["accent"]};
            --border-color: {dark_mode_colors["border"]};
            --hover-color: {dark_mode_colors["hover"]};
            --button-bg: #5b9dd9;
            --success-bg: #34c759;
            --error-bg: #ff3b30;
        }}

        body {{
            font-family: {page_font if page_font else "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"};
            font-size: {page_font_size if page_font_size else '14px'};
            background-color: var(--bg-color);
            color: var(--text-color);
            padding-left: {'40px' if sidebar_collapsible else sidebar_width};
            min-height: 100vh;
            transition: all 0.3s;
        }}

        .sidebar {{
            position: fixed;
            top: 0;
            left: 0;
            width: {sidebar_width};
            height: 100vh;
            background-color: var(--sidebar-bg);
            overflow-y: auto;
            padding: 20px 10px;
            box-shadow: 2px 0 5px rgba(0,0,0,0.1);
            z-index: 1000;
        }}

        .sidebar-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            /*border-bottom: 2px solid var(--accent-color);*/
        }}

        .sidebar-title {{
            font-size: 18px;
            font-weight: bold;
            color: var(--accent-color);
        }}

        /* ── Search box ── */
        .search-box {{
            margin-bottom: 10px;
        }}

        .search-wrap {{
            position: relative;
            display: flex;
            align-items: center;
        }}

        .search-input {{
            flex: 1;
            min-width: 0;
            width: 100%;
            padding: 7px 26px 7px 10px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 12px;
            background-color: var(--bg-color);
            color: var(--text-color);
            transition: all 0.2s;
        }}

        .search-input:focus {{
            outline: none;
            border-color: var(--accent-color);
            box-shadow: 0 0 0 2px rgba(0,123,255,0.1);
        }}

        .search-clear {{
            position: absolute;
            right: 6px;
            background: none;
            border: none;
            color: var(--text-color);
            cursor: pointer;
            font-size: 13px;
            padding: 2px 3px;
            opacity: 0;
            transition: opacity 0.15s;
            line-height: 1;
            z-index: 1;
        }}
        .search-clear.visible {{ opacity: 0.6; }}
        .search-clear:hover {{ opacity: 1 !important; }}

        /* ── Icon group below search ── */
        .search-icon-group {{
            display: flex;
            align-items: center;
            gap: 2px;
            flex-shrink: 0;
            margin-top: 4px;
        }}

        .search-icon-btn {{
            background: none;
            border: none;
            color: var(--text-color);
            cursor: pointer;
            padding: 4px 5px;
            border-radius: 4px;
            opacity: 0.5;
            transition: opacity 0.15s, background 0.15s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
        }}
        .search-icon-btn:hover {{
            opacity: 1;
            background: var(--hover-color);
        }}

        /* ── Help tooltip ── */
        .help-tooltip {{
            display: none;
            background: var(--sidebar-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 10px;
            margin-top: 6px;
            font-size: 11px;
            color: var(--text-color);
        }}
        .help-tooltip.visible {{ display: block; }}
        .help-row {{
            display: flex;
            align-items: center;
            gap: 5px;
            margin: 3px 0;
        }}
        kbd {{
            display: inline-block;
            padding: 1px 5px;
            border: 1px solid var(--border-color);
            border-radius: 3px;
            font-size: 10px;
            font-family: monospace;
            background: var(--hover-color);
            color: var(--text-color);
            line-height: 1.5;
        }}

        .search-count {{
            font-size: 11px;
            color: var(--text-color);
            margin-top: 4px;
            display: block;
            opacity: 0.7;
        }}

        /* ── Collapsible nav groups ── */
        .nav-group {{
            display: flex;
            flex-direction: column;
        }}
        .nav-group-header {{
            display: flex;
            align-items: center;
            gap: 0;
            border-radius: 4px;
            transition: background-color 0.15s;
            cursor: pointer;
            user-select: none;
        }}
        .nav-group-header:hover {{
            background-color: var(--hover-color);
        }}
        .nav-group-children {{
            display: block;
            padding-left: 12px;
        }}
        .nav-group-children.collapsed {{
            display: none;
        }}
        .nav-toggle-icon {{
            display: inline-flex;
            align-items: center;
            padding: 2px 3px 2px 4px;
            flex-shrink: 0;
            opacity: 0.45;
            transition: opacity 0.15s;
            fill: var(--text-color);
        }}
        .nav-group-header:hover .nav-toggle-icon {{ opacity: 0.9; }}

        /* Navigation links */
        .nav-links {{
            display: flex;
            flex-direction: column;
            gap: 1px;
        }}

        .nav-link {{
            color: var(--text-color);
            text-decoration: none;
            padding: 6px 10px 6px 6px;
            border-radius: 4px;
            border-left: 2px solid transparent;
            transition: color 0.15s, border-color 0.15s;
            display: block;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: {(nav_font_sizes or {}).get(2, '13px')};
            font-weight: 600;
            flex: 1;
            min-width: 0;
        }}
        .nav-link:link,
        .nav-link:visited {{
            color: var(--text-color);
            text-decoration: none;
        }}

        .nav-link:hover {{
            color: var(--accent-color);
        }}

        .nav-group-header:hover .nav-link {{
            color: var(--accent-color);
        }}

        .nav-link.hidden {{
            display: none;
        }}

        .nav-link.sub-link {{
            padding-left: 18px;
            font-size: {(nav_font_sizes or {}).get(4, '12px')};
            font-weight: 400;
            opacity: 0.75;
        }}

        .nav-link.active {{
            color: var(--accent-color);
            font-weight: 600;
            border-left-color: var(--accent-color);
        }}

        .nav-link.sub-link.active {{
            color: var(--accent-color);
            border-left-color: var(--accent-color);
            opacity: 1;
        }}

        /* Search highlighting in navigation */
        .nav-link.search-hidden {{
            display: none;
        }}

        /* Level 2: group label (/* Table Name */) */
        .nav-group-label {{
            display: block;
            padding: 5px 10px 3px 8px;
            font-size: {(nav_font_sizes or {}).get(3, '12.5px')};
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--text-color);
            opacity: 0.85;
            margin-top: 8px;
            text-decoration: none;
            border-radius: 3px;
            transition: color 0.15s;
        }}
        .nav-group-label:link,
        .nav-group-label:visited {{
            color: var(--text-color);
            text-decoration: none;
        }}
        .nav-group-label:hover {{
            color: var(--accent-color);
        }}

        .nav-group-label.search-hidden {{
            display: none;
        }}

        .main-content {{
            padding: 30px;
            max-width: 1400px;
            margin: 0 auto;
        }}

        .report-header {{
            background-color: var(--bg-color);
            padding: 30px 0;
            margin-bottom: 30px;
        }}

        .report-title {{
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 8px;
            color: var(--text-color);
        }}

        .report-subtitle {{
            font-size: 18px;
            font-weight: normal;
            margin-bottom: 15px;
            color: var(--text-color);
            opacity: 0.8;
        }}

        .report-metadata {{
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-bottom: 15px;
            padding: 8px 0;
        }}

        .metadata-badge {{
            background-color: transparent;
            color: var(--text-color);
            padding: 0;
            font-size: 14px;
        }}

        .metadata-badge strong {{
            font-weight: 600;
            color: var(--text-color);
        }}

        .report-description {{
            font-size: 15px;
            line-height: 1.6;
            color: var(--text-color);
            padding: 0;
        }}

        .report-description p {{
            margin-bottom: 12px;
            color: var(--text-color);
        }}

        .report-description p:last-child {{
            margin-bottom: 0;
        }}

        .report-footer {{
            background-color: var(--bg-color);
            padding: 30px 0;
            margin-top: 50px;
            border-top: 2px solid var(--border-color);
        }}

        .footer-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 8px;
            color: var(--text-color);
        }}

        .footer-content {{
            font-size: 14px;
            line-height: 1.6;
            color: var(--text-color);
            opacity: 0.8;
        }}

        .footer-content p {{
            margin-bottom: 10px;
            color: var(--text-color);
        }}

        .footer-content p:last-child {{
            margin-bottom: 0;
        }}

        .result-section {{
            margin-bottom: 50px;
            scroll-margin-top: 20px;
        }}

        /* Level 2 group divider — /* Table Name */ rendered once per group */
        .result-group {{
            margin-bottom: 40px;
        }}

        .result-group-heading {{
            font-size: {(heading_font_sizes or {}).get(3, "20px")};
            font-weight: 600;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            color: var(--accent-color);
            opacity: 0.8;
            padding-bottom: 6px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 18px;
            margin-top: 8px;
        }}

        .result-section-title {{
            font-size: {(heading_font_sizes or {}).get(2, "22px")};
            font-weight: 700;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--accent-color);
        }}

        .result-title {{
            font-size: {(heading_font_sizes or {}).get(4, "15px")};;
            font-weight: 600;
            margin-bottom: 5px;
        }}

        .result-subtitle {{
            font-size: 16px;
            color: var(--accent-color);
            font-weight: 500;
        }}

        .embedded-image {{ margin: 20px 0; }}

        .embedded-image img {{
            max-width: {max_image_width};
            height: auto;
            border: 1px solid var(--border-color);
            border-radius: 6px;
        }}

        /* ── Search bars — minimal single-line style ── */
        .search-container {{
            display: flex;
            flex-direction: row;
            gap: 12px;
            margin-bottom: 10px;
        }}

        .column-search-box, .row-search-box {{
            flex: 1;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0;
            background: none;
            border: none;
        }}

        .search-input {{
            flex: 1;
            padding: 5px 10px;
            border: none;
            border-bottom: 1px solid var(--border-color);
            border-radius: 0;
            font-size: 12px;
            background: transparent;
            color: var(--text-color);
            transition: border-color 0.2s;
        }}

        .search-input:focus {{
            outline: none;
            border-bottom-color: var(--accent-color);
        }}

        .search-count {{
            font-size: 11px;
            white-space: nowrap;
            opacity: 0.55;
        }}

        .query-details {{
            border: 1px solid var(--border-color);
            border-radius: 6px;
            margin-bottom: 15px;
        }}

        .query-details summary {{
            padding: 10px 15px;
            background-color: var(--sidebar-bg);
            cursor: pointer;
            font-weight: 500;
            display: flex;
            align-items: center;
            justify-content: space-between;
            list-style: none;
            user-select: none;
        }}

        .query-details summary::-webkit-details-marker {{ display: none; }}

        .query-details summary span {{ flex: 1; }}

        /* Copy button hidden until hover on summary */
        .query-details summary .code-btn {{
            opacity: 0;
            transition: opacity 0.2s;
        }}
        .query-details summary:hover .code-btn {{
            opacity: 1;
        }}

        .code-btn {{
            background: none;
            border: none;
            color: var(--text-color);
            cursor: pointer;
            padding: 4px;
            border-radius: 3px;
            transition: all 0.2s;
            line-height: 1;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
        }}

        .code-btn:hover {{ background-color: var(--hover-color); }}

        .code-btn svg {{
            width: 14px;
            height: 14px;
            fill: currentColor;
        }}

        .embedded-chart-wrapper {{
            margin: 16px 0;
        }}

        /* Embedded chart: visible overflow for axis labels, clip at wrapper to suppress scrollbar */
        .embedded-chart {{
            overflow-x: clip;
        }}

        /* ── Query code block ── */
        .query-code {{
            margin-top: 10px;
            margin-bottom: 16px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            overflow: hidden;
            background-color: var(--sidebar-bg);
        }}

        .query-code-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 5px 12px;
            background-color: var(--sidebar-bg);
            border-bottom: 1px solid var(--border-color);
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            opacity: 0.55;
        }}

        .query-code pre {{
            font-family: 'Consolas', 'SF Mono', 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
            color: var(--text-color);
            padding: 12px 16px;
            margin: 0;
            overflow-x: auto;
            overflow-y: auto;
            max-height: {default_code_height};
            white-space: pre;
            scrollbar-width: thin;
            scrollbar-color: rgba(120,120,120,0.3) transparent;
        }}

        .query-code pre::-webkit-scrollbar {{ width: 4px; height: 4px; }}
        .query-code pre::-webkit-scrollbar-track {{ background: transparent; }}
        .query-code pre::-webkit-scrollbar-thumb {{
            border-radius: 999px;
            background: rgba(120,120,120,0.25);
        }}
        [data-theme="dark"] .query-code pre::-webkit-scrollbar-thumb {{
            background: rgba(200,200,200,0.18);
        }}

        .copy-code-btn {{
            background: none;
            border: none;
            cursor: pointer;
            color: var(--text-color);
            opacity: 0.45;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            letter-spacing: 0.04em;
            transition: opacity 0.2s;
        }}
        .copy-code-btn:hover {{ opacity: 1; }}

        /* ── Row density ── */
        .data-table.normal-density th       {{ padding: {density_settings["normal"]["th_padding"]}; }}
        .data-table.normal-density td       {{ padding: {density_settings["normal"]["td_padding"]}; }}
        .data-table.compact-density th      {{ padding: {density_settings["compact"]["th_padding"]}; }}
        .data-table.compact-density td      {{ padding: {density_settings["compact"]["td_padding"]}; }}
        .data-table.ultracompact-density th {{ padding: {density_settings["ultracompact"]["th_padding"]}; }}
        .data-table.ultracompact-density td {{ padding: {density_settings["ultracompact"]["td_padding"]}; }}

        /* ── Freeze columns ── */
        .data-table th[data-freeze-column="true"] {{
            background-color: var(--accent-color);
            color: #fff;
            border-bottom-color: var(--accent-color);
        }}
        .data-table th[data-freeze-column="true"]:hover {{ filter: brightness(1.1); }}
        .data-table td[data-freeze-column="true"] {{
            background-color: var(--hover-color);
            font-weight: 500;
        }}
        .data-table tbody tr:hover td[data-freeze-column="true"] {{
            background-color: var(--border-color);
        }}

        .table-wrapper {{
            overflow-x: auto;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            margin-bottom: 20px;
        }}

        /* Modern minimal scrollbars — webkit (Chrome, Safari, Edge) */
        .table-wrapper::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}
        .table-wrapper::-webkit-scrollbar-track {{
            background: transparent;
        }}
        .table-wrapper::-webkit-scrollbar-thumb {{
            border-radius: 999px;
            background: rgba(120, 120, 120, 0.25);
            transition: background 0.2s;
        }}
        .table-wrapper::-webkit-scrollbar-thumb:hover {{
            background: rgba(120, 120, 120, 0.5);
        }}
        .table-wrapper::-webkit-scrollbar-corner {{
            background: transparent;
        }}

        /* Dark mode scrollbar thumb — slightly lighter so it's visible on dark tracks */
        [data-theme="dark"] .table-wrapper::-webkit-scrollbar-thumb {{
            background: rgba(200, 200, 200, 0.18);
        }}
        [data-theme="dark"] .table-wrapper::-webkit-scrollbar-thumb:hover {{
            background: rgba(200, 200, 200, 0.38);
        }}

        /* Firefox */
        .table-wrapper {{
            scrollbar-width: thin;
            scrollbar-color: rgba(120, 120, 120, 0.3) transparent;
        }}
        [data-theme="dark"] .table-wrapper {{
            scrollbar-color: rgba(200, 200, 200, 0.2) transparent;
        }}

        .data-table {{
            border-collapse: collapse;
            font-size: 14px;
            white-space: nowrap;
        }}

        .data-table td {{
            white-space: nowrap;
        }}

        .data-table thead {{
            background-color: var(--table-header-bg);
            position: sticky;
            top: 0;
            z-index: 10;
        }}

        .data-table th {{
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid var(--border-color);
            cursor: pointer;
            user-select: none;
            background-color: var(--table-header-bg);
            white-space: nowrap;
            padding: 8px 20px 8px 8px;
        }}

        .data-table th:hover {{ background-color: var(--hover-color); }}

        .sort-indicator {{
            font-size: 11px;
            margin-left: 5px;
            opacity: 0.3;
        }}

        .data-table td {{
            border-bottom: 1px solid var(--border-color);
            white-space: nowrap;
        }}

        .data-table tbody tr:hover {{ background-color: var(--hover-color); }}

        .data-table th.hidden-column, .data-table td.hidden-column {{ display: none; }}
        .data-table tr.hidden-row {{ display: none; }}
        .data-table tr.initially-hidden {{ display: none; }}
        .data-table tr.initially-hidden.search-match {{ display: table-row; }}

        /* Cell truncation */
        .truncation-indicator {{
            color: var(--accent-color);
            font-weight: bold;
            font-size: 12px;
        }}

        td.cell-truncated {{
            cursor: pointer;
            max-width: 300px;
        }}

        td.cell-truncated:hover {{
            background-color: var(--hover-color);
            outline: 1px solid var(--accent-color);
        }}

        /* Cell expansion modal */
        .cell-modal-overlay {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.45);
            z-index: 9000;
            align-items: center;
            justify-content: center;
        }}

        .cell-modal-overlay.active {{
            display: flex;
        }}

        .cell-modal {{
            background: var(--bg-color);
            color: var(--text-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 24px;
            max-width: min(700px, 90vw);
            max-height: 70vh;
            overflow-y: auto;
            box-shadow: 0 8px 32px rgba(0,0,0,0.25);
            position: relative;
            word-break: break-word;
            white-space: pre-wrap;
            font-size: 14px;
            line-height: 1.6;
        }}

        .cell-modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }}

        .cell-modal-column {{
            font-weight: 600;
            font-size: 13px;
            color: var(--accent-color);
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        .cell-modal-close {{
            background: none;
            border: 1px solid var(--border-color);
            color: var(--text-color);
            cursor: pointer;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 16px;
            line-height: 1;
        }}

        .cell-modal-close:hover {{ background-color: var(--hover-color); }}

        .error-container {{
            border: 2px solid #dc3545;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
        }}

        .error-title {{
            color: #dc3545;
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 10px;
        }}

        .error-message {{
            padding: 15px;
            font-family: monospace;
            color: #dc3545;
        }}

        /* Scrollbar appears only on hover */
        .sidebar {{
            scrollbar-width: thin;
            scrollbar-color: transparent transparent;
            transition: scrollbar-color 0.3s ease;
        }}

        .sidebar:hover {{
            scrollbar-color: rgba(120, 120, 120, 0.3) transparent;
        }}

        .sidebar::-webkit-scrollbar {{
            width: 8px;
        }}

        .sidebar::-webkit-scrollbar-track {{
            background: transparent;
        }}

        .sidebar::-webkit-scrollbar-thumb {{
            background: transparent;
            border-radius: 10px;
            transition: background 0.2s ease;
        }}

        .sidebar:hover::-webkit-scrollbar-thumb {{
            background: rgba(120, 120, 120, 0.3);
        }}

        .sidebar:hover::-webkit-scrollbar-thumb:hover {{
            background: rgba(120, 120, 120, 0.5);
        }}

        [data-theme="dark"] .sidebar:hover {{
            scrollbar-color: rgba(200, 200, 200, 0.2) transparent;
        }}

        [data-theme="dark"] .sidebar:hover::-webkit-scrollbar-thumb {{
            background: rgba(200, 200, 200, 0.2);
        }}

        [data-theme="dark"] .sidebar:hover::-webkit-scrollbar-thumb:hover {{
            background: rgba(200, 200, 200, 0.35);
        }}

        
        /* — collapsible sidebar: floating nav rail + popover panel — */
        .sidebar-collapsed-strip {{
            display: {'flex' if sidebar_collapsible else 'none'};
            position: fixed;
            top: 0;
            left: 0;
            width: 40px;
            height: 100vh;
            flex-direction: column;
            align-items: center;
            padding-top: 14px;
            z-index: 1001;
            pointer-events: none;
        }}

        .sidebar-collapsed-strip > * {{
            pointer-events: auto;
        }}

        .sidebar-contents-badge {{
            background: var(--sidebar-bg);
            color: var(--text-color);
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            padding: 6px 4px;
            border-radius: 4px;
            cursor: pointer;
            user-select: none;
            writing-mode: vertical-rl;
            text-orientation: mixed;
            transform: rotate(180deg);
            border: 1px solid var(--border-color);
            opacity: 0.85;
            transition: opacity 0.2s, background 0.2s;
            margin-bottom: 8px;
        }}

        .sidebar-contents-badge:hover {{
            opacity: 1;
            background: var(--hover-color);
        }}

        .sidebar-nav-dots {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            margin-top: 4px;
        }}

        .sidebar-nav-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--border-color);
            cursor: pointer;
            transition: background 0.2s, transform 0.2s;
            position: relative;
        }}

        .sidebar-nav-dot:hover {{
            background: var(--accent-color);
            transform: scale(1.4);
        }}

        .sidebar-nav-dot.active {{
            background: var(--accent-color);
            transform: scale(1.3);
        }}

        .sidebar-nav-dot-tooltip {{
            display: none;
            position: absolute;
            left: 18px;
            top: 50%;
            transform: translateY(-50%);
            background: var(--sidebar-bg);
            color: var(--text-color);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 11px;
            white-space: nowrap;
            pointer-events: none;
            z-index: 1003;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}

        .sidebar-nav-dot:hover .sidebar-nav-dot-tooltip {{
            display: block;
        }}

        .sidebar-backdrop {{
            display: none;
            position: fixed;
            inset: 0;
            z-index: 999;
        }}

        .sidebar-backdrop.active {{
            display: block;
        }}

        .sidebar.collapsible {{
            position: fixed;
            top: 10px;
            left: 44px;
            width: min({sidebar_width}, calc(100vw - 60px));
            height: auto;
            max-height: calc(100vh - 20px);
            border-radius: 10px;
            border: 1px solid var(--border-color);
            box-shadow: 0 8px 32px rgba(0,0,0,0.18);
            transform: scale(0.95);
            opacity: 0;
            pointer-events: none;
            z-index: 1002;
            transition: transform 0.2s cubic-bezier(0.4,0,0.2,1), opacity 0.2s;
            overflow-y: auto;
        }}

        .sidebar.collapsible.open {{
            transform: scale(1);
            opacity: 1;
            pointer-events: auto;
        }}

</style>
</head>
<body data-theme="{default_theme}">
    <!-- Cell expansion modal -->
    <div class="cell-modal-overlay" id="cellModalOverlay" onclick="closeCellModal(event)">
        <div class="cell-modal" id="cellModal">
            <div class="cell-modal-header">
                <span class="cell-modal-column" id="cellModalColumn"></span>
                <button class="cell-modal-close" onclick="closeCellModalDirect()">✕</button>
            </div>
            <div id="cellModalContent"></div>
        </div>
    </div>
    <div class="sidebar-backdrop" id="sidebar-backdrop" onclick="closeSidebar()"></div>
    <div class="sidebar-collapsed-strip" id="sidebar-strip">
        <span class="sidebar-contents-badge" onclick="toggleSidebar()">Index</span>
        <div class="sidebar-nav-dots" id="sidebar-nav-dots"></div>
    </div>
    <div class="sidebar{' collapsible' if sidebar_collapsible else ''}">
        <div class= "sidebar-header">
        <div class="sidebar-title">{page_title}</div>{"" if not sidebar_collapsible else '<button onclick="closeSidebar()" title="Close navvigation" style="margin-left:auto;background:none;border:none;color:var(--text-color);cursor:pointer;padding:4px 6px;border-radius:4px;opacity:0.5;"><svg width=16" height="16 viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg></button>'}
        </div>
        <div class="search-box">
            <div class="search-wrap">
                <input type="text"
                       class="search-input"
                       id="navSearchInput"
                       placeholder="Search… (F)"
                       title="Press F to focus · Esc to clear · ↑↓ navigate"
                       onkeyup="filterNavigation()"
                       oninput="toggleNavClearButton()">
                <button class="search-clear" id="navSearchClear" onclick="clearNavigationSearch()" title="Clear search (Esc)">×</button>
            </div>
            <div class="search-icon-group">
                <button class="search-icon-btn" title="Expand all" onclick="expandAll()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                    </svg>
                </button>
                <button class="search-icon-btn" title="Collapse all" onclick="collapseAll()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19 13H5v-2h14v2z"/>
                    </svg>
                </button>
                <button class="search-icon-btn" id="themeToggleBtn" title="Toggle light / dark theme (T)" onclick="toggleTheme()">
                    <svg id="theme-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 7a5 5 0 0 1 5 5 5 5 0 0 1-5 5 5 5 0 0 1-5-5 5 5 0 0 1 5-5m0-2a7 7 0 0 0-7 7 7 7 0 0 0 7 7 7 7 0 0 0 7-7 7 7 0 0 0-7-7M2 11h2v2H2v-2m18 0h2v2h-2v-2M11 2h2v2h-2V2m0 18h2v2h-2v-2M4.22 3.93l1.42 1.42-1.42 1.41-1.41-1.41 1.41-1.42m15.14 13.3 1.41 1.41-1.41 1.42-1.42-1.42 1.42-1.41M4.22 19.07l-1.41-1.42 1.41-1.41 1.42 1.41-1.42 1.42M19.36 5.36l-1.42-1.42 1.42-1.41 1.41 1.42-1.41 1.41z"/>
                    </svg>
                </button>
                <button class="search-icon-btn" id="helpBtn" title="Keyboard shortcuts" onclick="toggleHelp()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M8.5 8.5A3.5 3.5 0 1 1 12 12v1"/>
                        <path d="M12 17h.01"/>
                    </svg>
                </button>
            </div>
            <div class="help-tooltip" id="helpTooltip">
                <div class="help-row"><kbd>F</kbd> Focus search box</div>
                <div class="help-row"><kbd>↑</kbd><kbd>↓</kbd> Navigate sidebar links</div>
                <div class="help-row"><kbd>T</kbd> Toggle light / dark</div>
                <div class="help-row"><kbd>Esc</kbd> Clear search / close</div>
                <div class="help-row"><kbd>N</kbd> Focus navigation panel</div>
                <div class="help-row"><kbd>M</kbd> Focus main content</div>
            </div>
            <span class="search-count" id="navSearchStats"></span>
        </div>

        <div class="nav-links" id="mainNav">"""

        # Navigation — section → group-label → query link hierarchy
        for section_type, section_data in query_results.items():
            if not section_data:
                continue
            section_id = section_type.replace(" ", "_").lower()
            grp_id = f"navgrp-{section_id}"
            html += f'''
            <div class="nav-group" id="ng-{section_id}">
              <div class="nav-group-header" onclick="handleNavRowClick(event, '{grp_id}')">
                <span class="nav-toggle-icon"><svg id="ngi-{grp_id}" viewBox="0 0 24 24" width="10" height="10" fill="currentColor"><path d="M19 13H5v-2h14v2z"/></svg></span>
                <a href="#section-{section_id}" class="nav-link" data-section-id="section-{section_id}"><svg width="13" height="13 viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-aligh:-1px;margin-right:4px;"><path d="M14 2H6a2 2 0 0 0-2 2V16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>{section_type}</a>
              </div>
              <div class="nav-group-children" id="{grp_id}">'''

            # Group items by subtitle so we emit the group label once
            seen_groups = []
            for item in section_data:
                group = item.get("subtitle") or ""
                if group and group not in seen_groups:
                    seen_groups.append(group)
                    grp_anchor = f"grp-{section_id}--{group.replace(' ', '_').lower()}"
                    html += f'\n                <a href="#{grp_anchor}" class="nav-group-label">{group}</a>'
                elif not group and "" not in seen_groups:
                    seen_groups.append("")
                error_icon = "⚠️ " if item.get("error") else ""
                html += f'\n                <a href="#{item["query_id"]}" class="nav-link sub-link" data-section-id="{item["query_id"]}" data-query-name="{item["display_title"].lower()}">{error_icon}{item["display_title"]}</a>'

            html += '\n              </div>\n            </div>'

        html += """
        </div>
    </div><div class="main-content" id="main-content-area" tabindex="-1" style="outline:none;">"""

        html += generate_report_header_html(report_header)

        # Content - group queries by subtitle so the /* Table */ heading appears once
        for section_type, section_data in query_results.items():
            if not section_data:
                continue

            # Wrap entire section in a result-section div
            section_id = section_type.replace(" ", "_").lower()
            html += f"""<div class="result-section" id="section-{section_id}" data-section-id="section-{section_id}"> <h2 class="result-section-title">{section_type}</h2>"""

            # Group items by subtitle, preserving order
            seen_subtitles: list = []
            groups: dict = {}
            for item in section_data:
                key = item.get("subtitle") or ""
                if key not in groups:
                    groups[key] = []
                    seen_subtitles.append(key)
                groups[key].append(item)

            for subtitle_key in seen_subtitles:
                items_in_group = groups[subtitle_key]
                html += f"""<div class="result-group">"""
                if subtitle_key:
                    grp_anchor = f"grp-{section_id}--{subtitle_key.replace(' ', '_').lower()}"
                    html += (
                        f"""<h3 class="result-group-heading" id="{grp_anchor}" style="scroll-margin-top:20px;">{subtitle_key}</h3>"""
                    )

                for item in items_in_group:
                    html += f"""
        <div id="{item["query_id"]}" data-section-id="{item["query_id"]}" style="scroll-margin-top:20px;margin-bottom:36px;">
            <div class="result-header">
                <h4 class="result-title">{item["display_title"]}</h4>
            </div>"""

                    if item.get("image"):
                        html += f"""<div class="embedded-image"><img src="{item["image"]}"></div>"""

                    if item.get("chart_html"):
                        html += f"""<div class="embedded-chart-wrapper">{item["chart_html"]}</div>"""

                    # Show SQL code FIRST (above the table)
                    if item.get("query") and include_code_blocks:
                        safe_query = (
                            item["query"]
                            .replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )
                        html += (
                            f'<div class="query-code">'
                            f'<div class="query-code-header">'
                            f"<span>SQL Query</span>"
                            f'<button class="copy-code-btn" onclick="copyQueryCode(\'{item["query_id"]}\')" title="Copy SQL">'
                            f"📋 Copy</button>"
                            f"</div>"
                            f'<pre id="qcode-{item["query_id"]}">{safe_query}</pre>'
                            f"</div>"
                        )

                    # Then show the error or data table
                    if item.get("error"):
                        html += f"""<div class="error-container">
                            <div class="error-title">⚠️  Error</div>
                            <div class="error-message">{item["error"]}</div></div>"""
                    elif item.get("html_table"):
                        html += item["html_table"]

                    html += """</div>"""

                html += """</div>"""  # result-group

            html += """</div>"""  # result-section

        html += generate_report_footer_html(report_footer)

        # JavaScript
        html += f"""
    </div>

    {pako_script}

    <script>
        // Auto-decompress embedded datasets on page load
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('🚀 Initializing data explorer...');

            // Find all embedded datasets
            const datasetKeys = Object.keys(window).filter(key => key.startsWith('fullDataCompressed_'));

            datasetKeys.forEach(key => {{
                const queryId = key.replace('fullDataCompressed_', '');
                const compressedData = window[key];
                const totalRows = window['fullDataRows_' + queryId];

                if (!compressedData) return;

                try {{
                    if (typeof pako === 'undefined') {{
                        console.error('❌  pako.js not loaded - cannot decompress data');
                        return;
                    }}

                    console.log('📦 Decompressing dataset:', queryId, '(' + totalRows.toLocaleString() + ' rows)');

                    const compressed = Uint8Array.from(atob(compressedData), c => c.charCodeAt(0));
                    const decompressed = pako.ungzip(compressed, {{ to: 'string' }});

                    // Payload is split format: {{columns: [...], data: [[...], ...]}}
                    // Column names appear once — reconstruct row objects for search compatibility
                    const parsed = JSON.parse(decompressed);
                    const columns = parsed.columns;
                    const rawRows = parsed.data;

                    // Build array of plain objects {{col: val, ...}} for search functions
                    const fullData = rawRows.map(row => {{
                        const obj = {{}};
                        for (let i = 0; i < columns.length; i++) obj[columns[i]] = row[i];
                        return obj;
                    }});

                    // Store for search functions
                    window['searchData_' + queryId] = fullData;
                    window['searchColumns_' + queryId] = columns;

                    console.log('☑️ Ready for search:', queryId, '-', fullData.length.toLocaleString(), 'rows');
                }} catch (error) {{
                    console.error('❌  Failed to decompress', queryId, ':', error);
                }}
            }});

            console.log('✅ Data explorer initialized');
        }});

        function openSidebar() {{
            var sb = document.querySelector('.sidebar.collapsible');
            var bd = document.getElementById('sidebar-backdrop');
            if (sb) sb.classList.add('open');
            if (bd) bd.classList.add('active');
        }}

        function closeSidebar() {{
            var sb = document.querySelector('.sidebar.collapsible');
            var bd = document.getElementById('sidebar-backdrop');
            if (sb) sb.classList.remove('open');
            if (bd) bd.classList.remove('active');
        }}

        function toggleSidebar() {{
            var sb = document.querySelector('.sidebar.collapsible');
            if (!sb) return;
            if (sb.classList.contains('open')) closeSidebar(); else openSidebar();
        }}        

        function toggleTheme() {{
            const body = document.body;
            const currentTheme = body.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            body.setAttribute('data-theme', newTheme);
            localStorage.setItem('report-theme', newTheme);
            updateThemeIcon(newTheme);
            const isDark = newTheme === 'dark';
            (window._chartThemeFns || []).forEach(fn => {{ try {{ fn(isDark); }} catch(e) {{}} }});
        }}

        function updateThemeIcon(theme) {{
            const icon = document.getElementById('theme-icon');
            if (!icon) return;
            if (theme === 'dark') {{
                icon.innerHTML = '<path d="M12 3a9 9 0 1 0 9 9c0-.46-.04-.92-.1-1.36a5.389 5.389 0 0 1-4.4 2.26 5.403 5.403 0 0 1-3.14-9.8c-.44-.06-.9-.1-1.36-.1z"/>';
            }} else {{
                icon.innerHTML = '<path d="M12 7a5 5 0 0 1 5 5 5 5 0 0 1-5 5 5 5 0 0 1-5-5 5 5 0 0 1 5-5m0-2a7 7 0 0 0-7 7 7 7 0 0 0 7 7 7 7 0 0 0 7-7 7 7 0 0 0-7-7M2 11h2v2H2v-2m18 0h2v2h-2v-2M11 2h2v2h-2V2m0 18h2v2h-2v-2M4.22 3.93l1.42 1.42-1.42 1.41-1.41-1.41 1.41-1.42m15.14 13.3 1.41 1.41-1.41 1.42-1.42-1.42 1.42-1.41M4.22 19.07l-1.41-1.42 1.41-1.41 1.42 1.41-1.42 1.42M19.36 5.36l-1.42-1.42 1.42-1.41 1.41 1.42-1.41 1.41z"/>';
            }}
        }}

        const savedTheme = localStorage.getItem('report-theme');
        if (savedTheme) {{
            document.body.setAttribute('data-theme', savedTheme);
            updateThemeIcon(savedTheme);
            window.addEventListener('load', function() {{
                const isDark = savedTheme === 'dark';
                (window._chartThemeFns || []).forEach(fn => {{ try {{ fn(isDark); }} catch(e) {{}} }});
            }});
        }} else {{
            updateThemeIcon(document.body.getAttribute('data-theme') || 'light');
        }}

        // ── Help tooltip ──────────────────────────────────────────────────
        function toggleHelp() {{
            document.getElementById('helpTooltip').classList.toggle('visible');
        }}

        document.addEventListener('click', function(e) {{
            const btn = document.getElementById('helpBtn');
            const tt  = document.getElementById('helpTooltip');
            if (btn && tt && !btn.contains(e.target) && !tt.contains(e.target)) {{
                tt.classList.remove('visible');
            }}
        }});

        // ── Collapsible nav groups ─────────────────────────────────────────
        function toggleNavGroup(grpId) {{
            const el  = document.getElementById(grpId);
            const ico = document.getElementById('ngi-' + grpId);
            if (!el) return;
            const collapsed = el.classList.toggle('collapsed');
            if (ico) {{
                ico.innerHTML = collapsed
                    ? '<path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>'
                    : '<path d="M19 13H5v-2h14v2z"/>';
            }}
        }}

        function handleNavRowClick(event, grpId) {{
            if (event.target.closest('a.nav-link')) {{
                return;
            }}
            event.preventDefault();
            toggleNavGroup(grpId);
        }}

        function collapseAll() {{
            document.querySelectorAll('.nav-group-children').forEach(el => {{
                el.classList.add('collapsed');
                const ico = document.getElementById('ngi-' + el.id);
                if (ico) ico.innerHTML = '<path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>';
            }});
        }}

        function expandAll() {{
            document.querySelectorAll('.nav-group-children').forEach(el => {{
                el.classList.remove('collapsed');
                const ico = document.getElementById('ngi-' + el.id);
                if (ico) ico.innerHTML = '<path d="M19 13H5v-2h14v2z"/>';
            }});
        }}

        // ── Navigation search ──────────────────────────────────────────────
        function toggleNavClearButton() {{
            const val = document.getElementById('navSearchInput').value.trim();
            const btn = document.getElementById('navSearchClear');
            if (btn) btn.classList.toggle('visible', val !== '');
        }}

        // Navigation search functionality
        function filterNavigation() {{
            const searchTerm = document.getElementById('navSearchInput').value.toLowerCase().trim();
            toggleNavClearButton();
            const statsSpan = document.getElementById('navSearchStats');

            if (!searchTerm) {{
                document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('hidden', 'search-hidden'));
                document.querySelectorAll('.nav-group-children').forEach(el => {{
                    el.classList.remove('collapsed');
                    const ico = document.getElementById('ngi-' + el.id);
                    if (ico) ico.innerHTML = '<path d="M19 13H5v-2h14v2z"/>';
                }});
                document.querySelectorAll('.nav-group-label').forEach(l => l.classList.remove('search-hidden'));
                if (statsSpan) statsSpan.textContent = '';
                return;
            }}

            let totalMatches = 0;

            // Filter sub-links (query items)
            document.querySelectorAll('.nav-link.sub-link').forEach(link => {{
                const text = link.getAttribute('data-query-name') || link.textContent.toLowerCase();
                const match = text.includes(searchTerm);
                link.classList.toggle('hidden', !match);
                if (match) {{
                    totalMatches++;
                    // Expand parent group
                    const grpChildren = link.closest('.nav-group-children');
                    if (grpChildren) {{
                        grpChildren.classList.remove('collapsed');
                        const ico = document.getElementById('ngi-' + grpChildren.id);
                        if (ico) ico.innerHTML = '<path d="M19 13H5v-2h14v2z"/>';
                    }}
                }}
            }});

            // Show/hide group labels based on whether any following sub-links are visible
            document.querySelectorAll('.nav-group-label').forEach(label => {{
                let next = label.nextElementSibling;
                let anyVisible = false;
                while (next && next.classList.contains('nav-link')) {{
                    if (!next.classList.contains('hidden')) {{ anyVisible = true; break; }}
                    next = next.nextElementSibling;
                }}
                label.classList.toggle('search-hidden', !anyVisible);
            }});

            // Hide top-level section groups that have no visible children
            document.querySelectorAll('.nav-group').forEach(grp => {{
                const visLinks = grp.querySelectorAll('.nav-link.sub-link:not(.hidden)');
                const topLink = grp.querySelector('.nav-link:not(.sub-link)');
                if (topLink) topLink.classList.toggle('hidden', visLinks.length === 0);
            }});

            if (statsSpan) {{
                statsSpan.textContent = totalMatches === 0
                    ? 'No results'
                    : `${{totalMatches}} result${{totalMatches !== 1 ? 's' : ''}}`;
            }}
        }}

        function clearNavigationSearch() {{
            const inp = document.getElementById('navSearchInput');
            if (inp) {{ inp.value = ''; filterNavigation(); inp.focus(); }}
        }}

        // ── Keyboard shortcuts ─────────────────────────────────────────────
        document.addEventListener('keydown', function(event) {{
            const tag     = document.activeElement.tagName;
            const inInput = tag === 'INPUT' || tag === 'TEXTAREA';

            // Esc — clear search or close any open modal
            if (event.key === 'Escape') {{
                const overlay = document.getElementById('cellModalOverlay');
                if (overlay && overlay.classList.contains('active')) {{
                    overlay.classList.remove('active');
                }} else if (inInput) {{
                    clearNavigationSearch();
                    document.activeElement.blur();
                    const main = document.getElementById('main-content-area');
                    if (main) main.focus();
                }}
                return;
            }}

            // F — focus search box
            if ((event.key === 'f' || event.key === 'F') && !inInput) {{
                event.preventDefault();
                const inp = document.getElementById('navSearchInput');
                if (inp) {{ inp.focus(); inp.select(); }}
                return;
            }}

            // T — toggle theme
            if ((event.key === 't' || event.key === 'T') && !inInput) {{
                event.preventDefault();
                toggleTheme();
                return;
            }}

            // S — toggle collapsible sidebar
            if ((event.key === 's' || event.key === 'S') && !inInput) {{
                event.preventDefault();
                toggleSidebar();
                return;
            }}
            
            // N — focus navigation sidebar
            if ((event.key === 'n' || event.key === 'N') && !inInput) {{
                event.preventDefault();
                const links = Array.from(document.querySelectorAll('.nav-link:not(.hidden)'));
                if (links.length) links[0].focus();
                return;
            }}

            // M — focus main content
            if ((event.key === 'm' || event.key === 'M') && !inInput) {{
                event.preventDefault();
                const main = document.getElementById('main-content-area');
                if (main) main.focus();
                return;
            }}

            // ↑ / ↓ — navigate visible nav links when a nav-link is focused
            const focusedIsNavLink = document.activeElement.classList.contains('nav-link');
            if (focusedIsNavLink && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {{
                event.preventDefault();
                const links = Array.from(document.querySelectorAll('.nav-link:not(.hidden)'));
                if (!links.length) return;
                const idx = links.indexOf(document.activeElement);
                if (event.key === 'ArrowDown') {{
                    links[idx + 1 < links.length ? idx + 1 : 0].focus();
                }} else {{
                    links[idx - 1 >= 0 ? idx - 1 : links.length - 1].focus();
                }}
            }}
        }});

        // ── Scroll spy ─────────────────────────────────────────────────────
        function initScrollSpy() {{
            const targets  = document.querySelectorAll('[data-section-id]');
            const navLinks = document.querySelectorAll('.nav-link');
            const observer = new IntersectionObserver(
                (entries) => {{
                    entries.forEach(entry => {{
                        if (!entry.isIntersecting) return;
                        const id = entry.target.getAttribute('data-section-id');
                        const searchTerm = document.getElementById('navSearchInput').value.trim();
                        if (searchTerm) return;
                        navLinks.forEach(l => l.classList.remove('active'));
                        const active = document.querySelector(`.nav-link[data-section-id="${{id}}"]`);
                        if (active) {{
                            active.classList.add('active');
                            active.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
                        }}
                    }});
                }},
                {{ root: null, rootMargin: '-20% 0px -60% 0px', threshold: 0 }}
            );
            targets.forEach(el => observer.observe(el));
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            initScrollSpy();
            toggleNavClearButton();
            const main = document.getElementById('main-content-area');
            if (main) main.focus();
            // Close collapsible sidebar on nav link click
            document.querySelectorAll('.nav-link, .nav-group-label').forEach(function(el) {{
                el.addEventListener('click', function() {{ closeSidebar(); }});
            }});
        }});

        // ── Cell expansion modal ──────────────────────────────────────
        function expandCell(td) {{
            const fullText = td.getAttribute('data-full-text') || td.textContent;
            const colName = td.getAttribute('data-column') || '';
            document.getElementById('cellModalColumn').textContent = colName;
            document.getElementById('cellModalContent').textContent = fullText;
            document.getElementById('cellModalOverlay').classList.add('active');
        }}

        function closeCellModal(event) {{
            // Only close when clicking the overlay backdrop, not the modal itself
            if (event.target === document.getElementById('cellModalOverlay')) {{
                document.getElementById('cellModalOverlay').classList.remove('active');
            }}
        }}

        function closeCellModalDirect() {{
            document.getElementById('cellModalOverlay').classList.remove('active');
        }}

        function copyQueryCode(queryId) {{
            const pre = document.getElementById('qcode-' + queryId);
            if (!pre) return;
            navigator.clipboard.writeText(pre.textContent).then(() => {{
                const btn = event.target.closest('.copy-code-btn');
                if (!btn) return;
                const orig = btn.innerHTML;
                btn.innerHTML = '✓ Copied!';
                setTimeout(() => {{ btn.innerHTML = orig; }}, 2000);
            }});
        }}

        // ─────────────────────────────────────────────────────────────

        function filterColumns(queryId) {{
            const searchInput = document.getElementById('col-search-' + queryId);
            const table = document.getElementById('table-' + queryId);
            const countDisplay = document.getElementById('col-count-' + queryId);
            const headers = table.querySelectorAll('th[data-column]');
            const rows = table.querySelectorAll('tbody tr');
            const searchText = searchInput.value.trim().toLowerCase();

            let visibleCount = 0;
            const totalCount = headers.length;

            if (searchText === '') {{
                headers.forEach(h => h.classList.remove('hidden-column'));
                rows.forEach(r => r.querySelectorAll('td').forEach(c => c.classList.remove('hidden-column')));
                countDisplay.textContent = 'Showing ' + totalCount + ' of ' + totalCount + ' columns';
                return;
            }}

            const searchTerms = searchText.split(',').map(t => t.trim()).filter(t => t);

            headers.forEach((header, index) => {{
                const columnName = header.getAttribute('data-column');
                const matches = searchTerms.some(term => columnName.includes(term));

                if (matches) {{
                    header.classList.remove('hidden-column');
                    visibleCount++;
                }} else {{
                    header.classList.add('hidden-column');
                }}

                rows.forEach(row => {{
                    const cells = row.querySelectorAll('td');
                    if (cells[index]) {{
                        if (matches) {{
                            cells[index].classList.remove('hidden-column');
                        }} else {{
                            cells[index].classList.add('hidden-column');
                        }}
                    }}
                }});
            }});

            countDisplay.textContent = 'Showing ' + visibleCount + ' of ' + totalCount + ' columns';
        }}

        function filterRows(queryId, maxRows) {{
            const searchInput = document.getElementById('row-search-' + queryId).querySelector('input');
            const table = document.getElementById('table-' + queryId);
            const countDisplay = document.getElementById('row-count-' + queryId);
            const searchTerm = searchInput.value.toLowerCase().trim();

            // Check if we have decompressed full data
            const fullData = window['searchData_' + queryId];
            const columns = window['searchColumns_' + queryId];
            const hasFullData = fullData && columns;

            if (hasFullData) {{
                // Search in full decompressed dataset
                filterRowsFullData(queryId, searchTerm, table, countDisplay, fullData, columns, {str(enable_multiword_search).lower()});
            }} else {{
                // Search in visible table rows only
                filterRowsTableOnly(queryId, searchTerm, table, countDisplay, maxRows);
            }}
        }}

        function filterRowsFullData(queryId, searchTerm, table, countDisplay, fullData, columns, enableMultiWord) {{
            const tbody = table.querySelector('tbody');
            const totalRows = window['fullDataRows_' + queryId] || fullData.length;

            if (searchTerm === '') {{
                // ✅ FIX: Restore original table rows when search is cleared
                tbody.innerHTML = '';
                // Get the original stored rows limit
                const storedRows = Math.min({stored_rows}, totalRows);
                const maxRowsToShow = Math.min({max_rows}, storedRows);
                // Rebuild table with original data
                for (let i = 0; i < storedRows; i++) {{
                    if (i >= fullData.length) break;

                    const row = fullData[i];
                    const tr = document.createElement('tr');
                    tr.setAttribute('data-row-id', i);

                    if (i >= maxRowsToShow) {{
                        tr.classList.add('initially-hidden');
                    }}

                    // Get visible columns
                    const visibleHeaders = Array.from(table.querySelectorAll('thead th:not(.hidden-column)'));
                    const visibleColumnNames = visibleHeaders.map(th => th.getAttribute('data-column'));

                    columns.forEach(col => {{
                        const td = document.createElement('td');
                        td.setAttribute('data-column', col.toLowerCase());

                        const cellValue = row[col];
                        const cellText = cellValue !== null && cellValue !== undefined ? String(cellValue) : '';
                        td.textContent = cellText;

                        if (visibleColumnNames.length > 0 && visibleColumnNames.length < columns.length && !visibleColumnNames.includes(col.toLowerCase())) {{
                            td.classList.add('hidden-column');
                        }}

                        tr.appendChild(td);
                    }});

                    tbody.appendChild(tr);
                }}

                countDisplay.textContent = 'Showing ' + maxRowsToShow.toLocaleString() + ' of ' + totalRows.toLocaleString() + ' rows';
                return;
            }}

            // Get visible column names
            const visibleHeaders = Array.from(table.querySelectorAll('thead th:not(.hidden-column)'));
            const visibleColumnNames = visibleHeaders.map(th => th.getAttribute('data-column'));

            console.log('🔍 Full data search in', queryId, 'for:', searchTerm);
            console.log('📋 Searching in columns:', visibleColumnNames);

            let filtered = [];

            if (searchTerm.includes(':')) {{
                // Column-specific search
                const parts = searchTerm.split(':');
                const columnSearch = parts[0].trim().toLowerCase();
                const value = parts[1].trim().toLowerCase();
                let matchedColumn = columns.find(col => col.toLowerCase() === columnSearch);
                if (!matchedColumn) {{
                    matchedColumn = columns.find(col => col.toLowerCase().includes(columnSearch));
                }}

                if (!matchedColumn) {{
                    countDisplay.textContent = '⚠️ Column "' + columnSearch + '" not found';
                    return;
                }}

                filtered = fullData.filter(row => {{
                    const cellValue = String(row[matchedColumn] || '').toLowerCase();
                    return cellValue.includes(value);
                }});

            }} else {{
                // General search in visible columns
                const columnsToSearch = (visibleColumnNames.length === 0 || visibleColumnNames.length === columns.length)
                    ? columns
                    : columns.filter(col => visibleColumnNames.includes(col.toLowerCase()));

                if (enableMultiWord) {{
                    const searchWords = searchTerm.split(/\\s+/).filter(w => w);

                    filtered = fullData.filter(row => {{
                        return searchWords.every(word => {{
                            return columnsToSearch.some(col => {{
                                const val = row[col];
                                const strVal = String(val || '').toLowerCase();
                                return strVal.includes(word);
                            }});
                        }});
                    }});
                }} else {{
                    filtered = fullData.filter(row => {{
                        return columnsToSearch.some(col => {{
                            const val = row[col];
                            const strVal = String(val !== null && val !== undefined ? val : '').toLowerCase();
                            return strVal.includes(searchTerm);
                        }});
                    }});
                }}
            }}

            // Rebuild table with filtered results
            tbody.innerHTML = '';

            if (filtered.length === 0) {{
                const colCount = visibleColumnNames.length || columns.length;
                tbody.innerHTML = '<tr><td colspan="' + colCount + '" style="text-align:center;padding:20px;color:#999;">❌  No results for "' + searchTerm + '"</td></tr>';
                countDisplay.textContent = 'No results';
                return;
            }}

            const displayLimit = Math.min(filtered.length, 1000);
            for (let i = 0; i < displayLimit; i++) {{
                const row = filtered[i];
                const tr = document.createElement('tr');
                tr.setAttribute('data-row-id', i);

                columns.forEach(col => {{
                    const td = document.createElement('td');
                    td.setAttribute('data-column', col.toLowerCase());

                    const cellValue = row[col];
                    const cellText = cellValue !== null && cellValue !== undefined ? String(cellValue) : '';
                    td.textContent = cellText;

                    if (visibleColumnNames.length > 0 && visibleColumnNames.length < columns.length && !visibleColumnNames.includes(col.toLowerCase())) {{
                        td.classList.add('hidden-column');
                    }}

                    tr.appendChild(td);
                }});

                tbody.appendChild(tr);
            }}

            const limitNote = filtered.length > 1000 ? ' (showing first 1,000)' : '';
            countDisplay.textContent = 'Found ' + filtered.length.toLocaleString() + ' results' + limitNote;
        }}


        function filterRowsTableOnly(queryId, searchTerm, table, countDisplay, maxRows) {{
            const rows = table.querySelectorAll('tbody tr[data-row-id]');
            let visibleCount = 0;
            const totalCount = rows.length;

            if (searchTerm === '') {{
                rows.forEach(row => {{
                    row.classList.remove('hidden-row');
                    row.classList.remove('search-match');
                }});
                countDisplay.textContent = 'Showing ' + maxRows.toLocaleString() + ' of ' + totalCount.toLocaleString() + ' rows';
                return;
            }}

            // Get visible column names
            const visibleHeaders = Array.from(table.querySelectorAll('thead th:not(.hidden-column)'));
            const visibleColumnNames = visibleHeaders.map(th => th.getAttribute('data-column'));

            rows.forEach(row => {{
                // Only search in cells from visible columns
                const cells = Array.from(row.querySelectorAll('td')).filter(cell => {{
                    const cellColumn = cell.getAttribute('data-column');
                    return visibleColumnNames.includes(cellColumn);
                }});

                const rowMatches = cells.some(cell =>
                    cell.textContent.toLowerCase().includes(searchTerm));

                if (rowMatches) {{
                    row.classList.remove('hidden-row');
                    row.classList.add('search-match');
                    visibleCount++;
                }} else {{
                    row.classList.add('hidden-row');
                    row.classList.remove('search-match');
                }}
            }});

            countDisplay.textContent = 'Showing ' + visibleCount.toLocaleString() + ' of ' + totalCount.toLocaleString() + ' rows';
        }}

        function makeSortable() {{
            document.querySelectorAll('.data-table').forEach(table => {{
                const headers = table.querySelectorAll('thead th[data-column]');
                headers.forEach((header, columnIndex) => {{
                    header.addEventListener('click', function() {{
                        const tbody = table.querySelector('tbody');
                        const rows = Array.from(tbody.querySelectorAll('tr'));
                        const isAscending = this.getAttribute('data-sort') !== 'asc';
                        headers.forEach(h => h.removeAttribute('data-sort'));
                        this.setAttribute('data-sort', isAscending ? 'asc' : 'desc');

                        const indicator = this.querySelector('.sort-indicator');
                        if (indicator) {{
                            indicator.textContent = isAscending ? '⮝' : '⮟';
                            indicator.style.opacity = '1';
                        }}

                        rows.sort((a, b) => {{
                            const cellA = a.children[columnIndex].textContent.trim();
                            const cellB = b.children[columnIndex].textContent.trim();
                            const numA = parseFloat(cellA.replace(/[^0-9.-]/g, ''));
                            const numB = parseFloat(cellB.replace(/[^0-9.-]/g, ''));
                            if (!isNaN(numA) && !isNaN(numB)) {{
                                return isAscending ? numA - numB : numB - numA;
                            }}
                            return isAscending ? cellA.localeCompare(cellB) : cellB.localeCompare(cellA);
                        }});

                        rows.forEach(row => tbody.appendChild(row));
                    }});
                }});
            }});
        }}

        document.addEventListener('DOMContentLoaded', makeSortable);
    </script>
</body>
</html>"""

        return html

    # Main execution
    try:
        print("🚀 Starting data explorer generation")

        pako_js_content = None
        if js_folder and embed_full_data:
            pako_js_content = embed_pako_js(js_folder)

        cache_path = setup_cache_folder()
        print(f"✅ Cache folder: {cache_path}")

        # Initialize sections
        query_results = {}
        query_counter = 0
        chart_counter = [0]  # mutable list so inner functions can increment it

        # Process SQL files — each file gets its own sidebar section
        if sql_file_paths:
            _sq_names = section_names["sql_queries"]
            _sq_list = _sq_names if isinstance(_sq_names, list) else None

            # Use the configured section name only when there is exactly one file
            # (legacy behaviour). For multiple files use the file stem as section name.
            for sf_index, sf_path in enumerate(sql_file_paths):
                if _sq_list and sf_index < len(_sq_list):
                    section_label = _sq_list[sf_index]
                elif len(sql_file_paths) == 1 and isinstance(_sq_names, str):
                    section_label = _sq_names
                else:
                    section_label = (
                        Path(sf_path).stem.replace("_", " ").replace("-", " ").title()
                    )

                if section_label not in query_results:
                    query_results[section_label] = []

                print(
                    f"\n📋 SQL File [{sf_index + 1}/{len(sql_file_paths)}]: {sf_path}"
                )
                sql_queries = parse_sql_file(sf_path)
                if not sql_queries:
                    print(f"  ⚠️  No queries found in {sf_path}")
                    continue

                print(f"  ✅ Found {len(sql_queries)} table sections")
                for table_name, table_queries in sql_queries.items():
                    for query_info in table_queries:
                        # ── Chart-only item (no SQL to execute) ───────────────
                        if query_info.get("chart_html") and query_info["query"] is None:
                            query_results[section_label].append(
                                {
                                    "query_id": f"chart_{chart_counter[0] - 1}",
                                    "display_title": query_info["title"],
                                    "subtitle": table_name,
                                    "query": None,
                                    "html_table": None,
                                    "error": None,
                                    "image": None,
                                    "chart_html": query_info["chart_html"],
                                }
                            )
                            print(f"    ✅ [{query_info['title']}] chart embedded")
                            continue

                        if query_info["query"] is None:
                            continue
                        query_id = generate_query_id("sql", query_counter)
                        query_counter += 1

                        df, error = execute_or_load_query(
                            query_id,
                            query_info["title"],
                            query_info["query"],
                            cache_path,
                        )

                        if error:
                            query_results[section_label].append(
                                {
                                    "query_id": query_id,
                                    "display_title": query_info["title"],
                                    "subtitle": table_name,
                                    "query": query_info["query"],
                                    "html_table": None,
                                    "error": error,
                                    "image": query_info.get("image"),
                                }
                            )
                        else:
                            full_data_json = None
                            if embed_full_data and pako_js_content:
                                print(
                                    f"    📦 Compressing full data for: {query_info['title']}"
                                )
                                full_data_json = df_to_json_base64(df)

                            html_table = df_to_html_table(
                                df,
                                table_name,
                                query_id,
                                max_rows,
                                stored_rows,
                                full_data_json,
                            )

                            query_results[section_label].append(
                                {
                                    "query_id": query_id,
                                    "display_title": query_info["title"],
                                    "subtitle": table_name,
                                    "query": query_info["query"],
                                    "html_table": html_table,
                                    "error": None,
                                    "image": query_info.get("image"),
                                }
                            )
                            indicator = " [FULL SEARCH]" if full_data_json else ""
                            print(
                                f"    ✅ [{query_id}] {query_info['title']} - {len(df):,} rows{indicator}"
                            )

        # Process direct files
        if direct_files:
            print("\n📁 Processing direct files")
            normalized_files = normalize_direct_files(direct_files)

            # Group files by section
            sections_dict = {}
            for file_entry in normalized_files:
                section = file_entry["section"]
                if section not in sections_dict:
                    sections_dict[section] = []
                sections_dict[section].append(file_entry)

            # Process each section
            for section_name, files_in_section in sections_dict.items():
                print(f"\n📁 Section: {section_name}")

                # Initialize section in query_results
                if section_name not in query_results:
                    query_results[section_name] = []

                for file_entry in files_in_section:
                    file_ext = Path(file_entry["path"]).suffix.lower()

                    # ── embedded HTML chart (.html direct entry) ──────────────
                    if file_ext == ".html":
                        chart_html = embed_html_chart(
                            file_entry["path"],
                            file_entry.get("height", default_embed_height),
                            chart_counter[0],
                        )
                        chart_counter[0] += 1
                        query_results[section_name].append(
                            {
                                "query_id": f"chart_{chart_counter[0] - 1}",
                                "display_title": file_entry["title"],
                                "query": None,
                                "subtitle": None,
                                "html_table": None,
                                "error": None,
                                "image": None,
                                "chart_html": chart_html,
                            }
                        )
                        print(f"    ✅ [{file_entry['title']}] embedded as chart")
                        continue

                    # ── parquet / data file ───────────────────────────────────
                    query_id = generate_query_id("file", query_counter)
                    query_counter += 1
                    df, error = load_or_read_file(
                        file_entry["path"], query_id, cache_path
                    )

                    if not error:
                        full_data_json = None
                        if embed_full_data and pako_js_content:
                            print(
                                f"   📦 Compressing full data for: {file_entry['title']}"
                            )
                            full_data_json = df_to_json_base64(df)

                        html_table = df_to_html_table(
                            df,
                            file_entry["title"],
                            query_id,
                            max_rows,
                            stored_rows,
                            full_data_json,
                        )

                        query_results[section_name].append(
                            {
                                "query_id": query_id,
                                "display_title": file_entry["title"],
                                "query": None,
                                "subtitle": None,
                                "html_table": html_table,
                                "error": None,
                                "image": None,
                            }
                        )
                        indicator = " [FULL SEARCH]" if full_data_json else ""
                        print(
                            f"    ✅ [{query_id}] {file_entry['title']} - {len(df):,} rows{indicator}"
                        )
                    else:
                        query_results[section_name].append(
                            {
                                "query_id": query_id,
                                "display_title": file_entry["title"],
                                "subtitle": None,
                                "query": None,
                                "html_table": None,
                                "error": error,
                                "image": None,
                            }
                        )
                        print(
                            f"    ❌  [{query_id}] {file_entry['title']} - Error: {error}"
                        )

        # Generate final HTML
        print("\n🌐 Generating HTML...")
        html_content = generate_html(query_results, pako_js_content, report_header)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        html_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        print("\n" + "=" * 60)
        print(f"✅ Data Explorer generated: {output_path}")
        print(f"📊 HTML file size: {html_size_mb:.2f} MB")
        print(f"📊 Total queries/files: {query_counter}")
        print(f"📊 Total sections: {len(query_results)}")

        if pako_js_content and embed_full_data:
            print("✅ Full data embedded with compression - search works on all rows!")
        elif embed_full_data:
            print("⚠️ pako.js not found - full data not compressed")
        else:
            print(f"Limited to {stored_rows} rows per table")

        print("=" * 60)

        return str(output_path.absolute())

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None