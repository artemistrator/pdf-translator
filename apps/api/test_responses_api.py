#!/usr/bin/env python3
"""
OpenAI Responses API test with image_generation tool
Attempts to generate translated images using the new Responses API
"""

import os
import sys
from pathlib import Path
import base64
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env", override=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_responses_api():
    """
    Test OpenAI Responses API with image generation tool
    """
    logger.info("🚀 TESTING OPENAI RESPONSES API WITH IMAGE GENERATION")
    logger.info("=" * 60)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY not set")
        return False
    
    logger.info("✅ OpenAI API key found")
    
    # Import OpenAI client
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        logger.info("✅ OpenAI client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenAI client: {e}")
        return False
    
    # Test 1: Simple image generation
    logger.info("\n🎨 TEST 1: Simple Image Generation")
    logger.info("-" * 40)
    
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input="Generate an image of a cat with Russian text 'Привет мир' (Hello world)",
            tools=[{"type": "image_generation"}],
        )
        
        logger.info(f"✅ Response received")
        logger.info(f"Response type: {type(response)}")
        logger.info(f"Response attributes: {dir(response)}")
        
        # Try to extract image data
        if hasattr(response, 'output'):
            logger.info(f"Output items: {len(response.output)}")
            for i, output in enumerate(response.output):
                logger.info(f"  Output {i}: type={output.type}")
                if hasattr(output, 'result'):
                    logger.info(f"    Result length: {len(output.result) if output.result else 0}")
        
    except Exception as e:
        logger.error(f"❌ Simple generation failed: {e}")
    
    # Test 2: Image analysis + generation combo
    logger.info("\n🔄 TEST 2: Image Analysis + Generation Combo")
    logger.info("-" * 40)
    
    try:
        # Load test image
        project_root = Path(__file__).parents[2]
        test_image = project_root / "page1_img1.png"
        
        if not test_image.exists():
            logger.error("❌ Test image not found")
            return False
        
        # Encode image
        with open(test_image, "rb") as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # Try to combine image analysis with generation
        prompt = f"""Analyze this image and then generate a new version where:
1. All English text is translated to Russian
2. The text is placed in the same positions as the original
3. The overall image composition is preserved

Original image provided as base64 data."""
        
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            tools=[
                {"type": "image_generation"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}"
                    }
                }
            ],
        )
        
        logger.info(f"✅ Combined analysis+generation response received")
        
        # Extract image data
        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]
        
        if image_data:
            logger.info(f"✅ Found {len(image_data)} generated images")
            
            # Save the generated image
            output_file = project_root / "page1_img1_openai_generated.png"
            image_base64 = image_data[0]
            
            with open(output_file, "wb") as f:
                f.write(base64.b64decode(image_base64))
            
            logger.info(f"✅ Generated image saved: {output_file}")
            logger.info(f"📏 File size: {output_file.stat().st_size} bytes")
            return True
        else:
            logger.warning("⚠️ No image data found in response")
            
    except Exception as e:
        logger.error(f"❌ Combined test failed: {e}")
        logger.exception("Detailed error:")
    
    # Test 3: Check what models are available
    logger.info("\n🔍 TEST 3: Model Availability Check")
    logger.info("-" * 40)
    
    try:
        # Try different models
        models_to_test = ["gpt-4.1-mini", "gpt-4o", "gpt-image-1"]
        
        for model in models_to_test:
            try:
                logger.info(f"Testing model: {model}")
                response = client.responses.create(
                    model=model,
                    input="Generate a simple test image",
                    tools=[{"type": "image_generation"}],
                )
                logger.info(f"✅ {model} works")
            except Exception as e:
                logger.info(f"❌ {model} failed: {str(e)[:100]}...")
                
    except Exception as e:
        logger.error(f"❌ Model testing failed: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("🎯 SUMMARY:")
    logger.info("OpenAI Responses API with image_generation tool is experimental")
    logger.info("Current approach with PIL overlay is more reliable")
    logger.info("For production use, consider combining:")
    logger.info("1. OpenAI Vision for text extraction/translation")
    logger.info("2. PIL/OpenCV for precise text overlay")
    logger.info("3. DALL-E for complete image regeneration when needed")
    logger.info("=" * 60)
    
    return False  # Return False since we didn't successfully generate an image

if __name__ == "__main__":
    success = test_responses_api()
    sys.exit(0 if success else 1)