# %% echarts_js_to_data_conversion

## Dependencies

import pandas as pd
import re
import json
from typing import List, Dict, Any


def hierarchical_to_dataframe(data: List[Dict]) -> pd.DataFrame:
    """
    Convert hierarchical sunburst data structure to a flat pandas DataFrame.
    Captures properties at all levels, not just leaf nodes.

    Args:
        data: List of dictionaries with nested 'children' structure

    Returns:
        pd.DataFrame with columns for each level and associated properties
    """
    records = []

    def traverse(
        node, path: List[str] = [], level: int = 0, parent_colors: List[str] = []
    ):
        """Recursively traverse the tree and collect records"""
        # Handle case where node might not be a dictionary
        if not isinstance(node, dict):
            return

        current_path = path + [node.get("name", "")]

        # Get color for this node
        item_style = node.get("itemStyle", {})
        if isinstance(item_style, dict):
            current_color = item_style.get("color", "")
        else:
            current_color = ""

        # Build color list for this path
        current_colors = (
            parent_colors + [current_color] if current_color else parent_colors
        )

        record = {
            f"level_{i}": current_path[i] if i < len(current_path) else None
            for i in range(10)  # Support up to 10 levels
        }

        # Add color for each level
        for i in range(10):
            if i < len(current_colors):
                record[f"color_level_{i}"] = current_colors[i]
            else:
                record[f"color_level_{i}"] = ""

        record["value"] = node.get("value", None)

        # Add label information if exists
        label = node.get("label", {})
        if isinstance(label, dict) and "color" in label:
            record["label_color"] = label.get("color", "")
        else:
            record["label_color"] = ""

        # Only add leaf nodes (nodes without children) as records
        children = node.get("children", [])
        if not children or not isinstance(children, list):
            records.append(record)

        # Traverse children
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    traverse(child, current_path, level + 1, current_colors)

    # Start traversal from each root node
    for root in data:
        traverse(root)

    df = pd.DataFrame(records)

    # Remove columns that are all None or empty
    df = df.dropna(axis=1, how="all")
    for col in df.columns:
        if df[col].astype(str).str.strip().eq("").all():
            df = df.drop(columns=[col])

    return df


def dataframe_to_hierarchical(df: pd.DataFrame) -> List[Dict]:
    """
    Convert a flat pandas DataFrame back to hierarchical sunburst data structure.
    Restores colors at each level.

    Args:
        df: DataFrame with level_0, level_1, etc. and color_level_0, color_level_1, etc. columns

    Returns:
        List of dictionaries with nested 'children' structure
    """
    # Get all level columns
    level_cols = [
        col
        for col in df.columns
        if col.startswith("level_") and not col.startswith("level_color")
    ]
    level_cols.sort(key=lambda x: int(x.split("_")[1]))

    # Build the tree
    root = {}

    for _, row in df.iterrows():
        current = root

        for i, level_col in enumerate(level_cols):
            name = row[level_col]
            if pd.isna(name) or name == "":
                break

            # Find or create child
            if "children" not in current:
                current["children"] = []

            # Look for existing child with this name
            child = None
            for c in current["children"]:
                if c.get("name") == name:
                    child = c
                    break

            # Create new child if not found
            if child is None:
                child = {"name": name}

                # Add color for this level if it exists
                color_col = f"color_level_{i}"
                if color_col in row and row.get(color_col) and row.get(color_col) != "":
                    child["itemStyle"] = {"color": row[color_col]}

                # Check if this is a leaf node (last level or next level is empty)
                is_leaf = (
                    i == len(level_cols) - 1
                    or pd.isna(row.get(level_cols[i + 1]))
                    or row.get(level_cols[i + 1]) == ""
                )

                # Add properties for leaf nodes
                if is_leaf:
                    if not pd.isna(row.get("value")) and row.get("value") != "":
                        child["value"] = (
                            int(row["value"])
                            if isinstance(row["value"], (int, float))
                            else row["value"]
                        )
                    if row.get("label_color") and row.get("label_color") != "":
                        child["label"] = {"color": row["label_color"]}

                current["children"].append(child)

            current = child

    return root.get("children", [])


