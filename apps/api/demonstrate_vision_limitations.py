#!/usr/bin/env python3
"""
Enhanced OpenAI Vision test that demonstrates the actual capabilities
and limitations of current OpenAI models for image translation
"""

import os
import sys
from pathlib import Path
import base64
from openai import OpenAI
import logging
from dotenv import load_dotenv
import json

# Add the api directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env", override=True)
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demonstrate_vision_capabilities():
    """
    Demonstrate what OpenAI Vision models can actually do
    """
    logger.info("🔍 DEMONSTRATING OPENAI VISION CAPABILITIES")
    logger.info("=" * 60)
    
    # Define paths
    project_root = Path(__file__).parents[2]
    test_image_path = project_root / "page1_img1.png"
    
    if not test_image_path.exists():
        logger.error("❌ Test image not found")
        return False
    
    # Encode image
    with open(test_image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Test 1: Text extraction and translation
    logger.info("\n📝 TEST 1: Text Extraction and Translation")
    logger.info("-" * 40)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Carefully examine this image. Extract ALL visible English text exactly as it appears. Then provide the Russian translation for each piece of text. Format your response as a JSON object with 'original_text' and 'russian_translation' fields."
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
        
        text_analysis = response.choices[0].message.content
        logger.info(f"✅ Text Analysis Response ({len(text_analysis)} chars):")
        logger.info(f"{text_analysis}")
        
        # Save text analysis
        analysis_file = project_root / "vision_text_analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(text_analysis)
        logger.info(f"💾 Text analysis saved to: {analysis_file}")
        
    except Exception as e:
        logger.error(f"❌ Text analysis failed: {e}")
        return False
    
    # Test 2: Image modification capability check
    logger.info("\n🎨 TEST 2: Image Modification Capability")
    logger.info("-" * 40)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Can you generate a modified version of this image where the English text is replaced with Russian text? If yes, return the modified image as base64. If not, explain why you cannot do this."
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
            max_tokens=500
        )
        
        capability_response = response.choices[0].message.content
        logger.info(f"✅ Capability Response:")
        logger.info(f"{capability_response}")
        
        # Save capability analysis
        capability_file = project_root / "vision_capability_analysis.txt"
        with open(capability_file, "w", encoding="utf-8") as f:
            f.write(capability_response)
        logger.info(f"💾 Capability analysis saved to: {capability_file}")
        
    except Exception as e:
        logger.error(f"❌ Capability test failed: {e}")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("🎯 SUMMARY OF FINDINGS:")
    logger.info("1. OpenAI Vision models can EXTRACT and TRANSLATE text from images")
    logger.info("2. OpenAI Vision models CANNOT generate or modify images")
    logger.info("3. For actual image modification, you need:")
    logger.info("   - DALL-E for image generation")
    logger.info("   - PIL/OpenCV for text overlay on existing images")
    logger.info("   - Specialized OCR + image editing tools")
    logger.info("=" * 60)
    
    return True

if __name__ == "__main__":
    success = demonstrate_vision_capabilities()
    sys.exit(0 if success else 1)