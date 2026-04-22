from pathlib import Path
import pandas as pd
import os
import glob
import os.path


def scan_dir(location_to_scan, ext=None):
    scan = []
    if ext:
        for i in glob.iglob(
            rf"{location_to_scan}\**\*{ext}".format(ext=ext), recursive=True
        ):
            scan.append(i)
    else:
        for i in glob.iglob(rf"{location_to_scan}\**\*.*", recursive=True):
            scan.append(i)

    if len(scan) > 0:
        scan = pd.DataFrame(scan).rename(columns={0: "unc"})
        scan["filename"] = scan["unc"].apply(lambda row: Path(row).name)
        scan["ext"] = scan["unc"].apply(
            lambda row: os.path.splitext(os.path.basename(row))[1]
        )
        scan["chart_hash"] = scan.filename.str.rsplit(".", expand=True, n=1)[0]
    else:
        scan = pd.DataFrame({"filename": ""}, index=[0])

    return scan


if __name__ == "__main__":
    # Scan for all files with .txt extension
    scan_txt = scan_dir("C:\\path\\to\\scan", ext=".txt")

    # Scan for all files with any extension
    scan_all = scan_dir("C:\\path\\to\\scan")
