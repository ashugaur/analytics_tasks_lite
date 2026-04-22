def export_folder_as_zip_nfp(
    source_folder, destination_folder, exclude_folder_names=None
):
    import os
    import zipfile

    if exclude_folder_names is None:
        exclude_folder_names = []

    os.chdir(destination_folder)

    output_filename = str(source_folder).rsplit("\\")[-1] + ".zip"

    # Create zip file
    with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as zf:
        # Walk through the source folder
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

            # Add files to zip
            for filename in files:
                # Get the absolute path of the file
                absolute_path = os.path.join(dirname, filename)
                # Create arcname (path within the zip file)
                arcname = os.path.relpath(absolute_path, source_folder)

                # Write file to zip
                zf.write(absolute_path, arcname)
