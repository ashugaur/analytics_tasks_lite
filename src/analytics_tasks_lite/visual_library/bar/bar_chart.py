# %% Simple / Grouped Bar Chart
#
# Produces a non-stacked bar chart where each series sits side-by-side within
# a category — the pattern shown in:
#   https://echarts.apache.org/examples/en/editor.html?c=bar-tick-align
#
# Key difference from bar_chart_stacked.py:
#   - No "stack" key on series  → bars sit side-by-side, not on top of each other
#   - axisTick.alignWithLabel: true  → ticks centre under each bar group
#   - Bar labels sit on top of each individual bar (not a scatter "total" series)
#   - No normalization / percentage logic — values are always plotted as-is
#
# Design system identical to bar_chart_stacked.py:
#   - Same THEME_DEFAULTS, color utilities, resolve_color priority chain
#   - Same dual-theme JS setChartTheme() API
#   - Same generate_bar_chart_html() pattern

import json
import pandas as pd


# ============================================================================
# THEME DEFAULTS  (identical to bar_chart_stacked.py)
# ============================================================================

THEME_DEFAULTS = {
    "light": {
        "axis_line": "#00165e",
        "axis_tick": "#00165e",
        "axis_label": "#00165e",
        "axis_title": "#00165e",
        "chart_title": "#00165e",
        "chart_subtitle": "#666666",
        "gridline": "#c0c0c0",
        "legend_text": "#00165e",
        "tooltip_bg": "rgba(255, 255, 255, 0.95)",
        "tooltip_border": "#ccc",
        "tooltip_text": "#333",
        "bar_label": "#00165e",
        "reference_line": "#e63946",
        "footnote": "#888888",
    },
    "dark": {
        "axis_line": "#dcdcdc",
        "axis_tick": "#dcdcdc",
        "axis_label": "#dcdcdc",
        "axis_title": "#dcdcdc",
        "chart_title": "#dcdcdc",
        "chart_subtitle": "#aaaaaa",
        "gridline": "#c0c0c0",
        "legend_text": "#dcdcdc",
        "tooltip_bg": "rgba(50, 50, 50, 0.95)",
        "tooltip_border": "#666",
        "tooltip_text": "#fff",
        "bar_label": "#c0c0c0",
        "reference_line": "#ff6b6b",
        "footnote": "#aaaaaa",
    },
}


# ============================================================================
# COLOR MAPPING UTILITIES  (identical to bar_chart_stacked.py)
# ============================================================================


def read_color_mapping(color_file_path, sheet_name="colorsEcharts"):
    """
    Read color mapping from Excel file.

    Expected columns:
        topic, chart_type, chart_element, element_name, light_hex, dark_hex, notes

    Parameters
    ----------
    color_file_path : str or Path
        Path to the Excel color mapping file.
    sheet_name : str or dict, default 'colorsEcharts'
        Worksheet name, or {'name': 'sheetName'} dict.

    Returns
    -------
    pd.DataFrame or None
    """
    if isinstance(sheet_name, dict):
        sheet_name = sheet_name.get("name")
    try:
        df = pd.read_excel(color_file_path, sheet_name=sheet_name)
        df.columns = [c.lower().strip() for c in df.columns]
        return df
    except Exception as e:
        print(f"Warning: Could not read color file: {e}")
        return None


def get_dual_theme_series_colors(color_df, topic, chart_type, series_names):
    """Return (light_color_map, dark_color_map) for series, or (None, None)."""
    if color_df is None:
        return None, None
    series_colors = color_df[
        (color_df["topic"] == topic)
        & (color_df["chart_type"] == chart_type)
        & (color_df["chart_element"] == "series")
    ]
    light_map, dark_map = {}, {}
    for name in series_names:
        match = series_colors[series_colors["element_name"] == name]
        if not match.empty:
            light_map[name] = match.iloc[0]["light_hex"]
            dark_map[name] = match.iloc[0]["dark_hex"]
    return (light_map if light_map else None, dark_map if dark_map else None)


def get_element_color(color_df, topic, chart_type, chart_element, element_name, theme):
    """Look up a single chart-element hex color from the color mapping file."""
    if color_df is None:
        return None
    hex_col = "light_hex" if theme == "light" else "dark_hex"
    match = color_df[
        (color_df["topic"] == topic)
        & (color_df["chart_type"] == chart_type)
        & (color_df["chart_element"] == chart_element)
        & (color_df["element_name"] == element_name)
    ]
    if not match.empty:
        return match.iloc[0][hex_col]
    return None


def resolve_color(
    param_value, color_df, topic, chart_type, chart_element, element_name, theme
):
    """
    Resolve a color using the standard three-level priority chain:
      1. Explicit parameter  →  always wins
      2. Color mapping file  →  by (topic, chart_type, element, element_name)
      3. Theme default       →  THEME_DEFAULTS fallback
    """
    if param_value is not None:
        return param_value
    if color_df is not None and topic is not None:
        file_color = get_element_color(
            color_df, topic, chart_type, chart_element, element_name, theme
        )
        if file_color:
            return file_color
    return THEME_DEFAULTS.get(theme, THEME_DEFAULTS["light"]).get(
        chart_element, "#000000"
    )


# ============================================================================
# VALUE FORMATTING UTILITY
# ============================================================================


def format_value(value, format_type="number_k", decimals=1):
    """
    Format a numeric value for display as a bar label.

    Parameters
    ----------
    value : float
    format_type : str
        'number_k'  – K/M suffix  (e.g. 1.2K, 3.4M)
        'number_m'  – M suffix only
        'percent_0' – integer percent  (e.g. 73%)
        'percent_1' – 1-decimal percent (e.g. 73.4%)
        'percent_2' – 2-decimal percent (e.g. 73.42%)
        'decimal_0' / 'integer' – whole number (e.g. 1234)
        'decimal_1' – 1 decimal (e.g. 1234.5)
        'decimal_2' – 2 decimals (e.g. 1234.50)
        'none'      – raw integer string
    decimals : int
        Decimal places for K/M formatting.

    Returns
    -------
    str
    """
    if pd.isna(value):
        return ""
    if format_type == "none":
        return str(int(value))
    if format_type == "number_k":
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.{decimals}f}M"
        elif abs(value) >= 1_000:
            return f"{value / 1_000:.{decimals}f}K"
        else:
            return f"{value:.0f}"
    if format_type == "number_m":
        return f"{value / 1_000_000:.{decimals}f}M"
    if format_type == "percent_0":
        return f"{value:.0f}%"
    if format_type == "percent_1":
        return f"{value:.1f}%"
    if format_type == "percent_2":
        return f"{value:.2f}%"
    if format_type in ("decimal_0", "integer"):
        return f"{value:.0f}"
    if format_type == "decimal_1":
        return f"{value:.1f}"
    if format_type == "decimal_2":
        return f"{value:.2f}"
    return str(value)


# ============================================================================
# MAIN CHART FUNCTION
# ============================================================================


