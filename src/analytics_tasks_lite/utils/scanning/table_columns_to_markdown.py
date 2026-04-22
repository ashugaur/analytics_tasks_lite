import pandas as pd
import subprocess


def table_columns_to_markdown(
    h1=None,
    h2=None,
    h3=None,
    h4=None,
    h5=None,
    h6=None,
    md_name_str="""---
title: Mindmap
markmap:
  colorFreezeLevel: 4
  maxWidth: 300
  embedAssets: true
  initialExpandLevel: 4
---\n\n""",
    filename="output.md",
):
    """
    Convert table columns to mindmap.
    Copy the datafame and run the function.

    Parameters:
    h1 (str or list): Column name(s) for heading level 1.
    h2 (str or list): Column name(s) for heading level 2.
    h3 (str or list): Column name(s) for heading level 3.
    h4 (str or list): Column name(s) for heading level 4.
    h5 (str or list): Column name(s) for heading level 5.
    h6 (str or list): Column name(s) for heading level 6.
    filename (str): Output markdown filename.

    Returns:
    None
    """

    # Read clipboard
    df = pd.read_clipboard()

    # Initialize markdown content
    markdown_content = md_name_str

    # Define heading levels
    heading_levels = {
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "h4": h4,
        "h5": h5,
        "h6": h6,
    }

    # Iterate over heading levels
    for i, (level, columns) in enumerate(heading_levels.items()):
        if columns:
            # Convert column name to list if it's a string
            if isinstance(columns, str):
                columns = [columns]

            # Get unique values for the current level, ignoring NaN
            unique_values = df[columns[0]].dropna().unique()

            # Iterate over unique values
            for value in unique_values:
                # Get filtered dataframe for the current value
                filtered_df = df[df[columns[0]] == value]

                # Add heading to markdown content
                markdown_content += "#" * (i + 1) + " " + str(value) + "\n"

                # Check if there are more heading levels to process
                next_levels = list(heading_levels.items())[i + 1 :]
                if next_levels:
                    # Iterate over next heading levels
                    for j, (next_level, next_columns) in enumerate(
                        next_levels, start=i + 1
                    ):
                        if next_columns:
                            # Convert column name to list if it's a string
                            if isinstance(next_columns, str):
                                next_columns = [next_columns]

                            # Get unique values for the next level, ignoring NaN
                            next_unique_values = (
                                filtered_df[next_columns[0]].dropna().unique()
                            )

                            # Iterate over unique values
                            for next_value in next_unique_values:
                                # Get filtered dataframe for the current value
                                next_filtered_df = filtered_df[
                                    filtered_df[next_columns[0]] == next_value
                                ]

                                # Add heading to markdown content
                                markdown_content += (
                                    "#" * (j + 1) + " " + str(next_value) + "\n"
                                )

                                # Add values to markdown content (only if there are no more nested levels)
                                if not list(heading_levels.items())[j + 1 :]:
                                    for _, row in next_filtered_df.iterrows():
                                        markdown_content += (
                                            str(row[list(df.columns)[-1]]) + "\n"
                                        )

                            # Add newline after each group
                            markdown_content += "\n"
                else:
                    # If no more heading levels, add the values directly
                    for _, row in filtered_df.iterrows():
                        markdown_content += str(row[list(df.columns)[-1]]) + "\n"

                # Add newline after each group
                markdown_content += "\n"

    # Write markdown content to file
    with open(filename, "w") as f:
        f.write(markdown_content)

    subprocess.Popen(filename, shell=True)  # open files


if __name__ == "__main__":
    ## Example from gant chart
    table_columns_to_markdown(h2="Task", h3="force_color")
