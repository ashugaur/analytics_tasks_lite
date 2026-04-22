import os
import json
from pathlib import Path
from datetime import datetime

def folder_cypher(folder_path, cypher='.txt', decypher=False):
    """
    Function to rename all file extensions in a folder to a specified extension,
    handling duplicate filenames, with ability to restore original names.

    Args:
        folder_path (str): Path to the folder to process
        cypher (str): Extension to rename files to (default: '.txt')
        decypher (bool): If True, restore original filenames (default: False)
    """
    folder = Path(folder_path)
    log_file = folder / 'rename_log.json'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not folder.exists():
        raise ValueError(f"Folder {folder_path} does not exist")

    if decypher:
        # Restore original filenames
        if not log_file.exists():
            raise FileNotFoundError("No rename log file found to decypher")

        with open(log_file, 'r') as f:
            rename_data = json.load(f)

        # Restore in reverse order to handle potential conflicts
        for entry in reversed(rename_data):
            current_path = folder / entry['new_name']
            original_path = folder / entry['original_name']

            if current_path.exists():
                try:
                    current_path.rename(original_path)
                    print(f"Restored: {entry['new_name']} -> {entry['original_name']}")
                except OSError as e:
                    print(f"Error restoring {entry['new_name']}: {e}")

    else:
        # Rename files and create log
        rename_data = []
        name_counter = {}  # Track duplicates: base_name -> count

        # First pass: collect all files and count duplicates
        for root, _, files in os.walk(folder):
            for filename in files:
                if filename == 'rename_log.json':
                    continue

                old_path = Path(root) / filename
                rel_path = old_path.relative_to(folder)
                base_name = str(rel_path.with_suffix(''))

                # Count occurrences of each base name
                name_counter[base_name] = name_counter.get(base_name, 0) + 1

        # Second pass: rename with unique identifiers for duplicates
        for root, _, files in os.walk(folder):
            for filename in files:
                if filename == 'rename_log.json':
                    continue

                old_path = Path(root) / filename
                rel_path = old_path.relative_to(folder)
                base_name = str(rel_path.with_suffix(''))

                # Handle duplicates by adding a unique identifier
                if name_counter[base_name] > 1:
                    counter = name_counter[base_name]
                    name_counter[base_name] -= 1  # Decrease counter as we process
                    unique_name = f"{base_name}_{counter}_{timestamp}{cypher}"
                else:
                    unique_name = f"{base_name}{cypher}"

                new_path = folder / unique_name

                try:
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    old_path.rename(new_path)
                    rename_data.append({
                        'original_name': str(rel_path),
                        'new_name': unique_name
                    })
                    print(f"Renamed: {filename} -> {unique_name}")
                except OSError as e:
                    print(f"Error renaming {filename}: {e}")

        # Save the rename data to log file
        with open(log_file, 'w') as f:
            json.dump(rename_data, f, indent=4)
        print(f"Log file created at: {log_file}")

if __name__ == "__main__":
    # To rename all files
    # folder_cypher(r"C:\Users\ashut\Downloads\flow")

    # To restore original filenames
    # folder_cypher(r"C:\Users\ashut\Downloads\flow", decypher=True)
    pass
