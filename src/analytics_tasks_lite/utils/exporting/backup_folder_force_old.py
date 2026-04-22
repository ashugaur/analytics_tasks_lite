import os
import shutil


def backup_folder_force_old(source_folder, destination_folder):
    try:
        # Delete the destination folder if it exists
        if os.path.exists(destination_folder):
            shutil.rmtree(destination_folder)

        # Copy the source folder to the destination
        shutil.copytree(source_folder, destination_folder)
        # print(f"\nFolder '{source_folder}'\n\tcopied to \n\t'{destination_folder}' successfully.")
    except shutil.Error as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
