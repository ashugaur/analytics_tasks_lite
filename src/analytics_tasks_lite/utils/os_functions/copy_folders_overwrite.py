import os
import shutil


def copy_folders_overwrite(source, destination):
    try:
        # Ensure the destination directory exists
        if not os.path.exists(destination):
            os.makedirs(destination)

        # Copy each item from source to destination
        for item in os.listdir(source):
            s = os.path.join(source, item)
            d = os.path.join(destination, item)
            if os.path.isdir(s):
                # Recursively copy directories
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                # Copy files
                shutil.copy2(s, d)

        print(f"Successfully copied from {source} to {destination}")
    except Exception as e:
        print(f"Error copying from {source} to {destination}: {e}")
