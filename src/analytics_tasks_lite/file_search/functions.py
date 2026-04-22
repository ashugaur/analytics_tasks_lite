# %% File search functions

## Dependencies
import os
import polars as pl
import subprocess as sp
from datetime import datetime, timezone


## Load file search index
def load_fs_polars(scan_dir):
    """Loads file search index into a polars dataframe.

    Args:
        scan_dir: Path to directory containing parquet files
    Returns:
        DataFrame with aligned dtypes and joined data
    """
    # change working directory
    os.chdir(scan_dir)

    standard_dtypes = {
        "text": pl.String,
        "uf_id": pl.Float64,
        "row": pl.Float64,
        "column": pl.Float64,
        "sheet": pl.String,
        "formula_full": pl.String,
        "function": pl.String,
        "page": pl.Float64,
        "comments_top": pl.Float64,
    }

    try:
        print("🖧  Loading file search index...")
        scan0 = pl.read_parquet("scan0.parquet")
        searchx_final = pl.read_parquet("searchx_final.parquet")

        # Remove rows with unwanted text conditions
        searchx_final = searchx_final.filter(
            ~(
                (searchx_final["text"] == "")  # Empty strings
                | searchx_final["text"].is_null()  # Null values
                | (searchx_final["text"] == ".")  # Only a dot
            )
        )

        # Apply standard dtypes to both dataframes
        for col, dtype in standard_dtypes.items():
            if col in scan0.columns:
                if scan0.schema.get(col) != dtype:
                    scan0 = scan0.with_columns(scan0[col].cast(dtype))
            if col in searchx_final.columns:
                if searchx_final.schema.get(col) != dtype:
                    searchx_final = searchx_final.with_columns(
                        searchx_final[col].cast(dtype)
                    )

        # Join dataframes
        try:
            searchx = scan0.join(
                searchx_final, left_on="uf_id", right_on="uf_id", how="left"
            )
        except Exception:
            # If join fails, ensure consistent types for uf_id
            scan0 = scan0.with_columns(scan0["uf_id"].cast(pl.Float64))
            searchx_final = searchx_final.with_columns(
                searchx_final["uf_id"].cast(pl.Float64)
            )
            searchx = scan0.join(
                searchx_final, left_on="uf_id", right_on="uf_id", how="left"
            )

        print("💾  Estimated size:", round(searchx.estimated_size(unit="mb"), 1), "MB")
        return searchx
    except Exception as e:
        print(
            f"❌  WARNING: File search index not found. Please build the index using `fs_build.py`.\nError: {e}"
        )


# %% Query