def bar_chart(
    df,
    # ── DATA MAPPING ─────────────────────────────────────────────────────────
    x_col="x",  # Column for x-axis categories
    y_col="series",  # Column identifying each bar series (group)
    value_col="value",  # Column with numeric values
    # ── THEME & COLORS ────────────────────────────────────────────────────────
    theme="light",  # 'light' or 'dark'
    color_file_path=None,  # Path to Excel color mapping file
    color_sheet_name=None,  # Sheet name string or {'name': 'sheet'} dict
    color_topic=None,  # Topic filter in color file (e.g. 'Drugs')
    series_color_map=None,  # Manual override: {series_name: hex_color}
    # ── CHART DIMENSIONS ─────────────────────────────────────────────────────
    chart_width="100%",
    chart_height="100%",
    # ── GRID / PLOT AREA ─────────────────────────────────────────────────────
    grid_left="60",
    grid_right="40",
    grid_top="60",
    grid_bottom="40",
    grid_contain_label=True,
    # ── CHART TITLE ───────────────────────────────────────────────────────────
    chart_title="",
    chart_title_font_size=14,
    chart_title_font_weight="bold",
    chart_title_font_family=None,  # Falls back to chart_font_family
    chart_title_color=None,
    chart_title_left=None,  # Explicit left offset (overrides position)
    chart_title_top=None,  # Explicit top offset (overrides position)
    chart_title_right=None,  # Explicit right offset (overrides position)
    chart_title_position="top-left",  # 'top-left','top-center','top-right','bottom-*'
    chart_subtitle="",
    chart_subtitle_font_size=12,
    chart_subtitle_font_weight="normal",
    chart_subtitle_font_family=None,
    chart_subtitle_color=None,
    # ── FOOTNOTE ─────────────────────────────────────────────────────────────
    chart_footnote="",                    # Footnote text (shown at bottom of chart)
    chart_footnote_font_size=9,
    chart_footnote_font_weight="normal",  # 'normal' or 'bold'
    chart_footnote_font_family=None,      # Falls back to chart_font_family
    chart_footnote_color=None,            # None = color mapping file → theme default
    chart_footnote_position="left",       # 'left', 'center', 'right'
    # ── X-AXIS ───────────────────────────────────────────────────────────────
    x_axis_title="",
    x_axis_title_font_size=10,
    x_axis_title_gap=25,
    x_axis_title_location="middle",  # 'start', 'middle', 'end'
    x_axis_title_color=None,
    x_axis_label_show=True,
    x_axis_label_font_size=9,
    x_axis_label_margin=8,
    x_axis_label_color=None,
    x_axis_label_rotate=0,  # Degrees to rotate labels (e.g. 30, 45)
    x_axis_label_formatter=None,  # Raw ECharts formatter string or None
    x_axis_line_show=True,
    x_axis_line_color=None,
    x_axis_line_width=0.75,
    x_axis_tick_show=True,  # True = ticks visible (alignWithLabel also set)
    x_axis_tick_color=None,
    x_axis_tick_align_with_label=True,  # ECharts axisTick.alignWithLabel — centres
    # ticks under grouped bar groups
    x_axis_sort=False,  # Sort categories before plotting
    # ── Y-AXIS ───────────────────────────────────────────────────────────────
    y_axis_title="",
    y_axis_title_font_size=10,
    y_axis_title_gap=40,
    y_axis_title_location="middle",
    y_axis_title_color=None,
    y_axis_label_show=True,
    y_axis_label_font_size=9,
    y_axis_label_margin=4,
    y_axis_label_color=None,
    y_axis_label_formatter="auto",  # See formatter options in docstring
    y_axis_label_decimals=0,  # Decimal places used by 'auto' formatter
    y_axis_line_show=True,
    y_axis_line_color=None,
    y_axis_line_width=0.75,
    y_axis_tick_show=False,
    y_axis_tick_color=None,
    y_axis_min=None,  # None = ECharts auto
    y_axis_max=None,
    y_axis_interval=None,
    # ── GRIDLINES ────────────────────────────────────────────────────────────
    gridline_show=True,
    gridline_color=None,
    gridline_width=0.2,
    gridline_type="dashed",  # 'solid', 'dashed', 'dotted'
    # ── BAR APPEARANCE ───────────────────────────────────────────────────────
    bar_width=None,  # None = auto, or '60%', or 30 (px)
    bar_max_width=None,  # Cap bar width in px (e.g. 40)
    bar_category_gap="20%",  # Gap between category groups
    bar_gap="10%",  # Gap between bars within a group
    bar_border_radius=None,  # [tl, tr, br, bl] e.g. [4, 4, 0, 0]
    bar_opacity=1.0,  # Bar fill opacity (0–1)
    bar_background_show=False,  # Show a light background bar behind each bar
    bar_background_color="rgba(180,180,180,0.2)",
    # ── BAR LABELS (on top of each bar) ──────────────────────────────────────
    bar_label_show=False,  # Show value label above each bar
    bar_label_position="top",  # 'top', 'inside', 'insideTop', 'insideBottom'
    bar_label_format="number_k",  # 'number_k','number_m','percent_0','percent_1',
    # 'percent_2','decimal_0','decimal_1','decimal_2','none'
    bar_label_decimals=1,  # Decimal places for K/M labels
    bar_label_font_size=10,
    bar_label_color=None,  # None = auto from theme
    bar_label_font_weight="normal",  # 'normal' or 'bold'
    bar_label_rotate=0,  # Degrees to rotate label text
    # ── LEGEND ────────────────────────────────────────────────────────────────
    legend_show=True,
    legend_position="top-right",  # 'top-left','top-center','top-right','bottom-*'
    legend_orient="horizontal",  # 'horizontal' or 'vertical'
    legend_icon="rect",  # 'rect','circle','roundRect','triangle','diamond'
    legend_icon_size=12,
    legend_font_size=9,
    legend_text_color=None,
    legend_sort=None,  # 'asc' or 'desc' — sort series alphabetically
    legend_custom_sort=None,  # ['Series B','Series A'] — explicit order
    # ── TOOLTIP ───────────────────────────────────────────────────────────────
    tooltip_show=True,
    tooltip_trigger="axis",  # 'axis' or 'item'
    tooltip_axis_pointer_type="shadow",  # 'shadow','line','cross','none'
    tooltip_padding=10,
    tooltip_font_size=12,
    tooltip_background_color=None,
    tooltip_border_color=None,
    tooltip_text_color=None,
    # ── REFERENCE LINE ────────────────────────────────────────────────────────
    reference_line_values=None,   # Single value, or list of values/dicts — see docstring
    reference_line_color=None,    # None = color mapping file → theme default
    reference_line_width=1.5,     # Line width in px
    reference_line_type="dashed", # 'solid', 'dashed', 'dotted'
    reference_line_label_show=True,
    reference_line_label_position="end",  # 'start', 'middle', 'end', 'insideStart', 'insideEnd'
    reference_line_label_font_size=10,
    reference_line_label_formatter=None,  # None = auto (shows value); or a fixed string
    # ── GLOBAL ────────────────────────────────────────────────────────────────
    chart_font_family="Arial",
    chart_background="transparent",
):
    """
    Build an ECharts option dict for a simple or grouped (non-stacked) bar chart.

    Each unique value in y_col becomes one bar series drawn side-by-side within
    each x-axis category — matching the ECharts bar-tick-align example.

    Parameters
    ----------
    df : pd.DataFrame
        Long-format DataFrame with at least three columns: x_col, y_col, value_col.
        One row per (category × series) combination.

    x_col : str, default 'x'
        Column whose unique values form the x-axis categories (e.g. months, brands).

    y_col : str, default 'series'
        Column whose unique values become separate bar series drawn side-by-side.
        Single-series charts have only one unique value here.

    value_col : str, default 'value'
        Numeric column to plot on the y-axis.

    theme : str, default 'light'
        'light' or 'dark'.

    color_file_path : str or Path or None
        Excel color mapping file.  Expected columns:
        topic, chart_type, chart_element, element_name, light_hex, dark_hex, notes.

    color_sheet_name : str or dict or None
        Worksheet name (e.g. 'colorsEcharts') or {'name': 'sheet'} dict.

    color_topic : str or None
        Topic string for color file lookup (e.g. 'Drugs', 'Finance').

    series_color_map : dict or None
        Manual color override: {'Series A': '#3b82f6', 'Series B': '#dc2626'}.
        Overrides color file and default palette.

    chart_width : str, default '100%'
        CSS width of the chart container div.

    chart_height : str, default '100%'
        CSS height of the chart container div.

    grid_left / grid_right / grid_top / grid_bottom : str, default '60'/'40'/'60'/'40'
        ECharts grid offsets.  Use '60' (px) or '10%'.

    grid_contain_label : bool, default True
        Prevent axis labels from being clipped by the grid boundary.

    chart_title : str, default ''
        Main title text.

    chart_title_font_size : int, default 14
    chart_title_font_weight : str, default 'bold'   ('normal' or 'bold')
    chart_title_font_family : str or None           Falls back to chart_font_family.
    chart_title_color : str or None                 Hex; None = theme default.
    chart_title_left : str or None                  Explicit left CSS value (overrides position).
    chart_title_top : str or None                   Explicit top CSS value.
    chart_title_right : str or None                 Explicit right CSS value.
    chart_title_position : str, default 'top-left'
        Preset position.  Format '<vertical>-<horizontal>'.
        Vertical: 'top', 'bottom'.  Horizontal: 'left', 'center', 'right'.

    chart_subtitle : str, default ''
    chart_subtitle_font_size : int, default 12
    chart_subtitle_font_weight : str, default 'normal'
    chart_subtitle_font_family : str or None
    chart_subtitle_color : str or None

    chart_footnote : str, default ''
        Text shown at the bottom of the chart (e.g. source, caveat, date).
        Rendered as a second ECharts title object pinned to the bottom.
    chart_footnote_font_size : int, default 9
    chart_footnote_font_weight : str, default 'normal'   ('normal' or 'bold')
    chart_footnote_font_family : str or None             Falls back to chart_font_family.
    chart_footnote_color : str or None
        Hex color.  Resolution priority:
          1. This parameter (always wins)
          2. Color mapping file  chart_element='footnote', element_name='main'
          3. Theme default       light=#888888  dark=#aaaaaa
    chart_footnote_position : str, default 'left'
        Horizontal alignment at the bottom: 'left', 'center', or 'right'.

    x_axis_title : str, default ''
    x_axis_title_font_size : int, default 10
    x_axis_title_gap : int, default 25
    x_axis_title_location : str, default 'middle'   ('start', 'middle', 'end')
    x_axis_title_color : str or None
    x_axis_label_show : bool, default True
    x_axis_label_font_size : int, default 9
    x_axis_label_margin : int, default 8
    x_axis_label_color : str or None
    x_axis_label_rotate : int, default 0
        Degrees to rotate x-axis labels.  Useful for long category names.
    x_axis_label_formatter : str or None
        Raw ECharts formatter string (e.g. '{value} kg') or None for default.
    x_axis_line_show : bool, default True
    x_axis_line_color : str or None
    x_axis_line_width : float, default 0.75
    x_axis_tick_show : bool, default True
    x_axis_tick_color : str or None
    x_axis_tick_align_with_label : bool, default True
        ECharts axisTick.alignWithLabel.  When True, tick marks align with the
        centre of each bar group rather than the category boundary — this is the
        defining feature of the bar-tick-align ECharts example.
    x_axis_sort : bool, default False
        Sort x-axis categories before building the chart.

    y_axis_title : str, default ''
    y_axis_title_font_size : int, default 10
    y_axis_title_gap : int, default 40
    y_axis_title_location : str, default 'middle'
    y_axis_title_color : str or None
    y_axis_label_show : bool, default True
    y_axis_label_font_size : int, default 9
    y_axis_label_margin : int, default 4
    y_axis_label_color : str or None
    y_axis_label_formatter : str, default 'auto'
        Controls how y-axis tick values are formatted.  Options:
            'auto'         – raw number, precision set by y_axis_label_decimals
            'none'         – raw number (same as auto)
            'integer'      – whole number                  e.g.  1 234
            'decimal_1'    – 1 decimal                     e.g.  1 234.5
            'decimal_2'    – 2 decimals                    e.g.  1 234.50
            'decimal_3'    – 3 decimals                    e.g.  1 234.500
            'percent_0'    – integer percent               e.g.  73%
            'percent_1'    – 1-decimal percent             e.g.  73.4%
            'percent_2'    – 2-decimal percent             e.g.  73.42%
            'number_k'     – K / M suffix (auto-scales)    e.g.  1.2K  /  2.5M
            'number_m'     – M suffix only                 e.g.  0.001M
            'currency_usd' – USD prefix                    e.g.  $1,234
            'currency_gbp' – GBP prefix                    e.g.  £1,234
            'currency_eur' – EUR prefix                    e.g.  €1.234
        Legacy raw ECharts strings (e.g. '{value}%', '${value}') are still
        accepted and passed through unchanged for backward compatibility.
    y_axis_label_decimals : int, default 0
        Decimal places used by the 'auto' / 'none' formatters.
    y_axis_line_show : bool, default True
    y_axis_line_color : str or None
    y_axis_line_width : float, default 0.75
    y_axis_tick_show : bool, default False
    y_axis_tick_color : str or None
    y_axis_min : float or None     None = ECharts auto.
    y_axis_max : float or None
    y_axis_interval : float or None

    gridline_show : bool, default True
    gridline_color : str or None
    gridline_width : float, default 0.2
    gridline_type : str, default 'dashed'   ('solid', 'dashed', 'dotted')

    bar_width : str, int, or None
        Width of each individual bar.  None = ECharts auto.
        String percentage (e.g. '60%') is relative to the category slot.
        Integer is pixels.
    bar_max_width : int or None
        Maximum bar width in pixels.  Prevents very wide bars on sparse charts.
    bar_category_gap : str, default '20%'
        Gap between category groups as a percentage of the slot width.
    bar_gap : str, default '10%'
        Gap between bars within a group as a percentage of bar width.
        '-100%' makes bars completely overlap (for manual multi-series overlap).
    bar_border_radius : list or None
        Corner radii [top-left, top-right, bottom-right, bottom-left].
        E.g. [4, 4, 0, 0] for rounded tops only.
    bar_opacity : float, default 1.0
        Fill opacity for all bars (0 = transparent, 1 = fully opaque).
    bar_background_show : bool, default False
        Show a faint background bar behind each bar (ECharts showBackground).
    bar_background_color : str, default 'rgba(180,180,180,0.2)'
        Color of the background bar when bar_background_show is True.

    bar_label_show : bool, default False
        Show a value label on each bar.
    bar_label_position : str, default 'top'
        Where the label appears relative to the bar:
        'top', 'inside', 'insideTop', 'insideBottom', 'insideTopLeft', etc.
    bar_label_format : str, default 'number_k'
        How the label value is formatted.  Same keys as format_value():
        'number_k', 'number_m', 'percent_0', 'percent_1', 'percent_2',
        'decimal_0'/'integer', 'decimal_1', 'decimal_2', 'none'.
    bar_label_decimals : int, default 1
        Decimal places for K/M label formatting.
    bar_label_font_size : int, default 10
    bar_label_color : str or None    None = auto from theme.
    bar_label_font_weight : str, default 'normal'   ('normal' or 'bold')
    bar_label_rotate : int, default 0   Degrees to rotate label text.

    legend_show : bool, default True
    legend_position : str, default 'top-right'
        'top-left', 'top-center', 'top-right',
        'bottom-left', 'bottom-center', 'bottom-right'
    legend_orient : str, default 'horizontal'   ('horizontal', 'vertical')
    legend_icon : str, default 'rect'
        'rect', 'circle', 'roundRect', 'triangle', 'diamond', 'line'.
    legend_icon_size : int, default 12
    legend_font_size : int, default 9
    legend_text_color : str or None
    legend_sort : str or None
        'asc' or 'desc' — sort series alphabetically.  Ignored when
        legend_custom_sort is provided.
    legend_custom_sort : list or None
        Explicit series order, e.g. ['Series B', 'Series A'].  Any series not
        in the list are appended at the end in original order.

    tooltip_show : bool, default True
    tooltip_trigger : str, default 'axis'   ('axis' or 'item')
    tooltip_axis_pointer_type : str, default 'shadow'
        'shadow', 'line', 'cross', or 'none'.
    tooltip_padding : int, default 10
    tooltip_font_size : int, default 12
    tooltip_background_color : str or None
    tooltip_border_color : str or None
    tooltip_text_color : str or None

    reference_line_values : float, list, or None, default None
        Draw one or more horizontal reference lines across the chart.
        Accepts:
            None                    — no reference lines
            42                      — single line at y=42
            [42, 100]               — two lines at fixed values
            [{"value": 42, "label": "Target"}, {"value": 100}]
                                    — lines with custom labels
        When a dict entry omits "label", the label shows the numeric value
        (formatted the same way as the y-axis, controlled by
        reference_line_label_formatter).
    reference_line_color : str or None, default None
        Hex color for the line and its label.  Resolution priority:
          1. This parameter (always wins)
          2. Color mapping file  chart_element='reference_line', element_name='main'
          3. Theme default       light=#e63946  dark=#ff6b6b
    reference_line_width : float, default 1.5
        Stroke width of the reference line in pixels.
    reference_line_type : str, default 'dashed'
        Line style: 'solid', 'dashed', or 'dotted'.
    reference_line_label_show : bool, default True
        Show a label alongside the reference line.
    reference_line_label_position : str, default 'end'
        Where the label sits on the line:
        'start', 'middle', 'end', 'insideStart', 'insideEnd'.
    reference_line_label_font_size : int, default 10
    reference_line_label_formatter : str or None, default None
        Fixed string to use as every line's label (e.g. 'Average').
        None = show the numeric value.

    chart_font_family : str, default 'Arial'
    chart_background : str, default 'transparent'

    Returns
    -------
    tuple : (option_dict, chart_width, chart_height, theme, theme_ui)
        Pass directly to generate_bar_chart_html().

    Color resolution priority
    -------------------------
    1. Explicit parameter  (always wins)
    2. Color mapping file  (topic / chart_type / element / element_name lookup)
    3. Theme defaults      (THEME_DEFAULTS fallback)
    """

    chart_type = "bar_chart"

    # ── Load color file ───────────────────────────────────────────────────────
    color_df = None
    if color_file_path:
        color_df = read_color_mapping(color_file_path, sheet_name=color_sheet_name)

    # ── Unique values ─────────────────────────────────────────────────────────
    x_values = df[x_col].unique().tolist()
    y_series = df[y_col].unique().tolist()

    # ── Series / legend ordering ──────────────────────────────────────────────
    if legend_custom_sort is not None:
        remaining = [s for s in y_series if s not in legend_custom_sort]
        y_series = [s for s in legend_custom_sort if s in y_series] + remaining
    elif legend_sort is not None:
        y_series = sorted(y_series, reverse=(legend_sort.lower() == "desc"))

    # ── X-axis sort ───────────────────────────────────────────────────────────
    if x_axis_sort:
        try:
            import re

            def _num(s):
                if isinstance(s, (int, float)):
                    return s
                m = re.search(r"\d+", str(s))
                return int(m.group()) if m else 0

            x_values = sorted(x_values, key=_num)
        except Exception:
            x_values = sorted(x_values)

    # ── Series colors ─────────────────────────────────────────────────────────
    default_light = [
        "#3b82f6",
        "#dc2626",
        "#84942a",
        "#f59e0b",
        "#6b46c1",
        "#10b981",
        "#f97316",
        "#06b6d4",
    ]
    default_dark = [
        "#60a5fa",
        "#f87171",
        "#a3b845",
        "#fbbf24",
        "#a78bfa",
        "#34d399",
        "#fb923c",
        "#22d3ee",
    ]

    series_color_map_light = None
    series_color_map_dark = None

    if series_color_map is None:
        if color_df is not None and color_topic:
            series_color_map_light, series_color_map_dark = (
                get_dual_theme_series_colors(
                    color_df, color_topic, chart_type, y_series
                )
            )
            series_color_map = (
                series_color_map_light if theme == "light" else series_color_map_dark
            )

    if series_color_map is None:
        series_color_map = {
            s: default_light[i % len(default_light)] for i, s in enumerate(y_series)
        }

    if series_color_map_light is None:
        series_color_map_light = {
            s: default_light[i % len(default_light)] for i, s in enumerate(y_series)
        }
        series_color_map_dark = {
            s: default_dark[i % len(default_dark)] for i, s in enumerate(y_series)
        }

    # ── Resolve chart-element colors ──────────────────────────────────────────
    def _rc(val, element, name="main"):
        return resolve_color(
            val, color_df, color_topic, chart_type, element, name, theme
        )

    rc_title = _rc(chart_title_color, "chart_title")
    rc_subtitle = _rc(chart_subtitle_color, "chart_subtitle")
    rc_x_title = _rc(x_axis_title_color, "axis_title", "x_axis")
    rc_x_label = _rc(x_axis_label_color, "axis_label", "x_axis")
    rc_x_line = _rc(x_axis_line_color, "axis_line", "x_axis")
    rc_x_tick = _rc(x_axis_tick_color, "axis_tick", "x_axis")
    rc_y_title = _rc(y_axis_title_color, "axis_title", "y_axis")
    rc_y_label = _rc(y_axis_label_color, "axis_label", "y_axis")
    rc_y_line = _rc(y_axis_line_color, "axis_line", "y_axis")
    rc_y_tick = _rc(y_axis_tick_color, "axis_tick", "y_axis")
    rc_gridline = _rc(gridline_color, "gridline")
    rc_legend = _rc(legend_text_color, "legend_text")
    rc_tooltip_bg = _rc(tooltip_background_color, "tooltip_bg")
    rc_tooltip_border = _rc(tooltip_border_color, "tooltip_border")
    rc_tooltip_text = _rc(tooltip_text_color, "tooltip_text")
    rc_bar_label = _rc(bar_label_color, "bar_label", "total")
    rc_ref_line  = _rc(reference_line_color, "reference_line")
    rc_footnote  = _rc(chart_footnote_color, "footnote")

    # ── Y-axis label formatter → JS sentinel ─────────────────────────────────
    _yfmt = y_axis_label_formatter
    _y_formatter_str = None  # plain ECharts string formatter
    _y_formatter_type = None  # JS function sentinel

    if _yfmt in (None, "auto", "none"):
        _y_formatter_type = "none"
    elif _yfmt == "integer":
        _y_formatter_type = "integer"
    elif _yfmt.startswith("decimal_"):
        _y_formatter_type = _yfmt  # e.g. "decimal_1"
    elif _yfmt == "percent_0":
        _y_formatter_str = "{value}%"
        _y_formatter_type = "percent_0"
    elif _yfmt == "percent_1":
        _y_formatter_type = "percent_1"
    elif _yfmt == "percent_2":
        _y_formatter_type = "percent_2"
    elif _yfmt == "number_k":
        _y_formatter_type = "number_k"
    elif _yfmt == "number_m":
        _y_formatter_type = "number_m"
    elif _yfmt == "currency_usd":
        _y_formatter_type = "currency_usd"
    elif _yfmt == "currency_gbp":
        _y_formatter_type = "currency_gbp"
    elif _yfmt == "currency_eur":
        _y_formatter_type = "currency_eur"
    else:
        # Legacy raw ECharts string e.g. "{value}%" — pass through unchanged
        _y_formatter_str = _yfmt
        _y_formatter_type = "raw"

    # ── Build series ──────────────────────────────────────────────────────────
    series = []
    for s_name in y_series:
        sdf = df[df[y_col] == s_name]
        value_map = dict(zip(sdf[x_col], sdf[value_col]))
        values = [value_map.get(x, None) for x in x_values]

        color = series_color_map.get(s_name, "#000000")

        # Data must be plain numbers (or null).
        # Per-item label.formatter strings cause ECharts to crash:
        #   "Cannot read properties of undefined (reading 'coordinateSystem')"
        # Pre-formatted strings are stored in _labelData and injected via a
        # JS formatter function that reads them by dataIndex.
        plain_data = [v if v is not None else None for v in values]
        label_strings = [
            format_value(v, bar_label_format, bar_label_decimals)
            if v is not None
            else ""
            for v in values
        ]

        item_style = {
            "color": color,
            "opacity": bar_opacity,
        }
        if bar_border_radius:
            item_style["borderRadius"] = bar_border_radius

        s_cfg = {
            "name": s_name,
            "type": "bar",
            "data": plain_data,
            "itemStyle": item_style,
            "label": {
                "show": bar_label_show,
                "position": bar_label_position,
                "fontSize": bar_label_font_size,
                "fontWeight": bar_label_font_weight,
                "color": rc_bar_label,
                "fontFamily": chart_font_family,
                "rotate": bar_label_rotate,
            },
            # Pre-formatted strings consumed by the JS formatter below
            "_labelData": label_strings,
            "emphasis": {"focus": "series"},
            "showBackground": bar_background_show,
            "backgroundStyle": {"color": bar_background_color},
            # Dual-theme metadata
            "_lightColor": series_color_map_light.get(s_name, "#000000"),
            "_darkColor": series_color_map_dark.get(s_name, "#000000"),
        }

        if bar_width is not None:
            s_cfg["barWidth"] = bar_width
        if bar_max_width is not None:
            s_cfg["barMaxWidth"] = bar_max_width
        s_cfg["barCategoryGap"] = bar_category_gap
        s_cfg["barGap"] = bar_gap

        series.append(s_cfg)

    # ── X-axis ────────────────────────────────────────────────────────────────
    x_axis_config = {
        "type": "category",
        "data": x_values,
        "name": x_axis_title,
        "nameLocation": x_axis_title_location,
        "nameGap": x_axis_title_gap,
        "nameTextStyle": {
            "fontSize": x_axis_title_font_size,
            "fontFamily": chart_font_family,
            "color": rc_x_title,
        },
        "axisLabel": {
            "show": x_axis_label_show,
            "fontSize": x_axis_label_font_size,
            "fontFamily": chart_font_family,
            "color": rc_x_label,
            "margin": x_axis_label_margin,
            "rotate": x_axis_label_rotate,
        },
        "axisLine": {
            "show": x_axis_line_show,
            "lineStyle": {"color": rc_x_line, "width": x_axis_line_width},
        },
        "axisTick": {
            "show": x_axis_tick_show,
            "alignWithLabel": x_axis_tick_align_with_label,
            "lineStyle": {"color": rc_x_tick},
        },
    }
    if x_axis_label_formatter:
        x_axis_config["axisLabel"]["formatter"] = x_axis_label_formatter

    # ── Y-axis ────────────────────────────────────────────────────────────────
    y_axis_config = {
        "type": "value",
        "name": y_axis_title,
        "nameLocation": y_axis_title_location,
        "nameGap": y_axis_title_gap,
        "nameRotate": 90,
        "nameTextStyle": {
            "fontSize": y_axis_title_font_size,
            "fontFamily": chart_font_family,
            "color": rc_y_title,
        },
        "axisLabel": {
            "show": y_axis_label_show,
            "fontSize": y_axis_label_font_size,
            "fontFamily": chart_font_family,
            "color": rc_y_label,
            "margin": y_axis_label_margin,
            **({"formatter": _y_formatter_str} if _y_formatter_str else {}),
        },
        "axisLine": {
            "show": y_axis_line_show,
            "lineStyle": {"color": rc_y_line, "width": y_axis_line_width},
        },
        "axisTick": {
            "show": y_axis_tick_show,
            "lineStyle": {"color": rc_y_tick},
        },
        "splitLine": {
            "show": gridline_show,
            "lineStyle": {
                "color": rc_gridline,
                "width": gridline_width,
                "type": gridline_type,
            },
        },
        "_formatterType": _y_formatter_type,
        "_formatterDecimals": y_axis_label_decimals,
    }
    if y_axis_min is not None:
        y_axis_config["min"] = y_axis_min
    if y_axis_max is not None:
        y_axis_config["max"] = y_axis_max
    if y_axis_interval is not None:
        y_axis_config["interval"] = y_axis_interval

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_positions = {
        "top-left": {"top": 0, "left": 0},
        "top-right": {"top": 0, "right": 0},
        "top-center": {"top": 0, "left": "center"},
        "bottom-left": {"bottom": 0, "left": 0},
        "bottom-right": {"bottom": 0, "right": 0},
        "bottom-center": {"bottom": 0, "left": "center"},
    }
    legend_pos = legend_positions.get(legend_position, {"top": 0, "right": 0})

    legend_config = {
        "show": legend_show,
        "data": y_series,
        "orient": legend_orient,
        "icon": legend_icon,
        "itemWidth": legend_icon_size,
        "itemHeight": legend_icon_size,
        **legend_pos,
        "textStyle": {
            "fontSize": legend_font_size,
            "fontFamily": chart_font_family,
            "color": rc_legend,
        },
    }

    # ── Title ─────────────────────────────────────────────────────────────────
    title_font_family = chart_title_font_family or chart_font_family
    subtitle_font_family = chart_subtitle_font_family or chart_font_family

    if chart_title or chart_subtitle:
        parts = chart_title_position.lower().split("-")
        if len(parts) != 2:
            parts = ["top", "left"]
        vertical, horizontal = parts

        title_config = {}
        if chart_title_left is not None:
            title_config["left"] = chart_title_left
        elif horizontal == "left":
            title_config["left"] = "3%"
        elif horizontal == "center":
            title_config["left"] = "center"
        elif horizontal == "right":
            title_config["right"] = chart_title_right or "5%"

        if chart_title_top is not None:
            title_config["top"] = chart_title_top
        elif vertical == "top":
            title_config["top"] = 0
        else:
            title_config["bottom"] = "2%"

        if chart_title:
            title_config["text"] = chart_title
            title_config["textStyle"] = {
                "fontWeight": chart_title_font_weight,
                "fontSize": chart_title_font_size,
                "fontFamily": title_font_family,
                "color": rc_title,
            }
        if chart_subtitle:
            title_config["subtext"] = chart_subtitle
            title_config["subtextStyle"] = {
                "fontWeight": chart_subtitle_font_weight,
                "fontSize": chart_subtitle_font_size,
                "fontFamily": subtitle_font_family,
                "color": rc_subtitle,
            }
            title_config["itemGap"] = 5
        title_config["show"] = True
    else:
        title_config = {"show": False, "text": ""}

    # ── Tooltip ───────────────────────────────────────────────────────────────
    axis_pointer = {"type": tooltip_axis_pointer_type}
    tooltip_config = {
        "show": tooltip_show,
        "trigger": tooltip_trigger,
        "confine": True,
        "axisPointer": axis_pointer,
        "backgroundColor": rc_tooltip_bg,
        "borderColor": rc_tooltip_border,
        "borderWidth": 1,
        "padding": tooltip_padding,
        "textStyle": {"color": rc_tooltip_text, "fontSize": tooltip_font_size},
        "extraCssText": "box-shadow: 0 2px 8px rgba(0,0,0,0.15);",
    }

    # ── Dual-theme UI map ─────────────────────────────────────────────────────
    def _rc2(val, element, name, t):
        return resolve_color(val, color_df, color_topic, chart_type, element, name, t)

    theme_ui = {
        "light": {
            "axisLine": _rc2(x_axis_line_color, "axis_line", "x_axis", "light"),
            "axisLabel": _rc2(x_axis_label_color, "axis_label", "x_axis", "light"),
            "axisTitle": _rc2(x_axis_title_color, "axis_title", "x_axis", "light"),
            "gridline": _rc2(gridline_color, "gridline", "main", "light"),
            "legend": _rc2(legend_text_color, "legend_text", "main", "light"),
            "tooltipBg": _rc2(tooltip_background_color, "tooltip_bg", "main", "light"),
            "tooltipBorder": _rc2(
                tooltip_border_color, "tooltip_border", "main", "light"
            ),
            "tooltipText": _rc2(tooltip_text_color, "tooltip_text", "main", "light"),
            "chartTitle": _rc2(chart_title_color, "chart_title", "main", "light"),
            "chartSubtitle": _rc2(
                chart_subtitle_color, "chart_subtitle", "main", "light"
            ),
            "barLabel": _rc2(bar_label_color, "bar_label", "total", "light"),
            "referenceLineColor": _rc2(reference_line_color, "reference_line", "main", "light"),
            "footnote": _rc2(chart_footnote_color, "footnote", "main", "light"),
        },
        "dark": {
            "axisLine": _rc2(None, "axis_line", "x_axis", "dark"),
            "axisLabel": _rc2(None, "axis_label", "x_axis", "dark"),
            "axisTitle": _rc2(None, "axis_title", "x_axis", "dark"),
            "gridline": _rc2(None, "gridline", "main", "dark"),
            "legend": _rc2(None, "legend_text", "main", "dark"),
            "tooltipBg": _rc2(None, "tooltip_bg", "main", "dark"),
            "tooltipBorder": _rc2(None, "tooltip_border", "main", "dark"),
            "tooltipText": _rc2(None, "tooltip_text", "main", "dark"),
            "chartTitle": _rc2(None, "chart_title", "main", "dark"),
            "chartSubtitle": _rc2(None, "chart_subtitle", "main", "dark"),
            "barLabel": _rc2(None, "bar_label", "total", "dark"),
            "referenceLineColor": _rc2(None, "reference_line", "main", "dark"),
            "footnote": _rc2(None, "footnote", "main", "dark"),
        },
    }

    # ── Assemble option ───────────────────────────────────────────────────────
    # ── Reference lines (markLine on the first series) ────────────────────────
    if reference_line_values is not None:
        # Normalise to list of dicts: [{"value": v, "label": str}, ...]
        raw = reference_line_values
        if not isinstance(raw, list):
            raw = [raw]
        mark_data = []
        for entry in raw:
            if isinstance(entry, dict):
                yval  = entry.get("value", entry.get("yAxis", 0))
                label = entry.get("label", None)
            else:
                yval  = entry
                label = None

            label_text = label if label is not None else (
                reference_line_label_formatter if reference_line_label_formatter is not None
                else str(yval)
            )
            mark_item = {
                "yAxis": yval,
                "label": {
                    "show": reference_line_label_show,
                    "position": reference_line_label_position,
                    "fontSize": reference_line_label_font_size,
                    "color": rc_ref_line,
                    "fontFamily": chart_font_family,
                    "formatter": label_text,
                },
                "lineStyle": {
                    "color": rc_ref_line,
                    "width": reference_line_width,
                    "type": reference_line_type,
                },
            }
            mark_data.append(mark_item)

        # Attach to the first series so only one set of lines is drawn
        if series and mark_data:
            series[0]["markLine"] = {
                "silent": True,
                "symbol": ["none", "none"],
                "data": mark_data,
            }

    # ── Footnote ──────────────────────────────────────────────────────────────
    footnote_font_family = chart_footnote_font_family or chart_font_family
    footnote_align_map = {"left": "left", "center": "center", "right": "right"}
    footnote_pos_key = chart_footnote_position.lower() if chart_footnote_position else "left"

    if chart_footnote:
        footnote_config = {
            "show": True,
            "text": chart_footnote,
            "bottom": "1%",
            "textStyle": {
                "fontSize": chart_footnote_font_size,
                "fontWeight": chart_footnote_font_weight,
                "fontFamily": footnote_font_family,
                "color": rc_footnote,
                "align": footnote_align_map.get(footnote_pos_key, "left"),
            },
        }
        if footnote_pos_key == "right":
            footnote_config["right"] = "3%"
        elif footnote_pos_key == "center":
            footnote_config["left"] = "center"
        else:
            footnote_config["left"] = "3%"
    else:
        footnote_config = {"show": False, "text": ""}

    option = {
        "backgroundColor": chart_background,
        "title": [title_config, footnote_config],
        "legend": legend_config,
        "grid": {
            "left": grid_left,
            "right": grid_right,
            "top": grid_top,
            "bottom": grid_bottom,
            "containLabel": grid_contain_label,
        },
        "xAxis": x_axis_config,
        "yAxis": y_axis_config,
        "series": series,
        "tooltip": tooltip_config,
        # Reference-line theme colours (read by generate_bar_chart_html)
        "_themeRefLine": {
            "light": theme_ui["light"]["referenceLineColor"],
            "dark":  theme_ui["dark"]["referenceLineColor"],
        },
        # Footnote theme colours (read by generate_bar_chart_html)
        "_themeFootnote": {
            "light": theme_ui["light"]["footnote"],
            "dark":  theme_ui["dark"]["footnote"],
        },
    }

    return option, chart_width, chart_height, theme, theme_ui


