from pathlib import Path
from analytics_tasks.utils.combine.combine_charts import combine_charts

# Write to file
c = combine_charts(
    input_files=[
        Path(r"C:\my_disk\projects\visual_library\bar\simple\bar_chart.html"),
        Path(
            r"C:\my_disk\projects\visual_library\distribution\density\histogram_summary_frequency.html"
        ),
        Path(r"C:\my_disk\projects\visual_library\bar\simple\bar_chart.html"),
        Path(
            r"C:\my_disk\projects\visual_library\radar\radar_patient_profile.html"
        ),
    ],
    cols=2,
    rows=2,
    output_file=Path(
        r"C:\my_disk\projects\visual_library\report\utilities\combine_charts.html"
    ),
)





c = combine_charts(
    input_files=[
        r"C:\my_disk\____tmp\word_count_distribution.html",
        r"C:\my_disk\____tmp\snippet_duration_distribution.html",
    ],
    cols=2,
    rows=1,
    output_file=Path(r"C:\my_disk\____tmp\snippet_duration_word_count_distribution1.html"),
)



c = combine_charts(
    input_files=[
        r"C:\Users\Ashut\Downloads\div_writeup.htmltable",
        r"C:\my_disk\____tmp\snippet_duration_distribution.html",
    ],
    cols=2,
    rows=1,
    col_spacing=[0.35, 0.65],
    output_file=Path(r"C:\my_disk\____tmp\snippet_duration_word_count_distribution1.html"),
)
