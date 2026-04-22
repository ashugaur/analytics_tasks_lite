import re
import pandas as pd

def parse_ui_colors_to_theme_df(css_text: str) -> pd.DataFrame:
    """
    Parses CSS text copied from https://www.iamsajid.com/ui-colors/
    into a Theme_Config-ready DataFrame with light and dark rows.

    Handles messy clipboard input: bare variables, :root blocks, body.light blocks,
    duplicates, mixed order — all cleaned up automatically.

    The 5 slidejs-specific columns not on the site are derived from parsed values:
        muted       ← text_muted
        light       ← border (a mid-tone surface color)
        content_bg  ← bg_light  (lightest surface for content areas)
        slide_bg    ← bg        (main background)
        header_border ← border_muted
    """

    VAR_MAP = {
        "bg-dark":      "bg_dark",
        "bg":           "bg",
        "bg-light":     "bg_light",
        "text":         "text",
        "text-muted":   "text_muted",
        "highlight":    "highlight",
        "border":       "border",
        "border-muted": "border_muted",
        "primary":      "primary",
        "secondary":    "secondary",
        "danger":       "danger",
        "warning":      "warning",
        "success":      "success",
        "info":         "info",
    }

    def parse_vars(block: str, prefer: str = "oklch") -> dict:
        """
        Parse all --var: value; pairs from a CSS block.
        When a variable appears multiple times (hsl then oklch),
        the preferred format wins; falls back to the other.
        """
        hsl_vals    = {}
        oklch_vals  = {}
        pattern = re.compile(r'--([a-zA-Z0-9-]+)\s*:\s*([^;]+);')

        for m in pattern.finditer(block):
            name  = m.group(1).strip()
            value = m.group(2).strip()
            if name not in VAR_MAP:
                continue
            col = VAR_MAP[name]
            if value.startswith("oklch"):
                oklch_vals[col] = value
            elif value.startswith("hsl"):
                hsl_vals[col] = value

        # Merge: preferred format wins, other fills any gaps
        if prefer == "oklch":
            merged = {**hsl_vals, **oklch_vals}
        else:
            merged = {**oklch_vals, **hsl_vals}
        return merged

    def extract_named_block(text: str, selector: str) -> str | None:
        """Extract contents of a named CSS block e.g. ':root { ... }'"""
        sel_esc = re.escape(selector)
        m = re.search(sel_esc + r'\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', text, re.DOTALL)
        return m.group(1) if m else None

    def derive_slidejs_cols(vars_dict: dict) -> dict:
        """
        Derive the 5 slidejs-specific columns that have no CSS equivalent
        on the site, by mapping from semantically similar parsed values.

        Mapping rationale:
          muted         → text_muted  (same concept: de-emphasised text)
          light         → border      (a mid-surface tone used for light text)
          content_bg    → bg_light    (lightest surface, used for content panes)
          slide_bg      → bg          (main page/slide background)
          header_border → border_muted (softest border, used for header lines)
        """
        return {
            "muted":         vars_dict.get("text_muted", ""),
            "light":         vars_dict.get("border",     ""),
            "content_bg":    vars_dict.get("bg_light",   ""),
            "slide_bg":      vars_dict.get("bg",         ""),
            "header_border": vars_dict.get("border_muted", ""),
        }

    # ── Step 1: try to extract named blocks ──────────────────────────────────
    root_block  = extract_named_block(css_text, ":root")
    light_block = extract_named_block(css_text, "body.light")

    # ── Step 2: fall back to parsing the whole text as a flat variable list ──
    # (handles the case where the user pastes bare --var: value; lines)
    if not root_block and not light_block:
        # No named blocks found — treat entire text as one dark-theme block
        all_vars    = parse_vars(css_text)
        dark_vars   = all_vars
        light_vars  = {}
    elif root_block and light_block:
        dark_vars   = parse_vars(root_block)
        light_vars  = parse_vars(light_block)
    elif root_block:
        dark_vars   = parse_vars(root_block)
        light_vars  = {}
    else:
        light_vars  = parse_vars(light_block)
        dark_vars   = {}

    # ── Step 3: build rows ────────────────────────────────────────────────────
    css_cols     = list(VAR_MAP.values())   # all 14 CSS-mapped columns
    slidejs_cols = ["muted", "light", "content_bg", "slide_bg", "header_border"]

    def build_row(theme_name: str, vars_dict: dict) -> dict:
        row = {"Theme_Name": theme_name}
        row["primary"] = vars_dict.get("primary", "")
        row["text"]    = vars_dict.get("text", "")
        # Derived slidejs columns
        row.update(derive_slidejs_cols(vars_dict))
        # Remaining CSS columns
        for col in css_cols:
            if col not in ("primary", "text"):
                row[col] = vars_dict.get(col, "")
        row["Notes"] = f"Auto-parsed from iamsajid.com/ui-colors — {theme_name} theme"
        return row

    rows = []
    if light_vars:
        rows.append(build_row("light", light_vars))
    if dark_vars:
        rows.append(build_row("dark",  dark_vars))
    if not rows:
        raise ValueError("No CSS variables could be parsed from the input text.")

    # ── Step 4: assemble DataFrame with Theme_Config column order ─────────────
    col_order = (
        ["Theme_Name", "primary", "text"]
        + slidejs_cols
        + [c for c in css_cols if c not in ("primary", "text")]
        + ["Notes"]
    )
    df = pd.DataFrame(rows)
    df = df[[c for c in col_order if c in df.columns]]

    return df


if __name__ == "__main__":
    # ── Run it ────────────────────────────────────────────────────────────────────
    css_input = """
    paste full text from site here
    """

    df = parse_ui_colors_to_theme_df(css_input)

    # Pretty print to verify
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(df.to_string(index=False))

    # Copy straight to clipboard → paste into Excel
    df.to_clipboard(index=False)
    print("\n✅ Copied to clipboard — paste into Theme_Config sheet")
