import zipfile
import os


def zip_files(file_list, destination_file):
    """
    Zips a list of files into a single zip file.

    Args:
        file_list (list): A list of file paths to zip.
        destination_file (str): The path to the destination zip file.
    """

    try:
        # Create a zip file
        with zipfile.ZipFile(destination_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add files to the zip file
            for file in file_list:
                if os.path.exists(file):
                    relative_path = os.path.relpath(file)
                    zip_file.write(file, relative_path)
                else:
                    print(f"File not found: {file}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    file_list = [
        "/path/to/file1.txt",
        "/path/to/folder/file2.txt",
        "/path/to/file3.pdf",
    ]
    destination_file = "/path/to/destination/zipfile.zip"

    zip_files(file_list, destination_file)
