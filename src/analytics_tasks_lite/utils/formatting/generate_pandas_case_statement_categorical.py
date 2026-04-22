# %% generate_pandas_case_statement_categorical

## Dependencies
import pandas as pd
from .create_bins_categorical import create_bins_categorical

def generate_pandas_case_statement_categorical(df, column_name, bins):
    # Create a dictionary to map each unique value to its corresponding bin label
    bin_dict = {value: f"Bin_{i + 1}" for i, bin in enumerate(bins) for value in bin}

    # Replace the values in the column with their corresponding bin labels
    df[f"{column_name}_bins"] = df[column_name].map(bin_dict).fillna("00000")

    return df


if __name__ == "__main__":
    df = pd.DataFrame({"bining_column": ["zebra", "bat", "cat", "rat", "mouse", "dog"]})

    df, column_name, bins = create_bins_categorical(df, nbr_of_bins=3)
    case_statement_pandas = generate_pandas_case_statement_categorical(
        df, column_name, bins
    )

    print(case_statement_pandas)
