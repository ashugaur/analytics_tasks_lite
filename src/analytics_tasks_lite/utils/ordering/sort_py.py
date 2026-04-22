import re
from typing import List, Tuple, Optional, Union
from pathlib import Path


def sort_py(
    code: Union[str, Path],
    output_file: Optional[Union[str, Path]] = None,
    ascending: bool = True,
    exception: Optional[List[str]] = None,
) -> str:
    """
    Sort Python code blocks hierarchically while respecting exceptions.

    Args:
        code (Union[str, Path]): The Python code string to sort OR path to .py file
        output_file (Union[str, Path], optional): Output file path. If None and input is a file,
                                                overwrites the input file. If specified, saves to new file.
        ascending (bool): True for ascending order, False for descending
        exception (List[str], optional): List of block headers to exclude from sorting.
                                       Format: ["# %% Block Name", "## Sub-block Name"]

    Returns:
        str: Sorted code string (also writes to file if input was a file)
    """
    if exception is None:
        exception = []

    # Handle file input
    input_file_path = None
    if isinstance(code, (str, Path)) and (
        Path(code).exists() if isinstance(code, str) else code.exists()
    ):
        input_file_path = Path(code)
        try:
            with open(input_file_path, "r", encoding="utf-8") as f:
                code_content = f.read()
        except Exception as e:
            raise ValueError(f"Error reading file {input_file_path}: {e}")
    else:
        # Assume it's a code string
        code_content = str(code)

    # Parse exception pairs
    exception_pairs = []
    for i in range(0, len(exception), 2):
        if i + 1 < len(exception):
            main_block = exception[i].strip()
            sub_block = exception[i + 1].strip()
            exception_pairs.append((main_block, sub_block))

    # Split code into lines
    lines = code_content.split("\n")

    # Find all main blocks (# %% or #%%)
    main_blocks = []
    current_block = None
    current_content = []

    for i, line in enumerate(lines):
        # Check if line is a main block header
        if re.match(r"^#\s*%%\s*", line.strip()):
            # Save previous block if exists
            if current_block is not None:
                main_blocks.append(
                    {
                        "header": current_block,
                        "content": current_content,
                        "original_index": len(main_blocks),
                    }
                )

            # Start new block
            current_block = line.strip()
            current_content = []
        else:
            # Add line to current block content
            if current_block is not None:
                current_content.append(line)
            else:
                # Lines before first block
                if not main_blocks:
                    main_blocks.append(
                        {"header": "", "content": [line], "original_index": 0}
                    )
                else:
                    main_blocks[0]["content"].insert(0, line)

    # Add the last block
    if current_block is not None:
        main_blocks.append(
            {
                "header": current_block,
                "content": current_content,
                "original_index": len(main_blocks),
            }
        )

    # Process each main block to sort its sub-blocks
    for block in main_blocks:
        if block["header"]:  # Skip empty header (pre-block content)
            block["content"] = sort_sub_blocks(
                block["content"], block["header"], exception_pairs, ascending
            )

    # Separate exception blocks from sortable blocks
    exception_blocks = []
    sortable_blocks = []

    for block in main_blocks:
        if block["header"]:
            is_exception = any(
                block["header"] == exc_pair[0] for exc_pair in exception_pairs
            )
            if is_exception:
                exception_blocks.append(block)
            else:
                sortable_blocks.append(block)
        else:
            # Pre-block content stays at the beginning
            exception_blocks.append(block)

    # Sort the sortable blocks
    if sortable_blocks:
        sortable_blocks.sort(key=lambda x: x["header"].lower(), reverse=not ascending)

    # Combine blocks: exceptions first (in original order), then sorted blocks
    final_blocks = []

    # Add exception blocks in their original positions relative to each other
    exception_blocks.sort(key=lambda x: x["original_index"])
    final_blocks.extend(exception_blocks)
    final_blocks.extend(sortable_blocks)

    # Reconstruct the code with proper spacing
    result_lines = []

    for i, block in enumerate(final_blocks):
        # Add spacing before main blocks (except the first one)
        if block["header"] and i > 0:
            # Add 3 blank lines before each main block
            result_lines.extend(["", "", ""])

        # Add the main block header
        if block["header"]:
            result_lines.append(block["header"])

        # Process block content with proper spacing for sub-blocks
        formatted_content = format_block_content(block["content"])
        result_lines.extend(formatted_content)

    sorted_code = "\n".join(result_lines)

    # Handle file output
    if input_file_path is not None:
        # Determine output file path
        if output_file is None:
            # Overwrite the input file
            output_path = input_file_path
        else:
            # Save to specified output file
            output_path = Path(output_file)

        # Write sorted code to file
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(sorted_code)
            print(f"Sorted code written to: {output_path}")
        except Exception as e:
            print(f"Error writing to file {output_path}: {e}")

    return sorted_code


