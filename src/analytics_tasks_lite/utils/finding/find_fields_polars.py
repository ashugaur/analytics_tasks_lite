# %% Finding

## Dependencies
import polars as pl
import pandas as pd
import time
from typing import List, Union
""" from fuzzywuzzy import fuzz """


# %% Find field values across table columns
def find_fields_polars(
    base_table: Union[pd.DataFrame, pl.DataFrame],
    checklist_table: Union[pd.DataFrame, pl.DataFrame],
    base_column: str,
    checklist_column: str,
    match_types: List[str] = None,
    fuzzy_threshold: int = 90,
    include_matched_values: bool = True,
    verbose: bool = True,
    debug: bool = False,
) -> pd.DataFrame:
    """
    Ultra-fast comparison using Polars with configurable matching
    strategies.

    Parameters:
    ---
    base_table : pd.DataFrame or pl.DataFrame
        The base reference table
    checklist_table : pd.DataFrame or pl.DataFrame
        The checklist table to compare against base
    base_column : str
        Column name in base_table to use for comparison
    checklist_column : str
        Column name in checklist_table to use for comparison
    match_types : List[str], optional
        List of match types to perform. Options:
        ['exact', 'ignore_case', 'cleaned', 'like', 'fuzzy']
        Default: ['exact', 'ignore_case', 'cleaned']
    fuzzy_threshold : int, optional
        Similarity threshold for fuzzy matching (0-100). Default: 90
    include_matched_values : bool, optional
        Whether to include the 'matched_values' column. Default: True
    verbose : bool, optional
        Whether to print progress. Default: True
    debug : bool, optional
        Whether to print debug information. Default: False

    Returns:
    ---
    pd.DataFrame
        Combined table with all records and match flags
    """
    start_time = time.time()

    # Default match types if not specified
    if match_types is None:
        match_types = ["exact", "ignore_case", "cleaned"]

    # Validate match_types
    valid_types = ["exact", "ignore_case", "cleaned", "like", "fuzzy"]
    invalid_types = [mt for mt in match_types if mt not in valid_types]
    if invalid_types:
        raise ValueError(
            f"Invalid match types: {invalid_types}. Valid options: {valid_types}"
        )

    if verbose:
        print(f"Starting Polars comparison: {base_column} vs {checklist_column}")
        print(f"Match types enabled: {match_types}")
        if "fuzzy" in match_types:
            print(f"Fuzzy threshold: {fuzzy_threshold}")

    # Convert to Polars if needed
    if isinstance(base_table, pd.DataFrame):
        base_df = pl.from_pandas(base_table)
        if verbose:
            print(f"Converted base table to Polars: {base_df.shape}")
    else:
        base_df = base_table.clone()

    if isinstance(checklist_table, pd.DataFrame):
        check_df = pl.from_pandas(checklist_table)
        if verbose:
            print(f"Converted checklist table to Polars: {check_df.shape}")
    else:
        check_df = checklist_table.clone()

    # Add row indices for tracking (using new method)
    base_df = base_df.with_row_index(name="_base_idx")
    check_df = check_df.with_row_index(name="_check_idx")

    # Store original column names (exclude temp columns)
    base_cols = [col for col in base_df.columns if not col.startswith("_")]
    check_cols = [col for col in check_df.columns if not col.startswith("_")]

    # Prepare comparison values
    base_df = base_df.with_columns(
        [pl.col(base_column).fill_null("").cast(pl.Utf8).alias("_compare_val")]
    )

    check_df = check_df.with_columns(
        [pl.col(checklist_column).fill_null("").cast(pl.Utf8).alias("_compare_val")]
    )

    # Prepare uppercase versions if needed
    if any(mt in match_types for mt in ["exact", "ignore_case", "like", "fuzzy"]):
        if verbose:
            print("Preparing uppercase values...")
        base_df = base_df.with_columns(
            [pl.col("_compare_val").str.to_uppercase().alias("_upper")]
        )
        check_df = check_df.with_columns(
            [pl.col("_compare_val").str.to_uppercase().alias("_upper")]
        )

    if debug:
        print("\nSample uppercase values:")
        print("Base:", base_df.select(["_compare_val", "_upper"]).head(3))
        print("Check:", check_df.select(["_compare_val", "_upper"]).head(3))

    # Prepare cleaned versions if needed
    if "cleaned" in match_types:
        if verbose:
            print("Preparing cleaned values...")

        # Clean: uppercase, remove all non-alphanumeric
        base_df = base_df.with_columns(
            [
                pl.col("_compare_val")
                .str.to_uppercase()
                .str.replace_all(r"[^A-Z0-9]", "")
                .alias("_cleaned")
            ]
        )
        check_df = check_df.with_columns(
            [
                pl.col("_compare_val")
                .str.to_uppercase()
                .str.replace_all(r"[^A-Z0-9]", "")
                .alias("_cleaned")
            ]
        )

        if debug:
            print("\nSample cleaned values:")
            print("Base:", base_df.select(["_compare_val", "_cleaned"]).head(5))
            print("Check:", check_df.select(["_compare_val", "_cleaned"]).head(5))

            # Check if there are any non-empty cleaned values
            base_cleaned_count = (
                base_df.filter(pl.col("_cleaned") != "").select(pl.count()).item()
            )
            check_cleaned_count = (
                check_df.filter(pl.col("_cleaned") != "").select(pl.count()).item()
            )
            print(f"\nBase non-empty cleaned: {base_cleaned_count}")
            print(f"Check non-empty cleaned: {check_cleaned_count}")

    # Store all matches with their match details
    all_match_records = []

    # Track what we've matched to avoid re-matching
    matched_pairs = set()  # (check_idx, base_idx)

    # 1. EXACT MATCH (case insensitive)
    if "exact" in match_types:
        if verbose:
            print("\nPerforming exact match...")

        exact_matches = (
            check_df.select(["_check_idx", "_upper", "_compare_val"])
            .join(
                base_df.select(["_base_idx", "_upper", "_compare_val"]),
                on="_upper",
                how="inner",
                suffix="_base",
            )
            .filter(pl.col("_upper") != "")
        )  # Exclude empty matches

        if len(exact_matches) > 0:
            if debug:
                print("Sample exact matches:")
                print(exact_matches.head(3))

            for row in exact_matches.iter_rows(named=True):
                pair = (row["_check_idx"], row["_base_idx"])
                if pair not in matched_pairs:
                    all_match_records.append(
                        {
                            "_check_idx": row["_check_idx"],
                            "_base_idx": row["_base_idx"],
                            "match_exact": 1,
                            "match_ignore_case": 1,  # exact implies ignore_case
                            "match_cleaned": 0,
                            "match_like": 0,
                            "match_fuzzy": 0,
                            "matched_value": f"exact:{row['_compare_val_base']}",
                        }
                    )
                    matched_pairs.add(pair)

            if verbose:
                print(
                    f" Found {len([r for r in all_match_records if r['match_exact'] == 1])} exact matches"
                )
        else:
            if verbose:
                print(" Found 0 exact matches")

    # 2. CLEANED MATCH
    if "cleaned" in match_types:
        if verbose:
            print("\nPerforming cleaned match...")

        cleaned_matches = (
            check_df.select(["_check_idx", "_cleaned", "_compare_val", "_upper"])
            .join(
                base_df.select(["_base_idx", "_cleaned", "_compare_val", "_upper"]),
                on="_cleaned",
                how="inner",
                suffix="_base",
            )
            .filter(
                (pl.col("_cleaned") != "")  # Not empty
                & (
                    pl.col("_upper") != pl.col("_upper_base")
                )  # Not already matched by exact
            )
        )

        if debug:
            print(f"\nCleaned match candidates: {len(cleaned_matches)}")
            if len(cleaned_matches) > 0:
                print("Sample cleaned matches:")
                print(cleaned_matches.head(5))

        if len(cleaned_matches) > 0:
            for row in cleaned_matches.iter_rows(named=True):
                pair = (row["_check_idx"], row["_base_idx"])
                if pair not in matched_pairs:
                    all_match_records.append(
                        {
                            "_check_idx": row["_check_idx"],
                            "_base_idx": row["_base_idx"],
                            "match_exact": 0,
                            "match_ignore_case": 0,
                            "match_cleaned": 1,
                            "match_like": 0,
                            "match_fuzzy": 0,
                            "matched_value": f"cleaned:{row['_compare_val_base']}",
                        }
                    )
                    matched_pairs.add(pair)

            if verbose:
                print(
                    f"✓ Found {len([r for r in all_match_records if r['match_cleaned'] == 1])} cleaned matches"
                )
        else:
            if verbose:
                print("✓ Found 0 cleaned matches")

    # 3. LIKE MATCH (contains - unidirectional: checklist in base)
    if "like" in match_types:
        if verbose:
            print("\nPerforming like match...")

        like_match_count = 0
        check_df_pd = check_df.select(
            ["_check_idx", "_upper", "_compare_val"]
        ).to_pandas()
        base_df_pd = base_df.select(["_base_idx", "_upper", "_compare_val"]).to_pandas()

        for _, check_row in check_df_pd.iterrows():
            check_val = check_row["_upper"]
            if not check_val or check_val == "" or len(check_val) == 0:
                continue

            # Find base values that CONTAIN the checklist value
            mask = base_df_pd["_upper"].str.contains(check_val, regex=False, na=False)
            matched_base = base_df_pd[mask]

            if debug and len(matched_base) > 0:
                print(
                    f"\nChecklist '{check_val}' found in {len(matched_base)} base values:"
                )
                print(matched_base[["_upper", "_compare_val"]].head(3))

            for _, base_row in matched_base.iterrows():
                pair = (check_row["_check_idx"], base_row["_base_idx"])
                # Skip if exact match
                if check_val == base_row["_upper"]:
                    continue

                if pair not in matched_pairs:
                    all_match_records.append(
                        {
                            "_check_idx": check_row["_check_idx"],
                            "_base_idx": base_row["_base_idx"],
                            "match_exact": 0,
                            "match_ignore_case": 0,
                            "match_cleaned": 0,
                            "match_like": 1,
                            "match_fuzzy": 0,
                            "matched_value": f"like:{base_row['_compare_val']}",
                        }
                    )
                    matched_pairs.add(pair)
                    like_match_count += 1

        if verbose:
            print(f" Found {like_match_count} like matches")

    # 4. FUZZY MATCH
    if "fuzzy" in match_types:
        if verbose:
            print(f"\nPerforming fuzzy match (threshold: {fuzzy_threshold})...")

        check_df_pd = check_df.select(
            ["_check_idx", "_upper", "_compare_val"]
        ).to_pandas()
        base_df_pd = base_df.select(["_base_idx", "_upper", "_compare_val"]).to_pandas()

        fuzzy_match_count = 0
        total_check = len(check_df_pd)

        for idx, check_row in check_df_pd.iterrows():
            if verbose and idx % 20 == 0:
                print(f" Fuzzy matching {idx}/{total_check}...")

            check_val = check_row["_upper"]
            if not check_val or check_val == "":
                continue

            for _, base_row in base_df_pd.iterrows():
                base_val = base_row["_upper"]
                if not base_val or base_val == "":
                    continue

                pair = (check_row["_check_idx"], base_row["_base_idx"])
                if pair in matched_pairs:
                    continue

                similarity = fuzz.ratio(check_val, base_val)
                if similarity >= fuzzy_threshold:
                    all_match_records.append(
                        {
                            "_check_idx": check_row["_check_idx"],
                            "_base_idx": base_row["_base_idx"],
                            "match_exact": 0,
                            "match_ignore_case": 0,
                            "match_cleaned": 0,
                            "match_like": 0,
                            "match_fuzzy": 1,
                            "matched_value": f"fuzzy:{base_row['_compare_val']}",
                        }
                    )
                    matched_pairs.add(pair)
                    fuzzy_match_count += 1

        if verbose:
            print(f" Found {fuzzy_match_count} fuzzy matches")

    # Convert matches to Polars DataFrame
    if all_match_records:
        matches_df = pl.DataFrame(all_match_records)
    else:
        schema = {
            "_check_idx": pl.Int64,
            "_base_idx": pl.Int64,
            "match_exact": pl.Int64,
            "match_ignore_case": pl.Int64,
            "match_cleaned": pl.Int64,
            "match_like": pl.Int64,
            "match_fuzzy": pl.Int64,
            "matched_value": pl.Utf8,
        }
        matches_df = pl.DataFrame(schema=schema)

    # Build final result dataframe
    if verbose:
        print("\nBuilding result dataframe...")

    results = []

    # ==== MATCHED RECORDS ====
    if len(matches_df) > 0:
        # Join with checklist table
        matched_result = matches_df.join(check_df, on="_check_idx", how="left")

        # Join with base table
        matched_result = matched_result.join(
            base_df, on="_base_idx", how="left", suffix="_base"
        )

        # Rename columns with prefixes
        rename_dict = {}
        for col in check_cols:
            if col in matched_result.columns:
                rename_dict[col] = f"checklist_{col}"

        for col in base_cols:
            col_base = f"{col}_base"
            if col_base in matched_result.columns:
                rename_dict[col_base] = f"base_{col}"
            elif (
                col in matched_result.columns
                and f"checklist_{col}" not in rename_dict.values()
            ):
                rename_dict[col] = f"base_{col}"

        matched_result = matched_result.rename(rename_dict)

        # Keep only enabled match type columns and cast to Int64
        match_cols_to_keep = []
        for mt in match_types:
            col_name = f"match_{mt}"
            if col_name in matched_result.columns:
                matched_result = matched_result.with_columns(
                    [pl.col(col_name).cast(pl.Int64)]
                )
                match_cols_to_keep.append(col_name)

        # Add matched_values column
        if include_matched_values:
            if "matched_value" in matched_result.columns:
                matched_result = matched_result.rename(
                    {"matched_value": "matched_values"}
                )
        else:
            if "matched_value" in matched_result.columns:
                matched_result = matched_result.drop("matched_value")

        # Add source flag
        matched_result = matched_result.with_columns(
            [pl.lit("both").alias("source_flag")]
        )

        # Select final columns
        final_cols = (
            [
                f"checklist_{col}"
                for col in check_cols
                if f"checklist_{col}" in matched_result.columns
            ]
            + [
                f"base_{col}"
                for col in base_cols
                if f"base_{col}" in matched_result.columns
            ]
            + match_cols_to_keep
            + ["source_flag"]
        )

        if include_matched_values and "matched_values" in matched_result.columns:
            final_cols.append("matched_values")

        matched_result = matched_result.select(
            [col for col in final_cols if col in matched_result.columns]
        )
        results.append(matched_result)

        if verbose:
            print(f" Added {len(matched_result)} matched records")

        # Get matched indices
        matched_check_idx = set()
        matched_base_idx = set()
        if len(matches_df) > 0:
            matched_check_idx = set(matches_df["_check_idx"].to_list())
            matched_base_idx = set(matches_df["_base_idx"].to_list())

    # ===== UNMATCHED CHECKLIST RECORDS =====
    if matched_check_idx:
        unmatched_check = check_df.filter(
            ~pl.col("_check_idx").is_in(list(matched_check_idx))
        )
    else:
        unmatched_check = check_df

    if len(unmatched_check) > 0:
        # Rename checklist columns
        rename_dict = {col: f"checklist_{col}" for col in check_cols}
        unmatched_check = unmatched_check.rename(rename_dict)

        # Add null base columns
        for col in base_cols:
            unmatched_check = unmatched_check.with_columns(
                [pl.lit(None).alias(f"base_{col}")]
            )

        # Add match flags (all 0) - only for enabled types, cast to Int64
        for mt in match_types:
            unmatched_check = unmatched_check.with_columns(
                [pl.lit(0).cast(pl.Int64).alias(f"match_{mt}")]
            )

        if include_matched_values:
            unmatched_check = unmatched_check.with_columns(
                [pl.lit("").alias("matched_values")]
            )

        # Add source flag
        unmatched_check = unmatched_check.with_columns(
            [pl.lit("checklist_table").alias("source_flag")]
        )

        # Select final columns
        final_cols = (
            [f"checklist_{col}" for col in check_cols]
            + [f"base_{col}" for col in base_cols]
            + [f"match_{mt}" for mt in match_types]
            + ["source_flag"]
        )

        if include_matched_values:
            final_cols.append("matched_values")

        unmatched_check = unmatched_check.select(
            [col for col in final_cols if col in unmatched_check.columns]
        )
        results.append(unmatched_check)

        if verbose:
            print(f" Added {len(unmatched_check)} unmatched checklist records")

    # ======= UNMATCHED BASE RECORDS =======
    if matched_base_idx:
        unmatched_base = base_df.filter(
            ~pl.col("_base_idx").is_in(list(matched_base_idx))
        )
    else:
        unmatched_base = base_df

    if len(unmatched_base) > 0:
        # Rename base columns
        rename_dict = {col: f"base_{col}" for col in base_cols}
        unmatched_base = unmatched_base.rename(rename_dict)

        # Add null checklist columns
        for col in check_cols:
            unmatched_base = unmatched_base.with_columns(
                [pl.lit(None).alias(f"checklist_{col}")]
            )

        # Add match flags (all 0) - only for enabled types, cast to Int64
        for mt in match_types:
            unmatched_base = unmatched_base.with_columns(
                [pl.lit(0).cast(pl.Int64).alias(f"match_{mt}")]
            )

        if include_matched_values:
            unmatched_base = unmatched_base.with_columns(
                [pl.lit("").alias("matched_values")]
            )

        # Add source flag
        unmatched_base = unmatched_base.with_columns(
            [pl.lit("base_table").alias("source_flag")]
        )

        # Select final columns
        final_cols = (
            [f"checklist_{col}" for col in check_cols]
            + [f"base_{col}" for col in base_cols]
            + [f"match_{mt}" for mt in match_types]
            + ["source_flag"]
        )

        if include_matched_values:
            final_cols.append("matched_values")

        unmatched_base = unmatched_base.select(
            [col for col in final_cols if col in unmatched_base.columns]
        )
        results.append(unmatched_base)

        if verbose:
            print(f" Added {len(unmatched_base)} unmatched base records")

    # Combine all results
    if results:
        result_pl = pl.concat(results, how="diagonal")
    else:
        result_pl = pl.DataFrame()

    # Convert back to pandas
    result_df = result_pl.to_pandas()

    elapsed = time.time() - start_time

    # Print summary
    if verbose:
        print("\n" + "=" * 80)
        print("COMPARISON SUMMARY")
        print("=" * 80)
        print(f"Execution time: {elapsed:.2f} seconds")
        print(f"Total records in result: {len(result_df)}")
        print("\nSource Distribution:")
        print(f" - Both tables: {(result_df['source_flag'] == 'both').sum()}")
        print(f" - Base table only: {(result_df['source_flag'] == 'base_table').sum()}")
        print(
            f" - Checklist table only: {(result_df['source_flag'] == 'checklist_table').sum()}"
        )

        matched_df = result_df[result_df["source_flag"] == "both"]
        if len(matched_df) > 0:
            print("\nMatch Type Distribution:")
            for mt in match_types:
                col_name = f"match_{mt}"
                if col_name in matched_df.columns:
                    count = matched_df[col_name].sum()
                    print(f" - {mt.replace('_', ' ').title()}: {count}")

            # Check for multiple matches
            if include_matched_values and "matched_values" in matched_df.columns:
                check_col = [
                    col for col in result_df.columns if col.startswith("checklist_")
                ][0]
                multi_match = matched_df.groupby(check_col).size()
                multi_match = multi_match[multi_match > 1]
                if len(multi_match) > 0:
                    print(
                        f"\n⚠️ Warning: {len(multi_match)} checklist entries matched multiple base entries"
                    )

        print("=" * 80 + "\n")

    return result_df

