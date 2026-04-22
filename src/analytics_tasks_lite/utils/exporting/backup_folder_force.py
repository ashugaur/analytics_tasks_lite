import os
import shutil


def backup_folder_force(source_folder, destination_folder, exclude_folders=None):
    """
    Copies the source folder to the destination, excluding specified folders.

    Args:
        source_folder (str): The path to the source folder.
        destination_folder (str): The path to the destination folder.
        exclude_folders (list, optional): A list of folder names to exclude. Defaults to None.
    """

    try:
        # Delete the destination folder if it exists
        if os.path.exists(destination_folder):
            shutil.rmtree(destination_folder)

        # Copy the source folder to the destination, excluding specified folders
        if exclude_folders is None:
            shutil.copytree(source_folder, destination_folder)
        else:
            shutil.copytree(
                source_folder,
                destination_folder,
                ignore=shutil.ignore_patterns(*exclude_folders),
            )

    except shutil.Error as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
