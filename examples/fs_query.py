# %% File search query

## Dependencies
# import polars as pl
from pathlib import Path
from analytics_tasks.file_search.build import lib_refs_fs
from analytics_tasks.file_search.functions import (
    load_fs_polars,
    overview,
    query,
    extract_xl,
)
from analytics_tasks.ml.functions import info_schema_parser
from analytics_tasks.utils import fakedatagenerator as fdg

## Project folder
at_dir = Path("C:/analytics_tasks")


## Assign working libraries
fs_index_dir, logs_folder, time_machine, reports_folder = lib_refs_fs(at_dir)


# %% Load file search index

## File search index & its coverage
searchx = load_fs_polars(fs_index_dir)


# %% Search report(s)

## Find 'substring' in files
substring = "script"
report = query(searchx)
report.fs_summary(substring)

## Summary by field
report.fs_summary(substring, field="unc")

## Details by extension
report.fs_details(substring, reports_folder, ext_filter=[".py"], dark_mode=1)

## Details for field by extension
report.fs_details(
    substring, reports_folder, ext_filter=[".py"], field="unc", dark_mode=1
)

## All details
report.fs_details(substring, reports_folder, ext_filter=[], dark_mode=1)

## Coverage
all = overview(searchx)
all.fs_coverage(reports_folder, dark_mode=1)


# %% Extract text corpus

## Excel file column names
""" Extracts column names from excel files.
Objective: Show that similar functions can be written to extract text
            as corpus from different files as the index readily has
            some of this information.
            Interesting use is extracting top comments from powerpoint
            files (in column searchx.comments_top).
"""
corpus_xl = extract_xl(searchx)  # help(corpus_xl)
fs_column_name = corpus_xl.column_names()
fs_column_name.limit(10)


## Information schema parser
""" This is limited to Excel column names as substitute of duckdb table names.
Please feel free to bring in the information schema as required, field names
in 'info_schema' object should remain as is.
info_schema_df = pl.DataFrame(
    {"table_catalog": "", "table_schema": "", "table_name": "", "column_name": ""}
)

Objective: Derive 'info_schema_parsed.HashTags' to classify files using
            KMeans clustering (Ref: examples/3_fs_ml.py).
 """
generator = fdg.FakeDataGenerator()
info_schema_df = generator.generate_fake_info_schema(num_rows=50)
info_schema_parsed = info_schema_parser.info_schema_parser(searchx, info_schema_df)
print("\nReport: Information schema values in .sql files stored in column `HashTags`.")
info_schema_parsed["HashTags"].unique().head().to_list()
