import os


def run_py_file(filepath):
    """
    Executes the Python script at the given filepath using exec().

    Args:
        filepath (str): The path to the Python script to execute.
    """
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return  # Important: Exit if file doesn't exist
    try:
        with open(filepath, "r") as f:
            code = f.read()
        exec(code)
    except Exception as e:
        print(f"Error executing script: {e}")  # catch errors
        # Optionally, you might want to re-raise the exception
        # raise  # Uncomment this if you want the error to halt execution
