# %% convert_markdown_to_html

## Dependencies
from pathlib import Path
import re
import base64
from datetime import datetime


def convert_markdown_to_html(
    markdown_file,
    output_file="convert_markdown_to_html.html",
    page_title="Documentation Report",
    page_subtitle=None,
    page_description=None,
    footer_content=None,
    sidebar_width="280px",
    default_theme="light",
    light_mode_colors=None,
    dark_mode_colors=None,
    navigation_title="📚 Navigation",
    include_code_blocks=True,
    code_blocks_collapsed=False,
    style_output_blocks=True,
):
    """
    Convert a Python-generated markdown file to a standalone HTML report.
    Handles specific patterns: ## headers, ### subheaders, code blocks,
    tab-indented reference text, and images.

    Args:
        markdown_file (str): Path to the markdown file
        output_file (str): Name of the output HTML file
        page_title (str): Main title for the report
        page_subtitle (str): Optional subtitle
        page_description (str): Optional description text for header
        footer_content (str): Optional footer content (HTML allowed)
        sidebar_width (str): Width of the sidebar (default: "280px")
        default_theme (str): Default theme - "light" or "dark"
        light_mode_colors (dict): Custom light mode colors
        dark_mode_colors (dict): Custom dark mode colors
        navigation_title (str): Title for the navigation sidebar
        include_code_blocks (bool): Whether to include code blocks in output
        code_blocks_collapsed (bool): Whether code blocks start collapsed
        style_output_blocks (bool): Whether to style output blocks with border/background (default: True)

    Returns:
        str: Path to the generated HTML file
    """

    # Set default colors
    if light_mode_colors is None:
        light_mode_colors = {
            "bg": "#ffffff",
            "text": "#333333",
            "sidebar_bg": "#f8f9fa",
            "accent": "#007bff",
            "border": "#dee2e6",
            "hover": "#f1f3f5",
            "code_bg": "#f5f5f5",
            "reference_bg": "#fffbeb",
            "reference_border": "#fbbf24",
        }

    if dark_mode_colors is None:
        dark_mode_colors = {
            "bg": "#1e1e1e",
            "text": "#e0e0e0",
            "sidebar_bg": "#2d2d2d",
            "accent": "#4a9eff",
            "border": "#444444",
            "hover": "#383838",
            "code_bg": "#2a2a2a",
            "reference_bg": "#2d2516",
            "reference_border": "#d97706",
        }

    def image_to_base64(image_path):
        """Convert image to base64 data URI"""
        try:
            with open(image_path, "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode("utf-8")
                ext = image_path.suffix.lower()
                mime_type = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".svg": "image/svg+xml",
                }.get(ext, "image/png")
                return f"data:{mime_type};base64,{encoded}"
        except Exception as e:
            print(f"Warning: Could not encode image {image_path}: {e}")
            return ""

    def parse_markdown(md_content, base_path):
        """
        Parse markdown content with specific patterns:
        - ## for main sections
        - ### for subsections
        - ``` for code blocks
        - 4-space/tab indented text for reference blocks
        - ![alt](path) for images
        """
        sections = []
        current_section = None
        current_subsection = None

        lines = md_content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Main section header (##)
            if line.startswith("## "):
                # Save previous section
                if current_section:
                    sections.append(current_section)

                title = line[3:].strip()
                current_section = {
                    "title": title,
                    "id": title.lower()
                    .replace(" ", "-")
                    .replace(":", "")
                    .replace("(", "")
                    .replace(")", "")
                    .replace("/", "-")
                    .replace(".", ""),
                    "subsections": [],
                    "content": [],
                }
                current_subsection = None
                i += 1
                continue

            # Subsection header (###)
            elif line.startswith("### "):
                if current_section:
                    title = line[4:].strip()
                    current_subsection = {"title": title, "content": []}
                    current_section["subsections"].append(current_subsection)
                i += 1
                continue

            # Code block start
            elif line.startswith("```"):
                if current_section and include_code_blocks:
                    language = line[3:].strip() or "python"
                    code_lines = []
                    i += 1

                    # Collect code lines
                    while i < len(lines) and not lines[i].startswith("```"):
                        code_lines.append(lines[i])
                        i += 1

                    code_content = "\n".join(code_lines)

                    # Add to current subsection or section
                    target = (
                        current_subsection if current_subsection else current_section
                    )
                    if "content" not in target:
                        target["content"] = []

                    target["content"].append(
                        {"type": "code", "language": language, "content": code_content}
                    )

                    i += 1  # Skip closing ```
                    continue
                elif current_section:
                    # Skip code blocks if include_code_blocks is False
                    i += 1
                    while i < len(lines) and not lines[i].startswith("```"):
                        i += 1
                    i += 1  # Skip closing ```
                    continue

            # Reference block (tab or 4-space indented)
            elif line.startswith("    ") or line.startswith("\t"):
                if current_section:
                    ref_lines = []

                    # Collect all consecutive indented lines
                    while i < len(lines) and (
                        lines[i].startswith("    ") or lines[i].startswith("\t")
                    ):
                        # Remove indentation
                        clean_line = lines[i].lstrip(" \t")
                        ref_lines.append(clean_line)
                        i += 1

                    # Join but preserve explicit line breaks
                    ref_content = "\n".join(ref_lines)

                    # Only add reference block if it has actual content (not just whitespace)
                    if ref_content.strip():
                        target = (
                            current_subsection
                            if current_subsection
                            else current_section
                        )
                        if "content" not in target:
                            target["content"] = []

                        target["content"].append(
                            {"type": "reference", "content": ref_content}
                        )
                    continue

            # HTML table detection (detect <table> tags)
            elif "<table" in line.lower() or "<div" in line.lower():
                if current_section:
                    html_lines = []
                    in_table = True

                    # Collect HTML content until we find a closing tag or end of table
                    while i < len(lines):
                        current_line = lines[i]
                        html_lines.append(current_line)

                        # Check for closing tags that might end our HTML block
                        if (
                            "</table>" in current_line.lower()
                            or "</div>" in current_line.lower()
                        ):
                            i += 1
                            break

                        i += 1
                        # If next line doesn't look like HTML continuation, break
                        if i < len(lines) and not (
                            lines[i].strip().startswith("<")
                            or lines[i].strip() == ""
                            or "<" in lines[i]
                            or ">" in lines[i]
                        ):
                            break

                    html_content = "\n".join(html_lines)

                    # Parse HTML table into proper table structure if it's a table
                    if "<table" in html_content.lower():
                        # Clean up the HTML table
                        html_content = re.sub(r'style="[^"]*"', "", html_content)
                        html_content = html_content.replace(
                            "<th>",
                            '<th style="text-align: left; padding: 8px; border-bottom: 1px solid var(--border-color);">',
                        )
                        html_content = html_content.replace(
                            "<td>",
                            '<td style="padding: 8px; border-bottom: 1px solid var(--border-color);">',
                        )
                        html_content = html_content.replace(
                            "<thead>",
                            '<thead style="background-color: var(--sidebar-bg);">',
                        )

                    target = (
                        current_subsection if current_subsection else current_section
                    )
                    if "content" not in target:
                        target["content"] = []

                    target["content"].append({"type": "html", "content": html_content})
                    continue

            # Image reference
            elif "![" in line:
                if current_section:
                    img_pattern = r"!\[.*?\]\((.*?)\)"
                    matches = re.findall(img_pattern, line)

                    for img_path in matches:
                        full_path = base_path / img_path
                        if full_path.exists():
                            base64_img = image_to_base64(full_path)
                            if base64_img:
                                target = (
                                    current_subsection
                                    if current_subsection
                                    else current_section
                                )
                                if "content" not in target:
                                    target["content"] = []

                                target["content"].append(
                                    {
                                        "type": "image",
                                        "content": base64_img,
                                        "alt": line.split("[")[1].split("]")[0]
                                        if "[" in line
                                        else "",
                                    }
                                )
                i += 1
                continue

            # Regular text
            elif line.strip() and current_section:
                # Collect text content
                text_content = line

                # Check if this is part of a multi-line string (like the ones in your examples)
                i += 1
                while i < len(lines):
                    next_line = lines[i]

                    # Check if we should stop collecting
                    if (
                        next_line.startswith("## ")
                        or next_line.startswith("### ")
                        or next_line.startswith("```")
                        or next_line.startswith("    ")
                        or next_line.startswith("\t")
                        or "<table" in next_line.lower()
                        or "<div" in next_line.lower()
                        or "![" in next_line
                    ):
                        break

                    # If line is empty, it might be a paragraph break
                    if not next_line.strip():
                        # Check if there's more text after this
                        j = i + 1
                        has_more_text = False
                        while j < len(lines):
                            if lines[j].strip() and not (
                                lines[j].startswith("## ")
                                or lines[j].startswith("### ")
                                or lines[j].startswith("```")
                                or lines[j].startswith("    ")
                                or lines[j].startswith("\t")
                                or "<table" in lines[j].lower()
                                or "<div" in lines[j].lower()
                                or "![" in lines[j]
                            ):
                                has_more_text = True
                                break
                            j += 1

                        if has_more_text:
                            # Add a blank line as paragraph separator
                            text_content += "\n\n"
                            i += 1
                            continue
                        else:
                            # No more text, stop here
                            break

                    # Add the line to text content
                    text_content += "\n" + next_line
                    i += 1

                # Process the text content - fix escaped newlines and quotes
                if text_content:
                    # Fix escaped newlines
                    text_content = text_content.replace("\\n", "\n")
                    # Fix escaped quotes
                    text_content = text_content.replace('\\"', '"')
                    text_content = text_content.replace("\\'", "'")
                    # Remove surrounding quotes if they exist
                    if text_content.startswith('"') and text_content.endswith('"'):
                        text_content = text_content[1:-1]
                    if text_content.startswith("'") and text_content.endswith("'"):
                        text_content = text_content[1:-1]

                    # Split by double newlines to get paragraphs
                    paragraphs = text_content.split("\n\n")

                    for para in paragraphs:
                        if para.strip():
                            target = (
                                current_subsection
                                if current_subsection
                                else current_section
                            )
                            if "content" not in target:
                                target["content"] = []

                            target["content"].append(
                                {"type": "text", "content": para.strip()}
                            )

                continue

            # Skip blank lines
            elif not line.strip():
                i += 1
                continue

            i += 1

        # Add the last section
        if current_section:
            sections.append(current_section)

        return sections

    def process_content(content_items, section_id):
        """Process content items and return HTML"""
        html = ""
        code_counter = 0

        for item in content_items:
            content_type = item.get("type")

            if content_type == "text":
                content = item["content"]
                if content:
                    # First, clean up any remaining escaped characters
                    content = (
                        content.replace("\\n", "\n")
                        .replace("\\t", "\t")
                        .replace('\\"', '"')
                        .replace("\\'", "'")
                    )

                    # Split by newlines to create proper paragraphs
                    html += '                    <div class="text-content">\n'

                    # Handle different paragraph separators
                    if "\n\n" in content:
                        paragraphs = content.split("\n\n")
                        for para in paragraphs:
                            if para.strip():
                                # Replace single newlines within paragraphs with <br>
                                lines = [
                                    line.strip()
                                    for line in para.split("\n")
                                    if line.strip()
                                ]
                                if lines:
                                    paragraph_html = "<br>".join(lines)
                                    html += f"                        <p>{paragraph_html}</p>\n"
                    else:
                        # Single paragraph, just replace newlines with <br>
                        lines = [
                            line.strip() for line in content.split("\n") if line.strip()
                        ]
                        if lines:
                            paragraph_html = "<br>".join(lines)
                            html += f"                        <p>{paragraph_html}</p>\n"

                    html += "                    </div>\n"

            elif content_type == "reference":
                # For reference blocks, also clean up escaped characters
                if item["content"].strip():
                    content = item["content"]
                    content = (
                        content.replace("\\n", "\n")
                        .replace("\\t", "\t")
                        .replace('\\"', '"')
                        .replace("\\'", "'")
                    )

                    # Replace newlines with <br> tags
                    lines = [
                        line.strip() for line in content.split("\n") if line.strip()
                    ]
                    if lines:
                        formatted_content = "<br>".join(lines)
                        if style_output_blocks:
                            html += f'                    <div class="reference-block">{formatted_content}</div>\n'
                        else:
                            html += f'                    <div class="output-text">{formatted_content}</div>\n'

            elif content_type == "code":
                block_id = f"{section_id}-code-{code_counter}"
                code_counter += 1
                collapsed_class = "collapsed" if code_blocks_collapsed else ""
                # Note: We're not generating the header HTML here anymore
                html += f'''                    <div class="code-container">
                            <div class="code-content {collapsed_class}" id="{block_id}">
                                <pre><code>{item["content"]}</code></pre>
                            </div>
                        </div>
'''

            elif content_type == "image":
                alt_text = item.get("alt", "Image")
                html += f'''                    <div class="image-container">
                            <img src="{item["content"]}" alt="{alt_text}">
                        </div>
'''

            elif content_type == "html":
                html += f"""                    <div class="html-content">
                            {item["content"]}
                        </div>
"""

        return html

    def generate_html(sections):
        """Generate complete HTML with embedded styles and content"""

        # Generate timestamp for footer
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --bg-color: {light_mode_colors["bg"]};
            --text-color: {light_mode_colors["text"]};
            --sidebar-bg: {light_mode_colors["sidebar_bg"]};
            --accent-color: {light_mode_colors["accent"]};
            --border-color: {light_mode_colors["border"]};
            --hover-color: {light_mode_colors["hover"]};
            --code-bg: {light_mode_colors["code_bg"]};
            --reference-bg: {light_mode_colors["reference_bg"]};
            --reference-border: {light_mode_colors["reference_border"]};
        }}

        [data-theme="dark"] {{
            --bg-color: {dark_mode_colors["bg"]};
            --text-color: {dark_mode_colors["text"]};
            --sidebar-bg: {dark_mode_colors["sidebar_bg"]};
            --accent-color: {dark_mode_colors["accent"]};
            --border-color: {dark_mode_colors["border"]};
            --hover-color: {dark_mode_colors["hover"]};
            --code-bg: {dark_mode_colors["code_bg"]};
            --reference-bg: {dark_mode_colors["reference_bg"]};
            --reference-border: {dark_mode_colors["reference_border"]};
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            padding-left: {sidebar_width};
            transition: background-color 0.3s, color 0.3s;
            line-height: 1.6;
        }}

        .sidebar {{
            position: fixed;
            top: 0;
            left: 0;
            width: {sidebar_width};
            height: 100vh;
            background-color: var(--sidebar-bg);
            padding: 15px 12px;
            overflow-y: auto;
            box-shadow: 2px 0 5px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            transition: background-color 0.3s;
        }}

        .sidebar::-webkit-scrollbar {{
            width: 6px;
        }}

        .sidebar::-webkit-scrollbar-track {{
            background: var(--sidebar-bg);
        }}

        .sidebar::-webkit-scrollbar-thumb {{
            background: var(--border-color);
            border-radius: 3px;
        }}

        .sidebar::-webkit-scrollbar-thumb:hover {{
            background: var(--accent-color);
        }}

        .sidebar-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 12px;
            //border-bottom: 1px solid var(--border-color);
        }}

        .sidebar-title {{
            font-size: 14px;
            font-weight: bold;
            color: var(--accent-color);
        }}

        .theme-toggle {{
            background: none;
            border: none;
            color: var(--text-color);
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 14px;
            transition: all 0.3s;
        }}

        .theme-toggle:hover {{
            opacity: 0.7;  /* Optional: just dim slightly on hover */
        }}

        .search-box {{
            margin-bottom: 15px;
            position: relative;
        }}

        .search-input {{
            width: 100%;
            padding: 8px 30px 8px 10px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 13px;
            background-color: var(--bg-color);
            color: var(--text-color);
            transition: all 0.2s;
        }}

        .search-input:focus {{
            outline: none;
            border-color: var(--accent-color);
            box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1);
        }}

        .search-clear {{
            position: absolute;
            right: 8px;
            top: 8px;
            background: none;
            border: none;
            color: var(--text-color);
            cursor: pointer;
            font-size: 16px;
            padding: 0 4px;
            opacity: 0;
            transition: opacity 0.2s;
            line-height: 1;
        }}

        .search-clear.visible {{
            opacity: 0.6;
        }}

        .search-clear:hover {{
            opacity: 1 !important;
        }}

        .search-count {{
            font-size: 11px;
            color: var(--text-color);
            margin-top: 4px;
            display: block;
            opacity: 0.7;
        }}

        .nav-links {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}

        .nav-link {{
            color: var(--text-color);
            text-decoration: none;
            padding: 8px 10px;
            border-radius: 4px;
            font-size: 13px;
            border-left: 2px solid transparent;
            transition: all 0.2s;
            display: block;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .nav-link:hover {{
            background-color: var(--accent-color);
            color: white;
            border-left-color: var(--sidebar-bg);
            transform: translateX(3px);
        }}

        .nav-link.hidden {{
            display: none;
        }}

        .nav-link.subsection-link {{
            font-size: 12px;
            padding-left: 20px;
            color: var(--text-color);
            opacity: 0.9;
            margin-top: 1px;
            margin-bottom: 1px;
        }}

        .main-content {{
            padding: 0;
            max-width: 1400px;
            margin: 0 auto;
        }}

        .report-header {{
            padding: 40px 30px;
            margin-bottom: 30px;
            color: var(--text-color);
        }}

        .report-title {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 8px;
        }}

        .report-subtitle {{
            font-size: 18px;
            opacity: 0.9;
            margin-bottom: 12px;
        }}

        .report-description {{
            font-size: 14px;
            opacity: 0.85;
            max-width: 800px;
            line-height: 1.6;
        }}

        .content-area {{
            padding: 0 30px 30px 30px;
        }}

        .section {{
            margin-bottom: 40px;
            scroll-margin-top: 20px;
        }}

        .section-title {{
            font-size: 24px;
            color: var(--accent-color);
            margin-bottom: 20px;
            padding-bottom: 8px;
            //border-bottom: 1px solid var(--border-color);
            position: relative;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .section-title-text {{
            flex: 1;
        }}

        .code-buttons {{
            display: flex;
            gap: 4px;
            opacity: 0;
            transition: opacity 0.2s;
            margin-left: 10px;
        }}

        .code-buttons:hover {{
            opacity: 1;
        }}

        .subsection {{
            margin-bottom: 25px;
            padding-left: 15px;
            //border-left: 2px solid var(--border-color);
            padding-left: 0;
        }}

        .subsection-title {{
            font-size: 18px;
            color: var(--text-color);
            margin-bottom: 12px;
            font-weight: 600;
            position: relative;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .subsection-title-text {{
            flex: 1;
        }}

        .content-block {{
            margin-bottom: 15px;
        }}

        .text-content {{
            color: var(--text-color);
            margin: 12px 0;
            line-height: 1.7;
        }}

        .text-content p {{
            margin-bottom: 16px;
            padding-bottom: 8px;
        }}

        .text-content p:last-child {{
            margin-bottom: 0;
        }}

        .reference-block {{
            //background-color: var(--reference-bg);
            border-left: 3px solid var(--reference-border);
            padding: 12px 15px;
            margin: 15px 0;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
            white-space: pre-wrap;
            color: var(--text-color);
        }}

        .output-text {{
            margin: 15px 0;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
            white-space: pre-wrap;
            color: var(--text-color);
        }}

        .code-container {{
            position: relative;
            margin: 15px 0;
        }}

        .code-content {{
            background-color: var(--code-bg);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}

        .code-content.collapsed {{
            display: none;
        }}

        .code-btn {{
            background: none;
            border: none;
            color: var(--text-color);
            cursor: pointer;
            padding: 4px;
            border-radius: 3px;
            font-size: 14px;
            transition: all 0.2s;
            line-height: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
        }}

        .code-btn:hover {{
            background-color: var(--hover-color);
        }}

        .code-btn svg {{
            width: 14px;
            height: 14px;
            fill: currentColor;
        }}

        pre {{
            margin: 0;
            padding: 15px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.4;
        }}

        code {{
            color: var(--text-color);
        }}

        .image-container {{
            margin: 20px 0;
            text-align: center;
        }}

        .image-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            border: 1px solid var(--border-color);
        }}

        .html-content {{
            margin: 20px 0;
            overflow-x: auto;
        }}

        .html-content table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            font-size: 13px;
        }}

        .html-content th {{
            background-color: var(--sidebar-bg);
            color: var(--text-color);
            text-align: left;
            padding: 10px;
            border-bottom: 2px solid var(--border-color);
            font-weight: 600;
        }}

        .html-content td {{
            padding: 10px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-color);
        }}

        .html-content tr:hover {{
            background-color: var(--hover-color);
        }}

        .html-content .dataframe {{
            width: 100%;
            margin: 15px 0;
        }}

        .report-footer {{
            background-color: var(--sidebar-bg);
            padding: 25px 30px;
            margin-top: 50px;
            border-top: 1px solid var(--border-color);
            text-align: center;
            font-size: 12px;
            color: var(--text-color);
        }}

        .footer-timestamp {{
            opacity: 0.7;
            font-style: italic;
            margin-top: 8px;
        }}

        @media (max-width: 768px) {{
            body {{
                padding-left: 0;
                padding-top: 60px;
            }}

            .sidebar {{
                width: 100%;
                height: auto;
                position: relative;
            }}

            .report-header {{
                padding: 25px 20px;
            }}

            .report-title {{
                font-size: 24px;
            }}

            .content-area {{
                padding: 0 20px 20px 20px;
            }}

            .subsection {{
                padding-left: 10px;
            }}

            .code-buttons {{
                opacity: 1; /* Always show on mobile for easier interaction */
            }}
        }}
    </style>
</head>
<body data-theme="{default_theme}">
    <div class="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-title">{navigation_title}</div>
            <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme">🔅</button>
        </div>

        <div class="search-box">
            <input type="text"
                   class="search-input"
                   id="search-input"
                   placeholder="Search sections..."
                   onkeyup="filterSections()"
                   oninput="toggleClearButton()">
            <button class="search-clear" id="search-clear" onclick="clearSearch()" title="Clear search">×</button>
            <span class="search-count" id="search-count"></span>
        </div>

        <div class="nav-links" id="nav-links">
"""

        for section in sections:
            html += f'            <a href="#{section["id"]}" class="nav-link" data-section-id="{section["id"]}">{section["title"]}</a>\n'
            # Add subsections to navigation
            for subsection in section.get("subsections", []):
                subsection_id = f"{section['id']}-{subsection['title'].lower().replace(' ', '-').replace(':', '').replace('(', '').replace(')', '').replace('/', '-').replace('.', '')}"
                html += f'            <a href="#{subsection_id}" class="nav-link subsection-link" data-section-id="{subsection_id}">  {subsection["title"]}</a>\n'

        html += (
            """        </div>
    </div>

    <div class="main-content">
        <div class="report-header">
            <div class="report-title">"""
            + page_title
            + """</div>
"""
        )

        if page_subtitle:
            html += f'            <div class="report-subtitle">{page_subtitle}</div>\n'

        if page_description:
            html += f'            <div class="report-description">{page_description}</div>\n'

        html += """        </div>

        <div class="content-area">
"""

        for section in sections:
            html += f'            <div class="section" id="{section["id"]}" data-section-id="{section["id"]}">\n'

            # Generate section title with code buttons for each code block in this section
            section_code_blocks = [
                item
                for item in section.get("content", [])
                if item.get("type") == "code"
            ]
            if include_code_blocks and section_code_blocks:
                # Add code buttons for each code block in this section
                buttons_html = '<div class="code-buttons">'
                for idx in range(len(section_code_blocks)):
                    block_id = f"{section['id']}-code-{idx}"
                    buttons_html += f"""
                        <button class="code-btn code-toggle" onclick="toggleCode('{block_id}')" title="Toggle code">
                            <svg viewBox="0 0 24 24">
                                <path d="M19 13H5c-0.6 0-1-0.4-1-1s0.4-1 1-1h14c0.6 0 1 0.4 1 1S19.6 13 19 13z"/>
                            </svg>
                        </button>
                        <button class="code-btn code-copy" onclick="copyCode('{block_id}')" title="Copy code">
                            <svg viewBox="0 0 24 24">
                                <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                            </svg>
                        </button>
                    """
                buttons_html += "</div>"
                html += f'                <h2 class="section-title"><span class="section-title-text">{section["title"]}</span>{buttons_html}</h2>\n'
            else:
                html += f'                <h2 class="section-title">{section["title"]}</h2>\n'

            if section.get("subsections"):
                for subsection in section["subsections"]:
                    subsection_id = f"{section['id']}-{subsection['title'].lower().replace(' ', '-').replace(':', '').replace('(', '').replace(')', '').replace('/', '-').replace('.', '')}"

                    # Generate subsection title with code buttons for each code block in this subsection
                    subsection_code_blocks = [
                        item
                        for item in subsection.get("content", [])
                        if item.get("type") == "code"
                    ]
                    if include_code_blocks and subsection_code_blocks:
                        # Add code buttons for each code block in this subsection
                        buttons_html = '<div class="code-buttons">'
                        for idx in range(len(subsection_code_blocks)):
                            block_id = f"{subsection_id}-code-{idx}"
                            buttons_html += f"""
                                <button class="code-btn code-toggle" onclick="toggleCode('{block_id}')" title="Toggle code">
                                    <svg viewBox="0 0 24 24">
                                        <path d="M19 13H5c-0.6 0-1-0.4-1-1s0.4-1 1-1h14c0.6 0 1 0.4 1 1S19.6 13 19 13z"/>
                                    </svg>
                                </button>
                                <button class="code-btn code-copy" onclick="copyCode('{block_id}')" title="Copy code">
                                    <svg viewBox="0 0 24 24">
                                        <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                                    </svg>
                                </button>
                            """
                        buttons_html += "</div>"
                        html += f'                <div class="subsection" id="{subsection_id}" data-section-id="{subsection_id}">\n'
                        html += f'                    <h3 class="subsection-title"><span class="subsection-title-text">{subsection["title"]}</span>{buttons_html}</h3>\n'
                    else:
                        html += f'                <div class="subsection" id="{subsection_id}" data-section-id="{subsection_id}">\n'
                        html += f'                    <h3 class="subsection-title">{subsection["title"]}</h3>\n'

                    if subsection.get("content"):
                        html += process_content(subsection["content"], subsection_id)

                    html += "                </div>\n"

            if section.get("content"):
                html += process_content(section["content"], section["id"])

            html += "            </div>\n\n"

        html += """        </div>

        <div class="report-footer">
"""

        if footer_content:
            html += f"            <div>{footer_content}</div>\n"

        html += f'            <div class="footer-timestamp">Generated on {timestamp}</div>\n'

        html += """        </div>
    </div>

    <script>
        function toggleTheme() {
            const body = document.body;
            const currentTheme = body.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            body.setAttribute('data-theme', newTheme);
            localStorage.setItem('report-theme', newTheme);
        }

        const savedTheme = localStorage.getItem('report-theme');
        if (savedTheme) {
            document.body.setAttribute('data-theme', savedTheme);
        }

        function toggleCode(blockId) {
            const codeContent = document.getElementById(blockId);
            const toggleBtn = event.target.closest('.code-toggle');

            if (codeContent.classList.contains('collapsed')) {
                codeContent.classList.remove('collapsed');
                // Change SVG to minus/hide icon
                toggleBtn.innerHTML = `<svg viewBox="0 0 24 24">
                    <path d="M19 13H5c-0.6 0-1-0.4-1-1s0.4-1 1-1h14c0.6 0 1 0.4 1 1S19.6 13 19 13z"/>
                </svg>`;
            } else {
                codeContent.classList.add('collapsed');
                // Change SVG to plus/show icon
                toggleBtn.innerHTML = `<svg viewBox="0 0 24 24">
                    <path d="M19 13h-6v6c0 0.6-0.4 1-1 1s-1-0.4-1-1v-6H5c-0.6 0-1-0.4-1-1s0.4-1 1-1h6V5c0-0.6 0.4-1 1-1s1 0.4 1 1v6h6c0.6 0 1 0.4 1 1S19.6 13 19 13z"/>
                </svg>`;
            }
        }

        function copyCode(blockId) {
            const codeElement = document.querySelector(`#${blockId} code`);
            const text = codeElement.textContent;

            navigator.clipboard.writeText(text).then(() => {
                const btn = event.target.closest('.code-copy');
                const originalSvg = btn.innerHTML;
                // Change to checkmark icon
                btn.innerHTML = `<svg viewBox="0 0 24 24" style="color: var(--accent-color);">
                    <path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/>
                </svg>`;
                setTimeout(() => {
                    btn.innerHTML = originalSvg;
                }, 2000);
            });
        }

        function toggleClearButton() {
            const searchInput = document.getElementById('search-input');
            const clearButton = document.getElementById('search-clear');

            if (searchInput.value.trim() !== '') {
                clearButton.classList.add('visible');
            } else {
                clearButton.classList.remove('visible');
            }
        }

        function clearSearch() {
            const searchInput = document.getElementById('search-input');
            searchInput.value = '';
            toggleClearButton();
            filterSections();
        }

        function filterSections() {
            const searchInput = document.getElementById('search-input');
            const searchTerm = searchInput.value.toLowerCase().trim();
            const navLinks = document.querySelectorAll('.nav-link');
            const sections = document.querySelectorAll('.section');
            const searchCount = document.getElementById('search-count');

            let visibleCount = 0;
            const totalCount = navLinks.length;

            // When there's no search term, show everything
            if (searchTerm === '') {
                navLinks.forEach(link => link.classList.remove('hidden'));
                sections.forEach(section => section.classList.remove('hidden'));
                searchCount.textContent = '';
                return;
            }

            // Reset visibility for all sections (they remain visible by default)
            sections.forEach(section => section.classList.remove('hidden'));

            // Filter navigation links only
            navLinks.forEach(link => {
                const linkText = link.textContent.toLowerCase();
                if (linkText.includes(searchTerm)) {
                    link.classList.remove('hidden');
                    visibleCount++;
                } else {
                    link.classList.add('hidden');
                }
            });

            searchCount.textContent = `Showing ${visibleCount} of ${totalCount} navigation items`;
        }

        // Initialize navigation links with event listeners
        function initNavigation() {
            document.querySelectorAll('.nav-link').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('href');
                    const targetElement = document.querySelector(targetId);
                    if (targetElement) {
                        targetElement.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });

                        // Highlight the section briefly
                        targetElement.style.backgroundColor = 'var(--hover-color)';
                        setTimeout(() => {
                            targetElement.style.backgroundColor = '';
                        }, 1000);
                    }
                });
            });
        }

        // Initialize code buttons with correct icons based on collapsed state
        function initCodeButtons() {
            document.querySelectorAll('.code-toggle').forEach(btn => {
                const blockId = btn.getAttribute('onclick').match(/toggleCode\('([^']+)'\)/)[1];
                const codeContent = document.getElementById(blockId);
                if (codeContent && codeContent.classList.contains('collapsed')) {
                    // Set to plus icon for collapsed state
                    btn.innerHTML = `<svg viewBox="0 0 24 24">
                        <path d="M19 13h-6v6c0 0.6-0.4 1-1 1s-1-0.4-1-1v-6H5c-0.6 0-1-0.4-1-1s0.4-1 1-1h6V5c0-0.6 0.4-1 1-1s1 0.4 1 1v6h6c0.6 0 1 0.4 1 1S19.6 13 19 13z"/>
                    </svg>`;
                }
            });
        }

        document.addEventListener('DOMContentLoaded', function() {
            initNavigation();
            initCodeButtons();
            toggleClearButton();
        });
    </script>