# ============================================================================
# HTML GENERATION
# ============================================================================


def generate_bar_chart_html(
    option,
    width="100%",
    height="100%",
    output_file="bar_chart.html",
    renderer="svg",
):
    """
    Write a standalone HTML file containing the ECharts bar chart.

    Parameters
    ----------
    option : tuple or dict
        Output of bar_chart() — (option_dict, width, height, theme, theme_ui) —
        or a raw ECharts option dict.
    width : str
        Container width.  Overridden by the tuple value when a tuple is passed.
    height : str
        Container height.  Overridden by the tuple value when a tuple is passed.
    output_file : str or Path
        Destination HTML file path.
    renderer : str
        'svg' (default, sharp at any resolution) or 'canvas'.

    Returns
    -------
    str : path to the written HTML file.
    """
    theme = "light"
    theme_ui = None

    if isinstance(option, tuple):
        if len(option) == 5:
            option, width, height, theme, theme_ui = option
        elif len(option) == 4:
            option, width, height, theme = option
        elif len(option) == 3:
            option, width, height = option

    if theme_ui is None:
        theme_ui = {
            "light": {
                "axisLine": "#00165e",
                "axisLabel": "#00165e",
                "axisTitle": "#00165e",
                "gridline": "#c0c0c0",
                "legend": "#00165e",
                "tooltipBg": "rgba(255,255,255,0.95)",
                "tooltipBorder": "#ccc",
                "tooltipText": "#333",
                "chartTitle": "#00165e",
                "chartSubtitle": "#666666",
                "barLabel": "#00165e",
            },
            "dark": {
                "axisLine": "#dcdcdc",
                "axisLabel": "#dcdcdc",
                "axisTitle": "#dcdcdc",
                "gridline": "#c0c0c0",
                "legend": "#dcdcdc",
                "tooltipBg": "rgba(50,50,50,0.95)",
                "tooltipBorder": "#666",
                "tooltipText": "#fff",
                "chartTitle": "#dcdcdc",
                "chartSubtitle": "#aaaaaa",
                "barLabel": "#c0c0c0",
            },
        }

    theme_colors_js = json.dumps(
        {
            s["name"]: {
                "light": s.get("_lightColor", "#000000"),
                "dark": s.get("_darkColor", "#000000"),
            }
            for s in option.get("series", [])
            if "_lightColor" in s
        }
    )
    theme_ui_js = json.dumps(theme_ui)

    # Extract reference-line theme colours and strip the private key before
    # serialising option so ECharts never sees it.
    _theme_ref_line = option.pop("_themeRefLine", {"light": "#e63946", "dark": "#ff6b6b"})
    theme_ref_line_js = json.dumps(_theme_ref_line)

    # Extract footnote theme colours likewise.
    _theme_footnote = option.pop("_themeFootnote", {"light": "#888888", "dark": "#aaaaaa"})
    theme_footnote_js = json.dumps(_theme_footnote)

    option_js = json.dumps(option, allow_nan=False)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Bar Chart</title>
    <style>
      *, *::before, *::after {{ box-sizing: border-box; }}
      html, body {{
        margin: 0; padding: 0;
        width: 100%; height: 100%;
        background: transparent;
        overflow: hidden;
      }}
      #main {{
        width: {width}; height: {height};
      }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
