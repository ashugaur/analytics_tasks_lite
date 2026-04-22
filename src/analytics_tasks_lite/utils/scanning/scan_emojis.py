import re
import os.path


def scan_emojis(path, extensions, output_file=None):
    emojis = set()
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f1e0-\U0001f1ff"  # flags (iOS)
        "\U00002500-\U00002bef"  # chinese char
        "\U00002702-\U000027b0"
        "\U00002702-\U000027b0"
        "\U000024c2-\U0001f251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2b55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"  # dingbats
        "\u3030"
        "]+",
        re.UNICODE,
    )

    files_to_scan = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if os.path.splitext(file)[1].lower() in extensions:
                files_to_scan.append(os.path.join(root, file))

    for i, file_path in enumerate(files_to_scan):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                emojis.update(emoji_pattern.findall(content))
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        print(f"Scanned {i + 1} of {len(files_to_scan)} files", end="\r")

    print()  # Newline after progress
    unique_emojis = "".join(sorted(set(emojis)))  # Ensure uniqueness
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(unique_emojis)
        print(f"Unique emojis written to {output_file}")
    return unique_emojis


if __name__ == "__main__":
    path_to_scan = "/path/to/your/directory"
    file_extensions = [".py", ".sql"]
    output_file = "scanned_emojis.txt"
    print(scan_emojis(path_to_scan, file_extensions, output_file))
