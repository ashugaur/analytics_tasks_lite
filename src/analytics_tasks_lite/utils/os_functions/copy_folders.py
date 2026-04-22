import os
import shutil


def copy_folders(source, destination):
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
                if os.path.exists(d):
                    copy_folders(s, d)
                else:
                    shutil.copytree(s, d)
            else:
                # Copy files if they don't exist in the destination
                if not os.path.exists(d):
                    shutil.copy2(s, d)

        print(
            f"\ncopy_folders() does not overrite files.\nSuccessfully copied from {source} to {destination}."
        )
    except Exception as e:
        print(f"Error copying from {source} to {destination}: {e}")
