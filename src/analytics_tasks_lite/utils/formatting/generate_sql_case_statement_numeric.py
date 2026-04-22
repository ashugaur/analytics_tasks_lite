# %% generate_sql_case_statement_numeric

## Dependencies
import pandas as pd
from .create_bins_numeric import create_bins_numeric


def generate_sql_case_statement_numeric(df, column_name):
    unique_bins = df["bins_rounded"].dropna().unique()
    case_statement = "case\n"

    for bin_range in unique_bins:
        lower, upper = bin_range.left, bin_range.right
        # Construct the case statement
        case_statement += f"    when {column_name} >= {lower} and {column_name} < {upper} then '{bin_range}'\n"

    case_statement += f"    else '00000'\nend as {column_name}_bins"

    return case_statement


if __name__ == "__main__":
    df = pd.DataFrame({"bining_column": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]})

    result, column_name = create_bins_numeric(
        df, column_name="bining_column", nbr_of_bins=5, range_min=0, range_max=15
    )
    case_statement_sql = generate_sql_case_statement_numeric(result, column_name)

    print(case_statement_sql)
    print("\nDataFrame with bins:")
    print(result)
