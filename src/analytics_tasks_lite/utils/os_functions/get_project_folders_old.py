from pathlib import Path


def get_project_folders(
    root_markers=(".github_root",),
    project_markers=("*.code-workspace",),
    calling_file=None,
    debug=False
):
    """
    Locate the GitHub root folder and the current project folder.

    Walks up the directory tree from the script location (or cwd in
    interactive mode) to find:
    - root_folder : The GitHub root directory (contains root marker)
    - project_folder: The immediate project directory (contains .code-workspace)

    Parameters
    ----------
    root_markers : tuple
        Files or folders identifying the GitHub root directory.
        Must not be empty.
    project_markers : tuple
        Files or folders identifying the project root directory.
        Supports glob patterns e.g. ("*.code-workspace",)
        Must not be empty.
    calling_file : str or Path, optional
        Only needed when using exec() to load this function.
        In script mode pass __file__.
        In interactive mode pass Path.cwd().
        Once imported as a package, this is handled automatically.
    debug : bool
        If True, prints each directory checked during the walk.

    Returns
    -------
    dict with keys:
        'root_folder' : Path to GitHub root
        'project_folder' : Path to current project

    Raises
    ------
    ValueError
        If root_markers or project_markers are empty.
        If project folder is not inside root folder or equal to it.
    FileNotFoundError
        If either root or project markers cannot be found.

    Examples
    --------
    # exec() stage - interactive mode
    >>> folders = get_project_folders(calling_file=Path.cwd())

    # exec() stage - script mode
    >>> folders = get_project_folders(calling_file=__file__)

    # package import stage (future) - both modes handled automatically
    >>> folders = get_project_folders()
    """

    # Validate inputs early - before anything else runs
    if not root_markers:
        raise ValueError(
            "root_markers cannot be empty.\n"
            "Tip: Pass at least one marker e.g. root_markers=('.github_root',)"
        )

    if not project_markers:
        raise ValueError(
            "project_markers cannot be empty.\n"
            "Tip: Pass at least one marker e.g. project_markers=('.code-workspace',)"
        )

    # Helper: check if any marker exists in a directory
    # Supports both exact filenames and glob patterns
    def marker_exists(directory, markers):
        for marker in markers:
            if list(directory.glob(marker)):  # glob e.g. *.code-workspace
                return True
            if (directory / marker).exists():  # exact match fallback
                return True
        return False

    # -----------------------------------------
    # Determine start path
    # Strict priority: calling_file > __file__ > cwd
    # cwd is only used as last resort to avoid picking up unrelated
    # deep directories as the search starting point
    # -----------------------------------------
    if calling_file is not None:
        # Explicit anchor - highest priority
        p = Path(calling_file).resolve()
        start_path = p if p.is_dir() else p.parent

    else:
        try:
            # Script or package import mode
            start_path = Path(__file__).resolve().parent
        except NameError:
            # Interactive mode - cwd is only fallback
            start_path = Path.cwd()

    if debug:
        print(f"[DEBUG] Start path : {start_path}")

    # -----------------------------------------
    # Walk up to find both markers, starting from start_path itself
    # -----------------------------------------
    root_folder = None
    project_folder = None

    current = start_path
    while True:
        if debug:
            print(f"[DEBUG] Checking : {current}")

        if project_folder is None:
            if marker_exists(current, project_markers):
                project_folder = current
                if debug:
                    print(f"[DEBUG] project_folder : {project_folder}")

        if root_folder is None:
            if marker_exists(current, root_markers):
                root_folder = current
                if debug:
                    print(f"[DEBUG] root_folder : {root_folder}")

        if root_folder and project_folder:
            break

        parent = current.parent
        if parent == current:
            break
        current = parent

    # -----------------------------------------
    # Validation
    # -----------------------------------------
    if root_folder is None:
        raise FileNotFoundError(
            f"Could not find GitHub root folder.\n"
            f"Markers searched : {root_markers}\n"
            f"Search started from : {start_path}\n"
            f"Tip: Place a '{root_markers[0]}' file in your GitHub root folder."
        )

    if project_folder is None:
        raise FileNotFoundError(
            f"Could not find project folder.\n"
            f"Markers searched : {project_markers}\n"
            f"Search started from : {start_path}\n"
            f"Tip: Ensure a '{project_markers[0]}' file exists in your project root."
        )

    # Allow equality (root == project) for single project setups
    if root_folder != project_folder and root_folder not in project_folder.parents:
        raise ValueError(
            f"Project folder '{project_folder}' is not inside "
            f"root folder '{root_folder}'.\n"
            f"Check your marker file placements."
        )

    return {
        "root_folder": root_folder,
        "project_folder": project_folder
    }


# Convenience wrappers
def get_root_folder(calling_file=None, **kwargs):
    return get_project_folders(calling_file=calling_file, **kwargs)["root_folder"]


def get_project_folder(calling_file=None, **kwargs):
    return get_project_folders(calling_file=calling_file, **kwargs)["project_folder"]