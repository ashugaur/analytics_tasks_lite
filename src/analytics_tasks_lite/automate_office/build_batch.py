import re
import os
import ast
import json
import glob
import psutil
import shutil
import inspect
import subprocess
import numpy as np
import pandas as pd
import importlib.resources as pkg_resources
from art import tprint
import win32com.client
from pathlib import Path
from datetime import datetime, timezone
from openpyxl.utils import get_column_letter
import sys
from analytics_tasks.utils.controlling import log_start, log_end
from analytics_tasks.utils.scanning import scan_dir
from analytics_tasks.utils.imputing import fill_missing_colors
import matplotlib.pyplot as plt
from analytics_tasks.utils.os_functions import copy_folders_no_overwrite

folder_dt = datetime.now(timezone.utc).strftime("%Y%m%d")
file_dt = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def initialize_batch_globals(at_dir):
    """Initialize global variables in the calling module"""
    # Get the calling module's globals
    caller_globals = sys._getframe(1).f_globals

    # Get the results
    results = lib_refs_ao_batch(at_dir)
    var_names = [
        "_colors_file",
        "_xlsm_path",
        "_logs_dir",
        "_learn_dir",
        "_output_pptm",
        "_control_file",
        "_control_file_worksheet",
        "_template_path",
        "_template_pathx",
        "_visual_library_dir",
        "_image_dir",
        "_chart_data_dir",
        "_slide_json_path",
        "_slide_excel_path",
        "_master_json_path",
        "_master_excel_path",
        "_excel_output_path",
        "_learn_xl_output",
        "_colors",
    ]

    # Set variables in caller's global scope
    for name, value in zip(var_names, results):
        caller_globals[name] = value


def lib_refs_ao_batch(at_dir, report_name=None):
    """Assigns working libraries inside visual_library dir."""

    tprint("Batch mode", font="cybermedum")

    # Main directories
    _automate_office_dir = at_dir / "automate_office"
    
    _input_dir = _automate_office_dir / "input"
    _input_data_dir = _automate_office_dir / "input/data"
    _input_img_dir = _automate_office_dir / "input/img"
    _input_template_dir = _automate_office_dir / "input/templates"
    _learn_dir = _automate_office_dir / "output/learn"
    _logs_dir = _automate_office_dir / "output/log"
    _explore_dir = _automate_office_dir / "output/explore"

    # Copy demo template to working directory
    result = copy_input_dir(_automate_office_dir)
    print(f"Input copied to: {result}")

    # File folder reference post demo copy
    _control_file = _automate_office_dir / "input/____control.xlsm"
    _control_file_worksheet = "calibration"

    _image_dir = _automate_office_dir / "input/img/event_1"
    _chart_data_dir = _automate_office_dir / "input/data/event_1"
    _template_path = _automate_office_dir / "input/templates/template_v2.potm"
    _template_pathx = _automate_office_dir / "output/template_vx.potm"

    # Learn
    _slide_json_path = _automate_office_dir / "output/learn/elements.json"
    _slide_excel_path = _automate_office_dir / "output/learn/elements.xlsx"
    _master_json_path = _automate_office_dir / "output/learn/elements_master.json"
    _master_excel_path = _automate_office_dir / "output/learn/elements_master.xlsx"
    _excel_output_path = _automate_office_dir / "output/learn/txt.xlsx"

    if report_name:
        _output_pptm = _automate_office_dir / f"output/{report_name}__{file_dt}.pptm"
    else:
        _output_pptm = _automate_office_dir / f"output/report__{file_dt}.pptm"
    _xlsm_path = (
        _automate_office_dir
        / rf"output/explore/{(Path(_output_pptm).name).rsplit('.')[0]}.xlsm"
    )

    _learn_xl_output = (
        _automate_office_dir
        / f"output/learn/lc_{(Path(_output_pptm).name).rsplit('.')[0]}.xlsx"
    )

    Path(_automate_office_dir).mkdir(parents=True, exist_ok=True)
    
    Path(_input_dir).mkdir(parents=True, exist_ok=True)
    Path(_input_data_dir).mkdir(parents=True, exist_ok=True)
    Path(_input_img_dir).mkdir(parents=True, exist_ok=True)
    Path(_input_template_dir).mkdir(parents=True, exist_ok=True)
    Path(_learn_dir).mkdir(parents=True, exist_ok=True)
    Path(_logs_dir).mkdir(parents=True, exist_ok=True)
    Path(_explore_dir).mkdir(parents=True, exist_ok=True)

    print("Assigned visual_library directories.")

    check_and_confirm_close_applications()

    close_powerpoint_excel()

    log_start(_logs_dir)

    try:
        _visual_library_dir = at_dir / "visual_library"
        _colors_file = _visual_library_dir / "____settings/colors.xlsm"
        _colors = my_colors(_colors_file)
        Path(_visual_library_dir).mkdir(parents=True, exist_ok=True)

    except Exception:
        print(f"File not found: {_colors_file}. Returning an empty DataFrame.")
        _colors_file = ""
        _colors = pd.DataFrame()
        _visual_library_dir = ''

    return (
        _colors_file,
        _xlsm_path,
        _logs_dir,
        _learn_dir,
        _output_pptm,
        _control_file,
        _control_file_worksheet,
        _template_path,
        _template_pathx,
        _visual_library_dir,
        _image_dir,
        _chart_data_dir,
        _slide_json_path,
        _slide_excel_path,
        _master_json_path,
        _master_excel_path,
        _excel_output_path,
        _learn_xl_output,
        _colors,
    )


def execute_pptx_pipeline(
    _control,
    scan_python_functions_from_file_s,
    _visual_library_dir,
    _learn_dir,
    _chart_data_dir,
    _image_dir,
    _colors_file,
    _template_path,
    _template_pathx,
    _output_pptm,
    slide_master_text_elements,
):
    """Execute the complete PPTX processing pipeline"""

    _control = python_override(
        _control,
        scan_python_functions_from_file_s,
        _visual_library_dir,
        _learn_dir,
        _chart_data_dir,
        _image_dir,
        _colors_file,
    )

    apply_or_create_potm_colors(
        _template_path,
        _template_pathx,
        _control[["master_name", "layout_name", "element_name"]]
        .drop_duplicates()
        .reset_index(drop=True),
        slide_master_text_elements,
    )

    _template_path = _template_pathx
    create_or_apply_potm(_template_pathx, _output_pptm, _control)

    return _control, _template_path


def draw_charts(
    _control,
    _xlsm_path,
    _visual_library_dir,
    universal_chart_elements,
    _colors,
    _chart_data_dir,
    _output_pptm,
    _image_dir,
    _elements_combined,
    _master_json_path,
    _slide_json_path,
    _slide_excel_path,
    _master_excel_path,
    _excel_output_path,
    _learn_xl_output,
    round_columns,
    _control_file,
    _control_file_worksheet,
):
    """Execute the complete chart drawing and processing pipeline"""

    _control_xlm = macro_baseline(
        _control, _xlsm_path, _visual_library_dir, universal_chart_elements
    )

    create_excel_charts_batch(_control, _colors, _xlsm_path, _chart_data_dir)

    success, df_known_errors = export_to_powerpoint_batch(
        _control, _xlsm_path, _output_pptm, _image_dir
    )

    mask_ppt_errors(
        df_known_errors,
        _elements_combined,
        _master_json_path,
        _output_pptm,
        _slide_json_path,
        _slide_excel_path,
        _master_excel_path,
        _excel_output_path,
        _control,
        _learn_xl_output,
        round_columns,
        _control_file,
        _control_file_worksheet,
        _xlsm_path,
        _image_dir,
    )

    delete_all_chart_placeholders(_output_pptm)

    return _control_xlm, success, df_known_errors


def adjust_colors(universal_chart_elements, slide_master_text_elements):
    """
    Adjusts the colors in slide_master_text_elements based on the chartElementsColor
    from universal_chart_elements.

    Args:
        universal_chart_elements (dict): Dictionary containing chart element properties.
        slide_master_text_elements (dict): Dictionary containing slide master text element colors.

    Returns:
        dict: Updated slide_master_text_elements dictionary.
    """

    base_color_str = universal_chart_elements.get("chartElementsColor")
    if not base_color_str:
        return slide_master_text_elements  # Return original if base color is missing

    # Extract RGB values from the string
    base_color_rgb = tuple(map(int, base_color_str[4:-1].split(", ")))

    updated_slide_master_text_elements = {}
    for key, color_str in slide_master_text_elements.items():
        if key == "title":
            updated_slide_master_text_elements[key] = base_color_str
        else:
            # Create alpha variations (simplified example)
            alpha_values = [int(c * 0.5) for c in base_color_rgb]  # Example: 50% alpha
            updated_slide_master_text_elements[key] = (
                f"RGB({alpha_values[0]}, {alpha_values[1]}, {alpha_values[2]})"
            )

    return updated_slide_master_text_elements


def parse_rgb(rgb_string):
    match = re.search(r"RGB\((\d+),\s*(\d+),\s*(\d+)\)", rgb_string)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    raise ValueError(f"Invalid RGB format: {rgb_string}")


def rgb_to_bgr_hex(rgb_tuple):
    return int(
        "{:02x}{:02x}{:02x}".format(rgb_tuple[2], rgb_tuple[1], rgb_tuple[0]), 16
    )


