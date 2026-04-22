# %% File search build

## Dependencies
from pathlib import Path
from analytics_tasks.utils import fakedatagenerator as fdg
from analytics_tasks.file_search.build import (
    lib_refs_fs,
    scan_directories_python,
    # scan_dir_powershell,
    scan_time_machine,
    scan_clean,
    scan_history,
    exceptions,
    apply_filters,
    scan_drives,
    export_index_files,
    ifp_optimized,
)
from analytics_tasks.utils.controlling import log_start, log_end

## Project folder (at_dir: analytics_tasks directoary)
at_dir = Path("C:/analytics_tasks")


## Assign file/folder references
_fs_index_dir, _logs_dir, _time_machine_path, _reports_dir = lib_refs_fs(at_dir)


## Logging
log_start(_logs_dir)


## Dictionary of list of file type to scan and index
scan_ext = {
    "txt": [".ps1", ".py", ".txt", ".R", ".sql", ".sas", ".rtf", ".md", ".yml", ".bas"],
    "docx": [".docx"],
    "pptx": [".pptx", ".pptm"],
    "ppt": [".ppt"],
    "msg": [".msg"],
    "eml": [".eml"],
    "epub": [".epub"],
    "pdf": [".pdf"],
    "excel": [".xls", ".xlsx", ".xlsm"],
}

## Size limit in MB for 'scan_ext' dictionary
scan_size = {
    "txt": [3],
    "docx": [500],
    "pptx": [500],
    "ppt": [50],
    "msg": [100],
    "eml": [100],
    "epub": [300],
    "pdf": [300],
    "excel": [0.010891],
}


## Generate fake data (Skip this step if working with real data)
""" 
generator = fdg.FakeDataGenerator()
generator.generate_all_files(
    xlsx_count=20,  # Number of Excel files (.xlsx)
    txt_count=20,  # Number of text files
    sql_count=50,  # Number of SQL files
    py_count=15,  # Number of Python files
    pptx_count=6,  # Number of PowerPoint files
    pdf_count=7,  # Number of PDF files
    max_rows=500,  # Maximum rows for Excel files
    max_lines=100,  # Maximum lines for text/SQL/Python files
    max_slides=7,  # Maximum slides for PowerPoint files
    max_pages=10,  # Maximum pages for PDF files
    output_dir=at_dir / "fake_data",  # Output directory
)
 """

## List folders to scan and index
scan_dirs = [at_dir / "fake_data", Path("C:/Unknown2049")]
scan_dirs


## Scan directories (Recommended for small file corpus and fast hard disk)
scan_directories_python(_fs_index_dir, scan_dirs)


## Scan directories (Recommended for large file corpus and slow hard disk)
# scan_dir_powershell(_fs_index_dir, scan_dirs)


## Time machine
scan_time_machine(_time_machine_path)


## Scan clean
scan0 = scan_clean(_fs_index_dir)


## Scan history
scan, scan_old, searchx_final_old = scan_history(scan0, _fs_index_dir)


## Exceptions
paths_to_exclude = [Path("C:/Unknown2049")]
scan, exception_file = exceptions(scan, paths_to_exclude)


## Apply filters
scan = apply_filters(scan, scan_ext, scan_size)


# Scan disk
scan_drives(scan, scan_ext)


## Index files creating an 'intermediate file pool'
searchx = ifp_optimized(scan0, searchx_final_old, scan_ext, scan_size)


## Export search index
export_index_files(_fs_index_dir, _time_machine_path, scan0, searchx)


# Close logging
log_end()
