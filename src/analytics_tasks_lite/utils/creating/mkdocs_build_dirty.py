import os
import subprocess as sp


def mkdocs_build_dirty(path, tool=None):
    """Build mkdocs static site with latest partial updates.

    Options: tool='uv | pip', default 'uv'
    """

    print("Running: MkDocs dirty build (defaults to uv)...")
    os.chdir(path.replace("\\", "/"))

    if tool == "pip":
        print("Using pip may be compartively slower than uv (default).")
        sp.check_output(
            "powershell -Executionpolicy ByPass -command uv run mkdocs build --dirty"
        )
