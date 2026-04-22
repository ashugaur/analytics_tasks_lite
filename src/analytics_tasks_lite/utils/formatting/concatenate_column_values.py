# %% Formatting

## Dependencies
import pyperclip


def concatenate_column_values(delimiter=",", sort=False, case_transform=None):
    """
    Concatenate column values from clipboard with specified options.

    Parameters:
    - delimiter (str, optional): Delimiter between quoted values. Defaults to ','.
    - sort (bool, optional): Whether to sort the values. Defaults to False.
    - case_transform (str, optional): Transform case of values.
      Options: 'upper', 'lower', or None. Defaults to None.

    Returns and copies concatenated string of quoted values to clipboard
    """
    # Get data from clipboard
    try:
        clipboard_data = pyperclip.paste()
        print(f"REPORT: Length of copied string {len(clipboard_data)}.")
    except Exception:
        print(
            "Warning: Unable to read from clipboard. Please copy a column from Excel."
        )
        return

    # Split the clipboard data into lines and remove the header
    lines = clipboard_data.strip().split("\n")
    values = lines[1:]  # Skip the first line (header)

    # Optional sorting
    if sort:
        values.sort()

    # Optional case transformation
    if case_transform == "upper":
        values = [val.upper() for val in values]
    elif case_transform == "lower":
        values = [val.lower() for val in values]

    # Enclose each value in quotes
    quoted_values = [f"'{val.strip()}'" for val in values]

    # Concatenate with specified delimiter
    result = delimiter.join(quoted_values)

    # Copy result to clipboard
    pyperclip.copy(result)

    return result


if __name__ == "__main__":
    concatenate_column_values()  # Uses defaults
    concatenate_column_values(sort=True, case_transform="upper")
