# %% line_multi_xstr_ypct

## About
"""
transform_data(df, x=['days_on_therapy'], y=['brand'], value=['value'])

brand 	value	days_on_therapy
Drug A	1.0  	Day 0          
Drug A	0.9  	Day 30         
Drug A	0.77 	Day 60         
Drug A	0.64 	Day 90         
Drug A	0.51 	Day 120        
"""


## Simulated staytime data

import math
import numpy as np
import pandas as pd
import subprocess as sp
from itertools import product
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def generate_simulated_data(brand_list,
                          period_flag_list,
                          date_range_list,
                          grace_list,
                          cohort_list,
                          num_months=13):
    """
    Generate a simulated dataset with specified conditions.

    Parameters:
    brand_list (list): List of brand names
    period_flag_list (list): List of period flags
    date_range_list (list): List of date ranges
    grace_list (list): List of grace period values
    cohort_list (list): List of cohort values
    num_months (int): Number of months to generate (default 13 for 0 to 360 by 30)

    Returns:
    pandas.DataFrame: Simulated dataset with specified columns and conditions
    """
    # Generate all combinations of grouping columns
    combinations = list(product(brand_list, period_flag_list, date_range_list,
                              grace_list, cohort_list))

    # Generate month_date sequence
    month_dates = [i * 30 for i in range(num_months)]

    # Create empty lists to store the data
    data = []

    # Generate data for each combination
    for brand, period_flag, date_range, grace, cohort in combinations:
        # Generate decreasing values starting from 1
        # Using random decrease between 5% to 25% for each step
        values = [1.0]  # Start with 1
        for _ in range(len(month_dates) - 1):
            decrease = np.random.uniform(0.05, 0.25)  # Random decrease between 5-25%
            next_value = max(0, values[-1] * (1 - decrease))  # Ensure value doesn't go below 0
            values.append(round(next_value, 2))

        # Create rows for this combination
        for month_date, value in zip(month_dates, values):
            # Format month_date with T prefix and padding
            formatted_month_date = f"T{str(month_date).zfill(4)}"
            # Format days_on_therapy
            days_on_therapy = f"Day {month_date}"

            data.append({
                'cohort': cohort,
                'grace': grace,
                'brand': brand,
                'period_flag': period_flag,
                'date_range': date_range,
                'month_date': formatted_month_date,
                'value': value,
                'days_on_therapy': days_on_therapy
            })

    # Create DataFrame
    df = pd.DataFrame(data)

    # Sort the DataFrame by all grouping columns and month_date
    df = df.sort_values(['brand', 'period_flag', 'date_range', 'grace', 'cohort', 'month_date'])

    return df

# Define the lists for grouping columns - now outside the function
brand_list = ['Drug A', 'Drug B', 'Drug C']
period_flag_list = ['12mnth']
date_range_list = ['jan to feb 2025']
grace_list = [60]  # New list for grace periods
cohort_list = ['Q1 2020']  # New list for cohorts

df = generate_simulated_data(brand_list,
                          period_flag_list,
                          date_range_list,
                          grace_list,
                          cohort_list,
                          num_months=13)

#df.to_clipboard()
#df.head(5).to_clipboard()
#df.to_csv(_vl+r'\charts\change\xyv_multiline.csv', index=False)


# %% Transform data

exec(open(_exploratory+r"\transpose\pandas\transform_data.py").read())
df = transform_data(df, x=['days_on_therapy'], y=['brand'], value=['value'])


# %% Color

exec(open(_exploratory+r"\format\pandas\hex_to_rgb_fill_missing_colors.py").read())
df_colors = pd.read_excel(_edupunk_docs+r"\tables\mkdocs.xlsx", sheet_name='colors')
df_colors = df_colors.sort_values(by=['Mode', 'Tool', 'Usage']).reset_index(drop=True)
df_colors = fill_missing_colors(df_colors)
df_colors.columns = df_colors.columns.str.lower()

df = pd.merge(df, df_colors[['usage', 'color_hex', 'color_rgb']], left_on='y', right_on='usage', how='left')
del df['usage']


# %% Plot

# Create the plot
plt.figure()

# Create color mapping
color_map = dict(zip(df['y'].unique(), df['color_hex'].unique()))

# Plot lines for each y
for y in df['y'].unique():
    y_data = df[df['y'] == y]
    color = color_map[y]
    plt.plot('x', 'value', data=y_data, label=y,
             marker='o', markersize=5, color=color)

# Customize the plot
plt.title("xyv_multiline")
plt.xlabel("Date")
plt.ylabel("Value")

# Set y-axis limits and ticks
plt.ylim(0, 1.1)
y_ticks = [i/10 for i in range(0, 11)]
plt.yticks(y_ticks, [f'{int(y*100)}%' for y in y_ticks])

# Format x-axis ticks
plt.xticks(range(len(df['x'].unique())), df['x'].unique(), rotation=0, ha='center')

# Add value labels to the last point of each line
for y in df['y'].unique():
    y_data = df[df['y'] == y]
    last_point = y_data.iloc[-1]
    x_pos = df['x'].unique().tolist().index(last_point['x'])
    plt.annotate(f"{int(last_point['value']*100)}%",
                 (x_pos, last_point['value']),
                 textcoords="offset points",
                 xytext=(0,10),
                 ha="center")

# Remove top and right spines
plt.gca().spines['top'].set_visible(False)
plt.gca().spines['right'].set_visible(False)

## Add only horizontal grid lines
plt.gca().yaxis.grid(True, linestyle='--', alpha=0.2)
plt.gca().xaxis.grid(False)

# Adjust x-axis limits
plt.xlim(-0.5, len(df['x'].unique()) -0.5)

# Add legend with no background or border
plt.legend(frameon=False)

# Use tight layout
plt.tight_layout()

# Show the plot
#plt.show()

chart_out = _vl + r'\change\line_multi_xstr_ypct.png'
plt.savefig(chart_out)
#sp.Popen(chart_out, shell=True) #open file
#plt.show()

#exec(open(_vl+r'\change\line_multi_xstr_ypct.py').read())

