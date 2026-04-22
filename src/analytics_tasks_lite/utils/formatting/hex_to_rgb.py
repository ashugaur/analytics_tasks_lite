# %% hex_to_rgb


def hex_to_rgb(hex_color):
    """
    Converts a hexadecimal color code to an RGB tuple.

    Args:
      hex_color: The hexadecimal color code (e.g., '#FF0000').

    Returns:
      A tuple containing the RGB values (red, green, blue), each in the range 0-255.
    """
    hex_color = hex_color.lstrip("#")  # Remove the leading '#' if present
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
