# %% Impute functions
import pandas as pd
import numpy as np
import matplotlib.colors as mcolors
import ast


## Dependencies
def fill_missing_colors(df: pd.DataFrame) -> pd.DataFrame:
    def rgb_to_hex(rgb):
        """Convert R, G, B values in 0-255 range to hex."""
        if isinstance(rgb, (list, tuple)) and len(rgb) == 3:
            rgb_norm = tuple(x / 255 for x in rgb)  # Normalize RGB values to 0-1
            return mcolors.to_hex(rgb_norm)
        return None

    def hex_to_rgb(hex_code):
        """Convert hex color to comma-separated R, G, B string in 0-255 range."""
        if isinstance(hex_code, str) and hex_code.startswith("#"):
            return ", ".join(str(int(x * 255)) for x in mcolors.to_rgb(hex_code))
        return None

    df = df.copy()

    # Replace '.' with NaN using numpy where instead of deprecated replace method
    df["color_hex"] = np.where(df["color_hex"] == ".", np.nan, df["color_hex"])
    df["color_rgb"] = np.where(df["color_rgb"] == ".", np.nan, df["color_rgb"])

    # Convert 'color_rgb' string tuples into comma-separated strings
    df["color_rgb"] = df["color_rgb"].apply(
        lambda x: ", ".join(map(str, ast.literal_eval(x)))
        if isinstance(x, str) and x.startswith("(")
        else x
    )

    # Explicitly cast 'color_rgb' column to 'object' dtype
    df["color_rgb"] = df["color_rgb"].astype("object")

    # Fill missing color_hex values using RGB conversion
    df.loc[df["color_hex"].isna(), "color_hex"] = df.loc[
        df["color_hex"].isna(), "color_rgb"
    ].apply(
        lambda x: rgb_to_hex(tuple(map(int, x.split(", "))))
        if isinstance(x, str)
        else None
    )

    # Fill missing color_rgb values using hex conversion
    df.loc[df["color_rgb"].isna(), "color_rgb"] = df.loc[
        df["color_rgb"].isna(), "color_hex"
    ].apply(hex_to_rgb)

    return df
