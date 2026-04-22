import re
import inspect
from pathlib import Path

def map_contents(path, level=0, include_files=True, verbose=True, target_globals=None):
    """
    Maps subfolders (and optionally files) to Python variables in the global namespace.
    """
    path = Path(path).resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError(f"Invalid directory path: {path}")

    # If target_globals is not provided, we try to find the globals of the caller
    if target_globals is None:
        # stack[1] is the context that called this function
        caller_frame = inspect.stack()[1]
        target_globals = caller_frame.frame.f_globals

    def sanitize_name(name):
        name = name.lower()
        name = re.sub(r"[^a-z0-9]", "_", name)
        name = re.sub(r"_+", "_", name)
        name = name.strip("_")
        return f"_{name}"

    result = {}
    name_counts = {}

    for current_level in range(level + 1):
        pattern = "/".join(["*"] * (current_level + 1))
        
        for item in sorted(path.glob(pattern)):
            # Check if it's a dir OR a file (based on include_files flag)
            if not item.is_dir() and not include_files:
                continue

            var_name = sanitize_name(item.name)

            # Handle name collisions
            if var_name in result:
                name_counts[var_name] = name_counts.get(var_name, 1) + 1
                var_name = f"{var_name}_{name_counts[var_name]}"

            result[var_name] = item

    # The Magic: Injecting into the target namespace
    for var_name, item_path in result.items():
        target_globals[var_name] = item_path

    if verbose:
        print(f"\n - Mapped items in '{path.name}' (level={level}) - ")
        for var_name, item_path in result.items():
            print(f"  {var_name:30s} : {item_path.name}")
        print("-" * 60)
        print(f"  {len(result)} variable(s) injected into global namespace.\n")

    return result