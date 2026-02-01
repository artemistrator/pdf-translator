#!/usr/bin/env python3
"""
Test the vision-translate endpoint
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_vision_translate_endpoint():
    """Test the POST /api/vision-translate/{job_id}/{image_name} endpoint"""
    
    # Use an existing job with images for testing
    job_id = "ba0e7b2f-9692-45fb-8259-33ff53181ca1"  # Known job with images
    image_name = "page1_img1.png"
    
    print("=== Vision Translate Endpoint Test ===\n")
    print(f"Testing with job_id: {job_id}")
    print(f"Testing with image: {image_name}")
    
    # Test payload
    payload = {
        "target_language": "russian"
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/vision-translate/{job_id}/{image_name}",
            json=payload
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ SUCCESS! Response:")
            print(json.dumps(result, indent=2))
            
            # Verify expected fields
            expected_fields = ["original_image_name", "translated_image_name", "image_url", "target_language"]
            for field in expected_fields:
                if field in result:
                    print(f"   ✓ Contains '{field}': {result[field]}")
                else:
                    print(f"   ✗ Missing '{field}'")
                    
            return True
            
        else:
            print(f"\n❌ FAILED with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

def test_invalid_language():
    """Test with invalid language"""
    job_id = "ba0e7b2f-9692-45fb-8259-33ff53181ca1"
    image_name = "page1_img1.png"
    
    print("\n=== Testing Invalid Language ===")
    
    payload = {
        "target_language": "spanish"  # Invalid language
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/api/vision-translate/{job_id}/{image_name}",
            json=payload
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 400:
            print("✅ Correctly rejected invalid language")
            print(f"Response: {response.text}")
            return True
        else:
            print(f"❌ Expected 400, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_nonexistent_job():
    """Test with nonexistent job"""
    job_id = "nonexistent-job-123"
    image_name = "test.png"
    
    print("\n=== Testing Nonexistent Job ===")
    
    payload = {
        "target_language": "russian"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/api/vision-translate/{job_id}/{image_name}",
            json=payload
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 404:
            print("✅ Correctly rejected nonexistent job")
            print(f"Response: {response.text}")
            return True
        else:
            print(f"❌ Expected 404, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Testing Vision Translate Endpoint\n")
    print("=" * 50)
    
    success = True
    
    # Run all tests
    success &= test_vision_translate_endpoint()
    success &= test_invalid_language()
    success &= test_nonexistent_job()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED!")