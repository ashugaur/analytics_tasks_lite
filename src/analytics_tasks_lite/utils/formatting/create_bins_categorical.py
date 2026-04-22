# %% Formatting

## Dependencies
import math


def create_bins_categorical(df, column_name=None, nbr_of_bins=5):
    """
    Create bins for a categorical column.

    Parameters
    ----------
    df : pd.DataFrame
        Input data.  The function does **not** modify the original frame.
    column_name : str | None
        Column to bin.  If None, the first non‑numeric column is used.
    nbr_of_bins : int
        Desired number of bins.

    Returns
    -------
    tuple
        (df_copy, column_name, bins)
    """
    # Work on a copy to preserve the original df
    df_copy = df.copy()

    # Infer column if not supplied
    if column_name is None:
        cat_cols = df_copy.select_dtypes(include=["object", "category"]).columns
        if not cat_cols.size:
            raise ValueError(
                "No categorical columns found; please specify `column_name`."
            )
        column_name = cat_cols[0]

    # Ensure the column exists
    if column_name not in df_copy.columns:
        raise KeyError(f"Column '{column_name}' not found in DataFrame.")

    # Get unique values and sort them
    unique_values = sorted(df_copy[column_name].dropna().unique())

    if len(unique_values) < nbr_of_bins:
        raise ValueError(
            f"Not enough unique values ({len(unique_values)}) for {nbr_of_bins} bins."
        )

    # Number of values per bin
    values_per_bin = math.ceil(len(unique_values) / nbr_of_bins)

    # Create the bins (list of lists)
    bins = [
        unique_values[i : i + values_per_bin]
        for i in range(0, len(unique_values), values_per_bin)
    ]

    return df_copy, column_name, bins