</head>
<body>
    <div id="main"></div>
    <script type="text/javascript">
        var chartDom = document.getElementById('main');
        var myChart  = echarts.init(chartDom, null, {{ renderer: '{renderer}' }});
        var option   = {option_js};

        // ── Build seriesColors lookup (used by tooltip formatter below) ────────
        var seriesColors = {{}};
        option.series.forEach(function(s) {{
            if (s.itemStyle && s.itemStyle.color) {{
                seriesColors[s.name] = s.itemStyle.color;
            }}
        }});

        // ── Initial render — NO JS formatter functions anywhere in option ─────
        // ECharts crashes with "Cannot read properties of undefined (reading
        // 'coordinateSystem')" if ANY JS function is present anywhere in the
        // option during the first setOption call — including the Y-axis formatter.
        // Build all function references first, then patch them ALL in afterwards.
        myChart.setOption(option, true);

        // ── Y-axis label formatter — patched in AFTER initial render ─────────
        if (option.yAxis && option.yAxis._formatterType) {{
            var yFmt = option.yAxis._formatterType;
            var yFn  = null;
            if (yFmt === 'integer') {{
                yFn = function(v) {{ return Math.round(v).toString(); }};
            }} else if (yFmt === 'decimal_1') {{
                yFn = function(v) {{ return v.toFixed(1); }};
            }} else if (yFmt === 'decimal_2') {{
                yFn = function(v) {{ return v.toFixed(2); }};
            }} else if (yFmt === 'decimal_3') {{
                yFn = function(v) {{ return v.toFixed(3); }};
            }} else if (yFmt === 'percent_0') {{
                yFn = function(v) {{ return Math.round(v) + '%'; }};
            }} else if (yFmt === 'percent_1') {{
                yFn = function(v) {{ return v.toFixed(1) + '%'; }};
            }} else if (yFmt === 'percent_2') {{
                yFn = function(v) {{ return v.toFixed(2) + '%'; }};
            }} else if (yFmt === 'number_k') {{
                yFn = function(v) {{
                    var a = Math.abs(v);
                    if (a >= 1e6) return (v/1e6).toFixed(1).replace(/\\.0$/,'') + 'M';
                    if (a >= 1e3) return (v/1e3).toFixed(1).replace(/\\.0$/,'') + 'K';
                    return Math.round(v).toString();
                }};
            }} else if (yFmt === 'number_m') {{
                yFn = function(v) {{ return (v/1e6).toFixed(2) + 'M'; }};
            }} else if (yFmt === 'currency_usd') {{
                yFn = function(v) {{ return '$' + Math.round(v).toLocaleString('en-US'); }};
            }} else if (yFmt === 'currency_gbp') {{
                yFn = function(v) {{ return '\u00a3' + Math.round(v).toLocaleString('en-GB'); }};
            }} else if (yFmt === 'currency_eur') {{
                yFn = function(v) {{ return '\u20ac' + Math.round(v).toLocaleString('de-DE'); }};
            }}
            if (yFn !== null) {{
                myChart.setOption({{ yAxis: {{ axisLabel: {{ formatter: yFn }} }} }});
            }}
        }}

        // ── Tooltip formatter — patched in after initial render ──────────────
        if (option.tooltip && option.tooltip.show) {{
            myChart.setOption({{
                tooltip: {{
                    formatter: function(params) {{
                        var rows  = Array.isArray(params) ? params : [params];
                        var label = rows.length > 0 ? rows[0].axisValue || rows[0].name : '';
                        var html  = '<div style="padding:2px 0;">';
                        html += '<div style="font-weight:bold;margin-bottom:6px;">' + label + '</div>';
                        rows.forEach(function(p) {{
                            if (p.value == null || (typeof p.value === 'object' && p.value.value == null)) return;
                            var rawVal = (typeof p.value === 'object' && p.value !== null) ? p.value.value : p.value;
                            if (rawVal == null) return;
                            var numVal = parseFloat(rawVal);
                            var disp   = isNaN(numVal) ? String(rawVal) : numVal.toLocaleString();
                            var col    = seriesColors[p.seriesName] || '#000';
                            var dot    = '<span style="display:inline-block;width:10px;height:10px;'
                                       + 'border-radius:2px;background:' + col
                                       + ';margin-right:7px;vertical-align:middle;"></span>';
                            html += '<div style="margin:3px 0;">' + dot
                                  + p.seriesName + ': <b>' + disp + '</b></div>';
                        }});
                        html += '</div>';
                        return html;
                    }}
                }}
            }});
        }}

        // ── Bar label formatters — patched in after initial render ───────────
        // Each series carries _labelData (array of pre-formatted strings built
        // in Python). Patch via a separate setOption so coordinateSystem exists.
        var labelPatches = [];
        option.series.forEach(function(s, idx) {{
            if (!s._labelData || !s.label) return;
            (function(labels) {{
                labelPatches.push({{
                    label: {{
                        formatter: function(params) {{
                            return labels[params.dataIndex] || '';
                        }}
                    }}
                }});
            }})(s._labelData);
        }});
        if (labelPatches.length > 0) {{
            myChart.setOption({{ series: labelPatches }});
        }}

        window.addEventListener('resize', function() {{ myChart.resize(); }});

        // ── Dual-theme support ────────────────────────────────────────────────
        var _themeColors   = {theme_colors_js};
        var _themeUI       = {theme_ui_js};
        var _themeRefLine  = {theme_ref_line_js};
        var _themeFootnote = {theme_footnote_js};

        window.setChartTheme = function(isDark) {{
            var t = isDark ? _themeUI.dark : _themeUI.light;

            option.series.forEach(function(s) {{
                var c = _themeColors[s.name];
                if (!c) return;
                if (s.itemStyle) s.itemStyle.color = isDark ? c.dark : c.light;
                seriesColors[s.name] = isDark ? c.dark : c.light;
            }});

            myChart.setOption({{
                title: [
                    {{
                        textStyle:    {{ color: t.chartTitle }},
                        subtextStyle: {{ color: t.chartSubtitle }},
                    }},
                    {{
                        textStyle: {{ color: isDark ? _themeFootnote.dark : _themeFootnote.light }},
                    }},
                ],
                xAxis: {{
                    axisLine:      {{ lineStyle: {{ color: t.axisLine }} }},
                    axisTick:      {{ lineStyle: {{ color: t.axisLine }} }},
                    axisLabel:     {{ color: t.axisLabel }},
                    nameTextStyle: {{ color: t.axisTitle }},
                }},
                yAxis: {{
                    axisLine:      {{ lineStyle: {{ color: t.axisLine }} }},
                    axisTick:      {{ lineStyle: {{ color: t.axisLine }} }},
                    axisLabel:     {{ color: t.axisLabel }},
                    nameTextStyle: {{ color: t.axisTitle }},
                    splitLine:     {{ lineStyle: {{ color: t.gridline }} }},
                }},
                legend:  {{ textStyle: {{ color: t.legend }} }},
                tooltip: {{
                    backgroundColor: t.tooltipBg,
                    borderColor:     t.tooltipBorder,
                    textStyle:       {{ color: t.tooltipText }},
                }},
                series: option.series,
            }});

            // ── Update reference line colours ─────────────────────────────────
            var refColor = isDark ? _themeRefLine.dark : _themeRefLine.light;
            var refPatches = [];
            option.series.forEach(function(s) {{
                if (!s.markLine || !s.markLine.data) {{
                    refPatches.push(null);
                    return;
                }}
                var patchedData = s.markLine.data.map(function(d) {{
                    return {{
                        yAxis: d.yAxis,
                        label: Object.assign({{}}, d.label, {{ color: refColor }}),
                        lineStyle: Object.assign({{}}, d.lineStyle, {{ color: refColor }}),
                    }};
                }});
                refPatches.push({{ markLine: {{ data: patchedData }} }});
            }});
            var hasRefPatch = refPatches.some(function(p) {{ return p !== null; }});
            if (hasRefPatch) {{
                myChart.setOption({{ series: refPatches.map(function(p) {{ return p || {{}}; }}) }});
            }}
        }};

        chartDom.setAttribute('data-chart-ready', 'true');
    </script>
