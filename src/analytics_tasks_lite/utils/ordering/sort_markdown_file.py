import re
from typing import List, Tuple
from pathlib import Path


class MarkdownSorter:
    def __init__(self):
        self.code_block_pattern = re.compile(r"^```|^~~~")
        self.heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

    def is_in_code_block(self, lines: List[str], line_index: int) -> bool:
        """Check if a line is inside a code block by counting block markers before it"""
        code_block_count = 0
        for i in range(line_index):
            if self.code_block_pattern.match(lines[i].strip()):
                code_block_count += 1
        return code_block_count % 2 == 1

    def find_heading_indices(self, lines: List[str]) -> List[Tuple[int, int, str]]:
        """Find all heading lines that are NOT in code blocks"""
        headings = []
        for i, line in enumerate(lines):
            if not self.is_in_code_block(lines, i):
                match = self.heading_pattern.match(line.strip())
                if match:
                    level = len(match.group(1))
                    title = match.group(2).strip()
                    headings.append((i, level, title))
        return headings

    def extract_sort_key(self, title: str) -> str:
        """Extract clean text for sorting, removing markdown links and special characters"""
        # Remove markdown links [text](url) -> text
        title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", title)
        # Remove markdown links [text]{target="_blank"} -> text
        title = re.sub(r"\[([^\]]+)\]\{[^}]+\}", r"\1", title)
        # Remove other markdown formatting
        title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)
        title = re.sub(r"\*([^*]+)\*", r"\1", title)
        title = re.sub(r"`([^`]+)`", r"\1", title)
        # Remove leading/trailing special characters for sorting
        title = re.sub(r"^[^\w\s]+", "", title)
        title = re.sub(r"[^\w\s]+$", "", title)
        return title.strip().lower()

    def extract_sections(self, lines: List[str]) -> List[dict]:
        """Extract sections with their complete content"""
        headings = self.find_heading_indices(lines)
        sections = []

        # Handle content before first heading
        if headings and headings[0][0] > 0:
            pre_content = lines[: headings[0][0]]
            if any(line.strip() for line in pre_content):  # Only if non-empty
                sections.append(
                    {
                        "level": 0,
                        "title": "",
                        "content": pre_content,
                        "line_start": 0,
                        "line_end": headings[0][0] - 1,
                    }
                )

        # Process each heading and its content
        for i, (line_idx, level, title) in enumerate(headings):
            # Determine content end
            if i + 1 < len(headings):
                content_end = headings[i + 1][0]
            else:
                content_end = len(lines)

            # Extract content (including the heading line)
            section_content = lines[line_idx:content_end]

            sections.append(
                {
                    "level": level,
                    "title": title,
                    "content": section_content,
                    "line_start": line_idx,
                    "line_end": content_end - 1,
                }
            )

        return sections

    def build_hierarchy(self, sections: List[dict]) -> List[dict]:
        """Build hierarchical structure from flat sections"""
        root_sections = []
        section_stack = []

        for section in sections:
            level = section["level"]

            # Handle pre-content (level 0)
            if level == 0:
                root_sections.append(section)
                continue

            # Remove deeper levels from stack
            while section_stack and section_stack[-1]["level"] >= level:
                section_stack.pop()

            # Add subsections list if not exists
            if "subsections" not in section:
                section["subsections"] = []

            # Add to parent or root
            if section_stack:
                parent = section_stack[-1]
                if "subsections" not in parent:
                    parent["subsections"] = []
                parent["subsections"].append(section)
            else:
                root_sections.append(section)

            section_stack.append(section)

        return root_sections

    def sort_sections_recursive(self, sections: List[dict]) -> List[dict]:
        """Sort sections recursively, keeping H1 at top"""
        # Separate by level
        h1_sections = [s for s in sections if s.get("level") == 1]
        other_sections = [s for s in sections if s.get("level", 0) != 1]

        # Sort non-H1 sections alphabetically by cleaned title
        other_sections.sort(key=lambda x: self.extract_sort_key(x.get("title", "")))

        # Recursively sort subsections
        for section in sections:
            if "subsections" in section and section["subsections"]:
                section["subsections"] = self.sort_sections_recursive(
                    section["subsections"]
                )

        return h1_sections + other_sections

    def sections_to_lines(self, sections: List[dict]) -> List[str]:
        """Convert sections back to lines"""
        result_lines = []

        for section in sections:
            # Add the section's content
            result_lines.extend(section["content"])

            # Add subsections
            if "subsections" in section and section["subsections"]:
                subsection_lines = self.sections_to_lines(section["subsections"])
                result_lines.extend(subsection_lines)

        return result_lines

    def sort_markdown_file(self, input_file: str, output_file: str = None) -> None:
        """
        Sort markdown headings in a file while preserving all content

        Args:
            input_file (str): Path to input markdown file
            output_file (str): Path to output file. If None, overwrites input file
        """
        input_path = Path(input_file)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        print(f"Reading file: {input_file}")

        # Read the file
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_size = len(content)
        print(f"Original file size: {original_size} characters")

        # Split into lines
        lines = content.split("\n")
        print(f"Total lines: {len(lines)}")

        # Extract sections
        sections = self.extract_sections(lines)
        print(f"Found {len(sections)} sections")

        # Build hierarchy
        hierarchical_sections = self.build_hierarchy(sections)
        print(f"Built hierarchy with {len(hierarchical_sections)} root sections")

        # Sort sections
        sorted_sections = self.sort_sections_recursive(hierarchical_sections)

        # Convert back to lines
        sorted_lines = self.sections_to_lines(sorted_sections)

        # Join lines back to content
        sorted_content = "\n".join(sorted_lines)

        # Ensure file ends with newline
        if not sorted_content.endswith("\n"):
            sorted_content += "\n"

        new_size = len(sorted_content)
        print(f"New file size: {new_size} characters")

        if new_size < original_size * 0.9:  # If more than 10% content lost
            print("WARNING: Significant content loss detected!")
            print(f"Original: {original_size} chars, New: {new_size} chars")
            print("Aborting to prevent data loss. Please check the input file.")
            return

        # Write to output file
        output_path = Path(output_file) if output_file else input_path

        # Create backup if overwriting
        if output_path == input_path:
            backup_path = input_path.with_suffix(input_path.suffix + ".backup")
            print(f"Creating backup: {backup_path}")
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(content)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(sorted_content)

        print(f"Sorted markdown saved to: {output_path}")


def sort_markdown_file(input_file: str, output_file: str = None) -> None:
    """
    Convenience function to sort markdown file

    Args:
        input_file (str): Path to input markdown file
        output_file (str): Path to output file. If None, overwrites input file
    """
    sorter = MarkdownSorter()
    sorter.sort_markdown_file(input_file, output_file)
