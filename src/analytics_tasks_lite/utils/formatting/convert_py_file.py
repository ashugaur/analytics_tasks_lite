# %% convert_py_file_to__ipynb_html_md

## Dependencies
from pathlib import Path
import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell
from nbclient import execute
from nbformat import read, write
from nbconvert import HTMLExporter, MarkdownExporter
from nbconvert.writers import FilesWriter
import subprocess as sp
from bs4 import BeautifulSoup
import os

## convert_py_file_to__ipynb_html_md


def export_notebook(notebook_path, exporter_cls, extension, output_folder):
    """
    Export the notebook to the specified format and save it in the given output folder.
    """
    notebook_path = Path(notebook_path)
    with open(notebook_path, "r", encoding="utf-8") as file:
        notebook = nbformat.read(file, as_version=4)

    exporter = exporter_cls()
    output, _ = exporter.from_notebook_node(notebook)

    output_file_path = output_folder / notebook_path.with_suffix(extension).name
    with open(output_file_path, "w", encoding="utf-8") as file:
        file.write(output)
    print(f"Exported to {output_file_path}")


def convert_py_file(
    py_file_path,
    output_format=[".ipynb"],
    run_ipynb=False,
    output_folder=None,
    md_output_folder=None,
    md_img_folder=None,
    file_prefix=None,
    file_suffix=None,
):
    """
    Convert a .py file to various formats with optional execution, destination folders, and filtering options.

    Parameters:
        py_file_path (str): Path to the .py file or directory containing .py files.
        output_format (list): List of formats to export (e.g., ['.ipynb', '.html', '.md']).
        run_ipynb (bool): Whether to execute the notebook before exporting.
        output_folder (str): Custom folder for all output files.
        md_output_folder (str): Custom folder for Markdown files and images.
        md_img_folder (str): Custom subfolder for Markdown images.
        file_prefix (str): Process only files starting with this prefix.
        file_suffix (str): If specified, disables notebook execution for files with this suffix.
    """
    if file_prefix:
        dir_path = (
            Path(py_file_path).parent
            if Path(py_file_path).is_file()
            else Path(py_file_path)
        )
        matching_files = list(dir_path.glob(f"{file_prefix}*.py"))

        if not matching_files:
            print(f"No files found with prefix '{file_prefix}' in {dir_path}")
            return

        for file_path in matching_files:
            print(f"\nProcessing {file_path.name}...")
            convert_py_file(
                file_path,
                output_format,
                run_ipynb,
                output_folder,
                md_output_folder,
                md_img_folder,
                file_prefix=None,
                file_suffix=file_suffix,
            )
        return

    py_file_path = Path(py_file_path)
    base_output_folder = output_folder or py_file_path.parent
    base_output_folder = Path(base_output_folder)
    base_output_folder.mkdir(parents=True, exist_ok=True)

    # Check if file_suffix matches
    if file_suffix and py_file_path.name.endswith(file_suffix):
        run_ipynb = False  # Disable execution for matching files
        print(
            f"Execution disabled for file: {py_file_path.name} (matches suffix '{file_suffix}')"
        )

    notebook_file_path = base_output_folder / py_file_path.with_suffix(".ipynb").name

    if not run_ipynb and notebook_file_path.exists():
        # If run_ipynb is False and notebook exists, use the existing notebook
        print(f"Using existing notebook: {notebook_file_path}")
        with open(notebook_file_path, "r", encoding="utf-8") as file:
            notebook = read(file, as_version=4)
    else:
        # Create new notebook from .py file
        with open(py_file_path, "r", encoding="utf-8") as f:
            code = f.read()

        notebook = new_notebook()
        blocks = code.split("\n# %% ")

        if blocks[0].strip().startswith("# %% "):
            blocks[0] = "##" + blocks[0][4:]

        for i, block in enumerate(blocks):
            parts = block.split("\n##")
            if i == 0 and parts[0].strip():
                notebook.cells.append(new_markdown_cell(parts[0].strip()))
            elif i > 0 and parts[0].strip():
                heading = parts[0].strip()
                notebook.cells.append(new_markdown_cell("## " + heading))
            for part in parts[1:]:
                markdown_heading = part.split("\n", 1)[0].strip()
                code_content = part.split("\n", 1)[1].strip() if "\n" in part else ""
                if markdown_heading:
                    notebook.cells.append(new_markdown_cell("### " + markdown_heading))
                if code_content:
                    notebook.cells.append(new_code_cell(code_content))

        # Write the notebook
        nbformat.write(notebook, notebook_file_path)

        # Execute if requested
        if run_ipynb:
            with open(notebook_file_path, "r", encoding="utf-8") as file:
                notebook = read(file, as_version=4)
            executed_notebook = execute(notebook, output_path=str(notebook_file_path))
            with open(notebook_file_path, "w", encoding="utf-8") as file:
                write(executed_notebook, file)
            notebook = executed_notebook

    try:
        # Convert to other formats
        for fmt in output_format:
            if fmt == ".html":
                export_notebook(
                    notebook_file_path, HTMLExporter, fmt, base_output_folder
                )
            elif fmt == ".md":
                export_notebook_with_images_and_clean_tables(
                    notebook_file_path,
                    fmt,
                    base_output_folder,
                    md_output_folder=md_output_folder,
                    md_img_folder=md_img_folder,
                )
    finally:
        # Clean up .ipynb file only if it's not in output_format AND we ran the notebook
        if ".ipynb" not in output_format and run_ipynb:
            notebook_file_path.unlink(missing_ok=True)

    # Open the generated file only if .ipynb was requested
    if ".ipynb" in output_format:
        sp.Popen(str(notebook_file_path), shell=True)


