#!/usr/bin/env python3
"""Test script for 3 overlay approaches: Markdown replacement, HTML replacement, Canvas"""

import json
import shutil
from pathlib import Path
from html_render import generate_pdf_from_markdown

# Root paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PNG = PROJECT_ROOT / "page1_img1.png"
API_DIR = Path(__file__).resolve().parent

async def run_test_variant(variant_num: int, variant_name: str):
    """Run one test variant"""
    print(f"\n=== Test Variant {variant_num}: {variant_name} ===")
    
    # 1. Create job directory in the correct storage location
    from storage import storage_manager
    job_id = f"test-overlay-{variant_num}"
    job_dir = storage_manager.jobs_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Copy PNG to md_assets
    assets_dir = job_dir / "md_assets"
    assets_dir.mkdir(exist_ok=True)
    target_png = assets_dir / "page1_img1.png"
    shutil.copy2(SOURCE_PNG, target_png)
    print(f"Copied PNG to: {target_png}")
    print(f"Job directory: {job_dir}")
    
    # 3. Create ocr_translations.json
    ocr_data = {
        "page1_img1.png": {
            "boxes": [{
                "id": "1",
                "x": 100,
                "y": 100,
                "w": 200,
                "h": 40,
                "text": "IT IS TEST!!!"
            }]
        }
    }
    ocr_file = job_dir / "ocr_translations.json"
    with open(ocr_file, "w") as f:
        json.dump(ocr_data, f, indent=2)
    print(f"Created OCR data: {ocr_file}")
    
    # 4. Create markdown
    markdown_content = "![Image](md_assets/page1_img1.png)\n\nSome text below the image."
    md_file = job_dir / "layout.md"
    with open(md_file, "w") as f:
        f.write(markdown_content)
    print(f"Created markdown: {md_file}")
    
    # 5. Generate PDF and HTML
    result_pdf = job_dir / f"result_{variant_num}.pdf"
    html_file = job_dir / f"html_{variant_num}.html"
    
    try:
        # Pass variant parameter to generate_pdf_from_markdown
        await generate_pdf_from_markdown(md_file, result_pdf, variant=variant_num)
        print(f"Generated PDF: {result_pdf}")
        
        # Copy the generated HTML for inspection
        generated_html = job_dir / "markdown.html"
        if generated_html.exists():
            shutil.copy2(generated_html, html_file)
            print(f"Generated HTML: {html_file}")
        else:
            print("WARNING: markdown.html not found")
            html_file = None
            
    except Exception as e:
        print(f"ERROR in variant {variant_num}: {e}")
        return None, None
    
    return result_pdf, html_file


async def main():
    """Main test runner"""
    print("Starting overlay test with 3 variants...")
    print(f"Source PNG: {SOURCE_PNG}")
    
    if not SOURCE_PNG.exists():
        print("ERROR: Source PNG not found!")
        return
    
    results = []
    
    # Variant 1: Markdown replacement (modify html_render.py logic)
    print("\n" + "="*50)
    pdf1, html1 = await run_test_variant(1, "Markdown Replacement")
    results.append(("Variant 1 (Markdown)", pdf1, html1))
    
    # Variant 2: HTML replacement (modify html_render.py logic)
    print("\n" + "="*50)
    pdf2, html2 = await run_test_variant(2, "HTML Replacement")
    results.append(("Variant 2 (HTML)", pdf2, html2))
    
    # Variant 3: Canvas approach (would need pdf_generate.py modification)
    print("\n" + "="*50)
    pdf3, html3 = await run_test_variant(3, "Canvas Approach")
    results.append(("Variant 3 (Canvas)", pdf3, html3))
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY:")
    for name, pdf, html in results:
        status = "✅" if pdf and pdf.exists() else "❌"
        # Use absolute paths for display since files are in different locations
        pdf_path = str(pdf) if pdf and pdf.exists() else "FAILED"
        html_path = str(html) if html and html.exists() else "N/A"
        print(f"{status} {name}:")
        print(f"    PDF:  {pdf_path}")
        print(f"    HTML: {html_path}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())