#!/usr/bin/env python3
"""
Complete AI-powered image translation workflow
1. Analyze image with OpenAI Vision
2. Translate text to Russian  
3. Generate new image with DALL-E 3 containing Russian text
"""

import os
import sys
from pathlib import Path
import base64
import logging
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env", override=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_and_translate_image(image_path: Path) -> dict:
    """
    Analyze image and extract/translate text using OpenAI Vision
    """
    logger.info(f"👁️  Analyzing image: {image_path.name}")
    
    # Encode image
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Extract and translate text
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": """Carefully analyze this image and provide:
1. Extract ALL visible English text exactly as it appears
2. Provide accurate Russian translation for each text element
3. Describe the image content and context
4. Suggest how to recreate this image with Russian text

Format as JSON:
{
  "original_texts": ["text1", "text2", ...],
  "translations": ["translation1", "translation2", ...],
  "image_description": "description of image content",
  "composition_notes": "layout and design elements"
}"""
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
    
    content = response.choices[0].message.content
    logger.info(f"✅ Analysis complete ({len(content)} chars)")
    
    # Parse JSON response
    try:
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content
            
        analysis = json.loads(json_str)
        logger.info(f"✅ Parsed analysis with {len(analysis.get('original_texts', []))} text elements")
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Failed to parse analysis: {e}")
        return {}

def generate_image_with_dalle(analysis: dict, output_path: Path) -> bool:
    """
    Generate new image with Russian text using DALL-E 3
    """
    logger.info("🎨 Generating image with DALL-E 3")
    
    # Create prompt for DALL-E
    original_texts = analysis.get('original_texts', [])
    translations = analysis.get('translations', [])
    image_desc = analysis.get('image_description', 'an image')
    composition = analysis.get('composition_notes', '')
    
    # Build comprehensive prompt
    prompt_parts = [
        f"Create {image_desc} with the following Russian text:",
    ]
    
    for i, (orig, trans) in enumerate(zip(original_texts, translations)):
        if orig and trans:
            prompt_parts.append(f"- '{trans}' (translated from '{orig}')")
    
    if composition:
        prompt_parts.append(f"Maintain the original style and composition: {composition}")
    
    prompt_parts.append("High quality, professional appearance, clear readable text")
    
    dalle_prompt = "\n".join(prompt_parts)
    logger.info(f"📝 DALL-E prompt:\n{dalle_prompt}")
    
    # Generate image
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=dalle_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
            response_format="b64_json"
        )
        
        # Extract and save image
        if response.data and len(response.data) > 0:
            image_b64 = response.data[0].b64_json
            if image_b64:
                image_bytes = base64.b64decode(image_b64)
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                
                logger.info(f"✅ DALL-E image generated and saved: {output_path}")
                logger.info(f"📏 File size: {output_path.stat().st_size} bytes")
                logger.info(f"📝 Revised prompt: {getattr(response.data[0], 'revised_prompt', 'N/A')}")
                return True
            else:
                logger.error("❌ No image data in response")
                return False
        else:
            logger.error("❌ No data in DALL-E response")
            return False
            
    except Exception as e:
        logger.error(f"❌ DALL-E generation failed: {e}")
        return False

def main():
    """
    Main workflow: analyze → translate → generate
    """
    logger.info("🚀 COMPLETE AI IMAGE TRANSLATION WORKFLOW")
    logger.info("=" * 60)
    
    # Paths
    project_root = Path(__file__).parents[2]
    original_image = project_root / "page1_img1.png"
    output_image = project_root / "page1_img1_dalle_translated.png"
    analysis_file = project_root / "dalle_analysis.json"
    
    # Check prerequisites
    if not original_image.exists():
        logger.error(f"❌ Original image not found: {original_image}")
        return False
    
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY not set")
        return False
    
    logger.info(f"✅ Found original image: {original_image}")
    logger.info(f"✅ OpenAI API key configured")
    
    # Step 1: Analyze and translate
    analysis = analyze_and_translate_image(original_image)
    if not analysis:
        logger.error("❌ Image analysis failed")
        return False
    
    # Save analysis
    with open(analysis_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Analysis saved: {analysis_file}")
    
    # Display results
    logger.info("\n📋 ANALYSIS RESULTS:")
    logger.info(f"Image description: {analysis.get('image_description', 'N/A')}")
    logger.info(f"Text elements found: {len(analysis.get('original_texts', []))}")
    
    for orig, trans in zip(analysis.get('original_texts', []), analysis.get('translations', [])):
        logger.info(f"  🇬🇧 {orig} → 🇷🇺 {trans}")
    
    # Step 2: Generate new image
    success = generate_image_with_dalle(analysis, output_image)
    
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
        logger.info(f"📁 Original: {original_image}")
        logger.info(f"📁 AI-generated translation: {output_image}")
        logger.info(f"📝 Analysis data: {analysis_file}")
        logger.info("=" * 60)
        return True
    else:
        logger.error("\n💥 IMAGE GENERATION FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)