class query:
    def __init__(self, searchx):
        self.searchx = searchx
        self.unc_func = "unc"
        self.ext = "ext"
        self.text = "text"
        self.lastwritetimeutc = "lastwritetimeutc"

    def fs_summary(self, substring, field=None):
        """Summary of search results for a given substring"""

        self.field = field
        try:
            if self.field:
                print(f"Searching <{substring}> in field <{self.field}>")
                query = (
                    self.searchx.select(
                        pl.col(self.unc_func, self.ext),
                        pl.col(self.unc_func)
                        .str.contains_any([str(substring)], ascii_case_insensitive=True)
                        .alias("unc_flag"),
                    )
                    .filter(pl.col("unc_flag"))
                    .select(pl.col(self.unc_func, self.ext))
                    .unique()
                    .sort(self.ext)
                )
                # print(query)
            else:
                query = (
                    self.searchx.select(
                        pl.col(self.unc_func, self.ext),
                        pl.col(self.text)
                        .str.contains_any([str(substring)], ascii_case_insensitive=True)
                        .alias("text_flag"),
                    )
                    .filter(pl.col("text_flag"))
                    .sort(self.ext)
                )

            query_n_unique = query.select(pl.col(self.unc_func).n_unique())

            if self.field:
                query_summary = (
                    query.group_by(self.ext)
                    .agg(
                        pl.col(self.unc_func).n_unique().alias("files"),
                    )
                    .sort("files")
                    .reverse()
                )
            else:
                query_summary = (
                    query.group_by(self.ext)
                    .agg(
                        pl.col(self.unc_func).n_unique().alias("files"),
                        pl.col(self.unc_func).count().alias("frequency"),
                    )
                    .sort("files")
                    .reverse()
                )

            if query_summary.is_empty():
                raise ValueError(f"No matches to substring '{substring}'")
            s = (
                "\n"
                + "Number of files containing: "
                + substring
                + " = "
                + str(query_n_unique.row(0)[0])
                + "\n"
            )
            print(s + "-" * len(s))
            return query_summary

        except Exception as e:
            print(f"Result: {e}")
            return None

    ## fs_details
    def fs_details(
        self, substring, reports_folder, ext_filter=None, field=None, dark_mode=0
    ):
        """overall details of searchx results as .html file"""

        self.field = field

        # export html
        if dark_mode == 1:

            def create_html_file(
                df,
                file_path,
                custom_string,
                right_spacing,
                custom_string_color="#5c5757",
                font_family="Arial, sans-serif",
                content_font_size="14px",
                utc_font_size="11px",
            ):
                df1 = (
                    df.select(pl.col(self.unc_func, self.lastwritetimeutc))
                    .unique()
                    .sort(self.lastwritetimeutc)
                    .reverse()
                )
                unique_unc_values = df1[self.unc_func]
                unique_lastwritetimeutc_values = df1[self.lastwritetimeutc]

                with open(file_path, "w", encoding="utf-8") as file:
                    file.write("<html>\n<head>\n<style>\n")
                    file.write(
                        "body { background-color: #1a1a1a; color: #5c5454; margin: 0 auto; max-width: 1200px; text-align: left; font-family: "
                        + font_family
                        + ";}\n"
                    )
                    file.write("h1, h2, p { color: #6483a3; }\n")
                    file.write("a { color: #826a65; text-decoration: none; }\n")
                    file.write(
                        ".content { padding: 20px; overflow-x: hidden; font-size: "
                        + content_font_size
                        + ";}\n"
                    )
                    file.write(
                        ".toc { font-size: 13px; line-height: 0; margin-bottom: 0; }\n"
                    )
                    file.write(
                        ".content h1 { font-size: 100%; margin-bottom: 16px; }\n"
                    )
                    file.write(".content h2 { margin-bottom: 8px; }\n")
                    file.write(".content p { margin: 0; }\n")
                    file.write(".unc-bold { font-weight: bold; }\n")
                    file.write(
                        ".custom-string { color: " + custom_string_color + "; }\n"
                    )
                    file.write(".utc { font-size: " + utc_font_size + "; }\n")
                    file.write("</style>\n</head>\n<body>\n")

                    # Custom String
                    file.write(
                        f'<div class="content">\n<span class="custom-string">{custom_string}</span></div>\n'
                    )

                    # Table of Contents
                    file.write(
                        '<div class="toc">\n<table style="border-collapse: collapse; max-width: 90%; width: auto; margin-left: 0;">\n'
                    )  # set max-width for the table
                    for i, (unc_value, utc_value) in enumerate(
                        zip(unique_unc_values, unique_lastwritetimeutc_values)
                    ):
                        filename = os.path.basename(unc_value)
                        file.write(r'<tr style="border: none;">')  # start table row
                        file.write(
                            f'<td style="border: none; vertical-align: top; font-size: 11px;">{i + 1:02d}. <a href="#{unc_value}" style="font-size: 11px;">{filename}</a></td>\n'
                        )  # font size for filename
                        file.write(
                            f'<td style="border: none; text-align: right; font-size: 11px;"><span class="utc">{utc_value}</span></td>\n'
                        )  # font size for lastwritetimeutc
                        file.write("</tr>\n")  # end table row
                    file.write("</table>\n</div>\n")

                    # Content
                    file.write('<div class="content">\n')
                    sorted_df = df.sort([self.unc_func, self.ext])
                    for i, (index, unc_value) in enumerate(
                        zip(range(1, len(unique_unc_values) + 1), unique_unc_values)
                    ):
                        filtered_df = sorted_df.filter(
                            sorted_df[self.unc_func] == unc_value
                        )
                        first_row = filtered_df.to_pandas().iloc[0]
                        file.write(
                            f'<p class="unc-bold" id="{unc_value}">{index:02d}. <a href="{unc_value}" target="_blank">{unc_value}</a> <span class="utc" style="font-size: {utc_font_size};">{first_row[self.lastwritetimeutc]}</span></p>\n'
                        )  # hyperlink to external file
                        for row in filtered_df.to_pandas().itertuples(index=False):
                            file.write(f'<p id="{row.text}">{row.text}</p>\n')
                        if i < len(unique_unc_values) - 1:
                            file.write(
                                f'<div style="height: {right_spacing};"></div>\n'
                            )
                    file.write("</div>\n</body>\n</html>")
        else:

            def create_html_file(
                df,
                file_path,
                custom_string,
                right_spacing,
                custom_string_color="#5c5757",
                font_family="Arial, sans-serif",
                content_font_size="14px",
                utc_font_size="11px",
            ):
                df1 = (
                    df.select(pl.col(self.unc_func, self.lastwritetimeutc))
                    .unique()
                    .sort(self.lastwritetimeutc)
                    .reverse()
                )
                unique_unc_values = df1[self.unc_func]
                unique_lastwritetimeutc_values = df1[self.lastwritetimeutc]

                with open(file_path, "w", encoding="utf-8") as file:
                    file.write("<html>\n<head>\n<style>\n")
                    file.write(
                        "body { margin: 0 auto; max-width: 1200px; text-align: left; font-family: "
                        + font_family
                        + ";}\n"
                    )
                    file.write(
                        "h1, h2, p { color: #000; }\n"
                    )  # Standard color for headings and paragraphs
                    file.write(
                        "a { color: #0000EE; text-decoration: none; }\n"
                    )  # Standard blue for links
                    file.write(
                        ".content { padding: 20px; overflow-x: hidden; font-size: "
                        + content_font_size
                        + ";}\n"
                    )
                    file.write(
                        ".toc { font-size: 13px; line-height: 0; margin-bottom: 0; }\n"
                    )  # Smaller font size and no space between lines for table of contents
                    file.write(
                        ".content h1 { font-size: 100%; margin-bottom: 16px; }\n"
                    )
                    file.write(".content h2 { margin-bottom: 8px; }\n")
                    file.write(".content p { margin: 0; }\n")
                    file.write(".unc-bold { font-weight: bold; }\n")
                    file.write(
                        ".custom-string { color: " + custom_string_color + "; }\n"
                    )  # Custom color for custom_string
                    file.write(
                        ".utc { font-size: " + utc_font_size + "; }\n"
                    )  # Font size for UTC label
                    file.write("</style>\n</head>\n<body>\n")

                    # Custom String
                    file.write(
                        f'<div class="content">\n<span class="custom-string">{custom_string}</span></div>\n'
                    )

                    # Table of Contents
                    file.write(
                        '<div class="toc">\n<table style="border-collapse: collapse; max-width: 90%; width: auto; margin-left: 0;">\n'
                    )  # Set max-width for the table
                    for i, (unc_value, utc_value) in enumerate(
                        zip(unique_unc_values, unique_lastwritetimeutc_values)
                    ):
                        filename = os.path.basename(unc_value)
                        file.write(r'<tr style="border: none;">')  # Start table row
                        file.write(
                            f'<td style="border: none; vertical-align: top; font-size: 11px;">{i + 1:02d}. <a href="#{unc_value}" style="font-size: 11px;">{filename}</a></td>\n'
                        )  # Font size for filename
                        file.write(
                            f'<td style="border: none; text-align: right; font-size: 11px;"><span class="utc">{utc_value}</span></td>\n'
                        )  # Font size for lastwritetimeutc
                        file.write("</tr>\n")  # End table row
                    file.write("</table>\n</div>\n")

                    # Content
                    file.write('<div class="content">\n')
                    sorted_df = df.sort([self.unc_func, self.ext])
                    for i, (index, unc_value) in enumerate(
                        zip(range(1, len(unique_unc_values) + 1), unique_unc_values)
                    ):
                        filtered_df = sorted_df.filter(
                            sorted_df[self.unc_func] == unc_value
                        )
                        first_row = filtered_df.to_pandas().iloc[0]
                        file.write(
                            f'<p class="unc-bold" id="{unc_value}">{index:02d}. <a href="{unc_value}" target="_blank">{unc_value}</a> <span class="utc" style="font-size: {utc_font_size};">{first_row[self.lastwritetimeutc]}</span></p>\n'
                        )  # Hyperlink to external file
                        for row in filtered_df.to_pandas().itertuples(index=False):
                            file.write(f'<p id="{row.text}">{row.text}</p>\n')
                        if i < len(unique_unc_values) - 1:
                            file.write(
                                f'<div style="height: {right_spacing};"></div>\n'
                            )
                    file.write("</div>\n</body>\n</html>")

        # search
        if self.field:
            query = (
                self.searchx.select(
                    pl.col(self.unc_func, self.ext, self.lastwritetimeutc),
                    pl.col(self.field)
                    .str.contains_any([str(substring)], ascii_case_insensitive=True)
                    .alias("text"),
                )
                .filter(pl.col("text"))
                .unique()
            )
        else:
            query = self.searchx.select(
                pl.col(self.unc_func, self.ext, self.lastwritetimeutc, self.text),
                pl.col(self.text)
                .str.contains_any([str(substring)], ascii_case_insensitive=True)
                .alias("text_flag"),
            ).filter(pl.col("text_flag"))

        if ext_filter:
            query = query.filter(pl.col(self.ext).is_in(ext_filter))

        query = (
            query.select(
                pl.col(self.unc_func, self.ext, self.lastwritetimeutc, self.text)
            )
            .sort(self.lastwritetimeutc)
            .reverse()
        )

        query_records = query.shape[0]
        query_n_unique = query.select(pl.col(self.unc_func).n_unique())

        query_summary = (
            query.group_by(self.ext)
            .agg(
                pl.col(self.unc_func).n_unique().alias("files"),
                pl.col(self.unc_func).count().alias("frequency"),
            )
            .sort("files")
            .reverse()
        )

        grouped_df = query_summary.group_by(self.ext).agg(
            pl.col("files").sum().alias("total_files"),
            pl.col("frequency").sum().alias("total_frequency"),
        )

        # Create a list of tuples containing ext, total_files, and total_frequency
        data = [
            (ext, total_files, total_frequency)
            for ext, total_files, total_frequency in zip(
                grouped_df[self.ext],
                grouped_df["total_files"],
                grouped_df["total_frequency"],
            )
        ]

        # Sort the list of tuples based on total_files
        sorted_data = sorted(data, key=lambda x: x[1], reverse=True)

        # Join the sorted values
        output_string = "&emsp;".join(
            f"{ext}: {total_files}.{total_frequency}"
            for ext, total_files, total_frequency in sorted_data
        )

        custom_string = (
            r"searchx_detailed &emsp; files.frequency &emsp; total:"
            + str(query_n_unique.row(0)[0])
            + "."
            + str(query_records)
            + "&emsp;"
            + output_string
        )

        right_spacing = "30px"  # Adjust spacing as needed
        file_dt = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        filename = (
            str(reports_folder).replace("\\", "/")
            + r"/"
            + str(substring[:19])
            + "."
            + file_dt
            + ".html"
        )

        if grouped_df.is_empty():
            print(f"WARNING: No matches to substring '{substring}'")
        else:
            create_html_file(query, filename, custom_string, right_spacing)

        sp.Popen(filename, shell=True)


