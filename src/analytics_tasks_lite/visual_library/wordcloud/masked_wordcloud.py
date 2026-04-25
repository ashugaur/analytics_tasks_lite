# %% Masked wordcloud

## Dependencies
import os
import numpy as np
from os import path
from PIL import Image
from pathlib import Path
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
from analytics_tasks.utils.os_functions import assign_rd

result = assign_rd(
    code_folder_exists=0,
    base_level=1,
    file_path=Path(
        "C:/my_disk/projects/visual_library/wordcloud/masked_wordcloud.py"
    ),
    upaths=[
        {"_startup": Path("C:/my_disk/edupunk/src/functions/startup.py")},
    ],
    startup=True,
)
rf, ff, fn, fr, rfo, rfi, rfir, *user_paths, startup_vars = result
globals().update(startup_vars)


text = open(Path(ff) / "masked_wordcloud.txt").read()

## read the mask image
alice_mask = np.array(Image.open(Path(ff) / "masked_wordcloud.jpg"))

stopwords = set(STOPWORDS)
stopwords.add("said")

wc = WordCloud(
    background_color="white",
    max_words=2000,
    mask=alice_mask,
    stopwords=stopwords,
    contour_width=3,
    contour_color="steelblue",
)

wc.generate(text)

## Export
wc.to_file(path.join(str(ff), "masked_wordcloud.png"))

""" Export: svg
wc_image = wc.to_image()
plt.figure(figsize=(10, 10))  # Optional: define size for the SVG
plt.imshow(wc_image, interpolation="bilinear")  # <-- Using wc_image here
plt.axis("off")
plt.savefig(
    path.join(str(ff), "masked_wordcloud.svg"),
    format="svg",
    bbox_inches="tight",
    pad_inches=0,
)
"""