def apply_or_create_potm_colors(
    template_path, output_potm, control, slide_master_text_elements
):
    ppt_app = None
    template_ppt = None
    try:
        ppt_app = win32com.client.Dispatch("PowerPoint.Application")
        ppt_app.Visible = 1
    except Exception as e:
        print(f"Error initializing PowerPoint: {e}")
        return

    if not os.path.exists(template_path):
        print(f"Error: Template file not found at {template_path}")
        if ppt_app:
            ppt_app.Quit()
        return

    output_dir = os.path.dirname(output_potm)
    if not os.path.exists(output_dir):
        # print(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)

    try:
        # print(f"Opening template: {template_path}")
        template_ppt = ppt_app.Presentations.Open(template_path, WithWindow=False)
    except Exception as e:
        print(f"Error opening template {template_path}: {e}")
        if ppt_app:
            ppt_app.Quit()
        return

    # Process each slide master
    for master_name, master_group in control.groupby("master_name"):
        target_master = None
        for design in template_ppt.Designs:
            # print(f"Found design: {design.Name}")
            if design.Name.lower() == master_name.lower():
                target_master = design.SlideMaster
                break
        if not target_master:
            print(
                f"Warning: Master '{master_name}' not found. Using default SlideMaster."
            )
            target_master = template_ppt.SlideMaster

        for shape in target_master.Shapes:
            shape_name = shape.Name.lower()
            # print(f" - Found shape: {shape.Name}")
            if shape_name in slide_master_text_elements:
                try:
                    rgb_color = parse_rgb(slide_master_text_elements[shape_name])
                    bgr_hex = rgb_to_bgr_hex(rgb_color)
                    # print(f"   Applying font color {rgb_color} (BGR: {bgr_hex}) to '{shape_name}'")
                    if shape.HasTextFrame:
                        shape.TextFrame.TextRange.Font.Color.RGB = bgr_hex
                except Exception as e:
                    print(
                        f"WARNING: Failed to apply color to {master_name}_{shape_name}: {e}"
                    )

        for layout_name, layout_group in master_group.groupby("layout_name"):
            # print(f"\nProcessing layout '{layout_name}' in master '{master_name}':")
            target_layout = None
            for custom_layout in target_master.CustomLayouts:
                if custom_layout.Name.lower() == layout_name.lower():
                    target_layout = custom_layout
                    break
            if not target_layout:
                print(
                    f"Warning: Layout '{layout_name}' not found in master '{master_name}'. Skipping."
                )
                continue

            for shape in target_layout.Shapes:
                shape_name = shape.Name.lower()
                # print(f" - Found shape: {shape.Name}")
                if shape_name in slide_master_text_elements:
                    try:
                        rgb_color = parse_rgb(slide_master_text_elements[shape_name])
                        bgr_hex = rgb_to_bgr_hex(rgb_color)
                        # print(f"   Applying font color {rgb_color} (BGR: {bgr_hex}) to '{shape_name}'")
                        if shape.HasTextFrame:
                            shape.TextFrame.TextRange.Font.Color.RGB = bgr_hex
                    except Exception as e:
                        print(
                            f"WARNING: Failed to apply color to {master_name}_{layout_name}_{shape_name}: {e}"
                        )

    # Save without verification
    try:
        print(f"Saving modified template as: {output_potm}")
        # Try saving without forcing FileFormat first
        template_ppt.SaveAs(
            str(output_potm)
        )  # Let PowerPoint infer format from extension
        # If that fails, uncomment the next line and comment the above line
        # template_ppt.SaveAs(output_potm, FileFormat=25)  # ppSaveAsOpenXMLTemplateMacroEnabled

        if os.path.exists(output_potm):
            print(
                f"File saved at: {output_potm}, size: {os.path.getsize(output_potm)} bytes"
            )
        else:
            print("Error: Output file was not created.")

        template_ppt.Close()
        ppt_app.Quit()
        print(f"Processed: {output_potm}")
    except Exception as e:
        print(f"Error during save: {e}")
        if template_ppt:
            try:
                template_ppt.Close()
            except Exception:
                pass
        if ppt_app:
            ppt_app.Quit()


def copy_control_file(control_file_path: str, output_file_path: str) -> str:
    """
    Copies the control file to a new location

    control_file_path: Path to the original control file
    output_file_path: Path where the copied file will be saved

    Returns: The path to the copied file
    """

    try:
        os.remove(output_file_path)
        print("WARNING: Old file removed.")
    except Exception:
        print("WARNING: Old file does not exist. No action taken.")

    excel_app = None
    try:
        # Start Excel
        excel_app = win32com.client.DispatchEx("Excel.Application")
        excel_app.Visible = False

        if not os.path.exists(control_file_path):
            print(f"Error: Control file not found at {control_file_path}")
            return None

        # Open the control file
        control_workbook = excel_app.Workbooks.Open(control_file_path)

        # Save as new file
        control_workbook.SaveAs(
            str(output_file_path), FileFormat=52
        )  # 52 = xlsm format

        # Close the control file
        control_workbook.Close()

        return output_file_path

    except Exception as e:
        print(f"Error copying control file: {e}")
        return None

    finally:
        if excel_app:
            try:
                excel_app.Quit()
                del excel_app
            except Exception as e:
                print(f"Error closing Excel: {e}")


