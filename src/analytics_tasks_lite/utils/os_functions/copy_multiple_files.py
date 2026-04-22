import os
import shutil


def copy_multiple_files(source_files, destination):
    """
    Copies multiple files from different locations to a destination folder.

    Args:
        source_files (list): List of source file paths to copy
        destination_folder (str): Path to destination folder

    Returns:
        int: Number of files successfully copied
    """
    # Create destination folder if it doesn't exist
    os.makedirs(destination, exist_ok=True)

    copied_count = 0

    for source_file in source_files:
        try:
            # Get the base filename
            filename = os.path.basename(source_file)
            destination_path = os.path.join(destination, filename)

            # Copy file (this will overwrite if exists)
            shutil.copy2(source_file, destination_path)
            copied_count += 1
            print(f"Copied: {source_file} -> {destination_path}")

        except Exception as e:
            print(f"Error copying {source_file}: {str(e)}")

    return copied_count
