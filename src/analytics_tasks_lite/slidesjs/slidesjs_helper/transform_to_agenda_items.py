# %% Slide agenda

import pandas as pd

def transform_to_agenda_items(df):
    """
    Transforms a DataFrame into a list of dictionaries with HTML-formatted strings.
    """
    agenda_items = []
    
    for _, row in df.iterrows():
        # Construct the formatted string
        formatted_text = f"<strong>{row['agenda_starter']}</strong> {row['agenda_statment']}"
        
        # Append to the final list
        agenda_items.append({
            "slide_num": int(row['slide_nbr']),
            "text": formatted_text
        })
        
    return agenda_items

if __name__ == '__main__':
    data = {
        'slide_nbr': [2, 3, 4, 5, 6],
        'agenda_starter': ['Overview:', 'Analysis:', 'Comparison:', 'Details:', 'Flow:'],
        'agenda_statment': ['Sunburst Visualizations', 'Network Graphs', 'Side-by-side Charts', 'Grid Layout', 'D3 Sankey Diagram']
    }

    df = pd.DataFrame(data)
    agenda_list = transform_to_agenda_items(df)