def create_excel_charts_batch(
    control_df: pd.DataFrame,
    _colors: pd.DataFrame,
    control_file_path: str,
    input_chart_folder=None,
):
    """
    Processes multiple entries from the control DataFrame, creates sheets in a single Excel file,
    copies chart data, and runs macros to generate charts.

    control_df: Pandas DataFrame containing chart data file names, macro names, and target slide numbers.
    control_file_path: Path to the master Excel control file (.xlsm) containing VBA macros.
    input_chart_folder: Directory where the chart data files are stored.
    """

    global_vars = list(globals().keys())

    # Check if df is in globals
    if "df" in globals():
        print("DEBUG: 'df' is found in globals")
        outer_df = globals()["df"]
        print(f"DEBUG: Shape of global df: {outer_df.shape}")
    else:
        print("DEBUG: 'df' is NOT found in globals")
        outer_df = None

    # Also check locals (current namespace)
    local_vars = list(locals().keys())

    excel_app = None
    try:
        # Start Excel
        excel_app = win32com.client.DispatchEx("Excel.Application")
        excel_app.Visible = False

        # Open the copied control file
        output_workbook = excel_app.Workbooks.Open(control_file_path)

        # Extract relevant rows where chart_data is valid
        chart_rows = control_df[
            (control_df["chart_data"].notna()) & (control_df["chart_data"] != ".")
        ]

        for _, row in chart_rows.iterrows():
            macro_name = row["chart_hash"]  # Use explicit macro name column
            to_slide = str(row["to_slide"])
            row_number = str(row["row_number"])
            sheet_name = f"{macro_name}_{row_number}"
            chart_dict_str = row["chart_data_dict"]
            if isinstance(chart_dict_str, dict):
                chart_data_dict = chart_dict_str
            else:
                chart_data_dict = ast.literal_eval(chart_dict_str)

            try:
                # Check if sheet exists and delete it if needed
                for sheet in output_workbook.Sheets:
                    if sheet.Name == sheet_name:
                        excel_app.DisplayAlerts = False
                        sheet.Delete()
                        excel_app.DisplayAlerts = True
                        break

                # Add a new sheet
                worksheet = output_workbook.Sheets.Add()
                worksheet.Name = sheet_name
                worksheet.Activate()

                # Variable to hold our dataframe for this iteration
                current_df = None

                # Read data from chart_data file
                if input_chart_folder:
                    chart_data_path = os.path.join(
                        input_chart_folder, row["chart_data"]
                    )
                else:
                    chart_data_path = ""
                if chart_data_path.endswith(".csv"):
                    print(f"\nREADING: {chart_data_path}")
                    try:
                        current_df = pd.read_csv(chart_data_path)
                    except UnicodeDecodeError:
                        current_df = pd.read_csv(chart_data_path, encoding="cp1252")
                    current_df = pass_dict_to_transform(current_df, chart_data_dict)
                    current_df = pass_dict_to_transform_batch(
                        current_df, _colors, chart_data_dict
                    )

                else:
                    print("\nNOTE: No CSV file, checking for available dataframe.")
                    # First try to use the dataframe we found in globals
                    if outer_df is not None:
                        print("Using df from global scope.")
                        current_df = (
                            outer_df.copy()
                        )  # Make a copy to avoid modifying original
                        print(current_df.head(3))
                        current_df = pass_dict_to_transform(current_df, chart_data_dict)
                        current_df = pass_dict_to_transform_batch(
                            current_df, _colors, chart_data_dict
                        )

                    else:
                        # As a fallback, see if we can find df in the caller's frame
                        caller_frame = inspect.currentframe().f_back
                        if caller_frame and "df" in caller_frame.f_locals:
                            print("Found df in caller's namespace.")
                            current_df = caller_frame.f_locals["df"].copy()

                            print(current_df.head(3))
                            _ct_calc, _ct_default = determine_columns(current_df)
                            if _ct_calc == "y":
                                pass
                            else:
                                print(f"Reference: Auto color column is {_ct_calc}.")
                            current_df = clean_merge(
                                current_df, _colors, df1_join_col=_ct_calc
                            ).reset_index(drop=True)
                        else:
                            print("Error: Couldn't find df in any scope.")
                            continue

                # Proceed only if we have a dataframe
                if current_df is not None:
                    # Write data to Excel
                    data_to_write = [current_df.columns.tolist()]
                    data_to_write.extend(current_df.values.tolist())

                    num_rows = len(data_to_write)
                    num_cols = len(data_to_write[0])
                    range_address = f"A1:{chr(64 + num_cols)}{num_rows}"
                    worksheet.Range(range_address).Value = data_to_write

                    # Run the VBA macro after data is in place
                    try:
                        macro_module = f"{macro_name}_{row_number}"
                        macro_location = f"{macro_module}.{macro_name}"
                        excel_app.Run(macro_location)
                        print(
                            f"✅ Successfully created sheet: {sheet_name} and ran macro: {macro_name}"
                        )
                    except Exception as e:
                        print(
                            f"⚠️ Warning: Could not run macro '{macro_name}'. Error: {e}"
                        )
                else:
                    print(f"❌ No data available for sheet: {sheet_name}")

            except Exception as e:
                print(f"❌ Error processing {sheet_name}: {e}")
                import traceback

                traceback.print_exc()  # Print full traceback for better debugging
                continue

        # Save and close
        excel_app.DisplayAlerts = False
        output_workbook.Save()
        output_workbook.Close()
        excel_app.DisplayAlerts = True
        return True

    except Exception as e:
        print(f"❌ Error in batch processing: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        if excel_app:
            try:
                excel_app.Quit()
                del excel_app
            except Exception as e:
                print(f"⚠️ Error closing Excel: {e}")


def export_to_powerpoint_batch(
    control_df: pd.DataFrame,
    excel_file_path: str,
    ppt_file_path: str,
    image_folder: str,
):
    """
    Exports multiple charts from Excel to PowerPoint in one session.

    control_df: Pandas DataFrame containing chart data file names, macro names, and target slide numbers.
    excel_file_path: Path to Excel file containing charts.
    ppt_file_path: Path to PowerPoint file to update.
    image_folder: Path to folder containing images.
    """
    excel_app = None
    ppt_app = None
    df_known_errors = pd.DataFrame(
        columns=control_df.columns
    )  # Initialize error tracking DataFrame
    try:
        # Initialize applications
        excel_app = win32com.client.DispatchEx("Excel.Application")
        ppt_app = win32com.client.Dispatch(
            "PowerPoint.Application"
        )  # Using Dispatch instead of DispatchEx
        excel_app.Visible = False  # Keep Excel hidden

        # Check if files exist
        if not all(os.path.exists(f) for f in [excel_file_path, ppt_file_path]):
            print("❌ Error: One or more files not found")
            return False, df_known_errors

        workbook = excel_app.Workbooks.Open(excel_file_path)
        presentation = ppt_app.Presentations.Open(ppt_file_path)

        # Process each export task
        for _, row in control_df.iterrows():
            if pd.isna(row["element_name_slide"]) or row["element_name_slide"] == ".":
                continue

            try:
                # Get slide
                slide = None
                if row["to_slide"] <= presentation.Slides.Count:
                    slide = presentation.Slides(row["to_slide"])
                    print(f"✅ Using existing slide {row['to_slide']}")
                else:
                    if row["layout_name"] != "_null":
                        # Find layout in master
                        for layout in presentation.SlideMaster.CustomLayouts:
                            if layout.Name == row["layout_name"]:
                                slide = presentation.Slides.Add(row["to_slide"], layout)
                                print(
                                    f"✅ Created new slide {row['to_slide']} with layout {row['layout_name']}"
                                )
                                break
                    if slide is None:
                        print(
                            f"⚠️ Warning: Could not find layout {row['layout_name']}, using default"
                        )
                        slide = presentation.Slides.Add(row["to_slide"], 1)

                if slide is None:
                    print(
                        f"❌ Error: Could not access or create slide {row['to_slide']}"
                    )
                    continue

                # Find the placeholder shape
                placeholder_shape = None
                for shape in slide.Shapes:
                    if shape.Name == row["element_name_slide"]:
                        placeholder_shape = shape
                        break

                if placeholder_shape is None:
                    print(
                        f"❌ Error: Placeholder '{row['element_name_slide']}' not found on slide {row['to_slide']}"
                    )
                    error_row = pd.DataFrame([row])  # Wrap row in DataFrame
                    df_known_errors = pd.concat(
                        [df_known_errors, error_row], ignore_index=True
                    )
                    print(
                        f"🔴 Added error row to df_known_errors. Current length: {len(df_known_errors)}"
                    )
                    continue

                # Update content based on type
                if row["text"] not in [None, ".", np.nan]:
                    try:
                        placeholder_shape.TextFrame.TextRange.Text = str(row["text"])
                        print(
                            f"✅ Updated text in {row['element_name_slide']} on slide {row['to_slide']}"
                        )
                    except Exception as e:
                        print(f"❌ Error updating text: {e}")

                elif row["chart_hash"] not in [None, ".", np.nan]:
                    try:
                        chart_sheet_name = f"{row['chart_hash']}_{row['row_number']}"
                        worksheet = workbook.Sheets(chart_sheet_name)

                        if hasattr(worksheet, "ChartObjects"):
                            chart_objects = worksheet.ChartObjects()
                            if chart_objects.Count > 0:
                                chart_obj = chart_objects(1)
                                chart_obj.Copy()

                                # Paste the chart and position it
                                pasted_shape = slide.Shapes.Paste()
                                if placeholder_shape:
                                    pasted_shape.Left = placeholder_shape.Left
                                    pasted_shape.Top = placeholder_shape.Top
                                    pasted_shape.Width = placeholder_shape.Width
                                    pasted_shape.Height = placeholder_shape.Height

                                print(
                                    f"✅ Inserted chart from {chart_sheet_name} to slide {row['to_slide']}"
                                )
                            else:
                                print(
                                    f"⚠️ Warning: No chart found in sheet {chart_sheet_name}"
                                )
                        else:
                            print(
                                f"⚠️ Warning: No ChartObjects in {chart_sheet_name}, trying Shapes..."
                            )

                            # Fallback to checking Shapes
                            chart_found = False
                            for shape in worksheet.Shapes:
                                if shape.HasChart:
                                    shape.Chart.Copy()
                                    pasted_shape = slide.Shapes.Paste()
                                    if placeholder_shape:
                                        pasted_shape.Left = placeholder_shape.Left
                                        pasted_shape.Top = placeholder_shape.Top
                                        pasted_shape.Width = placeholder_shape.Width
                                        pasted_shape.Height = placeholder_shape.Height

                                    chart_found = True
                                    print(
                                        f"✅ Inserted chart from {chart_sheet_name} to slide {row['to_slide']} (via Shapes)"
                                    )
                                    break

                            if not chart_found:
                                print(
                                    f"❌ Error: No charts found in {chart_sheet_name}"
                                )

                    except Exception as e:
                        print(f"❌ Error inserting chart: {e}")

                elif row["image_link"] not in [None, ".", np.nan]:
                    try:
                        image_path = os.path.join(image_folder, row["image_link"])
                        if os.path.exists(image_path):
                            # Step 1: Get placeholder dimensions and position, then delete it
                            ph_left = placeholder_shape.Left
                            ph_top = placeholder_shape.Top
                            ph_width = placeholder_shape.Width
                            ph_height = placeholder_shape.Height
                            placeholder_name = (
                                placeholder_shape.Name
                            )  # Store name for reference

                            # Delete the placeholder
                            placeholder_shape.Delete()

                            # Step 2: Place the image on the slide
                            picture_shape = slide.Shapes.AddPicture(
                                image_path,
                                LinkToFile=False,
                                SaveWithDocument=True,
                                Left=0,
                                Top=0,
                                Width=-1,  # Original width
                                Height=-1,  # Original height
                            )

                            # Step 3: Lock aspect ratio explicitly
                            picture_shape.LockAspectRatio = True

                            # Step 4: Position and resize with locked aspect ratio
                            orig_aspect = picture_shape.Width / picture_shape.Height
                            ph_aspect = ph_width / ph_height

                            if orig_aspect > ph_aspect:
                                picture_shape.Width = ph_width
                            else:
                                picture_shape.Height = ph_height

                            # Center the image at the placeholder's position
                            picture_shape.Left = (
                                ph_left + (ph_width - picture_shape.Width) / 2
                            )
                            picture_shape.Top = (
                                ph_top + (ph_height - picture_shape.Height) / 2
                            )

                            try:
                                picture_shape.Name = f"Image_{placeholder_name}"
                            except Exception:
                                pass  # Ignore if renaming fails

                            # Bring the image to front
                            picture_shape.ZOrder(0)  # 0 = msoBringToFront

                            print(
                                f"✅ Inserted image {row['image_link']} in place of {placeholder_name} with preserved aspect ratio"
                            )
                        else:
                            print(f"⚠️ Warning: Image not found at {image_path}")
                    except Exception as e:
                        print(f"❌ Error inserting image: {e}")

            except Exception as e:
                print(f"❌ Error processing slide {row['to_slide']}: {e}")
                continue

        # Save PowerPoint
        try:
            presentation.Save()
            print("✅ Successfully saved presentation")
            return True, df_known_errors
        except Exception as e:
            print(f"❌ Error saving presentation: {e}")
            return False, df_known_errors

    except Exception as e:
        print(f"❌ Error in PowerPoint batch export: {e}")
        return False, df_known_errors

    finally:
        # Explicitly close Excel workbook before quitting
        if "workbook" in locals():
            try:
                workbook.Close(False)  # Close without saving
            except Exception as e:
                print(f"⚠️ Warning: Error closing Excel workbook: {e}")
            del workbook

        # Release Presentation object
        if "presentation" in locals():
            try:
                presentation.Close()
            except Exception as e:
                print(f"⚠️ Warning: Error closing PowerPoint presentation: {e}")
            del presentation

        # Quit Excel and PowerPoint
        for app, name in [(excel_app, "Excel"), (ppt_app, "PowerPoint")]:
            if app:
                try:
                    app.Quit()
                    print(f"✅ Closed {name}")
                except Exception as e:
                    print(f"⚠️ Warning: Error closing {name}: {e}")
                finally:
                    del app

        # Force garbage collection
        import gc

        gc.collect()

        close_powerpoint_excel()


def calibration(_control_file):
    _control = pd.read_excel(_control_file, sheet_name="calibration")

    ## Modify for same slide same template issue
    _control["row_number"] = range(len(_control))
    _control["row_number"] = (
        _control["row_number"].astype(str) + "_" + _control["to_slide"].astype(str)
    )

    ## Provision to run python code as an override on the primarily vba based process
    df_py_override = _control[_control["py_override"] == 1]

    ch = concatenate_chart_hashes(_control)
    ch = ch.drop_duplicates()
    # del _control['chart_hash']
    _control = pd.merge(_control, ch, on=["master_name", "layout_name"], how="left")

    # Override to auto generate text info on slides
    _control["text"] = np.where(
        ((_control["layout_name"] == "home_1") & (_control["element_name"] == "title")),
        "Calibration",
        _control["text"],
    )
    _control["text"] = np.where(
        (
            (_control["layout_name"] == "home_1")
            & (_control["element_name"] == "subtitle")
        ),
        "chart_hash + master_name + layout_name + chart_data_dict",
        _control["text"],
    )
    _control["text"] = np.where(
        (_control["element_name"] == "slide_header"),
        _control["layout_name"],
        _control["text"],
    )

    _control["text"] = np.where(
        (_control["element_name"] == "subtitle"),
        (
            "master_name: "
            + _control["master_name"]
            + "; layout_name: "
            + _control["layout_name"]
            + "; chart_hash: "
            + _control["chart_hash_1"]
        ),
        _control["text"],
    )
    _control["text"] = np.where(
        (_control["element_name"] == "subtitle_1"),
        (
            "master_name: "
            + _control["master_name"]
            + "; layout_name: "
            + _control["layout_name"]
            + "; chart_hash: "
            + _control["chart_hash_1"]
        ),
        _control["text"],
    )
    _control["text"] = np.where(
        (_control["element_name"] == "subtitle_2"),
        (
            "master_name: "
            + _control["master_name"]
            + "; layout_name: "
            + _control["layout_name"]
            + "; chart_hash: "
            + _control["chart_hash_1"]
        ),
        _control["text"],
    )

    _control["text"] = np.where(
        (_control["element_name"] == "subtitle_desc"),
        "Universal settings are not accounted here, however can be if needed",
        _control["text"],
    )
    _control["text"] = np.where(
        (_control["element_name"] == "subtitle_desc_1"),
        "Universal settings are not accounted here, however can be if needed",
        _control["text"],
    )
    _control["text"] = np.where(
        (_control["element_name"] == "subtitle_desc_2"),
        "Universal settings are not accounted here, however can be if needed",
        _control["text"],
    )

    _control["text"] = np.where(
        (_control["element_name"] == "footnote"),
        "Applies to respective slide master and layout only",
        _control["text"],
    )

    return _control


def check_and_confirm_close_applications():
    """
    Checks if Excel or PowerPoint processes are running, and prompts for confirmation only if they are.
    """
    excel_running = False
    powerpoint_running = False

    try:
        # Check for Excel processes
        result_excel = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq excel.exe"],
            capture_output=True,
            text=True,
        )
        if "excel.exe" in result_excel.stdout.lower():
            excel_running = True

        # Check for PowerPoint processes
        result_powerpoint = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq powerpnt.exe"],
            capture_output=True,
            text=True,
        )
        if "powerpnt.exe" in result_powerpoint.stdout.lower():
            powerpoint_running = True

    except Exception as e:
        print(f"Error checking processes: {e}")
        return  # Exit if process check fails

    if not excel_running and not powerpoint_running:
        return  # No applications running, so exit

    attempts = 0
    while attempts < 5:
        user_input = input(
            "Excel and/or PowerPoint are running. Please ensure you have saved your work. Close applications? (y/n): "
        ).lower()
        if user_input == "y":
            return
        elif user_input == "n":
            continue
        else:
            attempts += 1
            print("Invalid input. Please enter 'y' or 'n'.")

    print("Warning: Maximum attempts reached. Applications will be closed forcefully.")
    return