</body>
</html>"""

        return html

    try:
        md_path = Path(markdown_file)
        if not md_path.exists():
            print(f"Error: Markdown file '{markdown_file}' not found!")
            return None

        print(f"📖 Reading markdown file: {markdown_file}")
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        print("🔍 Parsing markdown content...")
        sections = parse_markdown(md_content, md_path.parent)

        if not sections:
            print("No sections found in markdown file!")
            return None

        print(f"✅ Found {len(sections)} sections")

        total_code = 0
        total_images = 0
        total_refs = 0
        total_html = 0

        for section in sections:
            total_code += len(
                [c for c in section.get("content", []) if c.get("type") == "code"]
            )
            total_images += len(
                [c for c in section.get("content", []) if c.get("type") == "image"]
            )
            total_refs += len(
                [c for c in section.get("content", []) if c.get("type") == "reference"]
            )
            total_html += len(
                [c for c in section.get("content", []) if c.get("type") == "html"]
            )
            for subsection in section.get("subsections", []):
                total_code += len(
                    [
                        c
                        for c in subsection.get("content", [])
                        if c.get("type") == "code"
                    ]
                )
                total_images += len(
                    [
                        c
                        for c in subsection.get("content", [])
                        if c.get("type") == "image"
                    ]
                )
                total_refs += len(
                    [
                        c
                        for c in subsection.get("content", [])
                        if c.get("type") == "reference"
                    ]
                )
                total_html += len(
                    [
                        c
                        for c in subsection.get("content", [])
                        if c.get("type") == "html"
                    ]
                )

        print("🌐 Generating HTML report...")
        html_content = generate_html(sections)

        output_path = md_path.parent / output_file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print("✅ HTML report created successfully!")
        print(f"📁 Output: {output_path}")
        print(f"📊 Sections: {len(sections)}")
        if include_code_blocks:
            print(
                f"💻 Code blocks: {total_code} ({'collapsed' if code_blocks_collapsed else 'expanded'})"
            )
            print(f"🎨 Code buttons: Integrated into section titles (hover to reveal)")
        print(f"🖼️  Images embedded: {total_images}")
        print(
            f"📝 Reference blocks: {total_refs} ({'styled' if style_output_blocks else 'plain'})"
        )
        print(f"📋 HTML tables: {total_html}")

        return str(output_path)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None


# if __name__ == "__main__":
#     convert_markdown_to_html(
#         # markdown_file=r"C:\my_disk\edupunk\all_docs\docs\analytics_express\machine_learning\model_selection\roc_curve.md",
#         # markdown_file=r"C:\my_disk\edupunk\all_docs\docs\analytics_express\machine_learning\model_selection\demystify_ml_model_selection.md",
#         markdown_file=r"C:\my_disk\edupunk\all_docs\docs\analytics_express\machine_learning\regression\house_prices.md",
#         # markdown_file=r"C:\my_disk\edupunk\all_docs\docs\analytics_express\machine_learning\regression\marketing_effectiveness.md",
#         output_file=r"C:\my_disk\projects\visual_library\report\py_to_ipynb_to_html.html",
#         page_title="Python Diagrams Documentation",
#         page_subtitle="Comprehensive Guide to Creating Visual Diagrams",
#         page_description="This report demonstrates...",
#         footer_content="Created with Python • Link",
#         default_theme="dark",
#         navigation_title="Report Juice!",
#         include_code_blocks=True,
#         code_blocks_collapsed=True,
#         style_output_blocks=False,  # Set to False for plain text output without border/background
#     )
