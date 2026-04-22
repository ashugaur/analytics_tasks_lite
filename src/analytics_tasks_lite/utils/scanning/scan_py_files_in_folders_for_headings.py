import pandas as pd
import numpy as np
import subprocess
from os.path import isfile
import re
from pathlib import Path
import os.path


def scan_py_files_in_folders_for_headings(
    unc, md_name="Project report", heading_order=0, start_heading=1
):
    """function to extract directory tree and python file headings to be human readable
    heading_order = 1: ascending i.e. markdown default heading hierarchy
    heading_order = 0: descending
    start_heading = 1: the starting heading level for the top folder
    md_name = 'Project report': the first line in the .md output
    """

    ## scan folder
    def list_folder_structure(folder_path, unc):
        result = []

        for root, dirs, files in os.walk(folder_path):
            # Calculate the indentation level based on the relative path
            relative_path = os.path.relpath(root, unc)
            indent_level = relative_path.count(os.path.sep)

            # Adjust heading level based on start_heading
            heading_level = start_heading + indent_level

            # Format and append to the result
            formatted_item = f"{'#' * heading_level} {os.path.basename(root)}"
            result.append(formatted_item)

            # Print files in the current folder
            for file in files:
                file_path = os.path.join(root, file)
                file_heading_level = (
                    heading_level + 1
                )  # Set the number of hashes for files
                formatted_file = (
                    f"{'#' * file_heading_level} {file_path[len(str(unc)) + 1 :]}"
                )
                result.append(formatted_file)

        return result

    def export_to_dataframe(folder_path, unc):
        formatted_structure = list_folder_structure(folder_path, unc)

        # Create a Pandas DataFrame
        df = pd.DataFrame(
            {
                "unc": [
                    os.path.join(unc, item.split(" ", 1)[1])
                    for item in formatted_structure
                ],
                "formatted_structure": [
                    os.path.basename(item.split(" ", 1)[1])
                    for item in formatted_structure
                ],
                "num_hashes": [item.count("#") for item in formatted_structure],
            }
        )

        return df

    # run
    output_dataframe = export_to_dataframe(unc, unc)
    output_dataframe = output_dataframe.drop(output_dataframe.index[[0]]).reset_index(
        drop=True
    )

    ## scan files
    def scan_py_files_for_headings_modified(unc, num_hashes):
        """function to extract comments from python a file and export as .md to create markmap"""

        # Read the file and process lines
        lines = []
        flags = []
        extracts = []

        if heading_order == 0:
            pattern0 = re.compile(r"^(#|--) ")
            pattern1 = re.compile(r"^# %% ")
            pattern2 = re.compile(r"^###### ")
            pattern3 = re.compile(r"^##### ")
            pattern4 = re.compile(r"^#### ")
            pattern5 = re.compile(r"^### ")
            pattern6 = re.compile(r"^## ")
            pattern7 = re.compile(r"^#([^ ]+)")

            with open(unc, "r", encoding="utf-8", errors="ignore") as file:
                for line in file:
                    lines.append(line.strip())
                    if pattern1.match(line):
                        flags.append(1 + num_hashes)
                        extracts.append(pattern1.sub("", line).strip())
                    elif pattern2.match(line):
                        flags.append(2 + num_hashes)
                        extracts.append(pattern2.sub("", line).strip())
                    elif pattern3.match(line):
                        flags.append(3 + num_hashes)
                        extracts.append(pattern3.sub("", line).strip())
                    elif pattern4.match(line):
                        flags.append(4 + num_hashes)
                        extracts.append(pattern4.sub("", line).strip())
                    elif pattern5.match(line):
                        flags.append(5 + num_hashes)
                        extracts.append(pattern5.sub("", line).strip())
                    elif pattern6.match(line):
                        flags.append(6 + num_hashes)
                        extracts.append(pattern6.sub("", line).strip())
                    elif pattern7.match(line):
                        flags.append(999 + num_hashes)
                        extracts.append(pattern7.sub(r"\1", line).strip())
                    elif pattern0.match(line):
                        flags.append(-1)
                        extracts.append(pattern0.sub("", line).strip())
                    else:
                        flags.append(0)
                        extracts.append(line.strip())
        else:
            pattern0 = re.compile(r"^(#|--) ")
            pattern1 = re.compile(r"^# %% ")
            pattern2 = re.compile(r"^## ")
            pattern3 = re.compile(r"^### ")
            pattern4 = re.compile(r"^#### ")
            pattern5 = re.compile(r"^##### ")
            pattern6 = re.compile(r"^###### ")
            pattern7 = re.compile(r"^#([^ ]+)")

            with open(unc, "r", encoding="utf-8", errors="ignore") as file:
                for line in file:
                    lines.append(line.strip())
                    if pattern1.match(line):
                        flags.append(1 + num_hashes)
                        extracts.append(pattern1.sub("", line).strip())
                    elif pattern2.match(line):
                        flags.append(2 + num_hashes)
                        extracts.append(pattern2.sub("", line).strip())
                    elif pattern3.match(line):
                        flags.append(3 + num_hashes)
                        extracts.append(pattern3.sub("", line).strip())
                    elif pattern4.match(line):
                        flags.append(4 + num_hashes)
                        extracts.append(pattern4.sub("", line).strip())
                    elif pattern5.match(line):
                        flags.append(5 + num_hashes)
                        extracts.append(pattern5.sub("", line).strip())
                    elif pattern6.match(line):
                        flags.append(6 + num_hashes)
                        extracts.append(pattern6.sub("", line).strip())
                    elif pattern7.match(line):
                        flags.append(999 + num_hashes)
                        extracts.append(pattern7.sub(r"\1", line).strip())
                    elif pattern0.match(line):
                        flags.append(-1)
                        extracts.append(pattern0.sub("", line).strip())
                    else:
                        flags.append(0)
                        extracts.append(line.strip())

        # Create a DataFrame
        df = pd.DataFrame({"line": lines, "flag": flags, "extract": extracts})

        # Create markdown
        df["hierarchy"] = np.where(
            (df["flag"].between(1, 15)), df["flag"].apply(lambda x: "#" * x), np.nan
        )
        df["hierarchy"] = np.where((df["flag"] == -1), "-", df["hierarchy"])
        df["md"] = np.where(
            (df["hierarchy"].isnull()), "", df["hierarchy"] + " " + df["extract"]
        )

        markdown_string = ""
        for i in df["md"]:
            if i != "":
                markdown_string = markdown_string + "\n" + i

        return markdown_string

    ## combine folder and file heading structure
    for i in range(0, len(output_dataframe)):
        if isfile(output_dataframe.loc[i, "unc"]):
            output_dataframe.loc[i, "file_md"] = scan_py_files_for_headings_modified(
                output_dataframe.loc[i, "unc"], output_dataframe.loc[i, "num_hashes"]
            )

    for i in range(0, len(output_dataframe)):
        base_string = (
            "#" * output_dataframe.loc[i, "num_hashes"]
            + " "
            + output_dataframe.loc[i, "formatted_structure"]
        )
        if pd.isna(output_dataframe.loc[i, "file_md"]):
            output_dataframe.loc[i, "md"] = base_string + "\n"
        else:
            output_dataframe.loc[i, "md"] = (
                base_string + "\n" + output_dataframe.loc[i, "file_md"] + "\n"
            )

    # create markdown
    markdown_statement = f"{md_name}\n"  # Add the md_name as the first line
    for i in output_dataframe["md"]:
        markdown_statement = markdown_statement + "\n" + str(i)

    # export
    def export_to_file(file_path, content):
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)

        # Open the file automatically
        try:
            os.startfile(file_path)
        except AttributeError:
            # For non-Windows systems
            subprocess.run(["open", file_path], check=True)

    output_file_path = str(unc).split("\\")[-1] + ".md"

    # formatted_structure = list_folder_structure(folder_path)
    export_to_file(output_file_path, markdown_statement)


if __name__ == "__main__":
    unc = Path("C:/my_disk/edupunk/src/functions")
    md_name_str = """---
    title: Project report
    markmap:
    colorFreezeLevel: 4
    maxWidth: 300
    embedAssets: true
    initialExpandLevel: 4
    ---"""
    scan_py_files_in_folders_for_headings(unc, md_name=md_name_str, heading_order=1)
