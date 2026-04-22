import zipfile
import pandas as pd


def import_csv_within_zip(
    zip_filename,
    filename,
    sep=",",
    header=0,
    parse_dates=None,
    encoding=None,
    na_values=None,
    skiprows=0,
    index_col=0,
    skipfooter=0,
    names=None,
):
    """
    Import a CSV file within a zip archive with flexible options.

    Parameters:
    - zip_filename (str): Path to the zip file.
    - filename (str): Name of the CSV file within the zip archive.
    - sep (str, optional): Delimiter to use. Default is ','.
    - header (int, optional): Row number to use as column names. Default is 0.
    - parse_dates (list or None, optional): Columns to parse as dates. Default is None.
    - encoding (str or None, optional): Encoding to use. Default is None.
    - na_values (list or None, optional): Additional strings to recognize as NA/NaN. Default is None.

    Returns:
    - pd.DataFrame: DataFrame containing the CSV data.
    """
    with zipfile.ZipFile(zip_filename) as zf:
        with zf.open(filename) as file:
            df = pd.read_csv(
                file,
                sep=sep,
                header=header,
                parse_dates=parse_dates,
                encoding=encoding,
                na_values=na_values,
                skiprows=skiprows,
                index_col=index_col,
                skipfooter=skipfooter,
                names=names,
            )
    return df
