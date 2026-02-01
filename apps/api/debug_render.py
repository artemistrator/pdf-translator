"""Debug rendering utilities for visualizing bounding boxes on page images."""

from pathlib import Path
from typing import Dict, Any
from PIL import Image, ImageDraw, ImageFont
import json


def render_debug_page_png(job_dir: Path, vision: Dict[str, Any], page_num: int) -> Path:
    """
    Render debug page image with bounding boxes and labels.
    
    Args:
        job_dir: Job directory containing pages/
        vision: Vision analysis data with pages and blocks
        page_num: Page number (1-indexed)
        
    Returns:
        Path to generated debug image file
        
    Process:
        1. Load pages/page_{page_num}.png as base image
        2. Draw red rectangles for each bbox
        3. Add text labels with block ID and type
        4. Save as pages/debug_page_{page_num}.png
    """
    pages_dir = job_dir / "pages"
    input_image_path = pages_dir / f"page_{page_num}.png"
    output_image_path = pages_dir / f"debug_page_{page_num}.png"
    
    # Check if input image exists
    if not input_image_path.exists():
        raise FileNotFoundError(f"Input image not found: {input_image_path}")
    
    # Load base image
    base_image = Image.open(input_image_path)
    draw = ImageDraw.Draw(base_image)
    
    # Try to get a font (fallback to default if not available)
    try:
        # Try to use a system font
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
    except:
        try:
            # Fallback to default font
            font = ImageFont.load_default()
        except:
            # Last resort - no font
            font = None
    
    # Find the page data
    page_data = None
    for page in vision.get("pages", []):
        if page.get("page") == page_num:
            page_data = page
            break
    
    if not page_data:
        # Save original image as debug (no blocks found)
        base_image.save(output_image_path)
        return output_image_path
    
    # Draw bounding boxes and labels
    blocks = page_data.get("blocks", [])
    for idx, block in enumerate(blocks):
        bbox = block.get("bbox", [])
        block_type = block.get("type", "unknown")
        text = block.get("text", "")
        
        # Skip invalid blocks
        if not bbox or len(bbox) != 4 or not text.strip():
            continue
        
        try:
            x1, y1, x2, y2 = map(int, bbox)
        except (ValueError, TypeError):
            continue
        
        # Draw red rectangle
        draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
        
        # Create label text
        block_id = f"p{page_num}-b{idx}"
        label_text = f"{block_id} [{block_type}]"
        
        # Draw label background (semi-transparent)
        if font:
            text_width = draw.textlength(label_text, font=font)
            text_height = 16  # Approximate height
            draw.rectangle([
                x1, y1 - text_height - 4,
                x1 + text_width + 4, y1
            ], fill=(255, 255, 255, 180))
            
            # Draw label text
            draw.text([x1 + 2, y1 - text_height - 2], label_text, fill="red", font=font)
    
    # Save debug image
    base_image.save(output_image_path)
    base_image.close()
    
    return output_image_path


def render_all_debug_pages(job_dir: Path, vision: Dict[str, Any]) -> int:
    """
    Render debug images for all pages.
    
    Args:
        job_dir: Job directory
        vision: Vision analysis data
        
    Returns:
        Number of debug pages generated
    """
    pages_dir = job_dir / "pages"
    debug_count = 0
    
    # Get all page numbers from vision data
    page_numbers = []
    for page in vision.get("pages", []):
        page_num = page.get("page")
        if page_num and isinstance(page_num, int) and page_num > 0:
            page_numbers.append(page_num)
    
    # Render debug image for each page
    for page_num in sorted(page_numbers):
        try:
            render_debug_page_png(job_dir, vision, page_num)
            debug_count += 1
        except Exception as e:
            # Log error but continue with other pages
            print(f"Warning: Failed to render debug page {page_num}: {e}")
            continue
    
    return debug_count