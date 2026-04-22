"""
slidejs - Professional Presentation Generator
Creates standalone HTML presentations with embedded charts and flexible layouts.
"""

import os
import re
import base64
from pathlib import Path
from jinja2 import Template
from datetime import datetime
from bs4 import BeautifulSoup


def embed_image_as_base64(image_path):
    """Convert image file to base64 data URI."""
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
        }
        mime_type = mime_types.get(ext, "image/png")
        base64_data = base64.b64encode(image_data).decode("utf-8")
        return f"data:{mime_type};base64,{base64_data}"
    except Exception as e:
        print(f"❌ Error encoding image {image_path}: {e}")
        return None


def read_svg_flag_file(svg_path):
    """
    Read SVG file content for inline embedding.
    Handles complex SVGs like Brazil (br.svg) by preserving internal references
    and handling custom viewBox coordinate systems.
    """
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        
        # 1. Clean up XML headers that interfere with HTML embedding
        svg_content = re.sub(r"<\?xml[^>]+\?>\s*", "", svg_content)
        svg_content = re.sub(r"<!DOCTYPE[^>]+>\s*", "", svg_content)
        
        # 2. Extract existing viewBox or create one if missing
        # We search specifically in the opening <svg> tag
        svg_tag_match = re.search(r'<svg([^>]+)>', svg_content, re.IGNORECASE)
        if svg_tag_match:
            tag_content = svg_tag_match.group(1)
            
            if "viewBox" not in tag_content:
                # Only try to inject viewBox if it's missing
                width_match = re.search(r'width\s*=\s*["\']?(\d+)', tag_content)
                height_match = re.search(r'height\s*=\s*["\']?(\d+)', tag_content)
                
                if width_match and height_match:
                    w, h = width_match.group(1), height_match.group(1)
                    new_viewbox = f' viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet"'
                    # Insert the new attributes into the tag
                    svg_content = svg_content.replace(tag_content, tag_content + new_viewbox)
                    print(f"  ✓ Injected viewBox: 0 0 {w} {h}")
        
        # 3. CRITICAL: Ensure namespaces are preserved.
        # Brazil's flag uses 'xlink:href'. If the xmlns:xlink is missing from 
        # the snippet, the stars won't render in some browsers.
        if 'xlink:href' in svg_content and 'xmlns:xlink' not in svg_content:
            svg_content = svg_content.replace('<svg', '<svg xmlns:xlink="http://www.w3.org/1999/xlink"', 1)

        return svg_content

    except Exception as e:
        print(f"❌ Error reading SVG {svg_path}: {e}")
        return None

def read_svg_file(svg_path):
    """Read SVG file content for inline embedding."""
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        svg_content = re.sub(r"<\?xml[^>]+\?>\s*", "", svg_content)
        svg_content = re.sub(r"<!DOCTYPE[^>]+>\s*", "", svg_content)

        if "viewBox" not in svg_content:
            width_match = re.search(r'width\s*=\s*["\']?(\d+)', svg_content)
            height_match = re.search(r'height\s*=\s*["\']?(\d+)', svg_content)

            if width_match and height_match:
                width = width_match.group(1)
                height = height_match.group(1)
                viewBox = f"00 {width} {height}"

                svg_content = re.sub(
                    r"<svg",
                    f'<svg viewBox="{viewBox}" preserveAspectRatio="xMidYMid meet"',
                    svg_content,
                    count=1,
                )
                print(f"  ✓ Added viewBox: {viewBox}")

        svg_content = re.sub(
            r'\s+height\s*=\s*["\'][^"\']*["\']', "", svg_content, flags=re.IGNORECASE
        )
        svg_content = re.sub(
            r'\s+height\s*=\s*["\'][^"\']*["\']', "", svg_content, flags=re.IGNORECASE
        )

        svg_content = re.sub(
            r'style\s*=\s*["\'][^"\']*width\s*:[^;"\']*(;|["\'])',
            "",
            svg_content,
            flags=re.IGNORECASE,
        )
        svg_content = re.sub(
            r'style\s*=\s*["\'][^"\']*height\s*:[^;"\']*(;|["\'])',
            "",
            svg_content,
            flags=re.IGNORECASE,
        )

        return svg_content
    except Exception as e:
        print(f"❌ Error reading SVG {svg_path}: {e}")
        return None


def read_js_library(js_path):
    """Read JavaScript library file."""
    try:
        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()
        size_kb = len(js_content) / 1024
        print(f"  ✓ Loaded: {Path(js_path).name} ({size_kb:.2f} KB)")
        return js_content
    except Exception as e:
        print(f"  ❌ Error loading {js_path}: {e}")
        return None


