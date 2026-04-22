# %% Formatting


def round_columns(df, columns, digits=2):
    """
    Rounds specified columns of a Pandas DataFrame to a given number of decimal places.

    Args:
        df: The Pandas DataFrame.
        columns: A list of column names to round.
        digits: The number of decimal places to round to.  Defaults to 2.

    Returns:
        A new Pandas DataFrame with the specified columns rounded, or the original
        DataFrame if no columns are provided or if the specified columns are not found.
        Prints a warning if some columns are not found.
    """

    if not columns:  # Handle empty column list
        return df

    df_copy = (
        df.copy()
    )  # Important: Create a copy to avoid modifying the original DataFrame

    not_found_cols = []
    for col in columns:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].round(digits)
        else:
            not_found_cols.append(col)

    if not_found_cols:
        print(f"Warning: Columns not found: {', '.join(not_found_cols)}")

    return df_copy