def clean_merge(df1, df2, df1_join_col="y", how="left"):
    result = pd.merge(df1, df2, left_on=df1_join_col, right_on="y", how=how)
    if df1_join_col != "y":
        if "y_x" in result.columns and "y_y" in result.columns:
            result = result.drop(columns=["y_y"])
            result = result.rename(columns={"y_x": "y"})
    return result


def close_powerpoint_excel():
    """Closes PowerPoint and Excel processes, even if they're stuck in the task manager."""

    processes_to_kill = ["POWERPNT.EXE", "EXCEL.EXE"]  # Process names

    for proc in psutil.process_iter():
        try:
            if proc.name().upper() in processes_to_kill:  # Case-insensitive comparison
                # Try different methods to terminate the process, escalating if necessary
                try:
                    proc.terminate()  # First try a gentle termination
                    proc.wait(5)  # Wait a bit for it to actually close

                except psutil.NoSuchProcess:
                    print(f"Process {proc.pid} already terminated.")
                    continue  # Move to the next process

                except psutil.AccessDenied:
                    print(
                        f"Access denied to terminate process {proc.pid}. Trying to kill..."
                    )
                    try:
                        proc.kill()  # Force kill if terminate fails
                        proc.wait(5)
                        print(f"Process {proc.pid} killed.")
                    except psutil.NoSuchProcess:
                        print(f"Process {proc.pid} already terminated.")
                        continue
                    except psutil.AccessDenied:
                        print(
                            f"Still access denied to kill process {proc.pid}.  Skipping."
                        )
                        continue  # If still access denied, skip the process
                    except Exception as e:
                        print(
                            f"An unexpected error occurred while killing {proc.pid}: {e}"
                        )
                        continue
                except Exception as e:
                    print(
                        f"An unexpected error occurred while terminating {proc.pid}: {e}"
                    )
                    continue

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass  # Process might have already terminated or we don't have access.  Ignore.
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


def combine_dataframes(elements, elements_master, txt, control, round_columns):
    # Merge _elements and _txt on 'element_name'
    elements_merged = elements.merge(
        txt, on=["slide_number", "element_name"], how="left"
    )
    elements_merged["element_name_slide"] = elements_merged["element_name"]

    # Round off
    elements_merged = round_columns(
        elements_merged, ["left", "top", "width", "height"], digits=0
    )
    elements_master = round_columns(
        elements_master, ["left", "top", "width", "height"], digits=0
    )

    final_df = elements_master.merge(
        elements_merged,
        on=["layout_name", "left", "top", "width", "height"],
        how="outer",
        suffixes=("", "_elements"),
    )

    # Prioritize _elements_master values where conflicts exist
    for col in elements_master.columns:
        if col in final_df.columns and col + "_elements" in final_df.columns:
            final_df[col] = final_df[col].fillna(final_df[col + "_elements"])
            final_df.drop(columns=[col + "_elements"], inplace=True)

    # Add remaining _elements and _txt columns that do not exist in _elements_master
    additional_columns = [
        col for col in elements_merged.columns if col not in elements_master.columns
    ]
    final_df = final_df[list(elements_master.columns) + additional_columns]

    # Check if all 'element_name' values are present in _control column names
    missing_elements = set(final_df["element_name"].dropna()) - set(control.columns)
    if missing_elements:
        print("\n")

    # Create a new _control_new dataframe including missing elements as new columns
    control_new = control.copy()
    for element in missing_elements:
        control_new[element] = None  # Initializing missing columns with None

    return final_df, control_new


def concatenate_chart_hashes(df):
    """
    Concatenates non-empty values in the 'chart_hash' column
    for each group of 'master_name' and 'layout_name',
    removing duplicates.

    Args:
    df (pd.DataFrame): The input DataFrame.

    Returns:
    pd.DataFrame: The resulting DataFrame with concatenated 'chart_hash' values.
    """

    # Filter out empty values in the 'chart_hash' column
    df = df[
        df["chart_hash"].notna() & (df["chart_hash"] != "") & (df["chart_hash"] != ".")
    ]

    # Group by 'master_name' and 'layout_name',
    # concatenate 'chart_hash' values, and remove duplicates
    df = (
        df.groupby(["master_name", "layout_name"])["chart_hash"]
        .apply(lambda x: ", ".join(set(x)))
        .reset_index()
    )

    # Rename the 'chart_hash' column to 'chart_hash_1'
    df = df.rename(columns={"chart_hash": "chart_hash_1"})

    return df


def copy_input_dir(destination_path):
    """
    Copy the input folder from the installed analytics_tasks package to a specified destination.

    Args:
        destination_path (str or Path): The destination directory where the input folder will be copied.
                                       The input folder will be created inside this directory.

    Returns:
        str: Path to the copied input folder

    Raises:
        FileNotFoundError: If the input folder cannot be found in the package
        PermissionError: If there are insufficient permissions to copy files
        OSError: If there are other filesystem-related errors
    """
    try:
        # Method 1: Using pkg_resources (recommended for older Python versions)
        try:
            # Get the path to the installed package
            package_path = pkg_resources.resource_filename(
                "analytics_tasks", "automate_office/input"
            )
        except Exception:
            # Method 2: Using importlib.resources (Python 3.9+) or direct import
            try:
                import analytics_tasks.automate_office

                package_dir = Path(analytics_tasks.automate_office.__file__).parent
                package_path = package_dir / "input"
            except Exception:
                # Method 3: Fallback using the package's __file__ attribute
                import analytics_tasks

                package_root = Path(analytics_tasks.__file__).parent
                package_path = package_root / "automate_office/input"

        # Convert to Path object for easier handling
        source_path = Path(package_path)
        dest_path = Path(destination_path)

        # Check if source input folder exists
        if not source_path.exists():
            raise FileNotFoundError(f"input folder not found at: {source_path}")

        if not source_path.is_dir():
            raise FileNotFoundError(
                f"input path exists but is not a directory: {source_path}"
            )

        # Create destination directory if it doesn't exist
        dest_path.mkdir(parents=True, exist_ok=True)

        # Define the target input path
        target_input_path = dest_path / "input"

        # Copy the entire input folder without overwriting
        if target_input_path.exists():
            # If target exists, merge directories without overwriting files
            copy_folders_no_overwrite(source_path, target_input_path)
        else:
            # If target doesn't exist, use regular copytree
            shutil.copytree(source_path, target_input_path)

        print(f"Successfully copied input folder to: {target_input_path}")
        return str(target_input_path)

    except Exception as e:
        print(f"Error copying input folder: {e}")
        raise


def create_or_apply_potm(_template_path, _output_pptm, _control):
    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    ppt_app.Visible = 1  # Make PowerPoint visible (optional)

    # Open the POTM template
    template_ppt = ppt_app.Presentations.Open(_template_path, WithWindow=False)
    template_master = template_ppt.SlideMaster  # Get the slide master

    if os.path.exists(_output_pptm):
        # Open existing PPTM file
        ppt = ppt_app.Presentations.Open(str(_output_pptm), WithWindow=False)
    else:
        # Create a new PPTM from scratch
        ppt = ppt_app.Presentations.Add()
        ppt.SaveAs(_output_pptm, 25)  # Save as PPTM (format 25)

    # Get existing master layouts in the output PPTM
    existing_masters = {layout.Name for layout in ppt.SlideMaster.CustomLayouts}

    # Find the '_null' layout in the master
    null_layout = None
    for layout in ppt.SlideMaster.CustomLayouts:
        if layout.Name == "_null":
            null_layout = layout
            break

    # if null_layout is None:
    # print("Warning: Layout '_null' not found in master. Default layout will be used.")

    # Process _control DataFrame
    for _, row in _control.iterrows():
        if row["run"] == 1:
            layout_name = row["layout_name"]
            target_slide_num = row["to_slide"]

            # First ensure the template's theme is applied if needed
            if layout_name not in existing_masters:
                ppt.ApplyTemplate(_template_path)

            # Find the desired layout in the master
            target_layout = None
            for layout in ppt.SlideMaster.CustomLayouts:
                if layout.Name == layout_name:
                    target_layout = layout
                    break

            if target_layout:
                # Check if target slide exists
                target_slide = None
                try:
                    target_slide = ppt.Slides(target_slide_num)
                except Exception:
                    # Create new slides until we reach the target slide number
                    while ppt.Slides.Count < target_slide_num:
                        ppt.Slides.AddSlide(
                            ppt.Slides.Count + 1,
                            null_layout
                            if null_layout
                            else ppt.SlideMaster.CustomLayouts(1),
                        )
                    target_slide = ppt.Slides(target_slide_num)

                # Apply the layout to the target slide
                if target_slide:
                    target_slide.CustomLayout = target_layout
            else:
                print(f"Warning: Layout '{layout_name}' not found in master")

    ppt.Save()
    ppt.Close()
    template_ppt.Close()
    ppt_app.Quit()

    close_powerpoint_excel()

    print(f"Processed: {_output_pptm}")


def delete_all_chart_placeholders(presentation_path=None):
    close_powerpoint_excel()

    ppt_app = None
    ppt_pres = None
    try:
        ppt_app = win32com.client.gencache.EnsureDispatch("PowerPoint.Application")

        if presentation_path:
            ppt_pres = ppt_app.Presentations.Open(presentation_path)
        else:
            ppt_pres = ppt_app.ActivePresentation

        for slide_index, slide in enumerate(ppt_pres.Slides):
            i = len(slide.Shapes)

            while i > 0:
                shape_to_delete = None
                try:
                    shape = slide.Shapes(i)
                    if shape.Type == 14 and "Chart Placeholder" in shape.Name:
                        shape_to_delete = shape
                        print(
                            f"Deleting chart placeholder '{shape.Name}' from slide {slide_index + 1}"
                        )
                        shape.Delete()

                except Exception as e:
                    print(f"Error processing shape {i} on slide {slide_index + 1}: {e}")

                i -= 1

        if presentation_path:
            ppt_pres.Save()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        try:
            if ppt_pres:
                ppt_pres.Close()
                del ppt_pres
            if ppt_app:
                ppt_app.Quit()
                del ppt_app
        except Exception as e:
            print(f"Error during cleanup: {e}")

        # Force garbage collection to release COM objects
        import gc

        gc.collect()

    close_powerpoint_excel()

    log_end()


def determine_columns(df, override=None):
    """
    Determines the preferred column and always returns 'y' as the second value.

    Args:
        df: The pandas DataFrame containing the columns 'x' and 'y'.
        override: An optional string to override the default column selection.

    Returns:
        A tuple containing the preferred column and 'y'.
    """

    if override:
        return override, "y"

    if len(df["y"].unique()) == 1:
        return "x", "y"

    return "y", "y"


