# %% docx_to_md

## Dependencies
from bs4 import BeautifulSoup
import os
import re
import mammoth
import markdownify


def docx_to_md(
    source_folder,
    destination_folder,
    file_size_limit_in_mb=None,
    scan_subfolders=1,
    folder_structure=1,
):
    """
    Convert .docx files to .md format while optionally maintaining the folder structure.

    Parameters:
    - source_folder (str): Path to the source directory containing .docx files.
    - destination_folder (str): Path to the destination directory where .md files will be saved.
    - file_size_limit_in_mb (float, optional): Maximum file size in MB for conversion. Files larger than this will be skipped.
    - scan_subfolders (int, 0|1): If 1, scan subfolders recursively; if 0, process only the source folder.
    - folder_structure (int, 0|1): If 1, maintain folder structure in the destination; if 0, place all files in the destination folder.
    """

    # Define the custom style map for Mammoth
    style_map = """
    p[style-name='Contact Info'] => p.contact-info
    p[style-name='Normal1'] => p.normal
    p[style-name='Heading 31'] => h3
    """

    # Define file size limit in bytes, if specified
    file_size_limit_bytes = (
        file_size_limit_in_mb * 1024 * 1024 if file_size_limit_in_mb else None
    )

    for root, dirs, files in os.walk(source_folder):
        if not scan_subfolders and root != source_folder:
            continue

        # Filter `.docx` files in the current directory
        docx_files = [file for file in files if file.lower().endswith(".docx")]
        if not docx_files:
            continue  # Skip creating the destination directory if no .docx files are present

        for file in docx_files:
            source_file = os.path.join(root, file)

            # Determine destination path based on `folder_structure` parameter
            if folder_structure:
                relative_path = os.path.relpath(root, source_folder)
                dest_path = os.path.join(destination_folder, relative_path)
            else:
                dest_path = destination_folder

            os.makedirs(dest_path, exist_ok=True)
            destination_file = os.path.join(
                dest_path, os.path.splitext(file)[0] + ".md"
            )

            # Check file size limit
            if (
                file_size_limit_bytes
                and os.path.getsize(source_file) > file_size_limit_bytes
            ):
                print(f"Skipping {source_file}: File size exceeds the limit.")
                continue

            try:
                # Read and convert .docx to HTML using Mammoth
                with open(source_file, "rb") as docx_file:
                    result = mammoth.convert_to_html(docx_file, style_map=style_map)
                    html = result.value
                    messages = result.messages
                    if messages:
                        print(f"Messages for {source_file}: {messages}")

                # Parse the HTML with BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")

                for strong in soup.find_all("strong"):
                    strong.insert_before(soup.new_tag("br"))

                # Decrease heading levels dynamically
                for heading in soup.find_all(
                    ["h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8", "h9"]
                ):
                    current_level = int(
                        heading.name[1]
                    )  # Extract the current heading level (e.g., 1 for <h1>)
                    if (
                        current_level < 6
                    ):  # Only decrease if the level is less than 6 (since <h6> is the lowest level)
                        new_level = current_level + 1
                        heading.name = (
                            f"h{new_level}"  # Update the tag to the new level
                        )

                # Ensure paragraphs and line breaks are preserved
                for paragraph in soup.find_all("p"):
                    # Replace any `<br>` tags within paragraphs with actual line breaks for Markdown compatibility
                    paragraph_text = paragraph.decode_contents().replace("<br>", "\n")
                    paragraph.string = (
                        paragraph_text.strip()
                    )  # Replace content with line-preserved text

                # Get the modified HTML
                modified_html = str(soup)

                # Convert HTML to Markdown using Markdownify
                try:
                    markdown_content = markdownify.markdownify(
                        modified_html, heading_style="ATX"
                    )
                except Exception as e:
                    print(f"Markdown conversion error: {e}")
                    markdown_content = modified_html

                # Convert modified HTML to Markdown
                markdown_output = markdownify.markdownify(
                    markdown_content, heading_style="ATX"
                )

                # Create H1 heading with hyperlink to the original file
                docx_name = os.path.splitext(file)[0]
                h1_title = re.sub(r"[_-]+", " ", docx_name).strip().title()
                corrected_path = source_file.replace("\\", "/")
                h1_hyperlink = (
                    f'# [{h1_title}](file:///{corrected_path}){{target="_blank"}}\n\n'
                )

                # Save Markdown to destination file
                with open(destination_file, "w", encoding="utf-8") as md_file:
                    md_file.write(h1_hyperlink)
                    md_file.write(markdown_output)

                print(f"Converted {source_file} -> {destination_file}")

            except Exception as e:
                print(f"Error processing {source_file}: {e}")
