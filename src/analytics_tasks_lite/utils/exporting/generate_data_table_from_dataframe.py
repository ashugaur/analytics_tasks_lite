def generate_data_table_from_dataframe(df):
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>DataFrame Table</title>
    <link href="../../assets/data_table/bootstrap.min.css" rel="stylesheet">
    <script src="../../assets/data_table/jquery.min.js"></script>
    <link rel="stylesheet" href="../../assets/data_table/jquery.dataTables.min.css">
    <script type="text/javascript" src="../../assets/data_table/jquery.dataTables.min.js"></script>
    <script type="text/javascript" src="../../assets/data_table/bootstrap.min.js"></script>
    <script>
        $(document).ready(function () {
            $('#myTable').dataTable({
                "pageLength": 100 /*load number of rows*/
            });
        });
    </script>
    <style>
        body {
            margin: 0;
            padding: 0;
            /*background-color: transparent;*/ /* Set background color to transparent */
        }
        h1 {
            /* text-align: center; */
            margin-top: 20px;
        }
        table {
            width: 70%;
            margin: 20px auto;
            border-collapse: collapse;
        }
        th, td {
            padding: 8px;
            /* text-align: center; */
            border: 1px solid #ddd;
        }
        th {
            vertical-align: middle;
        }
        .color-cell {
            width: 100px;
            /* text-align: center; */
        }
        button {
            padding: 0;
            line-height: 0;
        }
    </style>
</head>
<body style="margin:20px auto">
    <div class="container">
        <h1 style="padding:0; margin-top:0px"></h1>
        <table id="myTable" class="table table-striped">
            <thead>
                <tr>
"""

    # Add table headers dynamically
    for col in df.columns:
        html_content += f"                    <th>{col}</th>\n"
    html_content += "                </tr>\n"
    html_content += "            </thead>\n"
    html_content += "            <tbody>\n"

    # Iterate over DataFrame rows
    for _, row in df.iterrows():
        html_content += "                <tr>\n"
        for col in df.columns:
            html_content += f"                    <td>{row[col]}</td>\n"
        html_content += "                </tr>\n"

    html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

    return html_content
