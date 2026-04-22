import pandas as pd
import numpy as np
import pathlib
from pathlib import Path
import os
import glob
import shutil
import os.path


def scan_dir_to_markdown(_source, _destination):
    """
    Parse a folder containing files and convert them to markdown documents.

    Parameters:
    _source (str): Source directory path
    _destination (str): Destination directory path for markdown output
    """
    global scan, scan_md

    os.chdir(_destination)

    _relevant_file_type = [".R", ".bat", ".txt", ".sql", ".Rmd", ".py", ".ps1"]

    # remove folder
    os.system('rmdir /S /Q "{}"'.format(_destination / str(_source).split("\\")[-1]))

    # create folder
    pathlib.Path(str(_source).split("/")[-1]).mkdir(parents=True, exist_ok=True)

    # scan folder
    def scan_dir(location_to_scan):
        global scan
        scan = []
        for i in glob.iglob(rf"{location_to_scan}\**\*", recursive=True):
            scan.append(i)
        if len(scan) > 0:
            scan = pd.DataFrame(scan).rename(columns={0: "unc"})
            scan["filename"] = scan["unc"].apply(lambda row: Path(row).name)
            scan["ext"] = scan["unc"].apply(
                lambda row: os.path.splitext(os.path.basename(row))[1]
            )
        else:
            scan = pd.DataFrame({"filename": ""}, index=([0]))

    scan_dir(_source)

    # Filter rows with extensions .ipynb and .py
    relevant_files = scan[scan["ext"].isin([".ipynb", ".py"])].copy()

    # Extract the base filenames (without extensions)
    relevant_files["base_filename"] = relevant_files["filename"].str.replace(
        r"\.ipynb|\.py", "", regex=True
    )

    # Identify base filenames that have both .ipynb and .py extensions
    duplicate_bases = (
        relevant_files.groupby("base_filename")["ext"]
        .apply(lambda x: set(x))
        .reset_index()
    )

    # Filter for base filenames with both .ipynb and .py extensions
    duplicate_bases = duplicate_bases[
        duplicate_bases["ext"].apply(lambda x: {".ipynb", ".py"}.issubset(x))
    ]["base_filename"]
    print(
        f"REPORT: Count of duplicate .py and .ipynb files ignored...{len(duplicate_bases)}"
    )

    # Remove .py files for these duplicate base filenames
    scan = scan[
        ~(
            (scan["ext"] == ".py")
            & (
                scan["filename"]
                .str.replace(r"\.py", "", regex=True)
                .isin(duplicate_bases)
            )
        )
    ]
    scan = scan.reset_index(drop=True)

    # flag files and folders
    scan["dir_flag"] = False
    scan["file_flag"] = False

    for i in range(0, len(scan)):
        _unc = scan.loc[i, "unc"]
        if os.path.exists(_unc):
            scan.loc[i, "dir_flag"] = os.path.isdir(_unc)
            scan.loc[i, "file_flag"] = os.path.isfile(_unc)

    # dir depth
    scan["unc"] = scan["unc"].str.replace("\\", "/")
    scan["depth"] = scan["unc"].str.count("/") - str(_source).count("\\") - 1

    # Extract folder structure information
    scan["folder_path"] = scan["unc"].str.rsplit("/", expand=True, n=1)[0]

    # Create a dictionary to track which folders have files and which have subfolders
    folder_contains = {}

    # Initialize with empty sets
    for folder in scan["folder_path"].unique():
        folder_contains[folder] = {"files": False, "folders": False}

    # Mark folders that contain direct files
    for i, row in scan[scan["file_flag"]].iterrows():
        folder_contains[row["folder_path"]]["files"] = True

    # Mark folders that contain subfolders
    for folder in folder_contains:
        parent_folders = [
            p
            for p in folder_contains.keys()
            if folder.startswith(p + "/") and p != folder
        ]
        for parent in parent_folders:
            folder_contains[parent]["folders"] = True

    # Find folders that have both files and subfolders
    mixed_folders = [
        folder
        for folder, content in folder_contains.items()
        if content["files"] and content["folders"]
    ]

    print(f"REPORT: Folders with both files and subfolders: {len(mixed_folders)}")

    # Flag files that should be converted to index.md
    scan["in_mixed_folder"] = scan["folder_path"].isin(mixed_folders)

    # Create a helper column to indicate if a file is in a mixed folder
    scan["make_index"] = scan["in_mixed_folder"] & scan["file_flag"]

    # Calculate destination markdown path
    scan["_unc_md"] = np.where(
        scan["make_index"],  # Files in mixed folders become index.md
        scan["folder_path"].str.replace(
            "/".join(str(_source).split("\\")[:-1]),
            str(_destination).replace("\\", "/"),
        )
        + "/index.md",
        np.where(
            (scan["depth"] == 2),  # Top-level files become index.md
            scan["unc"]
            .str.rsplit("/", expand=True, n=1)[0]
            .str.replace(
                "/".join(str(_source).split("\\")[:-1]),
                str(_destination).replace("\\", "/"),
            )
            + "/index.md",
            # Other files get their own markdown
            scan["unc"]
            .str.rsplit("/", expand=True, n=1)[0]
            .str.replace(
                "/".join(str(_source).split("\\")[:-1]),
                str(_destination).replace("\\", "/"),
            )
            + ".md",
        ),
    )

    scan["unc_l1"] = np.where(
        (scan["depth"] == 2),
        scan["unc"]
        .str.rsplit("/", expand=True, n=1)[0]
        .str.replace(
            "/".join(str(_source).split("\\")[:-1]),
            str(_destination).replace("\\", "/"),
        ),
        scan["unc"]
        .str.rsplit("/", expand=True, n=2)[0]
        .str.replace(
            "/".join(str(_source).split("\\")[:-1]),
            str(_destination).replace("\\", "/"),
        ),
    )

    scan["_unc_img"] = scan["unc"].str.replace(
        "/".join(str(_source).split("\\")[:-1]), str(_destination).replace("\\", "/")
    )

    # Create all necessary directories first
    all_dirs = set()

    # Add all folder paths that need to be created
    for md_path in scan["_unc_md"].unique():
        dir_path = os.path.dirname(md_path)
        all_dirs.add(dir_path)

    # Create directories
    for dir_path in all_dirs:
        os.makedirs(dir_path, exist_ok=True)

    # copy markdowns
    scan_md = scan[scan["ext"] == ".md"]
    scan_md = scan_md[
        ~scan_md["unc"].str.contains("projects", case=False, na=False, regex=True)
    ].reset_index(drop=True)

    # copy .ipynb
    scan_ipynb = scan[scan["ext"] == ".ipynb"]

    # identify image folders
    scan_img = scan[
        (scan["dir_flag"]) & (scan["unc"].str.rsplit("/", expand=True, n=1)[1] == "img")
    ].reset_index(drop=True)

    # exceptions
    scan = scan[
        ~scan["unc"].str.contains("visual_library", case=False, na=False, regex=True)
    ].reset_index(drop=True)
    scan = scan[
        ~scan["unc"].str.contains(
            "edupunk_open_internet", case=False, na=False, regex=True
        )
    ]
    scan = scan[~scan["unc"].str.contains("projects", case=False, na=False, regex=True)]
    scan = scan[~scan["unc"].str.contains("python", case=False, na=False, regex=True)]

    # filter relevant unc
    scan = scan[scan["file_flag"]]
    scan = scan[scan["ext"].isin(_relevant_file_type)].reset_index(drop=True)

    # write markdown
    select = (
        scan[["unc", "_unc_md", "filename", "ext"]]
        .sort_values(["_unc_md", "filename"])
        .reset_index(drop=True)
    )
    select["_filename"] = select["filename"].str.rsplit(".", expand=True, n=1)[0]

    for _topic in select["_unc_md"].unique().tolist():
        _td = select[select["_unc_md"] == _topic].reset_index(drop=True)
        _file = _td["_unc_md"].unique()[0]
        _filemd = os.path.basename(_file).rsplit(".")[0]

        # Get the directory name (for index files)
        _dir_path = os.path.dirname(_file)

        # Ensure directory exists before writing to file
        os.makedirs(_dir_path, exist_ok=True)

        _filemd1 = os.path.basename(_dir_path)

        with open(_file, "w", encoding="utf-8") as f:
            if "index" == _filemd:
                f.write("# " + _filemd1.lower() + "\n\n")
            else:
                f.write("# " + _filemd.lower() + "\n\n")

            for unc, _unc_md, filename, ext, _filename in _td.itertuples(index=False):
                _ext = ext.split(".")[1]

                if "automated_function_scan" in unc.lower():
                    filename_mdx = str(
                        filename.split("__")[1] if "__" in filename else filename
                    )
                    f.write("??? " + "null" + ' "' + filename_mdx + '"\n\n')
                    f.write("\t```" + ext + ' linenums="1"' + "\n")
                else:
                    # Handle file names that don't have '__' in them
                    if "__" in filename:
                        filename_mdx = str(filename.split("__")[0])
                    else:
                        filename_mdx = filename
                    f.write("??? " + "null" + ' "' + filename_mdx + '"\n\n')
                    f.write("\t```" + ext + ' linenums="1"' + "\n")

                _sql_str = ""
                try:
                    with open(unc, "r", encoding="utf-8", errors="replace") as j:
                        content = j.readlines()
                        for _sql_substrx in content:
                            _sql_str = _sql_str + "\t" + _sql_substrx
                except Exception as e:
                    print(f"Error reading file {unc}: {e}")
                    _sql_str = f"\tError reading file: {e}"

                f.write(_sql_str + "\n")
                f.write("\t```" + "\n\n")

    # copy .md files as is
    scan_md = scan_md.reset_index(drop=True)
    scan_md["copy_md"] = (
        (scan_md["unc"].str.rsplit("/", expand=True, n=1)[0]).str.replace(
            "/".join(str(_source).split("\\")[:-1]),
            str(_destination).replace("\\", "/"),
        )
        + "/"
        + scan_md["filename"]
    )

    for i in range(0, len(scan_md)):
        __source = scan_md.loc[i, "unc"]
        __destination = scan_md.loc[i, "copy_md"]

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(__destination), exist_ok=True)

        try:
            shutil.copy(__source, __destination)
        except Exception as e:
            print(f"Error copying markdown file {__source} to {__destination}: {e}")

    # copy img folder as is
    for i in range(0, len(scan_img)):
        __source = scan_img.loc[i, "unc"]
        __destination = scan_img.loc[i, "_unc_img"]
        try:
            backup_folder_force_md(__source, __destination)
        except Exception as e:
            print(f"Error copying folder {__source} to {__destination}: {e}")


def backup_folder_force_md(source_folder, destination_folder):
    """Copy contents of source folder to destination folder"""
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    for item in os.listdir(source_folder):
        s = os.path.join(source_folder, item)
        d = os.path.join(destination_folder, item)
        if os.path.isdir(s):
            backup_folder_force_md(s, d)
        else:
            shutil.copy2(s, d)

