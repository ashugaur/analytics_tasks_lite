import os
import subprocess


def open_file_folder(path=None):
    if path is None:
        path = os.getcwd()

    try:
        # Try to rename the file/folder (will fail if open)
        os.rename(path, path)
        # If successful, open it
        subprocess.Popen(f'explorer "{path}"')
    except OSError:
        print(f"☑️  {path} is already open or in use!")