def extract_chart_components(chart_source, chart_index, chart_container_id):
    """
    Extract chart components with ISOLATED containers to prevent overlaps.
    UPDATED: Added theme support detection
    """
    print(f"\n  📊 Processing chart {chart_index}: {str(chart_source)[:60]}...")

    # Handle TEXT: prefix
    if isinstance(chart_source, str) and chart_source.startswith("TEXT:"):
        text_content = chart_source[5:].strip()
        print("    ✓ Text content detected")
        return {
            "type": "text",
            "container_id": chart_container_id,
            "text_content": text_content,
            "script": "",
            "styles": "",
            "cdns": [],
            "custom_tooltip_id": None,
        }

    file_path = Path(chart_source)
    file_ext = file_path.suffix.lower()

    # ✅ Handle .htmltable files
    if file_ext == ".htmltable":
        print("    ✓ HTML table file detected")
        if not file_path.exists():
            print(f"    ❌ File not found: {file_path}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                table_html = f.read().strip()

            print(f"    ✓ Loaded table: {len(table_html):,} characters")

            # Extract <script> block so slidejs can detect, namespace, and
            # register window.setChartTheme — same as ECharts HTML charts.
            import re as _re
            script_match = _re.search(
                r'<script[^>]*>(.*?)</script>', table_html, _re.DOTALL
            )
            extracted_script = script_match.group(1).strip() if script_match else ""

            # Strip the <script> from the HTML content to avoid double injection
            table_content = _re.sub(
                r'\s*<script[^>]*>.*?</script>', '', table_html, flags=_re.DOTALL
            ).strip()

            # Namespace setChartTheme so multiple tables on different slides
            # don't overwrite each other's window.setChartTheme
            has_theme_support = "window.setChartTheme" in extracted_script
            theme_function_name = None

            if has_theme_support:
                theme_function_name = f"setChartTheme_{chart_container_id}"
                extracted_script = _re.sub(
                    r'window\.setChartTheme\s*=\s*function',
                    f'window.{theme_function_name} = function',
                    extracted_script
                )
                print(f"    ✓ Theme script namespaced → {theme_function_name}")

            return {
                "type": "text",
                "container_id": chart_container_id,
                "text_content": table_content,
                "script": extracted_script,
                "styles": "",
                "cdns": [],
                "custom_tooltip_id": None,
                "supports_theme_toggle": has_theme_support,
                "theme_function_name": theme_function_name,
            }
        except Exception as e:
            print(f"    ❌ Error reading table file: {e}")
            return None

    # Handle SVG files
    if file_ext == ".svg":
        print("    ✓ SVG file detected")
        svg_content = read_svg_file(file_path)
        if not svg_content:
            return None
        return {
            "type": "svg",
            "container_id": chart_container_id,
            "svg_content": svg_content,
            "script": "",
            "styles": "",
            "cdns": [],
            "custom_tooltip_id": None,
        }

    # Handle raster images
    if file_ext in [".png", ".jpg", ".jpeg", ".gif"]:
        print(f"    ✓ Image file detected: {file_ext}")
        data_uri = embed_image_as_base64(file_path)
        if not data_uri:
            return None
        return {
            "type": "image",
            "container_id": chart_container_id,
            "image_data_uri": data_uri,
            "script": "",
            "styles": "",
            "cdns": [],
            "custom_tooltip_id": None,
        }

    # Handle HTML chart files
    if file_ext != ".html":
        print(f"    ❌ Unsupported file type: {file_ext}")
        return None

    if not file_path.exists():
        print(f"    ❌ File not found: {file_path}")
        return None

    print("    ✓ HTML chart file detected")

    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Extract CDN links
    cdns = []
    for script in soup.find_all("script", src=True):
        cdns.append(script["src"])
        print(f"      📦 Found CDN: {script['src']}")

    # Detect chart type
    is_d3 = any("d3" in cdn.lower() for cdn in cdns)
    is_echarts = any("echarts" in cdn.lower() for cdn in cdns)

    if is_d3:
        print("      🔵 D3.js chart detected")
    elif is_echarts:
        print("      🟢 ECharts chart detected")
    else:
        print("      ⚪ Generic chart detected")

    # Extract inline scripts
    inline_scripts = []
    for script in soup.find_all("script", src=False):
        if script.string and script.string.strip():
            inline_scripts.append(script.string)

    if not inline_scripts:
        print("      ⚠️ No inline scripts found")
        return None

    combined_script = "\n\n// ========== NEXT SCRIPT BLOCK ==========\n\n".join(
        inline_scripts
    )

    # === CRITICAL: Detect custom tooltip BEFORE transforming ===
    has_custom_tooltip = (
        "customTooltip" in combined_script or
        "custom-tooltip" in combined_script or
        "custom-tooltip-target" in combined_script
    )
    custom_tooltip_id = None
    uses_class_tooltip = "custom-tooltip-target" in combined_script

    if has_custom_tooltip:
        custom_tooltip_id = f"customTooltip_{chart_index}"
        print(f"      💬 Custom tooltip detected - ID: {custom_tooltip_id}")
        print(f"      📌 Uses class-based tooltip: {uses_class_tooltip}")

    # === CRITICAL: CONTAINER ISOLATION ===
    patterns = [
        # getElementById patterns
        (
            r"getElementById\s*\(\s*['\"]container['\"]\s*\)",
            f"getElementById('{chart_container_id}')",
        ),
        (
            r"getElementById\s*\(\s*['\"]chart['\"]\s*\)",
            f"getElementById('{chart_container_id}')",
        ),
        (
            r"getElementById\s*\(\s*['\"]main['\"]\s*\)",
            f"getElementById('{chart_container_id}')",
        ),
        # querySelector patterns
        (
            r"querySelector\s*\(\s*['\"]#container['\"]\s*\)",
            f"querySelector('#{chart_container_id}')",
        ),
        (
            r"querySelector\s*\(\s*['\"]#chart['\"]\s*\)",
            f"querySelector('#{chart_container_id}')",
        ),
        (
            r"querySelector\s*\(\s*['\"]#main['\"]\s*\)",
            f"querySelector('#{chart_container_id}')",
        ),
        # D3 select patterns
        (
            r'd3\.select\s*\(\s*["\']#container["\']\s*\)',
            f'd3.select("#{chart_container_id}")',
        ),
        (
            r'd3\.select\s*\(\s*["\']#chart["\']\s*\)',
            f'd3.select("#{chart_container_id}")',
        ),
        (
            r'd3\.select\s*\(\s*["\']#main["\']\s*\)',
            f'd3.select("#{chart_container_id}")',
        ),
    ]

    transformed_script = combined_script
    for pattern, replacement in patterns:
        transformed_script = re.sub(pattern, replacement, transformed_script)

    # === CRITICAL: Handle custom tooltip references ===
    if has_custom_tooltip:
        # Replace customTooltip references with scoped ID
        transformed_script = re.sub(
            r"getElementById\s*\(\s*['\"]customTooltip['\"]\s*\)",
            f"getElementById('{custom_tooltip_id}')",
            transformed_script,
        )
        transformed_script = re.sub(
            r"querySelector\s*\(\s*['\"]#customTooltip['\"]\s*\)",
            f"querySelector('#{custom_tooltip_id}')",
            transformed_script,
        )
        # Also handle variable declarations
        transformed_script = re.sub(
            r"(const|var|let)\s+customTooltip\s*=\s*document\.getElementById\s*\(\s*['\"]customTooltip['\"]\s*\)",
            f"\\1 customTooltip = document.getElementById('{custom_tooltip_id}')",
            transformed_script,
        )

    # === CRITICAL FIX: Force overflow visible for Sankey/D3 charts ===
    if is_d3:
        print("     🔧 Applying D3/Sankey overflow fixes")

        # Add CSS to force overflow visible
        d3_overflow_fix = """ 
        <style>
            #{chart_container_id},
            #{chart_container_id} svg {{
                overflow: visible !important;
            }}
        </style>
        """

        # Insert before </head> or at start of body
        if '</head>' in transformed_script:
            transformed_script = transformed_script.replace('</head>', d3_overflow_fix + '</head>')
        elif '<body>' in transformed_script:
            transformed_script = transformed_script.replace('<body>', '<body>' + d3_overflow_fix)

    # # === NEW: Handle D3 tooltips that append to body ===
    # # D3 charts often create tooltips like: d3.select("body").append("div").attr("class", "tooltip")
    # # We need to scope these to the container instead
    # if is_d3:
    #     # Replace d3.select("body").append("div") with d3.select("#container_id").append("div")
    #     # This ensures tooltips are scoped to the chart container
    #     transformed_script = re.sub(
    #         r'd3\.select\s*\(\s*["\']body["\']\s*\)\s*\.append\s*\(\s*["\']div["\']\s*\)',
    #         f'd3.select("#{chart_container_id}").append("div")',
    #         transformed_script,
    #     )
    #     # Also handle document.body selections
    #     transformed_script = re.sub(
    #         r"document\.body\.appendChild",
    #         f'document.getElementById("{chart_container_id}").appendChild',
    #         transformed_script,
    #     )
    #     print(f"      🔧 D3 tooltip scoped to container: {chart_container_id}")

    # === CRITICAL: Handle resize listeners for draggable charts ===
    # Detect if chart has updatePosition or similar functions (draggable charts)
    has_update_position = (
        "updatePosition" in transformed_script
        or "update_position" in transformed_script
    )

    if has_update_position:
        print("      🎯 Draggable chart detected - keeping resize handler as-is")
        # For draggable charts, DON'T touch anything - keep resize handlers
    else:
        # For static charts, carefully remove ONLY the window.addEventListener('resize') block
        # Don't remove any other closing braces

        # Find and remove ONLY complete addEventListener blocks
        # Pattern: entire line containing window.addEventListener('resize'...)
        lines = transformed_script.split("\n")
        filtered_lines = []
        skip_resize_block = False
        resize_depth = 0

        for i, line in enumerate(lines):
            # Check if this line contains a resize event listener
            if (
                "window.addEventListener('resize'" in line
                or 'window.addEventListener("resize"' in line
            ):
                # Check if it's a complete single-line handler
                if line.count("(") == line.count(")") and ");" in line:
                    # Single-line handler - skip entire line
                    print(f"      🧹 Removed single-line resize handler at line {i}")
                    continue
                else:
                    # Multi-line handler - skip this line AND all body lines until closing
                    print(f"      🧹 Skipped resize handler start at line {i}")
                    skip_resize_block = True
                    resize_depth = line.count("{") - line.count("}")
                    continue

            # If we're inside a multi-line resize block, skip everything until balanced
            if skip_resize_block:
                resize_depth += line.count("{") - line.count("}")
                stripped = line.strip()
                # Block ends when braces balance and we hit a closing
                if resize_depth <= 0 and stripped in ["});", "};"]:
                    print(f"      🧹 Removed resize handler closing at line {i}")
                    skip_resize_block = False
                    resize_depth = 0
                    continue
                else:
                    # Skip body lines too
                    continue

            filtered_lines.append(line)

        transformed_script = "\n".join(filtered_lines)

    transformed_script = transformed_script.strip()

    # === DETECT THEME SUPPORT ===
    has_theme_support = "window.setChartTheme" in transformed_script
    theme_function_name = None

    if has_theme_support:
        # Namespace the theme function to avoid conflicts
        theme_function_name = f"setChartTheme_{chart_container_id}"

        # Replace generic function name with namespaced version
        transformed_script = re.sub(
            r'window\.setChartTheme\s*=\s*function',
            f'window.{theme_function_name} = function',
            transformed_script
        )

        # Fix: ECharts mutates the option object in-place when setOption() is called,
        # stripping unknown fields like _darkColor/_lightColor from series objects.
        # Solution: inject a snapshot of series color metadata immediately after the
        # first myChart.setOption() call, capturing them before ECharts normalizes.
        # Then patch setChartTheme to use the snapshot for color lookups.
        option_var_match = re.search(r'(myChart\.setOption\s*\([^)]+\)\s*;)', transformed_script)
        if option_var_match:
            first_setoption = option_var_match.group(1)
            snapshot_injection = (
                "        // Snapshot _darkColor/_lightColor before ECharts normalizes option\n"
                "        var _seriesColorMeta = (option.series || []).map(function(s, i) {\n"
                "            return { _lightColor: s._lightColor, _darkColor: s._darkColor };\n"
                "        });\n"
                + first_setoption + "\n"
            )
            transformed_script = transformed_script.replace(first_setoption, snapshot_injection, 1)
            print("      🔧 Injected _seriesColorMeta snapshot after first setOption()")

            # Patch setChartTheme: replace getOption() with option,
            # replace s._darkColor/s._lightColor with snapshot lookup by index
            transformed_script = transformed_script.replace(
                'myChart.getOption()', 'option'
            )
            transformed_script = re.sub(
                r'var currentOption\s*=\s*option;\s*\n',
                '',
                transformed_script
            )
            transformed_script = transformed_script.replace(
                'currentOption.series.forEach', 'option.series.forEach'
            )
            # Replace s._darkColor / s._lightColor with snapshot lookup
            transformed_script = re.sub(
                r'var newColor\s*=\s*isDark\s*\?\s*s\._darkColor\s*:\s*s\._lightColor;',
                ('var _idx = option.series.indexOf(s);\n'
                 '                        var _meta = (_idx >= 0 && _seriesColorMeta[_idx]) ? _seriesColorMeta[_idx] : s;\n'
                 '                        var newColor = isDark ? _meta._darkColor : _meta._lightColor;'),
                transformed_script
            )
            transformed_script = re.sub(
                r'myChart\.setOption\s*\(currentOption\s*,\s*true\s*\)',
                'myChart.setOption(option, true)',
                transformed_script
            )
            print(f"      🔧 Patched setChartTheme to use _seriesColorMeta snapshot")

        print(f"      🎨 Theme support detected - function: {theme_function_name}")

    # === VALIDATION: Check for balanced braces ===
    open_braces = transformed_script.count("{")
    close_braces = transformed_script.count("}")
    if open_braces != close_braces:
        print(
            f"      ⚠️ WARNING: Unbalanced braces detected ({open_braces} open, {close_braces} close)"
        )

    # Indent the script for proper nesting inside try-catch
    indented_script = "\n".join(
        "        " + line for line in transformed_script.split("\n")
    )

    # === Tooltip fix for standard ECharts (not custom tooltips) ===
    tooltip_fix = ""
    if is_echarts and not has_custom_tooltip:
        tooltip_fix = f"""
                setTimeout(function() {{
                    const container = document.getElementById('{chart_container_id}');
                    if (!container) return;

                    container.addEventListener('mousemove', function(event) {{
                        const tooltips = document.querySelectorAll('.tooltip[style*="opacity: 1"]');

                        tooltips.forEach(function(tooltip) {{
                            tooltip.style.position = 'fixed';
                            tooltip.style.left = (event.clientX + 10) + 'px';
                            tooltip.style.top = (event.clientY - 28) + 'px';
                        }});
                    }});
                }}, 100);
        """

    # === CRITICAL FIX: Ensure tooltip_fix doesn't have unclosed blocks ===
    if tooltip_fix:
        # Count braces in tooltip_fix
        tf_open = tooltip_fix.count("{")
        tf_close = tooltip_fix.count("}")
        if tf_open != tf_close:
            print(
                f"      ⚠️ WARNING: Tooltip fix has unbalanced braces ({tf_open} open, {tf_close} close)"
            )
            tooltip_fix = ""  # Disable it if malformed

    # Build the final script WITHOUT f-string to avoid escaping issues
    script_parts = [
        f"// ===== CHART {chart_index} START ({chart_container_id}) =====\n",
        "(function() {\n",
        f"    console.log('🎨 Initializing chart {chart_index}: {chart_container_id}');\n",
        "    try {\n",
        indented_script,
        "\n",
        tooltip_fix,
        "\n        // Force resize and position update for complex/draggable charts\n",
        "        setTimeout(function() {\n",
        "            try {\n",
        f"                const container = document.getElementById('{chart_container_id}');\n",
        "                if (container && typeof myChart !== 'undefined' && myChart.resize) {\n",
        f"                    console.log('🔄 Force-resizing chart {chart_index}');\n",
        "                    myChart.resize();\n",
        "                    if (typeof updatePosition === 'function') {\n",
        f"                        console.log('📍 Updating positions for chart {chart_index}');\n",
        "                        updatePosition();\n",
        "                    }\n",
        "                }\n",
        "            } catch(resizeErr) {\n",
        f"                console.warn('⚠️ Chart {chart_index} resize warning:', resizeErr);\n",
        "            }\n",
        "        }, 500);\n",
        f"\n        console.log('✅ Chart {chart_index} loaded successfully');\n",
        "    } catch(err) {\n",
        f"        console.error('❌ Chart {chart_index} error:', err);\n",
        "        console.error('Stack:', err.stack);\n",
        "    }\n",
        "})();\n",
        f"// ===== CHART {chart_index} END =====\n",
    ]

    final_script = "".join(script_parts)

    # === FINAL VALIDATION: Count braces in final script ===
    final_open = final_script.count("{")
    final_close = final_script.count("}")
    if final_open != final_close:
        print(
            f"      ❌ ERROR: Final script has unbalanced braces ({final_open} open, {final_close} close)"
        )
        print("      This WILL cause a syntax error!")
        # Show where the imbalance might be
        print(f"      Original script: {open_braces} open, {close_braces} close")
        print("      After indenting: check debug file")

    # === FINAL VALIDATION: Check try-catch structure ===
    # Verify the try block has matching catch
    try_pattern = r"try\s*\{"
    catch_pattern = r"\}\s*catch\s*\("

    try_count = len(re.findall(try_pattern, final_script))
    catch_count = len(re.findall(catch_pattern, final_script))

    if try_count != catch_count:
        print(
            f"      ❌ ERROR: Mismatched try-catch blocks (try: {try_count}, catch: {catch_count})"
        )

    # === DEBUG: Save script to file for inspection ===
    # debug_file = Path(f"debug_chart_{chart_index}_script.js")
    # debug_file_raw = Path(f"debug_chart_{chart_index}_raw.js")

    try:
        # with open(debug_file, "w", encoding="utf-8") as f:
        #     f.write(final_script)
        # print(f"      📝 Debug script saved to: {debug_file}")

        # # Save the original transformed script before wrapping
        # with open(debug_file_raw, "w", encoding="utf-8") as f:
        #     f.write(transformed_script)
        # print(f"      📝 Raw script saved to: {debug_file_raw}")

        # ✅ COMPREHENSIVE: Validate the script with comprehensive pattern detection
        script_lines = final_script.split("\n")
        for idx, line in enumerate(script_lines, 1):
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith("//"):
                continue

            # ✅ Skip valid JavaScript patterns that look suspicious
            valid_patterns = [
                "`))",          # Template literal closing with extra parenthesis
                "`)",           # Template literal closing
                "});",          # Callback/function closing
                "}))",          # Nested callback closing
                "})",           # Object/function closing
                "};",           # Block closing with semicolon
            ]

            if stripped in valid_patterns:
                continue

            # ✅ Skip D3/jQuery method chaining patterns
            if stripped.startswith(".") and (stripped.endswith(")") or stripped.endswith(");")):
                continue

            # Check for orphaned 'if' statements
            if stripped == "if" or (
                stripped.startswith("if ") and "(" not in stripped and "{" not in line
            ):
                print(f"       ⚠️ WARNING: Suspicious 'if' at line {idx}: {line[:60]}")

            # ✅ Check for incomplete function calls, only warn if line ends with "." and does not start with "."
            if stripped.endswith(".") and not stripped.startswith("."):
                print(f"      ⚠️ WARNING: Suspicious line {idx}: {line[:60]}")

            # ✅ Check for truly unbalanced parentheses
            elif stripped.endswith(")") and not stripped.startswith("."):
                if stripped not in [")", ");", "));", "});", "})", "}))", "`))", "`)"]:
                    open_count = stripped.count("(")
                    close_count = stripped.count(")")

                    if open_count != close_count:
                        print(f"     ⚠️ WARNING: Suspicious line {idx}: {line[:60]}")

    except Exception as e:
        print(f"      ⚠️ Could not save debug script: {e}")

    # Extract custom styles
    custom_styles = []
    for style in soup.find_all("style"):
        if style.string:
            # Scope styles to this chart's container to prevent leaks
            scoped_style = f"#{chart_container_id} {{\n{style.string}\n}}"
            custom_styles.append(scoped_style)

    # === Add custom tooltip styles if needed ===
    if has_custom_tooltip:
        # Extract tooltip styles from the original HTML
        print("      🔍 DEBUG: Custom tooltip details:")
        print(f"         - Tooltip ID: {custom_tooltip_id}")
        print(f"         - Uses class-based: {uses_class_tooltip}")
        print(f"         - Will create DIV: {custom_tooltip_id is not None}")
        tooltip_style_match = re.search(
            r"#customTooltip\s*\{([^}]+)\}", html_content, re.DOTALL
        )
        if tooltip_style_match:
            tooltip_styles = tooltip_style_match.group(1).strip()
            custom_styles.append(f"#{custom_tooltip_id} {{\n    {tooltip_styles}\n}}")
            print(f"      ✓ Added custom tooltip styles for {custom_tooltip_id}")

    print(f"    ✓ Chart {chart_index} processed ({len(final_script)} chars)")

    return {
        "type": "chart",
        "container_id": chart_container_id,
        "script": final_script,
        "styles": "\n".join(custom_styles),
        "cdns": cdns,
        "is_d3": is_d3,
        "is_echarts": is_echarts,
        "custom_tooltip_id": custom_tooltip_id,
        "supports_theme_toggle": has_theme_support,
        "theme_function_name": theme_function_name,
    }


def slidejs(
    slides_config,
    output_file="presentation.html",
    template_file=None,
    page_title="Presentation",
    company_name="Company",
    default_footer="Internal Use Only",
    current_date=None,
    js_folder=Path("C:/my_disk/projects/visual_library/____settings/js"),
    slide_width=1280,
    slide_height=720,
    theme_colors=None,
    font_sizes=None,
    debug_mode=False,
    console_debug=False,
    console_level='info',
    help_text=None,
    enabled_buttons=None,
    glass_effect_slides=False,
    index_columns='auto',
    summary_items=None,
):
    """
    Generate a standalone HTML presentation with embedded charts.

    Parameters:
    -----------
    slides_config : list of dict
        Each dict defines a slide with keys:
        - layout: 'single', 'two-column', 'three-column', 'grid-2x2', etc.
        - charts: list of chart file paths or 'TEXT:...' strings
        - title: slide title
        - subtitle: slide subtitle (optional)
        - title_image: path to logo image (optional)
        - footer: footer text (optional, uses default_footer if not specified)
        - footnote: footnote text (optional)
        - chart_scale: [0.6, 0.4] for custom proportions in two-column (optional)
        - overlay: dict with 'text', 'position', 'bg_color', 'text_color', 'font_size' (optional)
        - title_font_size: override default title font size (optional)
        - title_color: override default title color (optional)
        - subtitle_font_size: override default subtitle font size (optional)
        - subtitle_color: override default subtitle color (optional)

    output_file : str
        Output HTML filename

    template_file : str
        Path to HTML template file (uses embedded template if None)

    page_title : str
        Main page title shown at top

    company_name : str
        Company name shown in top-right of each slide

    default_footer : str
        Default footer text for slides

    current_date : str
        Date string (auto-generated if None)

    js_folder : str
        Folder containing JS libraries (echarts.min.js, d3.v7.min.js, etc.)

    slide_width : int
        Slide width in pixels (default: 1280)

    slide_height : int
        Slide height in pixels (default: 720)

    theme_colors : dict
        Color overrides: {'primary': '#001965', 'text': '#333', 'muted': '#666'}

    font_sizes : dict
        Font size overrides: {'title': '36px', 'subtitle': '18px', 'body': '16px'}

    debug_mode : bool
        Show colored borders and debug labels (default: False)

    Returns:
    --------
    str : Path to generated HTML file, or None on error
    """

    print("=" * 70)
    print("🚀 slidejs - Professional Presentation Generator")
    print("=" * 70)

    # Set defaults
    if current_date is None:
        current_date = datetime.now().strftime("%d-%b-%Y")

    if theme_colors is None:
        theme_colors = {}

    # Set default help text if not provided
    if help_text is None:
        help_text = """<strong>Keyboard Shortcuts:</strong><br>
    • <strong>H</strong> = Jump to Home (first slide)<br>
    • <strong>I</strong> = Jump to Index<br>
    • <strong>Q</strong> = Quick Insights<br>
    • <strong>Arrow Keys / Space</strong> = Navigate slides<br>
    • <strong>Esc</strong> = Exit presentation mode"""

    # Set default summary items if not provided
    if summary_items is None:
        summary_items = []

    if enabled_buttons is None or enabled_buttons == "" or enabled_buttons == []:
        enabled_buttons = ['present']
    elif isinstance(enabled_buttons, str):
        try:
            enabled_buttons = json.loads(enabled_buttons)
        except:
            enabled_buttons = ['present']
    elif not isinstance(enabled_buttons, list):
        enabled_buttons = ['present']

    if 'present' not in enabled_buttons:
        enabled_buttons.append('present')

    print(f"🔵 Enabled buttons: {enabled_buttons}")

    # ── Light-mode defaults (used in :root) ──────────────────────────────────
    default_theme = {
        # Core brand / existing fields
        "primary":       "#001965",
        "text":          "#333333",
        "muted":         "#666666",
        "light":         "#999999",
        "footnote":      "#555555",
        "content_bg":    "#f9f9f9",
        "slide_bg":      "#ffffff",
        "header_border": "#e0e0e0",
        # New semantic tokens – light mode
        "bg_dark":       "hsl(34 29% 89%)",
        "bg":            "hsl(34 54% 94%)",
        "bg_light":      "hsl(34 100% 99%)",
        "text_muted":    "hsl(34 20% 26%)",
        "highlight":     "hsl(34 100% 98%)",
        "border":        "hsl(34 12% 49%)",
        "border_muted":  "hsl(34 16% 60%)",
        "secondary":     "hsl(213 62% 30%)",
        "danger":        "hsl(9 21% 41%)",
        "warning":       "hsl(52 23% 34%)",
        "success":       "hsl(147 19% 36%)",
        "info":          "hsl(217 22% 41%)",
    }

    # ── Dark-mode defaults (override variables inside body.dark-mode) ─────────
    default_theme_dark = {
        "primary":       "#4a9eff",
        "text":          "#e0e0e0",
        "muted":         "#999999",
        "light":         "#666666",
        "footnote":      "#bbbbbb",
        "content_bg":    "#252525",
        "slide_bg":      "#2d2d2d",
        "header_border": "#444444",
        # New semantic tokens – dark mode
        "bg_dark":       "hsl(28 76% 1%)",
        "bg":            "hsl(32 50% 4%)",
        "bg_light":      "hsl(34 29% 8%)",
        "text_muted":    "hsl(34 19% 68%)",
        "highlight":     "hsl(34 15% 37%)",
        "border":        "hsl(34 20% 26%)",
        "border_muted":  "hsl(35 31% 16%)",
        "secondary":     "hsl(214 78% 73%)",
        "danger":        "hsl(9 26% 64%)",
        "warning":       "hsl(52 19% 57%)",
        "success":       "hsl(146 17% 59%)",
        "info":          "hsl(217 28% 65%)",
    }

    # Merge user overrides; support flat dict OR {"light": {...}, "dark": {...}}
    if isinstance(theme_colors, dict) and "light" in theme_colors and "dark" in theme_colors:
        theme_light = {**default_theme,      **theme_colors["light"]}
        theme_dark  = {**default_theme_dark, **theme_colors["dark"]}
    else:
        theme_light = {**default_theme,      **(theme_colors or {})}
        theme_dark  = {**default_theme_dark}

    # Keep legacy `theme` alias so all existing template references still work
    theme = theme_light

    if font_sizes is None:
        font_sizes = {}

    default_fonts = {
        "title": "36px",
        "subtitle": "18px",
        "body": "16px",
        "agenda_group_heading": "16px",
        "agenda_item": "14px",
        "index_group_heading": "16px",
        "index_item": "14px"
    }

    fonts = {**default_fonts, **font_sizes}

    # NEW: pull font_family out of fonts so it can be passed to template separately
    # Default matches the current hardcoded value in the template
    font_family = fonts.pop("font_family", "Calibri, Arial, sans-serif")


    # Load JavaScript libraries
    print("\n📦 Loading JavaScript libraries...")
    js_libs = {}
    required_libs = [
        "echarts.min.js",
        "html2canvas.min.js",
        # 'jspdf.umd.min.js',
        "d3.v7.min.js",
        "d3-sankey.min.js",
    ]

    for lib_name in required_libs:
        lib_path = Path(js_folder) / lib_name
        content = read_js_library(lib_path)
        if content:
            js_libs[lib_name] = content
        else:
            print(f"  ⚠️ Warning: {lib_name} not found, some features may not work")

    total_js_size = sum(len(v) for v in js_libs.values())
    print(
        f"  ✓ Total JS: {total_js_size / 1024:.2f} KB ({total_js_size / 1024 / 1024:.2f} MB)"
    )

    # Process slides
    print("\n📊 Processing slides...")
    processed_slides = []
    all_scripts = []
    all_styles = []
    all_cdns = set()
    global_chart_index = 1
    themeable_charts = []

    for slide_idx, slide_config in enumerate(slides_config, start=1):
        print(f"\n--- Slide {slide_idx}: {slide_config.get('layout', 'single')} ---")

        chart_files = slide_config.get("charts", [])
        if not chart_files:
            print("  ⚠️ No charts specified, skipping...")
            continue

        slide_charts = []

        for chart_file in chart_files:
            # Generate unique container ID for THIS chart
            chart_container_id = f"chart_container_{global_chart_index}"

            components = extract_chart_components(
                chart_file, global_chart_index, chart_container_id
            )

            if not components:
                print("    ⚠️ Skipping chart")
                continue

            # Collect global resources
            if components["cdns"]:
                all_cdns.update(components["cdns"])
            if components["script"]:
                all_scripts.append(components["script"])
            if components["styles"]:
                all_styles.append(components["styles"])

            if components.get("supports_theme_toggle"):
                themeable_charts.append({
                    "container_id": components["container_id"],
                    "function_name": components["theme_function_name"],
                })
                print("      ✓ Added to themeable charts registry")

            slide_charts.append({
                "type": components["type"],
                "container_id": components["container_id"],
                "text_content": components.get("text_content"),
                "svg_content": components.get("svg_content"),
                "image_data_uri": components.get("image_data_uri"),
            })

            global_chart_index += 1

        if not slide_charts:
            print(f"  ⚠️ No valid charts for slide {slide_idx}")
            continue

        # Process title image if provided
        title_image_data = None
        title_image_is_svg = False
        if slide_config.get("title_image"):
            img_path = slide_config["title_image"]
            if Path(img_path).exists():
                file_ext = Path(img_path).suffix.lower()

                if file_ext == ".svg":
                    # Handle SVG separately (inline embedding)
                    title_image_data = read_svg_file(img_path)
                    title_image_is_svg = True
                    if title_image_data:
                        print("  ✓ Embedded title image (SVG - inline)")
                else:
                    # Handle raster images (base64 encoding)
                    title_image_data = embed_image_as_base64(img_path)
                    title_image_is_svg = False
                    if title_image_data:
                        print("  ✓ Embedded title image (raster - base64)")

        processed_slide = {
            "layout": slide_config.get("layout", "single"),
            "charts": slide_charts,
            "title": slide_config.get("title", ""),
            "subtitle": slide_config.get("subtitle", ""),
            "title_image": title_image_data,
            "title_image_is_svg": title_image_is_svg,
            "footer": slide_config.get("footer", default_footer),
            "footnote": slide_config.get("footnote", ""),
            "chart_scale": slide_config.get("chart_scale"),
            "overlay": slide_config.get("overlay"),
            "title_font_size": slide_config.get("title_font_size"),
            "title_color": slide_config.get("title_color"),
            "subtitle_font_size": slide_config.get("subtitle_font_size"),
            "subtitle_color": slide_config.get("subtitle_color"),
            "debug_borders": debug_mode or slide_config.get("debug_borders", False),
            "warning_strip": slide_config.get("warning_strip"),
        }

        custom_boxes_processed = []
        if slide_config.get("custom_boxes"):
            print(f"  📦 Processing {len(slide_config['custom_boxes'])} custom box(es)...")

            for box in slide_config["custom_boxes"]:
                box_id = box["box_id"]
                source_type = box["source_type"]
                source_path = box["source_path"]

                box_processed = {
                    "box_id": box_id,
                    "top": box["top"],
                    "left": box["left"],
                    "width": box["width"],
                    "height": box["height"],
                    "z_index": box["z_index"],
                    "bg_color": box["bg_color"],
                    "text_color": box["text_color"],
                    "border": box["border"],
                    "border_radius": box["border_radius"],
                    "padding": box["padding"],
                    "font_size": box["font_size"],
                    "text_align": box["text_align"],
                    "box_shadow": box["box_shadow"],
                    "opacity": box["opacity"],
                }

                # Handle different source types
                if source_type == "TEXT":
                    # Handle inline text with TEXT: prefix
                    if source_path.startswith("TEXT:"):
                        content = source_path[5:].strip()
                    else:
                        content = source_path

                    box_processed["content_type"] = "text"
                    box_processed["content"] = content
                    print(f"    ✓ Box '{box_id}': Inline text ({len(content)} chars)")

                elif source_type == "HTMLTABLE":
                    table_path = Path(source_path)
                    if not table_path.exists():
                        print(f"    ❌ Box '{box_id}': File not found: {source_path}")
                        continue

                    try:
                        import re as _re
                        with open(table_path, 'r', encoding='utf-8') as f:
                            table_html = f.read().strip()

                        # Extract and namespace the setChartTheme script so the
                        # table registers with the themeable charts system, same
                        # as Chart_Config .htmltable files.
                        script_match = _re.search(
                            r'<script[^>]*>(.*?)</script>', table_html, _re.DOTALL
                        )
                        box_script = script_match.group(1).strip() if script_match else ""

                        # Strip script from HTML content — it goes into all_scripts
                        table_content = _re.sub(
                            r'\s*<script[^>]*>.*?</script>', '', table_html, flags=_re.DOTALL
                        ).strip()

                        if "window.setChartTheme" in box_script:
                            box_fn_name = f"setChartTheme_box_{box_id}"
                            box_script = _re.sub(
                                r'window\.setChartTheme\s*=\s*function',
                                f'window.{box_fn_name} = function',
                                box_script
                            )
                            all_scripts.append(box_script)
                            themeable_charts.append({
                                "container_id": box_id,
                                "function_name": box_fn_name,
                            })
                            print(f"    ✓ Box '{box_id}': Table theme namespaced → {box_fn_name}")
                        else:
                            table_content = table_html  # no script — use full content

                        box_processed["content_type"] = "html"
                        box_processed["content"] = table_content
                        print(f"    ✓ Box '{box_id}': HTML table loaded ({len(table_content)} chars)")
                    except Exception as e:
                        print(f"    ❌ Box '{box_id}': Error reading file: {e}")
                        continue

                elif source_type == "HTML":
                    html_path = Path(source_path)
                    if not html_path.exists():
                        print(f"    ❌ Box '{box_id}': File not found: {source_path}")
                        continue

                    try:
                        with open(html_path, 'r', encoding='utf-8') as f:
                            html_content = f.read().strip()

                        box_processed["content_type"] = "html"
                        box_processed["content"] = html_content
                        print(
                            f"    ✓ Box '{box_id}': HTML loaded ({len(html_content)} chars)"
                        )
                    except Exception as e:
                        print(f"    ❌ Box '{box_id}': Error reading file: {e}")
                        continue

                elif source_type == "IMAGE":
                    img_path = Path(source_path)
                    if not img_path.exists():
                        print(f"    ❌ Box '{box_id}': Image not found: {source_path}")
                        continue

                    data_uri = embed_image_as_base64(img_path)
                    if data_uri:
                        box_processed["content_type"] = "image"
                        box_processed["content"] = data_uri
                        print(f"    ✓ Box '{box_id}': Image embedded")
                    else:
                        print(f"    ❌ Box '{box_id}': Failed to encode image")
                        continue

                # In slidejs.py, in the SVG processing section (around line 950-960)
                elif source_type == "SVG":
                    svg_path = Path(source_path)
                    if not svg_path.exists():
                        print(f"    ❌ Box '{box_id}': SVG not found: {source_path}")
                        continue
                    
                    svg_content = read_svg_flag_file(svg_path)
                    if svg_content:
                        # Add XML namespace and ensure references work
                        from xml.dom import minidom
                        import re
                        
                        # Parse and namespace all IDs to make them unique
                        try:
                            # Add a unique prefix for this box
                            prefix = f"{box_id}_"
                            
                            # Find all IDs in the SVG
                            id_map = {}
                            def add_id(match):
                                old_id = match.group(1)
                                new_id = prefix + old_id
                                id_map[old_id] = new_id
                                return f'id="{new_id}"'
                            
                            # First pass: rename all IDs
                            svg_content = re.sub(r'id="([^"]+)"', add_id, svg_content)
                            
                            # Second pass: update all xlink:href references
                            def update_ref(match):
                                old_ref = match.group(1)
                                if old_ref.startswith('#'):
                                    old_id = old_ref[1:]
                                    if old_id in id_map:
                                        return f'xlink:href="#{id_map[old_id]}"'
                                return match.group(0)
                            
                            svg_content = re.sub(r'xlink:href="([^"]+)"', update_ref, svg_content)
                            
                            # Also handle href without xlink prefix
                            svg_content = re.sub(r'href="([^"]+)"', update_ref, svg_content)
                            
                            # Ensure xlink namespace is present
                            if 'xmlns:xlink' not in svg_content:
                                svg_content = svg_content.replace(
                                    '<svg',
                                    '<svg xmlns:xlink="http://www.w3.org/1999/xlink"'
                                )
                            
                            print(f"    ✓ Box '{box_id}': Namespaced {len(id_map)} IDs (prefix: {prefix})")
                            
                            box_processed["content_type"] = "html"
                            box_processed["content"] = svg_content
                            print(f"    ✓ Box '{box_id}': SVG embedded with namespaced IDs")
                            
                        except Exception as e:
                            print(f"    ⚠️  Box '{box_id}': Namespacing failed ({e}), using raw SVG")
                            box_processed["content_type"] = "html"
                            box_processed["content"] = svg_content
                    else:
                        print(f"    ❌ Box '{box_id}': Failed to read SVG")
                        continue

                else:
                    print(f"    ⚠️  Box '{box_id}': Unknown source_type '{source_type}'")
                    continue

                custom_boxes_processed.append(box_processed)

        processed_slide = {
            "layout": slide_config.get("layout", "single"),
            "charts": slide_charts,
            "title": slide_config.get("title", ""),
            "subtitle": slide_config.get("subtitle", ""),
            "title_image": title_image_data,
            "title_image_is_svg": title_image_is_svg,
            "footer": slide_config.get("footer", default_footer),
            "footnote": slide_config.get("footnote", ""),
            "chart_scale": slide_config.get("chart_scale"),
            "overlay": slide_config.get("overlay"),
            "title_font_size": slide_config.get("title_font_size"),
            "title_color": slide_config.get("title_color"),
            "subtitle_font_size": slide_config.get("subtitle_font_size"),
            "subtitle_color": slide_config.get("subtitle_color"),
            "debug_borders": debug_mode or slide_config.get("debug_borders", False),
            "warning_strip": slide_config.get("warning_strip"),
            "custom_boxes": custom_boxes_processed,
            "deep_dives": slide_config.get("deep_dives", []),
        }

        processed_slides.append(processed_slide)
        print(f"  ✓ Slide {slide_idx} processed ({len(slide_charts)} chart(s))")

    if not processed_slides:
        print("\n❌ No valid slides to generate!")
        return None

    print(f"\n✅ Processed {len(processed_slides)} slide(s)")

    # Read or use embedded template
    if template_file and Path(template_file).exists():
        print(f"\n📄 Loading template: {template_file}")
        with open(template_file, "r", encoding="utf-8") as f:
            template_str = f.read()
    else:
        print("\n📄 Using embedded template")
        # Template will be embedded here (we'll create a separate template file)
        template_str = get_embedded_template()

    # Render template
    print("\n🎨 Rendering presentation...")
    template = Template(template_str)

    print("\n🎨 SLIDES SENT TO TEMPLATE:")
    for i, slide in enumerate(processed_slides, 1):
        print(f"   Slide {i}:")
        print(f"      title: {repr(slide.get('title'))}")
        print(f"      subtitle: {repr(slide.get('subtitle'))}")
        print(f"      has charts: {len(slide.get('charts', []))}")
        print(f"      has custom_boxes: {len(slide.get('custom_boxes', []))}")
        print(f"      has deep_dives: {len(slide.get('deep_dives', []))}")

    html_output = template.render(
        page_title=page_title,
        company_name=company_name,
        default_footer=default_footer,
        current_date=current_date,
        slides=processed_slides,
        combined_scripts="\n\n".join(all_scripts),
        custom_styles="\n".join(all_styles),
        cdns=sorted(all_cdns),
        echarts_js=js_libs.get("echarts.min.js", ""),
        html2canvas_js=js_libs.get("html2canvas.min.js", ""),
        d3_js=js_libs.get("d3.v7.min.js", ""),
        d3_sankey_js=js_libs.get("d3-sankey.min.js", ""),
        slide_width=slide_width,
        slide_height=slide_height,
        theme=theme_light,
        theme_dark=theme_dark,
        fonts=fonts,
        font_family=font_family,
        debug_mode=debug_mode,
        console_debug=console_debug,
        console_level=console_level,
        help_text=help_text,
        enabled_buttons=enabled_buttons,
        glass_effect_slides=glass_effect_slides,
        themeable_charts=themeable_charts,
        index_columns=index_columns,
        summary_items=summary_items,
    )

    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_output)

    file_size = len(html_output)
    print(f"\n✅ Generated: {output_file}")
    print(
        f"   Size: {file_size:,} bytes ({file_size / 1024:.2f} KB, {file_size / 1024 / 1024:.2f} MB)"
    )
    print(f"   Slides: {len(processed_slides)}")
    print(f"   Charts: {global_chart_index - 1}")
    print(f"   Themeable Charts: {len(themeable_charts)}")
    print("=" * 70)

    return output_file


