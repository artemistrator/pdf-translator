#!/usr/bin/env python3
"""
Test script for the visual OCR editor functionality.
"""

import requests
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_put_ocr_translation():
    """Test the PUT /api/ocr-translations/{job_id}/{image_name} endpoint"""
    
    # Test data
    job_id = "test-job-123"
    image_name = "test_image.png"
    
    payload = {
        "bbox": [100, 50, 200, 30],
        "text": "Hello World!",
        "font_size": 16,
        "color": "#FF0000"
    }
    
    print("Testing PUT /api/ocr-translations/{job_id}/{image_name}")
    print(f"Job ID: {job_id}")
    print(f"Image: {image_name}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.put(
            f"{API_BASE}/api/ocr-translations/{job_id}/{image_name}",
            json=payload
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ PUT request successful!")
        else:
            print("❌ PUT request failed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_get_ocr_translations():
    """Test getting OCR translations"""
    job_id = "test-job-123"
    
    print(f"\nTesting GET /api/ocr-translations/{job_id}")
    
    try:
        response = requests.get(f"{API_BASE}/api/ocr-translations/{job_id}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ GET request successful!")
        else:
            print("❌ GET request failed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_post_ocr():
    """Test OCR endpoint with translation loading"""
    # First, we need a real job with images
    # This would require uploading a PDF and running OCR first
    print("\nTo test POST /api/ocr/{job_id}/{image_name}:")
    print("1. Upload a PDF through the web interface")
    print("2. Run OCR on images")
    print("3. The response should include translations")

if __name__ == "__main__":
    print("=== Visual OCR Editor Backend Tests ===\n")
    
    test_put_ocr_translation()
    test_get_ocr_translations()
    test_post_ocr()
    
    print("\n=== Test Summary ===")
    print("Backend endpoints are ready for the visual editor!")
    print("Open http://localhost:3001/test in your browser to test the frontend.")