</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    # print(f"Chart saved → {output_file}")
    # return output_file


# ============================================================================
# SIMULATED DATA HELPERS
# ============================================================================


def make_single_series_data():
    """Single bar series — one bar per month."""
    import random

    random.seed(42)
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    rows, val = [], 120_000
    for m in months:
        val += random.randint(-8_000, 18_000)
        rows.append({"month": m, "series": "Revenue", "value": max(val, 50_000)})
    return pd.DataFrame(rows)


def make_multi_series_data():
    """Three bar series side-by-side per month — the classic grouped bar."""
    import random

    random.seed(7)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    series = ["Product A", "Product B", "Product C"]
    bases = [80_000, 55_000, 40_000]
    rows = []
    for s, base in zip(series, bases):
        val = base
        for m in months:
            val += random.randint(-5_000, 12_000)
            rows.append({"month": m, "series": s, "value": max(val, 20_000)})
    return pd.DataFrame(rows)


def make_category_comparison_data():
    """Two series compared across five drug categories — good for bar_gap demo."""
    data = [
        ("Drug A", "Year 1", 1_200),
        ("Drug A", "Year 2", 1_850),
        ("Drug B", "Year 1", 3_400),
        ("Drug B", "Year 2", 2_900),
        ("Drug C", "Year 1", 780),
        ("Drug C", "Year 2", 1_100),
        ("Drug D", "Year 1", 2_100),
        ("Drug D", "Year 2", 2_450),
        ("Drug E", "Year 1", 4_300),
        ("Drug E", "Year 2", 5_200),
    ]
    return pd.DataFrame(data, columns=["drug", "year", "patients"])


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    from pathlib import Path

    output_dir = Path(".")

    # ── Example 1: Single-series — monthly revenue ────────────────────────────
    df1 = make_single_series_data()

    result1 = bar_chart(
        df1,
        x_col="month",
        y_col="series",
        value_col="value",
        theme="light",
        chart_title="Monthly Revenue",
        chart_subtitle="Jan – Dec · Product A",
        chart_title_position="top-left",
        chart_width="100%",
        chart_height="100%",
        x_axis_title="Month",
        x_axis_tick_show=True,
        x_axis_tick_align_with_label=True,
        y_axis_title="Revenue (USD)",
        y_axis_label_formatter="currency_usd",
        gridline_show=True,
        gridline_type="dashed",
        bar_border_radius=[4, 4, 0, 0],
        bar_label_show=True,
        bar_label_format="number_k",
        bar_label_font_size=9,
        legend_show=False,  # Single series — legend not needed
        tooltip_show=True,
        tooltip_axis_pointer_type="shadow",
    )

    generate_bar_chart_html(
        result1,
        output_file=output_dir / "bar_chart_single.html",
    )

    # ── Example 2: Grouped — three products side-by-side ──────────────────────
    df2 = make_multi_series_data()

    result2 = bar_chart(
        df2,
        x_col="month",
        y_col="series",
        value_col="value",
        theme="light",
        chart_title="Monthly Revenue by Product",
        chart_subtitle="Grouped bars · Jan – Jul",
        chart_title_position="top-left",
        chart_width="100%",
        chart_height="100%",
        x_axis_title="Month",
        x_axis_tick_show=True,
        x_axis_tick_align_with_label=True,  # ← key bar-tick-align feature
        y_axis_title="Revenue (USD)",
        y_axis_label_formatter="number_k",
        gridline_show=True,
        gridline_type="dashed",
        bar_border_radius=[3, 3, 0, 0],
        bar_gap="5%",
        bar_category_gap="30%",
        bar_label_show=True,
        bar_label_format="number_k",
        bar_label_font_size=8,
        legend_show=True,
        legend_position="top-right",
        tooltip_show=True,
        tooltip_axis_pointer_type="shadow",
    )

    generate_bar_chart_html(
        result2,
        output_file=output_dir / "bar_chart_grouped.html",
    )

    # ── Example 3: Category comparison — Year 1 vs Year 2 ────────────────────
    df3 = make_category_comparison_data()

    result3 = bar_chart(
        df3,
        x_col="drug",
        y_col="year",
        value_col="patients",
        theme="light",
        chart_title="Patient Volume by Drug",
        chart_subtitle="Year 1 vs Year 2",
        chart_title_position="top-left",
        chart_width="100%",
        chart_height="100%",
        x_axis_tick_show=True,
        x_axis_tick_align_with_label=True,
        y_axis_title="Patients",
        y_axis_label_formatter="number_k",
        bar_border_radius=[4, 4, 0, 0],
        bar_gap="10%",
        bar_category_gap="25%",
        bar_label_show=True,
        bar_label_format="number_k",
        bar_label_font_size=9,
        bar_label_font_weight="bold",
        legend_show=True,
        legend_position="top-right",
        legend_icon="rect",
        tooltip_axis_pointer_type="shadow",
        # Custom sort so Year 1 always renders before Year 2
        legend_custom_sort=["Year 1", "Year 2"],
    )

    generate_bar_chart_html(
        result3,
        output_file=output_dir / "bar_chart_comparison.html",
    )

    # ── Example 4: Dark theme — same data as Ex 3 ────────────────────────────
    result4 = bar_chart(
        df3,
        x_col="drug",
        y_col="year",
        value_col="patients",
        theme="dark",
        chart_title="Patient Volume by Drug",
        chart_subtitle="Year 1 vs Year 2  ·  Dark theme",
        chart_title_position="top-left",
        chart_width="100%",
        chart_height="100%",
        chart_background="#1a1a2e",
        x_axis_tick_show=True,
        x_axis_tick_align_with_label=True,
        y_axis_label_formatter="number_k",
        bar_border_radius=[4, 4, 0, 0],
        bar_label_show=True,
        bar_label_format="number_k",
        bar_label_font_size=9,
        legend_show=True,
        legend_position="top-right",
        legend_custom_sort=["Year 1", "Year 2"],
        tooltip_axis_pointer_type="shadow",
    )

    generate_bar_chart_html(
        result4,
        output_file=output_dir / "bar_chart.html",
    )

    print("\nAll examples generated:")
    print("  bar_chart_single.html     — single series, monthly revenue")
    print("  bar_chart_grouped.html    — 3 grouped series, monthly revenue")
    print("  bar_chart_comparison.html — Year 1 vs Year 2 per drug (light)")
    print("  bar_chart_dark.html       — same comparison in dark theme")


