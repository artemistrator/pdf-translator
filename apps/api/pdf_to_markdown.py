from pathlib import Path
import pymupdf4llm
import fitz  # PyMuPDF
import re


def pdf_to_markdown_with_assets(pdf_path: Path, job_dir: Path) -> dict:
    """
    Convert PDF to Markdown + assets using pymupdf4llm and PyMuPDF.
    Saves:
      - layout.md  (full markdown)
      - md_assets/  (directory for extracted images)
    Returns small dict with paths + basic stats + image metadata.
    
    Args:
        pdf_path: Path to input PDF file
        job_dir: Job directory where output will be saved
        
    Returns:
        dict with keys:
            - markdown_path: path to layout.md
            - assets_dir: path to md_assets directory
            - images_count: number of extracted images
            - chars: character count of markdown text
            - images: list of image metadata
    """
    # Ensure job directory exists
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Create assets directory
    assets_dir = job_dir / "md_assets"
    assets_dir.mkdir(exist_ok=True)
    
    # Extract images using PyMuPDF first
    images_metadata = []
    doc = fitz.open(pdf_path)
    
    for page_num, page in enumerate(doc):
        img_list = page.get_images()
        for img_index, img in enumerate(img_list):
            try:
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha < 4:  # not RGBA
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                img_filename = f"page{page_num+1}_img{img_index+1}.png"
                img_path = assets_dir / img_filename
                pix.save(str(img_path))
                pix = None
                
                # Get image bounding box (safely)
                try:
                    bbox = page.get_image_bbox(img)
                    bbox_coords = [float(x) for x in bbox]
                except ValueError:
                    # Fallback to page dimensions if bbox extraction fails
                    bbox_coords = [0, 0, page.rect.width, page.rect.height]
                
                images_metadata.append({
                    "page": page_num + 1,
                    "index": img_index + 1,
                    "file": img_filename,
                    "bbox": bbox_coords
                })
                
                print(f"Page {page_num+1}, Image {img_index+1}: bbox={bbox_coords}")
            except Exception as e:
                print(f"Warning: Failed to extract image {img_index+1} on page {page_num+1}: {e}")
                continue
    
    doc.close()
    
    # Convert PDF to Markdown with image extraction
    md_text = pymupdf4llm.to_markdown(
        str(pdf_path),
        image_path=str(assets_dir)
    )
    
    # Replace image placeholders with proper references
    # Find all ![.*] patterns and replace them
    def replace_image_placeholders(match):
        # This is a simple approach - in practice, you might want to match
        # the actual image filenames from pymupdf4llm
        return f"![Figure](md_assets/page{match.group(1)}_img{match.group(2)}.png)"
    
    # Try to replace placeholders (this is a simplified approach)
    # In practice, you'd need to correlate pymupdf4llm's image references
    # with the actual extracted images
    md_text = re.sub(r'!\[.*?\]\(image_(\d+)_(\d+)\.png\)', 
                     r'![Figure](md_assets/page\1_img\2.png)', md_text)
    
    # Add extracted images section if images were found
    if images_metadata:
        md_text += "\n\n## Extracted Images\n\n"
        for img_meta in images_metadata:
            md_text += f"![Figure page{img_meta['page']}_img{img_meta['index']}]"
            md_text += f"(md_assets/{img_meta['file']})\n\n"
    
    # Save Markdown to layout.md
    layout_md_path = job_dir / "layout.md"
    with open(layout_md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    
    # Count extracted images
    images_count = len(list(assets_dir.glob("*.png")))
    
    return {
        "markdown_path": str(layout_md_path),
        "assets_dir": str(assets_dir),
        "images_count": images_count,
        "chars": len(md_text),
        "images": images_metadata
    }