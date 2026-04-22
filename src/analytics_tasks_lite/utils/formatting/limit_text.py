# %% Formatting

## Dependencies
import pyperclip
import textwrap


def limit_text(max_length=50, border=None, prefix="", suffix=""):
    """
    Copies text from clipboard, splits it into fixed-length lines,
    adds prefix and suffix to each line if provided, pads each line
    to ensure it reaches max_length, copies the result back to clipboard,
    and prints it.

    Args:
        max_length (int, optional): Maximum length of each line. Defaults to 50.
        prefix (str, optional): Prefix to add to each line. Defaults to ''.
        suffix (str, optional): Suffix to add to each line. Defaults to ''.
    """

    # Get the text from clipboard
    text = pyperclip.paste()

    # Replace all occurrences of \r\n with \n
    text = text.replace("\r\n", "\n")

    # Split the text into paragraphs
    paragraphs = text.split("\n\n")

    # Initialize the result text
    result_text = ""

    # Calculate available width after adding prefix and suffix
    available_width = max_length - len(prefix) - len(suffix)

    # Process each paragraph
    for i, paragraph in enumerate(paragraphs):
        # Remove leading and trailing whitespace from the paragraph
        paragraph = paragraph.strip()

        # If the paragraph is not empty, wrap it into fixed-length lines
        if paragraph:
            wrapped_lines = textwrap.wrap(paragraph, width=available_width)

            # Add prefix, suffix, and pad each line to the exact max_length
            formatted_lines = [
                f"{prefix}{line.ljust(available_width)}{suffix}"
                for line in wrapped_lines
            ]

            # Join the formatted lines back into a paragraph
            formatted_paragraph = "\n".join(formatted_lines)

            # Add the formatted paragraph to the result text
            result_text += formatted_paragraph

            # Add an extra newline character between paragraphs
            if i < len(paragraphs) - 1:
                result_text += "\n\n"

    # Enclose with proper border
    if border:
        border = "#" + "-" * (max_length - 1)
        result_text = f"{border}\n{result_text}\n{border}"

        # Ensure UTF-8 encoding
        result_text = result_text.encode("utf-8").decode("utf-8")

        # Copy the result text back to clipboard
        pyperclip.copy(result_text)

        # Print the result text
        # print(result_text)
        print(f"☑️  Text limited to {max_length} characters copied to clipboard.")
    else:
        # Ensure UTF-8 encoding
        result_text = result_text.encode("utf-8").decode("utf-8")

        # Copy the result text back to clipboard
        pyperclip.copy(result_text)

        # Print the result text
        # print(result_text)
        print(f"☑️  Text limited to {max_length} characters copied to clipboard.")


if __name__ == "__main__":
    limit_text(max_length=50, prefix=">> ", suffix=" <<")
