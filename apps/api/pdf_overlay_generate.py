"""PDF overlay generation using PyMuPDF - draws text over background images."""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, List
import math
import json

# Overlay policy constants
HEADINGS_SCOPE_TYPES = {"heading", "title"}
SAFE_SCOPE_TYPES = HEADINGS_SCOPE_TYPES | {"caption", "figure_caption", "label"}
MAX_W_RATIO_HEADINGS = 0.80   # Max width for headings scope
MAX_H_RATIO_HEADINGS = 0.18   # Max height for headings scope
MAX_W_RATIO_SAFE = 0.55       # Max width for safe scope
MAX_H_RATIO_SAFE = 0.10       # Max height for safe scope
MAX_AREA_RATIO_SAFE = 0.04    # Max area ratio for safe scope
MAX_PARAGRAPH_HEIGHT = 70     # Max height in pixels for paragraphs to be replaced
MIN_W_PX = 8                  # Minimum width in pixels
MIN_H_PX = 8                  # Minimum height in pixels
PAD_PX = 2                    # Padding in pixels


def should_replace_block(block: Dict[str, Any], img_width: int, img_height: int, overlay_scope: str) -> tuple[bool, str]:
    """
    Determine if a block should be replaced based on overlay scope and rules.
    
    Args:
        block: Block data with bbox and type
        img_width: Image width in pixels
        img_height: Image height in pixels
        overlay_scope: Scope mode ("headings", "safe", or "all")
        
    Returns:
        Tuple of (should_replace: bool, reason: str)
    """
    bbox = block.get("bbox", [])
    block_type = block.get("type", "paragraph").lower()
    
    if not bbox or len(bbox) != 4:
        return False, "invalid_bbox"
    
    try:
        x1, y1, x2, y2 = map(float, bbox)
        if math.isnan(x1) or math.isnan(y1) or math.isnan(x2) or math.isnan(y2):
            return False, "nan_coordinates"
        if x1 >= x2 or y1 >= y2:
            return False, "invalid_dimensions"
    except (ValueError, TypeError):
        return False, "parse_error"
    
    # Convert to integers
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    width_px = x2 - x1
    height_px = y2 - y1
    
    # Minimum size check
    if width_px < MIN_W_PX or height_px < MIN_H_PX:
        return False, "too_small"
    
    # Normalize type to lowercase
    block_type = block_type.lower()
    
    # Key rule: Always skip large/high paragraphs regardless of scope
    if block_type == "paragraph":
        if height_px >= MAX_PARAGRAPH_HEIGHT:
            return False, "paragraph_height_exceeded"
        # For small paragraphs, apply scope rules
        width_ratio = width_px / img_width
        height_ratio = height_px / img_height
        area_ratio = (width_px * height_px) / (img_width * img_height)
        
        if width_ratio <= MAX_W_RATIO_SAFE and height_ratio <= MAX_H_RATIO_SAFE and area_ratio <= MAX_AREA_RATIO_SAFE:
            # Even small paragraphs only processed in "all" scope
            if overlay_scope == "all":
                return True, "small_paragraph_in_all_scope"
            else:
                return False, "paragraph_not_allowed_in_scope"
        else:
            return False, "paragraph_too_large"
    
    # Apply scope-specific rules
    if overlay_scope == "headings":
        if block_type in HEADINGS_SCOPE_TYPES:
            width_ratio = width_px / img_width
            height_ratio = height_px / img_height
            if width_ratio <= MAX_W_RATIO_HEADINGS and height_ratio <= MAX_H_RATIO_HEADINGS:
                return True, "allowed_in_headings_scope"
            else:
                return False, "heading_too_large"
        else:
            return False, "type_not_allowed_in_headings_scope"
    
    elif overlay_scope == "safe":
        if block_type in SAFE_SCOPE_TYPES:
            width_ratio = width_px / img_width
            height_ratio = height_px / img_height
            area_ratio = (width_px * height_px) / (img_width * img_height)
            if width_ratio <= MAX_W_RATIO_SAFE and height_ratio <= MAX_H_RATIO_SAFE and area_ratio <= MAX_AREA_RATIO_SAFE:
                return True, "allowed_in_safe_scope"
            else:
                return False, "block_too_large_for_safe_scope"
        else:
            # Also allow small blocks of any type in safe scope
            width_ratio = width_px / img_width
            height_ratio = height_px / img_height
            area_ratio = (width_px * height_px) / (img_width * img_height)
            if width_ratio <= MAX_W_RATIO_SAFE and height_ratio <= MAX_H_RATIO_SAFE and area_ratio <= MAX_AREA_RATIO_SAFE:
                return True, "small_block_allowed_in_safe_scope"
            else:
                return False, "block_not_safe"
    
    elif overlay_scope == "all":
        # All scope: process everything but still protect against giant bbox
        width_ratio = width_px / img_width
        height_ratio = height_px / img_height
        area_ratio = (width_px * height_px) / (img_width * img_height)
        
        # Protection against covering faces/images (giant bbox)
        if width_ratio > 0.9 or height_ratio > 0.9 or area_ratio > 0.8:
            return False, "giant_bbox_protected"
        
        return True, "allowed_in_all_scope"
    
    else:
        return False, "invalid_scope"


