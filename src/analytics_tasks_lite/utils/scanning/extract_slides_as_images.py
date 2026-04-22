import os.path
import comtypes.client


def extract_slides_as_images(input_folder, output_folder):
    """
    Extract PowerPoint slides as images

    Args:
    input_folder: Folder containing PowerPoint files
    output_folder: Folder to save extracted images
    """
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Get all PowerPoint files
    pptx_files = [f for f in os.listdir(input_folder) if f.endswith(".pptx")]

    # Initialize PowerPoint application
    powerpoint = comtypes.client.CreateObject("Powerpoint.Application")
    powerpoint.Visible = 1

    try:
        for pptx_file in pptx_files:
            print(f"Processing: {pptx_file}")

            # Get filename without extension
            base_name = os.path.splitext(pptx_file)[0]

            # Full path to presentation
            pptx_path = os.path.abspath(os.path.join(input_folder, pptx_file))

            # Open presentation
            presentation = powerpoint.Presentations.Open(pptx_path)

            # Export each slide
            for i, slide in enumerate(presentation.Slides, start=1):
                output_filename = f"{base_name}_{i}.png"
                output_path = os.path.join(output_folder, output_filename)

                # Export slide as image
                slide.Export(output_path, "PNG")
                print(f"  Exported: {output_filename}")

            # Close presentation
            presentation.Close()

    finally:
        # Quit PowerPoint application
        powerpoint.Quit()

    print("All slides extracted successfully!")
