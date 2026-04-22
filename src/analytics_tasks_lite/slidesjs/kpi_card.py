# %% kpi_card

## Dependencies
"""
KPI Card Generator for SlideJS
Generates dual-theme HTML KPI cards embeddable via Custom_Box_config (Source_Type=HTMLTABLE).

Styles:
  'simple'     — large value + label + optional delta. No icon.
  'icon'       — SVG/image icon left, title + value right. Like a receipt/app card.
  'comparison' — two values side by side (e.g. actual vs target) with a delta.
"""

import uuid
import pandas as pd
from pathlib import Path


# ============================================================================
# THEME DEFAULTS
# ============================================================================

KPI_THEME_DEFAULTS = {
    "light": {
        "card_bg":          "#ffffff",
        "card_border":      "#e5e7eb",
        "card_shadow":      "0 2px 8px rgba(0,0,0,0.08)",
        "title_text":       "#6b7280",
        "value_text":       "#111827",
        "subtitle_text":    "#9ca3af",
        "delta_positive":   "#16a34a",
        "delta_negative":   "#dc2626",
        "delta_neutral":    "#6b7280",
        "icon_bg":          "#f3f4f6",
        "icon_color":       "#374151",   # dark grey — visible on light bg
        "divider":          "#e5e7eb",
        "label_a":          "#6b7280",
        "value_a":          "#111827",
        "label_b":          "#6b7280",
        "value_b":          "#111827",
    },
    "dark": {
        "card_bg":          "#1f2937",
        "card_border":      "#374151",
        "card_shadow":      "0 2px 8px rgba(0,0,0,0.4)",
        "title_text":       "#9ca3af",
        "value_text":       "#f9fafb",
        "subtitle_text":    "#6b7280",
        "delta_positive":   "#4ade80",
        "delta_negative":   "#f87171",
        "delta_neutral":    "#9ca3af",
        "icon_bg":          "#374151",
        "icon_color":       "#e5e7eb",   # light grey — visible on dark bg
        "divider":          "#374151",
        "label_a":          "#9ca3af",
        "value_a":          "#f9fafb",
        "label_b":          "#9ca3af",
        "value_b":          "#f9fafb",
    },
}


# ============================================================================
# COLOR HELPERS  (same interface as excel_table_to_html.py)
# ============================================================================

def _kpi_read_color_mapping(color_file_path, sheet_name=None):
    if color_file_path is None:
        return None
    if isinstance(sheet_name, dict):
        sheet_name = sheet_name.get("name")
    try:
        return pd.read_excel(color_file_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"  ⚠️  Could not read color file: {e}")
        return None


def _kpi_resolve_color(param_value, color_df, topic, chart_element,
                       element_name, theme, fallback_key):
    """Priority: explicit param > color file > KPI_THEME_DEFAULTS."""
    if param_value is not None:
        return param_value
    if color_df is not None and topic is not None:
        try:
            hex_col = "light_hex" if theme == "light" else "dark_hex"
            match = color_df[
                (color_df["topic"]           == topic)
                & (color_df["chart_type"]    == "kpi_card")
                & (color_df["chart_element"] == chart_element)
                & (color_df["element_name"]  == element_name)
            ]
            if not match.empty:
                return str(match.iloc[0][hex_col])
        except Exception:
            pass
    defaults = KPI_THEME_DEFAULTS.get(theme, KPI_THEME_DEFAULTS["light"])
    return defaults.get(fallback_key, "#333333")


# ============================================================================
# HTML BUILDERS — one per style, called twice (light + dark)
# ============================================================================

