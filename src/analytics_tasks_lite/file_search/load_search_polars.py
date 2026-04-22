import os
import polars as pl


def load_search_polars(scan_dir):
    """loads search index into a polars datafame"""

    print("\nLoading search index...")

    # change working directory
    os.chdir((scan_dir).replace("\\", "/"))

    # import scan
    scan0 = pl.read_parquet("scan0.parquet")
    searchx_final = pl.read_parquet("searchx_final.parquet")

    try:
        searchx = scan0.join(
            searchx_final, left_on="uf_id", right_on="uf_id", how="left"
        )
    except Exception:
        scan0 = scan0.with_columns(scan0["uf_id"].cast(pl.Int64))
        searchx_final = searchx_final.with_columns(
            searchx_final["uf_id"].cast(pl.Int64)
        )
        searchx = scan0.join(
            searchx_final, left_on="uf_id", right_on="uf_id", how="left"
        )
        print("ERROR       : The format for uf_id field may be inconsistent.")

    searchx = searchx.sort("lastwritetimeutc").reverse()
    print("Estimated size:", searchx.estimated_size(unit="mb"), "MB")

    return searchx

    del [scan0, searchx_final]

    print("\nsearchx loaded...")
