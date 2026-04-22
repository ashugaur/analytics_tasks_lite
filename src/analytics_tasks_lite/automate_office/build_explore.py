import sys
import os
import shutil
import pandas as pd
import importlib.resources as pkg_resources
from pathlib import Path
from datetime import datetime, timezone
import psutil
import win32com.client
import re
from analytics_tasks.automate_office.build_batch import (
    transform_data,
    determine_columns,
    clean_merge,
    my_colors,
)
from analytics_tasks.utils.scanning import scan_dir
from analytics_tasks.utils.imputing import fill_missing_colors
from analytics_tasks.utils.os_functions import open_file_folder, copy_folders_no_overwrite

folder_dt = datetime.now(timezone.utc).strftime("%Y%m%d")
file_dt = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def initialize_explore_globals(at_dir):
    """Initialize global variables in the calling module"""
    # Get the calling module's globals
    caller_globals = sys._getframe(1).f_globals

    # Get the results
    results = lib_refs_ao_explore(at_dir, report_name="explore")
    var_names = [
        "_colors_file",
        "_xlsm_path",
        "_logs_dir",
        "_input_dir",
        "_learn_dir",
        "_output_pptm",
        "_control_file",
        "_control_file_worksheet",
        "_explore_dir",
        "_template_path",
        "_input_img_dir",
        "_input_data_dir",
        "_vl",
        "_visual_library_file",
        "_automate_office_dir",
        "_input_template_dir",
    ]

    # Set variables in caller's global scope
    for name, value in zip(var_names, results):
        caller_globals[name] = value


def lib_refs_ao_explore(at_dir, report_name=None):
    """Assigns working libraries inside visual_library dir."""
    _automate_office_dir = at_dir / "automate_office"
    _vl = at_dir / "visual_library"
    _visual_library_file = at_dir / "visual_library/visual_library.html"
    _input_dir = _automate_office_dir / "input"
    _input_data_dir = _automate_office_dir / "input/data"
    _input_img_dir = _automate_office_dir / "input/img"
    _input_template_dir = _automate_office_dir / "input/templates"
    _learn_dir = _automate_office_dir / "output/learn"
    _logs_dir = _automate_office_dir / "output/log"
    _explore_dir = _automate_office_dir / "output/explore"

    result = copy_input_folder(_automate_office_dir)
    # print(f"☑️  Input copied to: {result}")

    _control_file = _automate_office_dir / "input/____control.xlsm"
    _control_file_worksheet = "calibration"

    _colors_file = _vl / "____settings/colors.xlsm"

    _template_path = _automate_office_dir / "input/templates/template_v1.potm"
    if report_name:
        _output_pptm = _automate_office_dir / rf"/output/{report_name}__{file_dt}.pptm"
    else:
        _output_pptm = _automate_office_dir / rf"/output/report__{file_dt}.pptm"
    _xlsm_path = (
        _automate_office_dir
        / rf"output/explore/{(Path(_output_pptm).name).rsplit('.')[0]}.xlsm"
    )

    Path(_automate_office_dir).mkdir(parents=True, exist_ok=True)
    Path(_vl).mkdir(parents=True, exist_ok=True)
    Path(_input_dir).mkdir(parents=True, exist_ok=True)
    Path(_input_data_dir).mkdir(parents=True, exist_ok=True)
    Path(_input_img_dir).mkdir(parents=True, exist_ok=True)
    Path(_input_template_dir).mkdir(parents=True, exist_ok=True)
    Path(_learn_dir).mkdir(parents=True, exist_ok=True)
    Path(_logs_dir).mkdir(parents=True, exist_ok=True)
    Path(_explore_dir).mkdir(parents=True, exist_ok=True)

    print("✅ Assigned automate office directories.")

    return (
        _colors_file,
        _xlsm_path,
        _logs_dir,
        _input_dir,
        _learn_dir,
        _output_pptm,
        _control_file,
        _control_file_worksheet,
        _explore_dir,
        _template_path,
        _input_img_dir,
        _input_data_dir,
        _vl,
        _visual_library_file,
        _automate_office_dir,
        _input_template_dir,
    )


