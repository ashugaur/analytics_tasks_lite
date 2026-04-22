import zipfile
import os
from datetime import datetime


def export_folder_as_zip_timestamp(
    source_folder, destination_folder, exclude_folder_names=None
):
    if exclude_folder_names is None:
        exclude_folder_names = []

    now = datetime.now()
    folder_dt = (
        "{:02d}".format(now.year)
        + "{:02d}".format(now.month)
        + "{:02d}".format(now.day)
    )
    file_dt = (
        "{:02d}".format(now.year)
        + "{:02d}".format(now.month)
        + "{:02d}".format(now.day)
        + "_"
        + "{:02d}".format(now.hour)
        + "{:02d}".format(now.minute)
    )

    os.chdir(destination_folder)

    output_filename = str(source_folder).rsplit("\\")[-1] + "_" + file_dt + ".zip"
    zf = zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED)

    for dirname, subdirs, files in os.walk(source_folder):
        # Check if current directory or any parent directory should be excluded
        relative_path = os.path.relpath(dirname, source_folder)
        path_parts = relative_path.split(os.sep)

        # Skip if any part of the path matches excluded folder names
        if any(part in exclude_folder_names for part in path_parts):
            subdirs.clear()  # Don't traverse subdirectories of excluded folders
            continue

        # Also check the folder name itself
        folder_name = os.path.basename(dirname)
        if folder_name in exclude_folder_names:
            subdirs.clear()  # Don't traverse subdirectories of excluded folders
            continue

        zf.write(dirname)
        for filename in files:
            zf.write(os.path.join(dirname, filename))

    zf.close()