def _build_simple(title, value, subtitle, delta, delta_is_positive,
                  font_family, value_font_size, title_font_size,
                  subtitle_font_size, delta_font_size,
                  c):                      # c = resolved colour dict
    """Large centred value with label above and optional delta + subtitle below."""
    delta_color = (c["delta_positive"] if delta_is_positive
                   else c["delta_negative"] if delta_is_positive is False
                   else c["delta_neutral"])

    delta_html = (
        f'<div style="margin-top:4px;font-size:{delta_font_size};'
        f'color:{delta_color};font-weight:600;">{delta}</div>'
    ) if delta else ""

    subtitle_html = (
        f'<div style="margin-top:2px;font-size:{subtitle_font_size};'
        f'color:{c["subtitle_text"]};">{subtitle}</div>'
    ) if subtitle else ""

    return f"""<div style="
        width:100%; height:100%; box-sizing:border-box;
        display:flex; flex-direction:column;
        align-items:center; justify-content:center;
        text-align:center; padding:16px;
        font-family:{font_family};">
  <div style="font-size:{title_font_size}; color:{c['title_text']};
              font-weight:500; letter-spacing:0.02em;">{title}</div>
  <div style="font-size:{value_font_size}; color:{c['value_text']};
              font-weight:700; line-height:1.1; margin-top:6px;">{value}</div>
  {delta_html}
  {subtitle_html}
</div>"""


def _build_icon(title, value, subtitle, delta, delta_is_positive,
                icon_path, icon_size,
                font_family, value_font_size, title_font_size,
                subtitle_font_size, delta_font_size,
                c, icon_color=None):
    """Icon on the left, title + value + subtitle on the right."""
    delta_color = (c["delta_positive"] if delta_is_positive
                   else c["delta_negative"] if delta_is_positive is False
                   else c["delta_neutral"])

    delta_html = (
        f'<span style="margin-left:8px;font-size:{delta_font_size};'
        f'color:{delta_color};font-weight:600;">{delta}</span>'
    ) if delta else ""

    subtitle_html = (
        f'<div style="margin-top:3px;font-size:{subtitle_font_size};'
        f'color:{c["subtitle_text"]};">{subtitle}</div>'
    ) if subtitle else ""

    # Icon: SVG file, image file, or plain emoji/text
    icon_html = ""
    if icon_path:
        p = Path(str(icon_path))
        if p.suffix.lower() == ".svg" and p.exists():
            try:
                import re as _re
                svg = p.read_text(encoding="utf-8")
                svg = _re.sub(r"<\?xml[^>]+\?>\s*", "", svg)
                svg = _re.sub(r"<!DOCTYPE[^>]+>\s*", "", svg)
                svg = _re.sub(r'\s+width\s*=\s*["\'][^"\']*["\']', "", svg)
                svg = _re.sub(r'\s+height\s*=\s*["\'][^"\']*["\']', "", svg)
                icon_html = (
                    f'<div style="width:{icon_size};height:{icon_size};'
                    f'border-radius:12px;background:{c["icon_bg"]};'
                    f'display:flex;align-items:center;justify-content:center;'
                    f'flex-shrink:0;padding:6px;box-sizing:border-box;'
                    f'color:{c["icon_color"]};fill:{c["icon_color"]};">'
                    f'{svg}</div>'
                )
            except Exception:
                pass
        elif p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp") and p.exists():
            import base64
            data = base64.b64encode(p.read_bytes()).decode()
            ext  = p.suffix.lower().lstrip(".")
            mime = "jpeg" if ext == "jpg" else ext
            icon_html = (
                f'<div style="width:{icon_size};height:{icon_size};'
                f'border-radius:12px;background:{c["icon_bg"]};'
                f'display:flex;align-items:center;justify-content:center;'
                f'flex-shrink:0;overflow:hidden;">'
                f'<img src="data:image/{mime};base64,{data}" '
                f'style="width:100%;height:100%;object-fit:cover;"/></div>'
            )
        elif len(str(icon_path)) <= 8 and not p.suffix:
            # Short string with no file extension — treat as emoji / text symbol
            icon_html = (
                f'<div style="width:{icon_size};height:{icon_size};'
                f'border-radius:12px;background:{c["icon_bg"]};'
                f'display:flex;align-items:center;justify-content:center;'
                f'flex-shrink:0;font-size:calc({icon_size} * 0.55);">'
                f'{icon_path}</div>'
            )
        else:
            # File not found or unrecognised — show a neutral placeholder box
            # (avoids rendering the raw file path as visible text)
            print(f"   ⚠️  Icon not found or unrecognised: {icon_path} — using placeholder")
            icon_html = (
                f'<div style="width:{icon_size};height:{icon_size};'
                f'border-radius:12px;background:{c["icon_bg"]};'
                f'flex-shrink:0;"></div>'
            )

    return f"""<div style="
        width:100%; height:100%; box-sizing:border-box;
        display:flex; flex-direction:row;
        align-items:center; gap:14px; padding:14px 16px;
        font-family:{font_family};">
  {icon_html}
  <div style="flex:1; min-width:0;">
    <div style="font-size:{title_font_size}; color:{c['title_text']};
                font-weight:500; white-space:nowrap; overflow:hidden;
                text-overflow:ellipsis;">{title}</div>
    <div style="margin-top:4px; display:flex; align-items:baseline; gap:0;">
      <span style="font-size:{value_font_size}; color:{c['value_text']};
                   font-weight:700; line-height:1.1;">{value}</span>
      {delta_html}
    </div>
    {subtitle_html}
  </div>
</div>"""


