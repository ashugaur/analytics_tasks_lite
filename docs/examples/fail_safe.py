# %% Obfuscation

import os
import re
import base64
import tempfile


def convert_html_to_offline(
    input_html,
    output_html,
    js_libraries=None,
    verify=True,
    add_browser_check=True,
):
    if not os.path.exists(input_html):
        raise FileNotFoundError(f"Input HTML file not found at: {input_html}")

    # Normalize js_libraries to dict format
    js_lib_map = {}

    if js_libraries is None:
        raise ValueError("js_libraries parameter is required")
    elif isinstance(js_libraries, str):
        # Single file - assume it's ECharts
        js_lib_map["echarts"] = js_libraries
    elif isinstance(js_libraries, list):
        # List of files - try to auto-detect library type
        for lib_path in js_libraries:
            lib_name = os.path.basename(lib_path).lower()
            if "echarts" in lib_name:
                js_lib_map["echarts"] = lib_path
            elif "d3-sankey" in lib_name or "d3.sankey" in lib_name:
                js_lib_map["d3-sankey"] = lib_path
            elif "d3" in lib_name and "sankey" not in lib_name:
                js_lib_map["d3"] = lib_path
            else:
                # Generic name based on filename
                key = lib_name.replace(".min.js", "").replace(".js", "")
                js_lib_map[key] = lib_path
    elif isinstance(js_libraries, dict):
        js_lib_map = js_libraries
    else:
        raise ValueError("js_libraries must be str, list, or dict")

    # Verify library files exist
    for lib_name, lib_path in js_lib_map.items():
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"{lib_name} JS file not found at: {lib_path}")

    # Read the input HTML
    with open(input_html, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Find all script tags
    print("\n🔍 DEBUG: Searching for script tags in HTML...")
    import re

    all_scripts = re.findall(
        r"<script[^>]*>.*?</script>", html_content, re.DOTALL | re.IGNORECASE
    )
    print(f"    Found {len(all_scripts)} script tags total")

    # Find the echarts one specifically
    echarts_scripts = [s for s in all_scripts if "echarts" in s.lower()]
    print(f"    Found {len(echarts_scripts)} script tags containing 'echarts'")

    if echarts_scripts:
        for i, script in enumerate(echarts_scripts):
            # Show first 200 chars
            preview = script[:200].replace("\n", " ")
            print(f"    Script {i + 1}: {preview}...")

    # Try to find the EXACT cdn link
    cdn_url = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"
    if cdn_url in html_content:
        print(f"\n✅ Found exact CDN URL in HTML: {cdn_url}")

        # Find the exact script tag
        idx = html_content.find(cdn_url)
        # Go back to find the opening <script
        start = html_content.rfind("<script", max(0, idx - 200), idx)
        # Go forward to find the closing >
        end = html_content.find("</script>", idx) + len("</script>")

        if start != -1 and end != -1:
            exact_tag = html_content[start:end]
            print("\n📋 EXACT script tag found:")
            print(f"    {exact_tag}")
            print(f"\n  Tag starts at position: {start}")
            print(f"    Tag ends at position: {end}")
    else:
        print("\n❌  CDN URL NOT found in HTML")

    replaced_count = 0

    # NOW do the actual replacement
    for lib_name, lib_path in js_lib_map.items():
        # Read the library content
        with open(lib_path, "r", encoding="utf-8") as f:
            lib_content = f.read()

        embedded_script = f'<script type="text/javascript">\n/* Embedded {lib_name.upper()} Library */\n{lib_content}\n</script>'

        if lib_name == "echarts":
            # Find the EXACT tag using the debug info
            cdn_url = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"
            idx = html_content.find(cdn_url)

            if idx != -1:
                start = html_content.rfind("<script", max(0, idx - 200), idx)
                end = html_content.find("</script>", idx) + len("</script>")

                if start != -1 and end != -1:
                    exact_tag = html_content[start:end]
                    print(f"\n🔄 Replacing tag...")
                    print(f"    Removing: {exact_tag[:100]}...")

                    html_content = (
                        html_content[:start] + embedded_script + html_content[end:]
                    )
                    replaced_count += 1

                    print(f"🗸 Successfully replaced {lib_name} CDN link")
                else:
                    print("❌  Could not find script tag boundaries")
            else:
                print("❌  CDN URL not found for replacement")

    if replaced_count == 0:
        # Check if echarts is already embedded
        if (
            "Apache Software Foundation" in html_content
            and "echarts" in html_content.lower()
        ):
            print(
                "\n⚠️  Note: Echarts appears to already be embedded. Skipping replacement."
            )
        else:
            print("\n⚠️  Warning: No CDN links were replaced.")

    else:
        print(f"\n✅ Successfully replaced {replaced_count} CDN link(s)")

    # Add browser verification if requested
    if add_browser_check:
        verification_script = """
<script type="text/javascript">
// Offline Verification Check
(function() {
    'use strict';
    window.addEventListener('load', function() {
        console.log('%c🔍 Checking if libraries loaded...', 'color: #4CAF50;');
        if (typeof echarts !== 'undefined') {
            console.log('%c✅ Echarts loaded successfully', 'color: #4CAF50;');
        } else {
            console.error('%c❌ Echarts NOT loaded', 'color: #f44336;');
        }
    });
})();
</script>
"""
        body_close = html_content.rfind("</body>")
        if body_close != -1:
            html_content = (
                html_content[:body_close]
                + verification_script
                + html_content[body_close:]
            )
        else:
            html_content += verification_script

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    if verify:
        external_refs = re.findall(
            r'(?:src|href)\s*=\s*"(https?://[^"]+)"', html_content
        )
        if external_refs:
            print(
                f"\n⚠️  Warning: HTML still contains {len(external_refs)} external references(s):"
            )
            for ref in external_refs[:5]:
                print(f"  - {ref}")
            if len(external_refs) > 5:
                print(f"   ... and {len(external_refs) - 5} more")
        else:
            print("\n✅ Fully offline HTML saved")

    original_size = os.path.getsize(input_html)
    output_size = os.path.getsize(output_html)
    print(f"📊 File size: {original_size / 1024:.1f} KB → {output_size / 1024:.1f} KB")


def obfuscate_html(
    input_file,
    output_file,
    add_warning=True,
    company_name="Company Inc.",
    preserve_unicode=True,
    # Warning banner styling parameters
    banner_gradient_start="#8856a7",
    banner_gradient_end="#c23899",
    banner_text_color="white",
    banner_height="35px",
    banner_font_family="Arial, sans-serif",
    banner_font_size="10px",
    banner_font_weight="600",
    banner_box_shadow="0 2px 10px rgba(0,0,0,0.2)",
    banner_animation=True,
):
    """
    Obfuscate HTML file with Unicode character preservation

    Modern banner formatting options:
    - Gradient backgrounds for a sleek look
    - Optional animation (pulse/shimmer effect)
    - Customizable colors, fonts, and sizing
    """
    with open(input_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    encoded_content = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")
    encoding_note = "Base64 (UTF-8 preserved)" if preserve_unicode else "Base64"

    # Build modern warning banner
    warning_banner = ""
    if add_warning:
        # Animation styles
        animation_style = ""
        if banner_animation:
            animation_style = """
                animation: subtlePulse 2s ease-in-out infinite;
            """

        warning_banner = f"""
    <style>
        @keyframes subtlePulse {{
            0% {{ opacity: 0.95; }}
            50% {{ opacity: 1; box-shadow: 0 2px 15px rgba(0,0,0,0.3); }}
            100% {{ opacity: 0.95; }}
        }}
        
        @keyframes shimmer {{
            0% {{ background-position: -100% 0; }}
            100% {{ background-position: 200% 0; }}
        }}
        
        .warning-banner {{
            background: linear-gradient(135deg, {banner_gradient_start} 0%, {banner_gradient_end} 100%);
            color: {banner_text_color};
            padding: 8px 20px;
            text-align: center;
            font-family: {banner_font_family};
            font-size: {banner_font_size};
            font-weight: {banner_font_weight};
            letter-spacing: 0.5px;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 99999;
            box-shadow: {banner_box_shadow};
            backdrop-filter: blur(0px);
            {animation_style}
        }}
        
        .warning-banner strong {{
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .warning-banner .separator {{
            margin: 0 12px;
            opacity: 0.7;
            font-weight: 300;
        }}
        
        .warning-banner:hover {{
            opacity: 1;
            animation: none;
        }}
        
        .banner-spacer {{
            height: {banner_height};
        }}
        
        @media print {{
            .warning-banner {{
                display: none;
            }}
            .banner-spacer {{
                display: none;
            }}
        }}
    </style>
    <div class="warning-banner">
        <strong>⚠️  {company_name.upper()} INTERNAL USE ONLY</strong>
        <span class="separator">|</span>
        Unauthorized distribution or extraction of data is prohibited
    </div>
    <div class="banner-spacer"></div>
"""

    obfuscated_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
</head>
<body>
    <script>
        // Obfuscated content loader
        // Encoding: {encoding_note}
        (function() {{
            'use strict';

            var encodedContent = "{encoded_content}";

            try {{
                var decodedContent = atob(encodedContent);
                var bytes = new Uint8Array(decodedContent.length);
                for (var i = 0; i < decodedContent.length; i++) {{
                    bytes[i] = decodedContent.charCodeAt(i);
                }}
                var decoder = new TextDecoder('utf-8');
                var utf8Content = decoder.decode(bytes);

                document.open();
                document.write(utf8Content);
                document.close();

                setTimeout(function() {{
                    var banner = `{warning_banner}`;
                    if (banner && document.body) {{
                        document.body.insertAdjacentHTML('afterbegin', banner);
                    }}
                }}, 50);

            }} catch(e) {{
                document.body.innerHTML = '<div style="padding:20px;color:red;">Error loading content. Please contact support.</div>';
                console.error('Decoding error:', e);
            }}

            if (typeof console !== 'undefined') {{
                console.log('%c⚠️  STOP!', 'color: red; font-size: 40px; font-weight: bold;');
                console.log('%c{company_name} internal report.', 'font-size: 16px;');
                console.log('%cUnauthorized access or data extraction may violate company policy.', 'font-size: 14px;');
            }}
        }})();
    </script>
</body>
</html>'''

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(obfuscated_html)

    original_size = os.path.getsize(input_file)
    obfuscated_size = os.path.getsize(output_file)

    print("✅ Obfuscation complete!")
    print(f"   Input:  {os.path.basename(input_file)}")
    print(f"   Output: {os.path.basename(output_file)}")
    print(f"   Size:   {original_size:,} bytes → {obfuscated_size:,} bytes")
    if preserve_unicode:
        print(" ✓ Unicode characters preserved (⭐🎉💩💢🔅💥 etc.)")
    if add_warning:
        print(
            f" ✓ Warning banner added (gradient: {banner_gradient_start} → {banner_gradient_end})"
        )


def create_protected_offline_html(
    input_html,
    output_html,
    js_libraries,  # Now accepts str, list, or dict
    company_name="Company Inc.",
    preserve_unicode=True,
    add_warning=True,
    verify_offline=True,
    # Warning banner styling parameters
    banner_gradient_start="#8856a7",
    banner_gradient_end="#c23899",
    banner_text_color="white",
    banner_height="35px",
    banner_font_family="Arial, sans-serif",
    banner_font_size="10px",
    banner_font_weight="600",
    banner_box_shadow="0 2px 10px rgba(0,0,0,0.2)",
    banner_animation=True,
):
    print("=" * 70)
    print("STEP 1: Converting to OFFLINE mode...")
    print("=" * 70)

    temp_offline = tempfile.mktemp(suffix="__offline.html")

    try:
        convert_html_to_offline(
            input_html,
            temp_offline,
            js_libraries=js_libraries,
            verify=True,
            add_browser_check=True,
        )

        if verify_offline:
            with open(temp_offline, "r", encoding="utf-8") as f:
                content = f.read()

            external_refs = re.findall(
                r'<(?:script|link|img|iframe)[^>]*\s(?:src|href)\s*=\s*"(https?://[^"]+)"',
                content,
                re.IGNORECASE,
            )

            if external_refs:
                print("\n❌  ERROR: File is NOT fully offline!")
                print("   Found external dependencies (scripts/stylesheets/iframes):")
                for ref in external_refs[:10]:
                    print(f"   - {ref}")
                print("\n⚠️  Cannot obfuscate a file with external dependencies.")

                os.unlink(temp_offline)
                return False
            else:
                print("\n✅ Verification passed: No external dependencies found")
                hyperlinks = re.findall(
                    r'<a[^>]*\shref\s*=\s*"(https?://[^"]+)"', content, re.IGNORECASE
                )
                if hyperlinks:
                    print(
                        f"ℹ️ Note: found {len(hyperlinks)} external hyperlink(s) (this is OK)"
                    )

        print("\n" + "=" * 70)
        print("STEP 2: Applying OBFUSCATION (with Unicode preservation)...")
        print("=" * 70)

        obfuscate_html(
            temp_offline,
            output_html,
            add_warning=add_warning,
            company_name=company_name,
            preserve_unicode=preserve_unicode,
            banner_gradient_start=banner_gradient_start,
            banner_gradient_end=banner_gradient_end,
            banner_text_color=banner_text_color,
            banner_height=banner_height,
            banner_font_family=banner_font_family,
            banner_font_size=banner_font_size,
            banner_font_weight=banner_font_weight,
            banner_box_shadow=banner_box_shadow,
            banner_animation=banner_animation,
        )

        os.unlink(temp_offline)
        print("\n" + "=" * 70)
        print("✅ COMPLETE! File is now offline and obfuscated.")
        print("=" * 70)
        print(f" Output: {output_html}")
        print("\n💡  Test by opening in browser and checking console (F12)")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        if os.path.exists(temp_offline):
            os.unlink(temp_offline)
        return False


if __name__ == "__main__":
    success = create_protected_offline_html(
        input_html=Path(ff) / "bar\bar_chart_stacked.html",
        output_html=Path(ff) / "____tmp\test_stress_protected.html",
        js_libraries=[
        _vl_js / "echarts.min.js",
        _vl_js / "d3-sankey.min.js",
        _vl_js / "d3.v7.min.js",
        ],
        company_name="Company Inc.",
        preserve_unicode=True,
        add_warning=True,
        verify_offline=True,
        # Modern banner styling with gradient
        banner_gradient_start="#667eea",  # Modern purple-blue
        banner_gradient_end="#764ba2",  # Deep purple
        banner_text_color="white",
        banner_height="40px",
        banner_font_family="'Segoe UI', 'Roboto', Arial, sans-serif",
        banner_font_size="11px",
        banner_font_weight="600",
        banner_box_shadow="0 4px 15px rgba(0,0,0,0.2)",
        banner_animation=True,
    )
