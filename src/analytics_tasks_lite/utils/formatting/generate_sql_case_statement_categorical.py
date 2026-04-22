# %% generate_sql_case_statement_categorical

## Dependencies
import pandas as pd
from .create_bins_categorical import create_bins_categorical

def generate_sql_case_statement_categorical(column_name, bins, null_label="00000"):
    """
    Build a SQL CASE statement that maps categorical values to bin labels.

    Parameters
    ----------
    column_name : str
        Name of the column in the SQL table.
    bins : list[list]
        Bins returned by ``create_bins_categorical``.
    null_label : str, optional
        Value returned for NULL entries.

    Returns
    -------
    str
        The CASE statement as a string.
    """
    case_statement_sql = "CASE\n"

    # Construct WHEN/THEN clauses
    for i, bin_values in enumerate(bins):
        # Quote strings, leave numbers as‑is
        bin_vals_sql = ", ".join(
            f"'{v}'" if isinstance(v, str) else str(v) for v in bin_values
        )
        case_statement_sql += (
            f"    WHEN `{column_name}` IN ({bin_vals_sql}) THEN 'Bin_{i + 1}'\n"
        )

    # Optional handling of NULLs
    if null_label is not None:
        case_statement_sql += f"    WHEN `{column_name}` IS NULL THEN '{null_label}'\n"

    case_statement_sql += f"    ELSE '{null_label}'\nEND AS `{column_name}_bins`"

    return case_statement_sql


if __name__ == "__main__":
    df = pd.DataFrame({"bining_column": ["zebra", "bat", "cat", "rat", "mouse", "dog"]})

    df, column_name, bins = create_bins_categorical(df, nbr_of_bins=3)
    case_statement_sql = generate_sql_case_statement_categorical(column_name, bins)

    print(case_statement_sql)
