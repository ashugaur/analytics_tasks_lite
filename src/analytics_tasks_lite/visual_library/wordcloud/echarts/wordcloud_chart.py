# %% Word Cloud Chart

## Dependencies
import base64
import json
import re
from collections import Counter
from io import BytesIO
from pathlib import Path

# ============================================================================
# THEME DEFAULTS
# ============================================================================

THEME_DEFAULTS = {
    "light": {
        "chart_title":    "#00165e",
        "chart_subtitle": "#666666",
        "tooltip_bg":     "rgba(255, 255, 255, 0.95)",
        "tooltip_border": "#ccc",
        "tooltip_text":   "#333",
        "legend_text":    "#00165e",
    },
    "dark": {
        "chart_title":    "#dcdcdc",
        "chart_subtitle": "#aaaaaa",
        "tooltip_bg":     "rgba(50, 50, 50, 0.95)",
        "tooltip_border": "#666",
        "tooltip_text":   "#fff",
        "legend_text":    "#dcdcdc",
    },
}

DEFAULT_WORD_COLORS = {
    "light": ["#1a6faf","#c0392b","#16a085","#8e44ad",
              "#d35400","#27ae60","#2980b9","#f39c12",
              "#2c3e50","#e74c3c","#1abc9c","#9b59b6"],
    "dark":  ["#4da6e8","#e87d74","#48c9b0","#c39bd3",
              "#f0a27a","#6fcf97","#7fb3d3","#f7dc6f",
              "#95a5a6","#ff6b6b","#1dd3b0","#c77dff"],
}

VALID_SHAPES = {
    "circle","cardioid","diamond","triangle-forward",
    "triangle","pentagon","star",
}

DEFAULT_STOPWORDS = {
    "a","an","the","and","or","but","in","on","at","to","for",
    "of","with","by","from","is","are","was","were","be","been",
    "being","have","has","had","do","does","did","will","would",
    "could","should","may","might","shall","can","not","this","that",
    "these","those","it","its","as","if","so","we","you","he","she",
    "they","their","our","your","his","her","i","me","my","us",
    "also","which","who","what","when","where","how","than","more",
    "into","about","up","out","such","there","then","thus",
    "https","www","com","org","en","wikipedia",
}


# ============================================================================
# COLOR MAPPING UTILITIES
# ============================================================================

def read_color_mapping(color_file_path, sheet_name="colorsEcharts"):
    try:
        import pandas as pd
        if isinstance(sheet_name, dict):
            sheet_name = sheet_name.get("name")
        df = pd.read_excel(color_file_path, sheet_name=sheet_name)
        df.columns = [c.lower().strip() for c in df.columns]
        return df
    except Exception as e:
        print(f"Warning: Could not read color file: {e}")
        return None

def get_element_color(color_df, topic, chart_type, chart_element, element_name, theme):
    if color_df is None:
        return None
    hex_col = "light_hex" if theme == "light" else "dark_hex"
    match = color_df[
        (color_df["topic"]         == topic)
        & (color_df["chart_type"]    == chart_type)
        & (color_df["chart_element"] == chart_element)
        & (color_df["element_name"]  == element_name)
    ]
    if not match.empty:
        return match.iloc[0][hex_col]
    return None

def resolve_color(param_value, color_df, topic, chart_type, chart_element, element_name, theme):
    if param_value is not None:
        return param_value
    if color_df is not None and topic is not None:
        c = get_element_color(color_df, topic, chart_type, chart_element, element_name, theme)
        if c:
            return c
    return THEME_DEFAULTS.get(theme, THEME_DEFAULTS["light"]).get(chart_element, "#000000")


# ============================================================================
# TEXT PROCESSING
# ============================================================================

def text_to_word_freq(text, stopwords=None, min_word_length=3, max_words=200):
    """Convert raw text → [(word, frequency), ...] sorted descending."""
    if stopwords is None:
        stopwords = DEFAULT_STOPWORDS
    words = re.findall(r"[a-zA-Z']+", text.lower())
    words = [w.strip("'") for w in words
             if len(w) >= min_word_length and w not in stopwords]
    return Counter(words).most_common(max_words)

def dict_to_word_freq(word_dict, max_words=200):
    """Convert {word: weight} → sorted [(word, weight), ...]."""
    return sorted(word_dict.items(), key=lambda x: x[1], reverse=True)[:max_words]


