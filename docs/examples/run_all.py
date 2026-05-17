# %% File search

## Dependencies
"""Run the full file_search pipeline in a single script.

Steps:
  1. Build the index (scan files, extract text -> parquet)
  2. Enrich the index with info schema references (optional, skipped if file missing)
  3. Query the index (search + generate reports)
  4. Export to DuckDB (for the web search app)

Usage:
    python run_all.py
    python run_all.py --scan-dir "C:\my\files" --skip-enrich --skip-export
    python run_all.py --skip-python-scan
"""

from __future__ import annotations
import argparse
import importlib
import sys
import time
from pathlib import Path
import warnings
import pandas as pd
import polars as pl
import os
from datetime import datetime
from analytics_tasks.utils.os_functions import assign_rd
from analytics_tasks.utils.reporting import create_color_reference_html
from analytics_tasks.utils.imputing import fill_missing_colors
from analytics_tasks.visual_library_ao.visual_library_demo_v14 import create_site
from analytics_tasks.file_search_app.file_search import (
    IndexBuilder,
    extract_excel_columns,
    load_index,
    search,
    search_coverage,
    search_details,
    search_summary,
    config,
)
from analytics_tasks.file_search_app.file_search.scanner import scan_clean
from analytics_tasks.file_search_app.extra import (
    enrich_index,
    load_info_schema,
    build_lookup,
)
from analytics_tasks.utils.controlling import log_start, log_end
from analytics_tasks.file_search.build import scan_dir_powershell

## Assign root directories
result = assign_rd(
    code_folder_exists=1,
    base_level=1,
    file_path=Path(
        r"C:\my_disk\edupunk\analytics\exploratory\file_search_app\code\run_all.py"
    ),
    upaths=[
        {"_startup": Path(r"C:/my_disk/edupunk/src/functions/startup.py")},
    ],
    startup=True,
)
rf, ff, fn, fr, rfo, rfi, rfir, *user_paths, startup_vars = result
globals().update(startup_vars)

log_start(Path(rfo) / "log")

## — Configuration ————————————————————————————————————————————————————————————
INDEX_DIR = Path(r"C:\my_disk\edupunk\analytics\exploratory\file_search_app")
REPORTS_DIR = INDEX_DIR / "output" / "report"
EXTRA_DIR = INDEX_DIR / "output" / "extra"
INFO_SCHEMA_FILE = EXTRA_DIR / "information_schema.xlsm"
SEARCHAPP_DATA_DIR = INDEX_DIR / "output" / "searchapp" / "data"
OUTPUT_FILE = INDEX_DIR / "input" / "searchx_enriched.parquet"

DEFAULT_SCAN_DIRS = [
    r"C:\my_disk",
]

def _drop_missing_local_paths(scan_df: pd.DataFrame) -> pd.DataFrame:
    """ Drop rows pointing to missing local files to avoid noisy exxtraction errors. """
    path_col = next(
        (c for c in ("unc", "full_name", "fullname", "path") if c in scan_df.columns),
        None,
    )
    if not path_col:
        return scan_df
    
    paths = scan_df[path_col].fillna("").astype(str)
    is_local_path = paths.str.match(r"^[A-Za-z]:[\\/]")
    if not is_local_path.any():
        return scan_df
    
    exists_local = paths[is_local_path].apply(os.path.exists)
    missing_idx = exists_local[~exists_local].index
    if len(missing_idx) > 0:
        print(
            f"  ⚠️  Dropped {len(missing_idx):,} missing local file(s) from existing scan input"
        )
        return scan_df.drop(index=missing_idx).reset_index(drop=True)
    
    return scan_df

## Build config overrides
DEFAULT_EXCLUDE: list[str] = [
    Path("C:/my_disk/edupunk/metadata"),
    Path("C:/my_disk/a/metadata"),
    Path("C:/my_disk/edupunk/all_docs/site"),
    Path("C:/my_disk/edupunk/all_docs/includes"),
    Path("C:/my_disk/edupunk/all_docs/docs/analytics"),
    Path("C:/my_disk/edupunk/all_docs/docs/assets"),
    Path("C:/my_disk/edupunk/all_docs/docs/revise"),
    Path("C:/my_disk/edupunk/analytics/exploratory/file_search_app"),
    # Path("C:/my_disk/edupunk/analytics/application/____automated_function_scan"),
    Path(".git"),
    Path(".ruff_cache"),
    Path(".venv"),
]
SIZE_OVERRIDES: dict[str, float | None] = {"excel": 10}
EXTENSION_GROUPS: list[str] | None = None

## Query defaults
SEARCH_TERM = "disprin"
SEARCH_FIELD = "text"
DARK_MODE = False


def _apply_config_overrides() -> None:
    """Push local overrides into the config module before the builder uses them."""
    for group, limit in SIZE_OVERRIDES.items():
        if limit is not None:
            config.SCAN_SIZE[group] = [limit]
    if EXTENSION_GROUPS is not None:
        groups_to_remove = [
            g for g in list(config.SCAN_EXT) if g not in EXTENSION_GROUPS
        ]
        for g in groups_to_remove:
            del config.SCAN_EXT[g]
            config.SCAN_SIZE.pop(g, None)


