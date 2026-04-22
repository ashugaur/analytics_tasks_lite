import zipfile
import pandas as pd


def import_parquet_within_zip(zip_filename, filename, columns=None, **kwargs):
    """
    Import a Parquet file within a zip archive.

    Parameters:
    - zip_filename (str): Path to the zip file.
    - filename (str): Name of the Parquet file within the zip archive.
    - columns (list or None, optional): List of columns to read. Default is None.
    - **kwargs: Additional keyword arguments for pd.read_parquet.

    Returns:
    - pd.DataFrame: DataFrame containing the Parquet data.
    """
    with zipfile.ZipFile(zip_filename) as zf:
        with zf.open(filename) as file:
            df = pd.read_parquet(file, columns=columns, **kwargs)
    return df
