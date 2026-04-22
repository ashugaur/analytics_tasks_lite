import math

def round_smart(value, buffer=0.0):
    """
    Intelligently round based on value magnitude for BOTH positive and negative values,
    with optional buffer for extra range.

    Parameters:
    - value: The value to round
    - buffer: Percentage buffer to add (e.g., 0.1 for 10%, 0.15 for 15%)
    - Applied BEFORE rounding to ensure extra space

    - Positive values: round UP (ceiling) for upper buffer
    - Negative values: round DOWN (floor) for lower buffer

    Magnitude-based rounding:
    - < 1K: round to nearest 100
    - 1K-10K: round to nearest 1K
    - 10K-100K: round to nearest 10K
    - 100K-1M: round to nearest 50K
    - >= 1M: round to nearest 100K
    """

    # Handle zero
    if value == 0:
        return 0

    # Apply buffer FIRST (before rounding)
    if value > 0:
        # For positive values, add buffer upward
        value_with_buffer = value * (1 + buffer)
    else:
        # For negative values, add buffer downward (more negative)
        value_with_buffer = value * (1 + buffer)

    # Get absolute value for magnitude comparison
    abs_value = abs(value_with_buffer)

    # Determine rounding unit based on magnitude
    if abs_value < 1000:
        unit = 100
    elif abs_value < 10000:
        unit = 1000
    elif abs_value < 100000:
        unit = 10000
    elif abs_value < 1000000:
        unit = 50000
    else:
        unit = 100000

    # Round based on sign
    if value_with_buffer > 0:
        # Positive: round UP (ceiling)
        return math.ceil(value_with_buffer / unit) * unit
    else:
        # Negative: round DOWN (floor)
        return math.floor(value_with_buffer / unit) * unit