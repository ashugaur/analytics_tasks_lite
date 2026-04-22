import pandas as pd
import pathlib
from pathlib import Path
import os
import glob
import shutil
import ast
import os.path
import os


def scan_python_functions_from_file_s(
    _source, _destination, _load_functions, _write_to_mkdocs
):
    """function to load functions from python files in folders to memory"""

    global scan

    _relevant_file_type = [".py"]

    if _write_to_mkdocs == 1:
        os.chdir(_destination.replace("\\", "/"))

        # remove folder
        os.chdir("\\".join(_destination.split("\\")[:-1]))
        shutil.rmtree(_destination.split("\\")[-1])

        # create folder
        pathlib.Path(_destination.split("\\")[-1]).mkdir(parents=True, exist_ok=True)
        os.chdir(_destination)
        # print('NOTE: functions written to documents site.')
    # else:
    # print('NOTE: functions not written to documents site.')

    # scan folder
    def scan_dir(location_to_scan):
        global scan
        scan = []
        for i in glob.iglob(rf"{location_to_scan}\**\*", recursive=True):
            scan.append(i)
        if len(scan) > 0:
            scan = pd.DataFrame(scan).rename(columns={0: "unc"})
            scan["filename"] = scan["unc"].apply(lambda row: Path(row).name)
            scan["ext"] = scan["unc"].apply(
                lambda row: os.path.splitext(os.path.basename(row))[1]
            )
        else:
            scan = pd.DataFrame({"filename": ""}, index=([0]))

    scan_dir(_source)

    # flag files and folders
    for i in range(0, len(scan)):
        _unc = scan.loc[i, "unc"]
        scan.loc[i, "dir_flag"] = None
        scan.loc[i, "file_flag"] = None
        if os.path.exists(_unc):
            if os.path.isdir(_unc):
                scan.loc[i, "dir_flag"] = os.path.isdir(_unc)
            else:
                scan.loc[i, "dir_flag"] = False
            if os.path.isfile(_unc):
                scan.loc[i, "file_flag"] = os.path.isfile(_unc)
            else:
                scan.loc[i, "file_flag"] = False

    # filter relevant unc
    scan = scan[scan["file_flag"]]
    scan = scan[scan["ext"].isin(_relevant_file_type)]

    # scan['relevant'] = np.where(scan['ext'].isin(_relevant_file_type), 1, 0)

    # exceptions
    scan = scan[~scan["filename"].isin(["edupunk.py"])]
    # scan = scan[~scan['filename'].str.contains('functions', case=False, regex=True, na=False)]

    # dir depth
    scan["unc"] = scan["unc"].str.replace("\\", "/")
    scan["depth"] = scan["unc"].str.count("/") - _source.count("\\") - 1
    scan["unc_l1"] = (scan["unc"].str.rsplit("/", expand=True, n=2)[0]).str.replace(
        "/".join(_source.split("\\")[:-1]), _destination.replace("\\", "/")
    )
    scan["_unc_md"] = (
        (scan["unc"].str.rsplit("/", expand=True, n=1)[0]).str.replace(
            "/".join(_source.split("\\")[:-1]), _destination.replace("\\", "/")
        )
        + ".md"
    )

    # create folder structure
    # for i in scan[scan['depth']>1]['unc_l1'].drop_duplicates():
    # print(i)
    # pathlib.Path(i).mkdir(parents=True, exist_ok=True)

    # write markdown
    select = scan[["unc", "_unc_md", "filename", "ext"]].sort_values(
        ["_unc_md", "filename"]
    )
    select["_filename"] = select["filename"].str.rsplit(".", expand=True, n=1)[0]

    # loop through files
    # _function_count = 0
    for unc in select["unc"].unique().tolist():
        # print('reading...: '+unc)
        function_code = ""

        try:
            # read the contents of the file
            with open(unc, "r", encoding="utf-8") as f:
                file_contents = f.read()

            # parse the file contents into an AST
            # parsed_file = ast.parse(repr(file_contents))
            parsed_file = ast.parse(file_contents)
            methods = find_methods_in_python_file(unc)

            for _function in methods:
                # find the function definition node in the AST
                function_node = next(
                    (
                        node
                        for node in parsed_file.body
                        if isinstance(node, ast.FunctionDef) and node.name == _function
                    ),
                    None,
                )

                # extract the code of the function
                if function_node is not None:
                    function_code = ast.unparse(function_node)
                    # print(function_code)
                else:
                    # print(f"function '{_function}' not found in file '{unc}'")
                    # print('warning... skipping:', unc)
                    continue

                if _write_to_mkdocs == 1:
                    _file = (
                        _function + "__" + str((unc.split("/")[-1]).lower())
                    )  # +'.py'
                    with open(_file, "w", encoding="utf-8") as f:
                        f.write("# " + unc + "\n\n" + function_code)
                        # print('REPORT: written function to disk from: '+unc)

                if 1 == _load_functions:
                    # _function_count += 1
                    exec(function_code, globals())

        except Exception:
            continue
            # print('warning: not able to scan', unc)

    # print('REPORT: # of times functions loaded to memory: '+str(_function_count))



def find_methods_in_python_file(file_path):
    """finds functions with python files
    Source: https://stackoverflow.com/questions/58935006/iterate-over-directory-and-get-function-names-from-found-py-files, chatgpt (openai)
    """

    methods = []
    o = open(file_path, "r", encoding="utf-8")
    text = o.read()
    # p = ast.parse(repr(text))
    p = ast.parse(text)
    for node in ast.walk(p):
        if isinstance(node, ast.FunctionDef):
            methods.append(node.name)
    return methods


