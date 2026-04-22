from pathlib import Path
import os


def get_downloads_folder():
    """
    Automatically runs to get the downloads folder directory.
    Run <_download> to know the folder path.
    """
    # Get the user's home directory
    home_dir = str(Path.home())

    # Check the common download folder names on different operating systems
    download_folders = ["Downloads", "My Documents", "Documents"]

    # Iterate through the possible download folders and return the first one that exists
    for folder in download_folders:
        downloads_path = os.path.join(home_dir, folder)
        if os.path.exists(downloads_path):
            return downloads_path

    # If none of the common folders exist, return the user's home directory
    return home_dir


if __name__ == "__main__":
    _download_dir = get_downloads_folder()
    print("\n_download_dir:", _download_dir)