# ============================================================================
# HORIZONTAL BAR CHART
# ============================================================================


def bar_chart_horizontal(
    df,
    # ── DATA MAPPING ─────────────────────────────────────────────────────────
    x_col="x",
    y_col="series",
    value_col="value",
    # ── LABEL POSITION DEFAULTS (horizontal-friendly) ─────────────────────
    bar_label_position="right",  # 'right' sits outside bar end; 'inside' is also common
    # ── ALL OTHER PARAMS passed through to bar_chart() ────────────────────
    **kwargs,
):
    """
    Horizontal grouped bar chart.  Identical API to bar_chart(), but categories
    run along the Y-axis and values along the X-axis.

    Implementation
    --------------
    Calls bar_chart() with the same arguments, then post-processes the returned
    option dict to swap xAxis ↔ yAxis (and move gridlines to xAxis), producing
    a horizontal layout without duplicating any chart-building logic.

    Parameters
    ----------
    df : pd.DataFrame
        Long-format DataFrame — same shape as bar_chart().
    x_col : str
        Column for categories (rendered on the Y-axis in horizontal mode).
    y_col : str
        Column identifying each bar series.
    value_col : str
        Numeric column to plot (now the X-axis).
    bar_label_position : str, default 'right'
        Default label position for horizontal bars.  Overridden by caller if
        passed via kwargs.
    **kwargs
        All other bar_chart() parameters (theme, titles, colors, legend, …).

    Returns
    -------
    tuple : (option_dict, chart_width, chart_height, theme, theme_ui)
        Pass directly to generate_bar_chart_html().
    """

    # Merge bar_label_position default — caller kwargs win
    kwargs.setdefault("bar_label_position", bar_label_position)

    # Also default border_radius to round the *right* end of horizontal bars
    kwargs.setdefault("bar_border_radius", [0, 4, 4, 0])

    # Build the vertical option first (all logic lives there)
    result = bar_chart(df, x_col=x_col, y_col=y_col, value_col=value_col, **kwargs)

    option, chart_width, chart_height, theme, theme_ui = result

    # ── Swap axis roles ───────────────────────────────────────────────────────
    x_cfg = option["xAxis"]  # currently: category axis
    y_cfg = option["yAxis"]  # currently: value axis

    # The category axis must become yAxis; value axis must become xAxis.
    # Move gridlines (splitLine) from value axis → the new xAxis (still value).
    # Remove nameRotate from the new yAxis (category) to avoid upside-down labels.

    # Strip the rotation that only made sense for vertical value axis
    y_cfg.pop("nameRotate", None)

    # Move splitLine to the value axis (now xAxis)
    x_cfg["splitLine"] = y_cfg.pop("splitLine", {"show": False})

    # Swap
    option["xAxis"] = y_cfg  # value axis → xAxis
    option["yAxis"] = x_cfg  # category axis → yAxis

    # ECharts reverses category order in horizontal mode by default
    # (bottom category = first datum).  Invert so order matches the data.
    option["yAxis"]["inverse"] = True

    return option, chart_width, chart_height, theme, theme_ui


