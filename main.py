# %% Welcome message

## Dependencies
"""After editable install: uv pip install -e ."""


## Hello!
def main():
    print("Hello from at!")


## Add packages

"""
# file search build
uv add PYPDF2, openpyxl, numpy, polars, pandas, ebooklib, python-docx, python-pptx, bs4, extract_msg

# file search query
uv add faker, reportlab, pyarrow

# file search ml (machine learning)
uv add matplotlib, scikit-learn
"""


# %% Manual testing

""" 
import os
from pathlib import Path

os.chdir(Path("C:/my_disk/projects/analytics_tasks"))

exec(open("C:/my_disk/projects/analytics_tasks/dev.py").read())
exec(open("C:/my_disk/projects/analytics_tasks/src/analytics_tasks/examples/1_fs_build.py").read())
"""


# %% Dev


def main():
    pass


if __name__ == "__main__":
    main()
