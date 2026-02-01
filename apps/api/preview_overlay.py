"""Generate PNG preview with OCR overlays for instant feedback."""

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Dict, Any


def generate_preview_overlay(png_path: str, translations: Dict[str, Any], max_width: int = 600, max_height: int = 800) -> BytesIO:
    """
    Generate a PNG preview with OCR text overlays.
    
    Args:
        png_path: Path to the source PNG image
        translations: OCR translations data with boxes
        max_width: Maximum preview width
        max_height: Maximum preview height
        
    Returns:
        BytesIO buffer containing the PNG image
    """
    # Open the original image
    img = Image.open(png_path)
    
    # Calculate scaling to fit within max dimensions while preserving aspect ratio
    original_width, original_height = img.size
    scale = min(max_width / original_width, max_height / original_height, 1.0)
    
    if scale < 1.0:
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Create drawing context
    draw = ImageDraw.Draw(img)
    
    # Process each text box
    for box in translations.get("boxes", []):
        x = int(box["x"] * scale)
        y = int(box["y"] * scale)
        w = int(box["w"] * scale)
        h = int(box["h"] * scale)
        text = box["text"]
        
        # Draw white rectangle with black border
        draw.rectangle(
            [x, y, x + w, y + h],
            fill="white",
            outline="black",
            width=2
        )
        
        # Draw text (try to fit within box with padding)
        try:
            # Simple font sizing - adjust to box height
            font_size = max(8, min(int(h * 0.7), 24))
            font = ImageFont.load_default()  # Use default font for simplicity
            # Alternative: font = ImageFont.truetype("arial.ttf", font_size)
            
            # Add padding
            text_x = x + 6
            text_y = y + 2
            
            # Draw black text
            draw.text((text_x, text_y), text, fill="black", font=font)
        except Exception:
            # Fallback: draw text without specific font
            draw.text((x + 2, y + 2), text, fill="black")
    
    # Save to BytesIO buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return buffer


def img_to_bytes(img: Image.Image) -> BytesIO:
    """Convert PIL Image to BytesIO buffer."""
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