def _build_comparison(title,
                      label_a, value_a, label_b, value_b,
                      delta, delta_is_positive,
                      font_family, value_font_size, title_font_size,
                      subtitle_font_size, delta_font_size,
                      c, value=None, subtitle=None):  # value/subtitle unused in this style
    """Two values side by side with a divider, delta below."""
    delta_color = (c["delta_positive"] if delta_is_positive
                   else c["delta_negative"] if delta_is_positive is False
                   else c["delta_neutral"])

    delta_html = (
        f'<div style="margin-top:8px;font-size:{delta_font_size};'
        f'color:{delta_color};font-weight:600;text-align:center;">{delta}</div>'
    ) if delta else ""

    return f"""<div style="
        width:100%; height:100%; box-sizing:border-box;
        display:flex; flex-direction:column;
        align-items:center; justify-content:center;
        padding:14px 16px; font-family:{font_family};">
  <div style="font-size:{title_font_size}; color:{c['title_text']};
              font-weight:500; margin-bottom:10px;
              text-align:center;">{title}</div>
  <div style="display:flex; width:100%; align-items:stretch; gap:0;">
    <div style="flex:1; display:flex; flex-direction:column;
                align-items:center; justify-content:center; padding:6px 0;">
      <div style="font-size:{subtitle_font_size}; color:{c['label_a']};
                  font-weight:500; margin-bottom:4px;">{label_a}</div>
      <div style="font-size:{value_font_size}; color:{c['value_a']};
                  font-weight:700; line-height:1.1;">{value_a}</div>
    </div>
    <div style="width:1px; background:{c['divider']}; margin:4px 0;
                flex-shrink:0;"></div>
    <div style="flex:1; display:flex; flex-direction:column;
                align-items:center; justify-content:center; padding:6px 0;">
      <div style="font-size:{subtitle_font_size}; color:{c['label_b']};
                  font-weight:500; margin-bottom:4px;">{label_b}</div>
      <div style="font-size:{value_font_size}; color:{c['value_b']};
                  font-weight:700; line-height:1.1;">{value_b}</div>
    </div>
  </div>
  {delta_html}
</div>"""


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def kpi_card(
    # ── Content ──────────────────────────────────────────────────────────────
    title="KPI Title",
    value="0",
    subtitle=None,             # small text below value (date, source, unit)
    delta=None,                # change indicator, e.g. "+12%" or "▲ 3.2pp"
    delta_is_positive=None,    # True=green, False=red, None=neutral grey
    # ── Style ────────────────────────────────────────────────────────────────
    style="simple",            # "simple" | "icon" | "comparison"
    # 'icon' style extras
    icon_path=None,            # path to .svg/.png or emoji string e.g. "💊"
    icon_size="52px",
    icon_color=None,           # SVG fill color: None=inherit, or e.g. "#2A918B"
                               # Use color_file_path entry (icon/color) for theme-aware color
    # 'comparison' style extras
    label_a="Actual",
    value_a="—",
    label_b="Target",
    value_b="—",
    # ── Typography ───────────────────────────────────────────────────────────
    font_family="Segoe UI, Helvetica Neue, Arial, sans-serif",
    value_font_size="28px",
    title_font_size="12px",
    subtitle_font_size="11px",
    delta_font_size="12px",
    # ── Card shell ───────────────────────────────────────────────────────────
    border_radius="12px",
    # ── Color overrides (None = resolved from color file / defaults) ─────────
    card_bg=None,
    card_border=None,
    card_shadow=None,
    title_color=None,
    value_color=None,
    subtitle_color=None,
    delta_positive_color=None,
    delta_negative_color=None,
    delta_neutral_color=None,
    icon_bg=None,
    # ── Output ───────────────────────────────────────────────────────────────
    output_file=None,
    # ── Theme & color mapping ─────────────────────────────────────────────────
    theme="light",
    color_file_path=None,
    color_sheet_name=None,
    color_topic=None,
):
    """
    Generate a dual-theme KPI card as an HTML fragment for SlideJS.

    The output is a self-contained HTML fragment with an embedded
    window.setChartTheme hook — drop it into Custom_Box_config with
    Source_Type=HTMLTABLE and it will toggle with the presentation theme.

    Parameters
    ----------
    style : "simple" | "icon" | "comparison"
        "simple"     — large centred value, title above, delta + subtitle below
        "icon"       — icon left, title + value + delta right
        "comparison" — two values (label_a/value_a vs label_b/value_b) + delta

    Returns
    -------
    str : output_file path if output_file given, else "TEXT:<html>"
    """
    print(f"\n🎴 Generating KPI card: '{title}' (style={style}, theme={theme})")

    # ── Resolve colours for both themes ──────────────────────────────────────
    _color_df = _kpi_read_color_mapping(color_file_path, sheet_name=color_sheet_name)

    def _rc(param_val, element, elem_name, fallback_key, t):
        return _kpi_resolve_color(param_val, _color_df, color_topic,
                                  element, elem_name, t, fallback_key)

    def _resolve(t):
        is_active = (t == theme)
        pv = lambda v: v if is_active else None
        return {
            "card_bg":         _rc(pv(card_bg),               "card",  "background",  "card_bg",         t),
            "card_border":     _rc(pv(card_border),           "card",  "border",      "card_border",     t),
            "card_shadow":     _rc(pv(card_shadow),           "card",  "shadow",      "card_shadow",     t),
            "title_text":      _rc(pv(title_color),           "title", "text",        "title_text",      t),
            "value_text":      _rc(pv(value_color),           "value", "text",        "value_text",      t),
            "subtitle_text":   _rc(pv(subtitle_color),        "subtitle", "text",     "subtitle_text",   t),
            "delta_positive":  _rc(pv(delta_positive_color),  "delta", "positive",    "delta_positive",  t),
            "delta_negative":  _rc(pv(delta_negative_color),  "delta", "negative",    "delta_negative",  t),
            "delta_neutral":   _rc(pv(delta_neutral_color),   "delta", "neutral",     "delta_neutral",   t),
            "icon_bg":         _rc(pv(icon_bg),               "icon",  "background",  "icon_bg",         t),
            "icon_color":      _rc(pv(icon_color),            "icon",  "color",       "icon_color",      t),
            "divider":         _rc(None,                      "card",  "divider",     "divider",         t),
            "label_a":         _rc(None,                      "comparison", "label_a","label_a",         t),
            "value_a":         _rc(None,                      "comparison", "value_a","value_a",         t),
            "label_b":         _rc(None,                      "comparison", "label_b","label_b",         t),
            "value_b":         _rc(None,                      "comparison", "value_b","value_b",         t),
        }

    cl = _resolve("light")
    cd = _resolve("dark")

    # ── Build inner HTML for each theme ──────────────────────────────────────
    common = dict(
        title=title, value=value, subtitle=subtitle,
        delta=delta, delta_is_positive=delta_is_positive,
        font_family=font_family,
        value_font_size=value_font_size,
        title_font_size=title_font_size,
        subtitle_font_size=subtitle_font_size,
        delta_font_size=delta_font_size,
    )

    if style == "icon":
        inner_light = _build_icon(**common, icon_path=icon_path, icon_size=icon_size, c=cl, icon_color=cl.get("icon_color"))
        inner_dark  = _build_icon(**common, icon_path=icon_path, icon_size=icon_size, c=cd, icon_color=cd.get("icon_color"))
    elif style == "comparison":
        comp = dict(label_a=label_a, value_a=value_a,
                    label_b=label_b, value_b=value_b)
        inner_light = _build_comparison(**common, **comp, c=cl)
        inner_dark  = _build_comparison(**common, **comp, c=cd)
    else:  # "simple"
        inner_light = _build_simple(**common, c=cl)
        inner_dark  = _build_simple(**common, c=cd)

    # ── Card shell — light and dark ───────────────────────────────────────────
    def _shell(inner, c):
        # No display here — display is controlled on the .kpi-light/.kpi-dark wrapper
        return (
            f'<div style="'
            f'width:100%;box-sizing:border-box;'
            f'background:{c["card_bg"]};'
            f'border:1px solid {c["card_border"]};'
            f'border-radius:{border_radius};'
            f'box-shadow:{c["card_shadow"]};'
            f'overflow:hidden;">'
            f'{inner}'
            f'</div>'
        )

    card_light = _shell(inner_light, cl)
    card_dark  = _shell(inner_dark,  cd)

    # ── Stable unique wrapper ID ──────────────────────────────────────────────
    # static_uid is baked into the file at generation time — used as a data attribute
    # to locate THIS wrapper instance. A runtime counter then stamps a unique DOM id
    # on each insertion, so the same file can appear multiple times without collision.
    static_uid = "kpi_" + uuid.uuid4().hex[:12]

    # ── Assemble dual-theme fragment with setChartTheme hook ─────────────────
    html = f"""<div class="dual-theme-kpi-wrapper" data-kpi-uid="{static_uid}" style="width:100%;" data-chart-ready="true">
  <div class="kpi-light" style="display:{'block' if theme == 'light' else 'none'};">{card_light}</div>
  <div class="kpi-dark"  style="display:{'none'  if theme == 'light' else 'block'};">{card_dark}</div>
</div>
<script>
(function() {{
  var uid = '{static_uid}';
  // Assign a runtime-unique id to THIS specific DOM insertion.
  // Finds the last uninitialized wrapper with our data-kpi-uid and stamps it,
  // so duplicate files on the same page each get their own unique id.
  window._kpiSeq = (window._kpiSeq || 0) + 1;
  var runtimeId = 'kpi_r_' + window._kpiSeq + '_' + Date.now();
  var allWrappers = document.querySelectorAll('[data-kpi-uid="' + uid + '"]:not([id])');
  var wrapper = allWrappers[allWrappers.length - 1];
  if (wrapper) wrapper.id = runtimeId;

  var attempts = 0;
  function register() {{
    var el = document.getElementById(runtimeId);
    if (!el) {{
      if (attempts++ < 20) {{ setTimeout(register, 50); }}
      return;
    }}
    var isDark = !!window.isDarkMode;
    var lightDiv = el.querySelector('.kpi-light');
    var darkDiv  = el.querySelector('.kpi-dark');
    if (lightDiv) lightDiv.style.display = isDark ? 'none'  : 'block';
    if (darkDiv)  darkDiv.style.display  = isDark ? 'block' : 'none';
    window.setChartTheme = function(d) {{
      if (lightDiv) lightDiv.style.display = d ? 'none'  : 'block';
      if (darkDiv)  darkDiv.style.display  = d ? 'block' : 'none';
    }};
  }}
  register();
}})();
</script>"""

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"   ✅ KPI card saved: {output_path}  ({len(html):,} chars, dual-theme)")
        return str(output_path)
    else:
        print(f"   ✅ KPI card generated: {len(html):,} chars (dual-theme)")
        return f"TEXT:{html}"