# %% create_bins_numeric

## Dependencies
import pandas as pd

import numpy as np


def create_bins_numeric(df, column_name, nbr_of_bins=5, range_min=0, range_max=100):
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    df.columns = df.columns.str.lower()

    # Use the lowercased column name
    column_name_lower = column_name.lower()

    # Convert the column to numeric, dropping any non-numeric values
    df[column_name_lower] = pd.to_numeric(df[column_name_lower], errors="coerce")
    df = (
        df.dropna().sort_values(column_name_lower).reset_index(drop=True)
    )  # Sort the data and reset index

    if df[column_name_lower].empty:
        raise ValueError("No numeric data found after conversion.")

    # Calculate bins using the entire data range
    bins_default = pd.cut(df[column_name_lower], bins=nbr_of_bins)  # Default bins

    # Create bins based on manually specified range_min and range_max
    # Use float division to ensure proper bin width calculation
    bin_width = (range_max - range_min) / nbr_of_bins
    bins_rounded = np.arange(range_min, range_max + bin_width, bin_width)
    bins_rounded_cut = pd.cut(
        df[column_name_lower], bins=bins_rounded, include_lowest=True, right=False
    )

    # Add both bins to the dataframe
    df["bins_default"] = bins_default  # Default bins based on data distribution
    df["bins_rounded"] = bins_rounded_cut  # Manually specified range bins

    return df, column_name_lower
