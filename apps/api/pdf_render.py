"""
PDF to PNG rendering utilities
"""
import fitz  # PyMuPDF
from pathlib import Path
from typing import List


def render_pdf_to_pngs(
    input_pdf_path: Path, 
    out_dir: Path, 
    max_pages: int = 2, 
    dpi: int = 144
) -> List[Path]:
    """
    Render PDF pages to PNG images
    
    Args:
        input_pdf_path: Path to input PDF file
        out_dir: Output directory for PNG files
        max_pages: Maximum number of pages to render
        dpi: Resolution in dots per inch
        
    Returns:
        List of paths to rendered PNG files
    """
    # Ensure output directory exists
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Open PDF document
    doc = fitz.open(str(input_pdf_path))
    
    rendered_pages = []
    
    # Render pages up to max_pages or document length
    for i in range(min(max_pages, doc.page_count)):
        # Load page
        page = doc.load_page(i)
        
        # Render to pixmap with specified DPI
        pix = page.get_pixmap(dpi=dpi)
        
        # Convert to PNG bytes
        png_bytes = pix.tobytes("png")
        
        # Save as page_{i+1}.png
        png_path = out_dir / f"page_{i+1}.png"
        with open(png_path, "wb") as f:
            f.write(png_bytes)
        
        rendered_pages.append(png_path)
    
    # Close document
    doc.close()
    
    return rendered_pages
