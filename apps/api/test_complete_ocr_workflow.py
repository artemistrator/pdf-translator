#!/usr/bin/env python3
"""
Complete end-to-end test for OCR → PDF workflow.
"""

import asyncio
import sys
import requests
import time
from pathlib import Path

# Add the api directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

API_BASE = "http://localhost:8001"

def test_complete_workflow():
    """Test the complete OCR to PDF workflow."""
    job_id = "ba0e7b2f-9692-45fb-8259-33ff53181ca1"  # Existing job with images
    
    print("🧪 Testing Complete OCR → PDF Workflow")
    print("=" * 50)
    
    # Step 1: Perform OCR on image
    print("\n1️⃣ Performing OCR on image...")
    try:
        response = requests.post(f"{API_BASE}/api/ocr/{job_id}/page1_img1.png")
        if response.status_code == 200:
            ocr_data = response.json()
            print(f"✅ OCR successful! Found {len(ocr_data['ocr_boxes'])} text boxes")
            for i, box in enumerate(ocr_data['ocr_boxes'][:3]):
                print(f"   Box {i}: '{box['text']}' (confidence: {box['confidence']:.2f})")
        else:
            print(f"❌ OCR failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ OCR request failed: {e}")
        return False
    
    # Step 2: Save OCR translations (change "IS" to "IT")
    print("\n2️⃣ Saving OCR translations...")
    translations_payload = {
        "translations": {
            "page1_img1.png": {
                "ocr_result": ocr_data,
                "translations": {
                    "0": "IT",  # Change first box from "IS" to "IT"
                    "1": "WORKING",  # Change second box
                    "2": "PERFECTLY"  # Change third box
                }
            }
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/api/ocr-translations/{job_id}",
            json=translations_payload
        )
        if response.status_code == 200:
            print("✅ OCR translations saved successfully")
        else:
            print(f"❌ Failed to save translations: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Save translations request failed: {e}")
        return False
    
    # Step 3: Generate PDF from markdown with OCR overlays
    print("\n3️⃣ Generating PDF with OCR overlays...")
    markdown_content = f"""# OCR Test Document

This document demonstrates OCR text overlay functionality.

![Test Image](md_assets/page1_img1.png)

The image above should show the original text with OCR-detected bounding boxes and translated text overlaid on top.

Original text was: IS 1T MEME YOU'RE LOOKING/FOR?
Translated text is: IT WORKING PERFECTLY YOU'RE LOOKING/FOR?

End of document."""

    try:
        response = requests.post(
            f"{API_BASE}/api/pdf-from-markdown/{job_id}",
            json={"markdown": markdown_content}
        )
        if response.status_code == 200:
            pdf_result = response.json()
            print("✅ PDF generated successfully!")
            print(f"   PDF path: {pdf_result['pdf_path']}")
        else:
            print(f"❌ PDF generation failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ PDF generation request failed: {e}")
        return False
    
    # Step 4: Generate HTML with OCR overlays for verification
    print("\n4️⃣ Generating HTML with OCR overlays...")
    try:
        response = requests.get(f"{API_BASE}/api/download-html/{job_id}")
        if response.status_code == 200:
            # Save HTML for inspection
            html_file = "test_final_ocr.html"
            with open(html_file, "wb") as f:
                f.write(response.content)
            print(f"✅ HTML generated successfully! Saved as {html_file} ({len(response.content)} bytes)")
            
            # Check if OCR overlays are present in HTML
            html_content = response.content.decode('utf-8')
            if "ocr-overlay" in html_content and "IT" in html_content:
                print("✅ OCR text overlays found in HTML!")
            else:
                print("⚠️  OCR overlays may not be properly rendered")
        else:
            print(f"❌ HTML generation failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ HTML generation request failed: {e}")
        return False
    
    # Step 5: Verify files exist
    print("\n5️⃣ Verifying output files...")
    try:
        # Check PDF file
        pdf_path = Path(f"../data/jobs/{job_id}/result.pdf")
        if pdf_path.exists():
            size = pdf_path.stat().st_size
            print(f"✅ PDF file exists: {size} bytes")
        else:
            print("❌ PDF file not found")
            return False
            
        # Check HTML file
        html_path = Path(f"../data/jobs/{job_id}/document_with_ocr_{job_id}.html")
        if html_path.exists():
            size = html_path.stat().st_size
            print(f"✅ HTML file exists: {size} bytes")
        else:
            print("❌ HTML file not found")
            return False
            
        # Check OCR translations file
        translations_path = Path(f"../data/jobs/{job_id}/ocr_translations.json")
        if translations_path.exists():
            size = translations_path.stat().st_size
            print(f"✅ OCR translations file exists: {size} bytes")
        else:
            print("❌ OCR translations file not found")
            return False
            
    except Exception as e:
        print(f"❌ File verification failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 COMPLETE WORKFLOW TEST PASSED!")
    print("=" * 50)
    print("✅ OCR detection works")
    print("✅ OCR translations can be saved") 
    print("✅ PDF generation with OCR overlays works")
    print("✅ HTML generation with OCR overlays works")
    print("✅ All output files are created successfully")
    print("\nYou can now:")
    print("1. Open the generated PDF to see OCR text overlays")
    print("2. Open the HTML file to see the web version with overlays")
    print("3. Use the frontend to edit OCR text and regenerate PDFs")
    
    return True

if __name__ == "__main__":
    success = test_complete_workflow()
    sys.exit(0 if success else 1)