# %% Formatting

## Dependencies
import pyperclip
import pandas as pd


def limit_text_df(prefix="", suffix="", triple_quotes=False, df=None):
    """
    Formats a DataFrame with even spacing for each column, adds prefix and suffix to each row
    if provided, or encloses the entire output within triple quotes if specified.
    The DataFrame can be provided directly or read from clipboard.

    Args:
        prefix (str, optional): Prefix to add to each row. Defaults to ''.
        suffix (str, optional): Suffix to add to each row. Defaults to ''.
        triple_quotes (bool, optional): If True, encloses the output in triple quotes
                                        and ignores prefix/suffix. Defaults to False.
        df (pandas.DataFrame, optional): DataFrame to format. If None, reads from clipboard.
                                         Defaults to None.
    """
    # Get the DataFrame from parameter or clipboard
    if df is None:
        try:
            df = pd.read_clipboard()
        except Exception:
            print("No valid DataFrame found in clipboard.")
            return

    # Convert all columns to string type
    df = df.astype(str)

    # Create a new DataFrame to store formatted data
    formatted_df = pd.DataFrame()

    # Format each column with even spacing
    for col in df.columns:
        # Determine max length needed (either column name or longest value)
        col_len = max(len(col), df[col].str.len().max())

        # Create column name with padding
        padded_col = col + " " * (col_len - len(col))

        # Add padded values to the formatted DataFrame
        for i in range(len(df)):
            value = df.loc[i, col]
            formatted_df.loc[i, padded_col] = value + " " * (col_len - len(value))

    # Convert DataFrame to string with even spacing
    formatted_text = formatted_df.to_string(index=False)

    if triple_quotes:
        # Enclose in triple quotes, ignoring prefix and suffix
        result_text = f'"""\n{formatted_text}\n"""'
    else:
        # Apply prefix and suffix to each line
        lines = formatted_text.split("\n")
        result_text = "\n".join([f"{prefix}{line}{suffix}" for line in lines])

    # Copy the result text back to clipboard
    pyperclip.copy(result_text)

    # Print the result text
    print(result_text)
    return result_text
