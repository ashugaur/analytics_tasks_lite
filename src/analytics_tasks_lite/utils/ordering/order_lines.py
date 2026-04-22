import pyperclip


def order_lines(sort=1):
    """
    Process the text from clipboard.

    Args:
        sort (int, optional): Sorting order. 1 for ascending, 0 for descending. Defaults to 1.

    Returns:
        str: Processed text.
    """

    # Get text from clipboard
    text = pyperclip.paste()

    # Split text into lines
    lines = text.split("\n")

    # Remove duplicates
    lines = list(set(lines))

    # Sort lines based on length
    if sort == 1:
        lines.sort(key=len)
    elif sort == 0:
        lines.sort(key=len, reverse=True)
    else:
        raise ValueError("Invalid sort order. Use 1 for ascending or 0 for descending.")

    # Join lines back into a string
    processed_text = "\n".join(lines)

    # Copy processed text back to clipboard
    pyperclip.copy(processed_text)

    # Print processed text
    # print(processed_text)
    print("☑️  Sorted lines copied to clipboard.")

    return processed_text
