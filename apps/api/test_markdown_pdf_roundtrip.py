#!/usr/bin/env python3
"""
Test PDF → Markdown → PDF roundtrip workflow.

This test validates the full circle:
1. Upload PDF → extract to Markdown with images
2. Generate PDF from Markdown (with images)
3. Compare input and output visually
"""

import os
import sys
from pathlib import Path
import requests
import time
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from storage import storage_manager

API_BASE_URL = "http://localhost:8000"
TEST_PDF_PATH = Path(__file__).parent / "data" / "jobs" / "28d3a163-c560-45c8-9cac-6d4d2d63fcae" / "input.pdf"

def test_markdown_pdf_roundtrip():
    """Test full PDF → Markdown → PDF workflow"""
    
    print("🧪 Testing PDF → Markdown → PDF Roundtrip")
    print("=" * 50)
    
    # Check if test PDF exists
    if not TEST_PDF_PATH.exists():
        print(f"❌ Test PDF not found at {TEST_PDF_PATH}")
        print("Please create a sample PDF at apps/api/sample_documents/sample.pdf")
        return False
    
    # Step 1: Upload PDF
    print("\n📝 Step 1: Uploading PDF...")
    with open(TEST_PDF_PATH, 'rb') as f:
        files = {'file': ('sample.pdf', f, 'application/pdf')}
        data = {'target_language': 'en'}
        
        response = requests.post(
            f"{API_BASE_URL}/api/translate",
            files=files,
            data=data
        )
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        return False
    
    job_data = response.json()
    job_id = job_data['job_id']
    print(f"✅ Uploaded successfully! Job ID: {job_id}")
    
    # Step 2: Process PDF (extract vision data)
    print("\n🔍 Step 2: Processing PDF...")
    response = requests.post(f"{API_BASE_URL}/api/process/{job_id}")
    
    if response.status_code != 200:
        print(f"❌ Processing failed: {response.text}")
        return False
    
    process_data = response.json()
    if process_data['status'] != 'done':
        print(f"❌ Processing failed: {process_data.get('error', 'Unknown error')}")
        return False
    
    print("✅ Processing completed!")
    
    # Step 3: Convert to Markdown
    print("\n📄 Step 3: Converting to Markdown...")
    response = requests.post(f"{API_BASE_URL}/api/pdf-markdown/{job_id}")
    
    if response.status_code != 200:
        print(f"❌ Markdown conversion failed: {response.text}")
        return False
    
    markdown_data = response.json()
    print(f"✅ Converted to Markdown! Chars: {markdown_data['chars']}, Images: {markdown_data['images_count']}")
    
    # Step 4: Get Markdown content
    print("\n📥 Step 4: Loading Markdown content...")
    response = requests.get(f"{API_BASE_URL}/api/pdf-markdown/{job_id}")
    
    if response.status_code != 200:
        print(f"❌ Failed to load Markdown: {response.text}")
        return False
    
    content_data = response.json()
    markdown_content = content_data['markdown']
    print("✅ Markdown content loaded!")
    
    # Step 5: Generate PDF from Markdown
    print("\n🖨️ Step 5: Generating PDF from Markdown...")
    payload = {
        "markdown": markdown_content
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/pdf-from-markdown/{job_id}",
        json=payload
    )
    
    if response.status_code != 200:
        print(f"❌ PDF generation from Markdown failed: {response.text}")
        return False
    
    pdf_data = response.json()
    pdf_path = pdf_data['pdf_path']
    print(f"✅ PDF generated from Markdown! Path: {pdf_path}")
    
    # Step 6: Verify files exist
    print("\n📂 Step 6: Verifying output files...")
    job_dir = storage_manager.jobs_dir / job_id
    
    expected_files = [
        "markdown_for_pdf.md",
        "markdown.html",
        "result.pdf",
        "layout.md",
        "md_assets"
    ]
    
    all_good = True
    for filename in expected_files:
        file_path = job_dir / filename
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✅ {filename} ({size} bytes)")
        else:
            print(f"❌ {filename} not found")
            all_good = False
    
    if not all_good:
        return False
    
    # Step 7: Summary
    print("\n" + "=" * 50)
    print("🎉 ROUNDTRIP TEST COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print(f"Job ID: {job_id}")
    print(f"Original PDF: {TEST_PDF_PATH.name}")
    print(f"Markdown chars: {len(markdown_content)}")
    print(f"Images extracted: {markdown_data['images_count']}")
    print(f"Output PDF: {pdf_path}")
    print("\n📁 Files created:")
    print(f"  - {job_dir / 'layout.md'} (original layout)")
    print(f"  - {job_dir / 'markdown_for_pdf.md'} (edited markdown)")
    print(f"  - {job_dir / 'markdown.html'} (intermediate HTML)")
    print(f"  - {job_dir / 'result.pdf'} (final PDF)")
    print(f"  - {job_dir / 'md_assets/'} (extracted images)")
    
    return True

if __name__ == "__main__":
    # Run the test
    success = test_markdown_pdf_roundtrip()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)
