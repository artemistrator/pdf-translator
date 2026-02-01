#!/usr/bin/env python3
"""Demonstrate bbox coordinate conversion for PDF overlay generation."""

def convert_bbox_to_pdf_coords(bbox, page_height_pixels, dpi):
    """
    Convert bounding box coordinates from pixel space to PDF point space.
    
    Args:
        bbox: [x1, y1, x2, y2] in pixels (origin top-left)
        page_height_pixels: Height of page in pixels
        dpi: DPI used for rendering
        
    Returns:
        tuple: (x_pdf, y_pdf, width_pdf, height_pdf) in points
    """
    x1, y1, x2, y2 = bbox
    
    # Convert to points (1 point = 1/72 inch)
    x_pdf = x1 * 72 / dpi
    width_pdf = (x2 - x1) * 72 / dpi
    y_top_pdf = y1 * 72 / dpi  # Distance from top in points
    height_pdf = (y2 - y1) * 72 / dpi
    
    # Convert to PDF coordinate system (origin bottom-left)
    # y_pdf is the bottom coordinate of the rectangle
    y_pdf = (page_height_pixels * 72 / dpi) - y_top_pdf - height_pdf
    
    return x_pdf, y_pdf, width_pdf, height_pdf


# Example usage
if __name__ == "__main__":
    # Example: bbox from vision analysis
    bbox = [100, 200, 300, 250]  # x1, y1, x2, y2 in pixels
    page_height_pixels = 1000    # Page height in pixels
    dpi = 144                    # DPI used for PNG rendering
    
    print("Input:")
    print(f"  Bounding box (pixels): {bbox}")
    print(f"  Page height: {page_height_pixels}px")
    print(f"  DPI: {dpi}")
    
    x, y, width, height = convert_bbox_to_pdf_coords(bbox, page_height_pixels, dpi)
    
    print("\nOutput (PDF coordinates in points):")
    print(f"  X: {x:.2f} points")
    print(f"  Y (bottom): {y:.2f} points")
    print(f"  Width: {width:.2f} points")
    print(f"  Height: {height:.2f} points")
    
    print("\nRectangle coordinates:")
    print(f"  Top-left: ({x:.2f}, {y + height:.2f})")
    print(f"  Bottom-right: ({x + width:.2f}, {y:.2f})")
    
    print("\nCurl example for overlay mode:")
    print('curl -X POST "http://localhost:8001/api/generate/YOUR_JOB_ID?mode=overlay"')
    
    print("\nCurl example for HTML mode:")
    print('curl -X POST "http://localhost:8001/api/generate/YOUR_JOB_ID?mode=html"')
