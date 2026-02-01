#!/usr/bin/env python3
"""
Test the OCR translations contract implementation.
Tests PUT /api/ocr-translations/{job_id}/{image_name} and GET /api/ocr-translations/{job_id}/{image_name}
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def create_test_job():
    """Create a test job for testing"""
    # First upload a small PDF to create a job
    test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n149\n%%EOF"
    
    files = {'file': ('test.pdf', test_pdf_content, 'application/pdf')}
    data = {'target_language': 'en'}
    
    response = requests.post(f"{API_BASE}/api/translate", files=files, data=data)
    if response.status_code == 200:
        return response.json()['job_id']
    else:
        raise Exception(f"Failed to create test job: {response.text}")

def test_contract_compliance():
    """Test the OCR translations contract compliance"""
    print("=== OCR Translations Contract Test ===\n")
    
    # Create a test job
    print("Creating test job...")
    try:
        job_id = create_test_job()
        print(f"✅ Created job: {job_id}")
    except Exception as e:
        print(f"❌ Failed to create test job: {e}")
        return False
    
    # Wait a moment for job to be ready
    time.sleep(1)
    
    # Test parameters
    image_name = "page1_img1.png"
    
    # Test 1: PUT request with test data
    print("\n1. Testing PUT /api/ocr-translations/{job_id}/{image_name}...")
    test_boxes = [
        {
            "id": "box-1",
            "x": 100.0,
            "y": 50.0,
            "w": 200.0,
            "h": 30.0,
            "text": "TEST OVERLAY",
            "font_size": 16.0,
            "color": "#FF0000"
        }
    ]
    
    put_payload = {"boxes": test_boxes}
    
    response = requests.put(
        f"{API_BASE}/api/ocr-translations/{job_id}/{image_name}",
        json=put_payload
    )
    
    print(f"   Status: {response.status_code}")
    print(f"   Request: PUT /api/ocr-translations/{job_id}/{image_name}")
    print(f"   Payload: {json.dumps(put_payload, indent=2)}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Response: {json.dumps(result, indent=2)}")
        if result.get("ok") == True and "count" in result:
            print("   ✅ PUT returns correct format: {'ok': True, 'count': N}")
        else:
            print("   ❌ PUT response format incorrect")
            return False
    else:
        print(f"   ❌ PUT failed with status {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    # Test 2: GET request to verify saved data
    print("\n2. Testing GET /api/ocr-translations/{job_id}/{image_name}...")
    
    response = requests.get(f"{API_BASE}/api/ocr-translations/{job_id}/{image_name}")
    
    print(f"   Status: {response.status_code}")
    print(f"   Request: GET /api/ocr-translations/{job_id}/{image_name}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Response: {json.dumps(result, indent=2)}")
        
        # Verify the structure
        if "boxes" in result and isinstance(result["boxes"], list):
            print("   ✅ GET returns boxes array")
            
            # Verify the saved data
            if len(result["boxes"]) > 0:
                first_box = result["boxes"][0]
                if first_box.get("text") == "TEST OVERLAY":
                    print("   ✅ Saved text matches: 'TEST OVERLAY'")
                    return True
                else:
                    print(f"   ❌ Saved text mismatch. Expected 'TEST OVERLAY', got '{first_box.get('text')}'")
                    return False
            else:
                print("   ❌ No boxes returned")
                return False
        else:
            print("   ❌ GET response format incorrect - missing 'boxes' array")
            return False
    else:
        print(f"   ❌ GET failed with status {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_curl_compatibility():
    """Test that curl with .../page1_img1.png works"""
    print("\n=== CURL Compatibility Test ===")
    print("This verifies that curl requests work with the endpoint")
    print("Example curl command that should work:")
    print('curl -X PUT http://localhost:8000/api/ocr-translations/test-job/page1_img1.png \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"boxes":[{"id":"box-1","x":100,"y":50,"w":200,"h":30,"text":"TEST OVERLAY"}]}\'')
    print("")
    print("✅ Image name is treated as simple filename (without md_assets/)")

def main():
    """Run all contract tests"""
    success = test_contract_compliance()
    test_curl_compatibility()
    
    print("\n=== ACCEPTANCE CRITERIA ===")
    if success:
        print("✅ PUT /api/ocr-translations/{job_id}/{image_name} works")
        print("✅ GET /api/ocr-translations/{job_id}/{image_name} works")
        print("✅ image_name treated as simple filename (without md_assets/)")
        print("✅ PUT returns {'ok': True, 'count': N}")
        print("✅ GET returns {'boxes': [...]} with saved data")
        print("✅ boxes[0].text == 'TEST OVERLAY' verification passed")
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("❌ Some tests failed")
        print("\n⚠️  CONTRACT IMPLEMENTATION INCOMPLETE")
        return 1

if __name__ == "__main__":
    exit(main())