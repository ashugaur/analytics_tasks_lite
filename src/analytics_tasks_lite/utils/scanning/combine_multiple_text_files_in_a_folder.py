import pandas as pd
from pathlib import Path
import os.path
from datetime import datetime
import subprocess
import os


def combine_multiple_text_files_in_a_folder(folder_path):
    """
    Combines multiple text files from a folder into an Excel file.

    Args:
        folder_path (str): Path to the folder containing text files
    """

    now = datetime.now()
    file_dt = (
        "{:02d}".format(now.year)
        + "{:02d}".format(now.month)
        + "{:02d}".format(now.day)
        + "_"
        + "{:02d}".format(now.hour)
        + "{:02d}".format(now.minute)
    )

    # Scan folder for files
    scan = []
    with os.scandir(folder_path) as it:
        for entry in it:
            if entry.is_file():
                filepath = entry.path  # absolute path
                scan.append(filepath)

    if not scan:
        print("No files found in the specified folder.")
        return

    scan = pd.DataFrame(scan).rename(columns={0: "unc"})

    # Get filename
    scan["filename"] = scan["unc"].apply(lambda row: Path(row).name)

    # Get extension
    scan["ext"] = scan["unc"].apply(
        lambda row: os.path.splitext(os.path.basename(row))[1]
    )

    # Filter for specific file types
    scan = scan[
        scan["ext"].isin([".R", ".sas", ".bat", ".sql", ".py", ".md", ".txt", ""])
    ]

    if scan.empty:
        print("No files with supported extensions found.")
        return

    # Import & clean text files
    lines_ = {}
    scanl = len(scan)

    print(f"Processing {scanl} files...")

    # Process files with simple progress tracking
    for i, (unc, filename, ext) in enumerate(scan.itertuples(index=False), 1):
        print(f"\n{i} of {scanl}")
        print("READING: " + unc)

        if os.path.exists(unc):
            try:
                # Try UTF-8 first
                with open(unc, encoding="utf-8", errors="ignore") as f:
                    listx = f.readlines()
            except UnicodeDecodeError:
                try:
                    print("Error reading file with UTF-8, trying UTF-16")
                    with open(unc, encoding="utf-16", errors="ignore") as f:
                        listx = f.readlines()  # Fixed typo: was "readliness()"
                except Exception as e:
                    print(f"Error reading file {unc}: {e}")
                    continue
            except Exception as e:
                print(f"Error reading file {unc}: {e}")
                continue

            lines_[unc] = listx
        else:
            print(f"File does not exist: {unc}")
            continue

    if not lines_:
        print("No files were successfully read.")
        return

    # Convert dictionary of lists to dataframe
    lines = []
    for k, v in lines_.items():
        if k != "":
            # Add header row for each file
            lines.append([k, None])  # File header
            for i, val in enumerate(v, 1):
                lines.append([k, val])
        else:
            continue

    # Convert to dataframe
    lines = pd.DataFrame(lines, columns=["unc", "lines"])

    # Clean newlines
    lines["lines"] = lines["lines"].astype(str).str.replace("\n", "", regex=True)

    lines = lines.reset_index().rename(columns={"index": "sn_"})
    lines["sn"] = lines.groupby("unc")["sn_"].rank("first", ascending=True)
    lines["filename"] = lines["unc"].apply(lambda row: Path(row).name)  # filename
    lines["ext"] = lines["unc"].apply(
        lambda row: os.path.splitext(os.path.basename(row))[1]
    )  # extension
    lines = lines[["unc", "filename", "ext", "sn", "lines"]]

    # Export to Excel
    xlf = "combined_txt_files" + "_" + file_dt + ".xlsx"  # export file name
    xlf_open = "explorer " + '"' + xlf + '"'

    try:
        writer = pd.ExcelWriter(xlf, engine="xlsxwriter")

        workbook = writer.book
        worksheet = workbook.add_worksheet("readme")  # new sheet

        worksheet.set_zoom(90)
        worksheet.set_column("A:A", 7)
        worksheet.set_column("B:B", 50)

        worksheet.write(0, 0, "Tab")  # (row, column)
        worksheet.write(0, 1, "Comments")
        worksheet.write(1, 0, "lines")
        worksheet.write(1, 1, "Table of all lines imported by filename")

        # Write main data
        lines.to_excel(writer, "lines", index=False, freeze_panes=(1, 0))
        workbook = writer.book
        worksheet = writer.sheets["lines"]
        worksheet.set_zoom(90)
        worksheet.set_column("A:A", 10)
        worksheet.set_column("B:B", 28)
        worksheet.set_column("C:C", 10)
        worksheet.set_column("D:D", 7)
        worksheet.set_column("E:E", 100)
        worksheet.autofilter("A1:E1")

        writer.close()  # Use close() instead of _save()

        print(f"Successfully created: {xlf}")

        # Try to open the file (Windows specific)
        try:
            subprocess.Popen(xlf_open, shell=True)
        except Exception as e:
            print(f"Could not auto-open file: {e}")
            print(f"Please manually open: {xlf}")

    except Exception as e:
        print(f"Error creating Excel file: {e}")
