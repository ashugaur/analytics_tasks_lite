# %% bar_stackedh_xstr_yum_kbspk

## About
"""
transform_data(df, x=['drug'], y=['staytime'])
transform_data(df, x=['drug'], y=['staytime'], z=['pc'])

drug   staytime
Drug C 8       
Drug B 6       
Drug A 5       
"""



import matplotlib.pyplot as plt
import pandas as pd
import io

# Sample data
data_stringx = """
x	y	value
Drug A	staytime	5
Drug B	staytime	6
Drug C	staytime	8
"""

data_string = """
drug	staytime
Drug C	8
Drug B	6
Drug A	5
"""

# Parse the data
df = pd.read_csv(io.StringIO(data_string), sep='\t')

# Colors
exec(open(_exploratory+r"\format\pandas\hex_to_rgb_fill_missing_colors.py").read())
df_colors = pd.read_excel(_edupunk_docs+r"\tables\mkdocs.xlsx", sheet_name='colors')
df_colors = df_colors.sort_values(by=['Mode', 'Tool', 'Usage']).reset_index(drop=True)
df_colors = fill_missing_colors(df_colors)
df_colors.columns = df_colors.columns.str.lower()

# Transpose (if function not there use data_strigx)
exec(open(_exploratory+r"\transpose\pandas\transform_data.py").read())
df = (transform_data(df, x=['drug'], y=['staytime']))
df = pd.merge(df, df_colors[['usage', 'color_hex', 'color_rgb']], left_on='x', right_on='usage', how='left')
del df['usage']
#df.to_clipboard(index=False)

# Set up the figure and axis
fig, ax = plt.subplots(figsize=(5, 1.5))

# Total bar length
total_bar_length = 10

# Create the stacked bars
categories = df['x'].tolist()
values = df['value'].tolist()
remainders = [total_bar_length - value for value in values]

# Get colors from the data - using hex values since they're easier to use directly
colors = df['color_hex'].tolist()

# Horizontal bars for first part (with the specified values)
# Using colors from the data for each bar
bars1 = ax.barh(categories, values, color=colors)

# Horizontal bars for second part (remainder to reach total_bar_length)
bars2 = ax.barh(categories, remainders, left=values, color='#e0e0e0')

# Add value labels on the bars with " month" suffix
for i, (bar, value) in enumerate(zip(bars1, values)):
    ax.text(value/2, i, f"{value} months", ha='center', va='center', 
            color='white', fontweight='bold')

# Title - left aligned
ax.set_title('bar_stackedh_xstr_yum_kbspk', fontsize=10, loc='left')

# Remove ALL x-axis elements completely
ax.set_xticks([])
ax.xaxis.set_ticks_position('none')
ax.spines['bottom'].set_visible(False)

# Set y-axis labels but remove tick marks
ax.yaxis.set_ticks_position('none')
ax.set_yticks(range(len(categories)))
ax.set_yticklabels(categories)
ax.spines['left'].set_visible(False)

# Remove other spines and grid
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(False)

# Adjust layout
plt.tight_layout()

# Show the plot
#plt.show()

chart_out = _vl + r'\compare\bar_stackedh_xstr_yum_kbspk'
plt.savefig(chart_out+'.png')
#plt.savefig(chart_out+'.svg')
#sp.Popen(chart_out, shell=True) #open file
#plt.show()

#exec(open(_vl+r'\compare\bar_stackedh_xstr_yum_kbspk.py').read())
