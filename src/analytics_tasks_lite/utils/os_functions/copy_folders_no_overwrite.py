from pathlib import Path
import shutil


def copy_folders_no_overwrite(src, dst):
    """
    Helper function to copy a directory tree without overwriting existing files.

    Args:
        src (Path): Source directory path
        dst (Path): Destination directory path
    """
    src = Path(src)
    dst = Path(dst)

    # Create destination directory if it doesn't exist
    dst.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        src_item = src / item.name
        dst_item = dst / item.name

        if item.is_file():
            # Only copy file if destination doesn't exist
            if not dst_item.exists():
                shutil.copy2(src_item, dst_item)
                print(f"✔️  Copied file: {item.name}")
            else:
                print(f"✔️  Skipped existing file: {item.name}")
        elif item.is_dir():
            # Recursively copy subdirectories
            copy_folders_no_overwrite(src_item, dst_item)
