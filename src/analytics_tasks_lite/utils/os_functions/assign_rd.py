# %% Assign working directories


## Dependencies
import os
from pathlib import Path
import sys


def assign_rd(
    code_folder_exists=1, base_level=None, file_path=None, upaths=None, startup=False
):
    """
    Assigns root directory, file folder, file reference paths + optional user-defined fixed paths.

    If startup=True and '_startup' is provided in upaths, executes the startup script
    and **returns its namespace as the last return value** (a dictionary).

    Returns:
    --------
    tuple:
        (rf, ff, fn, fr, rfo, rfi, rfir, *user_paths, [startup_namespace])
        - fn: filename without extension (stem only)
        startup_namespace (dict) is only returned if startup=True and the script ran successfully.
    """
    if upaths is None:
        upaths = []

    # Find startup path if provided
    startup_path = None
    for item in upaths:
        if isinstance(item, dict) and "_startup" in item:
            startup_path = Path(item["_startup"]).resolve()
            break

    # ──────────────────────────────────────────────────────────────
    #  File detection logic
    # ──────────────────────────────────────────────────────────────
    in_interactive_mode = (
        hasattr(sys, "ps1")
        or "IPython" in sys.modules
        or "ipykernel" in sys.modules
        or "SPYDER" in os.environ
    )

    try:
        frame = sys._getframe(1)
        caller_file = frame.f_code.co_filename
        if caller_file in ("<stdin>", "<console>", "<input>", "<string>"):
            in_interactive_mode = True
    except:
        pass

    if in_interactive_mode and file_path is None:
        raise ValueError(
            "Interactive mode detected. You must specify 'file_path' parameter."
        )

    detected_file_path = None

    if file_path is not None:
        detected_file_path = Path(file_path).resolve()
        if not detected_file_path.exists():
            raise ValueError(f"file_path does not exist: {file_path}")
        if detected_file_path.suffix != ".py":
            raise ValueError("file_path must be a .py file")
    else:
        # Auto-detect via frame walking
        try:
            this_file = Path(__file__).resolve()
            frame_depth = 1
            while frame_depth < 20:
                try:
                    frame = sys._getframe(frame_depth)
                    caller_file = frame.f_code.co_filename
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
                    if caller_path == this_file:
                        frame_depth += 1
                        continue
                    if caller_path.exists() and caller_path.suffix == ".py":
                        detected_file_path = caller_path
                        break
                except ValueError:
                    break
                frame_depth += 1
        except Exception:
            pass

        # Fallback: use sys.argv[0] — reliable when running from PowerShell/terminal
        # e.g. `python myscript.py` or `python -m mymodule`
        if detected_file_path is None and sys.argv and sys.argv[0]:
            argv_path = Path(sys.argv[0]).resolve()
            if argv_path.exists() and argv_path.suffix == ".py":
                detected_file_path = argv_path

        if detected_file_path is None:
            raise ValueError(
                "Could not auto-detect file. Please provide file_path.\n"
                "Tip: when running from a terminal, pass file_path=__file__ explicitly."
            )

    fn = detected_file_path.stem
    ff = detected_file_path.parent
    fr = detected_file_path.with_suffix("")

    # Root folder logic
    if code_folder_exists == 1:
        search_start = (
            ff
            if base_level is None
            else ff.parents[base_level - 1]
            if base_level > 0
            else ff
        )
        current = search_start
        rf = None
        for _ in range(11):
            try:
                if any(
                    d.is_dir() and d.name.lower() == "code" for d in current.iterdir()
                ):
                    rf = current
                    break
            except:
                pass
            if current.parent == current:
                break
            current = current.parent
        if rf is None:
            raise ValueError("Could not find 'code' folder upwards.")
    else:
        rf = ff
        if base_level:
            rf = rf.parents[base_level - 1] if base_level > 0 else rf

    if code_folder_exists == 1:
        rfo = rf / "output"
        rfi = rf / "input"
        rfir = rf / "input" / "reference"
    else:
        rfo = rfi = rfir = None

    # Convert to posix
    rf = rf.as_posix()
    ff = ff.as_posix()
    fr = fr.as_posix()
    if code_folder_exists == 1:
        rfo = rfo.as_posix()
        rfi = rfi.as_posix()
        rfir = rfir.as_posix()

    # User paths (exclude _startup)
    user_paths = []
    for item in upaths:
        if not isinstance(item, dict):
            raise ValueError("upaths items must be dicts")
        for k, v in item.items():
            if k != "_startup":
                user_paths.append(Path(v).resolve().as_posix())

    # Print
    print("✔️ Assigned paths:")
    print(f"  rf:  {rf}")
    print(f"  ff:  {ff}")
    print(f"  fn:  {fn}")
    print(f"  fr:  {fr}")
    if code_folder_exists == 1:
        print(f"  rfo: {rfo}")
        print(f"  rfi: {rfi}")
        print(f"  rfir:{rfir}")
    if user_paths:
        print("\n  User paths:")
        for i, p in enumerate(user_paths, 1):
            print(f"    {i}. {p}")

    startup_namespace = None

    # Startup execution
    if startup and startup_path:
        if startup_path.exists() and startup_path.suffix == ".py":
            print(f"→ Running startup: {startup_path.as_posix()}")
            try:
                orig_cwd = os.getcwd()
                os.chdir(startup_path.parent)
                print(f"   cwd → {startup_path.parent.as_posix()}")

                startup_namespace = {}
                exec(
                    compile(
                        open(startup_path, encoding="utf-8").read(),
                        str(startup_path),
                        "exec",
                    ),
                    startup_namespace,
                    startup_namespace,
                )

                os.chdir(orig_cwd)
                print("   cwd restored")
                print("→ Startup done")
            except Exception as e:
                print(f"⚠️ Startup failed: {type(e).__name__}: {e}")
                if "orig_cwd" in locals():
                    os.chdir(orig_cwd)
        else:
            print(f"⚠️ Startup file not found/invalid: {startup_path}")

    # Return
    result = (rf, ff, fn, fr, rfo, rfi, rfir, *user_paths)
    if startup_namespace is not None:
        result += (startup_namespace,)

    return result


# if __name__ == "__main__":
    # result = assign_rd(
    #     code_folder_exists=1,
    #     base_level=1,
    #     file_path=Path(
    #         "C:/my_disk/edupunk/analytics/exploratory/slidejs/code/slidejs.py"
    #     ),
    #     upaths=[
    #         {"_startup": Path("C:/my_disk/edupunk/src/functions/startup.py")},
    #     ],
    #     startup=True,
    # )
    # rf, ff, fn, fr, rfo, rfi, rfir, *user_paths, startup_vars = result
    # globals().update(startup_vars)
