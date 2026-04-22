# %% Find columns with specific substring or all column names in list of excel files

## Dependencies
import pandas as pd
from pathlib import Path
from typing import List, Optional, Union, Dict, Any


def find_excel_column_name(
    file_paths: List[Union[str, Path]],
    sheet: Optional[Union[str, int]] = None,
    string: Optional[str] = None,
    exact: bool = False,
    match_case: bool = False,
    unique_value_limit: int = 30,
    return_df: bool = False,
) -> Union[Dict[str, Any], pd.DataFrame]:
    """
    Search for columns in multiple Excel files that match (or contain) a given string.
    If string is None or empty, returns ALL column names with their unique value previews.

    Parameters:
    -----------
    file_paths : list of str or Path
        List of paths to Excel files (.xlsx, .xls, .xlsm, etc.)
    sheet : str or int, optional
        Specific sheet name or index to read. If None, checks all sheets.
    string : str or None, optional
        The string to search for in column names.
        If None or empty string → returns ALL columns.
    exact : bool, default False
        If True, requires exact match (only used when string is provided)
    match_case : bool, default False
        If True, matching is case-sensitive (only used when string is provided)
    unique_value_limit : int, default 30
        Maximum number of unique values to show per column.
        If more uniques exist, shows first N + a note "(X unique)"
    return_df : bool, default False
        If True, returns a pandas DataFrame with results
        If False, returns a nicely formatted dictionary

    Returns:
    --------
    If return_df=False: dict with structure:
        {
            'file.xlsx': {
                'Sheet1': {
                    'ColumnName': {
                        'matches': True/False,
                        'unique_values': ['rat', 'cat', ...] or str "(X unique)"
                    },
                    ...
                },
                ...
            },
            ...
        }

    If return_df=True: pandas DataFrame with columns:
        - file_path
        - sheet_name
        - column_name
        - matches (True/False)
        - match_type (exact/substring/all)
        - unique_values_preview
    """
    results = {}

    for file_path in file_paths:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            continue

        file_name = file_path.name

        try:
            excel_file = pd.ExcelFile(file_path, engine="openpyxl")
            sheet_names = [sheet] if sheet is not None else excel_file.sheet_names

            file_results = {}

            for sheet_name in sheet_names:
                try:
                    df = pd.read_excel(
                        file_path, sheet_name=sheet_name, engine="openpyxl", dtype=str
                    )

                    matching_cols = {}

                    search_active = string is not None and string.strip() != ""

                    for col in df.columns:
                        col_str = str(col)
                        matches = False
                        match_type = "all"

                        if search_active:
                            search_str = string if match_case else string.lower()
                            compare_col = col_str if match_case else col_str.lower()

                            if exact:
                                matches = compare_col == search_str
                                match_type = "exact"
                            else:
                                matches = search_str in compare_col
                                match_type = "contains"
                        else:
                            # When string is None → all columns match
                            matches = True

                        if matches:
                            uniques = df[col].dropna().unique()
                            unique_count = len(uniques)

                            if unique_count <= unique_value_limit:
                                preview = [str(x) for x in uniques]
                            else:
                                preview = [str(x) for x in uniques[:unique_value_limit]]
                                preview.append(f"({unique_count} unique values total)")

                            matching_cols[col_str] = {
                                "matches": matches,
                                "match_type": match_type,
                                "unique_values": preview,
                            }

                    if matching_cols:
                        file_results[sheet_name] = matching_cols

                except Exception as e:
                    print(f"Error reading sheet '{sheet_name}' in {file_name}: {e}")

            if file_results:
                results[file_name] = file_results

        except Exception as e:
            print(f"Could not open file {file_name}: {e}")
            continue

    if return_df:
        rows = []
        for file_name, sheets in results.items():
            for sheet_name, cols in sheets.items():
                for col_name, info in cols.items():
                    rows.append(
                        {
                            "file_path": file_name,
                            "sheet_name": sheet_name,
                            "column_name": col_name,
                            "matches": info["matches"],
                            "match_type": info["match_type"],
                            "unique_values_preview": ", ".join(info["unique_values"]),
                        }
                    )
        return pd.DataFrame(rows)

    else:
        return results


if __name__ == "__main__":
    files = [
        r"C:\Users\Ashut\Downloads\titanic.xlsx",
        r"C:\Users\Ashut\Downloads\titanic.xlsx",
    ]

    # Get ALL columns from all sheets
    all_columns = find_excel_column_name(
        file_paths=files, string=None, unique_value_limit=10, return_df=False
    )

    # import pprint
    # pprint.pprint(all_columns, width=140)

    # Or get as DataFrame
    df_all = find_excel_column_name(file_paths=files, string=None, return_df=True)
    print(df_all)
