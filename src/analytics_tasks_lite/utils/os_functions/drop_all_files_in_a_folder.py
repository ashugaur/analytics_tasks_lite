import os
import shutil


def drop_all_files_in_a_folder(unc, chmod_value=0o777):
    """
    Deletes all files and subdirectories within a given directory.

    Args:
        unc: Path to the directory to be emptied.
        chmod_value: Octal value for changing file/directory permissions before deletion.
                     Default is 0o777 (read, write, execute for all).

    Raises:
        OSError: If an error occurs during file or directory deletion.
    """

    for root, dirs, files in os.walk(unc, topdown=False):
        for f in files:
            file_path = os.path.join(root, f)
            try:
                os.chmod(file_path, chmod_value)
                os.remove(file_path)
            except OSError as e:
                print(f"Error deleting file {file_path}: {e}")

        for d in dirs:
            dir_path = os.path.join(root, d)
            try:
                os.chmod(dir_path, chmod_value)
                shutil.rmtree(dir_path)
            except OSError as e:
                print(f"Error deleting directory {dir_path}: {e}")


if __name__ == "__main__":
    try:
        drop_all_files_in_a_folder("path/to/your/folder")
    except OSError as e:
        print(f"Error deleting files: {e}")
