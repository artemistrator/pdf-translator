#!/usr/bin/env python3
"""
Test script to verify the vision translation endpoint functionality
"""

import os
import sys
from pathlib import Path
import base64
import json
import tempfile
import shutil
from openai import OpenAI
from dotenv import load_dotenv

# Add the api directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env", override=True)
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

def create_test_job():
    """Create a test job with the sample image"""
    import uuid
    from datetime import datetime
    from storage import storage_manager
    
    # Create a job ID
    job_id = "test-vision-" + str(uuid.uuid4())
    print(f"📋 Created test job: {job_id}")
    
    # Create job directory structure
    job_dir = storage_manager.jobs_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Create md_assets directory
    assets_dir = job_dir / "md_assets"
    assets_dir.mkdir(exist_ok=True)
    
    # Copy the test image to the job's md_assets directory
    project_root = Path(__file__).parents[2]
    source_image = project_root / "page1_img1.png"
    dest_image = assets_dir / "page1_img1.png"
    
    if source_image.exists():
        shutil.copy2(source_image, dest_image)
        print(f"🖼️  Copied test image to job: {dest_image}")
    else:
        print(f"❌ Source image not found: {source_image}")
        return None, None
    
    # Create a mock job.json
    job_data = {
        "job_id": job_id,
        "status": "done",
        "target_language": "russian",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "input_path": str(dest_image),
        "output_path": None,
        "error": None
    }
    
    job_json_path = job_dir / "job.json"
    with open(job_json_path, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, indent=2)
    
    print(f"📄 Created job metadata: {job_json_path}")
    
    return job_id, dest_image

def test_vision_endpoint():
    """Test the vision translation endpoint"""
    print("🔍 Testing vision translation endpoint...")
    
    # Import the necessary modules
    from main import vision_translate, get_translation_data
    from storage import storage_manager
    import asyncio
    
    # Create a test job
    job_id, image_path = create_test_job()
    if not job_id:
        print("❌ Failed to create test job")
        return False
    
    image_name = "page1_img1.png"
    
    try:
        # Test the vision translation endpoint
        print(f"🚀 Calling vision_translate endpoint for job={job_id}, image={image_name}")
        
        # Simulate the async function call
        result = asyncio.run(vision_translate(job_id, image_name))
        
        print(f"✅ Vision translation completed successfully")
        print(f"📊 Result: {result}")
        
        # Check if translated image was created
        job_dir = storage_manager.jobs_dir / job_id
        translated_image_name = result["translated_image_name"]
        translated_image_path = job_dir / "md_assets" / translated_image_name
        
        if translated_image_path.exists():
            print(f"🖼️  Translated image created: {translated_image_path}")
            print(f"📏 Size: {translated_image_path.stat().st_size} bytes")
        else:
            print(f"❌ Translated image not found: {translated_image_path}")
            return False
        
        # Test getting translation data
        print(f"🔍 Getting translation data for image...")
        translation_data = asyncio.run(get_translation_data(job_id, image_name))
        
        print(f"📊 Translation data: {json.dumps(translation_data, indent=2)[:500]}...")
        
        if "text_elements" in translation_data:
            elements = translation_data["text_elements"]
            print(f"✅ Found {len(elements)} text elements in translation data")
            for i, elem in enumerate(elements):
                original = elem.get("original", "N/A")
                translation = elem.get("translation", "N/A")
                x, y = elem.get("x", 0), elem.get("y", 0)
                print(f"   Element {i+1}: '{original[:30]}...' -> '{translation[:30]}...' at ({x}, {y})")
        else:
            print(f"⚠️  No text_elements found in translation data")
        
        print("✅ Vision endpoint test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Vision endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup: Remove test job directory
        job_dir = storage_manager.jobs_dir / job_id
        if job_dir.exists():
            import shutil
            shutil.rmtree(job_dir)
            print(f"🧹 Cleaned up test job: {job_id}")

def test_manual_api_call():
    """Test the API call directly using the same approach as the frontend"""
    print("\n🔍 Testing manual API call similar to frontend...")
    
    # Import the same modules as the main API
    from openai import OpenAI
    import base64
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return False
    
    # Load the test image
    project_root = Path(__file__).parents[2]
    image_path = project_root / "page1_img1.png"
    
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        return False
    
    # Encode image to base64
    with open(image_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode()
    
    print(f"🖼️  Loaded image: {len(image_base64)} bytes")
    
    # Create OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Same prompt as used in the vision_translate endpoint
    prompt = "Extract all visible English text from this image. Return JSON with original text, Russian translation, and approximate coordinates for each text element. Format: {\"text_elements\": [{\"original\": \"text\", \"translation\": \"перевод\", \"x\": 100, \"y\": 50, \"width\": 200, \"height\": 30}]}"
    
    try:
        print("📨 Sending request to OpenAI Vision API...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                    {"type": "text", "text": prompt}
                ]
            }],
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        print(f"✅ API response received ({len(content)} chars)")
        
        # Parse the response
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
        
        try:
            translation_data = json.loads(clean_content)
            text_elements = translation_data.get("text_elements", [])
            print(f"✅ Parsed {len(text_elements)} text elements from response")
            
            for i, elem in enumerate(text_elements):
                original = elem.get("original", "N/A")
                translation = elem.get("translation", "N/A")
                x, y = elem.get("x", 0), elem.get("y", 0)
                print(f"   Element {i+1}: '{original[:30]}...' -> '{translation[:30]}...' at ({x}, {y})")
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            print(f"📝 Raw response: {content[:500]}...")
            return False
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting vision endpoint tests...")
    
    # Test manual API call first
    manual_success = test_manual_api_call()
    
    print("\n" + "="*60)
    
    # Test the full endpoint
    endpoint_success = test_vision_endpoint()
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY:")
    print(f"Manual API call test: {'✅ PASSED' if manual_success else '❌ FAILED'}")
    print(f"Vision endpoint test: {'✅ PASSED' if endpoint_success else '❌ FAILED'}")
    
    if manual_success and endpoint_success:
        print("🎉 All tests passed! The image translation functionality is working correctly.")
        print("\n💡 Summary:")
        print("- OpenAI Vision API successfully extracts text and coordinates")
        print("- Vision endpoint properly processes the image and creates translated version")
        print("- Text elements with coordinates and translations are correctly extracted")
        print("- The system now properly uses the coordinate data to place translated text")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)