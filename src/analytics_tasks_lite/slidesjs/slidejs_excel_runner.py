"""
slidejs Excel Test Runner - UPDATED WITH AGENDA & HELP SUPPORT
"""
import pandas as pd
import json
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import traceback
from datetime import datetime
import numpy as np
import shutil
import tempfile
from .slidejs import slidejs

class ConfigValidator:
    """Validates Excel configuration before running tests."""

    VALID_LAYOUTS = ["single", "two-column", "three-column", "grid-2x2"]
    VALID_OVERLAY_POSITIONS = [
        "top-right",
        "top-left",
        "bottom-right",
        "bottom-left",
        "center",
    ]
    VALID_IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".svg"]
    VALID_CHART_EXTENSIONS = [".html"] + VALID_IMAGE_EXTENSIONS

    REQUIRED_COLUMNS = {
        "Global_Config": ["Parameter", "Type", "Default Value"],
        "Slide_Config": ["Test_ID", "Slide_Num", "layout"],
        "Chart_Config": ["Test_ID", "Slide_Num", "Chart_Pos", "Source_Path"],
        "Theme_Config": ["Test_ID"],
        "Font_Config": ["Test_ID"],
        # "Agenda_Config": ["Test_ID", "Slide_Num", "agenda_statement"],
        "Help": ["help_text"],
        "Summary_Config": ["Test_ID", "summary_text"],
        "Reference_Config": [
            "Test_ID",
            "text",
            "hyperlink",
            "group",
            "group_column_number",
        ],
        "Custom_Box_config": [
            "Test_ID",
            "Slide_Num",
            "Box_ID",
            "Source_Type",
            "Source_Path",
            "Top",
            "Left",
        ],
        # Deep_Overview_Config is optional — validated separately
    }

    def __init__(self, loaded_data: Dict[str, pd.DataFrame]):
        self.loaded_data = loaded_data
        self.errors = []
        self.warnings = []

    def validate_all(self) -> bool:
        print("\n🔍 Running configuration validation...")

        self.errors = []
        self.warnings = []

        self.validate_required_sheets()
        self.validate_column_structure()
        self.validate_slide_config()
        self.validate_chart_config()
        self.validate_chart_layout_compatibility()
        self.validate_file_paths()
        self.validate_theme_config()
        self.validate_font_config()
        self.validate_test_id_consistency()
        self.validate_agenda_config()
        self.validate_help_config()
        self.validate_summary_config()
        self.validate_reference_config()
        self.validate_custom_box_config()
        self.validate_deep_overview_config()

        self._report_results()

        return len(self.errors) == 0

    def validate_summary_config(self):
        """Validate Summary_Config sheet if present."""
        if "Summary_Config" not in self.loaded_data:
            # Summary is optional
            return

        df = self.loaded_data["Summary_Config"]

        required = ["Test_ID", "summary_text"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            self.errors.append(f"Summary_Config missing required columns: {missing}")
            return

        # Check for empty summary_text
        for idx, row in df.iterrows():
            summary_text = row.get("summary_text", "")

            if pd.isna(summary_text) or str(summary_text).strip() == "":
                self.warnings.append(
                    f"Summary_Config row {idx + 2}: summary_text is empty"
                )

    def validate_reference_config(self):
        """Validate Reference_Config sheet if present."""
        if "Reference_Config" not in self.loaded_data:
            # Reference is optional
            return

        df = self.loaded_data["Reference_Config"]

        required = ["Test_ID", "text", "hyperlink", "group", "group_column_number"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            self.errors.append(f"Reference_Config missing required columns: {missing}")
            return

        # Check for empty text
        for idx, row in df.iterrows():
            text = row.get("text", "")

            if pd.isna(text) or str(text).strip() == "":
                self.warnings.append(f"Reference_Config row {idx + 2}: text is empty")

            # Check if hyperlink=1 but unc is empty
            hyperlink = row.get("hyperlink", "0")
            unc = row.get("unc", "")

            if str(hyperlink).strip() == "1":
                if pd.isna(unc) or str(unc).strip() == "":
                    self.warnings.append(
                        f"Reference_Config row {idx + 2}: hyperlink=1 but unc is empty"
                    )

    def validate_custom_box_config(self):
        """Validate Custom_Box_Config sheet if present."""
        if "Custom_Box_config" not in self.loaded_data:
            # Custom boxes are optional
            return

        df = self.loaded_data["Custom_Box_config"]

        required = [
            "Test_ID",
            "Slide_Num",
            "Box_ID",
            "Source_Type",
            "Source_Path",
            "Top",
            "Left",
        ]
        missing = [col for col in required if col not in df.columns]
        if missing:
            self.errors.append(f"Custom_Box_Config missing required columns: {missing}")
            return

        # Check for empty required fields
        for idx, row in df.iterrows():
            test_id = row.get("Test_ID", "")
            slide_num = row.get("Slide_Num", "")
            box_id = row.get("Box_ID", "")

            if pd.isna(test_id) or str(test_id).strip() == "":
                self.errors.append(f"Custom_Box_Config row {idx + 2}: Test_ID is empty")

            # Check if hyperlink=1 but unc is empty
            if pd.isna(slide_num) or str(slide_num).strip() == "":
                self.errors.append(
                    f"Custom_Box_Config row {idx + 2}: Slide_Num is empty"
                )

            if pd.isna(box_id) or str(box_id).strip() == "":
                self.errors.append(f"Custom_Box_Config row {idx + 2}: Box_ID is empty")

            # Check Source_Path
            source_path = row.get("Source_Path", "")
            if pd.isna(source_path) or str(source_path).strip() == "":
                self.errors.append(
                    f"Custom_Box_Config row {idx + 2}: Source_Path is empty"
                )

            # Validate Source_Type
            source_type = row.get("Source_Type", "")
            valid_types = ["TEXT", "HTML", "IMAGE", "HTMLTABLE", "SVG"]
            if source_type not in valid_types:
                self.warnings.append(
                    f"Custom_Box_Config row {idx + 2}: Invalid Source_Type '{source_type}'. Valid: {valid_types}"
                )

            # Validate positioning (Top, Left must have units)
            top = row.get("Top", "")
            left = row.get("Left", "")

            if not self._validate_css_dimension(top):
                self.warnings.append(
                    f"Custom_Box_Config row {idx + 2}: Top '{top}' should have units (px or %)"
                )

            if not self._validate_css_dimension(left):
                self.warnings.append(
                    f"Custom_Box_Config row {idx + 2}: Left '{left}' should have units (px or %)"
                )

        # Check for duplicate Box_IDs within same slide
        for test_id in df["Test_ID"].dropna().unique():
            test_boxes = df[df["Test_ID"] == test_id]
            for slide_num in test_boxes["Slide_Num"].dropna().unique():
                slide_boxes = test_boxes[test_boxes["Slide_Num"] == slide_num]
                box_ids = slide_boxes["Box_ID"].tolist()
                duplicates = [bid for bid in box_ids if box_ids.count(bid) > 1]
                if duplicates:
                    self.errors.append(
                        f"Custom_Box_Config: Duplicate Box_IDs on Slide {slide_num}: {set(duplicates)}"
                    )

        print(f"  ✓ Custom_Box_Config validated: {len(df)} box(es) defined")

    def validate_deep_overview_config(self):
        """Validate Deep_Overview_Config sheet if present (optional feature)."""
        if "Deep_Overview_Config" not in self.loaded_data:
            return  # Fully optional

        df = self.loaded_data["Deep_Overview_Config"]

        required = ["Test_ID", "Slide_Num", "Overview_ID", "Content_Type", "Content", "Order"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            self.errors.append(f"Deep_Overview_Config missing required columns: {missing}")
            return

        valid_content_types = ["heading", "subheading", "paragraph", "list_item", "divider", "html"]

        for idx, row in df.iterrows():
            test_id      = row.get("Test_ID", "")
            slide_num    = row.get("Slide_Num", "")
            overview_id  = row.get("Overview_ID", "")
            content_type = str(row.get("Content_Type", "")).strip()
            content      = str(row.get("Content", "")).strip()

            if pd.isna(test_id) or str(test_id).strip() == "":
                self.errors.append(f"Deep_Overview_Config row {idx + 2}: Test_ID is empty")
            if pd.isna(slide_num) or str(slide_num).strip() == "":
                self.errors.append(f"Deep_Overview_Config row {idx + 2}: Slide_Num is empty")
            if pd.isna(overview_id) or str(overview_id).strip() == "":
                self.errors.append(f"Deep_Overview_Config row {idx + 2}: Overview_ID is empty")
            if content_type and content_type not in valid_content_types:
                self.warnings.append(
                    f"Deep_Overview_Config row {idx + 2}: Content_Type '{content_type}' "
                    f"not in {valid_content_types}"
                )

        print(f"  ✓ Deep_Overview_Config validated: {len(df)} row(s) defined")

    def _validate_css_dimension(self, value):
        """Check if dimension has valid CSS units (px or %)."""
        if pd.isna(value) or value == "":
            return False
        value_str = str(value).strip()
        if value_str == "auto":
            return True
        # Check for px or %
        if value_str.endswith("px") or value_str.endswith("%"):
            return True
        return False

    def validate_agenda_config(self):
        """Validate Agenda_Config sheet if present."""
        if "Agenda_Config" not in self.loaded_data:
            # This is now OK - agenda is optional
            return

        df = self.loaded_data["Agenda_Config"]

        required = ["Test_ID", "Slide_Num", "agenda_statement"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            self.errors.append(f"Agenda_Config missing required columns: {missing}")
            return

        # Check for empty agenda_statement when agenda_starter is also empty
        for idx, row in df.iterrows():
            starter = row.get("agenda_starter", "")
            statement = row.get("agenda_statement", "")

            if pd.isna(starter) or starter == "":
                starter = ""
            if pd.isna(statement) or statement == "":
                statement = ""

            if starter == "" and statement == "":
                self.warnings.append(
                    f"Agenda_Config row {idx + 2}: Both agenda_starter and agenda_statement are empty"
                )

        # Check for valid Slide_Num references
        if "Slide_Config" in self.loaded_data:
            slide_df = self.loaded_data["Slide_Config"]
            valid_slides = set(slide_df["Slide_Num"].astype(str).unique())

            for idx, row in df.iterrows():
                slide_num = str(row.get("Slide_Num", ""))
                if slide_num not in valid_slides:
                    self.warnings.append(
                        f"Agenda_Config row {idx + 2}: Slide_Num '{slide_num}' not found in Slide_Config"
                    )

    def validate_help_config(self):
        """Validate Help sheet if present."""
        if "Help" not in self.loaded_data:
            self.warnings.append("Help sheet not found. Help button will show default text.")
            return

        df = self.loaded_data["Help"]

        if "help_text" not in df.columns:
            self.errors.append("Help sheet missing 'help_text' column")
            return

        # Check if cell A2 has content
        if len(df) < 1:
            self.warnings.append("Help sheet has no content in cell A2")
        else:
            help_text = df["help_text"].iloc[0]
            if pd.isna(help_text) or str(help_text).strip() == "":
                self.warnings.append("Help text is empty")

    def validate_required_sheets(self):
        """Check that all required sheets are present."""
        required_sheets = ["Slide_Config", "Chart_Config"]
        for sheet in required_sheets:
            if sheet not in self.loaded_data:
                self.errors.append(f"Missing required sheet: '{sheet}'")

    def validate_column_structure(self):
        """Validate column structure for each sheet."""
        for sheet_name, required_cols in self.REQUIRED_COLUMNS.items():
            if sheet_name not in self.loaded_data:
                continue
            df = self.loaded_data[sheet_name]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                self.errors.append(
                    f"Sheet '{sheet_name}' missing required columns: {missing_cols}"
                )

    def validate_slide_config(self):
        if "Slide_Config" not in self.loaded_data:
            return
        df = self.loaded_data["Slide_Config"]
        if "Test_ID" not in df.columns or "layout" not in df.columns:
            return
        empty_test_ids = df["Test_ID"].isna().sum()
        if empty_test_ids > 0:
            self.errors.append(
                f"Slide_Config has {empty_test_ids} row(s) with empty Test_ID"
            )
        unique_layouts = df["layout"].dropna().unique()
        invalid_layouts = [l for l in unique_layouts if l not in self.VALID_LAYOUTS]
        if invalid_layouts:
            self.errors.append(
                f"Invalid layout types in Slide_Config: {invalid_layouts}. "
                f"Valid options: {self.VALID_LAYOUTS}"
            )

    def validate_chart_config(self):
        if "Chart_Config" not in self.loaded_data:
            return
        df = self.loaded_data["Chart_Config"]
        required = ["Test_ID", "Slide_Num", "Source_Path"]
        if not all(col in df.columns for col in required):
            return
        empty_paths = df["Source_Path"].isna() | (df["Source_Path"] == "")
        if empty_paths.sum() > 0:
            self.errors.append(
                f"Chart_Config has {empty_paths.sum()} row(s) with empty Source_Path"
            )

    def validate_chart_layout_compatibility(self):
        if (
            "Slide_Config" not in self.loaded_data
            or "Chart_Config" not in self.loaded_data
        ):
            return
        slide_df = self.loaded_data["Slide_Config"]
        chart_df = self.loaded_data["Chart_Config"]
        layout_requirements = {
            "single": (1, 1),
            "two-column": (2, 2),
            "three-column": (3, 3),
            "grid-2x2": (4, 4),
        }
        for test_id in slide_df["Test_ID"].dropna().unique():
            test_slides = slide_df[slide_df["Test_ID"] == test_id]
            for _, slide_row in test_slides.iterrows():
                slide_num = slide_row["Slide_Num"]
                layout = slide_row["layout"]
                if layout not in layout_requirements:
                    continue
                chart_count = len(
                    chart_df[
                        (chart_df["Test_ID"] == test_id)
                        & (chart_df["Slide_Num"].astype(str) == str(slide_num))
                    ]
                )
                min_charts, max_charts = layout_requirements[layout]
                if chart_count < min_charts:
                    self.errors.append(
                        f"Test '{test_id}', Slide {slide_num}: "
                        f"Layout '{layout}' requires {min_charts} chart(s), found {chart_count}"
                    )

    def validate_file_paths(self):
        if "Chart_Config" not in self.loaded_data:
            return
        df = self.loaded_data["Chart_Config"]
        missing_files = []
        for _, row in df.iterrows():
            source_path = row.get("Source_Path")
            if pd.isna(source_path) or source_path == "":
                continue
            if isinstance(source_path, str) and source_path.startswith("TEXT:"):
                continue
            file_path = Path(source_path)
            if not file_path.exists():
                test_id = row.get("Test_ID", "unknown")
                slide_num = row.get("Slide_Num", "unknown")
                missing_files.append(f"{test_id}/Slide{slide_num}: {source_path}")
        if missing_files:
            self.errors.append(
                f"Missing chart files ({len(missing_files)}):\n  "
                + "\n  ".join(missing_files[:5])
            )

    def validate_theme_config(self):
        if "Theme_Config" not in self.loaded_data:
            return
        df = self.loaded_data["Theme_Config"]
        color_fields = [
            # Core fields (original)
            "primary", "text", "muted", "light",
            "content_bg", "slide_bg", "header_border",
            # New semantic fields
            "bg_dark", "bg", "bg_light", "text_muted",
            "highlight", "border", "border_muted",
            "secondary", "danger", "warning", "success", "info",
        ]
        has_color_fields = any(field in df.columns for field in color_fields)
        if not has_color_fields:
            self.warnings.append(
                f"Theme_Config has no color fields. Expected: {color_fields}"
            )

    def validate_font_config(self):
        if "Font_Config" not in self.loaded_data:
            return
        df = self.loaded_data["Font_Config"]
        font_fields = ["title", "subtitle", "body", "overlay", "footnote", "footer"]
        has_font_fields = any(field in df.columns for field in font_fields)
        if not has_font_fields:
            self.warnings.append(
                f"Font_Config has no font size fields. Expected: {font_fields}"
            )

    def validate_test_id_consistency(self):
        """Check that Test_IDs are consistent across sheets."""
        test_ids_by_sheet = {}
        for sheet_name in [
            "Slide_Config",
            "Chart_Config",
            "Theme_Config",
            "Font_Config",
            "Agenda_Config",
        ]:
            if sheet_name not in self.loaded_data:
                continue
            df = self.loaded_data[sheet_name]
            if "Test_ID" in df.columns:
                test_ids_by_sheet[sheet_name] = set(df["Test_ID"].dropna().unique())
        if not test_ids_by_sheet:
            return
        if "Slide_Config" not in test_ids_by_sheet:
            return
        primary_test_ids = test_ids_by_sheet["Slide_Config"]
        if "Chart_Config" in test_ids_by_sheet:
            chart_test_ids = test_ids_by_sheet["Chart_Config"]
            missing_in_charts = primary_test_ids - chart_test_ids
            if missing_in_charts:
                self.errors.append(
                    f"Test_IDs in Slide_Config but missing from Chart_Config: {missing_in_charts}"
                )

    def _report_results(self):
        print("\n" + "=" * 60)
        print("📋 VALIDATION RESULTS")
        print("=" * 60)
        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")
            return
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        print("\n" + "=" * 60)
        if self.errors:
            print("\n❌ Configuration has errors. Please fix before running tests.")
        else:
            print("\n⚠️  Configuration has warnings but can proceed.")


class VersionChecker:
    """Checks Excel template version compatibility."""

    RUNNER_VERSION = "2.0.0"
    COMPATIBLE_TEMPLATE_VERSIONS = ["2.0.x", "1.5.x"]

    def __init__(self, loaded_data: dict):
        self.loaded_data = loaded_data
        self.template_version = None
        self.is_compatible = True
        self.warnings = []

    def check_compatibility(self) -> bool:
        """Check if template version is compatible with runner."""
        self.template_version = self._extract_template_version()
        if not self.template_version:
            self.warnings.append("No version information found in Excel template.")
            return True

        print(f"\n📌 Excel Template Version: {self.template_version}")
        print(f"📌 Runner Version: {self.RUNNER_VERSION}")
        return True

    def _extract_template_version(self) -> Optional[str]:
        if "Version" in self.loaded_data:
            version_df = self.loaded_data["Version"]
            for col in ["Version", "Template_Version", "TEMPLATE_VERSION"]:
                if col in version_df.columns:
                    version_val = (
                        version_df[col].dropna().iloc[0]
                        if len(version_df) > 0
                        else None
                    )
                    if version_val:
                        return str(version_val).strip()
        return None


class PathNormalizer:
    """Handle paths from Excel."""

    @staticmethod
    def normalize_path(path_str: Union[str, Path]) -> Path:
        if isinstance(path_str, Path):
            return path_str
        if not isinstance(path_str, str):
            path_str = str(path_str)
        path_str = path_str.strip().replace("\\", "/")
        return Path(path_str)

    @staticmethod
    def normalize_and_validate(
        path_str: Union[str, Path], base_path: Path = None, must_exist: bool = True
    ) -> Path:
        normalized = PathNormalizer.normalize_path(path_str)
        if base_path and not normalized.is_absolute():
            normalized = base_path / normalized
        if must_exist and not normalized.exists():
            raise FileNotFoundError(
                f"Path not found: {normalized}\n  Original path string: {path_str}"
            )
        return normalized


class slidejsExcelRunner:
    """Reads Excel configurations and runs slidejs tests."""

    def __init__(self, excel_path: Union[str, Path]):
        self.excel_path = Path(excel_path)
        self.test_results = []
        self.loaded_data = {}
        self.load_excel_data()

        version_checker = VersionChecker(self.loaded_data)
        version_checker.check_compatibility()

    def load_summary_config(self, test_id: str) -> List[str]:
        """Load summary items for Quick Insights overlay."""
        summary_items = []

        if "Summary_Config" not in self.loaded_data:
            print("ℹ️ No Summary_Config sheet found, Quick Insights will be empty")
            return summary_items

        df = self.loaded_data["Summary_Config"]
        print(f"\n📊 Loading Summary for test_id='{test_id}'")

        # Filter for this test
        df["Test_ID_str"] = df["Test_ID"].astype(str).str.strip()
        test_id_str = str(test_id).strip()
        test_summary = df[df["Test_ID_str"] == test_id_str]

        print(f"  Found {len(test_summary)} summary item(s)")

        # Sort by order if column exists
        if "order" in df.columns:
            test_summary = test_summary.sort_values("order")

        for idx, row in test_summary.iterrows():
            summary_text = self.safe_get(row, "summary_text", "")

            # Skip if text is empty
            if pd.isna(summary_text) or str(summary_text).strip() == "":
                print(f"  ⚠️  Skipping row {idx}: summary_text is empty")
                continue

            summary_text = str(summary_text).strip()
            summary_items.append(summary_text)
            print(f"  ✓ Summary item: {summary_text[:60]}...")

        return summary_items

    def load_reference_config(self, test_id: str) -> List[Dict[str, Any]]:
        """Load reference items for automatic reference slide generation."""
        reference_items = []

        if "Reference_Config" not in self.loaded_data:
            print(" ℹ️ No Reference_Config sheet found, skipping reference slide")
            return reference_items

        df = self.loaded_data["Reference_Config"]
        print(f"\n🔗 Loading References for test_id='{test_id}'")

        # Filter for this test
        df["Test_ID_str"] = df["Test_ID"].astype(str).str.strip()
        test_id_str = str(test_id).strip()
        test_references = df[df["Test_ID_str"] == test_id_str]

        print(f"  Found {len(test_references)} reference item(s)")

        for idx, row in test_references.iterrows():
            text = self.safe_get(row, "text", "")

            # Skip if text is empty
            if pd.isna(text) or str(text).strip() == "":
                print(f"  ⚠️  Skipping row {idx}: text is empty")
                continue

            hyperlink = self.safe_get(row, "hyperlink", "0")
            unc = self.safe_get(row, "unc", "")
            group = self.safe_get(row, "group", "")
            group_column_number = self.safe_get(row, "group_column_number", "1")
            order = self.safe_get(row, "order", "999")
            unc_keywords = self.safe_get(row, "unc_keywords", "")

            # Convert to proper types
            try:
                hyperlink = int(hyperlink) if hyperlink else 0
            except (ValueError, TypeError):
                hyperlink = 0

            try:
                group_column_number = (
                    int(group_column_number) if group_column_number else 1
                )
            except (ValueError, TypeError):
                group_column_number = 1

            try:
                order = int(order) if order else 999
            except (ValueError, TypeError):
                order = 999

            # Validate hyperlink logic
            if hyperlink == 1 and (pd.isna(unc) or str(unc).strip() == ""):
                print(
                    f"  ⚠️  Row {idx}: hyperlink=1 but unc is empty, treating as plain text"
                )
                hyperlink = 0

            # Build item
            reference_items.append(
                {
                    "text": str(text).strip(),
                    "hyperlink": hyperlink,
                    "unc": str(unc).strip() if unc else "",
                    "group": str(group).strip(),
                    "group_column_number": group_column_number,
                    "order": order,
                    "unc_keywords": str(unc_keywords).strip() if unc_keywords and not pd.isna(unc_keywords) else "",
                }
            )

            link_type = "link" if hyperlink == 1 else "text"
            print(
                f"  ✓ Reference [{link_type}] [col={group_column_number}] [{group}]: {text[:50]}..."
            )

        print(f"  ✓ Total references loaded: {len(reference_items)}")
        return reference_items

    def load_svg_icons(self) -> Dict[str, str]:
        """
        Load the svg_icons sheet if present.
        Returns dict: { icon_name_lower: svg_inner_html }
        """
        icons = {}
        if "svg_icons" not in self.loaded_data and "Svg_Icons" not in self.loaded_data:
            return icons

        sheet_key = "svg_icons" if "svg_icons" in self.loaded_data else "Svg_Icons"
        df = self.loaded_data[sheet_key]

        # Accept 'bubble_icon'/'icon_name'/'name' for the name col, 'svg'/'svg_content' for svg
        name_col = next((c for c in df.columns if c.lower() in ("bubble_icon", "icon_name", "name")), None)
        svg_col  = next((c for c in df.columns if c.lower() in ("svg", "svg_content")), None)

        if not name_col or not svg_col:
            print(f"  ⚠️  svg_icons sheet: could not find name/svg columns (found: {list(df.columns)})")
            return icons

        for _, row in df.iterrows():
            name = self.safe_get(row, name_col, "")
            svg  = self.safe_get(row, svg_col,  "")
            if name and svg and not pd.isna(name) and not pd.isna(svg):
                icons[str(name).strip().lower()] = str(svg).strip()

        print(f"  ✓ Loaded {len(icons)} custom SVG icon(s) from '{sheet_key}' sheet")
        return icons

    def _resolve_deep_dive_content(self, content: str, content_type: str,
                                   excel_base_path) -> str:
        """
        Resolve Content field: if it looks like a file path (.htmltable/.html),
        read and return the file contents; otherwise return as-is.
        """
        if not content or content_type == "divider":
            return content

        stripped = content.strip()

        # Check if it references an external file
        if stripped.lower().endswith((".htmltable", ".html", ".htm")):
            try:
                file_path = Path(stripped)
                if not file_path.is_absolute() and excel_base_path:
                    file_path = excel_base_path / file_path
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        raw = f.read().strip()
                    print(f"    ✓ Loaded content file: {file_path.name} ({len(raw):,} chars)")
                    return raw
                else:
                    print(f"    ⚠️  Content file not found: {file_path} — using text as-is")
            except Exception as exc:
                print(f"    ⚠️  Error reading content file '{stripped}': {exc} — using text as-is")

        return content

    def load_deep_overview_config(self, test_id: str, slide_num: int) -> List[Dict[str, Any]]:
        """
        Load Deep Dive panels for a specific slide.

        • Groups rows by Overview_ID (within test_id + slide_num).
        • Meta fields (Button_Icon, Button_Tooltip, Top, Left, Width, Height,
          Z_index, BG_Color, Title, Subtitle) are taken from the FIRST non-blank
          occurrence across all rows for that Overview_ID.  If the same field has
          more than one distinct non-blank value a WARNING is printed so the user
          can spot accidental inconsistencies.
        • Content field supports inline text OR a path to an .htmltable/.html file.
        • Button_Icon is resolved against the svg_icons sheet if present.
        """
        if "Deep_Overview_Config" not in self.loaded_data:
            return []

        df = self.loaded_data["Deep_Overview_Config"]
        excel_base = self.excel_path.parent
        svg_icons  = self.load_svg_icons()   # dict of name → svg innerHTML

        print(f"\n🔍 Loading Deep Dive config for test_id='{test_id}', slide={slide_num}")

        df["Test_ID_str"]   = df["Test_ID"].astype(str).str.strip()
        df["Slide_Num_str"] = df["Slide_Num"].astype(str).str.strip()

        test_id_str   = str(test_id).strip()
        slide_num_str = str(slide_num).strip()

        slide_rows = df[
            (df["Test_ID_str"] == test_id_str) &
            (df["Slide_Num_str"] == slide_num_str)
        ]

        if len(slide_rows) == 0:
            return []

        # Sort by Overview_ID then Order
        sort_cols = ["Overview_ID"]
        if "Order" in df.columns:
            sort_cols.append("Order")
        slide_rows = slide_rows.sort_values(sort_cols)

        # Meta fields that should be uniform across rows of the same Overview_ID
        META_FIELDS = [
            ("Button_Icon",    "bugfix"),
            ("Button_Tooltip", "Deep Dive"),
            ("Button_Top",     ""),        # optional: if blank, falls back to Top
            ("Button_Left",    ""),        # optional: if blank, falls back to Left
            ("Icon_Width",     ""),        # optional: SVG button width  e.g. 28px
            ("Icon_Height",    ""),        # optional: SVG button height e.g. 28px
            ("Top",            "20px"),
            ("Left",           "20px"),
            ("Width",          "340px"),
            ("Height",         "auto"),
            ("Z_index",        "1000"),
            ("BG_Color",       ""),
            ("Title",          ""),
            ("Subtitle",       ""),
        ]

        deep_dives = []

        for overview_id, group in slide_rows.groupby("Overview_ID", sort=False):
            overview_id = str(overview_id).strip()

            # ── Collect all non-blank values per meta field + warn on inconsistency ──
            meta = {}
            for field, default in META_FIELDS:
                if field not in group.columns:
                    meta[field] = default
                    continue

                values = []
                for _, r in group.iterrows():
                    v = self.safe_get(r, field, "")
                    if v not in (None, "", float("nan")) and not (
                        isinstance(v, float) and __import__("math").isnan(v)
                    ):
                        values.append(str(v).strip())

                distinct = list(dict.fromkeys(values))  # unique, order-preserving

                if len(distinct) > 1:
                    print(
                        f"  ⚠️  WARNING Deep_Overview_Config: Overview_ID='{overview_id}', "
                        f"Slide={slide_num} — field '{field}' has {len(distinct)} different "
                        f"values {distinct}. Using first: '{distinct[0]}'"
                    )

                meta[field] = distinct[0] if distinct else default

            # ── Resolve SVG icon ──
            icon_name = meta["Button_Icon"].lower()
            if icon_name in svg_icons:
                # Custom icon from svg_icons sheet — store the raw SVG markup
                custom_svg = svg_icons[icon_name]
                button_icon_resolved = f"__custom__:{custom_svg}"
                print(f"  ✓ Custom icon '{icon_name}' resolved from svg_icons sheet")
            else:
                # Fall back to built-in named icons (handled in the template)
                button_icon_resolved = meta["Button_Icon"]

            # ── Build content blocks ──
            content_blocks = []
            for _, row in group.iterrows():
                content_type = str(self.safe_get(row, "Content_Type", "paragraph")).strip()
                content      = self.safe_get(row, "Content", "")

                if pd.isna(content):
                    content = ""
                else:
                    content = str(content).strip()

                # Resolve file-based content
                content = self._resolve_deep_dive_content(content, content_type, excel_base)

                if content == "" and content_type != "divider":
                    continue  # skip blank non-divider rows

                try:
                    order = int(self.safe_get(row, "Order", 999))
                except (ValueError, TypeError):
                    order = 999

                content_blocks.append({
                    "content_type": content_type,
                    "content":      content,
                    "order":        order,
                })

            content_blocks.sort(key=lambda x: x["order"])

            deep_dives.append({
                "overview_id":    overview_id,
                "button_icon":    button_icon_resolved,
                "button_tooltip": meta["Button_Tooltip"],
                "button_top":     meta["Button_Top"] or meta["Top"],
                "button_left":    meta["Button_Left"] or meta["Left"],
                "icon_width":     meta["Icon_Width"],   # e.g. "28px" — sets --dd-btn-w
                "icon_height":    meta["Icon_Height"],  # e.g. "28px" — sets --dd-btn-h
                # Width: passed as --dd-width CSS var (overrides the default 40%)
                # Height, Top, Left for the panel are now handled by the curtain CSS
                "width":          meta["Width"],
                "z_index":        meta["Z_index"],
                "bg_color":       meta["BG_Color"],
                "title":          meta["Title"],
                "subtitle":       meta["Subtitle"],
                "content_blocks": content_blocks,
            })

            print(
                f"  ✓ Deep Dive '{overview_id}': {len(content_blocks)} block(s), "
                f"icon='{meta['Button_Icon']}', btn=({meta['Button_Top'] or meta['Top']}, {meta['Button_Left'] or meta['Left']}), "
                f"curtain-width={meta['Width'] or '40% (default)'}"
            )

        print(f"  ✓ Total deep dives for slide {slide_num}: {len(deep_dives)}")
        return deep_dives

    def load_custom_box_config(
        self, test_id: str, slide_num: int
    ) -> List[Dict[str, Any]]:
        """Load custom boxes for a specific slide."""
        custom_boxes = []

        if "Custom_Box_config" not in self.loaded_data:
            return custom_boxes

        df = self.loaded_data["Custom_Box_config"]
        print(f"\n📦 Loading Custom Boxes for test_id='{test_id}', slide={slide_num}")

        # Filter for this test and slide
        df["Test_ID_str"] = df["Test_ID"].astype(str).str.strip()
        df["Slide_Num_str"] = df["Slide_Num"].astype(str).str.strip()

        test_id_str = str(test_id).strip()
        slide_num_str = str(slide_num).strip()

        slide_boxes = df[
            (df["Test_ID_str"] == test_id_str) & (df["Slide_Num_str"] == slide_num_str)
        ]

        print(f"  Found {len(slide_boxes)} custom box(es)")

        # Sort by order if present
        if "Order" in df.columns:
            slide_boxes = slide_boxes.sort_values("Order")

        for idx, row in slide_boxes.iterrows():
            box_id = self.safe_get(row, "Box_ID", f"box_{idx}")
            source_type = self.safe_get(row, "Source_Type", "TEXT")
            source_path = self.safe_get(row, "Source_Path", "")

            # Skip if source_path is empty
            if pd.isna(source_path) or str(source_path).strip() == "":
                print(f"  ⚠️  Skipping box {box_id}: Source_Path is empty")
                continue

            # Build box configuration
            box_config = {
                "box_id": str(box_id).strip(),
                "source_type": str(source_type).strip().upper(),
                "source_path": str(source_path).strip(),
                "top": self.safe_get(row, "Top", "0px"),
                "left": self.safe_get(row, "Left", "0px"),
                "width": self.safe_get(row, "Width", "auto"),
                "height": self.safe_get(row, "Height", "auto"),
                "z_index": self.safe_get(row, "Z_index", "1000"),
                "bg_color": self.safe_get(row, "BG_Color", "rgba(255,255,255,0.95)"),
                "text_color": self.safe_get(row, "Text_Color", "#333"),
                "border": self.safe_get(row, "Border", "none"),
                "border_radius": self.safe_get(row, "Border_Radius", "0"),
                "padding": self.safe_get(row, "Padding", "10px"),
                "font_size": self.safe_get(row, "Font_Size", "14px"),
                "text_align": self.safe_get(row, "Text_Align", "left"),
                "box_shadow": self.safe_get(row, "Box_Shadow", "none"),
                "opacity": self.safe_get(row, "Opacity", "1"),
            }

            custom_boxes.append(box_config)

            print(
                f"  ✓ Box '{box_id}': {source_type} at ({box_config['top']}, {box_config['left']})"
            )

        return custom_boxes

    def detect_box_collisions(
        self, boxes: List[Dict[str, Any]], slide_num: int
    ) -> None:
        """Detect overlapping boxes and warn user."""
        if len(boxes) < 2:
            return

        print(f"\n🔍 Checking for box collisions on Slide {slide_num}...")

        def parse_dimension(value, default=0):
            """Extract numeric value from px or % dimension."""
            if pd.isna(value) or value == "auto":
                return default
            value_str = str(value).strip()
            if value_str.endswith("px"):
                return float(value_str[:-2])
            elif value_str.endswith("%"):
                # For %, we can't detect collision accurately without slide context
                return None
            return default

        def boxes_overlap(box1, box2):
            """Check if two boxes overlap using their coordinates."""
            # Parse positions
            b1_top = parse_dimension(box1["top"], 0)
            b1_left = parse_dimension(box1["left"], 0)
            b1_width = parse_dimension(box1["width"], 100)
            b1_height = parse_dimension(box1["height"], 50)

            b2_top = parse_dimension(box2["top"], 0)
            b2_left = parse_dimension(box2["left"], 0)
            b2_width = parse_dimension(box2["width"], 100)
            b2_height = parse_dimension(box2["height"], 50)

            # Skip if any dimension uses % (can't determine collision)
            if None in [
                b1_top,
                b1_left,
                b1_width,
                b1_height,
                b2_top,
                b2_left,
                b2_width,
                b2_height,
            ]:
                return False

            # Calculate bounds
            b1_right = b1_left + b1_width
            b1_bottom = b1_top + b1_height
            b2_right = b2_left + b2_width
            b2_bottom = b2_top + b2_height

            # Check overlap
            horizontal_overlap = not (b1_right <= b2_left or b2_right <= b1_left)
            vertical_overlap = not (b1_bottom <= b2_top or b2_bottom <= b1_top)

            return horizontal_overlap and vertical_overlap

        # Check all pairs
        collisions = []
        for i, box1 in enumerate(boxes):
            for j, box2 in enumerate(boxes[i + 1 :], start=i + 1):
                if boxes_overlap(box1, box2):
                    collisions.append((box1["box_id"], box2["box_id"]))

        if collisions:
            print(f"  ⚠️  WARNING: {len(collisions)} collision(s) detected:")
            for box1_id, box2_id in collisions:
                print(f"     - '{box1_id}' overlaps with '{box2_id}'")
        else:
            print("  ✓ No collisions detected")

    def validate_configuration(self) -> bool:
        validator = ConfigValidator(self.loaded_data)
        return validator.validate_all()

    def load_excel_data(self) -> None:
        """Load all sheets from Excel file.
        Copies to a temp file first so it can be read even when
        open/locked in Excel, OneDrive, or Google Drive.

        Sheet names and column names are normalised to canonical case at
        load time so the rest of the code can use exact string lookups
        without worrying about the user's capitalisation in the Excel file.
        """
        # Canonical sheet names — the code always references these exact strings.
        # Any casing variant in the Excel file (e.g. 'slide_config', 'SLIDE_CONFIG')
        # is mapped to the canonical form before storing in self.loaded_data.
        CANONICAL_SHEETS = {s.lower(): s for s in [
            "Global_Config", "Slide_Config", "Chart_Config",
            "Theme_Config", "Font_Config", "Agenda_Config",
            "Help", "Summary_Config", "Reference_Config",
            "Custom_Box_config", "Version",
            "Deep_Overview_Config", "svg_icons",
        ]}

        # Canonical column names per sheet — same principle.
        CANONICAL_COLUMNS = {col.lower(): col for col in [
            # Global / shared
            "Test_ID", "Slide_Num", "Parameter", "Type", "Default Value",
            "Test_Value", "Description",
            # Slide_Config
            "layout", "title", "subtitle", "footer", "footnote",
            "title_image", "warning_strip", "chart_scale",
            "title_font_size", "title_color", "subtitle_font_size",
            "subtitle_color", "debug_borders",
            # Chart_Config
            "Chart_Pos", "Source_Type", "Source_Path", "container_id",
            "custom_css", "width", "height", "Notes",
            # Custom_Box_config
            "Box_ID", "Top", "Left", "Width", "Height", "Z_index",
            "BG_Color", "Text_Color", "Border", "Border_Radius", "Padding",
            "Font_Size", "Text_Align", "Box_Shadow", "Opacity",
            # Theme_Config / Font_Config
            "primary", "text", "muted", "light", "content_bg", "slide_bg",
            "header_border", "bg_dark", "bg", "bg_light", "text_muted",
            "highlight", "border", "border_muted", "secondary", "danger",
            "warning", "success", "info",
            "font_family", "title", "subtitle", "body", "overlay",
            "footnote", "footer", "agenda_group_heading", "agenda_item",
            "index_group_heading", "index_item",
            # Agenda_Config
            "agenda_statement", "group", "order", "slide_num_override",
            # Help
            "help_text",
            # Summary_Config
            "summary_text",
            # Reference_Config
            "hyperlink", "unc", "group_column_number", "unc_keywords",
            # Version
            "version",
            # Color sheet
            "topic", "chart_type", "chart_element", "element_name",
            "element_name_display", "element_name_order",
            "light_hex", "dark_hex",
            # Deep_Overview_Config
            "Overview_ID", "Button_Icon", "Button_Tooltip",
            "Button_Top", "Button_Left", "Icon_Width", "Icon_Height",
            "Content_Type", "Content", "Order",
            "Title", "Subtitle",
            # svg_icons
            "bubble_icon", "svg",
        ]}

        print(f"📖 Loading Excel file: {self.excel_path.name}")
        tmp_path = None
        try:
            tmp = tempfile.NamedTemporaryFile(
                suffix=self.excel_path.suffix, delete=False
            )
            tmp.close()
            tmp_path = Path(tmp.name)
            shutil.copy2(self.excel_path, tmp_path)

            with pd.ExcelFile(tmp_path, engine="openpyxl") as excel_file:
                self.sheet_names = excel_file.sheet_names
                for raw_sheet_name in self.sheet_names:
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=raw_sheet_name,
                        dtype=str,
                    )

                    # Normalise sheet name → canonical form
                    canonical_sheet = CANONICAL_SHEETS.get(
                        raw_sheet_name.lower(), raw_sheet_name
                    )

                    # Normalise column names → canonical form
                    df.columns = [
                        CANONICAL_COLUMNS.get(str(c).lower().strip(), str(c).strip())
                        for c in df.columns
                    ]

                    self.loaded_data[canonical_sheet] = df
                    print(
                        f"  ✓ Loaded sheet: {raw_sheet_name}"
                        + (f" → {canonical_sheet}" if canonical_sheet != raw_sheet_name else "")
                        + f" ({len(df)} rows)"
                    )

            print("\n" + "=" * 60)
            if not self.validate_configuration():
                raise ValueError(
                    "Configuration validation failed. Please fix errors above."
                )
            print("=" * 60)
        except Exception as e:
            print(f"❌ Error loading Excel file: {e}")
            raise
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def safe_get(self, row, column, default=None):
        """Safely get value from a pandas Series/dict. Case-insensitive column lookup."""
        try:
            # Exact match first
            if column in row:
                value = row[column]
                if pd.isna(value):
                    return default
                return value
            # Case-insensitive fallback
            col_lower = column.lower()
            for key in row.index if hasattr(row, 'index') else row.keys():
                if str(key).lower() == col_lower:
                    value = row[key]
                    if pd.isna(value):
                        return default
                    return value
            return default
        except Exception:
            return default

    def get_test_ids(self) -> List[str]:
        """Get all unique test IDs from Slide_Config."""
        test_ids = set()
        if "Slide_Config" in self.loaded_data:
            slide_df = self.loaded_data["Slide_Config"]
            if "Test_ID" in slide_df.columns:
                ids = slide_df["Test_ID"].dropna().astype(str).unique()
                test_ids.update(ids)
        return sorted(list(test_ids))

    def parse_json_field(self, value: Any) -> Any:
        """Parse a JSON or Python literal field."""
        if pd.isna(value) or value == "" or value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        value = value.strip()
        if value.upper() == "TRUE":
            return True
        if value.upper() == "FALSE":
            return False

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            pass

        if value.replace(".", "", 1).isdigit():
            try:
                return float(value) if "." in value else int(value)
            except ValueError:
                pass

        return value

    def get_global_config(self, test_id: str) -> Dict[str, Any]:
        """Get global configuration including buttons parameter."""
        config = {}
        if "Global_Config" not in self.loaded_data:
            return config

        df = self.loaded_data["Global_Config"]
        required_cols = ["Parameter"]
        if not all(col in df.columns for col in required_cols):
            print("⚠️ Warning: Global_Config missing required columns")
            return config

        has_test_id = "Test_ID" in df.columns
        print(f"\n🔍 Loading Global_Config for test_id='{test_id}'")

        # Process each parameter
        for idx, row in df.iterrows():
            param_name = self.safe_get(row, "Parameter")
            if not param_name:
                continue
            # Strip whitespace — trailing spaces in Excel cells are a common gotcha
            param_name = str(param_name).strip()

            # Get test-specific value if exists
            if has_test_id:
                row_test_id = self.safe_get(row, "Test_ID")
                is_empty = (
                    row_test_id is None
                    or row_test_id == ""
                    or (isinstance(row_test_id, float) and np.isnan(row_test_id))
                    or str(row_test_id).strip() == ""
                    or str(row_test_id).strip().lower() == "nan"
                )

                if not is_empty:
                    row_test_id_str = str(row_test_id).strip()
                    test_id_str = str(test_id).strip()
                    if row_test_id_str != test_id_str:
                        continue

            test_value = None
            for col_name in ["Test_Value", "test_value", "TestValue"]:
                if col_name in df.columns:
                    test_value = self.safe_get(row, col_name)
                    if test_value is not None and test_value != "":
                        break

            # Get default value from appropriate column
            default_value = None
            for col_name in [
                "Default Value",
                "default_value",
                "DefaultValue",
                "Default",
            ]:
                if col_name in df.columns:
                    default_value = self.safe_get(row, col_name)
                    break

            # Get value
            if test_value is not None and test_value != "":
                value = test_value
            else:
                value = default_value

            # Parse the value
            parsed_value = self.parse_json_field(value)

            # ADDED: Special handling for 'buttons' parameter
            if param_name == "buttons":
                if parsed_value is None or parsed_value == "" or parsed_value == []:
                    parsed_value = None  # This will trigger minimal buttons
                elif isinstance(parsed_value, list):
                    # Filter out empty strings from list
                    parsed_value = [b for b in parsed_value if b and b.strip()]
                    if not parsed_value:
                        parsed_value = None
                print(f"        🔵 Buttons parameter: {parsed_value}")

            # ADD THIS: Special handling for 'agenda_columns' parameter
            if param_name == "agenda_columns":
                # Handle integer values (1, 2, 3) or 'auto'
                if isinstance(parsed_value, str):
                    if parsed_value.lower() == "auto":
                        parsed_value = "auto"
                    else:
                        try:
                            parsed_value = int(parsed_value)
                        except ValueError:
                            parsed_value = "auto"
                elif isinstance(parsed_value, (int, float)):
                    parsed_value = int(parsed_value)
                else:
                    parsed_value = "auto"
                print(f"      📊 Agenda columns parameter: {parsed_value}")

            config[param_name] = parsed_value

            # Console debug parameter
            if param_name == "console_debug":
                if isinstance(parsed_value, str):
                    parsed_value = parsed_value.strip().upper() == "TRUE"
                elif not isinstance(parsed_value, bool):
                    parsed_value = False
                print(f"      💻  Console debug: {parsed_value}")

            if param_name == "console_level":
                valid_levels = ["minimal", "info", "verbose"]
                if isinstance(parsed_value, str):
                    parsed_value = parsed_value.strip().lower()
                if parsed_value not in valid_levels:
                    parsed_value = "info"
                print(f"      📊 Console level: {parsed_value}")

            config[param_name] = parsed_value

            # ADD THIS: Special handling for 'index_columns' parameter
            if param_name == "index_columns":
                # Handle integer values (1, 2, 3) or 'auto'
                if isinstance(parsed_value, str):
                    if parsed_value.lower() == "auto":
                        parsed_value = "auto"
                    else:
                        try:
                            parsed_value = int(parsed_value)
                        except ValueError:
                            parsed_value = "auto"
                elif isinstance(parsed_value, (int, float)):
                    parsed_value = int(parsed_value)
                else:
                    parsed_value = "auto"
                print(f"      📊 Index columns parameter: {parsed_value}")

        return config

    def load_agenda_config(self, test_id: str) -> List[Dict[str, Any]]:
        """Load agenda configuration with grouping support."""
        agenda_items = []

        if "Agenda_Config" not in self.loaded_data:
            print("  ℹ️  No Agenda_Config sheet found, skipping index generation")
            return agenda_items

        df = self.loaded_data["Agenda_Config"]
        print(f"\n📋 Loading Agenda for test_id='{test_id}'")

        # Filter for this test
        df["Test_ID_str"] = df["Test_ID"].astype(str).str.strip()
        test_id_str = str(test_id).strip()
        test_agenda = df[df["Test_ID_str"] == test_id_str]

        print(f"  Found {len(test_agenda)} agenda item(s)")

        for idx, row in test_agenda.iterrows():
            slide_num = self.safe_get(row, "Slide_Num")
            group = self.safe_get(row, "group", "")
            agenda_starter = self.safe_get(row, "agenda_starter", "")
            agenda_statement = self.safe_get(row, "agenda_statement", "")

            # Skip if statement is empty
            if pd.isna(agenda_statement) or str(agenda_statement).strip() == "":
                print(f"  ⚠️  Skipping row {idx}: agenda_statement is empty")
                continue

            # Handle group
            if pd.isna(group) or group == "":
                group = None
            else:
                group = str(group).strip()

            # Handle starter
            if pd.isna(agenda_starter) or agenda_starter == "":
                agenda_starter = ""
            else:
                agenda_starter = str(agenda_starter).strip()

            # Handle statement
            agenda_statement = str(agenda_statement).strip()

            # Format text
            if agenda_starter != "":
                formatted_text = f"<strong>{agenda_starter}</strong> {agenda_statement}"
            else:
                formatted_text = agenda_statement

            try:
                slide_num_int = int(slide_num)
            except (ValueError, TypeError):
                print(f"  ⚠️  Invalid Slide_Num: {slide_num}")
                continue

            agenda_items.append(
                {"slide_num": slide_num_int, "group": group, "text": formatted_text}
            )

            group_display = f"[{group}]" if group else "[ungrouped]"
            print(
                f"  ✓ Agenda item: Slide {slide_num_int} {group_display} → {formatted_text[:50]}..."
            )

        return agenda_items

    def build_agenda_slide(
        self, agenda_items: List[Dict], global_config: Dict
    ) -> Dict[str, Any]:
        """Build an agenda slide from configuration."""
        if not agenda_items:
            return None

        print("\n📋 Building agenda slide...")

        # Sort by slide number to maintain sequence
        agenda_items_sorted = sorted(agenda_items, key=lambda x: x["slide_num"])

        # Get agenda configuration from global config
        agenda_title = global_config.get("agenda_title", "")
        agenda_columns_config = global_config.get("agenda_columns", "auto")
        agenda_layout = str(global_config.get("agenda_layout", "default")).strip().lower()

        item_count = len(agenda_items_sorted)

        # Determine columns with 4-column support
        if agenda_columns_config == "auto":
            if item_count <= 8:
                columns = 1
                max_width = "700px"
            elif item_count <= 16:
                columns = 2
                max_width = "1000px"
            elif item_count <= 28:
                columns = 3
                max_width = "1200px"
            else:
                columns = 4
                max_width = "1200px"
        else:
            try:
                columns = int(agenda_columns_config)
                columns = max(1, min(4, columns))
            except (ValueError, TypeError):
                columns = 1

            if columns == 1:
                max_width = "700px"
            elif columns == 2:
                max_width = "1000px"
            elif columns == 3:
                max_width = "1200px"
            else:  # columns == 4
                max_width = "1200px"

        print(f"  ✓ Using {columns} column(s) for {item_count} items")

        # Collect all items by group first, then organize by sequence
        groups_dict = {}  # {group_name: [items]}
        ungrouped_items = []

        for item in agenda_items_sorted:
            if item["group"] is None:
                ungrouped_items.append(item)
            else:
                group_name = item["group"]
                if group_name not in groups_dict:
                    groups_dict[group_name] = []
                groups_dict[group_name].append(item)

        # Build output maintaining slide sequence
        output_html_parts = []
        processed_groups = set()

        for item in agenda_items_sorted:
            if item["group"] is None:
                # Ungrouped item - add directly
                slide_target = item["slide_num"] - 1
                item_html = f'''
                <div class="agenda-item-clean" data-slide-target="{slide_target}">
                    <div class="agenda-item-number">{item["slide_num"]}</div>
                    <div class="agenda-item-text">{item["text"]}</div>
                </div>
                '''
                output_html_parts.append(item_html)
            else:
                # Grouped item - add group heading + all items only once
                group_name = item["group"]
                if group_name not in processed_groups:
                    processed_groups.add(group_name)

                    # Add group heading
                    group_html = (
                        f'<div class="agenda-group-heading">{group_name.upper()}</div>'
                    )
                    output_html_parts.append(group_html)

                    # Add ALL items in this group
                    for group_item in groups_dict[group_name]:
                        slide_target = group_item["slide_num"] - 1
                        item_html = f'''
                        <div class="agenda-item-clean" data-slide-target="{slide_target}">
                            <div class="agenda-item-number">{group_item["slide_num"]}</div>
                            <div class="agenda-item-text">{group_item["text"]}</div>
                        </div>
                        '''
                        output_html_parts.append(item_html)

        # ── Build complete HTML based on layout ──────────────────────────────
        title_html = ""
        if agenda_title and agenda_title.strip():
            title_html = f"""
            <h2 style="color: var(--color-primary);
                    font-size: 28px;
                    font-weight: bold;
                    margin: 0 0 20px 0;
                    text-align: center;">
                {agenda_title}
            </h2>
            """

        if agenda_layout == "flat":
            full_html = self._build_agenda_flat(
                output_html_parts, title_html, columns, max_width
            )
        else:
            full_html = self._build_agenda_default(
                output_html_parts, title_html, columns, max_width
            )

        # Build slide configuration
        agenda_slide = {
            "layout": "single",
            "title": "",
            "subtitle": "",
            "footer": global_config.get("default_footer", ""),
            "footnote": "",
            "charts": [f"TEXT:{full_html}"],
        }

        total_groups = len(processed_groups)
        total_ungrouped = len(ungrouped_items)
        print(
            f"  ✓ Agenda created: {total_groups} group(s), {total_ungrouped} ungrouped item(s), layout={agenda_layout}"
        )
        return agenda_slide

    def _build_agenda_default(
        self,
        output_html_parts: list,
        title_html: str,
        columns: int,
        max_width: str,
        container_style: str = None,
    ) -> str:
        """Original agenda layout — numbered circles, multi-column grid."""
        if container_style is None:
            if columns == 1:
                container_style = "display: flex; flex-direction: column; gap: 6px;"
            else:
                container_style = f"""
                    display: grid;
                    grid-template-columns: repeat({columns}, 1fr);
                    gap: 8px 20px;
                    align-items: start;
                """

        container_html = f'''
        <div style="max-width: {max_width}; margin: 0 auto;">
            <div class="agenda-items-container-clean" style="{container_style}">
                {"".join(output_html_parts)}
            </div>
        </div>
        '''

        return f"""
        <div style="font-family: var(--font-family, Calibri, Arial, sans-serif); padding: 20px;">
            {title_html}
            {container_html}
        </div>

        <style>
            .agenda-group-heading {{
                font-weight: bold;
                font-size: var(--font-agenda-group-heading, 16px);
                color: var(--color-primary);
                margin: 16px 0 8px 0;
                letter-spacing: 0.5px;
                grid-column: 1 / -1;
            }}
            body.dark-mode .agenda-group-heading {{
                color: var(--color-primary);
            }}
            .agenda-item-clean {{
                display: flex;
                align-items: center;
                cursor: pointer;
                padding: 6px 0;
                transition: all 0.2s ease;
                min-width: 0;
            }}
            .agenda-item-clean:hover {{
                transform: translateX(4px);
            }}
            .agenda-item-clean:hover .agenda-item-text {{
                color: var(--color-primary);
            }}
            body.dark-mode .agenda-item-clean:hover .agenda-item-text {{
                color: var(--color-primary);
            }}
            .agenda-item-number {{
                background: var(--color-primary);
                color: white;
                min-width: 2.3em;
                height: 2.3em;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: var(--font-agenda-item, 14px);
                margin-right: 12px;
                flex-shrink: 0;
                transition: all 0.2s ease;
            }}
            .agenda-item-clean:hover .agenda-item-number {{
                transform: scale(1.1);
                box-shadow: 0 2px 8px rgba(0, 25, 101, 0.3);
            }}
            body.dark-mode .agenda-item-number {{
                background: var(--color-primary);
            }}
            body.dark-mode .agenda-item-clean:hover .agenda-item-number {{
                box-shadow: 0 2px 8px rgba(74, 158, 255, 0.4);
            }}
            .agenda-item-text {{
                font-size: var(--font-agenda-item, 14px);
                line-height: 1.4;
                color: var(--color-primary);
                transition: all 0.2s ease;
                overflow: hidden;
                text-overflow: ellipsis;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                word-break: break-word;
            }}
            body.dark-mode .agenda-item-text {{
                color: var(--color-primary);
            }}
            .agenda-item-clean:hover .agenda-item-text {{
                overflow: visible;
                -webkit-line-clamp: unset;
            }}
        </style>
        """

    def _build_agenda_flat(
        self,
        output_html_parts: list,
        title_html: str,
        columns: int,
        max_width: str,
    ) -> str:
        """
        Flat agenda layout — horizontal rows with a left accent bar, no circles.
        Numbers are small and inline. Full text wraps naturally without clipping.
        Accommodates more items and longer text than the default circle layout.
        Multi-column support via CSS grid (same column logic as default).
        """
        if columns == 1:
            grid_style = "display: flex; flex-direction: column;"
        else:
            grid_style = f"""
                display: grid;
                grid-template-columns: repeat({columns}, 1fr);
                gap: 0 28px;
                align-items: start;
            """

        container_html = f'''
        <div style="max-width: {max_width}; margin: 0 auto;">
            <div class="agenda-flat-container" style="{grid_style}">
                {"".join(output_html_parts)}
            </div>
        </div>
        '''

        return f"""
        <div style="font-family: var(--font-family, Calibri, Arial, sans-serif); padding: 20px 28px;">
            {title_html}
            {container_html}
        </div>

        <style>
            /* ── Flat layout: group headings ─────────────────────── */
            .agenda-flat-container .agenda-group-heading {{
                font-size: var(--font-agenda-group-heading, 11px);
                font-weight: 700;
                letter-spacing: 1.2px;
                text-transform: uppercase;
                color: var(--color-primary);
                opacity: 0.5;
                padding: 14px 0 4px 12px;
                grid-column: 1 / -1;
                border: none;
                margin: 0;
            }}
            body.dark-mode .agenda-flat-container .agenda-group-heading {{
                color: var(--color-primary);
                opacity: 0.6;
            }}

            /* ── Flat layout: each row ───────────────────────────── */
            .agenda-flat-container .agenda-item-clean {{
                display: flex;
                align-items: baseline;
                gap: 10px;
                padding: 7px 10px 7px 12px;
                border-left: 3px solid transparent;
                cursor: pointer;
                transition: border-color 0.15s ease, background 0.15s ease;
                min-width: 0;
                border-bottom: 1px solid rgba(0, 0, 0, 0.07);
            }}
            body.dark-mode .agenda-flat-container .agenda-item-clean {{
                border-bottom-color: rgba(255, 255, 255, 0.08);
            }}

            .agenda-flat-container .agenda-item-clean:hover {{
                border-left-color: var(--color-primary);
                background: rgba(0, 22, 94, 0.04);
                transform: none;
            }}
            body.dark-mode .agenda-flat-container .agenda-item-clean:hover {{
                background: rgba(255, 255, 255, 0.05);
            }}

            /* ── Number: small, muted, inline ───────────────────── */
            .agenda-flat-container .agenda-item-number {{
                font-size: 10px;
                font-weight: 600;
                color: var(--color-primary);
                opacity: 0.45;
                min-width: 18px;
                text-align: right;
                flex-shrink: 0;
                line-height: 1.5;
                /* override default circle styles */
                background: none;
                border-radius: 0;
                height: auto;
                margin-right: 0;
                box-shadow: none;
            }}
            body.dark-mode .agenda-flat-container .agenda-item-number {{
                color: var(--color-primary);
                opacity: 0.5;
            }}
            .agenda-flat-container .agenda-item-clean:hover .agenda-item-number {{
                opacity: 0.85;
                transform: none;
                box-shadow: none;
            }}

            /* ── Text: full wrap, no clamp ───────────────────────── */
            .agenda-flat-container .agenda-item-text {{
                font-size: var(--font-agenda-item, 13px);
                line-height: 1.45;
                color: var(--color-primary);
                transition: color 0.15s ease;
                /* explicitly undo default clamp */
                overflow: visible;
                text-overflow: unset;
                display: block;
                -webkit-line-clamp: unset;
                -webkit-box-orient: unset;
                word-break: normal;
                white-space: normal;
            }}
            body.dark-mode .agenda-flat-container .agenda-item-text {{
                color: var(--color-primary);
            }}
            .agenda-flat-container .agenda-item-clean:hover .agenda-item-text {{
                color: var(--color-primary);
                overflow: visible;
                -webkit-line-clamp: unset;
            }}
        </style>
        """

    def load_help_text(self) -> str:
        """Load help text from Help sheet."""
        if "Help" not in self.loaded_data:
            return """<strong>Keyboard Shortcuts:</strong><br>
• <strong>H</strong> = Jump to Home (first slide)<br>
• <strong>I</strong> = Jump to Index<br>
• <strong>Arrow Keys / Space</strong> = Navigate slides<br>
• <strong>Esc</strong> = Exit presentation mode"""

        df = self.loaded_data["Help"]

        if "help_text" not in df.columns or len(df) < 1:
            return """<strong>Keyboard Shortcuts:</strong><br>
• <strong>H</strong> = Jump to Home<br>
• <strong>I</strong> = Jump to Index"""

        help_text = df["help_text"].iloc[0]

        if pd.isna(help_text) or str(help_text).strip() == "":
            return """<strong>Keyboard Shortcuts:</strong><br>
• <strong>H</strong> = Jump to Home<br>
• <strong>I</strong> = Jump to Index"""

        return str(help_text).strip()

    def build_slides_config(self, test_id: str) -> List[Dict[str, Any]]:
        """Build complete slides configuration for a test."""
        print(f"\n🔨 build_slides_config for test_id='{test_id}'")
        slides = []

        if "Slide_Config" not in self.loaded_data:
            print("❌ 'Slide_Config' not found!")
            return slides

        df = self.loaded_data["Slide_Config"]
        print(f"✅ Slide_Config loaded: {len(df)} rows")

        if "Test_ID" not in df.columns:
            print("❌ No 'Test_ID' column")
            return slides

        # Get global config for flags
        global_config = self.get_global_config(test_id)
        enable_starter = global_config.get("enable_starter_slide", False)
        enable_agenda = global_config.get("enable_agenda_slide", False)
        # Default True — existing setups without this param still get the reference slide
        enable_reference = global_config.get("enable_reference_slide", True)
        if isinstance(enable_reference, str):
            enable_reference = enable_reference.strip().upper() != "FALSE"

        print(f"  🎬 Starter slide enabled: {enable_starter}")
        print(f"  📋 Agenda slide enabled: {enable_agenda}")
        print(f"  🔗 Reference slide enabled: {enable_reference}")

        df["Test_ID_str"] = df["Test_ID"].astype(str).str.strip()
        test_id_str = str(test_id).strip()
        test_slides = df[df["Test_ID_str"] == test_id_str]

        print(f"  Found {len(test_slides)} slide(s) in Slide_Config")

        # === STEP 1: Starter Slide ===
        starter_slide = None
        if enable_starter:
            starter_rows = test_slides[
                test_slides["Slide_Num"].astype(str).str.strip() == "1"
            ]
            if len(starter_rows) > 0:
                starter_row = starter_rows.iloc[0]
                starter_slide = self._build_slide_from_row(starter_row, 1)
                if starter_slide:
                    print(
                        f"  🔍 DEBUG: Starter slide - charts={len(starter_slide.get('charts', []))}, boxes={len(starter_slide.get('custom_boxes', []))}"
                    )
                    slides.append(starter_slide)
                    print("  ✓ Starter slide added as Output Slide 1")
            else:
                print("  ⚠️ enable_starter_slide=True but no Slide_Num=1 found")

        # === STEP 2: Agenda Slide ===
        agenda_slide = None
        if enable_agenda:
            agenda_items = self.load_agenda_config(test_id)
            if agenda_items:
                agenda_slide = self.build_agenda_slide(agenda_items, global_config)
                if agenda_slide:
                    print(
                        f"  🔍 DEBUG: Agenda slide - charts={len(agenda_slide.get('charts', []))}, boxes={len(agenda_slide.get('custom_boxes', []))}"
                    )
                    slides.append(agenda_slide)
                    output_pos = 2 if starter_slide else 1
                    print(f"  ✓ Agenda slide added as Output Slide {output_pos}")
            else:
                print("  ⚠️ enable_agenda_slide=True but no agenda items found")

        # === STEP 3: User Slides ===
        for idx, (_, slide_row) in enumerate(test_slides.iterrows()):
            slide_num = self.safe_get(slide_row, "Slide_Num", 0)
            try:
                slide_num = int(slide_num)
            except (ValueError, TypeError):
                slide_num = 0

            if enable_starter and slide_num == 1:
                continue

            slide = self._build_slide_from_row(slide_row, slide_num)
            if slide:
                print(
                    f"  🔍 DEBUG: User slide {slide_num} - charts={len(slide.get('charts', []))}, boxes={len(slide.get('custom_boxes', []))}"
                )
                slides.append(slide)

        # === FILTER BEFORE REFERENCE ===
        slides = [s for s in slides if s and (s.get("charts") or s.get("custom_boxes"))]
        print(f"  🔍 DEBUG: After filtering, {len(slides)} slides remain")

        # === STEP 4: Reference Slide ===
        if not enable_reference:
            print("  ℹ️  Reference slide disabled (enable_reference_slide=False)")
        else:
            reference_items = self.load_reference_config(test_id)
            if reference_items:
                reference_slide = self.build_reference_slide(reference_items, global_config)
                if reference_slide:
                    print(
                        f"  🔍 DEBUG: Reference slide - charts={len(reference_slide.get('charts', []))}, boxes={len(reference_slide.get('custom_boxes', []))}"
                    )
                    slides.append(reference_slide)
                    print(f"  ✓ Reference slide added as final slide (Slide {len(slides)})")
            else:
                print("  ℹ️  No reference items found")

        print(f"  ✅ Total slides in output: {len(slides)}")

        # === FINAL DEBUG ===
        for i, s in enumerate(slides, 1):
            charts_count = len(s.get("charts", []))
            boxes_count = len(s.get("custom_boxes", []))
            print(f"     Output Slide {i}: charts={charts_count}, boxes={boxes_count}")
        
        print(f"  ✅ Total slides in output: {len(slides)}")

        print("\n🎯 FINAL SLIDES ABOUT TO RETURN:")
        for i, s in enumerate(slides, 1):
            print(f"   [{i}] title={repr(s.get('title'))}, subtitle={repr(s.get('subtitle'))}, charts={len(s.get('charts', []))}")

        return slides

    def build_reference_slide(
        self, reference_items: List[Dict], global_config: Dict
    ) -> Dict[str, Any]:
        """Build reference links slide with multi-column layout and keyword search."""
        if not reference_items:
            return None

        print("\n📚 Building reference slide...")

        # Check whether any item has keywords (drives search box visibility)
        has_keywords = any(item.get("unc_keywords", "") for item in reference_items)

        # Sort by group_column_number, then group, then order
        reference_items_sorted = sorted(
            reference_items,
            key=lambda x: (x["group_column_number"], x["group"], x["order"]),
        )

        # Separate into sections
        top_section_items = [
            item for item in reference_items_sorted if item["group_column_number"] == 0
        ]
        bottom_section_items = [
            item for item in reference_items_sorted if item["group_column_number"] == 999
        ]
        column_items = [
            item for item in reference_items_sorted if 1 <= item["group_column_number"] <= 6
        ]

        # Group column items by column number and group
        columns_dict = {}
        for item in column_items:
            col_num = item["group_column_number"]
            group_name = item["group"]
            if col_num not in columns_dict:
                columns_dict[col_num] = {}
            if group_name not in columns_dict[col_num]:
                columns_dict[col_num][group_name] = []
            columns_dict[col_num][group_name].append(item)

        num_columns = max(1, min(6, len(columns_dict) if columns_dict else 1))

        print(f"  ✓ Layout: {num_columns} column(s), search box: {has_keywords}")
        print(f"  ✓ Top section: {len(top_section_items)} item(s)")
        print(f"  ✓ Column section: {len(column_items)} item(s)")
        print(f"  ✓ Bottom section: {len(bottom_section_items)} item(s)")

        html_parts = []

        # ── Search box (only when at least one item has keywords) ──
        if has_keywords:
            search_html = """
            <div style="margin-bottom: 16px;">
                <input id="refSearch"
                       type="text"
                       placeholder="Search keywords…"
                       autocomplete="off"
                       style="width: 100%;
                              box-sizing: border-box;
                              padding: 7px 14px;
                              font-size: 13px;
                              font-family: var(--font-family, Calibri, Arial, sans-serif);
                              border: 1px solid var(--color-border, #ccc);
                              border-radius: 6px;
                              background: var(--content-bg, #fff);
                              color: var(--color-text, #333);
                              outline: none;
                              transition: border-color 0.15s;">
            </div>
            """
            html_parts.append(search_html)

        # ── Top section (disclaimer) ──
        if top_section_items:
            top_section_html = f"""
            <div style="font-size: 12px;
                        color: var(--color-muted);
                        line-height: 0.3;
                        margin-bottom: 10px;
                        # border-bottom: 1px solid var(--color-muted);
                        padding-bottom: 10px;">
                {"<br>".join(item["text"] for item in top_section_items)}
            </div>
            """
            html_parts.append(top_section_html)

        # ── Column section ──
        if columns_dict:
            column_htmls = []
            for col_num in sorted(columns_dict.keys()):
                groups = columns_dict[col_num]
                group_htmls = []
                for group_name, items in groups.items():
                    list_items_html = []
                    for item in items:
                        # Build search target: text + keywords (lowercased, space-joined)
                        kw = item.get("unc_keywords", "")
                        search_str = f"{item['text']} {kw}".strip().lower()
                        kw_attr = f' data-keywords="{search_str}"' if has_keywords else ""

                        if item["hyperlink"] == 1 and item["unc"]:
                            list_items_html.append(
                                f'<li{kw_attr}><a href="{item["unc"]}" target="_blank">{item["text"]}</a></li>'
                            )
                        else:
                            list_items_html.append(
                                f'<li{kw_attr} style="color: var(--color-light);">{item["text"]}</li>'
                            )

                    group_html = f"""
                    <div class="ref-group" style="margin-bottom: 20px;">
                        <div class="ref-group-heading"
                             style="font-weight: bold;
                                    margin-bottom: 10px;
                                    color: var(--color-muted);
                                    font-size: 13px;">
                            {group_name}
                        </div>
                        <ul style="list-style: none;
                                   padding: 0;
                                   margin: 0;
                                   line-height: 1.8;
                                   font-size: 12px;">
                            {"".join(list_items_html)}
                        </ul>
                    </div>
                    """
                    group_htmls.append(group_html)

                column_htmls.append(f'<div>{"".join(group_htmls)}</div>')

            columns_section_html = f"""
            <div id="refColumns"
                 style="display: grid;
                        grid-template-columns: repeat({num_columns}, 1fr);
                        gap: 20px;
                        padding: 30px 0;">
                {"".join(column_htmls)}
            </div>
            <p id="refNoResults"
               style="display:none;
                      font-size:13px;
                      color:var(--color-muted);
                      padding: 12px 0;
                      font-style: italic;">
                No links match your search.
            </p>
            """
            html_parts.append(columns_section_html)

        # ── Bottom section (copyright / footer) ──
        if bottom_section_items:
            bottom_html_items = []
            for item in bottom_section_items:
                if item["hyperlink"] == 1 and item["unc"]:
                    bottom_html_items.append(f'<a href="{item["unc"]}" target="_blank">{item["text"]}</a>')
                else:
                    bottom_html_items.append(item["text"])

            html_parts.append(f"""
            <div style="margin-top: 10px;
                        font-size: 11px;
                        color: var(--color-muted);
                        text-align: center;">
                {" &nbsp;|&nbsp; ".join(bottom_html_items)}
            </div>
            """)

        # ── Search script (injected once, only when keywords exist) ──
        search_script = ""
        if has_keywords:
            search_script = """
            <script>
            (function() {
                var input = document.getElementById('refSearch');
                if (!input) return;

                function filterRefs() {
                    var q = input.value.trim().toLowerCase();
                    var items = document.querySelectorAll('#refColumns li[data-keywords]');
                    var visibleCount = 0;

                    items.forEach(function(li) {
                        var kw = li.getAttribute('data-keywords') || '';
                        var show = !q || kw.indexOf(q) !== -1;
                        li.style.display = show ? '' : 'none';
                        if (show) visibleCount++;
                    });

                    // Show/hide empty group headings
                    document.querySelectorAll('#refColumns .ref-group').forEach(function(grp) {
                        var visible = grp.querySelectorAll('li[data-keywords]:not([style*="display: none"])').length;
                        grp.style.display = visible ? '' : 'none';
                    });

                    var noResults = document.getElementById('refNoResults');
                    if (noResults) noResults.style.display = visibleCount === 0 ? '' : 'none';
                }

                input.addEventListener('input', filterRefs);

                // Highlight search box on focus
                input.addEventListener('focus', function() {
                    this.style.borderColor = 'var(--color-primary)';
                    this.style.boxShadow = '0 0 0 2px color-mix(in srgb, var(--color-primary) 20%, transparent)';
                });
                input.addEventListener('blur', function() {
                    this.style.borderColor = 'var(--color-border, #ccc)';
                    this.style.boxShadow = 'none';
                });
            })();
            </script>
            """

        full_html = f"""
        <div style="font-family: var(--font-family, Calibri, Arial, sans-serif);
                    padding: 40px 80px;
                    max-width: 1120px;
                    margin: 0 auto;">
            {"".join(html_parts)}
        </div>
        {search_script}

        <style>
            div a, div a:link, div a:visited,
            li a, li a:link, li a:visited {{
                color: var(--color-primary) !important;
                text-decoration: none !important;
            }}
            div a:hover, li a:hover {{
                color: var(--color-primary) !important;
                text-decoration: underline !important;
            }}
            body.dark-mode div a, body.dark-mode div a:link, body.dark-mode div a:visited,
            body.dark-mode li a, body.dark-mode li a:link, body.dark-mode li a:visited {{
                color: var(--color-primary) !important;
            }}
            body.dark-mode div a:hover, body.dark-mode li a:hover {{
                color: var(--color-primary) !important;
                text-decoration: underline !important;
            }}
            #refSearch::placeholder {{
                color: var(--color-muted, #999);
                opacity: 1;
            }}
        </style>
        """

        reference_slide = {
            "layout": "single",
            "title": "",
            "subtitle": "",
            "footer": global_config.get("default_footer", ""),
            "footnote": "",
            "charts": [f"TEXT:{full_html}"],
        }

        print(
            f"  ✓ Reference slide created: {len(top_section_items)} disclaimer(s), "
            f"{len(column_items)} link(s), {len(bottom_section_items)} footer item(s), "
            f"search: {has_keywords}"
        )
        return reference_slide

    def _build_slide_from_row(
        self, slide_row, slide_num: int
    ) -> Optional[Dict[str, Any]]:
        """Helper method to build a slide dict from a Slide_Config row."""
        layout = self.safe_get(slide_row, "layout", "single")
        title = self.safe_get(slide_row, "title", "")

        print(f"\n🔍 DEBUG _build_slide_from_row (Slide {slide_num}):")
        print(f"   Raw title value: {repr(slide_row.get('title'))}")
        print(f"   After safe_get: {repr(title)}")
        print(f"   Raw subtitle value: {repr(slide_row.get('subtitle'))}")

        slide = {
            "layout": layout,
            "title": title,
            "subtitle": self.safe_get(slide_row, "subtitle"),
            "footer": self.safe_get(slide_row, "footer"),
            "footnote": self.safe_get(slide_row, "footnote"),
            "title_image": self.safe_get(slide_row, "title_image"),
            "chart_scale": self.parse_json_field(
                self.safe_get(slide_row, "chart_scale")
            ),
            "title_font_size": self.safe_get(slide_row, "title_font_size"),
            "title_color": self.safe_get(slide_row, "title_color"),
            "subtitle_font_size": self.safe_get(slide_row, "subtitle_font_size"),
            "subtitle_color": self.safe_get(slide_row, "subtitle_color"),
        }

        debug_borders = self.safe_get(slide_row, "debug_borders")
        if debug_borders is not None:
            slide["debug_borders"] = self.parse_json_field(debug_borders)

        overlay_text = self.safe_get(slide_row, "overlay_text")
        if overlay_text not in [None, "", np.nan]:
            slide["overlay"] = {
                "text": overlay_text,
                "position": self.safe_get(slide_row, "overlay_position", "top-right"),
                "bg_color": self.safe_get(slide_row, "overlay_bg_color"),
                "text_color": self.safe_get(slide_row, "overlay_text_color"),
                "font_size": self.safe_get(slide_row, "overlay_font_size"),
            }

        # Extract warning strip configuration
        warning_strip_text = self.safe_get(slide_row, "warning_strip_text")
        print(f"  🔍 DEBUG: warning_strip_text = '{warning_strip_text}'")

        if warning_strip_text not in [None, "", np.nan]:
            slide["warning_strip"] = {
                "text": warning_strip_text,
                "position": self.safe_get(slide_row, "warning_strip_position", "top"),
                "bg_color": self.safe_get(slide_row, "warning_strip_bg_color"),
                "text_color": self.safe_get(slide_row, "warning_strip_text_color"),
                "height": self.safe_get(slide_row, "warning_strip_height"),
            }
            print(f"  ✅ WARNING STRIP CONFIGURED: {slide['warning_strip']}")
        else:
            print("  ⚠️ Warning strip text is empty/None")

        # Get charts for this slide
        title_image_path = self.safe_get(slide_row, "title_image")
        if title_image_path not in [None, "", np.nan]:
            try:
                normalized = PathNormalizer.normalize_and_validate(
                    title_image_path,
                    base_path=self.excel_path.parent,
                    must_exist=True,
                )
                slide["title_image"] = str(normalized)
            except FileNotFoundError as e:
                print(f"⚠️  Warning: Title image not found: {e}")

        # ✅ NEW: Load custom boxes for this slide
        test_id = self.safe_get(slide_row, "Test_ID")
        custom_boxes = self.load_custom_box_config(test_id, slide_num)

        if custom_boxes:
            # Run collision detection
            self.detect_box_collisions(custom_boxes, slide_num)
            slide["custom_boxes"] = custom_boxes

        # ✅ NEW: Load Deep Dive panels for this slide
        deep_dives = self.load_deep_overview_config(test_id, slide_num)
        if deep_dives:
            slide["deep_dives"] = deep_dives

        # Get charts for this slide
        charts = self.get_charts_for_slide(
            self.safe_get(slide_row, "Test_ID"), slide_num
        )
        if charts:
            slide["charts"] = charts

        # Clean up None values
        clean_slide = {}
        for k, v in slide.items():
            # Always keep title and subtitle
            if k in ["title", "subtitle"]:
                clean_slide[k] = v if v is not None else ""
            elif (
                v is not None and v != "" and not (isinstance(v, float) and np.isnan(v))
            ):
                clean_slide[k] = v

        print(f"\n🔍 SLIDE {slide_num} BEFORE RETURN:")
        print(f"   Original slide keys: {list(slide.keys())}")
        print(f"   Original title: {repr(slide.get('title'))}")
        print(f"   Original subtitle: {repr(slide.get('subtitle'))}")
        print(f"   Clean slide keys: {list(clean_slide.keys())}")
        print(f"   Clean title: {repr(clean_slide.get('title'))}")
        print(f"   Clean subtitle: {repr(clean_slide.get('subtitle'))}")
        print(f"   Returning None? {clean_slide if clean_slide else None is None}")

        return clean_slide if clean_slide else None


    def get_charts_for_slide(self, test_id: str, slide_num: int) -> List[Union[str, Dict]]:
        """Get chart configurations for a specific slide."""
        charts = []

        if "Chart_Config" not in self.loaded_data:
            return charts

        df = self.loaded_data["Chart_Config"]

        # Filter for this test and slide
        df["Test_ID_str"] = df["Test_ID"].astype(str).str.strip()
        df["Slide_Num_str"] = df["Slide_Num"].astype(str).str.strip()

        test_id_str = str(test_id).strip()
        slide_num_str = str(slide_num).strip()

        test_charts = df[
            (df["Test_ID_str"] == test_id_str) & (df["Slide_Num_str"] == slide_num_str)
        ]

        excel_base_path = self.excel_path.parent

        for _, chart_row in test_charts.iterrows():
            source_path = self.safe_get(chart_row, "Source_Path", "")
            if source_path in [None, "", np.nan]:
                continue

            if isinstance(source_path, str) and source_path.startswith("TEXT:"):
                charts.append(source_path)
                continue

            try:
                normalized_path = PathNormalizer.normalize_and_validate(
                    source_path, base_path=excel_base_path, must_exist=True
                )
                charts.append(str(normalized_path))
            except FileNotFoundError as e:
                print(f"❌ Error: {e}")
                raise

        return charts

    def get_theme_colors(self, test_id: str) -> Optional[Dict]:
        """Get theme colors supporting both light/dark rows and flat single-row layouts."""
        if "Theme_Config" not in self.loaded_data:
            return None

        df = self.loaded_data["Theme_Config"]
        if "Test_ID" not in df.columns:
            return None

        df["Test_ID_str"] = df["Test_ID"].astype(str).str.strip()
        test_id_str = str(test_id).strip()
        test_themes = df[df["Test_ID_str"] == test_id_str]

        if len(test_themes) == 0:
            test_themes = df[df["Test_ID"].isna()]

        if len(test_themes) == 0:
            return None

        # All color fields (original + new semantic tokens)
        color_fields = [
            "primary", "text", "muted", "light", "footnote"
            "content_bg", "slide_bg", "header_border",
            "bg_dark", "bg", "bg_light", "text_muted",
            "highlight", "border", "border_muted",
            "secondary", "danger", "warning", "success", "info",
        ]

        # ── Try two-row light/dark layout ────────────────────────────────────
        has_theme_name_col = "Theme_Name" in df.columns
        if has_theme_name_col:
            light_rows = test_themes[
                test_themes["Theme_Name"].astype(str).str.strip().str.lower() == "light"
            ]
            dark_rows = test_themes[
                test_themes["Theme_Name"].astype(str).str.strip().str.lower() == "dark"
            ]

            if len(light_rows) > 0 and len(dark_rows) > 0:
                print("  🎨 Theme_Config: found separate light/dark rows")

                def extract_colors(row):
                    colors = {}
                    for field in color_fields:
                        value = self.safe_get(row, field)
                        if value not in [None, "", np.nan]:
                            colors[field] = str(value)
                    return colors

                light_colors = extract_colors(light_rows.iloc[0])
                dark_colors  = extract_colors(dark_rows.iloc[0])

                print(f"  ✓ Light theme: {len(light_colors)} field(s)")
                print(f"  ✓ Dark theme:  {len(dark_colors)} field(s)")

                return {"light": light_colors, "dark": dark_colors}

        # ── Fall back: single row (legacy / 'default' Theme_Name) ────────────
        print("  🎨 Theme_Config: using single-row (light) theme")
        theme_row = test_themes.iloc[0]
        theme_colors = {}
        for field in color_fields:
            value = self.safe_get(theme_row, field)
            if value not in [None, "", np.nan]:
                theme_colors[field] = str(value)

        return theme_colors if theme_colors else None

    def get_font_sizes(self, test_id: str) -> Optional[Dict[str, str]]:
        """Get font sizes including agenda fonts."""
        if "Font_Config" not in self.loaded_data:
            return None

        df = self.loaded_data["Font_Config"]
        if "Test_ID" not in df.columns:
            return None

        df["Test_ID_str"] = df["Test_ID"].astype(str).str.strip()
        test_id_str = str(test_id).strip()
        test_fonts = df[df["Test_ID_str"] == test_id_str]

        if len(test_fonts) == 0:
            test_fonts = df[df["Test_ID"].isna()]

        if len(test_fonts) == 0:
            return None

        font_row = test_fonts.iloc[0]
        font_sizes = {}

        # UPDATED: Added agenda font fields
        font_fields = [
            "title",
            "subtitle",
            "body",
            "overlay",
            "footnote",
            "footer",
            "agenda_group_heading",
            "agenda_item",
            "index_group_heading",
            "index_item",
        ]

        for field in font_fields:
            value = self.safe_get(font_row, field)
            if value not in [None, "", np.nan]:
                font_sizes[field] = str(value)

        # NEW: read font_family (e.g. "Consolas, monospace")
        font_family_val = self.safe_get(font_row, "font_family")
        if font_family_val not in [None, "", np.nan]:
            font_sizes["font_family"] = str(font_family_val)

        return font_sizes if font_sizes else None



    def diagnose_warning_strip(self, test_id: str, slide_num: int) -> None:
        """
        Diagnostic function to trace warning_strip data flow from Excel to Python.

        Args:
            test_id: Test ID to check
            slide_num: Slide number to check
        """
        print("\n" + "=" * 70)
        print("🔍 DIAGNOSTIC: Warning Strip Data Flow")
        print(f"   Test_ID: {test_id}, Slide_Num: {slide_num}")
        print("=" * 70)

        # Step 1: Check if Slide_Config sheet exists
        if "Slide_Config" not in self.loaded_data:
            print("❌ FAIL: Slide_Config sheet not found in loaded_data")
            return
        print("✅ PASS: Slide_Config sheet loaded")

        df = self.loaded_data["Slide_Config"]

        # Step 2: Check if warning_strip columns exist
        warning_columns = [
            "warning_strip_text",
            "warning_strip_position",
            "warning_strip_bg_color",
            "warning_strip_text_color",
            "warning_strip_height",
        ]

        print("\n📋 Checking for warning_strip columns:")
        missing_cols = []

        for col in warning_columns:
            if col in df.columns:
                print(f"   ✅ {col}")
            else:
                print(f"   ❌ {col} - MISSING!")
                missing_cols.append(col)

        if missing_cols:
            print(f"\n❌ FAIL: Missing columns: {missing_cols}")
            print("   → Add these columns to Slide_Config sheet in Excel")
            return

        # Step 3: Find the specific slide row
        df["Test_ID_str"] = df["Test_ID"].astype(str).str.strip()
        df["Slide_Num_str"] = df["Slide_Num"].astype(str).str.strip()

        test_id_str = str(test_id).strip()
        slide_num_str = str(slide_num).strip()

        matching_rows = df[
            (df["Test_ID_str"] == test_id_str) & (df["Slide_Num_str"] == slide_num_str)
        ]

        if len(matching_rows) == 0:
            print(
                f"\n❌ FAIL: No slide found with Test_ID='{test_id}' and Slide_Num={slide_num}"
            )
            return
        print(f"\n✅ PASS: Found {len(matching_rows)} matching row(s)")

        slide_row = matching_rows.iloc[0]

        # Step 4: Extract warning_strip values
        print("\n📊 Raw Excel Values:")
        for col in warning_columns:
            raw_value = slide_row.get(col)
            safe_value = self.safe_get(slide_row, col)

            print(f"   {col}:")
            print(f"      Raw: {repr(raw_value)} (type: {type(raw_value).__name__})")
            print(f"      Safe: {repr(safe_value)} (type: {type(safe_value).__name__})")

            # Check if value is empty/None
            is_empty = (
                safe_value is None
                or safe_value == ""
                or (isinstance(safe_value, float) and pd.isna(safe_value))
            )
            print(f"      Empty?: {is_empty}")

        # Step 5: Simulate the actual extraction logic
        print("\n🔧 Simulating _build_slide_from_row() logic:")

        warning_strip_text = self.safe_get(slide_row, "warning_strip_text")
        print(f"   warning_strip_text = {repr(warning_strip_text)}")

        if warning_strip_text not in [None, "", np.nan]:
            print("   ✅ PASS: Text is NOT empty, building warning_strip dict")

            warning_strip = {
                "text": warning_strip_text,
                "position": self.safe_get(slide_row, "warning_strip_position", "top"),
                "bg_color": self.safe_get(slide_row, "warning_strip_bg_color"),
                "text_color": self.safe_get(slide_row, "warning_strip_text_color"),
                "height": self.safe_get(slide_row, "warning_strip_height"),
            }
            print("\n📦 Built warning_strip dictionary:")
            for key, value in warning_strip.items():
                print(f"      {key}: {repr(value)}")

            # Check for potential issues
            print("\n⚠️  Potential Issues Check:")
            issues = []

            if warning_strip["position"] not in ["top", "bottom", None]:
                issues.append(
                    f"Invalid position: '{warning_strip['position']}' (should be 'top' or 'bottom')"
                )

            if warning_strip["height"]:
                try:
                    height_val = int(warning_strip["height"])
                    if height_val <= 0 or height_val > 200:
                        issues.append(
                            f"Suspicious height: {height_val}px (should be 20-50px typically)"
                        )
                except (ValueError, TypeError):
                    issues.append(
                        f"Invalid height: '{warning_strip['height']}' (should be a number)"
                    )

            if issues:
                for issue in issues:
                    print(f"      ⚠️  {issue}")
            else:
                print("      ✅ No issues detected")

        else:
            print("   ❌ FAIL: Text is empty/None/NaN")
            print("      Value comparison:")
            print(f"         warning_strip_text == None: {warning_strip_text is None}")
            print(f"         warning_strip_text == '': {warning_strip_text == ''}")
            if warning_strip_text is not None:
                print(f"         pd.isna(warning_strip_text): {pd.isna(warning_strip_text)}")

        print("\n" + "=" * 70)
        print("📢 DIAGNOSTIC COMPLETE")
        print("=" * 70 + "\n")

    def run_test(
        self, test_id: str, output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Run a single test configuration."""
        print(f"\n🔧 Running Test: {test_id}")
        print("-" * 50)

        start_time = datetime.now()

        try:
            global_config = self.get_global_config(test_id)

            # Check slide 29 for warning box
            # self.diagnose_warning_strip(test_id, 29)

            # Load help text
            help_text = self.load_help_text()
            print(f"\n📘 Help text loaded: {len(help_text)} characters")

            # Load summary items
            summary_items = self.load_summary_config(test_id)
            print(f"\n📊 Summary items loaded: {len(summary_items)} item(s)")

            if "output_file" in global_config and global_config["output_file"]:
                output_file = str(global_config["output_file"])
            else:
                output_file = (
                    f"test_{test_id}_{start_time.strftime('%Y%m%d_%H%M%S')}.html"
                )

            if output_dir:
                output_file = str(output_dir / Path(output_file).name)

            slides_config = self.build_slides_config(test_id)
            if not slides_config:
                raise ValueError(f"No slides defined for test '{test_id}'")

            theme_colors = self.get_theme_colors(test_id)
            font_sizes = self.get_font_sizes(test_id)

            slidejs_params = {
                "slides_config": slides_config,
                "output_file": output_file,
                "help_text": help_text,
                "summary_items": summary_items,
            }

            optional_params = {
                "page_title": global_config.get("page_title"),
                "company_name": global_config.get("company_name"),
                "default_footer": global_config.get("default_footer"),
                "current_date": global_config.get("current_date"),
                "js_folder": global_config.get("js_folder"),
                "slide_width": global_config.get("slide_width"),
                "slide_height": global_config.get("slide_height"),
                "theme_colors": theme_colors,
                "font_sizes": font_sizes,
                "debug_mode": global_config.get("debug_mode"),
                "console_debug": global_config.get("console_debug", False),
                "console_level": global_config.get("console_level", "info"),
                "enabled_buttons": global_config.get("buttons"),
                "glass_effect_slides": global_config.get("glass_effect_slides"),
                "index_columns": global_config.get("index_columns"),
            }

            # Add non-None optional params
            for key, value in optional_params.items():
                if value is not None:
                    slidejs_params[key] = value

            print("📊 Configuration Summary:")
            print(f"  • Slides: {len(slides_config)}")
            print(f"  • Output: {output_file}")

            # Show button configuration
            if (
                "enabled_buttons" in slidejs_params
                and slidejs_params["enabled_buttons"]
            ):
                print(f"  • Enabled Buttons: {slidejs_params['enabled_buttons']}")

            total_charts = sum(len(slide.get("charts", [])) for slide in slides_config)
            print(f"  • Total Charts: {total_charts}")

            print("\n🚀 Executing slidejs...")
            result = slidejs(**slidejs_params)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            test_result = {
                "test_id": test_id,
                "status": "PASS",
                "output_file": result,
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": duration,
                "slides_count": len(slides_config),
                "charts_count": total_charts,
                "error": None,
                "parameters_used": list(slidejs_params.keys()),
            }

            print(f"✅ Test '{test_id}' completed successfully")
            print(f"   Duration: {duration:.2f} seconds")
            print(f"   Output: {result}")

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_msg = str(e)
            print(f"❌ Test '{test_id}' failed: {error_msg}")
            print(f"   Duration: {duration:.2f} seconds")
            print("\n📋 Full traceback:")
            traceback.print_exc()

            test_result = {
                "test_id": test_id,
                "status": "FAIL",
                "output_file": None,
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": duration,
                "slides_count": 0,
                "charts_count": 0,
                "error": error_msg,
                "error_details": traceback.format_exc(),
                "parameters_used": [],
            }

        self.test_results.append(test_result)
        return test_result

    def run_all_tests(
        self, output_dir: Optional[Union[str, Path]] = None
    ) -> List[Dict[str, Any]]:
        """Run all tests."""
        test_ids = self.get_test_ids()
        if not test_ids:
            print("❌ No Test_IDs found!")
            return []

        print(f"\n🔍 Found {len(test_ids)} test(s): {', '.join(test_ids)}")

        for test_id in test_ids:
            self.run_test(test_id, output_dir)

        self.generate_summary()
        return self.test_results

    def generate_summary(self) -> None:
        """Generate test execution summary."""
        if not self.test_results:
            return

        print("\n" + "=" * 60)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        total_duration = sum(r["duration_seconds"] for r in self.test_results)
        total_slides = sum(r["slides_count"] for r in self.test_results)
        total_charts = sum(r["charts_count"] for r in self.test_results)

        print("\n📈 Statistics:")
        print(f"  • Total Tests: {total_tests}")
        print(f"  • Passed: {passed_tests} ({passed_tests / total_tests * 100:.1f}%)")
        print(f"  • Failed: {failed_tests} ({failed_tests / total_tests * 100:.1f}%)")
        print(f"  • Total Duration: {total_duration:.2f} seconds")
        print(f"  • Total Slides: {total_slides}")
        print(f"  • Total Charts: {total_charts}")

        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  • {result['test_id']}: {result['error']}")

        print("\n✅ Successful Tests:")
        for result in self.test_results:
            if result["status"] == "PASS":
                print(f"  • {result['test_id']}: {result['output_file']}")


def run_test(test_id, excel_file, output_dir=None, output_file=None, **kwargs):
    """Module-level wrapper for package import."""
    runner = slidejsExcelRunner(excel_file, **kwargs)
    
    if output_file:
        # Create the directory if it doesn't exist
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Override the output_file in global_config by modifying the loaded data
        if "Global_Config" in runner.loaded_data:
            # Find or create a row for this test_id with output_file parameter
            df = runner.loaded_data["Global_Config"]
            
            # Check if output_file parameter already exists for this test_id
            mask = (df["Test_ID"].astype(str).str.strip() == str(test_id).strip()) & \
                   (df["Parameter"].astype(str).str.strip() == "output_file")
            
            if mask.any():
                # Update existing row
                df.loc[mask, "Test_Value"] = str(output_path)
            else:
                # Add new row
                new_row = pd.DataFrame({
                    "Parameter": ["output_file"],
                    "Test_ID": [test_id],
                    "Test_Value": [str(output_path)],
                    "Default Value": [""]
                })
                runner.loaded_data["Global_Config"] = pd.concat([df, new_row], ignore_index=True)
        
        # Run with output_dir (the actual path will come from global_config)
        return runner.run_test(test_id=test_id, output_dir=output_path.parent)
    elif output_dir:
        # If only output_dir provided, use auto-generated filename
        return runner.run_test(test_id=test_id, output_dir=output_dir)
    else:
        # Default behavior
        return runner.run_test(test_id=test_id)

def main():
    """Main function."""
    import argparse

    # DEFAULT_EXCEL = Path(Path(ff) / "slidejs.xlsm")
    DEFAULT_EXCEL = "slidejs.xlsm"

    parser = argparse.ArgumentParser(description="Run slidejs tests from Excel")
    parser.add_argument("excel_file", nargs="?", default=DEFAULT_EXCEL)
    parser.add_argument("--output-dir", "-o", default="test_outputs")
    parser.add_argument("--save-results", "-s", action="store_true")
    parser.add_argument("--test-id", "-t", default=None)
    parser.add_argument("--list-tests", "-l", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 slidejs Excel Test Runner v2.0")
    print("=" * 60)

    excel_path = Path(args.excel_file)
    if not excel_path.exists():
        print(f"❌ Excel file not found: {excel_path}")
        return 1

    print(f"📄 Configuration: {excel_path.name}")
    runner = slidejsExcelRunner(excel_path)

    if args.list_tests:
        test_ids = runner.get_test_ids()
        print("\n📋 Available Tests:")
        for i, test_id in enumerate(test_ids, 1):
            print(f"  {i:2}. {test_id}")
        return 0
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.test_id:
        runner.run_test(args.test_id, output_dir)
    else:
        runner.run_all_tests(output_dir)

    if args.save_results and runner.test_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"test_results_{timestamp}.xlsx"
        summary_data = []
        for result in runner.test_results:
            summary_data.append(
                {
                    "test_id": result["test_id"],
                    "status": result["status"],
                    "output_file": result.get("output_file", ""),
                    "duration_seconds": result["duration_seconds"],
                    "slides_count": result["slides_count"],
                    "charts_count": result["charts_count"],
                    "error": result.get("error", ""),
                }
            )
        if summary_data:
            df = pd.DataFrame(summary_data)
            df.to_excel(results_file, index=False)
            print(f"\n📋 Results saved: {results_file}")

    failed_tests = sum(1 for r in runner.test_results if r["status"] == "FAIL")
    return 1 if failed_tests > 0 else 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)