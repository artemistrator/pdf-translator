#!/usr/bin/env python3
"""Regression test for full PDF generation workflow."""

import asyncio
import json
import sys
from pathlib import Path
import requests
import time

API_BASE = "http://localhost:8000"
PROJECT_ROOT = Path(__file__).parents[2]
SAMPLE_PDF_PATH = PROJECT_ROOT / "sample.pdf"
TEST_OUTPUT_DIR = Path("./tmp_test_output")


def wait_for_api(max_retries=30):
    """Wait for API to be ready."""
    print("⏳ Waiting for API to be ready...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{API_BASE}/health", timeout=2)
            if response.status_code == 200:
                print("✅ API is ready")
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)  # Shorter wait time
        print(f"... retry {i+1}/{max_retries}")
    
    print("❌ API not ready after retries")
    return False


def upload_pdf():
    """Step 1: Upload PDF file."""
    print("\n📝 Step 1: Uploading PDF...")
    
    if not SAMPLE_PDF_PATH.exists():
        print(f"❌ Sample PDF not found at {SAMPLE_PDF_PATH}")
        print("Please create a sample.pdf file in the project root")
        sys.exit(1)
    
    with open(SAMPLE_PDF_PATH, "rb") as f:
        files = {"file": ("sample.pdf", f, "application/pdf")}
        data = {"target_language": "en"}
        response = requests.post(f"{API_BASE}/api/translate", files=files, data=data)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        sys.exit(1)
    
    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"✅ Uploaded successfully. Job ID: {job_id}")
    return job_id


def process_job(job_id):
    """Step 2: Process the job."""
    print(f"\n⚙️  Step 2: Processing job {job_id}...")
    
    response = requests.post(f"{API_BASE}/api/process/{job_id}")
    
    if response.status_code != 200:
        print(f"❌ Processing failed: {response.status_code} - {response.text}")
        sys.exit(1)
    
    result = response.json()
    print(f"✅ Processing completed. Status: {result['status']}")


def get_vision_data(job_id):
    """Step 3: Get vision data."""
    print(f"\n👁️  Step 3: Getting vision data for job {job_id}...")
    
    response = requests.get(f"{API_BASE}/api/vision/{job_id}")
    
    if response.status_code != 200:
        print(f"❌ Failed to get vision data: {response.status_code} - {response.text}")
        sys.exit(1)
    
    vision_data = response.json()
    print("✅ Got vision data")
    return vision_data


def edit_vision_data(vision_data):
    """Step 4: Edit vision data by adding prefix to first block."""
    print("\n✏️  Step 4: Editing vision data...")
    
    if not vision_data.get("pages"):
        print("❌ No pages found in vision data")
        sys.exit(1)
    
    # Add prefix to first block's text
    first_page = vision_data["pages"][0]
    if first_page.get("blocks") and len(first_page["blocks"]) > 0:
        original_text = first_page["blocks"][0]["text"]
        first_page["blocks"][0]["text"] = f"Тестируем пдф: {original_text}"
        print(f"✅ Modified first block text: '{first_page['blocks'][0]['text']}'")
    else:
        # Create a new block if none exist
        first_page["blocks"] = [{
            "type": "paragraph",
            "text": "Тестируем пдф: This is a test paragraph",
            "bbox": [100, 100, 500, 200]
        }]
        print("✅ Created new test block")
    
    return vision_data