def export_dfs_to_excel(dfs, sheet_names, filename="output.xlsx"):
    """
    Exports a list of Pandas DataFrames to an Excel file, with each DataFrame
    on a separate sheet.

    Args:
        dfs: A list of Pandas DataFrames.
        sheet_names: A list of strings, where each string is the name of the
                     corresponding sheet.  Must be same length as dfs.
        filename: The name of the Excel file to create (default: "output.xlsx").
    """

    if len(dfs) != len(sheet_names):
        raise ValueError("dfs and sheet_names lists must have the same length.")

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        for i, df in enumerate(dfs):
            df.to_excel(writer, sheet_name=sheet_names[i], index=False)  # No index

        workbook = writer.book
        for sheet_name in sheet_names:
            worksheet = workbook[sheet_name]

            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                for cell in column:
                    try:  # Handle potential errors with cell values
                        max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                worksheet.column_dimensions[
                    get_column_letter(column[0].column)
                ].width = max(10, max_length + 2)  # Minimum width of 10

            # Freeze top row
            worksheet.freeze_panes = "A2"  # Freeze the first row

            # Set zoom level
            worksheet.sheet_view.zoomScale = 80

            # Apply filters (Auto Filter on all columns with headers)
            worksheet.auto_filter.ref = worksheet.dimensions

    print(f"DataFrames exported to {filename} successfully.", end="")


def extract_master_pptx_to_json(presentation_path, master_json_path):
    """Extracts elements from the Slide Master and saves them to JSON."""

    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    presentation = ppt_app.Presentations.Open(presentation_path, WithWindow=False)

    masters_data = []

    # Loop through Slide Masters
    for master in presentation.Designs:
        master_info = {"master_name": master.Name, "layouts": []}

        # Loop through layouts in the Slide Master
        for layout in master.SlideMaster.CustomLayouts:
            layout_info = {"layout_name": layout.Name, "elements": []}

            for i, shape in enumerate(
                layout.Shapes, start=1
            ):  # Enumerate to get shape_index
                element = {
                    "shape_index": i,  # ADDED: Include shape index
                    "shape_id": shape.Id,  # Add shape ID here
                    "name": shape.Name,
                    "type": shape.Type,
                    "left": shape.Left,
                    "top": shape.Top,
                    "width": shape.Width,
                    "height": shape.Height,
                }

                # Extract text for text elements
                if shape.Type == 14 and shape.TextFrame.HasText:
                    element["text"] = shape.TextFrame.TextRange.Text

                # Extract Straight Connector details
                if shape.Type == 9 or "connector" in shape.Name.lower():
                    try:
                        element["connector"] = {
                            "start_x": shape.ConnectorFormat.BeginX,
                            "start_y": shape.ConnectorFormat.BeginY,
                            "end_x": shape.ConnectorFormat.EndX,
                            "end_y": shape.ConnectorFormat.EndY,
                            "line_color": shape.Line.ForeColor.RGB,
                            "line_weight": shape.Line.Weight,
                            "dash_style": shape.Line.DashStyle,
                        }
                    except Exception as e:
                        element["connector_error"] = str(e)

                layout_info["elements"].append(element)

            master_info["layouts"].append(layout_info)

        masters_data.append(master_info)

    # Close PowerPoint
    presentation.Close()
    ppt_app.Quit()

    # Save template data to JSON
    with open(master_json_path, "w") as master_file:
        json.dump(masters_data, master_file, indent=4)


def extract_pptx_to_json(presentation_path, slide_json_path):
    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    presentation = ppt_app.Presentations.Open(presentation_path, WithWindow=False)

    slides_data = []

    for slide in presentation.Slides:
        try:
            section_name = slide.sectionTitle
        except Exception:
            section_name = "slide"

        slide_name = f"{section_name}_{slide.SlideNumber}"

        slide_info = {
            "layout_name": get_actual_layout_name(slide),
            "slide_name": slide_name,
            "slide_number": slide.SlideIndex,
            "elements": [],
        }

        for i, shape in enumerate(slide.Shapes, start=1):
            element = {
                "shape_index": i,
                "shape_id": shape.Id,  # Add shape ID here
                "name": shape.Name,
                "type": shape.Type,
                "role": get_shape_role(shape.Name),
                "left": shape.Left,
                "top": shape.Top,
                "width": shape.Width,
                "height": shape.Height,
            }

            if shape.Type == 14 and shape.TextFrame.HasText:
                element["text"] = shape.TextFrame.TextRange.Text

            if shape.Type == 15:
                element["chart_type"] = shape.Chart.ChartType
                element["series_count"] = shape.Chart.SeriesCollection().Count

            slide_info["elements"].append(element)

        slides_data.append(slide_info)

    presentation.Close()
    ppt_app.Quit()

    with open(slide_json_path, "w") as slide_file:
        json.dump(slides_data, slide_file, indent=4)


def extract_text_from_pptx(presentation_path, excel_output_path):
    """Extracts element names, text, and slide numbers from PowerPoint (excluding charts) and saves to Excel."""

    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    presentation = ppt_app.Presentations.Open(presentation_path, WithWindow=False)

    extracted_data = []

    # Loop through slides
    for i, slide in enumerate(
        presentation.Slides
    ):  # Enumerate to get slide index (starting from 0)
        slide_number = i + 1  # Slide numbers start from 1

        for shape in slide.Shapes:
            # Skip charts (Type 15)
            if shape.Type == 15:
                continue

            # Extract element name and text (if available)
            element_name = shape.Name
            text = (
                shape.TextFrame.TextRange.Text
                if shape.HasTextFrame and shape.TextFrame.HasText
                else ""
            )

            extracted_data.append(
                {
                    "slide_number": slide_number,  # Add slide number to the dictionary
                    "element_name": element_name,
                    "text": text,
                }
            )

    # Close PowerPoint
    presentation.Close()
    ppt_app.Quit()

    # Convert to DataFrame
    df = pd.DataFrame(
        extracted_data, columns=["slide_number", "element_name", "text"]
    )  # include slide_number in columns

    # Save to Excel
    df.to_excel(excel_output_path, index=False)


def my_colors(_colors_file):
    """User defined colors."""
    try:
        # Treat color file
        df_colors = pd.read_excel(_colors_file, sheet_name="colors")
        df_colors = df_colors.sort_values(by=["Mode", "Tool", "Usage"]).reset_index(
            drop=True
        )
        df_colors = fill_missing_colors(df_colors)
        df_colors.columns = df_colors.columns.str.lower()
        _colors = df_colors.rename(columns={"usage": "y"})[["y", "color_hex", "color_rgb"]]
    except FileNotFoundError:
        print(f"File not found: {_colors_file}. Returning an empty DataFrame.")
        _colors = pd.DataFrame()
    return _colors


def filter_chart_data_multiline(df, column_name):
    """Filters a DataFrame column for dictionary-like values."""

    def check_braces(value):
        if isinstance(value, dict):
            return True
        elif isinstance(value, str):
            text = value.strip()  # Assign value to text here
            return text.startswith("{") and text.endswith("}")
        return False

    return df[df[column_name].apply(check_braces)]


def find_methods_in_python_file(file_path):
    """finds functions with python files

    source: https://stackoverflow.com/questions/58935006/iterate-over-directory-and-get-function-names-from-found-py-files  + GPT
    """
    methods = []
    o = open(file_path, "r", encoding="utf-8")
    text = o.read()
    # p = ast.parse(repr(text))
    p = ast.parse(text)
    for node in ast.walk(p):
        if isinstance(node, ast.FunctionDef):
            methods.append(node.name)
    return methods


def scan_python_functions_from_file_s(
    _source, _destination, _load_functions, _write_to_mkdocs
):
    """function to load functions from python files in folders to memory"""

    import matplotlib.pyplot as plt
    
    global scan

    _relevant_file_type = [".py"]

    if _write_to_mkdocs == 1:
        os.chdir(_destination.replace("\\", "/"))

        # remove folder
        os.chdir("\\".join(_destination.split("\\")[:-1]))
        shutil.rmtree(_destination.split("\\")[-1])

        # create folder
        Path(_destination.split("\\")[-1]).mkdir(parents=True, exist_ok=True)
        os.chdir(_destination)
        # print('NOTE: functions written to documents site.')
    # else:
    # print('NOTE: functions not written to documents site.')

    # scan folder
    def scan_dir_local(location_to_scan):
        global scan
        scan = []
        for i in glob.iglob(rf"{location_to_scan}\**\*", recursive=True):
            scan.append(i)
        if len(scan) > 0:
            scan = pd.DataFrame(scan).rename(columns={0: "unc"})
            scan["filename"] = scan["unc"].apply(lambda row: Path(row).name)
            scan["ext"] = scan["unc"].apply(
                lambda row: os.path.splitext(os.path.basename(row))[1]
            )
        else:
            scan = pd.DataFrame({"filename": ""}, index=([0]))

    scan_dir_local(_source)

    # flag files and folders
    for i in range(0, len(scan)):
        _unc = scan.loc[i, "unc"]
        scan.loc[i, "dir_flag"] = None
        scan.loc[i, "file_flag"] = None
        if os.path.exists(_unc):
            if os.path.isdir(_unc):
                scan.loc[i, "dir_flag"] = os.path.isdir(_unc)
            else:
                scan.loc[i, "dir_flag"] = False
            if os.path.isfile(_unc):
                scan.loc[i, "file_flag"] = os.path.isfile(_unc)
            else:
                scan.loc[i, "file_flag"] = False

    # filter relevant unc
    scan = scan[scan["file_flag"]]
    scan = scan[scan["ext"].isin(_relevant_file_type)]

    # exceptions
    scan = scan[~scan["filename"].isin(["edupunk.py"])]
    # scan = scan[~scan['filename'].str.contains('functions', case=False, regex=True, na=False)]

    # dir depth
    scan["unc"] = scan["unc"].str.replace("\\", "/")
    scan["depth"] = scan["unc"].str.count("/") - _source.count("\\") - 1
    scan["unc_l1"] = (scan["unc"].str.rsplit("/", expand=True, n=2)[0]).str.replace(
        "/".join(_source.split("\\")[:-1]), _destination.replace("\\", "/")
    )
    scan["_unc_md"] = (
        (scan["unc"].str.rsplit("/", expand=True, n=1)[0]).str.replace(
            "/".join(_source.split("\\")[:-1]), _destination.replace("\\", "/")
        )
        + ".md"
    )

    # write markdown
    select = scan[["unc", "_unc_md", "filename", "ext"]].sort_values(
        ["_unc_md", "filename"]
    )
    select["_filename"] = select["filename"].str.rsplit(".", expand=True, n=1)[0]

    # loop through files
    for unc in select["unc"].unique().tolist():
        function_code = ""

        try:
            # read the contents of the file
            with open(unc, "r", encoding="utf-8") as f:
                file_contents = f.read()

            # parse the file contents into an AST
            parsed_file = ast.parse(file_contents)
            methods = find_methods_in_python_file(unc)

            for _function in methods:
                # find the function definition node in the AST
                function_node = next(
                    (
                        node
                        for node in parsed_file.body
                        if isinstance(node, ast.FunctionDef) and node.name == _function
                    ),
                    None,
                )

                # extract the code of the function
                if function_node is not None:
                    function_code = ast.unparse(function_node)
                else:
                    continue

                if _write_to_mkdocs == 1:
                    _file = (
                        _function + "__" + str((unc.split("/")[-1]).lower())
                    )  # +'.py'
                    with open(_file, "w", encoding="utf-8") as f:
                        f.write("# " + unc + "\n\n" + function_code)

                if 1 == _load_functions:
                    exec(function_code, globals())

        except Exception:
            continue


