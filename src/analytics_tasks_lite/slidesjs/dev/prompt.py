from analytics_tasks.utils.finding import find_excel_column_name

files = [r"C:\my_disk\projects\visual_library\slidejs\slidejs.xlsm"]

# Get ALL columns from all sheets
all_columns = find_excel_column_name(
    file_paths=files, string=None, unique_value_limit=10, return_df=False
)

# import pprint
# pprint.pprint(all_columns, width=140)

# Or get as DataFrame
df_all = find_excel_column_name(file_paths=files, string=None, return_df=True)
print(df_all)
df_all.to_clipboard(index=False)



"""
## Question scope
Please let me know if you understand the attached project and the task at hand.
The entire slidejs codebase and its pieces work perfect.

## Project files attached
slidejs.py: creates slide deck
slidejs_excel_runner.py: reads slidejs.xlsm or the control file to input into slidejs.py
slidejs_template.html: is the presentation re usable template
check_chart.py is compatability checked for a chart with slidejs project
slidejs.xlsm is the input file and its content are as in "" below.

""
file_path	sheet_name	column_name	matches	match_type	unique_values_preview
slidejs.xlsm	Version	Version	TRUE	all	2.0.0
slidejs.xlsm	Help	help_text	TRUE	all	<strong>Keyboard Shortcuts</strong>…
slidejs.xlsm	Summary_Config	Test_ID	TRUE	all	test_1
slidejs.xlsm	Summary_Config	order	TRUE	all	1, 2, 3, 4, 5
slidejs.xlsm	Summary_Config	summary_text	TRUE	all	Review in Q2 2026
slidejs.xlsm	Reference_Config	Test_ID	TRUE	all	test_1
slidejs.xlsm	Reference_Config	group	TRUE	all	top_of_links, AI, Benchmarks, Acccount
slidejs.xlsm	Reference_Config	text	TRUE	all	Disclaimer: Restrictions and limitations may apply.
slidejs.xlsm	Reference_Config	hyperlink	TRUE	all	0, 1
slidejs.xlsm	Reference_Config	unc	TRUE	all	https://huggingface.co/blog
slidejs.xlsm	Reference_Config	group_column_number	TRUE	all	0, 1, 2
slidejs.xlsm	Reference_Config	order	TRUE	all	1, 2, 3, 4, 5
slidejs.xlsm	Global_Config	Test_ID	TRUE	all	test_1
slidejs.xlsm	Global_Config	Parameter	TRUE	all	page_title, output_file, company_name, current_date, debug_mode, …
slidejs.xlsm	Global_Config	Type	TRUE	all	str, any, bool, string, int, list, boolean
slidejs.xlsm	Global_Config	Default Value	TRUE	all	All scenario testing…
slidejs.xlsm	Global_Config	Required	TRUE	all	No
slidejs.xlsm	Global_Config	Test_Value	TRUE	all	test_1.html, False, True, verbose
slidejs.xlsm	Global_Config	Description	TRUE	all	Title of the presentation…
slidejs.xlsm	Agenda_Config	Test_ID	TRUE	all	test_1
slidejs.xlsm	Agenda_Config	Slide_Num	TRUE	all	3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21
slidejs.xlsm	Agenda_Config	group	TRUE	all	Text, Custom box, Warning strip, Bar, Line
slidejs.xlsm	Agenda_Config	agenda_starter	TRUE	all	
slidejs.xlsm	Agenda_Config	agenda_statement	TRUE	all	Plain text, HTML text…
slidejs.xlsm	Slide_Config	Test_ID	TRUE	all	test_1
slidejs.xlsm	Slide_Config	Slide_Num	TRUE	all	1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21
slidejs.xlsm	Slide_Config	layout	TRUE	all	single, two-column
slidejs.xlsm	Slide_Config	title	TRUE	all	Plain text, HTML text…
slidejs.xlsm	Slide_Config	subtitle	TRUE	all	Normal text…
slidejs.xlsm	Slide_Config	title_image	TRUE	all	
slidejs.xlsm	Slide_Config	footer	TRUE	all	
slidejs.xlsm	Slide_Config	footnote	TRUE	all	
slidejs.xlsm	Slide_Config	chart_scale	TRUE	all	[0.5, 0.5]
slidejs.xlsm	Slide_Config	agenda_group	TRUE	all	Text, Custom box, Warning strip, Bar, Line
slidejs.xlsm	Slide_Config	agenda_starter	TRUE	all	
slidejs.xlsm	Slide_Config	agenda_statement	TRUE	all	Plain text, HTML text…
slidejs.xlsm	Slide_Config	overlay_text	TRUE	all	Hello! There
slidejs.xlsm	Slide_Config	overlay_position	TRUE	all	top-left
slidejs.xlsm	Slide_Config	overlay_bg_color	TRUE	all	
slidejs.xlsm	Slide_Config	overlay_text_color	TRUE	all	
slidejs.xlsm	Slide_Config	overlay_font_size	TRUE	all	8px
slidejs.xlsm	Slide_Config	title_font_size	TRUE	all	32px
slidejs.xlsm	Slide_Config	warning_strip_text	TRUE	all	This warning strip…
slidejs.xlsm	Slide_Config	warning_strip_position	TRUE	all	
slidejs.xlsm	Slide_Config	warning_strip_bg_color	TRUE	all	
slidejs.xlsm	Slide_Config	warning_strip_text_color	TRUE	all	
slidejs.xlsm	Slide_Config	warning_strip_height	TRUE	all	
slidejs.xlsm	Slide_Config	title_color	TRUE	all	rgba(220, 53, 69, 0.9)
slidejs.xlsm	Slide_Config	subtitle_font_size	TRUE	all	11px
slidejs.xlsm	Slide_Config	subtitle_color	TRUE	all	
slidejs.xlsm	Slide_Config	debug_borders	TRUE	all	
slidejs.xlsm	Slide_Config	Notes	TRUE	all	
slidejs.xlsm	Chart_Config	Test_ID	TRUE	all	test_1
slidejs.xlsm	Chart_Config	Slide_Num	TRUE	all	1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21
slidejs.xlsm	Chart_Config	Chart_Pos	TRUE	all	1, 2
slidejs.xlsm	Chart_Config	Source_Type	TRUE	all	TEXT, HTML
slidejs.xlsm	Chart_Config	Source_Path	TRUE	all	TEXT: sample text
slidejs.xlsm	Chart_Config	container_id	TRUE	all	auto
slidejs.xlsm	Chart_Config	type	TRUE	all	text, chart
slidejs.xlsm	Chart_Config	custom_css	TRUE	all	
slidejs.xlsm	Chart_Config	width	TRUE	all	
slidejs.xlsm	Chart_Config	height	TRUE	all	
slidejs.xlsm	Chart_Config	Notes	TRUE	all	ECharts/D3 chart
slidejs.xlsm	Custom_Box_config	Test_ID	TRUE	all	test_1
slidejs.xlsm	Custom_Box_config	Slide_Num	TRUE	all	9, 4
slidejs.xlsm	Custom_Box_config	Box_ID	TRUE	all	annotation_1, logo_overaly, data_table
slidejs.xlsm	Custom_Box_config	Source_Type	TRUE	all	TEXT, IMAGE, HTMLTABLE
slidejs.xlsm	Custom_Box_config	Source_Path	TRUE	all	TEXT: Key Finding #1…
slidejs.xlsm	Custom_Box_config	Top	TRUE	all	100px, 40px, 200px
slidejs.xlsm	Custom_Box_config	Left	TRUE	all	400px, 600px
slidejs.xlsm	Custom_Box_config	Width	TRUE	all	200px, 100px, 400px
slidejs.xlsm	Custom_Box_config	Height	TRUE	all	auto, 100px, 200px
slidejs.xlsm	Custom_Box_config	Z_index	TRUE	all	1000, 1050
slidejs.xlsm	Custom_Box_config	BG_Color	TRUE	all	rgba(255,255,255,0.9, transparent, white
slidejs.xlsm	Custom_Box_config	Text_Color	TRUE	all	#333, -
slidejs.xlsm	Custom_Box_config	Border	TRUE	all	2px solid #001965, none, 1px solid #ddd
slidejs.xlsm	Custom_Box_config	Border_Radius	TRUE	all	8px, 0, 6px
slidejs.xlsm	Custom_Box_config	Padding	TRUE	all	20px, 0, 15px
slidejs.xlsm	Theme_Config	Test_ID	TRUE	all	test_1
slidejs.xlsm	Theme_Config	Theme_Name	TRUE	all	default
slidejs.xlsm	Theme_Config	primary	TRUE	all	#c23899
slidejs.xlsm	Theme_Config	text	TRUE	all	#808080
slidejs.xlsm	Theme_Config	muted	TRUE	all	#666
slidejs.xlsm	Theme_Config	light	TRUE	all	#999
slidejs.xlsm	Theme_Config	content_bg	TRUE	all	#ffffff
slidejs.xlsm	Theme_Config	slide_bg	TRUE	all	#ffffff
slidejs.xlsm	Theme_Config	header_border	TRUE	all	#e0e0e0
slidejs.xlsm	Theme_Config	Notes	TRUE	all	Default blue theme
slidejs.xlsm	Font_Config	Test_ID	TRUE	all	test_1
slidejs.xlsm	Font_Config	title	TRUE	all	36px
slidejs.xlsm	Font_Config	subtitle	TRUE	all	18px
slidejs.xlsm	Font_Config	body	TRUE	all	16px
slidejs.xlsm	Font_Config	overlay	TRUE	all	11px
slidejs.xlsm	Font_Config	footnote	TRUE	all	12px
slidejs.xlsm	Font_Config	agenda_group_heading	TRUE	all	15px
slidejs.xlsm	Font_Config	agenda_item	TRUE	all	13px
slidejs.xlsm	Font_Config	footer	TRUE	all	12px
slidejs.xlsm	Font_Config	Notes	TRUE	all	Default sizes
""

## Problem to solve
The attached project has these closely related overlay features:

1. shortcut Q for quick summary is an overlay for quick insights, based on 'Summary_Config' sheet in the input file
2. shortcut I for index overlay
3. adding html and image and svg using 'Custom_Box_config'
4. there are hover on display buttons on each slide for going to home, index overlay and present from a slide button

I want to know what would it take to create a new overlay feature, a svg button, the main purpose of this button will be when we click it expands to open a box with text content, it should work in normal report mode and presentation mode.

The main content of this overlay will be writeup summary on an analysis, text information like executive summary neately formatted as heading subheading paragraphs and lists. in my mind creating an excel sheet 'Deep_Overview_Config' in our input file with parameters as in ``` below. We call this feature deep dive and have shortcut key 'd' to open it. The difference in this overlay is that it opens within the page within the dimensions that we specify in our sheet and it should if we press 'd' again it should close, there should be a 'x' button at top right to close the overlay with mouse. The mindset here is to better utilize the space within slides and provide user a better experince is reading report summaries. I want to discuss with you on what approach we should take to create a foolproof solution, as i think having this features capability to put content within each slide will add complexity.

```
Test_ID	Slide_Num	Overview_ID	Button_Icon	Button_Tooltip	Top	Left	Width	Height	Z_index	BG_Color	Title	Subtitle	Content_Type	Content	Order
test_1	3	DO_001	bugfix	Deep analysis	20px	20px	auto	auto	1000	rgba(0,0,0,0.7)	Executive Summary	Q3 Analysis	heading	Market Analysis	1
test_1	3	DO_001	bugfix	Deep analysis									paragraph	Our analysis reveals...	2
```

"""
