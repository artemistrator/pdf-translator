#!/usr/bin/env python3
"""
Integration test for OpenAI Vision translation functionality
Tests the full workflow: image -> OpenAI Vision -> translated image
"""

import os
import sys
from pathlib import Path
import base64
from openai import OpenAI
import logging
from dotenv import load_dotenv
import re

# Add the api directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from openai_vision import translate_image_with_openai_vision

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env files
load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env", override=True)
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

def test_openai_vision_translation():
    """
    Test OpenAI Vision translation with real image from root folder
    """
    logger.info("🚀 Starting OpenAI Vision Integration Test")
    
    # Define paths
    project_root = Path(__file__).parents[2]  # Go up 2 levels from apps/api to project root
    test_image_path = project_root / "page1_img1.png"
    output_image_path = project_root / "page1_img1_generated.png"
    
    # Check if test image exists
    if not test_image_path.exists():
        logger.error(f"❌ Test image not found: {test_image_path}")
        logger.info("Please place 'page1_img1.png' in the project root directory")
        return False
    
    logger.info(f"✅ Found test image: {test_image_path}")
    logger.info(f"📏 Image size: {test_image_path.stat().st_size} bytes")
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    logger.info(f"🔑 API Key present: {api_key is not None}")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY environment variable not set")
        logger.info("Please set OPENAI_API_KEY in your environment")
        logger.info(f"Checked paths: {Path(__file__).parents[2] / '.env'} and {Path(__file__).parent / '.env'}")
        return False
    
    logger.info("✅ OpenAI API key found")
    
    try:
        # Test the translation function
        logger.info("📨 Calling translate_image_with_openai_vision...")
        
        # Override the model to use a more capable vision model
        original_model = os.environ.get("OPENAI_MODEL")
        os.environ["OPENAI_MODEL"] = "gpt-4o"  # More capable vision model
        
        try:
            # This will use the existing function from openai_vision.py
            translated_image_b64 = translate_image_with_openai_vision(
                image_path=test_image_path,
                target_language="russian"
            )
        finally:
            # Restore original model
            if original_model:
                os.environ["OPENAI_MODEL"] = original_model
            else:
                os.environ.pop("OPENAI_MODEL", None)
        
        logger.info(f"✅ Received response from OpenAI Vision")
        logger.info(f"📏 Response size: {len(translated_image_b64)} characters")
        
        # Decode and save the image
        logger.info(f"💾 Saving translated image to: {output_image_path}")
        
        image_bytes = base64.b64decode(translated_image_b64)
        with open(output_image_path, "wb") as f:
            f.write(image_bytes)
        
        logger.info(f"✅ Image saved successfully!")
        logger.info(f"📁 Output file: {output_image_path}")
        logger.info(f"📏 Output size: {output_image_path.stat().st_size} bytes")
        
        # Verify the file was created
        if output_image_path.exists():
            logger.info("✅ TEST PASSED: Translated image file created successfully!")
            logger.info(f"🖼️  Check the file: {output_image_path}")
            return True
        else:
            logger.error("❌ TEST FAILED: Output file was not created")
            return False
            
    except Exception as e:
        logger.error(f"❌ TEST FAILED with exception: {e}")
        logger.exception("Detailed error traceback:")
        return False

def test_direct_openai_vision_api():
    """
    Alternative test using direct OpenAI API call to compare results
    """
    logger.info("\n🧪 Running Direct OpenAI Vision API Test")
    
    # Define paths
    project_root = Path(__file__).parents[2]
    test_image_path = project_root / "page1_img1.png"
    output_image_path = project_root / "page1_img1_direct_generated.png"
    
    if not test_image_path.exists():
        logger.error("❌ Test image not found for direct API test")
        return False
    
    try:
        # Encode image to base64
        with open(test_image_path, "rb") as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        logger.info("📨 Sending direct request to OpenAI Vision API...")
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Carefully examine this image. Read ALL visible English text. Translate it to Russian. Generate a NEW image where the original English text is replaced with Russian translation in the EXACT same positions and formatting. Return ONLY the modified image as base64 data URL."
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
            max_tokens=4096
        )
        
        # Extract image from response
        content = response.choices[0].message.content
        logger.info(f"✅ Direct API response received ({len(content)} chars)")
        logger.info(f"🔍 Response preview: {content[:200]}...")
        
        # Handle different response formats
        if content.startswith("data:image"):
            image_b64_result = content.split(",")[1]
            logger.info("✅ Found data:image URL format")
        elif "data:image" in content:
            # Extract from markdown or other format
            import re
            match = re.search(r"data:image/[a-zA-Z]+;base64,([A-Za-z0-9+/=]+)", content)
            if match:
                image_b64_result = match.group(1)
                logger.info("✅ Extracted base64 from data URL in response")
            else:
                image_b64_result = content
                logger.info("⚠️ No data URL found, using raw content")
        else:
            # If it's just base64 without data URL prefix
            image_b64_result = content
            logger.info("⚠️ Using raw response content as base64")
        
        # Save the result
        image_bytes = base64.b64decode(image_b64_result)
        with open(output_image_path, "wb") as f:
            f.write(image_bytes)
        
        logger.info(f"✅ Direct API test completed: {output_image_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Direct API test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("OPENAI VISION TRANSLATION INTEGRATION TEST")
    logger.info("=" * 60)
    
    # Run the main test
    success1 = test_openai_vision_translation()
    
    # Run alternative direct API test
    success2 = test_direct_openai_vision_api()
    
    logger.info("\n" + "=" * 60)
    if success1:
        logger.info("🎉 MAIN TEST: PASSED")
    else:
        logger.info("💥 MAIN TEST: FAILED")
        
    if success2:
        logger.info("🎉 DIRECT API TEST: PASSED")
    else:
        logger.info("💥 DIRECT API TEST: FAILED")
    
    logger.info("=" * 60)
    
    # Exit with appropriate code
    if success1 or success2:
        sys.exit(0)
    else:
        sys.exit(1)