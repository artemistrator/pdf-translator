"""HTML rendering utilities for vision analysis results."""

import json
import base64
from typing import Dict, Any, Optional, Union
from pathlib import Path


def load_translations(job_dir, image_name):
    """Simple fallback for loading translations"""
    trans_file = job_dir / "ocr_translations.json"
    if not trans_file.exists():
        return []
    
    try:
        data = json.loads(trans_file.read_text())
        return data.get(image_name, {}).get("boxes", [])
    except:
        return []


def vision_to_html(vision: Dict[str, Any], title: str, job_dir: Optional[Path] = None, embed_page_images: bool = False) -> str:
    """
    Convert vision analysis result to readable HTML.
    
    Args:
        vision: Vision analysis dictionary
        title: Document title
        job_dir: Job directory containing pages/page_N.png files (required if embed_page_images=True)
        embed_page_images: Whether to embed page PNG images as base64 data URLs
        
    Returns:
        HTML string ready for PDF generation
    """
    if embed_page_images and job_dir is None:
        raise ValueError("job_dir is required when embed_page_images=True")
    
    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"    <title>{title}</title>",
        '    <style>',
        "        @page { size: A4; margin: 10mm; }",
        "        @media print {",
        "            .page { page-break-after: always; break-after: page; }",
        "            .page:last-child { page-break-after: auto; break-after: auto; }",
        "        }",
        "        body {",
        "            font-family: Arial, sans-serif;",
        "            line-height: 1.6;",
        "            color: #333;",
        "            margin: 0;",
        "            padding: 0;",
        "        }",
        "        h1 {",
        "            color: #2c3e50;",
        "            border-bottom: 2px solid #3498db;",
        "            padding: 10px 20px;",
        "            margin: 0 0 20px 0;",
        "        }",
        "        .page {",
        "            width: 210mm;",
        "            margin: 0 auto 20mm auto;",
        "            padding: 0;",
        "            box-sizing: border-box;",
        "        }",
        "        .page-image {",
        "            width: 100%;",
        "            text-align: center;",
        "            margin: 0;",
        "            padding: 0;",
        "        }",
        "        .page-img {",
        "            width: 100%;",
        "            height: auto;",
        "            display: block;",
        "            margin: 0;",
        "            padding: 0;",
        "        }",
        "        .page-text {",
        "            margin-top: 10mm;",
        "            padding: 0 10mm;",
        "            box-sizing: border-box;",
        "        }",
        "        .block {",
        "            margin-bottom: 15px;",
        "        }",
        "        .heading {",
        "            font-size: 18px;",
        "            font-weight: bold;",
        "            color: #2c3e50;",
        "            margin: 10px 0;",
        "        }",
        "        .paragraph {",
        "            margin: 8px 0;",
        "            text-align: justify;",
        "        }",
        "        .list {",
        "            margin: 8px 0;",
        "            padding-left: 20px;",
        "        }",
        "        .list-item {",
        "            margin: 4px 0;",
        "        }",
        "        .footer {",
        "            margin-top: 30px;",
        "            padding-top: 10px;",
        "            border-top: 1px solid #bdc3c7;",
        "            font-size: 12px;",
        "            color: #7f8c8d;",
        "            text-align: center;",
        "        }",
        "    </style>",
        "</head>",
        "<body>",
        f"    <h1>{title}</h1>",
    ]
    
    # Process pages
    pages = vision.get("pages", [])
    for i, page in enumerate(pages, 1):
        html_parts.append(f'    <section class="page">')
        
        # Embed page image if requested
        if embed_page_images and job_dir:
            page_img_path = job_dir / "pages" / f"page_{i}.png"
            if page_img_path.exists():
                try:
                    with open(page_img_path, "rb") as f:
                        img_bytes = f.read()
                        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                        html_parts.append(f'        <div class="page-image">')
                        html_parts.append(f'            <img class="page-img" src="data:image/png;base64,{img_base64}" />')
                        html_parts.append(f'        </div>')
                except Exception as e:
                    # Silently fail if image can't be read
                    pass
        
        # Add text container
        html_parts.append('        <div class="page-text">')
        
        # Process blocks in order
        blocks = page.get("blocks", [])
        for block in blocks:
            block_type = block.get("type", "paragraph")
            text = block.get("text", "")
            
            if not text.strip():
                continue
                
            if block_type == "heading":
                html_parts.append(f'            <div class="block"><div class="heading">{_escape_html(text)}</div></div>')
            elif block_type == "list":
                items = text.split("\n")
                html_parts.append('            <div class="block"><ul class="list">')
                for item in items:
                    if item.strip():
                        html_parts.append(f'                <li class="list-item">{_escape_html(item.strip())}</li>')
                html_parts.append("            </ul></div>")
            else:  # paragraph
                html_parts.append(f'            <div class="block"><div class="paragraph">{_escape_html(text)}</div></div>')
        
        html_parts.append('        </div>')  # close page-text
        html_parts.append("    </section>")  # close page
    
    # Add footer
    html_parts.append('    <div class="footer">')
    html_parts.append("        Generated by PDF Translator")
    html_parts.append("    </div>")
    
    html_parts.append("</body>")
    html_parts.append("</html>")
    
    return "\n".join(html_parts)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