## STEP 1: Build the index
def step_build(
    scan_dirs: list[str],
    exclude: list[str] | None = None,
    workers: int | None = None,
    batch_size: int = 100,
    skip_python_scan: bool = False,
) -> None:
    print("\n" + "=" * 70)
    print("STEP 1: Building index")
    print("=" * 70)
    t0 = time.perf_counter()

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    _apply_config_overrides()

    for scan_dir in scan_dirs:
        Path(scan_dir).mkdir(parents=True, exist_ok=True)
        print(f"  📁 Scan folder: {scan_dir}")
    print(f"  📁 Index folder: {INDEX_DIR}")

    builder = IndexBuilder(str(INDEX_DIR))
    paths_to_exclude = (exclude or []) + DEFAULT_EXCLUDE or None
    if skip_python_scan:
        print("   ⏩  Skipping python scan step; using existing input scan file(s).")
        scan_csv = INDEX_DIR / "input" / "scan.csv"
        if not scan_csv.exists():
            raise FileNotFoundError(
                f"Missing scan input file: {scan_csv}. Generate it first (for example by running scan.ps1 manually)."
            )
        
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"Could not infer format, so each element will be parsed individually",
                category=UserWarning,
            )
            scan0 = scan_clean(str(builder.fs_index_dir))

        scan0 = _drop_missing_local_paths(scan0)
        if paths_to_exclude:
            scan0 = builder._apply_exclusions(scan0, paths_to_exclude)

        scan0, oversized_tabular = builder._apply_size_filter(scan0)
        builder._oversized_tabular = oversized_tabular
        builder.scan0 = scan0[scan0["filename"].str[0:1] != "~"].reset_index(drop=True)
        print(f"    ✅ Loaded existing scan.csv: {len(builder.scan0):,} files")
    else:
        builder.scan(
            scan_dirs=scan_dirs,
            paths_to_exclude=paths_to_exclude if paths_to_exclude else None,
        )
    builder.extract(max_workers=workers)
    searchx = builder.build_index(max_workers=workers, batch_size=batch_size)

    elapsed = time.perf_counter() - t0
    print(f"  ✅ Build complete: {len(searchx):,} rows in {elapsed:.1f}s")


## STEP 2: Enrich the index (optional)
def step_enrich() -> None:
    print("\n" + "=" * 70)
    print("STEP 2: Enriching index with info schema")
    print("=" * 70)

    if not INFO_SCHEMA_FILE.exists():
        print(f"  ⚠️  Info schema not found: {INFO_SCHEMA_FILE}")
        print("  Skipping enrichment step.")
        return

    # Import and run the enrich logic
    # import polars as pl

    t0 = time.perf_counter()

    # Load info schema
    # print(f"  📄 Loading info schema from {INFO_SCHEMA_FILE.name}...")
    # df_schema = pl.read_excel(INFO_SCHEMA_FILE)
    # col_map = {c: c.upper() for c in df_schema.columns}
    # df_schema = df_schema.rename(col_map)

    # required = ["TABLE_NAME", "COLUMN_NAME"]
    # missing = [c for c in required if c not in df_schema.columns]
    # if missing:
    #     print(f"  ⚠️  Missing columns in info schema: {missing}. Skipping enrichment.")
    #     return

    # keep_cols = [
    #     c for c in ["TABLE_NAME", "COLUMN_NAME", "DATA_TYPE"] if c in df_schema.columns
    # ]
    # df_schema = (
    #     df_schema.select(keep_cols).filter(pl.col("TABLE_NAME").is_not_null()).unique()
    # )
    # print(
    #     f"  Unique tables: {df_schema['TABLE_NAME'].n_unique()}, entries: {len(df_schema):,}"
    # )

    # Load the index and run enrichment via the enrich script
    # sys.path.insert(0, str(EXTRA_DIR))
    # enrich_module = importlib.import_module("enrich_index")
    # Reload to ensure fresh run
    # importlib.reload(enrich_module)

    # Extensions to check for schema references
    CODE_EXTENSIONS = {".py", ".sql", ".txt"}

    # Minimum table name length to avoid matching noise like "t1", "aa"
    # MIN_TABLE_NAME_LEN = 4

    # Minimum column name length for standalone matching
    # MIN_COLUMN_NAME_LEN = 5

    # Load info schema
    info_schema = load_info_schema(INFO_SCHEMA_FILE)
    table_columns, table_names_set = build_lookup(info_schema)

    # Load index (joins scan0 + searchx_final)
    print(f"\n Loading index from {INDEX_DIR}...")
    index_df = load_index(INDEX_DIR)
    print(f"   Index: {len(index_df):,} rows")

    code_count = index_df.filter(pl.col("ext").is_in(list(CODE_EXTENSIONS))).select(
        pl.col("unc").n_unique()
    )
    print(f"   Code files (.py/.sql/.txt): {code_count}")

    # Enrich
    print("\n Enriching index with info schema references...")
    enriched = enrich_index(index_df, table_columns, table_names_set)

    # Save
    print(f"\n Saving enriched index to {OUTPUT_FILE.name}...")
    enriched.write_parquet(str(OUTPUT_FILE))
    print(f"   Size: {OUTPUT_FILE.stat().st_size / (1024 * 1024):.1f} MB")
    print("\n Done! Re-run export_db.py to update the search app database.")

    elapsed = time.perf_counter() - t0
    print(f"  ✅ Enrichment complete in {elapsed:.1f}s")


