# %% dataframe_to_dict_list

## Dependencies
import pandas as pd


def dataframe_to_dict_list(df, key_col, value_col):
    """
    Converts two columns of a pandas DataFrame into a dictionary, storing values in lists.

    Args:
        df: The pandas DataFrame.
        key_col: The name of the column to use as keys.
        value_col: The name of the column to use as values.

    Returns:
        A dictionary where keys are from key_col and values are lists of values from value_col.
        Returns an empty dictionary if key_col or value_col are not found in the dataframe.
    """
    if key_col not in df.columns or value_col not in df.columns:
        print(f"Error: Column '{key_col}' or '{value_col}' not found in DataFrame.")
        return {}

    result_dict = {}
    for key, value in zip(df[key_col], df[value_col]):
        if key in result_dict:
            result_dict[key].append(value)
        else:
            result_dict[key] = [value]
    return result_dict


if __name__ == "__main__":
    data = {
        "parent": [
            "interactive",
            "interactive",
            "interactive",
            "interactive",
            "interactive",
            "interactive",
            "interactive",
        ],
        "parent_1": [
            "change",
            "compare",
            "correlation",
            "flow",
            "gantt",
            "maps",
            "test",
        ],
    }
    df = pd.DataFrame(data)

    result = dataframe_to_dict_list(df, "parent", "parent_1")
    print(result)

    # Example with more than one key
    data2 = {
        "parent": [
            "interactive",
            "interactive",
            "interactive",
            "static",
            "static",
            "static",
        ],
        "parent_1": ["change", "compare", "correlation", "flow", "gantt", "maps"],
    }
    df2 = pd.DataFrame(data2)

    result2 = dataframe_to_dict_list(df2, "parent", "parent_1")
    print(result2)

    # Example of error handling:
    invalid_dict = dataframe_to_dict_list(df, "NotAColumn", "parent_1")
    print("Invalid Dictionary:", invalid_dict)
