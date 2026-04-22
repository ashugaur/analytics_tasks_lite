import os
from datetime import datetime
import re


def get_latest_file(directory, start_string, ext):
    try:
        # Get a list of files with the prefix 'explore'
        files = [
            f
            for f in os.listdir(directory)
            if f.startswith(start_string) and f.endswith(ext)
        ]

        if not files:
            print("No files found with the prefix 'explore' and .xlsm extension.")
            return None

        # Parse the timestamp from each filename and find the latest one
        latest_file = max(
            files,
            key=lambda f: datetime.strptime(
                re.search(r"\d{8}_\d{4}", f).group(), "%Y%m%d_%H%M"
            ),
        )

        return os.path.join(directory, latest_file)

    except FileNotFoundError:
        print(f"Directory '{directory}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