def get_embedded_template():
    """
    Returns the embedded HTML template.
    Reads from slidejs_template.html in the same directory.
    """
    # Get the directory where slidejs.py is located
    script_dir = Path(__file__).parent
    # template_path = Path(
    #     "C:/my_disk/projects/visual_library/slidejs/slidejs_template.html"
    # )
    template_path = script_dir / "slidejs_template.html"

    if not template_path.exists():
        raise FileNotFoundError(
            f"Template file not found: {template_path}\n"
            f"Please ensure slidejs_template.html is available"
        )

    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


# Example usage
# if __name__ == "__main__":
#     slides_config = [
#         {
#             'layout': 'single',
#             'charts': ['chart1.html'],
#             'title': 'Test Slide',
#             'subtitle': 'Testing chart isolation',
#             'overlay': {
#                 'text': 'DRAFT',
#                 'position': 'top-right',
#                 'bg_color': 'rgba(220, 53, 69, 0.9)',
#                 'text_color': 'white',
#                 'font_size': '11px'
#             }
#         }
#     ]

#     output = slidejs(
#         slides_config=slides_config,
#         output_file="test_presentation.html",
#         page_title="Test Presentation",
#         js_folder="js",
#         debug_mode=True
#     )

#     if output:
#         print(f"\n✨ Open {output} in your browser!")