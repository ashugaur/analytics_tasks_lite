# %% convert_ipynb_to_py

## Dependencies
import nbformat
import subprocess as sp
import re
from nbconvert import PythonExporter


def convert_ipynb_to_py(ipynb_file, *, file_open=None):
    with open(ipynb_file, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    exporter = PythonExporter()
    source, _ = exporter.from_notebook_node(nb)
    source_cleaned = re.sub(r"# In\[\d*\]:\n\n\n|# In\[\s*\]:\n\n\n", "", source)

    py_file = str(ipynb_file)[:-5] + "py"

    with open(py_file, "w", encoding="utf-8") as f:
        f.write(source_cleaned)

    if file_open:
        sp.Popen(py_file, shell=True)