def export_notebook_with_images_and_clean_tables(
    notebook_path, extension, output_folder, md_output_folder=None, md_img_folder=None
):
    """
    Export the notebook to Markdown with optional custom output locations.

    Parameters:
    -----------
    notebook_path : str or Path
        Path to the notebook file
    extension : str
        File extension (e.g., '.md')
    output_folder : Path
        Default output folder
    md_output_folder : Path or str, optional
        Custom output folder for markdown files
    md_img_folder : Path or str, optional
        Custom folder for markdown images
    """
    with open(notebook_path, "r", encoding="utf-8") as file:
        notebook = nbformat.read(file, as_version=4)

    markdown_exporter = MarkdownExporter()
    markdown_exporter.output_files_dir = "img"
    markdown_exporter.files_writer = FilesWriter()

    output, resources = markdown_exporter.from_notebook_node(notebook)

    # Clean up HTML in the Markdown content
    output = clean_html_tables_and_styles(output)

    # Escape HTML-like output (e.g., from object representations)
    output = escape_html_like_output(output)

    # Determine output locations
    final_md_folder = Path(md_output_folder) if md_output_folder else output_folder
    final_img_folder = Path(md_img_folder) if md_img_folder else final_md_folder / "img"

    # Create output directories
    final_md_folder.mkdir(parents=True, exist_ok=True)
    final_img_folder.mkdir(parents=True, exist_ok=True)

    # Save images
    for idx, (filename, content) in enumerate(
        resources.get("outputs", {}).items(), start=1
    ):
        img_file_path = (
            final_img_folder
            / f"{Path(notebook_path).stem}_{idx}{Path(filename).suffix}"
        )
        with open(img_file_path, "wb") as img_file:
            img_file.write(content)

    # Adjust image references in markdown
    rel_img_path = os.path.relpath(final_img_folder, final_md_folder)
    for idx, filename in enumerate(resources.get("outputs", {}).keys(), start=1):
        old_ref = filename
        new_ref = (
            f"{rel_img_path}/{Path(notebook_path).stem}_{idx}{Path(filename).suffix}"
        )
        output = output.replace(old_ref, new_ref)

    # Save the markdown file
    md_file_path = final_md_folder / Path(notebook_path).with_suffix(extension).name
    with open(md_file_path, "w", encoding="utf-8") as file:
        file.write(output)
    print(f"Exported to {md_file_path}")


def escape_html_like_output(md_content):
    """
    Escape HTML-like output in code cell results so they display properly.
    Converts < to &lt; and > to &gt; for indented lines that look like HTML tags.
    """
    import re

    # Match indented lines that start with < and end with >
    # These are code outputs that look like HTML but aren't
    def escape_brackets(match):
        indent = match.group(1)
        content = match.group(2)
        # Replace < with &lt; and > with &gt;
        content = content.replace("<", "&lt;").replace(">", "&gt;")
        return indent + content

    # Pattern: 4 spaces followed by content starting with < and ending with >
    result = re.sub(
        r"^(    )(<[^>]+>)\s*$", escape_brackets, md_content, flags=re.MULTILINE
    )

    return result


def clean_html_tables_and_styles(md_content):
    """
    Remove <style> tags, clean up <table> elements (remove borders and classes),
    and wrap tables in <div> tags.
    """
    soup = BeautifulSoup(md_content, "html.parser")

    # Remove <style> tags
    for style in soup.find_all("style"):
        style.decompose()

    # Remove 'border' attribute and 'class="dataframe"' from <table> tags
    for table in soup.find_all("table"):
        if "border" in table.attrs:
            del table.attrs["border"]
        if "class" in table.attrs and "dataframe" in table.attrs["class"]:
            table.attrs["class"].remove("dataframe")
            # Remove the 'class' attribute entirely if it's now empty
            if not table.attrs["class"]:
                del table.attrs["class"]

    # Convert to string FIRST
    result = str(soup)

    # Then use regex to wrap tables in divs (avoiding BeautifulSoup manipulation which can break formatting)
    import re

    # Wrap each table in a div
    result = re.sub(
        r"(<table.*?</table>)", r"<div>\n\1\n</div>", result, flags=re.DOTALL
    )

    return result
