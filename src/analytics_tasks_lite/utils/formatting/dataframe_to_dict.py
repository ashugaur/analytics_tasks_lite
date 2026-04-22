# %% dataframe_to_dict

## Dependencies
import pandas as pd


def dataframe_to_dict(df, key_col, value_col):
    """
    Converts two columns of a pandas DataFrame into a dictionary.

    Args:
      df: The pandas DataFrame.
      key_col: The name of the column to use as keys.
      value_col: The name of the column to use as values.

    Returns:
      A dictionary where keys are from key_col and values are from value_col.
      Returns an empty dictionary if key_col or value_col are not found in the dataframe.
    """
    if key_col not in df.columns or value_col not in df.columns:
        print(f"Error: Column '{key_col}' or '{value_col}' not found in DataFrame.")
        return {}

    return dict(zip(df[key_col], df[value_col]))


if __name__ == "__main__":
    data = {
        "Name": ["Alice", "Bob", "Charlie"],
        "Age": [25, 30, 28],
        "City": ["New York", "London", "Tokyo"],
    }
    df = pd.DataFrame(data)

    # Convert 'Name' and 'Age' columns to a dictionary
    name_age_dict = dataframe_to_dict(df, "Name", "Age")
    print("Name to Age Dictionary:", name_age_dict)

    # Convert 'City' and 'Name' columns to a dictionary
    city_name_dict = dataframe_to_dict(df, "City", "Name")
    print("City to Name Dictionary:", city_name_dict)

    # Example of error handling:
    invalid_dict = dataframe_to_dict(df, "NotAColumn", "Age")
    print("Invalid Dictionary:", invalid_dict)

    # Example with duplicate keys. Last value will be kept.
    duplicate_data = {"ID": [1, 2, 1, 3], "Value": ["A", "B", "C", "D"]}
    duplicate_df = pd.DataFrame(duplicate_data)
    duplicate_dict = dataframe_to_dict(duplicate_df, "ID", "Value")
    print("Duplicate Key Dictionary:", duplicate_dict)
