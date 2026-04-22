import pandas as pd


def import_txt(
    filename,
    sep="\t",
    header=None,
    parse_dates=None,
    encoding=None,
    na_values=None,
    skiprows=0,
    index_col=None,
    skipfooter=0,
    names=None,
):
    """
    Import a TXT file with flexible options.

    Parameters:
    - filename (str): Path to the TXT file.
    - sep (str, optional): Delimiter to use. Default is '\t' (tab).
    - header (int or None, optional): Row number to use as column names. Default is None.
    - parse_dates (list or None, optional): Columns to parse as dates. Default is None.
    - encoding (str or None, optional): Encoding to use. Default is None.
    - na_values (list or None, optional): Additional strings to recognize as NA/NaN. Default is None.

    Returns:
    - pd.DataFrame: DataFrame containing the TXT data.
    """
    df = pd.read_csv(
        filename,
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


if __name__ == "__main__":
    df = import_txt("path/to/your/file.txt", sep=",", header=0)
    print(df.head())
