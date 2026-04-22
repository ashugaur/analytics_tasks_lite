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


def generate_slide_index_text(
    index_items,
    title="Presentation Agenda",
    columns=1,
    font_size=15,
    title_font_size=28,
    item_padding="16px 20px",
    gap="13px"
):
    """Generate clickable agenda (same as original)"""
    
    badge_size = int(font_size * 2.4)
    badge_font = int(font_size * 0.93)
    
    items_html = []
    for idx, item in enumerate(index_items):
        slide_target = item["slide_num"] - 1
        text = item["text"]
        
        margin_style = ""
        if columns == 1 and idx < len(index_items) - 1:
            margin_style = f"margin-bottom: {gap};"
        
        item_html = f'''
        <div class="index-item" data-slide-target="{slide_target}"
             style="background: white; padding: {item_padding}; border-radius: 8px;
                    cursor: pointer; transition: all 0.3s ease;
                    border-left: 5px solid #001965; display: flex;
                    align-items: center; box-shadow: 0 2px 6px rgba(0,0,0,0.08);
                    {margin_style}">
            <div style="background: #001965; color: white;
                        width: {badge_size}px; height: {badge_size}px;
                        border-radius: 50%; display: flex; align-items: center;
                        justify-content: center; font-weight: bold;
                        font-size: {badge_font}px;
                        margin-right: 14px; flex-shrink: 0;">
                {item["slide_num"]}
            </div>
            <div style="color: #333; font-size: {font_size}px; line-height: 1.5;">
                {text}
            </div>
        </div>
        '''
        items_html.append(item_html)
    
    if columns == 1:
        max_width = "700px"
        container_style = f"max-width: {max_width}; margin: 0 auto;"
        items_container = f'<div style="{container_style}">{"".join(items_html)}</div>'
    else:
        max_width = "1000px" if columns == 2 else "1100px"
        grid_template = " ".join(["1fr"] * columns)
        container_style = f"display: grid; grid-template-columns: {grid_template}; gap: {gap}; max-width: {max_width}; margin: 0 auto;"
        items_container = f'<div style="{container_style}">{"".join(items_html)}</div>'
    
    full_html = f"""
<div style="font-family: Calibri; padding: 20px;">
    <h2 style="color: #001965; font-size: {title_font_size}px; font-weight: bold;
               margin: 0 0 25px 0; text-align: center;">
        {title}
    </h2>
    {items_container}
</div>

<style>
    .index-item:hover {{
        background: #e8f0fe !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 25, 101, 0.15) !important;
    }}
</style>
"""
    
    return f"TEXT:{full_html}"

if __name__ == '__main__':

    agenda_items = [
        {"slide_num": 2, "text": "<strong>Overview:</strong> Sunburst Visualizations"},
        {"slide_num": 3, "text": "<strong>Analysis:</strong> Network Graphs"},
        {"slide_num": 4, "text": "<strong>Comparison:</strong> Side-by-side Charts"},
        {"slide_num": 5, "text": "<strong>Details:</strong> Grid Layout"},
        {"slide_num": 6, "text": "<strong>Flow:</strong> D3 Sankey Diagram"}
    ]
    
    agenda_slide = generate_slide_index_text(
        agenda_items,
        title="Presentation Agenda",
        columns=1,
        font_size=15
    )
    
    slides_config = [
        # Agenda
        {
            'layout': 'single',
            'charts': [agenda_slide],
            'title': 'blank',  # No title for agenda slide
            'footer': 'Internal Use Only',
            'footnote': 'Click any item to jump to section'
        },
        
        # Sunbursts
        {
            'layout': 'two-column',
            'charts': [
                str(_vl / "sunburst/simple.html"),
                str(_vl / "sunburst/labels.html")
            ],
            'title': 'Sunburst Visualizations',
            'subtitle': 'Hierarchical data representation',
            'title_image': str(_vl / '____settings/flag_countries/in.png'),
            'overlay': {
                'text': 'DRAFT',
                'position': 'top-right',
                'bg_color': 'rgba(220, 53, 69, 0.9)',
                'text_color': 'white'
            }
        },
        
        # Network
        {
            'layout': 'single',
            'charts': [str(_vl / "graph/graph-label-overlap.html")],
            'title': 'Network Graph Analysis',
            'subtitle': 'Relationship visualization',
            'title_image': str(_vl / '____settings/flag_countries/in.png')
        },
        
        # Side by side
        {
            'layout': 'two-column',
            'charts': [
                str(_vl / "candlestick/candlestick_nbrx_trx.html"),
                str(_vl / "venn/upset_movie_data_customize.html")
            ],
            'title': 'Comparative Analysis',
            'chart_scale': [0.6, 0.4],
            'title_image': str(_vl / '____settings/flag_countries/in.png'),
            'footnote': 'Trading patterns vs. Set intersections'
        },
        
        # Grid
        {
            'layout': 'grid-2x2',
            'charts': [
                str(_vl / "sunburst/labels.html"),
                str(_vl / "sunburst/labels.html"),
                str(_vl / "graph/graph-label-overlap.html"),
                str(_vl / "venn/upset_movie_data_customize.html")
            ],
            'title': 'Detailed Breakdown',
            'title_image': str(_vl / '____settings/flag_countries/in.png'),
            'footnote': 'Multiple perspectives on the data'
        },
        
        # Sankey
        {
            'layout': 'single',
            'charts': [str(_vl / "sankey/sankey_d3.html")],
            'title': 'Flow Analysis',
            'subtitle': 'D3 Sankey Diagram',
            'title_image': str(_vl / '____settings/flag_countries/in.png')
        },
        
        # Thank you
        {
            'layout': 'single',
            'charts': [
                """TEXT:
                <div style="text-align: center; padding: 100px 40px;">
                    <h1 style="font-size: 64px; color: #001965; margin-bottom: 40px;">
                        Thank You
                    </h1>
                    <p style="font-size: 24px; color: #666;">
                        Questions?<br><br>
                        analytics@company.com
                    </p>
                </div>
                """
            ],
            'footer': 'End of Presentation'
        }
    ]
    
    print("\n" + "="*70)
    print("🧪 TEST 5: Complete Presentation")
    print("="*70)
    
    output = slidesjs(
        slides_config=slides_config,
        output_file=str(_tmp / "test_full_presentation.html"),
        page_title="Insights",
        company_name="Company",
        default_footer="Internal Use Only",
        current_date="02-Jan-2026",
        js_folder=str(_vl / "____settings/js"),
        theme_colors={
            'primary': '#001965',
            'text': '#333',
            'muted': '#666',
            'light': '#999'
        },
        slide_width=1280,
        slide_height=720
    )

