# %% Assign working directories v1

## Dependencies
from pathlib import Path
import sys
import os


def assign_rd_v1(code_folder_exists=1, base_level=None, file_path=None):
    """
    Assigns root directory, file folder, and file reference paths.

    Parameters:
    -----------
    code_folder_exists : int, default=1
        1 if project has a 'code' folder, 0 otherwise
    base_level : int, optional
        Number of levels to go up from file location before processing
    file_path : str or Path, optional
        Explicit file path. REQUIRED when running in interactive mode (IPython/Jupyter).
        Auto-detected when running as a script.

    Returns:
    --------
    tuple : (rf, ff, fr, rfo, rfi, rfir)
        rf : Path to root folder
        ff : Path to file folder (where running file exists)
        fr : Full path of running file without extension
        rfo : Path to root folder output (rf/output) - None if code_folder_exists=0
        rfi : Path to root folder input (rf/input) - None if code_folder_exists=0
        rfir : Path to root folder input reference (rf/input/reference) - None if code_folder_exists=0
    """

    import inspect

    # Check if we're in interactive mode
    in_interactive_mode = (
        hasattr(sys, "ps1")
        or "IPython" in sys.modules
        or "ipykernel" in sys.modules
        or "SPYDER" in os.environ
    )

    # Also check if the immediate caller is <stdin>
    try:
        frame = sys._getframe(1)
        caller_file = frame.f_code.co_filename
        if caller_file in ("<stdin>", "<console>", "<input>", "<string>"):
            in_interactive_mode = True
    except:
        pass

    # If in interactive mode and file_path not provided, raise error
    if in_interactive_mode and file_path is None:
        raise ValueError(
            "Interactive mode detected. You must specify 'file_path' parameter to avoid "
            "accidental file overwrites.\n"
            "Example: assign_rd(code_folder_exists=0, base_level=0, "
            "file_path=r'C:\\path\\to\\your\\file.py')"
        )

    detected_file_path = None

    # If file_path explicitly provided, use it
    if file_path is not None:
        detected_file_path = Path(file_path).resolve()
        if not detected_file_path.exists():
            raise ValueError(f"Specified file_path does not exist: {file_path}")
        if detected_file_path.suffix != ".py":
            raise ValueError(f"Specified file_path must be a .py file: {file_path}")
    else:
        # Auto-detect from frames (script mode only at this point)
        try:
            # Get this function's file location
            this_file = Path(__file__).resolve()

            # Try to find the calling file by walking up frames
            frame_depth = 1
            while frame_depth < 20:
                try:
                    frame = sys._getframe(frame_depth)
                    caller_file = frame.f_code.co_filename

                    # Skip special files
                    if caller_file in (
                        "<stdin>",
                        "<console>",
                        "<input>",
                        "<string>",
                        "<frozen importlib._bootstrap>",
                        "<frozen importlib._bootstrap_external>",
                    ):
                        frame_depth += 1
                        continue

                    caller_path = Path(caller_file).resolve()

                    # Skip if it's this file itself
                    if caller_path == this_file:
                        frame_depth += 1
                        continue

                    # Check if it's a real Python file that exists
                    if caller_path.exists() and caller_path.suffix == ".py":
                        detected_file_path = caller_path
                        break

                except ValueError:
                    # No more frames
                    break

                frame_depth += 1

        except Exception as e:
            pass

        # If still no file detected in script mode, raise error
        if detected_file_path is None:
            raise ValueError(
                "Could not auto-detect the calling script file. "
                "Please specify 'file_path' parameter explicitly."
            )

    # Set ff (file folder)
    ff = detected_file_path.parent

    # Set fr (file reference - full path without extension)
    fr = detected_file_path.with_suffix("")

    # Determine rf (root folder)
    if code_folder_exists == 1:
        # Determine starting point for search
        if base_level is not None:
            # Go up base_level levels first
            search_start = ff
            for _ in range(base_level):
                search_start = search_start.parent
        else:
            search_start = ff

        # Search upward for directory containing 'code' folder
        current = search_start
        rf = None
        max_levels = 10

        for level in range(max_levels + 1):
            # Check if current directory contains a 'code' folder (case-insensitive)
            code_folder_found = False
            try:
                for item in current.iterdir():
                    if item.is_dir() and item.name.lower() == "code":
                        code_folder_found = True
                        break
            except (PermissionError, OSError):
                pass

            if code_folder_found:
                rf = current
                break

            # Move up one level
            parent = current.parent
            if parent == current:  # Reached filesystem root
                break
            current = parent

        if rf is None:
            raise ValueError(
                f"Could not find a 'code' folder within {max_levels} levels "
                f"searching upward from: {search_start}\n"
                f"Please verify your project structure or adjust parameters."
            )

    else:  # code_folder_exists == 0
        # Use base_level to determine rf
        if base_level is None:
            base_level = 0

        rf = ff
        for _ in range(base_level):
            rf = rf.parent

    # Set additional folder paths only if code_folder_exists == 1
    if code_folder_exists == 1:
        rfo = rf / "output"
        rfi = rf / "input"
        rfir = rf / "input" / "reference"
    else:
        rfo = None
        rfi = None
        rfir = None

    # Convert to forward slash strings
    rf = rf.as_posix()
    ff = ff.as_posix()
    fr = fr.as_posix()

    if code_folder_exists == 1:
        rfo = rfo.as_posix()
        rfi = rfi.as_posix()
        rfir = rfir.as_posix()

    # Print assigned paths for verification
    if code_folder_exists == 1:
        print("✔️  Assigned paths:")
        print(f"  rf (root folder):              {rf}")
        print(f"  ff (file folder):              {ff}")
        print(f"  fr (file reference):           {fr}")
        print(f"  rfo (root folder output):      {rfo}")
        print(f"  rfi (root folder input):       {rfi}")
        print(f"  rfir (root folder input ref):  {rfir}")
    else:
        print(
            "✔️  Assigned paths (rfo, rfi, rfir not included as code_folder_exists=0):"
        )
        print(f"  rf (root folder):              {rf}")
        print(f"  ff (file folder):              {ff}")
        print(f"  fr (file reference):           {fr}")

    return rf, ff, fr, rfo, rfi, rfir


if __name__ == "__main__":
    # Interactive mode
    rf, ff, fr, rfo, rfi, rfir = assign_rd_v1(
        code_folder_exists=0,
        base_level=1,
        file_path=r"C:\my_disk\projects\visual_library\line\draggable.py",
    )

    # Script mode (auto-detects)
    rf, ff, fr, rfo, rfi, rfir = assign_rd_v1(code_folder_exists=0, base_level=1)