# ============================================================================
# IMAGE MASK UTILITIES
# ============================================================================

def prepare_mask_image(
    image_path,
    mask_width=700,
    bg_threshold=15,
    color_ref_width=350,
):
    """
    Prepare image assets for ECharts wordcloud masking.

    How echarts-wordcloud (wordcloud2.js) uses maskImage
    ─────────────────────────────────────────────────────
    wordcloud2.js draws the maskImage onto an offscreen <canvas>, then reads
    pixel data with getImageData(). It checks the ALPHA channel (index 3) of
    each pixel:

        alpha == 0  →  pixel is EXCLUDED  (no word placed here)
        alpha > 0   →  pixel is AVAILABLE (words fill here)

    This means the mask must be a RGBA PNG where:
        • background pixels  → alpha = 0   (transparent, excluded)
        • subject pixels     → alpha = 255 (opaque, word fill zone)

    The parrot JPG has a plain black background (R+G+B < bg_threshold), so
    we detect it by brightness sum and set those pixels transparent.

    Two assets are returned:
        mask_data_uri   : RGBA PNG (tiny ~6KB) — drives word placement shape
        color_data_uri  : RGB JPEG (small ~20KB) — used in JS to sample pixel
                          colors at each word's canvas position, replicating
                          the image-colored effect from the Python wordcloud

    Parameters
    ----------
    image_path      : str | Path — Source image (JPG/PNG/GIF with dark BG).
    mask_width      : int  — Mask image width in px. Default: 700.
                      Height is computed to preserve aspect ratio.
                      This MUST match the ECharts series width/height ratio.
    bg_threshold    : int  — Pixels with RGB sum < this = background.
                      Default: 15. Raise to 25–40 for noisy dark backgrounds.
    color_ref_width : int  — Width of the color-sampling JPEG. Default: 350.
                      Half of mask_width is a good balance.

    Returns
    -------
    dict:
        mask_data_uri   : str  — 'data:image/png;base64,...'  (RGBA mask)
        color_data_uri  : str  — 'data:image/jpeg;base64,...' (color reference)
        mask_width      : int
        mask_height     : int
        color_ref_width : int
        color_ref_height: int
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        raise ImportError("pip install pillow numpy")

    img = Image.open(image_path).convert("RGB")
    W   = mask_width
    H   = int(img.height * W / img.width)
    img_r = img.resize((W, H), Image.LANCZOS)
    arr   = np.array(img_r)

    # Detect background: near-black pixels
    bg = arr.sum(axis=2) < bg_threshold

    # ── Asset 1: RGBA mask (transparent bg, opaque subject) ───────────────
    rgba      = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[~bg, 3] = 255           # parrot area = fully opaque
    # Colour doesn't matter for masking, but set to mid-grey so it's
    # visible if someone opens the PNG directly
    rgba[~bg, 0] = 128
    rgba[~bg, 1] = 128
    rgba[~bg, 2] = 128
    buf = BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG", optimize=True)
    mask_b64      = base64.b64encode(buf.getvalue()).decode()
    mask_data_uri = f"data:image/png;base64,{mask_b64}"

    # ── Asset 2: Color reference JPEG ────────────────────────────────────
    W2  = color_ref_width
    H2  = int(img.height * W2 / img.width)
    buf2 = BytesIO()
    img.resize((W2, H2), Image.LANCZOS).save(buf2, "JPEG", quality=82)
    color_b64      = base64.b64encode(buf2.getvalue()).decode()
    color_data_uri = f"data:image/jpeg;base64,{color_b64}"

    pct_subject = (~bg).mean() * 100
    print(
        f"Mask ready │ {W}×{H}px │ subject {pct_subject:.1f}% │ "
        f"mask {len(mask_b64)//1024}KB │ color-ref {len(color_b64)//1024}KB"
    )
    return {
        "mask_data_uri":    mask_data_uri,
        "color_data_uri":   color_data_uri,
        "mask_width":       W,
        "mask_height":      H,
        "color_ref_width":  W2,
        "color_ref_height": H2,
    }


# ============================================================================
# MAIN CHART FUNCTION
# ============================================================================

chart_type = "wordcloud_chart"

def wordcloud_chart(
    data,
    # ── Data ──
    text_col=None, word_col="word", weight_col="weight",
    stopwords=None, min_word_length=3, max_words=200,
    # ── Theme & colors ──
    theme="light", word_colors=None,
    color_file_path=None, color_sheet_name=None, color_topic=None,
    # ── Shape ──
    shape="circle",
    mask_image_path=None,
    mask_width=700,
    mask_bg_threshold=15,
    keep_aspect=True,
    # ── Layout ──
    size_range_min=12, size_range_max=60,
    rotation_range_min=-45, rotation_range_max=45, rotation_step=45,
    grid_size=4, draw_out_of_bound=False,
    # ── Dimensions ──
    chart_width="100%", chart_height="100%",
    # ── Title ──
    chart_title="", chart_title_font_size=14,
    chart_title_font_weight="bold", chart_title_font_family=None,
    chart_title_color=None, chart_title_position="top-left",
    chart_subtitle="", chart_subtitle_font_size=12,
    chart_subtitle_font_weight="normal", chart_subtitle_color=None,
    # ── Tooltip ──
    tooltip_show=True, tooltip_font_size=12,
    tooltip_background_color=None, tooltip_border_color=None,
    tooltip_text_color=None,
    # ── Global ──
    chart_font_family="Arial", chart_background="transparent",
    renderer="canvas",
):
    """
    Create an ECharts word cloud chart.

    Returns a tuple (option, width, height, theme, theme_ui, mask_assets)
    ready to pass directly into generate_wordcloud_html().

    mask_image_path
    ───────────────
    Path to a local image with a dark/black background (JPG, PNG, GIF).
    The function auto-generates two assets from it:

      • A transparent-background RGBA PNG used as maskImage — wordcloud2.js
        places words only where alpha > 0, producing the exact silhouette.

      • A colour-reference JPEG drawn on a hidden <canvas> in the HTML.
        A custom textStyle.color function samples the pixel at each word's
        canvas coordinates, so every word inherits the image colour at that
        spot — replicating the Python wordcloud photo-colour effect.

    shape still controls the spiral growth direction inside the mask,
    'circle' works best for compact fills.

    mask_width      : int  — Mask resolution in px. Default: 700.
                      The series is sized to match this aspect ratio.
    mask_bg_threshold: int — RGB sum threshold for background detection.
                      Default: 15 (pure-black BG). Raise for noisy BGs.
    """

    # ── Normalise data ────────────────────────────────────────────────────
    word_freq = _resolve_data(
        data, text_col, word_col, weight_col, stopwords, min_word_length, max_words
    )
    if not word_freq:
        raise ValueError("No word data found.")

    if shape not in VALID_SHAPES:
        print(f"Warning: shape='{shape}' unknown, falling back to 'circle'.")
        shape = "circle"

    # ── Color mapping ─────────────────────────────────────────────────────
    color_df = None
    if color_file_path:
        color_df = read_color_mapping(color_file_path, color_sheet_name or "colorsEcharts")

    def _rc(param, el, nm):
        return resolve_color(param, color_df, color_topic, chart_type, el, nm, theme)

    resolved = {
        "chart_title":    _rc(chart_title_color,          "chart_title",    "main"),
        "chart_subtitle": _rc(chart_subtitle_color,        "chart_subtitle", "main"),
        "tooltip_bg":     _rc(tooltip_background_color,    "tooltip_bg",     "main"),
        "tooltip_border": _rc(tooltip_border_color,        "tooltip_border", "main"),
        "tooltip_text":   _rc(tooltip_text_color,          "tooltip_text",   "main"),
    }

    # ── Process mask image ────────────────────────────────────────────────
    mask_assets = None
    if mask_image_path is not None:
        mask_assets = prepare_mask_image(
            mask_image_path,
            mask_width=mask_width,
            bg_threshold=mask_bg_threshold,
            color_ref_width=mask_width // 2,
        )

    # ── Build word data ───────────────────────────────────────────────────
    wc_light = DEFAULT_WORD_COLORS["light"]
    wc_dark  = DEFAULT_WORD_COLORS["dark"]
    wc_cur   = word_colors or DEFAULT_WORD_COLORS.get(theme, wc_light)

    echarts_data = [
        {
            "name":      str(w),
            "value":     float(v),
            "itemStyle": {"color": wc_cur[i % len(wc_cur)]},
            "_lc":       wc_light[i % len(wc_light)],
            "_dc":       wc_dark[i  % len(wc_dark)],
        }
        for i, (w, v) in enumerate(word_freq)
    ]

    # ── Title ─────────────────────────────────────────────────────────────
    title_left  = {"top-left":"left","top-center":"center","top-right":"right"}.get(
        chart_title_position, "left"
    )
    title_config = {}
    if chart_title:
        title_config = {
            "text": chart_title, "subtext": chart_subtitle,
            "left": title_left,  "top": "top",
            "textStyle": {
                "fontSize": chart_title_font_size,
                "fontWeight": chart_title_font_weight,
                "fontFamily": chart_title_font_family or chart_font_family,
                "color": resolved["chart_title"],
            },
            "subtextStyle": {
                "fontSize": chart_subtitle_font_size,
                "fontWeight": chart_subtitle_font_weight,
                "fontFamily": chart_font_family,
                "color": resolved["chart_subtitle"],
            },
        }

    # ── Series ────────────────────────────────────────────────────────────
    series = {
        "type":           "wordCloud",
        "shape":          shape,
        "keepAspect":     keep_aspect,
        "sizeRange":      [size_range_min, size_range_max],
        "rotationRange":  [rotation_range_min, rotation_range_max],
        "rotationStep":   rotation_step,
        "gridSize":       grid_size,
        "drawOutOfBound": draw_out_of_bound,
        "layoutAnimation": True,
        "textStyle": {
            "fontFamily": chart_font_family,
            "fontWeight": "bold",
        },
        "emphasis": {
            "focus": "self",
            "textStyle": {"textShadowBlur": 8, "textShadowColor": "rgba(0,0,0,0.5)"},
        },
        "data": echarts_data,
    }

    # If mask image provided, size the series to exactly match mask aspect ratio.
    # We do NOT set maskImage here — it's injected in JS after Image.onload.
    if mask_assets:
        mw = mask_assets["mask_width"]
        mh = mask_assets["mask_height"]
        series["left"]   = "center"
        series["top"]    = "center"
        series["width"]  = f"{mw}px"
        series["height"] = f"{mh}px"
    else:
        series["left"]   = "center"
        series["top"]    = "center"
        series["width"]  = "90%"
        series["height"] = "90%"

    option = {
        "backgroundColor": chart_background,
        "tooltip": {
            "show": tooltip_show,
            "padding": 10,
            "textStyle": {"fontSize": tooltip_font_size, "color": resolved["tooltip_text"]},
            "backgroundColor": resolved["tooltip_bg"],
            "borderColor":     resolved["tooltip_border"],
        },
        "series": [series],
    }
    if title_config:
        option["title"] = title_config

    # ── Theme UI map ──────────────────────────────────────────────────────
    def _rct(el, nm, t):
        return resolve_color(None, color_df, color_topic, chart_type, el, nm, t)

    theme_ui = {
        "light": {
            "tooltipBg":     _rct("tooltip_bg",     "main","light"),
            "tooltipBorder": _rct("tooltip_border",  "main","light"),
            "tooltipText":   _rct("tooltip_text",    "main","light"),
            "chartTitle":    _rct("chart_title",     "main","light"),
            "chartSubtitle": _rct("chart_subtitle",  "main","light"),
        },
        "dark": {
            "tooltipBg":     _rct("tooltip_bg",     "main","dark"),
            "tooltipBorder": _rct("tooltip_border",  "main","dark"),
            "tooltipText":   _rct("tooltip_text",    "main","dark"),
            "chartTitle":    _rct("chart_title",     "main","dark"),
            "chartSubtitle": _rct("chart_subtitle",  "main","dark"),
        },
    }

    return option, chart_width, chart_height, theme, theme_ui, mask_assets


# ============================================================================
# DATA NORMALISATION
# ============================================================================

def _resolve_data(data, text_col, word_col, weight_col, stopwords, min_word_length, max_words):
    if isinstance(data, str):
        return text_to_word_freq(data, stopwords=stopwords,
                                 min_word_length=min_word_length, max_words=max_words)
    if isinstance(data, dict):
        return dict_to_word_freq(data, max_words=max_words)
    if isinstance(data, list):
        if data and isinstance(data[0], (list, tuple)) and len(data[0]) == 2:
            return [(str(w), float(v))
                    for w, v in sorted(data, key=lambda x: x[1], reverse=True)[:max_words]]
        raise ValueError("List items must be (word, weight) tuples.")
    try:
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            if text_col and text_col in data.columns:
                full_text = " ".join(data[text_col].dropna().astype(str).tolist())
                return text_to_word_freq(full_text, stopwords=stopwords,
                                         min_word_length=min_word_length, max_words=max_words)
            if word_col in data.columns and weight_col in data.columns:
                rows = (data[[word_col, weight_col]].dropna()
                        .sort_values(weight_col, ascending=False).head(max_words))
                return [(str(r[word_col]), float(r[weight_col])) for _, r in rows.iterrows()]
            raise ValueError(f"DataFrame needs '{word_col}'+'{weight_col}' or text_col.")
    except ImportError:
        pass
    raise TypeError(f"Unsupported data type: {type(data)}.")


# ============================================================================
# HTML GENERATION
# ============================================================================

def generate_wordcloud_html(
    option,
    width="100%",
    height="100%",
    output_file="wordcloud_chart.html",
    renderer="canvas",
):
    """
    Generate a fully self-contained HTML file with an ECharts word cloud.

    When a mask image was provided to wordcloud_chart(), the HTML includes:
      • The RGBA mask PNG embedded as a data URI — drives word placement shape
      • The colour-reference JPEG embedded as a data URI — for pixel-colour sampling
      • JS that loads both images, attaches maskImage, and overrides
        textStyle.color with a function that samples the colour image at each
        word's canvas coordinates (replicating the Python photo-colour effect)

    Parameters
    ----------
    option      : tuple returned by wordcloud_chart(), or a raw option dict.
    width       : CSS container width.
    height      : CSS container height.
    output_file : Output .html filename.
    renderer    : 'canvas' (strongly preferred) or 'svg'.
    """
    theme    = "light"
    theme_ui = None
    mask_assets = None

    if isinstance(option, tuple):
        if len(option) == 6:
            option, width, height, theme, theme_ui, mask_assets = option
        elif len(option) == 5:
            option, width, height, theme, theme_ui = option
        elif len(option) == 4:
            option, width, height, theme = option
        elif len(option) == 3:
            option, width, height = option

    if theme_ui is None:
        theme_ui = {
            "light": {"tooltipBg":"rgba(255,255,255,0.95)","tooltipBorder":"#ccc",
                      "tooltipText":"#333","chartTitle":"#00165e","chartSubtitle":"#666"},
            "dark":  {"tooltipBg":"rgba(50,50,50,0.95)",  "tooltipBorder":"#666",
                      "tooltipText":"#fff","chartTitle":"#dcdcdc","chartSubtitle":"#aaa"},
        }

    theme_ui_js = json.dumps(theme_ui)
    option_js   = json.dumps(option, indent=2)

    # ── Build mask + color-sampling JS block ─────────────────────────────────
    if mask_assets:
        mw  = mask_assets["mask_width"]
        mh  = mask_assets["mask_height"]
        crw = mask_assets["color_ref_width"]
        crh = mask_assets["color_ref_height"]
        mask_uri  = mask_assets["mask_data_uri"]
        color_uri = mask_assets["color_data_uri"]

        mask_js = f"""
        // ── Responsive sizing: scale series to fit container ──────────────────
        function fitSeriesSize() {{
            var cw = chartDom.clientWidth  || 800;
            var ch = chartDom.clientHeight || 600;
            var aspectW = {mw}, aspectH = {mh};
            var scale   = Math.min(cw / aspectW, ch / aspectH) * 0.95;
            var sw      = Math.round(aspectW * scale);
            var sh      = Math.round(aspectH * scale);
            option.series[0].width  = sw + 'px';
            option.series[0].height = sh + 'px';
        }}

        // ── Pre-extract all pixel data ONCE from the colour reference image ────
        // willReadFrequently:true tells the browser to keep pixel data in CPU
        // memory so getImageData() is fast. We call it only once here at load
        // time — during rendering we do pure array lookups with zero canvas reads.
        var colorCanvas = document.createElement('canvas');
        colorCanvas.width  = {crw};
        colorCanvas.height = {crh};
        var colorCtx = colorCanvas.getContext('2d', {{ willReadFrequently: true }});
        var pixelData = null;   // flat Uint8ClampedArray: [R,G,B,A, R,G,B,A, ...]

        // Pre-build a lookup table: word index → hex color string
        // Computed once after pixel data is ready; zero cost during rendering.
        var wordColorTable = [];

        function buildColorTable(total) {{
            wordColorTable = [];
            if (!pixelData) return;
            for (var i = 0; i < total; i++) {{
                // Spread words across the image via an Archimedean spiral
                // so early (large) words land near the centre of the parrot
                // and later (small) words fan outward — matching wordcloud layout.
                var t   = i / Math.max(total - 1, 1);
                var ang = t * Math.PI * 8;          // 4 full turns
                var r   = Math.sqrt(t) * 0.42;      // radius grows as √t
                var nx  = Math.max(0.04, Math.min(0.96, 0.5 + r * Math.cos(ang)));
                var ny  = Math.max(0.04, Math.min(0.96, 0.5 + r * Math.sin(ang)));
                var px  = Math.round(nx * ({crw} - 1));
                var py  = Math.round(ny * ({crh} - 1));
                var off = (py * {crw} + px) * 4;
                var R = pixelData[off], G = pixelData[off+1], B = pixelData[off+2];
                // If pixel is near-black (background), walk inward toward centre
                var attempts = 0;
                while (R + G + B < 30 && attempts < 8) {{
                    nx = 0.5 + (nx - 0.5) * 0.7;
                    ny = 0.5 + (ny - 0.5) * 0.7;
                    px  = Math.round(nx * ({crw} - 1));
                    py  = Math.round(ny * ({crh} - 1));
                    off = (py * {crw} + px) * 4;
                    R = pixelData[off]; G = pixelData[off+1]; B = pixelData[off+2];
                    attempts++;
                }}
                wordColorTable.push(
                    '#' + ('0'+R.toString(16)).slice(-2)
                        + ('0'+G.toString(16)).slice(-2)
                        + ('0'+B.toString(16)).slice(-2)
                );
            }}
        }}

        // ── textStyle.color callback — pure array lookup, no canvas reads ──────
        function sampleWordColor(params) {{
            var idx = params.dataIndex !== undefined ? params.dataIndex : 0;
            return wordColorTable[idx] || '#cccccc';
        }}

        // ── Load both images in parallel, render when both are ready ──────────
        var maskImg   = new Image();
        var colorImg  = new Image();
        var readyCount = 0;

        function onImageReady() {{
            readyCount++;
            if (readyCount < 2) return;   // wait for both
            // Extract all pixel data once — only getImageData call in the file
            colorCtx.drawImage(colorImg, 0, 0, {crw}, {crh});
            pixelData = colorCtx.getImageData(0, 0, {crw}, {crh}).data;
            buildColorTable(option.series[0].data.length);
            fitSeriesSize();
            option.series[0].maskImage  = maskImg;
            option.series[0].textStyle.color = sampleWordColor;
            myChart.setOption(option, true);
            chartDom.setAttribute('data-chart-ready', 'true');
        }}

        maskImg.onload  = onImageReady;
        colorImg.onload = onImageReady;
        maskImg.src     = '{mask_uri}';
        colorImg.src    = '{color_uri}';"""

        set_option_block = "// (setOption deferred until both images load)"
        ready_block      = "// (data-chart-ready set after images load)"
        resize_extra     = """
            fitSeriesSize();
            myChart.setOption({ series: option.series }, false);"""
    else:
        mask_js          = ""
        set_option_block = "myChart.setOption(option, true);"
        ready_block      = "chartDom.setAttribute('data-chart-ready', 'true');"
        resize_extra     = ""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>ECharts Word Cloud</title>
  <style>
    * {{ box-sizing: border-box; margin:0; padding:0; }}
    body, html {{ background:transparent; overflow:hidden; }}
    #main {{ position:absolute; top:0; left:0; width:100vw; height:100vh; }}
  </style>
  <script>
    // Patch getContext BEFORE any library loads so every canvas on the page
    // — including the ones created internally by echarts-wordcloud/layout.js —
    // always has willReadFrequently:true. This eliminates the browser warning
    // "Multiple readback operations using getImageData are faster with
    // willReadFrequently" that originates from layout.js:1195.
    (function () {{
      var _orig = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (type, attrs) {{
        if (type === '2d') {{
          attrs = Object.assign({{}}, attrs, {{ willReadFrequently: true }});
        }}
        return _orig.call(this, type, attrs);
      }};
    }})();
  </script>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/echarts-wordcloud@2.1.0/dist/echarts-wordcloud.min.js"></script>
</head>
<body>
  <div id="main"></div>
  <script>
    var chartDom, myChart;
    function initChart() {{
      chartDom = document.getElementById('main');
      myChart  = echarts.init(chartDom, null, {{renderer:'{renderer}'}});

    var option = {option_js};

    // ── Tooltip formatter ───────────────────────────────────────────────
    option.tooltip.formatter = function(p) {{
      var c = (p.data.itemStyle && p.data.itemStyle.color) ? p.data.itemStyle.color : '#999';
      var dot = '<span style="display:inline-block;width:10px;height:10px;'
              + 'border-radius:50%;background:'+c+';margin-right:6px;vertical-align:middle;"></span>';
      return '<div style="line-height:1.6">' + dot + '<b>' + p.name + '</b>'
           + '<br>Count: <b>' + p.value.toLocaleString() + '</b></div>';
    }};

    {set_option_block}

    {mask_js}

    // ── Dual-theme support ──────────────────────────────────────────────
    var _themeUI = {theme_ui_js};
    window.setChartTheme = function(isDark) {{
      var t = isDark ? _themeUI.dark : _themeUI.light;
      option.series.forEach(function(s) {{
        s.data.forEach(function(pt) {{
          if (pt._lc && pt._dc) {{
            pt.itemStyle      = pt.itemStyle || {{}};
            pt.itemStyle.color = isDark ? pt._dc : pt._lc;
          }}
        }});
      }});
      myChart.setOption({{
        title:   {{ textStyle:{{color:t.chartTitle}}, subtextStyle:{{color:t.chartSubtitle}} }},
        tooltip: {{ backgroundColor:t.tooltipBg, borderColor:t.tooltipBorder,
                    textStyle:{{color:t.tooltipText}} }},
        series: option.series
      }});
    }};

    {ready_block}

    window.addEventListener('resize', function() {{
      myChart.resize();{resize_extra}
    }});
    }} // end initChart

    // Use rAF so the browser has painted #main and clientWidth/Height are real
    requestAnimationFrame(function() {{
      requestAnimationFrame(initChart);
    }});
  </script>
</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved → {output_file}")
    return output_file


# ============================================================================
# EXAMPLES
# ============================================================================

def run_example_shape():
    """Circle shape, no mask image."""
    text = open(Path(__file__).parent / "parrot.txt", encoding="utf-8").read()
    result = wordcloud_chart(
        text, theme="dark",
        chart_title="Rainbow — Wikipedia",
        chart_subtitle="Shape only · circle",
        shape="circle", size_range_min=14, size_range_max=72,
    )
    generate_wordcloud_html(result, output_file="wordcloud_shape.html")


def run_example_parrot_mask():
    """Parrot silhouette mask with image-sampled word colours."""
    text = open(Path(__file__).parent / "parrot.txt", encoding="utf-8").read()
    result = wordcloud_chart(
        text, theme="dark",
        chart_title="Rainbow — Wikipedia",
        chart_subtitle="Parrot silhouette · image-colour words",
        shape="circle",
        mask_image_path=Path(__file__).parent / "parrot.jpg",
        mask_width=700,
        mask_bg_threshold=15,
        keep_aspect=True,
        size_range_min=10, size_range_max=56,
        rotation_range_min=-45, rotation_range_max=45,
        grid_size=4,
    )
    generate_wordcloud_html(result, output_file="wordcloud_parrot_mask.html")


def run_example_parrot_horizontal():
    """Parrot silhouette, horizontal words only."""
    text = open(Path(__file__).parent / "parrot.txt", encoding="utf-8").read()
    result = wordcloud_chart(
        text, theme="dark",
        chart_title="Rainbow — Wikipedia",
        chart_subtitle="Parrot silhouette · horizontal words",
        shape="circle",
        mask_image_path=Path(__file__).parent / "parrot.jpg",
        mask_width=700, mask_bg_threshold=15,
        rotation_range_min=0, rotation_range_max=0,
        size_range_min=10, size_range_max=52,
        grid_size=5,
    )
    generate_wordcloud_html(result, output_file="wordcloud_parrot_horizontal.html")


if __name__ == "__main__":
    run_example_shape()
    run_example_parrot_mask()
    run_example_parrot_horizontal()
