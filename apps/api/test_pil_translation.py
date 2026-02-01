#!/usr/bin/env python3
"""
PIL-based image translation test
Extracts text with OpenAI Vision, then overlays Russian translation using PIL
Works with page1_img1.png from project root
"""

import os
import sys
from pathlib import Path
import base64
from openai import OpenAI
import logging
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import json

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env", override=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_text_with_vision(image_path: Path) -> list:
    """
    Extract and translate text from image using OpenAI Vision
    """
    logger.info(f"👁️  Extracting text from {image_path.name}")
    
    # Encode image
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": """Extract ALL visible English text from this image. For each piece of text, provide:
1. The exact text as it appears
2. Its Russian translation
3. Approximate coordinates (x, y, width, height) where you think it's located

Format as JSON array with objects containing:
{
  "original": "original text",
  "translation": "russian translation", 
  "bbox": [x, y, width, height]
}

If you can't determine exact coordinates, estimate based on typical text placement."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=1000
    )
    
    # Parse response
    content = response.choices[0].message.content
    logger.info(f"✅ Vision analysis complete ({len(content)} chars)")
    
    # Extract JSON from response
    try:
        # Handle markdown code blocks
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content
        
        text_data = json.loads(json_str)
        logger.info(f"✅ Extracted {len(text_data)} text elements")
        return text_data
        
    except Exception as e:
        logger.error(f"❌ Failed to parse JSON: {e}")
        logger.error(f"Response content: {content}")
        return []

def create_translated_image_with_pil(
    original_image_path: Path, 
    text_data: list,
    output_path: Path
) -> bool:
    """
    Create translated image by overlaying Russian text on original image
    """
    logger.info(f"🎨 Creating translated image with PIL")
    
    try:
        # Open original image
        with Image.open(original_image_path) as img:
            # Convert to RGBA for transparency support
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Create drawing context
            draw = ImageDraw.Draw(img)
            
            # Try to get a good font
            try:
                # Try common system fonts
                font_sizes = [24, 20, 18, 16, 14]
                fonts_to_try = [
                    "Arial.ttf",
                    "Helvetica.ttf", 
                    "DejaVuSans.ttf",
                    "LiberationSans.ttf",
                    "arial.ttf"
                ]
                
                font = None
                for font_name in fonts_to_try:
                    try:
                        font = ImageFont.truetype(font_name, font_sizes[0])
                        break
                    except:
                        continue
                
                if not font:
                    font = ImageFont.load_default()
                    logger.warning("⚠️ Using default font - install system fonts for better results")
                    
            except Exception as e:
                font = ImageFont.load_default()
                logger.warning(f"⚠️ Font loading failed: {e}")
            
            # Overlay translated text
            for i, item in enumerate(text_data):
                if 'translation' in item and item['translation']:
                    text = item['translation']
                    bbox = item.get('bbox', [10, 10 + i*30, 200, 25])  # Default positioning
                    
                    # Extract coordinates
                    if isinstance(bbox, list) and len(bbox) >= 4:
                        x, y, width, height = bbox[:4]
                    else:
                        # Fallback positioning
                        x, y = 20, 20 + i * 40
                        width, height = 200, 30
                    
                    logger.info(f"📝 Adding text: '{text}' at ({x}, {y})")
                    
                    # Draw text with background for better visibility
                    try:
                        # Get text dimensions
                        text_bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                        
                        # Draw semi-transparent background
                        draw.rectangle([
                            x-2, y-2, 
                            x + text_width + 2, y + text_height + 2
                        ], fill=(255, 255, 255, 180))
                        
                        # Draw text
                        draw.text((x, y), text, fill=(0, 0, 0, 255), font=font)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to draw text '{text}': {e}")
                        # Simple fallback
                        draw.text((x, y), text, fill=(0, 0, 0), font=font)
            
            # Save result
            if img.mode == 'RGBA':
                # Convert back to RGB for PNG saving
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if len(img.split()) == 4 else None)
                rgb_img.save(output_path, 'PNG')
            else:
                img.save(output_path, 'PNG')
            
            logger.info(f"✅ Translated image saved: {output_path}")
            logger.info(f"📏 File size: {output_path.stat().st_size} bytes")
            return True
            
    except Exception as e:
        logger.error(f"❌ PIL processing failed: {e}")
        return False

def main():
    """
    Main test function
    """
    logger.info("🚀 PIL-BASED IMAGE TRANSLATION TEST")
    logger.info("=" * 50)
    
    # Paths
    project_root = Path(__file__).parents[2]
    original_image = project_root / "page1_img1.png"
    output_image = project_root / "page1_img1_pil_translated.png"
    
    # Check files
    if not original_image.exists():
        logger.error(f"❌ Original image not found: {original_image}")
        return False
    
    logger.info(f"✅ Found original image: {original_image}")
    logger.info(f"📏 Size: {original_image.stat().st_size} bytes")
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY not set")
        return False
    
    logger.info("✅ OpenAI API key found")
    
    # Step 1: Extract and translate text
    text_data = extract_text_with_vision(original_image)
    if not text_data:
        logger.error("❌ Failed to extract text")
        return False
    
    # Save text analysis
    text_analysis_file = project_root / "pil_text_analysis.json"
    with open(text_analysis_file, "w", encoding="utf-8") as f:
        json.dump(text_data, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Text analysis saved: {text_analysis_file}")
    
    # Display extracted text
    logger.info("\n📋 EXTRACTED TEXT:")
    for item in text_data:
        logger.info(f"  🇬🇧 {item.get('original', '')}")
        logger.info(f"  🇷🇺 {item.get('translation', '')}")
        logger.info("")
    
    # Step 2: Create translated image
    success = create_translated_image_with_pil(original_image, text_data, output_image)
    
    if success:
        logger.info("\n" + "=" * 50)
        logger.info("🎉 TEST COMPLETED SUCCESSFULLY!")
        logger.info(f"📁 Original: {original_image}")
        logger.info(f"📁 Translated: {output_image}")
        logger.info(f"📝 Text analysis: {text_analysis_file}")
        logger.info("=" * 50)
        return True
    else:
        logger.error("\n💥 TEST FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)