# %% Visual library demo with fixed sidebar TOC

## Dependencies
from pathlib import Path
from collections import defaultdict


## create_site
def create_site(
    folder_to_scan,
    side_bar_width,
    page_color="#bb6e6e",
    toc_color="#007bff",
    toc_bg_color="rgba(255, 255, 255, 0.9)",
    image_extensions=[
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".svg",
        ".webp",
        ".jfif",
        ".xlsx",
        ".xlsm",
    ],
    exclude_folders=[],
):
    """
    Automatically generates an HTML gallery page by scanning a folder structure.
    Now with a fixed sidebar table of contents.

    Args:
        folder_to_scan (str): Path to the folder containing subfolders with images and related files
        page_color (str): Background color for the page (default: "#bb6e6e")
        toc_color (str): Color for the table of contents links (default: "#007bff")
        toc_bg_color (str): Background color for the TOC container (default: "rgba(255, 255, 255, 0.9)")
        output_file (str): Name of the output HTML file (default: "gallery.html")

    Returns:
        str: Path to the generated HTML file
    """

    # Define file type colors and priorities
    file_colors = {
        ".py": ("python", "#3776ab"),
        ".r": ("r", "#276dc3"),
        ".R": ("r", "#276dc3"),
        ".bas": ("basic", "#8b4513"),
        ".csv": ("csv", "#28a745"),
        ".xlsx": ("csv", "#15b63b"),
        ".xlsm": ("csv", "#11c93c"),
        ".jpg": ("jpg", "#dc3545"),
        ".jpeg": ("jpg", "#dc3545"),
        ".txt": ("txt", "#6c757d"),
        ".json": ("json", "#17a2b8"),
        ".xml": ("xml", "#fd7e14"),
        ".html": ("html", "#e83e8c"),
        ".js": ("js", "#ffc107"),
        ".css": ("css", "#20c997"),
    }

    def scan_folder(folder_path):
        """Scan folder and organize files by base name"""
        folder_path = Path(folder_path)
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder '{folder_path}' does not exist")

        gallery_data = {}

        # Scan each subfolder
        for subfolder in folder_path.iterdir():
            if not subfolder.is_dir() or subfolder.name in exclude_folders:
                continue

            subfolder_name = subfolder.name
            files_by_basename = defaultdict(list)

            # Group files by their base name (without extension)
            for file_path in subfolder.iterdir():
                if file_path.is_file():
                    basename = file_path.stem
                    extension = file_path.suffix.lower()
                    files_by_basename[basename].append(
                        {
                            "name": file_path.name,
                            "extension": extension,
                            "path": str(file_path.relative_to(folder_path)).replace(
                                "\\", "/"
                            ),
                        }
                    )

            # Process each group of files
            gallery_items = []
            for basename, files in files_by_basename.items():
                # Find the best image file
                image_file = None
                other_files = []

                for file_info in files:
                    if file_info["extension"] in image_extensions:
                        if image_file is None or image_extensions.index(
                            file_info["extension"]
                        ) < image_extensions.index(image_file["extension"]):
                            if image_file:
                                other_files.append(image_file)
                            image_file = file_info
                        else:
                            other_files.append(file_info)
                    else:
                        other_files.append(file_info)

                if image_file:
                    # Sort other files by extension for consistent display
                    other_files.sort(key=lambda x: x["extension"])

                    gallery_items.append(
                        {
                            "basename": basename,
                            "image": image_file,
                            "other_files": other_files,
                        }
                    )

            if gallery_items:
                # Sort items by basename for consistent ordering
                gallery_items.sort(key=lambda x: x["basename"])
                # gallery_items.sort(key=lambda x: image_extensions.index(x["image"]["extension"]))
                gallery_data[subfolder_name] = gallery_items

        return gallery_data

    def generate_html(gallery_data, page_color, toc_color, toc_bg_color):
        """Generate HTML content with fixed sidebar TOC"""

        html_template = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visual library</title>
    <style>
        /* Global styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: Arial, sans-serif;
            background-color: {page_color};
            padding-left: 250px; /* Space for fixed sidebar */
            min-height: 100vh;
        }}

        /* Fixed Sidebar Table of Contents */
        .toc-sidebar {{
            position: fixed;
            top: 0;
            left: 0;
            width: {side_bar_width};
            height: 100vh;
            background-color: {toc_bg_color};
            padding: 15px 10px;
            box-shadow: 1px 0 4px rgba(0, 0, 0, 0.1);
            overflow-y: auto;
            z-index: 1000;
        }}

        .toc-title {{
            font-size: 14px;
            font-weight: bold;
            color: {toc_color};
            margin-bottom: 20px;
            text-align: center;
            border-bottom: 2px solid {toc_color};
            padding-bottom: 10px;
        }}

        .toc-links {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .toc-link {{
            color: {toc_color};
            text-decoration: none;
            padding: 10px 15px;
            border-radius: 6px;
            background-color: rgba({int(toc_color[1:3], 16)}, {int(toc_color[3:5], 16)}, {int(toc_color[5:7], 16)}, 0.1);
            transition: all 0.1s ease;
            font-size: 14px;
            border-left: 3px solid transparent;
            display: block;
        }}

        .toc-link:hover {{
            background-color: {toc_color};
            color: {page_color};
            text-decoration: none;
            border-left-color: {toc_bg_color};
            transform: translateX(5px);
        }}

        .toc-link.active {{
            background-color: {toc_color};
            color: {page_color};
            border-left-color: white;
        }}

        /* Toggle button for mobile */
        .toc-toggle {{
            display: none;
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1001;
            background-color: {toc_color};
            color: {page_color};
            border: none;
            padding: 10px 15px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
        }}

        .toc-toggle:hover {{
            opacity: 0.3;
        }}

        /* Main content area */
        .main-content {{
            padding: 20px;
            min-height: 100vh;
        }}

        .gallery-container {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 10px;
            padding: 10px;
            max-width: 1200px;
            margin: 0 auto;
            background-color: {page_color};
        }}

        .gallery-item {{
            position: relative;
            width: 100%;
            border-radius: 8px;
            overflow: hidden;
            background-color: {page_color};
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .gallery-item:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }}

        .image-container {{
            position: relative;
            width: 100%;
            height: 112px;
            cursor: pointer;
        }}

        .gallery-item img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}

        .image-caption {{
            padding: 8px 10px;
            background-color: {page_color};
            border-bottom: 1px solid #e0e0e0;
            font-size: 12px;
            color: {toc_color};
            text-align: center;
            font-weight: 500;
            word-break: break-word;
        }}

        .file-list {{
            padding: 5px;
            background-color: {page_color};
            border-top: 1px solid {page_color};
        }}

        .file-link {{
            display: inline-block;
            margin: 2px 5px 2px 0;
            padding: 4px 8px;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
            transition: background-color 0.3s ease;
        }}

        .file-link:hover {{
            opacity: 0.5;
        }}

        /* File type specific colors */"""

        # Add CSS for each file type
        for ext, (class_name, color) in file_colors.items():
            html_template += f"""
        .file-link.{class_name} {{
            background-color: {color};
        }}"""

        html_template += f"""
        /* Modal styles */
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.3);
            z-index: 2000;
        }}

        .modal-content {{
            position: relative;
            max-width: 90vw;
            max-height: 90vh;
            margin: 5% auto;
            padding: 20px;
            background-color: rgba(212, 188, 150, 0.5);
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
        }}

        .modal img {{
            max-width: 100%;
            max-height: 70vh;
            display: block;
            margin: 0 auto;
        }}

        .close-btn {{
            position: absolute;
            top: 10px;
            right: 15px;
            cursor: pointer;
            font-size: 24px;
            color: #666;
            transition: opacity 0.3s ease;
        }}

        .close-btn:hover {{
            opacity: 0.8;
        }}

        h2 {{
            color: {toc_color};
            margin: 30px auto 10px auto;
            max-width: 1200px;
            font-size: 20px;
            text-transform: capitalize;
            scroll-margin-top: 20px;
        }}

        /* Responsive design */
        @media (max-width: 768px) {{
            body {{
                padding-left: 0;
            }}

            .toc-sidebar {{
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }}

            .toc-sidebar.open {{
                transform: translateX(0);
            }}

            .toc-toggle {{
                display: block;
            }}

            .main-content {{
                padding: 60px 20px 20px 20px;
            }}

            .gallery-container {{
                grid-template-columns: 1fr;
            }}

            .gallery-item {{
                margin-bottom: 20px;
            }}
        }}

        /* Scrollbar styling for webkit browsers */
        .toc-sidebar::-webkit-scrollbar {{
            width: 3px;
        }}

        .toc-sidebar::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 3px;
        }}

        .toc-sidebar::-webkit-scrollbar-thumb {{
            background: #c1c1c1;
            border-radius: 3px;
        }}

        .toc-sidebar::-webkit-scrollbar-thumb:hover {{
            background: #a8a8a8;
        }}
    </style>
</head>
<body>"""

        # Generate Mobile Toggle Button
        html_template += """
    <button class="toc-toggle" onclick="toggleSidebar()">☰ Sections</button>"""

        # Generate Fixed Sidebar Table of Contents
        section_names = sorted(gallery_data.keys())
        if section_names:
            html_template += """
    <div class="toc-sidebar" id="tocSidebar">
        <div class="toc-title">Visual Library</div>
        <div class="toc-links">"""

            for section_name in section_names:
                # Create anchor-friendly ID
                section_id = section_name.lower().replace(" ", "-").replace("_", "-")

                html_template += f"""
            <a href="#{section_id}" class="toc-link" onclick="closeSidebarOnMobile()">{section_name}</a>"""

            html_template += """
        </div>
    </div>"""

        # Main content area
        html_template += """
    <div class="main-content">"""

        # Generate gallery sections
        for section_name, items in sorted(gallery_data.items()):
            # Create anchor-friendly ID
            section_id = section_name.lower().replace(" ", "-").replace("_", "-")

            html_template += f'''
        <h2 id="{section_id}">{section_name}</h2>
        <div class="gallery-container">'''

            for item in items:
                image_info = item["image"]
                alt_text = item["basename"].replace("_", " ").title()

                html_template += f'''
            <div class="gallery-item">
                <div class="image-container">
                    <img src="{image_info["path"]}" alt="{alt_text}">
                </div>
                <div class="image-caption">
                    {image_info["name"]}
                </div>'''

                if item["other_files"]:
                    html_template += """
                <div class="file-list">"""

                    for file_info in item["other_files"]:
                        ext = file_info["extension"]
                        class_name = file_colors.get(ext, ("file", "#6c757d"))[0]

                        # Create display name for file link
                        if file_info["name"].startswith(item["basename"]):
                            display_name = ext
                        else:
                            display_name = file_info["name"]

                        html_template += f'''
                    <a href="{file_info["path"]}" class="file-link {class_name}" target="_blank">{display_name}</a>'''

                    html_template += """
                </div>"""

                html_template += """
            </div>"""

            html_template += """
        </div>"""

        # Close main content div
        html_template += """
    </div>"""

        # Add modal and JavaScript
        html_template += """

    <!-- Modal Container -->
    <div class="modal">
        <div class="modal-content">
            <span class="close-btn">×</span>
            <img id="modal-image" src="" alt="Modal Image">
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const imageContainers = document.querySelectorAll('.image-container');
            const modalImage = document.getElementById('modal-image');
            const tocLinks = document.querySelectorAll('.toc-link');

            // Open modal on image click
            imageContainers.forEach(container => {
                container.addEventListener('click', () => {
                    const img = container.querySelector('img');
                    const modal = document.querySelector('.modal');
                    modalImage.src = img.src;
                    modalImage.alt = img.alt;
                    modal.style.display = 'block';
                });
            });

            // Close modal when clicking close button
            document.querySelector('.close-btn').addEventListener('click', () => {
                document.querySelector('.modal').style.display = 'none';
            });

            // Close modal when clicking outside the modal content
            window.onclick = function(event) {
                const modal = document.querySelector('.modal');
                if (event.target == modal) {
                    modal.style.display = 'none';
                }
            };

            // Smooth scrolling for TOC links
            tocLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('href');
                    const targetElement = document.querySelector(targetId);
                    if (targetElement) {
                        targetElement.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                });
            });

            // Highlight active section in TOC
            function updateActiveSection() {
                const sections = document.querySelectorAll('h2[id]');
                const scrollPos = window.scrollY + 100;

                sections.forEach(section => {
                    const sectionTop = section.offsetTop;
                    const sectionBottom = sectionTop + section.offsetHeight;
                    const sectionId = section.getAttribute('id');
                    const tocLink = document.querySelector(`a[href="#${sectionId}"]`);

                    if (scrollPos >= sectionTop && scrollPos < sectionBottom) {
                        tocLinks.forEach(link => link.classList.remove('active'));
                        if (tocLink) tocLink.classList.add('active');
                    }
                });
            }

            // Update active section on scroll
            window.addEventListener('scroll', updateActiveSection);
            updateActiveSection(); // Initial call
        });

        // Mobile sidebar toggle functions
        function toggleSidebar() {
            const sidebar = document.getElementById('tocSidebar');
            sidebar.classList.toggle('open');
        }

        function closeSidebarOnMobile() {
            if (window.innerWidth <= 768) {
                const sidebar = document.getElementById('tocSidebar');
                sidebar.classList.remove('open');
            }
        }

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(event) {
            if (window.innerWidth <= 768) {
                const sidebar = document.getElementById('tocSidebar');
                const toggle = document.querySelector('.toc-toggle');
                
                if (!sidebar.contains(event.target) && !toggle.contains(event.target)) {
                    sidebar.classList.remove('open');
                }
            }
        });
    </script>
</body>
</html>"""

        return html_template

    try:
        # Scan the folder
        print(f"🔍 Scanning folder: {folder_to_scan}")
        gallery_data = scan_folder(folder_to_scan)

        if not gallery_data:
            print("No image files found in subfolders!")
            return None

        # Generate HTML
        print("🌿 Generating HTML...")
        html_content = generate_html(gallery_data, page_color, toc_color, toc_bg_color)

        # Write to file
        output_path = Path(folder_to_scan) / "visual_library.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Print summary
        total_items = sum(len(items) for items in gallery_data.values())
        # print("✅ Gallery created successfully!")
        print(f"- {len(gallery_data)} categories")
        print(f"- {total_items} image sets")
        print(f"- Output: {output_path}")

        return print("✅ Gallery created successfully!")

    except Exception as e:
        print(f"Error creating gallery: {e}")
        return None