def get_actual_layout_name(slide):
    try:
        if hasattr(slide, "CustomLayout"):
            return slide.CustomLayout.Name
        elif hasattr(slide, "Layout"):
            for master in slide.Parent.SlideMaster.CustomLayouts:
                if master.Type == slide.Layout:
                    return master.Name
            return f"Built-in Layout ({slide.Layout})"
        else:
            return "Unknown Layout"
    except Exception as e:
        return f"Error getting layout name: {e}"


def get_latest_file(directory):
    try:
        # Get a list of files with the prefix 'explore'
        files = [
            f
            for f in os.listdir(directory)
            if f.startswith("explore") and f.endswith(".xlsm")
        ]

        if not files:
            print("No files found with the prefix 'explore' and .xlsm extension.")
            return None

        # Parse the timestamp from each filename and find the latest one
        latest_file = max(
            files,
            key=lambda f: datetime.strptime(
                re.search(r"\d{8}_\d{4}", f).group(), "%Y%m%d_%H%M"
            ),
        )

        return os.path.join(directory, latest_file)

    except FileNotFoundError:
        print(f"Directory '{directory}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_shape_role(shape_name):
    """Helper function to assign roles based on shape names"""
    name_lower = shape_name.lower()

    if "title" in name_lower:
        return "title"
    elif "chart" in name_lower:
        # Extract number if present in name (e.g., "Chart 1" -> "chart_1")
        import re

        numbers = re.findall(r"\d+", name_lower)
        if numbers:
            return f"chart_{numbers[0]}"
        return "chart_1"  # default if no number found
    else:
        return "other"


def json_to_excel(json_file, output_excel):
    # Load the JSON data
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Prepare a list for flattened data
    rows = []

    # Loop through each slide template
    for slide in data:
        layout_name = slide.get("layout_name", "")
        slide_name = slide.get("slide_name", "")
        slide_number = slide.get("slide_number", "")

        # Loop through elements and create a row for each
        for element in slide.get("elements", []):
            row = {
                # New properties added at the beginning
                "shape_index": element.get("shape_index", ""),
                "shape_id": element.get("shape_id", ""),
                "layout_name": layout_name,
                "slide_name": slide_name,
                "slide_number": slide_number,
                "element_name": element.get("name", ""),
                "type": element.get("type", ""),
                "role": element.get("role", ""),
                "left": element.get("left", ""),
                "top": element.get("top", ""),
                "width": element.get("width", ""),
                "height": element.get("height", ""),
            }

            # Include chart details if applicable
            if "chart_format" in element:
                chart_format = element.get("chart_format", {})
                row.update(
                    {
                        "chart_type": element.get("chart_type", ""),
                        "series_count": element.get("series_count", ""),
                        "chart_title_font_size": chart_format.get(
                            "title_font_size", ""
                        ),
                        "axis_font_size": chart_format.get("axis_font_size", ""),
                    }
                )

            # Include table details if applicable
            if "table_format" in element:
                table_format = element.get("table_format", {})
                row.update(
                    {
                        "rows": table_format.get("rows", ""),
                        "columns": table_format.get("columns", ""),
                    }
                )

            rows.append(row)

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    # Save to Excel
    df.to_excel(output_excel, index=False)


def json_to_excel_master(json_file, output_excel):
    """Converts Slide Master JSON to an Excel file."""

    # Load the JSON data
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    # Loop through each Slide Master
    for master in data:
        master_name = master.get("master_name", "")

        # Loop through layouts
        for layout in master.get("layouts", []):
            layout_name = layout.get("layout_name", "")

            # Loop through elements in the layout
            for element in layout.get("elements", []):
                row = {
                    "master_name": master_name,
                    "layout_name": layout_name,
                    "element_name": element.get("name", ""),
                    "shape_index": element.get("shape_index", ""),
                    "shape_id_mstr": element.get("shape_id", ""),
                    "type": element.get("type", ""),
                    "role": element.get("role", ""),
                    "left": element.get("left", ""),
                    "top": element.get("top", ""),
                    "width": element.get("width", ""),
                    "height": element.get("height", ""),
                }

                rows.append(row)

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    # Save to Excel
    df.to_excel(output_excel, index=False)


def process_vba_files(_control_xlm, _xlsm_path, universal_chart_elements):
    """Main function to process VBA files and create a single XLSM file with multiple modules"""

    try:
        # Create Excel application object
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False

        # Create a new workbook only once
        workbook = excel.Workbooks.Add()

        # Loop through each row in the dataframe
        for index, row in _control_xlm.iterrows():
            unc_path = str(row["unc"])
            chart_dict_str = row["chart_data_dict"]
            to_slide_value = row["row_number"]

            # Step 1: Read the VBA file
            try:
                try:
                    with open(unc_path, "r", encoding="utf-8-sig") as file:
                        vba_code = file.read()
                except UnicodeDecodeError:
                    with open(unc_path, "r") as file:
                        vba_code = file.read()
                # print("Successfully read the VBA file")
            except Exception as e:
                print(f"Error reading file {unc_path}: {str(e)}")
                continue

            # Extract module name (filename without extension)
            module_name = Path(unc_path).stem

            # Create a unique module name using row_number value
            unique_module_name = f"{module_name}_{to_slide_value}"

            # Step 2: Merge dictionaries
            try:
                # Parse the chart_data_dict from string to dictionary
                if isinstance(chart_dict_str, dict):
                    chart_data_dict = chart_dict_str
                else:
                    chart_data_dict = ast.literal_eval(chart_dict_str)

                # Create merged dictionary
                merged_dict = {**universal_chart_elements, **chart_data_dict}
                # print("Successfully merged dictionaries:")
                # print(merged_dict)
            except Exception as e:
                print(f"Error merging dictionaries: {str(e)}")
                continue

            # Step 3: Replace values in the VBA code
            try:
                modified_vba = replace_values_in_vba(vba_code, merged_dict)
                # print("Successfully modified VBA code")
            except Exception as e:
                print(f"Error replacing values in VBA code: {str(e)}")
                continue

            # Step 4: Add the module to the workbook
            try:
                # Add a VBA module
                vb_comp = workbook.VBProject.VBComponents.Add(
                    1
                )  # 1 = vbext_ct_StdModule
                vb_comp.Name = unique_module_name
                vb_comp.CodeModule.AddFromString(modified_vba)
            except Exception as e:
                print(f"Error adding module {unique_module_name} to workbook: {str(e)}")
                continue

        # Save the workbook as XLSM after all modules have been added
        try:
            workbook.SaveAs(
                str(_xlsm_path), 52
            )  # 52 = xlOpenXMLWorkbookMacroEnabled (XLSM)
        except Exception as e:
            print(f"Error saving XLSM file: {str(e)}")

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
    finally:
        # Clean up resources
        if "workbook" in locals():
            workbook.Close(SaveChanges=False)
        if "excel" in locals():
            excel.Quit()
            del excel


def replace_values_in_vba_old(vba_code, merged_dict):
    """Replace values in VBA code based on the merged dictionary"""
    modified_vba = vba_code

    # Keys to ignore for replacement
    ignore_keys = ["x", "y", "z", "value"]

    for key, value in merged_dict.items():
        # Skip keys that should be ignored
        if key in ignore_keys:
            # print(f"  Skipping key: '{key}' (in ignore list)")
            continue

        # More specific pattern targeting variable declarations or assignments
        # Looking for patterns like: "key = value" with optional whitespace
        # Using word boundaries \b to ensure we're matching whole variable names
        if isinstance(value, str):
            if value.startswith("RGB"):
                # Handle RGB values without quotes
                pattern = rf"\b{key}\s*=\s*RGB\([^)]*\)(?:\s*\'[^\n]*)?"
                replacement = f"{key} = {value}"
            else:
                # Handle string values with quotes - more strict pattern
                pattern = rf'\b{key}\s*=\s*"[^"]*"'
                replacement = f'{key} = "{value}"'
        elif isinstance(value, list):
            # Handle list values (assuming first item is used)
            if value and isinstance(value[0], str):
                if value[0].startswith("RGB"):
                    pattern = rf"\b{key}\s*=\s*RGB\([^)]*\)(?:\s*\'[^\n]*)?"
                    replacement = f"{key} = {value[0]}"
                else:
                    pattern = rf'\b{key}\s*=\s*"[^"]*"'
                    replacement = f'{key} = "{value[0]}"'
        else:
            # Handle other types of values
            pattern = rf'\b{key}\s*=\s*[^"\n]+'
            replacement = f"{key} = {value}"

        # Search for the pattern in the VBA code
        match = re.search(pattern, modified_vba)
        if match:
            modified_vba = re.sub(pattern, replacement, modified_vba)
        else:
            print(f"  Reference: Pattern for '{key}' not found in VBA code")

    return modified_vba


def replace_values_in_vba(vba_code, merged_dict):
    """Replace values in VBA code based on the merged dictionary"""
    modified_vba = vba_code

    # print("\nReplacing values in VBA code:")

    # Keys to ignore for replacement
    ignore_keys = ["x", "y", "z", "value"]

    for key, value in merged_dict.items():
        if key in ignore_keys:
            continue

        if key == "sort_array":
            # Handle sort_array separately
            if not value or value == [
                ""
            ]:  # If empty list or contains only an empty string
                replacement = 'sort_array = ""'
            else:
                formatted_values = ", ".join(f'"{v}"' for v in value)
                replacement = f"sort_array = Array({formatted_values})"

            pattern = (
                r"sort_array\s*=\s*Array\([^)]*\)"  # Matches the sort_array pattern
            )
        elif isinstance(value, str):
            if value.startswith("RGB"):
                pattern = rf"\b{key}\s*=\s*RGB\([^)]*\)(?:\s*\'[^\n]*)?"
                replacement = f"{key} = {value}"
            else:
                pattern = rf'\b{key}\s*=\s*"[^"]*"'
                replacement = f'{key} = "{value}"'
        elif isinstance(value, list):
            if value and isinstance(value[0], str):
                if value[0].startswith("RGB"):
                    pattern = rf"\b{key}\s*=\s*RGB\([^)]*\)(?:\s*\'[^\n]*)?"
                    replacement = f"{key} = {value[0]}"
                else:
                    pattern = rf'\b{key}\s*=\s*"[^"]*"'
                    replacement = f'{key} = "{value[0]}"'
        else:
            pattern = rf'\b{key}\s*=\s*[^"\n]+'
            replacement = f"{key} = {value}"

        match = re.search(pattern, modified_vba)
        if match:
            old_text = match.group(0)
            modified_vba = re.sub(pattern, replacement, modified_vba)
        else:
            print(f"  Reference: Pattern for '{key}' not found in VBA code")

    return modified_vba


def create_xlsm_with_vba(_xlsm_path, module_name, vba_code):
    """Create a new XLSM file with the VBA code in a module"""
    # Create Excel application object
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False

    try:
        # Create a new workbook
        workbook = excel.Workbooks.Add()

        # Add a VBA module
        vb_comp = workbook.VBProject.VBComponents.Add(1)  # 1 = vbext_ct_StdModule
        vb_comp.Name = module_name
        vb_comp.CodeModule.AddFromString(vba_code)

        # Save the workbook as XLSM
        workbook.SaveAs(_xlsm_path, 52)  # 52 = xlOpenXMLWorkbookMacroEnabled (XLSM)
        workbook.Close(SaveChanges=False)

    except Exception as e:
        raise Exception(f"Error creating XLSM file: {str(e)}")
    finally:
        # Close Excel application
        excel.Quit()


def macro_baseline(_control, _xlsm_path, _visual_library_dir, universal_chart_elements):
    close_powerpoint_excel()

    ## Select relevant combinations
    _control_xlm = _control[
        ((_control["chart_data_dict"] != ".") & (_control["chart_data_dict"] != ""))
        & (_control["run"] == 1)
        & (_control["py_override"] != 1)
    ][["chart_hash", "chart_data_dict", "to_slide", "row_number"]].reset_index(
        drop=True
    )
    _control_xlm = filter_chart_data_multiline(_control_xlm, "chart_data_dict")
    _control_xlm_initial_len = len(_control_xlm)

    ## Scan drive
    scan = scan_dir(_visual_library_dir, ".bas")

    ## Identify relevant files
    _control_xlm = pd.merge(_control_xlm, scan, how="left", on=["chart_hash"])[
        ["unc", "chart_data_dict", "to_slide", "row_number"]
    ]
    _control_xlm_final_len = len(_control_xlm)

    ## QC
    if _control_xlm_initial_len == _control_xlm_final_len:
        print("\nREPORT: All chart macros found.")
    else:
        print(
            "ERROR: The count of chart macros in control file does not match those in drive."
        )
        print(_control_xlm)

    process_vba_files(_control_xlm, _xlsm_path, universal_chart_elements)

    close_powerpoint_excel()

    return _control_xlm


def mask_ppt_errors(
    df_known_errors,
    _elements_combined,
    _master_json_path,
    _output_pptm,
    _slide_json_path,
    _slide_excel_path,
    _master_excel_path,
    _excel_output_path,
    _control,
    _learn_xl_output,
    round_columns,
    _control_file,
    _control_file_worksheet,
    _xlsm_path,
    _image_dir,
):
    """Re-run learning steps condition to presence of errors."""
    print("REPORT: If nothing runs there are no issues.")
    while len(df_known_errors) != 0:
        close_powerpoint_excel()

        print("WARNING: Total known errors:", len(df_known_errors))
        print("WARNING: Error list...")
        print(
            df_known_errors[["master_name", "layout_name", "element_name", "to_slide"]]
        )

        # Rerun learning
        _control = ppt_learn(
            _master_json_path,
            _output_pptm,
            _slide_json_path,
            _slide_excel_path,
            _master_excel_path,
            _excel_output_path,
            _control,
            _learn_xl_output,
            round_columns,
        )

        # Updated control file
        _control = pd.read_excel(_control_file, sheet_name=_control_file_worksheet)
        _control = pd.merge(
            _control,
            _elements_combined[
                [
                    "master_name",
                    "layout_name",
                    "element_name",
                    "slide_number",
                    "shape_id",
                    "element_name_slide",
                ]
            ].rename(columns={"slide_number": "to_slide"}),
            how="left",
        )
        _control["shape_id"] = _control["shape_id"].astype("Int64")

        common_cols = ["master_name", "layout_name", "element_name"]
        _control = pd.merge(
            _control, df_known_errors[common_cols], how="inner", on=common_cols
        )

        success, df_known_errors = export_to_powerpoint_batch(
            _control, _xlsm_path, _output_pptm, _image_dir
        )

        print(
            "WARNING: Re-run iterations will be <= total known errors that now is",
            len(df_known_errors),
            "something may be wrong if it takes too much time.",
        )


def parse_string(string):
    # Remove leading and trailing whitespace
    string = string.strip()

    # Remove curly braces
    string = string[1:-1]

    # Split into key-value pairs
    pairs = string.split(", ")

    dictionary = {}

    for pair in pairs:
        # Split into key and value
        key, value = pair.split(": ")

        # Remove quotes from key and value
        key = key.strip("'")
        value = value.strip("'")

        # Convert value to list if necessary
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1].split(", ")

        dictionary[key] = value

    return dictionary