def generate_overlay_pdf(
    job_dir: Path, 
    vision: Dict[str, Any], 
    dpi: int = 144, 
    debug: bool = False,
    overlay_scope: str = "headings"
) -> bytes:
    """
    Generate PDF with background images and overlaid text rectangles.
    
    Args:
        job_dir: Directory containing pages/page_*.png files
        vision: Vision data dictionary with pages and blocks
        dpi: DPI used when rendering PNG pages (default: 144)
        debug: If True, generate debug overlay with red outlines only
        overlay_scope: Scope of replacement - "headings", "safe", or "all"
        
    Returns:
        PDF content as bytes
        
    Process:
        1. For each page in vision data:
           - Load corresponding page_N.png as background
           - Create new PDF page with same dimensions
           - Insert background image
           - For each block:
             * Apply overlay scope policy
             * Validate and filter bbox
             * Scale bbox coordinates to PDF page size
             * Draw white rectangle (or red outline in debug mode)
             * Insert text using insert_textbox for proper fitting
    """
    # Create new PDF document
    doc = fitz.open()
    
    pages_dir = job_dir / "pages"
    
    # Statistics for overlay report
    stats = {
        "total_blocks": 0,
        "replaced_blocks": 0,
        "skipped_blocks": 0,
        "skip_reasons": {},
        "replaced_details": []
    }
    
    # Process each page
    for page_data in vision.get("pages", []):
        page_num = page_data["page"]
        blocks = page_data.get("blocks", [])
        
        # Load background image
        bg_image_path = pages_dir / f"page_{page_num}.png"
        if not bg_image_path.exists():
            raise FileNotFoundError(f"Background image not found: {bg_image_path}")
        
        # Get image dimensions
        bg_pix = fitz.Pixmap(str(bg_image_path))
        img_width = bg_pix.width
        img_height = bg_pix.height
        bg_pix = None  # Free memory
        
        # Calculate page size in points (1 point = 1/72 inch)
        # PDF coordinate system: origin at bottom-left
        page_width_points = img_width * 72 / dpi
        page_height_points = img_height * 72 / dpi
        
        # Create new page
        page = doc.new_page(width=page_width_points, height=page_height_points)
        
        # Insert background image (scaled to fill page)
        page.insert_image(
            fitz.Rect(0, 0, page_width_points, page_height_points),
            filename=str(bg_image_path)
        )
        
        # Calculate scaling factors
        sx = page.rect.width / img_width  # Scale factor for x coordinates
        sy = page.rect.height / img_height  # Scale factor for y coordinates
        
        # Process each block
        for idx, block in enumerate(blocks):
            stats["total_blocks"] += 1
            bbox = block.get("bbox", [])
            text = block.get("text", "")
            block_type = block.get("type", "paragraph")
            
            # Skip invalid blocks
            if not bbox or len(bbox) != 4 or not text.strip():
                stats["skipped_blocks"] += 1
                reason = "invalid_block_data"
                stats["skip_reasons"][reason] = stats["skip_reasons"].get(reason, 0) + 1
                continue
            
            # Apply overlay scope policy
            should_replace, reason = should_replace_block(block, img_width, img_height, overlay_scope)
            
            if not should_replace:
                stats["skipped_blocks"] += 1
                stats["skip_reasons"][reason] = stats["skip_reasons"].get(reason, 0) + 1
                continue
            
            # Validate bbox coordinates
            try:
                x1, y1, x2, y2 = map(float, bbox)
                # Skip if NaN or invalid coordinates
                if math.isnan(x1) or math.isnan(y1) or math.isnan(x2) or math.isnan(y2):
                    stats["skipped_blocks"] += 1
                    reason = "nan_coordinates"
                    stats["skip_reasons"][reason] = stats["skip_reasons"].get(reason, 0) + 1
                    continue
                if x1 >= x2 or y1 >= y2:  # Invalid bbox
                    stats["skipped_blocks"] += 1
                    reason = "invalid_bbox_dimensions"
                    stats["skip_reasons"][reason] = stats["skip_reasons"].get(reason, 0) + 1
                    continue
            except (ValueError, TypeError):
                stats["skipped_blocks"] += 1
                reason = "bbox_parse_error"
                stats["skip_reasons"][reason] = stats["skip_reasons"].get(reason, 0) + 1
                continue
            
            # Convert to integers
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Size sanity checks
            width_px = x2 - x1
            height_px = y2 - y1
            
            if width_px < MIN_W_PX or height_px < MIN_H_PX:
                stats["skipped_blocks"] += 1
                reason = "too_small"
                stats["skip_reasons"][reason] = stats["skip_reasons"].get(reason, 0) + 1
                continue
            
            # Clamp bbox to image boundaries
            x1 = max(0, min(x1, img_width))
            y1 = max(0, min(y1, img_height))
            x2 = max(0, min(x2, img_width))
            y2 = max(0, min(y2, img_height))
            
            # Recalculate dimensions after clamping
            width_px = x2 - x1
            height_px = y2 - y1
            
            # Ratio checks against page size
            width_ratio = width_px / img_width
            height_ratio = height_px / img_height
            
            if width_ratio > 0.95 or height_ratio > 0.95:  # Additional safety check
                stats["skipped_blocks"] += 1
                reason = "exceeds_safety_limits"
                stats["skip_reasons"][reason] = stats["skip_reasons"].get(reason, 0) + 1
                continue
            
            # Scale coordinates to PDF page size
            x1_pdf = x1 * sx
            y1_pdf = y1 * sy
            x2_pdf = x2 * sx
            y2_pdf = y2 * sy
            
            # Apply padding in PDF coordinates
            pad_x = PAD_PX * sx
            pad_y = PAD_PX * sy
            
            rect = fitz.Rect(
                x1_pdf - pad_x,
                y1_pdf - pad_y,
                x2_pdf + pad_x,
                y2_pdf + pad_y
            )
            
            # Clamp to page boundaries
            rect = rect & page.rect  # Intersection with page bounds
            
            if debug:
                # Debug mode: draw red outline only (NO FILL)
                page.draw_rect(rect, color=(1, 0, 0), width=0.5)
                # Add small debug text with block ID and type
                debug_text = f"[{block_type[:3]}] p{page_num}-b{idx}"
                page.insert_text(
                    fitz.Point(rect.x0, rect.y0 - 2),
                    debug_text,
                    fontsize=5,
                    color=(1, 0, 0)
                )
            else:
                # Normal mode: white rectangle + black text ONLY for approved blocks
                # Draw white rectangle to cover original text
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                
                # Insert text using insert_textbox for proper fitting
                font_size = 12
                min_font_size = 6
                
                # Try to fit text with decreasing font sizes
                while font_size >= min_font_size:
                    # Try inserting text with current font size
                    try:
                        # Create slightly inset rectangle for text
                        inset_rect = fitz.Rect(
                            rect.x0 + 2,
                            rect.y0 + 2,
                            rect.x1 - 2,
                            rect.y1 - 2
                        )
                        
                        # Try insert_textbox - it handles word wrapping automatically
                        rc = page.insert_textbox(
                            inset_rect,
                            text,
                            fontsize=font_size,
                            fontname="helv",  # Helvetica
                            color=(0, 0, 0),
                            align=0  # Left alignment
                        )
                        
                        # If rc >= 0, text was successfully inserted
                        if rc >= 0:
                            break
                    except:
                        pass
                    
                    font_size -= 1
                
                # If still doesn't fit, truncate text
                if font_size < min_font_size:
                    font_size = min_font_size
                    # Truncate to fit in available space
                    max_chars = max(10, int(len(text) * 0.5))  # Conservative estimate
                    if len(text) > max_chars:
                        text = text[:max_chars-3] + "..."
                    
                    # Final attempt with truncated text
                    try:
                        inset_rect = fitz.Rect(
                            rect.x0 + 2,
                            rect.y0 + 2,
                            rect.x1 - 2,
                            rect.y1 - 2
                        )
                        page.insert_textbox(
                            inset_rect,
                            text,
                            fontsize=font_size,
                            fontname="helv",
                            color=(0, 0, 0),
                            align=0
                        )
                    except:
                        # Last resort: simple text insertion at bottom
                        page.insert_text(
                            fitz.Point(rect.x0 + 2, rect.y1 - 5),
                            text[:50] + "..." if len(text) > 50 else text,
                            fontsize=font_size,
                            color=(0, 0, 0)
                        )
            
            # Record replaced block details
            stats["replaced_blocks"] += 1
            stats["replaced_details"].append({
                "page": page_num,
                "block_index": idx,
                "type": block_type,
                "bbox_px": [int(x1), int(y1), int(x2), int(y2)],
                "dimensions_px": {
                    "width": width_px,
                    "height": height_px
                },
                "replacement_reason": reason
            })
    
    # Save overlay report
    overlay_report_path = job_dir / "overlay_report.json"
    with open(overlay_report_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    # Save to bytes
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes