from pathlib import Path


def show_image(filepath):
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"Error: {filepath} not found.")
        return

    try:
        # Jupyter / IPython environment
        from IPython import get_ipython
        from IPython.display import display, Image

        if get_ipython() is not None:
            display(Image(filename=str(filepath)))
            return
    except ImportError:
        pass
