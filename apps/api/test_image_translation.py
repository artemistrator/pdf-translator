#!/usr/bin/env python3
"""
Test script to verify image translation functionality with OpenAI Vision API
"""

import os
import sys
from pathlib import Path
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv

# Add the api directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from openai_vision import translate_image_with_openai_vision

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env", override=True)
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

def test_image_translation():
    """Test the image translation functionality"""
    print("🔍 Testing image translation functionality...")
    
    # Define paths
    project_root = Path(__file__).parents[2]  # Go up 2 levels from apps/api to project root
    test_image_path = project_root / "page1_img1.png"
    output_image_path = project_root / "page1_img1_translated.png"
    
    # Check if test image exists
    if not test_image_path.exists():
        print(f"❌ Test image not found: {test_image_path}")
        return False
    
    print(f"✅ Found test image: {test_image_path}")
    print(f"📏 Image size: {test_image_path.stat().st_size} bytes")
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"🔑 API Key present: {api_key is not None}")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set OPENAI_API_KEY in your environment")
        return False
    
    print("✅ OpenAI API key found")
    
    try:
        # Test the translation function
        print("📨 Calling translate_image_with_openai_vision...")
        
        # Use the improved function
        translated_image_b64 = translate_image_with_openai_vision(
            image_path=test_image_path,
            target_language="russian"
        )
        
        print(f"✅ Received response from OpenAI Vision")
        print(f"📏 Response size: {len(translated_image_b64)} characters")
        
        # Decode and save the image
        print(f"💾 Saving translated image to: {output_image_path}")
        
        import base64
        image_bytes = base64.b64decode(translated_image_b64)
        with open(output_image_path, "wb") as f:
            f.write(image_bytes)
        
        print(f"✅ Image saved successfully!")
        print(f"📁 Output file: {output_image_path}")
        print(f"📏 Output size: {output_image_path.stat().st_size} bytes")
        
        # Verify the file was created
        if output_image_path.exists():
            print("✅ TEST PASSED: Translated image file created successfully!")
            print(f"🖼️  Check the file: {output_image_path}")
            return True
        else:
            print("❌ TEST FAILED: Output file was not created")
            return False
            
    except Exception as e:
        print(f"❌ TEST FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_direct_openai_vision_api():
    """Test direct OpenAI Vision API call to see what it returns"""
    print("\n🧪 Testing direct OpenAI Vision API call...")
    
    # Define paths
    project_root = Path(__file__).parents[2]
    test_image_path = project_root / "page1_img1.png"
    
    if not test_image_path.exists():
        print("❌ Test image not found for direct API test")
        return False
    
    # Encode image
    with open(test_image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Test with the improved prompt
    prompt = (
        "Analyze this image and extract all visible text. Translate each text element to russian. "
        "Return a JSON object with 'text_elements' array, where each element has 'original', 'translation', 'x', 'y', 'width', 'height' fields. "
        "Coordinates should be relative to the image dimensions. "
        "Example format: {\"text_elements\":[{\"original\":\"Hello\", \"translation\":\"Привет\", \"x\":100, \"y\":50, \"width\":200, \"height\":30}]}"
    )
    
    try:
        print("📨 Sending request to OpenAI Vision API...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        print(f"✅ Direct API response received ({len(content)} chars)")
        print(f"🔍 Response preview: {content[:500]}...")
        
        # Try to parse as JSON
        try:
            import json
            import re
            
            # Clean up the response if it contains markdown code blocks
            clean_content = content.strip()
            if clean_content.startswith('```json'):
                clean_content = re.sub(r'^```json\s*', '', clean_content)
                clean_content = re.sub(r'\s*```$', '', clean_content)
            elif clean_content.startswith('```'):
                clean_content = re.sub(r'^```\w*\s*', '', clean_content)
                clean_content = re.sub(r'\s*```$', '', clean_content)
            
            parsed_data = json.loads(clean_content)
            print(f"✅ Successfully parsed JSON response")
            print(f"📊 Found {len(parsed_data.get('text_elements', []))} text elements")
            
            # Save the response for inspection
            response_file = project_root / "vision_api_response.json"
            with open(response_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Response saved to: {response_file}")
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            print(f"📝 Raw response: {content}")
            return False
        
    except Exception as e:
        print(f"❌ Direct API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting image translation tests...")
    
    # Test direct API call first
    direct_success = test_direct_openai_vision_api()
    
    print("\n" + "="*60)
    
    # Test the translation function
    function_success = test_image_translation()
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY:")
    print(f"Direct API test: {'✅ PASSED' if direct_success else '❌ FAILED'}")
    print(f"Translation function test: {'✅ PASSED' if function_success else '❌ FAILED'}")
    
    if direct_success and function_success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)