# ============================================================================
# HORIZONTAL EXAMPLE DATA HELPERS
# ============================================================================


def make_regional_sales_data():
    """Single series — revenue by sales region."""
    data = [
        ("North", 185_000),
        ("South", 142_000),
        ("East", 203_000),
        ("West", 167_000),
        ("Central", 98_000),
        ("Pacific", 221_000),
    ]
    return pd.DataFrame(data, columns=["region", "revenue"]).assign(series="Revenue")


def make_department_headcount_data():
    """Two series (Permanent / Contract) per department."""
    data = [
        ("Engineering", 120, 35),
        ("Sales", 80, 20),
        ("Marketing", 45, 15),
        ("Operations", 60, 10),
        ("HR", 25, 5),
        ("Finance", 30, 8),
    ]
    rows = []
    for dept, perm, cont in data:
        rows.append({"department": dept, "series": "Permanent", "headcount": perm})
        rows.append({"department": dept, "series": "Contract", "headcount": cont})
    return pd.DataFrame(rows)


def make_survey_score_data():
    """Single series — NPS scores per product."""
    data = [
        ("Product Alpha", 72),
        ("Product Beta", 58),
        ("Product Gamma", 81),
        ("Product Delta", 44),
        ("Product Epsilon", 65),
    ]
    return pd.DataFrame(data, columns=["product", "nps_score"]).assign(
        series="NPS Score"
    )


