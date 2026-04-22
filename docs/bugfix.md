---
title: Bugfix
hide:
    - navigation
    # - toc
    # - footer
---




# Bugfix



## Automate office

### _template_path not found

??? bug-outline "Error & Solution"

    ```.py title="Problem: ApplyTemplate"
    *Error comes after running this line
    _control, _template_path = execute_pptx_pipeline(
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
    )


    *Error Message: 
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "C:\Users\user\AppData\Local\Programs\Python\Python311\Lib\site-packages\analytics_tasks\automate_office\build_batch.py", line 223, in execute_pptx_pipeline
        create_or_apply_potm(_template_pathx, outputpptm, _control)
      File "C:\Users\user\AppData\Local\Programs\Python\Python311\Lib\site-packages\analytics_tasks\automate_office\build_batch.py", line 1508, in create_or_apply_potm
        ppt.ApplyTemplate(_template_path)
      File "C:\Users\user\AppData\Local\Temp\gen_py\3.11\91493440-5A91-11CF-8700-00AA0060263Bx0x2x12\_Presentation.py", line 50, in ApplyTemplate
        return self.oleobj.InvokeTypes(2007, LCID, 1, (24, 0), ((8, 1),),FileName
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    pywintypes.com_error: (-2147352567, 'Exception occurred.', (0, 'Microsoft PowerPoint', 'Presentation.ApplyTemplate : Object does not exist.', '', 0, -2147188720), None)


    *Solution: Complete win32 postinstall
    cd C:\Users\user\AppData\Local\Programs\Python\Python311
    python Scripts/pywin32_postinstall.py -install


    *Powershell message postinstall
    Parsed arguments are: Namespace(install=True, remove=False, wait=None, silent=False, quiet=False, destination='C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages')
    Copied pythoncom311.dll to C:\Users\user\AppData\Local\Programs\Python\Python311\pythoncom311.dll
    Copied pywintypes311.dll to C:\Users\user\AppData\Local\Programs\Python\Python311\pywintypes311.dll
    You do not have the permissions to install COM objects.
    The sample COM objects were not registered.
    -> Software\Python\PythonCore\3.11\Help[None]=None
    -> Software\Python\PythonCore\3.11\Help\Pythonwin Reference[None]='C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages\\PyWin32.chm' 
    Registered help file
    Pythonwin has been registered in context menu
    Creating directory C:\Users\user\AppData\Local\Programs\Python\Python311\Lib\site-packages\win32com\gen_py
    Shortcut for Pythonwin created
    Shortcut to documentation created
    The pywin32 extensions were successfully installed.
    ```




## File search

### File search xlrd issue

??? bug-outline "Error & Solution"

    ```.py title="Problem: xlrd not installed"
    *Error comes after running this line
    scan_drives(scan, scan_ext)

    *Error message
    c:\time_series\example\exponantial_smoothing.xls
    2025-06-24 19:57:04,540 | [INFO] | user | ERROR: function load_ifp_xlsx... cannot read file c:\time_series\example\exponantial_smoothing.xls
    2025-06-24 19:57:04,540 | [INFO] | user | Error details: openpyxl does not support the old .xls file format, please use xlrd to read this file, or convert it to the more recent .xlsx file format.

    *Solution
    uv pip install --system xlrd
    ```