def pass_dict_to_transform(df, parameter_dict):
    """
    Takes a DataFrame and a dictionary of parameters, then passes the relevant
    parameters to the transform_data function.

    Args:
        df: The DataFrame to transform
        parameter_dict: Dictionary containing parameter names and values

    Returns:
        Result of transform_data with the appropriate parameters
    """
    # Extract the parameters from the dictionary
    # For list values, take the first item if it exists
    x_param = (
        parameter_dict.get("x", [None])[0]
        if isinstance(parameter_dict.get("x", None), list)
        else parameter_dict.get("x")
    )
    y_param = (
        parameter_dict.get("y", [None])[0]
        if isinstance(parameter_dict.get("y", None), list)
        else parameter_dict.get("y")
    )
    z_param = (
        parameter_dict.get("z", [None])[0]
        if isinstance(parameter_dict.get("z", None), list)
        else parameter_dict.get("z")
    )
    value_param = (
        parameter_dict.get("value", [None])[0]
        if isinstance(parameter_dict.get("value", None), list)
        else parameter_dict.get("value")
    )
    y_override_param = (
        parameter_dict.get("y_override", [None])[0]
        if isinstance(parameter_dict.get("y_override", None), list)
        else parameter_dict.get("y_override")
    )

    # Call transform_data with the extracted parameters
    return transform_data(
        df,
        x=x_param,
        y=y_param,
        z=z_param,
        value=value_param,
        y_override=y_override_param,
    )


def pass_dict_to_transform_batch(df, _colors, parameter_dict):
    """
    Takes a DataFrame and a dictionary of parameters, then passes the relevant
    parameters to the transform_data function.

    Args:
        df: The DataFrame to transform
        parameter_dict: Dictionary containing parameter names and values

    Returns:
        Result of transform_data with the appropriate parameters
    """
    # Extract the parameters from the dictionary
    # For list values, take the first item if it exists
    y_override_col_param = (
        parameter_dict.get("y_override_col", [None])[0]
        if isinstance(parameter_dict.get("y_override_col", None), list)
        else parameter_dict.get("y_override_col")
    )

    y_override_color_param = (
        parameter_dict.get("y_override_color", [None])[0]
        if isinstance(parameter_dict.get("y_override_color", None), list)
        else parameter_dict.get("y_override_color")
    )

    # Call transform_data with the extracted parameters
    return transform_data_batch(
        df,
        _colors,
        y_override_col=y_override_col_param,
        y_override_color=y_override_color_param,
    )


def ppt_learn(
    _master_json_path,
    _output_pptm,
    _slide_json_path,
    _slide_excel_path,
    _master_excel_path,
    _excel_output_path,
    _control,
    _learn_xl_output,
    round_columns,
):
    # Slides
    extract_pptx_to_json(_output_pptm, _slide_json_path)
    json_to_excel(_slide_json_path, _slide_excel_path)

    # Slides master
    extract_master_pptx_to_json(_output_pptm, _master_json_path)
    json_to_excel_master(_master_json_path, _master_excel_path)

    # Extract text from .pptx
    extract_text_from_pptx(_output_pptm, _excel_output_path)

    # Combine learning
    _elements = pd.read_excel(_slide_excel_path)
    _elements_master = pd.read_excel(_master_excel_path)
    _txt = pd.read_excel(_excel_output_path)

    _elements_combined, _control_updated = combine_dataframes(
        _elements, _elements_master, _txt, _control, round_columns
    )
    _elements_combined = _elements_combined.sort_values(
        by=["slide_number"]
    ).reset_index(drop=True)

    # Export
    dfs = [
        _elements_combined,
        _control_updated,
        _control,
        _elements,
        _elements_master,
        _txt,
    ]
    sheet_names = [
        "Elements combined",
        "Control updated",
        "Control",
        "Elements",
        "Elements master",
        "Txt",
    ]
    export_dfs_to_excel(dfs, sheet_names, _learn_xl_output)

    # Control layout for new slides
    template_for_new_slides = _elements_combined[
        ["master_name", "layout_name", "element_name", "shape_index", "text"]
    ].copy()
    template_for_new_slides["chart_hash"] = "."
    template_for_new_slides["chart_data"] = "."
    template_for_new_slides["chart_data_dict"] = "."
    template_for_new_slides["image_link"] = "."
    template_for_new_slides["run"] = "1"
    template_for_new_slides["slide_hash"] = "."
    template_for_new_slides["py_override"] = "."
    template_for_new_slides["to_slide"] = _elements_combined["slide_number"]
    # template_for_new_slides[template_for_new_slides['to_slide'] == 5]
    template_for_new_slides = template_for_new_slides.sort_values(
        by=["master_name", "layout_name", "shape_index"], ascending=[True, True, False]
    )

    # Updated control file
    _control = pd.merge(
        _control,
        _elements_combined[
            [
                "master_name",
                "layout_name",
                "element_name",
                "slide_number",
                "shape_id",
                "element_name_slide",
            ]
        ].rename(columns={"slide_number": "to_slide"}),
        how="left",
    )
    _control["shape_id"] = _control["shape_id"].astype("Int64")

    close_powerpoint_excel()

    return _control, _elements_combined


def ppt_theme(_colors_file, universal_chart_elements, Theme=None, Override=None):
    df = pd.read_excel(_colors_file, sheet_name="ppt_theme")
    if Theme:
        df = df[df["Theme"] == Theme].reset_index()
        df["color_rgb_formatted"] = (
            df["color_rgb"].astype(str).apply(lambda x: f"RGB({x.replace(',', ', ')})")
        )
        slide_master_text_elements = dict(zip(df["Element"], df["color_rgb_formatted"]))
    elif "ao_slides_cool" in df["Theme"].unique():
        df = df[df["Theme"] == "ao_slides_cool"].reset_index()
        df["color_rgb_formatted"] = (
            df["color_rgb"].astype(str).apply(lambda x: f"RGB({x.replace(',', ', ')})")
        )
        slide_master_text_elements = dict(zip(df["Element"], df["color_rgb_formatted"]))
    else:
        print("WARNING: No theme file found, switching to last known defaults.")
        slide_master_text_elements = {
            "slide_header": "RGB(255, 255, 255)",  # Keeping white as requested
            "title": "RGB(0, 32, 96)",  # Slightly adjusted deep navy
            "subtitle": "RGB(37, 64, 143)",  # Refined medium blue
            "subtitle_desc": "RGB(37, 64, 143)",  # Matching medium blue
            "subtitle_1": "RGB(37, 64, 143)",  # Matching medium blue
            "subtitle_desc_1": "RGB(37, 64, 143)",  # Matching medium blue
            "subtitle_2": "RGB(37, 64, 143)",  # Matching medium blue
            "subtitle_desc_2": "RGB(37, 64, 143)",  # Matching medium blue
            "line": "RGB(0, 32, 96)",  # Matching the title
            "line_1": "RGB(0, 32, 96)",  # Matching the title
            "line_2": "RGB(0, 32, 96)",  # Matching the title
            "footnote": "RGB(102, 102, 127)",  # Blue-tinted gray
            "slide_nbr": "RGB(102, 102, 127)",  # Matching footnote color
        }

    if Override:
        slide_master_text_elements = adjust_colors(
            universal_chart_elements, slide_master_text_elements
        )

    return slide_master_text_elements


