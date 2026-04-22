# %% barh_stk_xs_yn_bkk

## Dependencies
import matplotlib.pyplot as plt
import pandas as pd
from analytics_tasks.automate_office.build_batch import (
    transform_data,
)
from analytics_tasks.automate_office.build_explore import (
    transform_data_explore,
)
from analytics_tasks.utils.os_functions import open_file_folder


## barh_stk_xs_yn_bkk
def barh_stk_xs_yn_bkk(
    df,
    chartTitle="barh_stk_xs_yn_bkk",
    studyPeriod=12,
    special_series_name=None,
    special_series_label_font_size=10,
    chart_out=None,
    chart_width=2.5,
    chart_height=1.3,
    chart_title_font_size=10,
    chart_title_color="black",  # New parameter for title color
    series_label_font_size=9,
    series_label_color="white",  # New parameter for bar text color
    xtick_label_font_size=9,
    xtick_label_color="black",  # New parameter for y-axis label color (categories)
    k_value_font_size=9,
    k_value_color="#01387B",
):  # New parameter for k-value (secondary) text color
    # Set up the figure and axis
    fig, ax = plt.subplots(figsize=(chart_width, chart_height))

    df["value"] = round(df["value"], 1)

    # Sort the dataframe by 'value' column in descending order
    df = df.sort_values(by="value", ascending=True).reset_index(drop=True)

    # After sorting, then extract lists
    categories = df["x"].tolist()
    values = df["value"].tolist()
    z_values = df["z"].tolist()
    colors = df["color_hex"].tolist()

    # Total bar length
    total_bar_length = studyPeriod

    # Calculate remainders
    remainders = [total_bar_length - value for value in values]

    # Horizontal bars for first part (with the specified values)
    bars1 = ax.barh(categories, values, color=colors)

    bars2 = ax.barh(categories, remainders, left=values, color="#e0e0e0")

    # Add value labels on the bars with " month" suffix
    for i, (bar, value, category) in enumerate(zip(bars1, values, categories)):
        # Make the text bold and larger for special_series_name
        if category == special_series_name:
            ax.text(
                value / 2,
                i,
                f"{value} months",
                ha="center",
                va="center",
                color=series_label_color,
                fontweight="bold",
                fontsize=special_series_label_font_size,
            )  # Using new color parameter
        else:
            ax.text(
                value / 2,
                i,
                f"{value} months",
                ha="center",
                va="center",
                color=series_label_color,
                fontweight="bold",
                fontsize=series_label_font_size,
            )  # Using new color parameter

    # Then update the z values text section
    for i, (z_value, category) in enumerate(zip(z_values, categories)):
        # Format the z_value in thousands with 'K' suffix
        formatted_z = f"{z_value / 1000:.0f}K"
        # Remove decimal point if it's a whole number
        if formatted_z.endswith(".0K"):
            formatted_z = formatted_z.replace(".0K", "K")

        # Make the text bold and larger for special_series_name
        if category == special_series_name:
            ax.text(
                total_bar_length + 0.2,
                i,
                formatted_z,
                ha="left",
                va="center",
                color=k_value_color,
                fontweight="bold",
                fontsize=special_series_label_font_size,
            )  # Using new color parameter
        else:
            ax.text(
                total_bar_length + 0.2,
                i,
                formatted_z,
                ha="left",
                va="center",
                # color=k_value_color, fontweight='bold', fontsize=k_value_font_size)  # Using new color parameter
                color=k_value_color,
                fontsize=k_value_font_size,
            )  # Using new color parameter

    # Title - extreme left aligned
    ax.set_title("")  # Remove the standard title
    if chartTitle == "":
        print("NOTE: No title.")
    else:
        chartTitle = f"{chartTitle}: {studyPeriod} months follow-up"
        ax.text(
            -0.19,
            1.15,
            chartTitle,
            fontsize=chart_title_font_size,
            color=chart_title_color,
            transform=ax.transAxes,
        )  # Using new color parameter

    # Remove ALL x-axis elements completely
    ax.set_xticks([])
    ax.xaxis.set_ticks_position("none")
    ax.spines["bottom"].set_visible(False)

    # Set y-axis labels with custom font size (this is for the category labels)
    ax.yaxis.set_ticks_position("none")
    ax.set_yticks(range(len(categories)))

    # First set all labels with default size and color
    ax.set_yticklabels(
        categories, fontsize=xtick_label_font_size, color=xtick_label_color
    )  # Using new color parameter

    # Then customize the specific label for special series
    for label in ax.get_yticklabels():
        if label.get_text() == special_series_name:
            label.set_fontweight("bold")
            label.set_fontsize(special_series_label_font_size)
            label.set_color(xtick_label_color)  # Maintain the same color

    ax.spines["left"].set_visible(False)

    # Remove other spines and grid
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(False)

    # Adjust layout
    plt.tight_layout()

    # Show the plot
    # plt.show()

    if chart_out:
        plt.savefig(chart_out)
        # print('REPORT: barh_stk_xs_yn_bkk output successfully saved.')

    plt.close()


## Run
if __name__ == "__main__":
    # Data
    df = pd.read_csv(_vl / "compare/barh_stk_xs_yn_bkk.csv")

    # Colors
    _colors_file = _vl / "____settings/colors.xlsm"

    # Transpose
    df = transform_data(df, x=["drug"], y=["staytime"], z=["pc"])

    # Add colors
    df = transform_data_explore(df, _colors_file)

    chart_out = _vl / "compare/barh_stk_xs_yn_bkk.png"

    barh_stk_xs_yn_bkk(
        df,
        chart_out=chart_out,
        chartTitle="",
        chart_title_font_size=16,
        chart_title_color="#00165E",
        studyPeriod=12,
        special_series_name="",
        special_series_label_font_size=11,
        chart_width=5,
        chart_height=2,
        series_label_font_size=12,
        xtick_label_color="#00165E",
        xtick_label_font_size=12,
        k_value_font_size=12,
        k_value_color="#00165E",
    )

    open_file_folder(chart_out)


## Self
"""
exec(open(_vl / 'compare/barh_stk_xs_yn_bkk.py', encoding='utf-8').read())
"""