## STEP 3: Query the index
def step_query(term: str | None = None) -> None:
    print("\n" + "=" * 70)
    print("STEP 3: Querying index")
    print("=" * 70)
    t0 = time.perf_counter()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    searchx = load_index(INDEX_DIR)
    print(f"  Index loaded: {len(searchx):,} rows")

    query_term = term or SEARCH_TERM
    print(f"  🔍 Searching for: {query_term!r}")

    summary = search_summary(searchx, query_term, field=SEARCH_FIELD)
    results = search(searchx, query_term, field=SEARCH_FIELD)

    if results.is_empty():
        print("  No rows matched.")
    else:
        print(f"  Found: {len(results):,} rows")
        print(
            results.select("unc", "text", "element_type", "line_number", "page").head(
                10
            )
        )

    # Generate reports
    search_details(
        searchx, query_term, str(REPORTS_DIR), dark_mode=DARK_MODE, max_total_rows=5000
    )
    search_coverage(searchx, str(REPORTS_DIR), dark_mode=DARK_MODE)

    elapsed = time.perf_counter() - t0
    print(f"  ✅ Query & reports complete in {elapsed:.1f}s")
    print(f"  📄 Reports saved to: {REPORTS_DIR}")


## STEP 4: Export to DuckDB
def step_export() -> None:
    print("\n" + "=" * 70)
    print("STEP 4: Exporting to DuckDB")
    print("=" * 70)
    t0 = time.perf_counter()

    import duckdb

    SEARCHAPP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_file = SEARCHAPP_DATA_DIR / "file_search.duckdb"

    searchx = load_index(INDEX_DIR)
    print(f"  Loaded: {len(searchx):,} rows")

    if db_file.exists():
        db_file.unlink()

    conn = duckdb.connect(str(db_file))
    conn.register("searchx_temp", searchx)
    conn.execute("""
        CREATE TABLE idx AS
        SELECT * REPLACE (strftime(lastwritetimeutc, '%Y-%m-%d %H:%M:%S') AS lastwritetimeutc)
        FROM searchx_temp
    """)
    conn.execute("CREATE INDEX idx_unc ON idx(unc)")
    conn.execute("CREATE INDEX idx_ext ON idx(ext)")

    row_count = conn.execute("SELECT COUNT(*) FROM idx").fetchone()[0]
    conn.close()

    db_size_mb = db_file.stat().st_size / (1024 * 1024)
    elapsed = time.perf_counter() - t0
    print(
        f"  ✅ Export complete: {row_count:,} rows, {db_size_mb:.1f} MB in {elapsed:.1f}s"
    )
    print(f"  📄 Database: {db_file}")


## Main
def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full file_search pipeline.")
    parser.add_argument(
        "--scan-dir",
        action="append",
        dest="scan_dirs",
        help="Directory to scan (repeat for multiple).",
    )
    parser.add_argument(
        "--refresh-scan",
        action="store_true",
        help="Regenerate input/scan.csv by running input/scan.ps1 before the build step.",
    )
    parser.add_argument(
        "--skip-python-scan",
        action="store_true",
        help="Skip python directory scanning and rely on existing scan input files (for example input/scan.csv).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        dest="paths_to_exclude",
        help="Path fragment to exclude (repeat for multiple).",
    )
    parser.add_argument("--term", default=None, help="Search term for query step.")
    parser.add_argument("--workers", type=int, default=None, help="Max worker count.")
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Batch size for build."
    )
    parser.add_argument(
        "--skip-enrich", action="store_true", help="Skip the enrichment step."
    )
    parser.add_argument(
        "--skip-query", action="store_true", help="Skip the query step."
    )
    parser.add_argument(
        "--skip-export", action="store_true", help="Skip the DuckDB export step."
    )
    args = parser.parse_args()

    scan_dirs = args.scan_dirs if args.scan_dirs else DEFAULT_SCAN_DIRS

    if args.refresh_scan:
        scan_dir_powershell(INDEX_DIR / "input", scan_dirs)

    total_t0 = time.perf_counter()

    # Step 1: Build
    step_build(
        scan_dirs,
        exclude=args.paths_to_exclude,
        workers=args.workers,
        batch_size=args.batch_size,
        skip_python_scan=args.skip_python_scan,
    )

    # Step 2: Enrich
    if not args.skip_enrich:
        step_enrich()

    # Step 3: Query
    if not args.skip_query:
        step_query(term=args.term)

    # Step 4: Export
    if not args.skip_export:
        step_export()

    total_elapsed = time.perf_counter() - total_t0
    print("\n" + "=" * 70)
    print(f"🎉 All steps complete in {total_elapsed:.1f}s")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

log_end()