def make_budget_vs_actual_data():
    """Two series — Budget vs Actual spend per cost centre."""
    data = [
        ("R&D", 500_000, 470_000),
        ("Sales", 320_000, 345_000),
        ("Marketing", 180_000, 162_000),
        ("IT", 140_000, 155_000),
        ("Admin", 90_000, 88_000),
    ]
    rows = []
    for centre, budget, actual in data:
        rows.append({"centre": centre, "series": "Budget", "amount": budget})
        rows.append({"centre": centre, "series": "Actual", "amount": actual})
    return pd.DataFrame(rows)


# ============================================================================
# HORIZONTAL EXAMPLES
# ============================================================================

if __name__ == "__main__":
    from pathlib import Path

    output_dir = Path(".")

    # ── Horizontal Example 1: Single series — regional revenue ───────────────
    df_h1 = make_regional_sales_data()

    result_h1 = bar_chart_horizontal(
        df_h1,
        x_col="region",
        y_col="series",
        value_col="revenue",
        theme="light",
        chart_title="Revenue by Sales Region",
        chart_subtitle="Single series · horizontal",
        chart_title_position="top-left",
        chart_width="100%",
        chart_height="100%",
        x_axis_title="Region",
        y_axis_title="Revenue (USD)",
        y_axis_label_formatter="currency_usd",
        gridline_show=True,
        gridline_type="dashed",
        bar_label_show=True,
        bar_label_format="number_k",
        bar_label_font_size=9,
        legend_show=False,
        tooltip_show=True,
        tooltip_axis_pointer_type="shadow",
    )

    generate_bar_chart_html(
        result_h1,
        output_file=output_dir / "bar_chart_horizontal_single.html",
    )

    # ── Horizontal Example 2: Grouped — department headcount ─────────────────
    df_h2 = make_department_headcount_data()

    result_h2 = bar_chart_horizontal(
        df_h2,
        x_col="department",
        y_col="series",
        value_col="headcount",
        theme="light",
        chart_title="Headcount by Department",
        chart_subtitle="Permanent vs Contract · grouped horizontal",
        chart_title_position="top-left",
        chart_width="100%",
        chart_height="100%",
        y_axis_title="Headcount",
        y_axis_label_formatter="integer",
        gridline_show=True,
        gridline_type="dashed",
        bar_gap="10%",
        bar_category_gap="30%",
        bar_label_show=True,
        bar_label_format="decimal_0",
        bar_label_font_size=9,
        legend_show=True,
        legend_position="top-right",
        tooltip_show=True,
        tooltip_axis_pointer_type="shadow",
        legend_custom_sort=["Permanent", "Contract"],
    )

    generate_bar_chart_html(
        result_h2,
        output_file=output_dir / "bar_chart_horizontal_grouped.html",
    )

    # ── Horizontal Example 3: Single series — NPS scores per product ──────────
    df_h3 = make_survey_score_data()

    result_h3 = bar_chart_horizontal(
        df_h3,
        x_col="product",
        y_col="series",
        value_col="nps_score",
        theme="light",
        chart_title="Net Promoter Score by Product",
        chart_subtitle="Higher is better · max 100",
        chart_title_position="top-left",
        chart_width="100%",
        chart_height="100%",
        y_axis_title="NPS Score",
        y_axis_label_formatter="integer",
        y_axis_min=0,
        y_axis_max=100,
        gridline_show=True,
        gridline_type="dashed",
        bar_label_show=True,
        bar_label_format="decimal_0",
        bar_label_font_size=10,
        bar_label_font_weight="bold",
        bar_background_show=True,
        legend_show=False,
        tooltip_show=True,
        tooltip_axis_pointer_type="shadow",
        series_color_map={"NPS Score": "#10b981"},
    )

    generate_bar_chart_html(
        result_h3,
        output_file=output_dir / "bar_chart_horizontal_nps.html",
    )

    # ── Horizontal Example 4: Dark theme — Budget vs Actual ───────────────────
    df_h4 = make_budget_vs_actual_data()

    result_h4 = bar_chart_horizontal(
        df_h4,
        x_col="centre",
        y_col="series",
        value_col="amount",
        theme="dark",
        chart_background="#1a1a2e",
        chart_title="Budget vs Actual Spend",
        chart_subtitle="By cost centre · dark theme",
        chart_title_position="top-left",
        chart_width="100%",
        chart_height="100%",
        y_axis_title="Amount (USD)",
        y_axis_label_formatter="number_k",
        gridline_show=True,
        gridline_type="dashed",
        bar_gap="8%",
        bar_category_gap="28%",
        bar_label_show=True,
        bar_label_format="number_k",
        bar_label_font_size=9,
        legend_show=True,
        legend_position="top-right",
        legend_custom_sort=["Budget", "Actual"],
        tooltip_show=True,
        tooltip_axis_pointer_type="shadow",
        series_color_map={"Budget": "#60a5fa", "Actual": "#34d399"},
    )

    generate_bar_chart_html(
        result_h4,
        output_file=output_dir / "bar_chart_horizontal_dark.html",
    )

    print("\nHorizontal examples generated:")
    print("  bar_chart_horizontal_single.html  — single series, regional revenue")
    print("  bar_chart_horizontal_grouped.html — grouped, department headcount")
    print("  bar_chart_horizontal_nps.html     — NPS scores per product")
    print("  bar_chart_horizontal_dark.html    — Budget vs Actual, dark theme")
