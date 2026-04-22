from pathlib import Path
from analytics_tasks.utils.os_functions import open_file_folder
from .generate_data_table_from_dataframe_text_dark_internet import generate_data_table_from_dataframe_text_dark_internet

def dataframe_to_data_table(
    df,
    func="generate_data_table_from_dataframe_text_dark_internet",
    out_file=None,
    open_file=None,
):
    func_ref = globals()[func]
    html_content = func_ref(df)
    if out_file is None:
        out_file = Path(
            "C:/my_disk/____tmp/generate_data_table_from_dataframe_text_dark_internet.html"
        )
    with open(Path(out_file), "w") as f:
        f.write(html_content)

    if open_file:
        open_file_folder(out_file)

