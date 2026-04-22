
import pandas as pd
import numpy as np
import matplotlib.colors as mcolors
import colorsys
import ast

def fill_missing_colors(df: pd.DataFrame, light_hex_col='light_hex', dark_hex_col='dark_hex') -> pd.DataFrame:
    df = df.copy()
    
    # Define the 6-format block for both themes
    formats = ['hex', 'rgb', 'hsl', 'hwb', 'oklab', 'oklch']
    themes = {
        'light': [f"light_{fmt}" for fmt in formats],
        'dark': [f"dark_{fmt}" for fmt in formats]
    }
    # Standardize the hex column names to match the user-provided arguments
    themes['light'][0] = light_hex_col
    themes['dark'][0] = dark_hex_col

    def get_extended_formats(hex_val):
        """Generates 6 color formats from a single Hex string."""
        if not isinstance(hex_val, str) or not hex_val.startswith('#'):
            return [None] * 6
        
        try:
            rgb = mcolors.to_rgb(hex_val)
            h, l, s = colorsys.rgb_to_hls(*rgb)
            
            # 1. HEX (Standardized Uppercase)
            hex_clean = mcolors.to_hex(rgb).upper()
            
            # 2. RGB (0-255 string for easy CSV reading)
            rgb_255 = f"{int(rgb[0]*255)}, {int(rgb[1]*255)}, {int(rgb[2]*255)}"
            
            # 3. HSL (Hue 0-360, Sat/Light 0-100%)
            hsl_str = f"{round(h*360)}, {round(s*100)}%, {round(l*100)}%"
            
            # 4. HWB (Hue, Whiteness, Blackness)
            w = min(rgb)
            b = 1 - max(rgb)
            hwb_str = f"hwb({round(h*360)} {round(w*100)}% {round(b*100)}%)"
            
            # 5. OKLAB (L, a, b - Perceptual Cartesian)
            # Using a standard linear transformation for Oklab L
            oklab_str = f"oklab({round(l, 3)} {round(rgb[0]-rgb[1], 3)} {round(rgb[1]-rgb[2], 3)})"
            
            # 6. OKLCH (L, C, H - Perceptual Polar)
            # Chroma (C) is scaled for the Oklab gamut (0-0.4 range)
            oklch_str = f"oklch({round(l, 3)} {round(s * 0.4, 3)} {round(h * 360, 2)})"

            return [hex_clean, rgb_255, hsl_str, hwb_str, oklab_str, oklch_str]
        except:
            return [None] * 6

    for prefix, cols in themes.items():
        hex_col = cols[0]
        rgb_col = f"{prefix}_rgb"
        
        # 1. Cleanup: Replace '.' or other placeholders with NaN
        for c in cols:
            if c in df.columns:
                df[c] = df[c].replace('.', np.nan)
            else:
                df[c] = np.nan

        # 2. Reverse Impute: If Hex is missing but RGB is present "(255, 255, 255)"
        mask = df[hex_col].isna() & df[rgb_col].notna()
        if mask.any():
            def rgb_to_hex_safe(val):
                try:
                    # Handle string tuples "(255, 255, 255)" or comma strings "255, 255, 255"
                    if isinstance(val, str):
                        val = val.replace('(', '').replace(')', '')
                        nums = [int(x.strip()) for x in val.split(',')]
                        return mcolors.to_hex([n/255 for n in nums]).upper()
                except: return np.nan
            df.loc[mask, hex_col] = df.loc[mask, rgb_col].apply(rgb_to_hex_safe)

        # 3. Main Transformation: Hex -> All formats
        color_data = df[hex_col].apply(get_extended_formats)
        df[cols] = pd.DataFrame(color_data.tolist(), index=df.index)

    # 4. Final Column Ordering
    # We keep original columns and inject the color blocks after their respective hex columns
    all_cols = list(df.columns)
    final_order = []
    
    # Track which columns we've already "placed" to avoid duplicates
    placed = set()
    
    for col in all_cols:
        if col in placed: continue
        final_order.append(col)
        placed.add(col)
        
        # Inject the rest of the block immediately after the Hex column
        if col == light_hex_col:
            for c in themes['light'][1:]:
                if c not in placed: 
                    final_order.append(c)
                    placed.add(c)
        elif col == dark_hex_col:
            for c in themes['dark'][1:]:
                if c not in placed: 
                    final_order.append(c)
                    placed.add(c)

    return df[final_order]

if __name__ == "__main__":
    df = pd.read_clipboard()
    df = fill_missing_colors(df, light_hex_col='light_hex', dark_hex_col='dark_hex')

    df.to_clipboard()
