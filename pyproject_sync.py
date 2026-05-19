import os
import ast
from pathlib import Path
import importlib.metadata
import re
import warnings
from stdlibs import stdlib_module_names

# --- CONFIGURATION ---
PACKAGE_DIR = Path("C:/my_disk/projects/analytics_tasks_lite")  
TOML_PATH = Path("C:/my_disk/projects/analytics_tasks_lite/pyproject.toml")
# ---------------------

def get_imported_modules(package_path):
    """Scans all .py files in the package to find imports, safely skipping errors."""
    imports = set()
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        
        for root, _, files in os.walk(package_path):
            for file in files:
                # Ignore this script tool and environment directory fragments if any
                if file.endswith(".py") and file != "sync_toml.py" and ".venv" not in root:
                    file_path = Path(root) / file
                    try:
                        tree = ast.parse(file_path.read_text(encoding="utf-8"))
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    imports.add(alias.name.split('.')[0])
                            elif isinstance(node, ast.ImportFrom):
                                if node.level == 0 and node.module:
                                    imports.add(node.module.split('.')[0])
                    except Exception:
                        # Safely alert and skip files with unparseable broken syntax or experimental drafts
                        print(f"Note: Skipped parsing file due to script syntax error: {file}")
                        
    builtins = stdlib_module_names()
    local_pkg_name = package_path.name.lower()
    
    return {imp.lower() for imp in imports if imp not in builtins and imp.lower() != local_pkg_name}

def map_import_to_package_name(import_names):
    """Maps import names to PyPI package names using environment distribution data."""
    mapping = {}
    for dist in importlib.metadata.distributions():
        pkg_name = dist.metadata["Name"]
        try:
            top_level = dist.read_text('top_level.txt')
            if top_level:
                for line in top_level.splitlines():
                    if line.strip().lower() in import_names:
                        mapping[line.strip().lower()] = pkg_name.lower()
        except Exception:
            continue
                    
    fallbacks = {
        "bs4": "beautifulsoup4",
        "docx": "python-docx",
        "pptx": "python-pptx",
        "yaml": "pyyaml",
    }
    
    final_pypi_names = set()
    for imp in import_names:
        if imp in mapping:
            final_pypi_names.add(mapping[imp])
        elif imp in fallbacks:
            final_pypi_names.add(fallbacks[imp])
        else:
            final_pypi_names.add(imp)
            
    return final_pypi_names

def sync_code_and_venv_to_toml():
    if not TOML_PATH.exists():
        print(f"Error: Target TOML file not found at '{TOML_PATH}'.")
        return
    if not PACKAGE_DIR.exists():
        print(f"Error: Package directory '{PACKAGE_DIR}' not found.")
        return

    # 1. Gather active venv state
    installed_packages = {
        dist.metadata["Name"].lower(): dist.version 
        for dist in importlib.metadata.distributions()
    }

    # 2. Analyze source code imports
    print(f"Analyzing source code in '{PACKAGE_DIR}' for imports...")
    detected_imports = get_imported_modules(PACKAGE_DIR)
    core_pypi_needed = map_import_to_package_name(detected_imports)
    
    # 3. Read TOML lines and find target lists using flexible Regex matching
    lines = TOML_PATH.read_text(encoding="utf-8").splitlines()
    core_start = core_end = dev_start = dev_end = -1
    in_dev_block = False

    for i, line in enumerate(lines):
        if re.search(r'dependencies\s*=\s*\[', line) and not in_dev_block:
            core_start = i
        if core_start != -1 and core_end == -1 and "]" in line and i > core_start:
            core_end = i
            
        if "[project.optional-dependencies]" in line:
            in_dev_block = True
            
        if in_dev_block and re.search(r'dev\s*=\s*\[', line):
            dev_start = i
        if dev_start != -1 and dev_end == -1 and "]" in line and i > dev_start:
            dev_end = i
            in_dev_block = False

    if core_start == -1 or dev_start == -1:
        print("\n[Error]: Could not match target array structures inside your pyproject.toml.")
        print("Please check that your file explicitly ends with:")
        print('[project.optional-dependencies]')
        print('dev = []\n')
        return

    # 4. Generate clean array inputs
    new_core_lines = []
    new_dev_lines = []

    for pkg_name in sorted(installed_packages.keys()):
        if pkg_name in ["setuptools", "wheel", "pip", "stdlibs"]:
            continue
            
        version = installed_packages[pkg_name]
        entry_string = f'    "{pkg_name}>={version}",'

        if pkg_name in core_pypi_needed:
            new_core_lines.append(entry_string)
        else:
            new_dev_lines.append(entry_string)

    # 5. Reconstruct the target configuration file
    output_lines = []
    output_lines.extend(lines[:core_start + 1])
    output_lines.extend(new_core_lines)
    output_lines.extend(lines[core_end:dev_start + 1])
    output_lines.extend(new_dev_lines)
    output_lines.extend(lines[dev_end:])

    # 6. Save modifications back to the real pyproject.toml
    TOML_PATH.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    print(f"\n🚀 Sync complete!")
    print(f" -> Core dependencies: {len(new_core_lines)} packages synchronized based on code imports.")
    print(f" -> Dev/Workspace tools: {len(new_dev_lines)} remaining venv packages mapped safely.")

if __name__ == "__main__":
    sync_code_and_venv_to_toml()