def save_edits(job_id, vision_data):
    """Step 5: Save edited vision data."""
    print(f"\n💾 Step 5: Saving edits for job {job_id}...")
    
    response = requests.put(
        f"{API_BASE}/api/vision/{job_id}",
        json=vision_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to save edits: {response.status_code} - {response.text}")
        sys.exit(1)
    
    print("✅ Edits saved successfully")


def generate_pdf(job_id, mode="html"):
    """Step 6: Generate PDF with specified mode."""
    print(f"\n📄 Step 6: Generating {mode.upper()} PDF for job {job_id}...")
    
    response = requests.post(f"{API_BASE}/api/generate/{job_id}?mode={mode}")
    
    if response.status_code != 200:
        print(f"❌ PDF generation failed: {response.status_code} - {response.text}")
        sys.exit(1)
    
    result = response.json()
    print(f"✅ PDF generated. Output: {result['output']}, Mode: {result['mode']}")


def download_pdf(job_id):
    """Step 7: Download the generated PDF."""
    print(f"\n⬇️  Step 7: Downloading PDF for job {job_id}...")
    
    TEST_OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = TEST_OUTPUT_DIR / "test_output.pdf"
    
    response = requests.get(
        f"{API_BASE}/api/result/{job_id}",
        headers={"Accept": "application/pdf"}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to download PDF: {response.status_code} - {response.text}")
        sys.exit(1)
    
    # Check content type
    content_type = response.headers.get("content-type", "")
    if "application/pdf" not in content_type:
        print(f"❌ Expected PDF content-type, got: {content_type}")
        sys.exit(1)
    
    with open(output_path, "wb") as f:
        f.write(response.content)
    
    print(f"✅ PDF downloaded to {output_path}")
    return output_path


def verify_output(job_id, pdf_path, mode="html"):
    """Step 8: Verify output files and content."""
    print(f"\n🔍 Step 8: Verifying {mode.upper()} output for job {job_id}...")
    
    # Check PDF file exists and size
    if not pdf_path.exists():
        print(f"❌ PDF file not found at {pdf_path}")
        sys.exit(1)
    
    file_size = pdf_path.stat().st_size
    if file_size < 1000:
        print(f"❌ PDF file too small ({file_size} bytes)")
        sys.exit(1)
    
    print(f"✅ PDF file exists and is {file_size} bytes")
    
    # Check render.html contains our test string and base64 images (only for HTML mode)
    if mode == "html":
        job_dir = PROJECT_ROOT / "data" / "jobs" / job_id
        render_html_path = job_dir / "render.html"
        
        if not render_html_path.exists():
            # Try alternative path (in case of different working directory)
            alt_path = Path("/Users/artem/Desktop/pdf translator/data/jobs") / job_id / "render.html"
            if alt_path.exists():
                render_html_path = alt_path
            else:
                print(f"❌ render.html not found at {render_html_path} or {alt_path}")
                sys.exit(1)
        
        with open(render_html_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "Тестируем пдф" not in content:
            print("❌ render.html does not contain test string 'Тестируем пдф'")
            sys.exit(1)
        
        # Check for base64 embedded images
        if "data:image/png;base64," not in content:
            print("❌ render.html does not contain base64 embedded images")
            sys.exit(1)
        
        # Check exact page count matches vision data
        page_count = content.count('class="page"')
        with open(job_dir / "edited.json", "r", encoding="utf-8") as f:
            vision_data = json.load(f)
        expected_pages = len(vision_data.get("pages", []))
        
        if page_count != expected_pages:
            print(f"❌ Page count mismatch: found {page_count}, expected {expected_pages}")
            sys.exit(1)
        
        print("✅ render.html contains test string")
        print("✅ render.html contains base64 embedded images")
        print(f"✅ Page count matches: {page_count} pages")
    
    # Check appropriate output file exists in job directory
    job_dir = PROJECT_ROOT / "data" / "jobs" / job_id
    if mode == "html":
        output_pdf_path = job_dir / "output.pdf"
    else:  # overlay
        output_pdf_path = job_dir / "output_overlay.pdf"
        
    if not output_pdf_path.exists():
        print(f"❌ {output_pdf_path.name} not found in job directory {output_pdf_path}")
        sys.exit(1)
    
    job_pdf_size = output_pdf_path.stat().st_size
    if job_pdf_size < 1000:
        print(f"❌ Job PDF too small ({job_pdf_size} bytes)")
        sys.exit(1)
    
    print(f"✅ Job {output_pdf_path.name} exists and is {job_pdf_size} bytes")
    
    print(f"\n🎉 {mode.upper()} mode verification passed!")


def main():
    """Main test workflow - test both HTML and Overlay modes."""
    print("=" * 60)
    print("PDF Generation Regression Test")
    print("=" * 60)
    
    # Wait for API
    if not wait_for_api():
        sys.exit(1)
    
    try:
        # Execute full workflow for HTML mode
        print("\n" + "=" * 50)
        print("Testing HTML Mode")
        print("=" * 50)
        job_id = upload_pdf()
        process_job(job_id)
        vision_data = get_vision_data(job_id)
        edited_data = edit_vision_data(vision_data)
        save_edits(job_id, edited_data)
        generate_pdf(job_id, mode="html")
        pdf_path = download_pdf(job_id)
        verify_output(job_id, pdf_path, mode="html")
        
        print("\n" + "=" * 50)
        print("Testing OVERLAY Mode")
        print("=" * 50)
        # Use same job_id for overlay test
        generate_pdf(job_id, mode="overlay")
        # Download overlay PDF (same endpoint, different file served)
        overlay_pdf_path = TEST_OUTPUT_DIR / "test_output_overlay.pdf"
        response = requests.get(
            f"{API_BASE}/api/result/{job_id}",
            headers={"Accept": "application/pdf"}
        )
        if response.status_code != 200:
            print(f"❌ Failed to download overlay PDF: {response.status_code}")
            sys.exit(1)
        with open(overlay_pdf_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Overlay PDF downloaded to {overlay_pdf_path}")
        verify_output(job_id, overlay_pdf_path, mode="overlay")
        
        print("\n" + "=" * 50)
        print("Testing OVERLAY DEBUG Mode")
        print("=" * 50)
        # Test debug overlay mode
        print(f"📄 Generating DEBUG overlay PDF for job {job_id}...")
        response = requests.post(f"{API_BASE}/api/generate/{job_id}?mode=overlay&debug_overlay=true")
        if response.status_code != 200:
            print(f"❌ Debug overlay generation failed: {response.status_code} - {response.text}")
            sys.exit(1)
        result = response.json()
        print(f"✅ Debug overlay PDF generated. Output: {result['output']}, Mode: {result['mode']}")
        
        # Download debug overlay PDF
        debug_overlay_pdf_path = TEST_OUTPUT_DIR / "test_output_overlay_debug.pdf"
        response = requests.get(
            f"{API_BASE}/api/result/{job_id}",
            headers={"Accept": "application/pdf"}
        )
        if response.status_code != 200:
            print(f"❌ Failed to download debug overlay PDF: {response.status_code}")
            sys.exit(1)
        with open(debug_overlay_pdf_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Debug overlay PDF downloaded to {debug_overlay_pdf_path}")
        
        # Verify debug overlay file exists
        job_dir = PROJECT_ROOT / "data" / "jobs" / job_id
        debug_output_path = job_dir / "output_overlay_debug.pdf"
        if not debug_output_path.exists():
            print(f"❌ Debug overlay output file not found: {debug_output_path}")
            sys.exit(1)
        print(f"✅ Debug overlay output file exists: {debug_output_path}")
        
        print("\n" + "=" * 60)
        print("✅ ALL REGRESSION TESTS PASSED")
        print("=" * 60)
        print(f"Job ID: {job_id}")
        print(f"HTML PDF: {pdf_path}")
        print(f"Overlay PDF: {overlay_pdf_path}")
        print(f"Debug Overlay PDF: {debug_overlay_pdf_path}")
        print("Test string 'Тестируем пдф' confirmed in render.html")
        print("All output files verified (output.pdf, output_overlay.pdf, output_overlay_debug.pdf)")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()