async def generate_pdf_from_markdown(markdown_path: Path, output_pdf: Path, variant: int = 1):
    """
    Convert Markdown to PDF via HTML + Playwright with OCR text overlays.
    
    Args:
        markdown_path: Path to markdown file
        output_pdf: Output PDF path
        variant: Overlay approach (1=Markdown replacement, 2=HTML replacement, 3=Canvas)
    """
    import markdown2
    import os
    import re
    import json
    from storage import storage_manager
    
    # 1) Read markdown content
    markdown_content = markdown_path.read_text(encoding='utf-8')
    
    # 2) Parse images from markdown to get original image names
    image_matches = re.findall(r'!\[.*?\]\((.*?)\)', markdown_content)
    image_names = [img for img in image_matches if img.startswith('md_assets/')]
    image_names = [img.replace('md_assets/', '') for img in image_names]
    
    # 3) Get job directory and job ID
    job_dir = markdown_path.parent
    job_id = job_dir.name  # Assuming job_dir is jobs/{job_id}
    
    # 4) Get API base URL
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    prefix = f'{api_base}/api/md-asset/{job_id}/'
    
    # 5) Load OCR translations if they exist
    ocr_translations = {}
    try:
        ocr_translations = storage_manager.load_ocr_translations(job_id)
    except Exception as e:
        print(f"Warning: Could not load OCR translations: {e}")
    
    # 6) Apply variant-specific overlay logic
    markdown_with_overlays = markdown_content
    
    if variant == 1:
        # VARIANT 1: Markdown replacement before HTML conversion
        print("Using Variant 1: Markdown replacement")
        for image_name in image_names:
            if image_name in ocr_translations:
                # Get image dimensions
                img_path = job_dir / "md_assets" / image_name
                if img_path.exists():
                    try:
                        from PIL import Image
                        with Image.open(img_path) as img:
                            img_width, img_height = img.size
                    except:
                        img_width, img_height = 800, 600  # fallback
                else:
                    img_width, img_height = 800, 600  # fallback
                
                # Build overlay HTML with white background + black text
                overlay_html = ""
                image_data = ocr_translations[image_name]
                if 'boxes' in image_data:
                    for box in image_data['boxes']:
                        x = box['x']
                        y = box['y']
                        w = box['w']
                        h = box['h']
                        text = box['text']
                        font_size = box.get('fontSize', box.get('font_size', max(8, min(h * 0.8, 24))))
                        
                        overlay_html += f'''
<div class="ov" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;font-size:{font_size}px">
{text}
</div>'''
                
                # Replace with proper container
                pattern = rf'!\[.*?\]\(md_assets/{re.escape(image_name)}\)'
                replacement = f'''<div class="img-wrap" style="width:{img_width}px;height:{img_height}px">
  <img class="img" src="md_assets/{image_name}" style="width:{img_width}px;height:{img_height}px" />
  {overlay_html}
</div>'''
                markdown_with_overlays = re.sub(pattern, replacement, markdown_with_overlays)
    
    elif variant == 2:
        # VARIANT 2: HTML replacement after markdown2 conversion
        print("Using Variant 2: HTML replacement")
        # Do nothing here, handle in HTML section below
        pass
    
    elif variant == 3:
        # VARIANT 3: Canvas approach (handled in pdf_generate.py)
        print("Using Variant 3: Canvas approach")
        # Do nothing here, handle in pdf_generate.py
        pass
    
    else:
        # Default behavior (existing logic)
        for image_name in image_names:
            # Check if we have OCR data for this image
            if image_name in ocr_translations:
                # Get image dimensions
                img_path = job_dir / "md_assets" / image_name
                if img_path.exists():
                    try:
                        from PIL import Image
                        with Image.open(img_path) as img:
                            img_width, img_height = img.size
                    except:
                        img_width, img_height = 800, 600  # fallback
                else:
                    img_width, img_height = 800, 600  # fallback
                
                # Build overlay HTML with white background + black text
                overlay_html = ""
                image_data = ocr_translations[image_name]
                if 'boxes' in image_data:
                    for box in image_data['boxes']:
                        x = box['x']
                        y = box['y']
                        w = box['w']
                        h = box['h']
                        text = box['text']
                        font_size = box.get('fontSize', box.get('font_size', max(8, min(h * 0.8, 24))))
                        
                        overlay_html += f'''
<div class="ov" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;font-size:{font_size}px">
{text}
</div>'''
                
                # Replace with proper container
                pattern = rf'!\[.*?\]\(md_assets/{re.escape(image_name)}\)'
                replacement = f'''<div class="img-wrap" style="width:{img_width}px;height:{img_height}px">
  <img class="img" src="md_assets/{image_name}" style="width:{img_width}px;height:{img_height}px" />
  {overlay_html}
</div>'''
                markdown_with_overlays = re.sub(pattern, replacement, markdown_with_overlays)
    
    # 7) Convert markdown with overlays to HTML (extras=['tables'] for GFM tables)
    html_content = markdown2.markdown(markdown_with_overlays, extras=['tables'])
    
    # 8) Apply variant-specific HTML modifications
    if variant == 2:
        # VARIANT 2: HTML replacement after markdown2
        print("Applying Variant 2 HTML replacement")
        # Do nothing for now, handled in markdown processing above
        pass
    
    # 9) Create HTML template
    html_template = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40mm;
            line-height: 1.6;
            position: relative;
        }
        .img-wrap {
            position: relative;
            display: inline-block;
        }
        .img {
            display: block;
        }
        .ov {
            position: absolute;
            background: white;
            color: black;
            padding: 2px 6px;
            font-size: 18px;
            line-height: 1.1;
            border: 1px solid #000;
            box-sizing: border-box;
            white-space: pre-wrap;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 24px;
            margin-bottom: 16px;
        }
        p {
            margin: 0 0 16px 0;
        }
        ul, ol {
            margin: 0 0 16px 0;
            padding-left: 30px;
        }
        li {
            margin: 4px 0;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: monospace;
        }
        pre {
            background-color: #f4f4f4;
            padding: 12px;
            border-radius: 5px;
            overflow-x: auto;
        }
        pre code {
            background: none;
            padding: 0;
        }
        blockquote {
            border-left: 4px solid #ddd;
            margin: 0 0 16px 0;
            padding: 0 16px;
            color: #666;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: #f8f8f8;
            font-weight: bold;
        }
    </style>