def load_macro_workbook(
    explore_folder,
    _control_file,
    _control_file_worksheet,
    visual_library_dir,
    _xlsm_path,
):
    _self_run = 1
    _latest_file = get_latest_file(explore_folder)
    if _latest_file == None:
        if (isinstance(_self_run, int)) & (_self_run == 1):
            _control = pd.read_excel(_control_file, sheet_name=_control_file_worksheet)
            # print("NOTE: Skipping .py override as not relevant in self run.")
        else:
            print("NOTE: Normal run.")

        # exec(open(_ao + r"\code\functions\create_macro_baseline_explore.py").read())
        scan = scan_dir(visual_library_dir, ".bas")

        if len(scan) <= 1:
            print(
                "❌ Check if visual library exists, if not run: examples\\vl.py"
            )
        else:
            ## Filter
            scan = scan[~scan["unc"].str.contains("____archive")].reset_index(drop=True)
            scan = scan[~scan["unc"].str.contains("____diagrams_custom")].reset_index(
                drop=True
            )
            scan = scan[~scan["unc"].str.contains("____settings")].reset_index(
                drop=True
            )
            scan = scan[~scan["unc"].str.contains("____uat")].reset_index(drop=True)

            process_vba_files_self(scan, _xlsm_path)

            open_file_folder(_xlsm_path)
    else:
        open_file_folder(_latest_file.replace("/", "\\"))


def close_powerpoint_excel():
    """Closes PowerPoint and Excel processes, even if they're stuck in the task manager."""

    processes_to_kill = ["POWERPNT.EXE", "EXCEL.EXE"]  # Process names

    for proc in psutil.process_iter():
        try:
            if proc.name().upper() in processes_to_kill:  # Case-insensitive comparison
                # print(f"Found process: {proc.name()} (PID: {proc.pid})")

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

                # print(f"Process {proc.pid} terminated.")

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass  # Process might have already terminated or we don't have access.  Ignore.
        except Exception as e:
            print(f"An unexpected error occurred: {e}")



