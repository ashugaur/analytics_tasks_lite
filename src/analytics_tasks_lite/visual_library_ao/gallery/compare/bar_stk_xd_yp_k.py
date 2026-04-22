# %% bar_stacked_xdt_ypct_k


## About
"""
transform_data(df, x=['date'], y=['source'], value=['nbr_of_patients'])

date       drug   source nbr_of_patients
2022-01-31 Drug A New    1243
2022-01-31 Drug A Old    19518
2022-01-31 Drug A Mature 47570
"""

## Dependencies
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from analytics_tasks.utils.functions import open_file_folder
from analytics_tasks.automate_office.build_batch import (
    transform_data,
)
from analytics_tasks.automate_office.build_explore import (
    transform_data_explore,
)


## generate_simulated_data
def generate_simulated_data(start_date, end_date, freq="D"):
    """
    Generate simulated data for a stacked bar chart.

    Parameters:
    start_date (str): The start date in 'YYYY-MM-DD' format.
    end_date (str): The end date in 'YYYY-MM-DD' format.
    freq (str): The frequency of the data. Can be 'D' (daily), 'M' (monthly), or 'Y' (yearly). Default is 'D'.

    Returns:
    pd.DataFrame: A DataFrame with the simulated data.
    """
    # Define the date range
    dates = pd.date_range(start=start_date, end=end_date, freq=freq)

    # Define the drug names
    drugs = ["Drug A", "Drug B", "Drug C", "Drug D"]

    # Define the source names
    sources = ["new", "old", "mature", "happy", "spring"]

    # Generate the data
    data = []
    for date in dates:
        for drug in drugs:
            for source in sources:
                # Generate random number of patients with a pattern
                if source == "New":
                    nbr_of_patients = np.random.randint(50, 5000)
                elif source == "Old":
                    nbr_of_patients = np.random.randint(5000, 20000)
                else:
                    nbr_of_patients = np.random.randint(20000, 50000)

                data.append([date.strftime("%Y-%m-%d"), drug, source, nbr_of_patients])

    # Create a DataFrame
    df = pd.DataFrame(data, columns=["date", "drug", "source", "nbr_of_patients"])

    return df


## Simulation
# df_daily = generate_simulated_data('2022-01-01', '2022-01-31', freq='D')
# print("Daily Data:")
# print(df_daily.head())

# df_monthly = generate_simulated_data("2022-01-01", "2023-12-31", freq="ME")
# print("\nMonthly Data:")
# print(df_monthly.head())
# df_monthly.head()
# df_monthly.head().to_clipboard()

# df_yearly = generate_simulated_data('2022-01-01', '2025-12-31', freq='Y')
# print("\nYearly Data:")
# print(df_yearly.head())


## Filter data
df_monthly = pd.read_csv(_vl / "compare/bar_stacked_xdt_ypct_k.csv")
df = df_monthly[df_monthly["drug"] == "Drug A"]


## Colors
# exec(open(_exploratory + r"\format\pandas\hex_to_rgb_fill_missing_colors.py").read())
# df_colors = pd.read_excel(_edupunk_docs + r"\tables\mkdocs.xlsx", sheet_name="colors")
# df_colors = df_colors.sort_values(by=["Mode", "Tool", "Usage"]).reset_index(drop=True)
# df_colors = fill_missing_colors(df_colors)
# df_colors.columns = df_colors.columns.str.lower()


# ## Transpose data
# exec(open(_exploratory + r"\transpose\pandas\transform_data.py").read())
df = transform_data(df, x=["date"], y=["source"], value=["nbr_of_patients"])

# df = pd.merge(
#     df, df_colors[["usage", "color_hex", "color_rgb"]], left_on="y", right_on="usage"
# )
# del df["usage"]
# df.head(3).to_clipboard()
# df.to_clipboard(index=False)

_colors_file = _vl / "____settings/colors.xlsm"

df = transform_data_explore(df, _colors_file)


# convert date string to datetime
df["x"] = pd.to_datetime(df["x"], format='%d-%m-%Y')

# Calculate percentages and totals
df_pct = df.pivot_table(index="x", columns="y", values="value", aggfunc="sum")
df_totals = df_pct.sum(axis=1)
df_pct = df_pct.div(df_totals, axis=0) * 100

# Create the stacked bar chart
plt.figure()
ax = plt.gca()
# ax.set_facecolor('#1f1f1f')
# plt.gcf().set_facecolor('#1f1f1f')
plt.gcf()

# Plot stacked bars
colors = df[["y", "color_hex"]].drop_duplicates().set_index("y")["color_hex"].to_dict()
df_pct.plot(kind="bar", stacked=True, ax=ax, color=[colors[y] for y in df_pct.columns])

# Customize the plot
# plt.grid(True, axis='y', linestyle='--', alpha=0.2)
ax.grid(False)  # Remove gridlines
ax.set_yticks([])  # Remove y-axis ticks
ax.set_ylabel("")  # Remove y-axis label


# Format x-axis
x_labels = [d.strftime("%b-%y") for d in df_pct.index]
ax.set_xticklabels(x_labels, rotation=0)

# Set x-axis title
ax.set_xlabel("Date")

# Add total values on top of bars
for i, total in enumerate(df_totals):
    plt.text(i, 100, f"{int(total / 1000)}K", ha="center", va="bottom")

# Add percentage labels
for c in ax.containers:
    ax.bar_label(c, fmt="%.0f%%", label_type="center", color="white")

# Customize apperance
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_visible(False)
# ax.spines['bottom'].set_color('white')
# ax.tick_params(colors='white')

# Add legend
# plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left',
# facecolor='#1f1f1f', labelcolor='white')

plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", frameon=False)

plt.tight_layout()
# plt.show()

chart_out = _vl / 'compare/bar_stacked_xdt_ypct_k.png'
plt.savefig(chart_out)
open_file_folder(chart_out)


## Self
"""
exec(open(_vl / 'compare/bar_stacked_xdt_ypct_k.py', encoding='utf-8').read())
"""
