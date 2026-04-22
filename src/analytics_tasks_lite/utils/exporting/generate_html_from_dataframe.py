def generate_html_with_color_and_copy(hex_color):
    html_copy_button = f'<button onclick="copyToClipboard(\'{hex_color}\')" style="width: 60px; height: 20px; background-color: {hex_color}; border: none;"></button>'
    return f"<div>{html_copy_button}</div>"


def generate_html_from_dataframe(df, color_column_name):
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Colors.py scan</title>
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

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text)
                .then(() => {
                    console.log('Copied to clipboard');
                    showNotification('Copied: ' + text);
                })
                .catch(err => {
                    console.error('Error copying to clipboard:', err);
                });
        }

        function showNotification(message) {
            var notification = document.createElement('div');
            notification.textContent = message;
            notification.style.position = 'fixed';
            notification.style.top = '20px';
            notification.style.left = '50%';
            notification.style.transform = 'translateX(-50%)';
            notification.style.background = '#d95f0e';
            notification.style.padding = '10px';
            notification.style.border = '1px solid #ccc';
            notification.style.borderRadius = '5px';
            notification.style.boxShadow = '0 0 10px rgba(0,0,0,0.1)';
            notification.style.zIndex = '9999';
            document.body.appendChild(notification);
            setTimeout(function() {
                document.body.removeChild(notification);
            }, 3000); // Remove notification after 3 seconds
        }
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
    html_content += "                    <th>Display color</th>\n"
    html_content += "                </tr>\n"
    html_content += "            </thead>\n"
    html_content += "            <tbody>\n"

    # Iterate over DataFrame rows
    for _, row in df.iterrows():
        html_content += "                <tr>\n"
        for col in df.columns:
            html_content += f"                    <td>{row[col]}</td>\n"
        html_content += f'                    <td class="color-cell">{generate_html_with_color_and_copy(row[color_column_name])}</td>\n'
        html_content += "                </tr>\n"

    html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

    return html_content

