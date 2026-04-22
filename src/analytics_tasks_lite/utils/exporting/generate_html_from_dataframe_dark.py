def generate_html_with_color_and_copy_dark(hex_color):
    html_copy_button = f'<button onclick="copyToClipboard(\'{hex_color}\')" style="width: 60px; height: 20px; background-color: {hex_color}; border: none;"></button>'
    return f"<div>{html_copy_button}</div>"


def generate_html_from_dataframe_dark(df, color_column_name):
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
        /* Light mode styles */
        body {
            background-color: white;  /* Background outside the table */
            color: black;
        }

        table {
            background-color: white;
            color: black;
        }

        th, td {
            border: 1px solid #ddd;
            background-color: white;
            color: black;
        }

        /* Dark mode styles */
        @media (prefers-color-scheme: dark) {
            body {
                background-color: #1e2129;  /* Dark mode background outside the table */
                color: #e0e0e0;
            }

            /* Optional: you can also target the container specifically if you want */
            .container {
                background-color: #1e2129; /* Dark mode container background */
            }

            /* Table styles in dark mode */
            table, .dataTables_wrapper {
                background-color: #333 !important;
                color: bdbdbd !important;
            }

            th, td {
                border-color: #555;
                background-color: #444 !important; /* Ensure all table cells have dark background */
                color: #bdbdbd !important; /* Ensure all text in table is white */
            }

            /* DataTable plugin-specific styles */
            .dataTables_wrapper .dataTables_paginate .paginate_button {
                background-color: #444 !important; /* Dark background for pagination buttons */
                color: bdbdbd !important; /* White text on pagination buttons */
            }

            .dataTables_wrapper .dataTables_filter input,
            .dataTables_wrapper .dataTables_length select,
            .dataTables_wrapper .dataTables_info {
                background-color: #444 !important; /* Dark background for inputs and dropdowns */
                color: white !important; /* White text for input fields */
            }

            /* Change hover effect in dark mode */
            tr:hover {
                background-color: #636363 !important;
            }

            /* Fix for "Show entries" and "Search" labels */
            .dataTables_wrapper .dataTables_length label,
            .dataTables_wrapper .dataTables_filter label {
                color: #bdbdbd !important; /* Ensure labels like "Show entries" and "Search" are white */
            }
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
        html_content += f'                    <td class="color-cell">{generate_html_with_color_and_copy_dark(row[color_column_name])}</td>\n'
        html_content += "                </tr>\n"

    html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

    return html_content