def python_override(
    _control,
    scan_python_functions_from_file_s,
    _visual_library_dir,
    _learn_dir,
    _chart_data_dir,
    _image_dir,
    _colors_file,
):
    print("NOTE: Normal run.")
    ## Modify for same slide same template issue
    _control["row_number"] = range(len(_control))
    _control["row_number"] = (
        _control["row_number"].astype(str) + "_" + _control["to_slide"].astype(str)
    )
    _control["text"] = _control["text"].str.replace(r"_x000B_", r"\n")

    ## Provision to run python code as an override on the primarily vba based process
    df_py_override = _control[_control["py_override"] == 1]

    if len(df_py_override) > 0:
        scan_python_functions_from_file_s(
            _source=str(_visual_library_dir),
            _destination=str(_learn_dir),
            _load_functions=1,
            _write_to_mkdocs=0,
        )

        # Run .py and load chart references into control
        for _, row in df_py_override.iterrows():
            chart_hash = row["chart_hash"]
            row_number = row["row_number"]
            # print(row)
            print(f"REPORT: Running python override on {row_number}")
            if (chart_hash == ".") | (chart_hash == ""):
                print("WARNING: Please provide a chart hash value from Visual library.")
            else:
                chart_dict_str = row["chart_data_dict"]
                if isinstance(chart_dict_str, dict):
                    chart_data_dict = chart_dict_str
                else:
                    chart_data_dict = ast.literal_eval(chart_dict_str)

            chart_data_dict["chart_out"] = os.path.join(
                _chart_data_dir, _image_dir, row_number
            )

            # Read data from chart_data file
            if _chart_data_dir:
                chart_data_path = os.path.join(_chart_data_dir, row["chart_data"])
            else:
                chart_data_path = ""
            if chart_data_path.endswith(".csv"):
                print(f"READING: {chart_data_path}")
                current_df = pd.read_csv(chart_data_path)
                current_df = pass_dict_to_transform(current_df, chart_data_dict)
                current_df = transform_data_batch_v1(current_df, _colors_file)

            # Run function with parameters
            run_dynamic_function(chart_hash, chart_data_dict, current_df)
            print(
                f"REPORT: .py override successful, if necessary use  help({chart_hash})  to calibrate output"
            )

            # Override image_link
            _control["image_link"] = np.where(
                (_control["row_number"] == row_number),
                f"{row_number}.png",
                _control["image_link"],
            )
            _control["chart_hash"] = np.where(
                (_control["row_number"] == row_number), ".", _control["chart_hash"]
            )
            _control["chart_data"] = np.where(
                (_control["row_number"] == row_number), ".", _control["chart_data"]
            )
            _control["chart_data_dict"] = np.where(
                (_control["row_number"] == row_number),
                ".",
                _control["chart_data_dict"],
            )

    close_powerpoint_excel()

    return _control


def run_dynamic_function(function_name, params_dict, df, globals_dict=None):
    """
    Dynamically calls a function by its string name with parameters from a dictionary.
    Automatically maps dictionary keys to function parameters when they match.

    Parameters:
    function_name (str): Name of the function to call
    params_dict (dict): Dictionary containing parameters that might match function parameters
    df (DataFrame): The dataframe to pass to the function
    globals_dict (dict, optional): Dictionary of global variables where the function is defined
                                   If None, uses the global namespace

    Returns:
    The result of calling the function with the provided parameters
    """
    if globals_dict is None:
        globals_dict = globals()

    # Get the actual function object from its name
    if function_name in globals_dict:
        func = globals_dict[function_name]
    else:
        raise ValueError(
            f"Function '{function_name}' not found in the provided namespace."
        )

    # Get the function's parameters using inspect
    import inspect

    sig = inspect.signature(func)
    param_names = list(sig.parameters.keys())

    # Create a dictionary of arguments to pass to the function
    kwargs = {"df": df}  # Always pass df

    # Map matching parameters from the dictionary
    for param_name in param_names:
        if (
            param_name in params_dict and param_name != "df"
        ):  # Skip 'df' as we're handling it separately
            kwargs[param_name] = params_dict[param_name]

    # Call the function with the matched parameters
    return func(**kwargs)


def transform_data(df, x=None, y=None, z=None, value=None, y_override=None):
    """
    Transforms the input DataFrame by creating a structured output with 'x', 'y', 'z', and 'value' columns.

    Parameters:
        df (pd.DataFrame): Input DataFrame
        x (list or str, optional): Column(s) to use as 'x' in output
        y (list or str, optional): Column(s) whose values will be placed in 'y' column
        z (list or str, optional): Additional column(s) to retain in the output
        value (list or str, optional): Column(s) whose values should be used as 'value' in output
        y_override (str, optional): Override value for column 'y'. If specified, this will be used instead of the actual values.

    Returns:
        pd.DataFrame: Transformed DataFrame with columns named 'x', 'y', 'z', and 'value'
    """
    try:
        # Convert string parameters to lists for consistency
        x = [x] if isinstance(x, str) else x
        y = [y] if isinstance(y, str) else y
        z = [z] if isinstance(z, str) and z is not None else z
        value = [value] if isinstance(value, str) and value is not None else value

        # Ensure required parameters are provided
        if x is None or y is None:
            raise ValueError("Parameters 'x' and 'y' must be specified.")

        # Check if all specified columns exist in df
        all_columns = x + y + (z if z else []) + (value if value else [])
        missing_columns = [col for col in all_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(
                f"Error: The following columns are not found in the provided DataFrame: {missing_columns}. Please check for typos or missing data."
            )

        # Make a copy of the input DataFrame to avoid modifying the original
        working_df = df.copy()

        # Case 1: Single y column and value is specified
        if len(y) == 1 and value:
            result_df = working_df[x + y + (z if z else []) + value].copy()
            result_df = result_df.rename(
                columns={x[0]: "x", y[0]: "y", value[0]: "value"}
            )

        # Case 2: Multiple y columns and value is specified
        elif len(y) > 1 and value:
            # For multiple y columns, create separate rows for each
            rows_list = []

            for y_col in y:
                temp_df = working_df[x + [y_col] + (z if z else []) + value].copy()
                temp_df = temp_df.rename(
                    columns={x[0]: "x", y_col: "y", value[0]: "value"}
                )
                rows_list.append(temp_df)

            result_df = pd.concat(rows_list, ignore_index=True)

        # Case 3: Single y column and no value specified (use y values as value)
        elif len(y) == 1 and not value:
            result_df = working_df[x + (z if z else [])].copy()
            result_df = result_df.rename(columns={x[0]: "x"})
            result_df["y"] = y[0]  # Use column name as label
            result_df["value"] = working_df[y[0]]  # Use column values as value

        # Case 4: Multiple y columns and no value specified (melt)
        else:
            result_df = working_df.melt(
                id_vars=x + (z if z else []),
                value_vars=y,
                var_name="y",
                value_name="value",
            )
            result_df = result_df.rename(columns={x[0]: "x"})

        # Handle y override
        if y_override:
            if not isinstance(y_override, dict):
                raise ValueError(
                    "y_override must be a dictionary mapping original 'y' values to new values."
                )
            # Replace 'y' column values based on the dictionary
            result_df["y"] = result_df["y"].map(y_override).fillna(result_df["y"])

        # Handle z column(s) renaming
        if z:
            if len(z) == 1:
                result_df = result_df.rename(columns={z[0]: "z"})
            else:
                for i, col in enumerate(z):
                    result_df = result_df.rename(columns={col: f"z{i + 1}"})

        # Create list of columns for output
        z_cols = (
            ["z"]
            if z and len(z) == 1
            else [f"z{i + 1}" for i in range(len(z) if z else 0)]
        )
        output_columns = ["x", "y"] + z_cols + ["value"]

        # Ensure all requested output columns exist
        existing_columns = [col for col in output_columns if col in result_df.columns]

        return result_df[existing_columns]

    except Exception as e:
        print(f"An error occurred:\n{e}")
        return None


def transform_data_batch_v1(df, _colors_file, y_override_col=None):
    """Transpose data to universal xyzv data structure."""
    _ct_calc, _ct_default = determine_columns(df, override=y_override_col)

    # Treat color file
    df_colors = pd.read_excel(_colors_file, sheet_name="colors")
    df_colors = df_colors.sort_values(by=["Mode", "Tool", "Usage"]).reset_index(
        drop=True
    )
    df_colors = fill_missing_colors(df_colors)
    df_colors.columns = df_colors.columns.str.lower()
    _colors = df_colors.rename(columns={"usage": "y"})[["y", "color_hex", "color_rgb"]]

    df = clean_merge(df, _colors, df1_join_col=_ct_calc).reset_index(drop=True)

    print("Report: Data transposed")
    df.head()

    return df


def transform_data_batch(df, _colors, y_override_col=None, y_override_color=None):
    """Apply colors and exceptions. Using default 'y' column for now."""
    _ct_calc, _ct_default = determine_columns(df, override=y_override_col)

    # Apply color overrides if provided
    if y_override_color is not None:
        for y_value, hex_color in y_override_color.items():
            # Update color_hex for matching y values
            mask = _colors["y"] == y_value
            _colors.loc[mask, "color_hex"] = hex_color

            # Convert hex to RGB if needed (assuming you have a function for this)
            # If you don't have a hex_to_rgb function, you can add one or remove this line
            try:
                # Simple hex to RGB conversion
                hex_color = hex_color.lstrip("#")
                rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
                rgb_string = f"{rgb[0]}, {rgb[1]}, {rgb[2]}"
                _colors.loc[mask, "color_rgb"] = rgb_string
            except ValueError:
                # If hex conversion fails, keep original RGB value
                pass

    df = clean_merge(df, _colors, df1_join_col=_ct_calc, how="left").reset_index(
        drop=True
    )

    if _ct_default == "y":
        pass
    else:
        print(f"Reference: Auto color column is {_ct_calc}.")

    print("Report: Data transposed")
    # df.head()

    return df

