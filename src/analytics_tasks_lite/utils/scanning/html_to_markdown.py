def html_to_markdown(html_path, output_md_path):
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    markdown = []

    # Convert headings
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        if heading:  # Ensure the heading exists
            level = int(heading.name[1])
            markdown.append(f"{'#' * level} {heading.get_text(strip=True)}")

    # Convert paragraphs
    for p in soup.find_all("p"):
        if p:
            markdown.append(p.get_text(strip=True))

    # Convert admonitions (example for "note" type)
    for admonition in soup.find_all(class_="admonition"):
        title_tag = admonition.find(class_="admonition-title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            content = admonition.get_text(strip=True).replace(title, "").strip()
            markdown.append(f"!!! {title.lower()}\n    {content}")

    # Convert links
    for a in soup.find_all("a", href=True):
        link_text = a.get_text(strip=True)
        href = a["href"]
        if link_text and href:
            markdown.append(f"[{link_text}]({href})")

    # Convert tables
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows = [
            [td.get_text(strip=True) for td in tr.find_all("td")]
            for tr in table.find_all("tr")
            if tr.find_all("td")
        ]
        if headers:
            markdown.append("| " + " | ".join(headers) + " |")
            markdown.append("|" + " --- |" * len(headers))
        for row in rows:
            markdown.append("| " + " | ".join(row) + " |")

    # Convert images
    for img in soup.find_all("img"):
        alt_text = img.get("alt", "Image")
        src = img.get("src", "")
        if src:
            markdown.append(f"![{alt_text}]({src})")

    # Convert code blocks
    for pre in soup.find_all("pre"):
        code = pre.get_text()
        if code:
            markdown.append(f"```\n{code}\n```")

    # Save to Markdown file
    with open(output_md_path, "w", encoding="utf-8") as md_file:
        md_file.write("\n\n".join(markdown))

    print(f"Markdown file saved to {output_md_path}")


if __name__ == "__main__":
    html_path = (
        r"C:/my_disk/edupunk/all_docs/site/settings/template/crisp_dm_template.html"
    )
    output_md_path = r"C:\Users\Ashut\Downloads\output.md"
    html_to_markdown(html_path, output_md_path)
