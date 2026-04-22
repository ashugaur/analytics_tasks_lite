import pandas as pd
import numpy as np
import os.path
import subprocess
import re


def scan_py_files_for_headings(unc):
    """function to extract comments from python a file and export as .md to create markmap"""

    # Read the file and process lines
    lines = []
    flags = []
    extracts = []

    pattern0 = re.compile(r"^# ")
    pattern1 = re.compile(r"^# %% ")
    pattern2 = re.compile(r"^###### ")
    pattern3 = re.compile(r"^##### ")
    pattern4 = re.compile(r"^#### ")
    pattern5 = re.compile(r"^### ")
    pattern6 = re.compile(r"^## ")
    pattern7 = re.compile(r"^#([^ ]+)")

    with open(unc, "r") as file:
        for line in file:
            ## exceptions
            line = line.replace(r"some abcd pattern", "a new pattern")
            line = line.strip()
            lines.append(line.strip())
            if pattern1.match(line):
                flags.append(1)
                extracts.append(pattern1.sub("", line).strip())
            elif pattern2.match(line):
                flags.append(2)
                extracts.append(pattern2.sub("", line).strip())
            elif pattern3.match(line):
                flags.append(3)
                extracts.append(pattern3.sub("", line).strip())
            elif pattern4.match(line):
                flags.append(4)
                extracts.append(pattern4.sub("", line).strip())
            elif pattern5.match(line):
                flags.append(5)
                extracts.append(pattern5.sub("", line).strip())
            elif pattern6.match(line):
                flags.append(6)
                extracts.append(pattern6.sub("", line).strip())
            elif pattern7.match(line):
                flags.append(7)
                extracts.append(pattern7.sub(r"\1", line).strip())
            elif pattern0.match(line):
                flags.append(-1)
                extracts.append(pattern0.sub("", line).strip())
            else:
                flags.append(0)
                extracts.append(line.strip())

    # Create a DataFrame
    df = pd.DataFrame({"line": lines, "flag": flags, "extract": extracts})

    # Create markdown
    df["hierarchy"] = np.where(
        (df["flag"].between(1, 6)), df["flag"].apply(lambda x: "#" * x), np.nan
    )
    df["hierarchy"] = np.where((df["flag"] == -1), "-", df["hierarchy"])
    df["md"] = np.where(
        (df["hierarchy"].isnull()), "", df["hierarchy"] + " " + df["extract"]
    )

    markdown_string = ""
    for i in df["md"]:
        if i != "":
            markdown_string = markdown_string + "\n" + i

    # Extract file name
    out_file, _ = os.path.splitext(os.path.basename(unc))
    out_file = out_file + ".md"

    # Export the string to a text file
    with open(out_file, "w") as file:
        file.write(markdown_string)

    # Open the text file using the default text editor without blocking
    subprocess.Popen(out_file, shell=True)
