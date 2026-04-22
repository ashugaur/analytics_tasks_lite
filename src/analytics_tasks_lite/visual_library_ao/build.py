from pathlib import Path
import shutil
from analytics_tasks.utils.os_functions import copy_folders_no_overwrite

# import pkg_resources
import importlib.resources as pkg_resources


def lib_refs_vl(at_dir):
    """Assigns working libraries inside visual_library dir."""
    visual_library_dir = at_dir / "visual_library"
    visual_library_file = at_dir / "visual_library/visual_library.html"

    Path(visual_library_dir).mkdir(parents=True, exist_ok=True)

    print("☑️  Assigned visual_library directories.")

    return visual_library_dir, visual_library_file



def copy_gallery_folder(destination_path):
    """
    Copy the gallery folder from the installed analytics_tasks package to a specified destination.

    Args:
        destination_path (str or Path): The destination directory where the gallery folder will be copied.
                                       The gallery folder will be created inside this directory.

    Returns:
        str: Path to the copied gallery folder

    Raises:
        FileNotFoundError: If the gallery folder cannot be found in the package
        PermissionError: If there are insufficient permissions to copy files
        OSError: If there are other filesystem-related errors
    """
    try:
        # Method 1: Using pkg_resources (recommended for older Python versions)
        try:
            # Get the path to the installed package
            package_path = pkg_resources.resource_filename(
                "analytics_tasks", "visual_library/gallery"
            )
        except Exception:
            # Method 2: Using importlib.resources (Python 3.9+) or direct import
            try:
                import analytics_tasks.visual_library_ao

                package_dir = Path(analytics_tasks.visual_library_ao.__file__).parent
                package_path = package_dir / "gallery"
            except Exception:
                # Method 3: Fallback using the package's __file__ attribute
                import analytics_tasks

                package_root = Path(analytics_tasks.__file__).parent
                package_path = package_root / "visual_library" / "gallery"

        # Convert to Path object for easier handling
        source_path = Path(package_path)
        dest_path = Path(destination_path)

        # Check if source gallery folder exists
        if not source_path.exists():
            raise FileNotFoundError(f"Gallery folder not found at: {source_path}")

        if not source_path.is_dir():
            raise FileNotFoundError(
                f"Gallery path exists but is not a directory: {source_path}"
            )

        # Create destination directory if it doesn't exist
        dest_path.mkdir(parents=True, exist_ok=True)

        # Define the target gallery path
        target_gallery_path = dest_path / "visual_library"

        # Copy the entire gallery folder without overwriting
        if target_gallery_path.exists():
            # If target exists, merge directories without overwriting files
            copy_folders_no_overwrite(source_path, target_gallery_path)
        else:
            # If target doesn't exist, use regular copytree
            shutil.copytree(source_path, target_gallery_path)

        print(f"✅ Gallery folder exists: {target_gallery_path}")
        return str(target_gallery_path)

    except Exception as e:
        print(f"❌  Gallery folder exists   NOT: {e}")
        raise


def copy_gallery_contents_only(destination_path):
    """
    Copy only the contents of the gallery folder (not the folder itself) to the destination.

    Args:
        destination_path (str or Path): The destination directory where gallery contents will be copied.

    Returns:
        str: Path to the destination directory
    """
    try:
        # Get the gallery folder path (same methods as above)
        try:
            package_path = pkg_resources.resource_filename(
                "analytics_tasks", "visual_library/gallery"
            )
        except Exception:
            try:
                import analytics_tasks.visual_library_ao

                package_dir = Path(analytics_tasks.visual_library_ao.__file__).parent
                package_path = package_dir / "gallery"
            except Exception:
                import analytics_tasks

                package_root = Path(analytics_tasks.__file__).parent
                package_path = package_root / "visual_library" / "gallery"

        source_path = Path(package_path)
        dest_path = Path(destination_path)

        # Check if source exists
        if not source_path.exists() or not source_path.is_dir():
            raise FileNotFoundError(f"Gallery folder not found at: {source_path}")

        # Create destination directory
        dest_path.mkdir(parents=True, exist_ok=True)

        # Copy all contents from gallery folder to destination
        for item in source_path.iterdir():
            if item.is_file():
                shutil.copy2(item, dest_path)
            elif item.is_dir():
                target_dir = dest_path / item.name
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(item, target_dir)

        print(f"Successfully copied gallery contents to: {dest_path}")
        return str(dest_path)

    except Exception as e:
        print(f"Error copying gallery contents: {e}")
        raise