def is_inside_code_block(lines: List[str], target_index: int) -> bool:
    """
    Check if a line at target_index is inside a Python code block (function, class, etc.)
    by analyzing indentation levels and Python syntax.
    """
    if target_index >= len(lines):
        return False

    # Get the indentation of the target line
    target_line = lines[target_index]
    target_stripped = target_line.strip()

    # If the line is not indented or only has comment indentation, it's likely a true header
    if not target_line.startswith("    ") and not target_line.startswith("\t"):
        # Check if it's only indented for comment formatting (e.g., "    ## comment")
        if (
            target_stripped.startswith("##")
            and len(target_line) - len(target_line.lstrip()) <= 4
        ):
            return False

    # Look backwards to find the context
    for i in range(target_index - 1, -1, -1):
        line = lines[i].strip()

        # Skip empty lines and pure comments
        if not line or line.startswith("#"):
            continue

        # Check for function/class/method definitions
        if (
            line.startswith("def ")
            or line.startswith("class ")
            or line.startswith("async def ")
            or ":" in line
        ):
            # If we find a function/class definition, check if our target is indented relative to it
            definition_indent = len(lines[i]) - len(lines[i].lstrip())
            target_indent = len(lines[target_index]) - len(lines[target_index].lstrip())

            # If target is indented more than the definition, it's inside the code block
            if target_indent > definition_indent:
                return True

        # If we hit a line that's not indented and not a comment, we're likely at module level
        if len(lines[i]) - len(lines[i].lstrip()) == 0 and line:
            break

    # Additional check: look for patterns that suggest we're inside a function
    # Check if there are indented lines before this that suggest we're in a code block
    indent_levels = []
    for i in range(max(0, target_index - 10), target_index):
        line = lines[i]
        if line.strip() and not line.strip().startswith("#"):
            indent_level = len(line) - len(line.lstrip())
            indent_levels.append(indent_level)

    # If we have consistent indentation before this line, we're likely inside a code block
    if indent_levels:
        target_indent = len(lines[target_index]) - len(lines[target_index].lstrip())
        # If most recent non-comment lines are indented and our target is also indented
        recent_indented = [level for level in indent_levels[-5:] if level > 0]
        if len(recent_indented) >= 2 and target_indent > 0:
            return True

    return False


def format_block_content(content: List[str]) -> List[str]:
    """
    Format block content with proper spacing before sub-blocks (##).
    """
    if not content:
        return content

    formatted_content = []

    for i, line in enumerate(content):
        # Check if this line is a sub-block header (and not inside a code block)
        if re.match(r"^##\s*", line.strip()) and not is_inside_code_block(content, i):
            # Add 2 blank lines before sub-block (except if it's the first line)
            if i > 0 and formatted_content:
                # Check if we already have blank lines
                blank_lines_count = 0
                for j in range(len(formatted_content) - 1, -1, -1):
                    if formatted_content[j].strip() == "":
                        blank_lines_count += 1
                    else:
                        break

                # Add blank lines to make total of 2
                lines_to_add = max(0, 2 - blank_lines_count)
                formatted_content.extend([""] * lines_to_add)

        formatted_content.append(line)

    return formatted_content


def sort_sub_blocks(
    content: List[str],
    main_header: str,
    exception_pairs: List[Tuple[str, str]],
    ascending: bool,
) -> List[str]:
    """
    Sort sub-blocks (##) within a main block's content, ignoring ## comments inside code blocks.
    """
    if not content:
        return content

    # Find sub-blocks (only those not inside code blocks)
    sub_blocks = []
    current_sub_block = None
    current_sub_content = []
    pre_sub_content = []

    for i, line in enumerate(content):
        # Check if line is a sub-block header (and not inside a code block)
        if re.match(r"^##\s*", line.strip()) and not is_inside_code_block(content, i):
            # Save previous sub-block if exists
            if current_sub_block is not None:
                sub_blocks.append(
                    {
                        "header": current_sub_block,
                        "content": current_sub_content,
                        "original_index": len(sub_blocks),
                    }
                )
            elif not sub_blocks and current_sub_content:
                # Content before first sub-block
                pre_sub_content.extend(current_sub_content)

            # Start new sub-block
            current_sub_block = line.strip()
            current_sub_content = []
        else:
            # Add line to current sub-block content
            if current_sub_block is not None:
                current_sub_content.append(line)
            else:
                # Lines before first sub-block
                pre_sub_content.append(line)

    # Add the last sub-block
    if current_sub_block is not None:
        sub_blocks.append(
            {
                "header": current_sub_block,
                "content": current_sub_content,
                "original_index": len(sub_blocks),
            }
        )

    # If no sub-blocks found, return original content
    if not sub_blocks:
        return content

    # Separate exception sub-blocks from sortable ones
    exception_sub_blocks = []
    sortable_sub_blocks = []

    for sub_block in sub_blocks:
        is_exception = any(
            main_header == exc_pair[0] and sub_block["header"] == exc_pair[1]
            for exc_pair in exception_pairs
        )
        if is_exception:
            exception_sub_blocks.append(sub_block)
        else:
            sortable_sub_blocks.append(sub_block)

    # Sort the sortable sub-blocks
    if sortable_sub_blocks:
        sortable_sub_blocks.sort(
            key=lambda x: x["header"].lower(), reverse=not ascending
        )

    # Combine sub-blocks: exceptions first (in original order), then sorted ones
    final_sub_blocks = []
    exception_sub_blocks.sort(key=lambda x: x["original_index"])
    final_sub_blocks.extend(exception_sub_blocks)
    final_sub_blocks.extend(sortable_sub_blocks)

    # Reconstruct content
    result_content = pre_sub_content.copy()

    for sub_block in final_sub_blocks:
        result_content.append(sub_block["header"])
        result_content.extend(sub_block["content"])

    return result_content
