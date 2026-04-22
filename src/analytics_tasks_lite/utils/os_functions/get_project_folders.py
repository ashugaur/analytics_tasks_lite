import inspect
from pathlib import Path

def get_project_folders(
    root_markers=(".github_root",),
    project_markers=("*.code-workspace",),
    calling_file=None,
    debug=False
):
    """
    Locates the GitHub root and project folder by walking up from the caller's location.
    """
    # 1. Determine start path dynamically
    if calling_file is not None:
        p = Path(calling_file).resolve()
        start_path = p if p.is_dir() else p.parent
    else:
        try:
            # Look at the caller's stack frame
            frame = inspect.stack()[1]
            module_path = frame.filename
            # Handle Interactive (Jupyter/IPython) vs Script mode
            if module_path == '<stdin>' or module_path.startswith('<ipython-input'):
                start_path = Path.cwd()
            else:
                start_path = Path(module_path).resolve().parent
        except Exception:
            start_path = Path.cwd()

    if debug:
        print(f"[DEBUG] Search starting at: {start_path}")

    # 2. Search Logic
    root_folder = None
    project_folder = None
    current = start_path

    while True:
        # Check Project Markers
        if project_folder is None:
            for m in project_markers:
                if any(current.glob(m)) or (current / m).exists():
                    project_folder = current
                    break
        
        # Check Root Markers
        if root_folder is None:
            for m in root_markers:
                if any(current.glob(m)) or (current / m).exists():
                    root_folder = current
                    break

        if root_folder and project_folder:
            break

        parent = current.parent
        if parent == current: # Reached drive root
            break
        current = parent

    # 3. Final Validation
    if not root_folder or not project_folder:
        missing = "Root" if not root_folder else "Project"
        raise FileNotFoundError(f"Could not locate {missing} folder from {start_path}")

    return {
        "root_folder": root_folder,
        "project_folder": project_folder
    }

# --- Convenience Wrappers ---

def get_root_folder(calling_file=None, **kwargs):
    """Returns only the Path object for the root folder."""
    # We pass calling_file=calling_file because if it's None, 
    # the stack search in get_project_folders will now need to look 
    # TWO levels up (Wrapper -> Caller)
    if calling_file is None:
        # Step back to the person who called THIS wrapper
        calling_file = inspect.stack()[1].filename
        
    return get_project_folders(calling_file=calling_file, **kwargs)["root_folder"]

def get_project_folder(calling_file=None, **kwargs):
    """Returns only the Path object for the project folder."""
    if calling_file is None:
        calling_file = inspect.stack()[1].filename
        
    return get_project_folders(calling_file=calling_file, **kwargs)["project_folder"]