</head>
<body>
''' + html_content + '''
</body>
</html>
'''

    # 10) Replace ALL relative asset paths with absolute API URLs
    # Handle src attributes (both double and single quotes)
    html_with_assets = html_template.replace('src="md_assets/', f'src="{prefix}')
    html_with_assets = html_with_assets.replace("src='md_assets/", f"src='{prefix}")
    html_with_assets = html_with_assets.replace('src="./md_assets/', f'src="{prefix}')
    html_with_assets = html_with_assets.replace("src='./md_assets/", f"src='{prefix}")
    
    # Handle href attributes for links to assets (both double and single quotes)
    html_with_assets = html_with_assets.replace('href="md_assets/', f'href="{prefix}')
    html_with_assets = html_with_assets.replace("href='md_assets/", f"href='{prefix}")
    html_with_assets = html_with_assets.replace('href="./md_assets/', f'href="{prefix}')
    html_with_assets = html_with_assets.replace("href='./md_assets/", f"href='{prefix}")
    
    # 11) For Variant 3: Add Canvas initialization script
    if variant == 3:
        print("Adding Variant 3 Canvas script")
        # Inject canvas overlay script
        canvas_script = """
<script>
window.overlayCanvas = async (imgSrc, text, x, y, w, h) => {
  const img = await new Promise(r=> {const i=new Image();i.onload=()=>r(i);i.src=imgSrc});
  const canvas = document.createElement('canvas');
  canvas.width = img.width; canvas.height = img.height;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0);
  ctx.fillStyle = 'red'; ctx.fillText(text, x, y);
  return canvas.toDataURL();
}
</script>
"""
        # Insert script before </head>
        html_with_assets = html_with_assets.replace('</head>', canvas_script + '</head>')
    
    # 12) Debug: Log first 5 img src attributes to verify URLs
    import logging
    logger = logging.getLogger(__name__)
    img_sources = re.findall(r'<img[^>]+src=["\']([^"\']+)', html_with_assets)[:5]
    logger.info(f"First 5 image sources in HTML: {img_sources}")
    
    # 13) Save intermediate HTML for debugging
    html_path = job_dir / "markdown.html"
    html_path.write_text(html_with_assets, encoding='utf-8')
    
    # 14) Generate PDF using Playwright with file navigation
    from pdf_generate import generate_pdf_from_html_file
    await generate_pdf_from_html_file(html_path, output_pdf)
