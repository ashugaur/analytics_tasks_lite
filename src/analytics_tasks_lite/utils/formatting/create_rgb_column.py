# %% create_rgb_column

## Dependencies
import pandas as pd
from .hex_to_rgb import hex_to_rgb


def create_rgb_column(df, hex_column_name):
    """
    Creates a new column in the given DataFrame containing RGB tuples
    from a column of hexadecimal color codes.

    Args:
      df: The pandas DataFrame.
      hex_column_name: The name of the column containing hexadecimal colors.

    Returns:
      The DataFrame with the new 'rgb_color' column.
    """
    df["RGB color"] = df[hex_column_name].apply(hex_to_rgb)
    return df


if __name__ == "__main__":
    data = {"hex_color": ["#FF0000", "#00FF00", "#0000FF"]}
    df = pd.DataFrame(data)

    df = create_rgb_column(df, "hex_color")
    print(df)
