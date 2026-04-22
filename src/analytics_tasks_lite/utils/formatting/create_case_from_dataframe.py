import pandas as pd

def create_case_from_dataframe(df, code_columns='ORC_NAME', condition_columns='Condition',
    output_columns='Condition_Category', else_value='Other'):
    """
    Generate SQL CASE statement from a DataFrame.
    
    Parameters:
    - df: pandas DataFrame with code and condition columns
    - code_columns: column name containing the codes
    - condition_columns: column name containing the condition names
    - output_columns: the name for the resulting column (alias)
    - else_values: default value for unmatched cases
    
    Returns:
    - SQL CASE statement as string
    """
    
    # Group codes by condition
    grouped = df.groupby(condition_columns)[code_columns].apply(list).to_dict()
    
    case_lines = ["CASE"]
    
    for condition, codes in grouped.items():
        codes_str = ", ".join(["{code}" for code in codes])
        case_lines.append(f"WHEN {code_columns} IN ({codes_str}) THEN '{condition}'")
    
    if else_value:
        case_lines.append(f"    ELSE '{else_value}'")
    
    case_lines.append(f"END AS {output_columns}")
    
    return "\n".join(case_lines)

data=pd.read_clipboard()

# df = pd.DataFrame(data)
""" Name DIAG_CD
Alzheimer    g30
Alzheimer    g300
Alzheimer    g301
Alzheimer    g308 """
sql_case = generate_case_from_dataframe(data, code_column='DIAG_CD', condition_column='ZS ORC Name')
print(sql_case)