class overview:
    def __init__(self, searchx):
        self.searchx = searchx

    # %% searchx_files_coverage

    def fs_coverage(self, reports_folder, dark_mode=0):
        """overall summary of search results"""

        # export html
        if dark_mode == 1:

            def create_html_file(
                df,
                file_path,
                custom_string,
                right_spacing,
                custom_string_color="#6483a3",
                font_family="Arial, sans-serif",
                content_font_size="12px",
                utc_font_size="11px",
                table_font_size="12px",
                table_content_color="#6483a3",
                border="1px solid",
                border_color="#ccc",
            ):
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write("<html>\n<head>\n<style>\n")
                    file.write(
                        "body { background-color: #1a1a1a; color: #5c5454; margin: 0 auto; max-width: 1200px; text-align: left; font-family: "
                        + font_family
                        + ";}\n"
                    )
                    file.write("h1, h2, p { color: #6483a3; }\n")
                    file.write("a { color: #826a65; text-decoration: none; }\n")
                    file.write(
                        ".content { padding: 20px; overflow-x: hidden; font-size: "
                        + content_font_size
                        + ";}\n"
                    )
                    file.write(
                        f"table {{ font-size: {table_font_size}; border-collapse: collapse; table-layout: auto; border: {border}; border-color: {border_color}; }}\n"
                    )
                    file.write(
                        ".toc { font-size: 13px; line-height: 0; margin-bottom: 0; }\n"
                    )
                    file.write(
                        ".content h1 { font-size: 100%; margin-bottom: 16px; }\n"
                    )
                    file.write(".content h2 { margin-bottom: 8px; }\n")
                    file.write(".content p { margin: 0; }\n")
                    file.write(".unc-bold { font-weight: bold; }\n")
                    file.write(
                        ".custom-string { color: " + custom_string_color + "; }\n"
                    )
                    file.write(".utc { font-size: " + utc_font_size + "; }\n")
                    file.write(
                        "th { text-align: left; border: "
                        + border
                        + "; border-color: "
                        + border_color
                        + ";}\n"
                    )
                    file.write(
                        f"td {{ color: {table_content_color}; border: {border}; border-color: {border_color}; }}\n"
                    )
                    file.write("td, th { whitespace: nowrap; }\n")
                    file.write("</style>\n</head>\n<body>\n")

                    # Custom String
                    file.write(
                        f'<div class="content">\n<span class="custom-string">{custom_string}</span></div>\n'
                    )

                    # Content
                    file.write('<div class="content">\n')
                    file.write("<table>\n")
                    # Table headers with left-alignment
                    file.write(
                        "<tr><th>Extension</th><th>Number of Files</th><th>Frequency</th><th>Coverage</th></tr>\n"
                    )

                    for row in df.to_pandas().itertuples(index=False):
                        file.write(
                            f"<tr><td>{row.ext}</td><td>{row.files}</td><td>{row.frequency}</td><td>{row.coverage}</td></tr>\n"
                        )

                    file.write("</table>\n")
                    file.write(f'<div style="height: {right_spacing};"></div>\n')
                    file.write("</div>\n</body>\n</html>")
        else:

            def create_html_file(
                df,
                file_path,
                custom_string,
                right_spacing,
                custom_string_color="#6483a3",
                font_family="Arial, sans-serif",
                content_font_size="12px",
                utc_font_size="11px",
                table_font_size="12px",
                table_content_color="#6483a3",
                border="1px solid",
                border_color="#ccc",
            ):
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write("<html>\n<head>\n<style>\n")
                    file.write(
                        "body { margin: 0 auto; max-width: 1200px; text-align: left; font-family: "
                        + font_family
                        + ";}\n"
                    )
                    file.write(
                        "h1, h2, p { color: #000; }\n"
                    )  # Standard color for headings and paragraphs
                    file.write(
                        "a { color: #0000EE; text-decoration: none; }\n"
                    )  # Standard blue for links
                    file.write(
                        ".content { padding: 20px; overflow-x: hidden; font-size: "
                        + content_font_size
                        + ";}\n"
                    )
                    file.write(
                        f"table {{ font-size: {table_font_size}; border-collapse: collapse; table-layout: auto; border: {border}; border-color: {border_color}; }}\n"
                    )
                    file.write(
                        ".toc { font-size: 13px; line-height: 0; margin-bottom: 0; }\n"
                    )  # Smaller font size and no space between lines for table of contents
                    file.write(
                        ".content h1 { font-size: 100%; margin-bottom: 16px; }\n"
                    )
                    file.write(".content h2 { margin-bottom: 8px; }\n")
                    file.write(".content p { margin: 0; }\n")
                    file.write(".unc-bold { font-weight: bold; }\n")
                    file.write(
                        ".custom-string { color: " + custom_string_color + "; }\n"
                    )  # Custom color for custom_string
                    file.write(
                        ".utc { font-size: " + utc_font_size + "; }\n"
                    )  # Font size for UTC label
                    file.write(
                        "th { text-align: left; border: "
                        + border
                        + "; border-color: "
                        + border_color
                        + ";}\n"
                    )  # Left-align table headers
                    file.write(
                        f"td {{ color: {table_content_color}; border: {border}; border-color: {border_color}; }}\n"
                    )  # Set table content font color
                    file.write(
                        "td, th { white-space: nowrap; }\n"
                    )  # Ensure cells do not wrap content
                    file.write("</style>\n</head>\n<body>\n")

                    # Custom String
                    file.write(
                        f'<div class="content">\n<span class="custom-string">{custom_string}</span></div>\n'
                    )

                    # Content
                    file.write('<div class="content">\n')
                    file.write("<table>\n")
                    # Table headers with left-alignment
                    file.write(
                        "<tr><th>Extension</th><th>Number of Files</th><th>Frequency</th><th>Coverage</th></tr>\n"
                    )

                    for row in df.to_pandas().itertuples(index=False):
                        file.write(
                            f"<tr><td>{row.ext}</td><td>{row.files}</td><td>{row.frequency}</td><td>{row.coverage}</td></tr>\n"
                        )

                    file.write("</table>\n")
                    file.write(f'<div style="height: {right_spacing};"></div>\n')
                    file.write("</div>\n</body>\n</html>")

        query_n_unique = self.searchx.select(pl.col("unc").n_unique())

        query_summary = (
            self.searchx.group_by("ext")
            .agg(
                pl.col("unc").n_unique().alias("files"),
                pl.col("unc").count().alias("frequency"),
            )
            .sort("files")
            .reverse()
        )

        query_summary = query_summary.with_columns(
            pl.when(pl.col("files") == pl.col("frequency"))
            .then(0)
            .otherwise(1)
            .alias("coverage")
        )

        custom_string = "Number of files by extension: " + str(query_n_unique.row(0)[0])

        right_spacing = "30px"  # Adjust spacing as needed
        file_dt = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = (
            str(reports_folder).replace("\\", "/")
            + r"/"
            + "searchx_files_summary."
            + file_dt
            + ".html"
        )

        create_html_file(
            query_summary,
            filename,
            custom_string,
            right_spacing,
            border="1px solid",
            border_color="#666",
        )

        sp.Popen(filename, shell=True)


# %% Extract


## Excel column names
class extract_xl:
    def __init__(self, searchx):
        self.searchx = searchx

    def column_names(self):
        """Pulls all values from Row A1 likely to be the column names in excel sheets."""

        fs_column_name = (
            self.searchx.filter(pl.col("row") == 1)
            .select(pl.col("text"))
            .rename({"text": "column_name"})
            .drop_nulls()
            .unique()
        )

        return fs_column_name