def python_to_js_object(obj: Any, indent: int = 2, level: int = 0) -> str:
    """
    Convert Python object back to JavaScript object literal format.
    Returns unquoted keys and proper formatting.
    Converts __VAR__ marked strings back to variable references.
    """
    if obj is None:
        return "null"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, (int, float)):
        return str(obj)
    elif isinstance(obj, str):
        # Check if this is a variable reference
        if obj.startswith("__VAR__"):
            # Remove the __VAR__ prefix and return as unquoted variable
            return obj[7:]  # Remove '__VAR__'
        # Escape quotes and return quoted string
        return '"' + obj.replace("\\", "\\\\").replace('"', '\\"') + '"'
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        items = []
        for item in obj:
            items.append(
                " " * (indent * (level + 1))
                + python_to_js_object(item, indent, level + 1)
            )
        return "[\n" + ",\n".join(items) + "\n" + " " * (indent * level) + "]"
    elif isinstance(obj, dict):
        if not obj:
            return "{}"
        items = []
        for key, value in obj.items():
            val_str = python_to_js_object(value, indent, level + 1)
            items.append(" " * (indent * (level + 1)) + f"{key}: {val_str}")
        return "{\n" + ",\n".join(items) + "\n" + " " * (indent * level) + "}"
    else:
        return str(obj)


def parse_js_object(js_string: str):
    """Parse JavaScript object literal to Python dict."""
    # Remove comments
    js_string = re.sub(r"//.*?$", "", js_string, flags=re.MULTILINE)
    js_string = re.sub(r"/\*.*?\*/", "", js_string, flags=re.DOTALL)

    # Replace variable references BEFORE other processing
    js_string = re.sub(r"colors\[(\d+)\]", r'"__VAR__colors[\1]"', js_string)
    js_string = re.sub(r"\bbgColor\b", '"__VAR__bgColor"', js_string)
    js_string = re.sub(r"\bitemStyle\.(star\d+)", r'"__VAR__itemStyle.\1"', js_string)

    # Add quotes around unquoted keys FIRST
    js_string = re.sub(r"([\{,\n]\s*)(\w+)(\s*:)", r'\1"\2"\3', js_string)

    # Handle single-quoted string values
    def replace_single_quote_strings(match):
        content = match.group(2)
        content = content.replace("\\'", "'").replace("\\", "\\\\").replace('"', '\\"')
        return f'{match.group(1)}"{content}"{match.group(3)}'

    js_string = re.sub(
        r"(:\s*)'((?:[^'\\]|\\.)*)'(\s*[,\}])", replace_single_quote_strings, js_string
    )

    # Remove trailing commas
    js_string = re.sub(r",\s*}", "}", js_string)
    js_string = re.sub(r",\s*]", "]", js_string)

    return json.loads(js_string)


def js_object_to_python(js_obj_string: str):
    """Convert JavaScript object literal string to Python object."""
    js_obj_string = js_obj_string.strip()
    if "=" in js_obj_string:
        js_obj_string = js_obj_string.split("=", 1)[1].strip()
        if js_obj_string.endswith(";"):
            js_obj_string = js_obj_string[:-1].strip()
    return parse_js_object(js_obj_string)


if __file__ == "__main__":
    # Read the file
    with open("./sunburst/sunburst-book.json", "r", encoding="utf-8") as f:
        sample_data = f.read()

    # Parse the data
    data = js_object_to_python(sample_data)
    print(f"✓ Parsed successfully! Loaded {len(data)} root categories")

    # Convert to DataFrame
    df = hierarchical_to_dataframe(data)
    print(f"✓ DataFrame created with shape: {df.shape}")
    print(f"\nColumns: {df.columns.tolist()}")
    print("\nFirst 5 rows:")
    print(df.head())

    # Check that colors are preserved at each level
    print("\n✓ Checking color preservation:")
    print(f"Unique color_level_0 values: {df['color_level_0'].unique()}")

    # Save to CSV for editing
    df.to_csv("./sunburst/sunburst-book.csv", index=False, encoding="utf-8-sig")
    print("\n✓ Saved to ./sunburst/sunburst-book.csv")

    # Test reconstruction
    print("\n✓ Testing reconstruction...")
    # new_data = dataframe_to_hierarchical(df)
    edited_data = pd.read_csv("./sunburst/sunburst-book.csv")
    new_data = dataframe_to_hierarchical(edited_data)
    js_code = python_to_js_object(new_data)

    # Save the JS code
    with open("./sunburst/sunburst-book.txt", "w", encoding="utf-8") as f:
        f.write(js_code)
    print("✓ Saved reconstructed JS to ./sunburst/sunburst-book.txt.")