def copy_input_folder(destination_path):
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
            raise FileNotFoundError(f"❌  Input folder not found at: {source_path}")

        if not source_path.is_dir():
            raise FileNotFoundError(
                f"❌  Input path exists but is not a directory: {source_path}"
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

        print(f"☑️  Successfully copied input folder to: {target_input_path}")
        return str(target_input_path)

    except Exception as e:
        print(f"❌  Error copying input folder: {e}")
        raise


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


def get_latest_file(directory):
    try:
        # Get a list of files with the prefix 'explore'
        files = [
            f
            for f in os.listdir(directory)
            if f.startswith("explore") and f.endswith(".xlsm")
        ]

        if not files:
            print("🚫 No files found with the prefix 'explore' and .xlsm extension.")
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


def process_vba_files_self(scan, _xlsm_path):
    """Main function to process VBA files and create a single XLSM file with multiple modules"""

    try:
        # Create Excel application object
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False

        # Create a new workbook only once
        workbook = excel.Workbooks.Add()

        # Loop through each row in the dataframe
        for index, row in scan.iterrows():
            unc_path = row["unc"]
            # chart_dict_str = row['chart_data_dict']
            to_slide_value = row["chart_hash"]

            # print(f"\nProcessing file: {unc_path}")

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

            # Create a unique module name using chart_hash value
            unique_module_name = f"{module_name}"
            # print(f"Module name will be: {unique_module_name}")

            # Step 2: Merge dictionaries
            # try:
            ## Parse the chart_data_dict from string to dictionary
            # if isinstance(chart_dict_str, dict):
            # chart_data_dict = chart_dict_str
            # else:
            # chart_data_dict = ast.literal_eval(chart_dict_str)
            ##chart_data_dict = json.loads(chart_dict_str)
            ##chart_data_dict = eval(chart_dict_str)
            ##chart_data_dict = parse_string(chart_dict_str)
            #
            ## Create merged dictionary
            # merged_dict = {**universal_chart_elements, **chart_data_dict}
            # print("Successfully merged dictionaries:")
            ##print(merged_dict)
            # except Exception as e:
            # print(f"Error merging dictionaries: {str(e)}")
            # continue

            # Step 3: Replace values in the VBA code
            # try:
            # modified_vba = replace_values_in_vba(vba_code, merged_dict)
            # print("Successfully modified VBA code")
            # except Exception as e:
            # print(f"Error replacing values in VBA code: {str(e)}")
            # continue

            # Step 4: Add the module to the workbook
            try:
                # Add a VBA module
                vb_comp = workbook.VBProject.VBComponents.Add(
                    1
                )  # 1 = vbext_ct_StdModule
                vb_comp.Name = unique_module_name
                vb_comp.CodeModule.AddFromString(vba_code)
                print(f"☑️  Successfully added module: {unique_module_name}")
            except Exception as e:
                print(f"❌  Error adding module to workbook: {str(e)}")
                continue

        # Save the workbook as XLSM after all modules have been added
        try:
            workbook.SaveAs(
                str(_xlsm_path), 52
            )  # 52 = xlOpenXMLWorkbookMacroEnabled (XLSM)
            print(f"✅ Successfully created XLSM file with all modules: {_xlsm_path}")
        except Exception as e:
            print(f"❌  Error saving XLSM file: {str(e)}")

    except Exception as e:
        print(f"❌  Unexpected error: {str(e)}")
    finally:
        # Clean up resources
        if "workbook" in locals():
            workbook.Close(SaveChanges=False)
        if "excel" in locals():
            excel.Quit()
            del excel


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


def pass_dict_to_transform_del(df, parameter_dict):
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

    # Call transform_data with the extracted parameters
    return transform_data(df, x=x_param, y=y_param, z=z_param, value=value_param)


def transform_data_explore_v1(df, _colors_file, override_xy=None):
    """Transpose data to universal xyzv data structure."""
    _ct_calc, _ct_default = determine_columns(df, override=override_xy)

    # Treat color file
    df_colors = pd.read_excel(_colors_file, sheet_name="colors")
    df_colors = df_colors.sort_values(by=["Mode", "Tool", "Usage"]).reset_index(
        drop=True
    )
    df_colors = fill_missing_colors(df_colors)
    df_colors.columns = df_colors.columns.str.lower()
    _colors = df_colors.rename(columns={"usage": "y"})[["y", "color_hex", "color_rgb"]]

    df = clean_merge(df, _colors, df1_join_col=_ct_calc).reset_index(drop=True)

    print(
        "\nReport: Transposed data copied to clipboard, paste it to report*.xlsm file and run relevant macro from visual library."
    )
    df.head()

    return df


def transform_data_explore_v1(
    df, _colors_file, y_override_col=None, y_override_color=None
):
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

    df = clean_merge(df, _colors, df1_join_col=_ct_calc).reset_index(drop=True)

    print(
        "\nReport: Transposed data copied to clipboard, paste it to report*.xlsm file and run relevant macro from visual library."
    )
    df.head()

    return df


def transform_data_explore(
    df, _colors_file, y_override_col=None, y_override_color=None
):
    """Transpose data to universal xyzv data structure."""
    _ct_calc, _ct_default = determine_columns(df, override=y_override_col)

    _colors = my_colors(_colors_file)

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

    df = clean_merge(df, _colors, df1_join_col=_ct_calc).reset_index(drop=True)

    print(
        "\nReport: Transposed data copied to clipboard, paste it to report*.xlsm file and run relevant macro from visual library."
    )
    df.head()

    return df
