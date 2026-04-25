"""
Image-colored wordcloud with boundary map
=========================================
A slightly more elaborate version of an image-colored wordcloud
that also takes edges in the image into account.
Recreating an image similar to the parrot example.
"""

import numpy as np
from PIL import Image
from os import path
from pathlib import Path
from wordcloud import WordCloud, STOPWORDS
from scipy.ndimage import gaussian_gradient_magnitude
from analytics_tasks.utils.os_functions import assign_rd

result = assign_rd(
    code_folder_exists=0,
    base_level=1,
    file_path=Path("C:/my_disk/projects/visual_library/wordcloud/parrot.py"),
    upaths=[
        {"_startup": Path("C:/my_disk/edupunk/src/functions/startup.py")},
    ],
    startup=True,
)
rf, ff, fn, fr, rfo, rfi, rfir, *user_paths, startup_vars = result
globals().update(startup_vars)

text = open(Path(ff) / "parrot.txt", encoding='utf-8').read()

alice_mask = np.array(Image.open(Path(ff) / "parrot.gif"))
parrot_color = np.array(Image.open(Path(ff) / "parrot.jpg"))
parrot_color = parrot_color[::3, ::3]
parrot_mask = parrot_color.copy()  # white is "masked out"
parrot_mask[parrot_mask.sum(axis=2) == 0] = 255

edges = np.mean(
    [gaussian_gradient_magnitude(parrot_color[:, :, i] / 255.0, 2) for i in range(3)],
    axis=0,
)
parrot_mask[edges > 0.08] = 255

wc = WordCloud(
    max_words=2000,
    mask=parrot_mask,
    max_font_size=40,
    random_state=42,
    relative_scaling=0,
)

wc.generate(text)

wc.to_file(path.join(str(ff), "parrot.png"))
