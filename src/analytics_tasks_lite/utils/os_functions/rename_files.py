import os


def rename_files(folder_path, prefix=None, suffix=None):
    """Rename files in a folder"""
    # List all files in the folder
    files = os.listdir(folder_path)

    # Iterate through each file
    for file_name in files:
        # Construct the new file name with prefix and/or suffix
        new_name = ""

        if prefix:
            new_name += prefix

        new_name += file_name

        if suffix:
            new_name += suffix

        # Create the full paths for old and new file names
        old_path = os.path.join(folder_path, file_name)
        new_path = os.path.join(folder_path, new_name)

        # Rename the file
        os.rename(old_path, new_path)
        print(f"Renamed: {file_name} -> {new_name}")


if __name__ == "__main__":
    folder_path = "/path/to/your/folder"
    prefix = "new_"
    suffix = "_v1"

    rename_files(r"C:\Users\Ashut\Downloads", prefix=prefix)
