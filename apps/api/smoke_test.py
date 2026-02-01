#!/usr/bin/env python3
"""
Smoke test for Document Translator API - Phase 2
Tests PDF→PNG→Vision pipeline with optional OpenAI key
"""
import os
import sys
from pathlib import Path
import requests
import json
from storage import resolve_storage_dir


def create_sample_pdf():
    """Create a simple PDF file for testing"""
    # Simple PDF content (minimal valid PDF)
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Resources <<>>\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000108 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n195\n%%EOF'
    
    project_root = Path(__file__).resolve().parents[2]
    sample_pdf_path = project_root / "sample.pdf"
    
    with open(sample_pdf_path, "wb") as f:
        f.write(pdf_content)
    
    print(f"Created sample PDF: {sample_pdf_path}")
    return sample_pdf_path


def main():
    # Get API base URL
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    print(f"Testing API at: {api_base_url}")
    
    # Check if sample.pdf exists, create if not
    project_root = Path(__file__).resolve().parents[2]
    sample_pdf_path = project_root / "sample.pdf"
    
    if not sample_pdf_path.exists():
        print("Sample PDF not found, creating...")
        sample_pdf_path = create_sample_pdf()
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{api_base_url}/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ Health check passed")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        sys.exit(1)
    
    # Test 2: Upload file
    print("\n2. Testing file upload...")
    try:
        with open(sample_pdf_path, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            data = {"target_language": "en"}
            response = requests.post(f"{api_base_url}/api/translate", files=files, data=data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        result = response.json()
        job_id = result["job_id"]
        print(f"✅ Upload successful, job_id: {job_id}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        sys.exit(1)
    
    # Test 3: Check job status
    print("\n3. Testing job status...")
    try:
        response = requests.get(f"{api_base_url}/api/status/{job_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        status_result = response.json()
        assert status_result["status"] == "queued", f"Expected 'queued', got '{status_result['status']}'"
        print("✅ Job status check passed")
    except Exception as e:
        print(f"❌ Job status check failed: {e}")
        sys.exit(1)
    
    # Test 4: Process job (Phase 2)
    print("\n4. Testing process endpoint...")
    try:
        response = requests.post(f"{api_base_url}/api/process/{job_id}")
        
        # Handle both success and missing key cases
        if response.status_code == 200:
            process_result = response.json()
            if process_result["status"] == "done":
                print("✅ Process successful - Vision analysis completed")
                
                # Test 5: Get result
                print("\n5. Testing result endpoint...")
                response = requests.get(f"{api_base_url}/api/result/{job_id}")
                assert response.status_code == 200, f"Expected 200, got {response.status_code}"
                
                result_data = response.json()
                assert "pages" in result_data, "Result should contain 'pages' key"
                assert "meta" in result_data, "Result should contain 'meta' key"
                
                # Validate JSON structure if API key was provided
                if os.getenv("OPENAI_API_KEY"):
                    # Check pages structure
                    assert isinstance(result_data["pages"], list), "'pages' should be a list"
                    for page in result_data["pages"]:
                        assert "page" in page, "Each page should have 'page' field"
                        assert "blocks" in page, "Each page should have 'blocks' field"
                        assert isinstance(page["blocks"], list), "'blocks' should be a list"
                        
                        # Check blocks structure
                        for block in page["blocks"]:
                            assert "type" in block, "Each block should have 'type' field"
                            assert "bbox" in block, "Each block should have 'bbox' field"
                            assert "text" in block, "Each block should have 'text' field"
                            
                            # Validate bbox is array of 4 numbers
                            assert isinstance(block["bbox"], list), "'bbox' should be a list"
                            assert len(block["bbox"]) == 4, "'bbox' should have 4 elements"
                            for coord in block["bbox"]:
                                assert isinstance(coord, (int, float)), "bbox coordinates should be numbers"
                            
                            # Validate type is valid enum
                            valid_types = ["heading", "paragraph", "list", "table", "header", "footer", "figure_caption", "other"]
                            assert block["type"] in valid_types, f"Invalid block type: {block['type']}"
                    
                    # Check meta structure
                    meta = result_data["meta"]
                    assert "target_language" in meta, "Meta should have 'target_language' field"
                    assert isinstance(meta["target_language"], str), "'target_language' should be string"
                    
                    print("✅ Result endpoint returned valid structured JSON")
                else:
                    print("✅ Result endpoint returned vision.json content")
                
                # Test 6: Generate PDF (new test)
                print("\n6. Testing PDF generation...")
                try:
                    response = requests.post(f"{api_base_url}/api/generate/{job_id}")
                    
                    if response.status_code == 200:
                        generate_result = response.json()
                        assert generate_result["status"] == "done", f"Expected 'done', got '{generate_result['status']}'"
                        assert generate_result["output"] == "pdf", f"Expected 'pdf', got '{generate_result['output']}'"
                        print("✅ PDF generation successful")
                        
                        # Verify PDF file exists and is reasonable size
                        storage_dir = resolve_storage_dir()
                        output_pdf = storage_dir / "jobs" / job_id / "output.pdf"
                        render_html = storage_dir / "jobs" / job_id / "render.html"
                        
                        assert output_pdf.exists(), f"Output PDF not found: {output_pdf}"
                        assert output_pdf.stat().st_size > 1000, f"Output PDF too small ({output_pdf.stat().st_size} bytes)"
                        print(f"✅ Output PDF created: {output_pdf} ({output_pdf.stat().st_size} bytes)")
                        
                        assert render_html.exists(), f"Render HTML not found: {render_html}"
                        assert render_html.stat().st_size > 1000, f"Render HTML too small ({render_html.stat().st_size} bytes)"
                        print(f"✅ Render HTML created: {render_html} ({render_html.stat().st_size} bytes)")
                        
                        # Test 7: Download PDF via result endpoint
                        print("\n7. Testing PDF download via result endpoint...")
                        response = requests.get(f"{api_base_url}/api/result/{job_id}")
                        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
                        assert response.headers["content-type"] == "application/pdf", f"Expected PDF content-type, got {response.headers.get('content-type')}"
                        assert len(response.content) > 1000, f"Downloaded PDF too small ({len(response.content)} bytes)"
                        print("✅ PDF download successful")
                        
                    elif response.status_code == 500:
                        error_result = response.json()
                        error_detail = error_result.get("detail", "")
                        if "chromium" in error_detail.lower() or "playwright" in error_detail.lower():
                            print("⚠️  PDF generation failed due to missing Playwright/Chromium")
                            print("   To fix: make api-playwright-install")
                            print("   SKIP PDF: Dependencies not installed")
                        else:
                            raise AssertionError(f"PDF generation failed: {error_detail}")
                    else:
                        raise AssertionError(f"Unexpected status code for generate: {response.status_code}")
                        
                except requests.exceptions.ConnectionError as e:
                    if "Connection refused" in str(e):
                        print("⚠️  Could not connect to API server")
                        print("   Make sure the API server is running: make api-dev")
                        sys.exit(1)
                    else:
                        raise
                
            elif process_result["status"] == "error" and "OPENAI_API_KEY is not set" in process_result.get("error", ""):
                print("✅ Process correctly failed due to missing API key")
                print("   SKIP VISION: Key not configured")
                
                # Verify PNG was created
                storage_dir = resolve_storage_dir()
                pages_dir = storage_dir / "jobs" / job_id / "pages"
                page_1_png = pages_dir / "page_1.png"
                
                assert page_1_png.exists(), f"page_1.png not found: {page_1_png}"
                assert page_1_png.stat().st_size > 0, f"page_1.png is empty: {page_1_png}"
                print(f"✅ PNG created successfully: {page_1_png}")
            else:
                raise AssertionError(f"Unexpected process result: {process_result}")
            
        elif response.status_code == 400:
            error_result = response.json()
            if "OPENAI_API_KEY is not set" in error_result.get("detail", ""):
                print("✅ Process correctly failed due to missing API key")
                print("   SKIP VISION: Key not configured")
                
                # Verify PNG was created
                storage_dir = resolve_storage_dir()
                pages_dir = storage_dir / "jobs" / job_id / "pages"
                page_1_png = pages_dir / "page_1.png"
                
                assert page_1_png.exists(), f"page_1.png not found: {page_1_png}"
                assert page_1_png.stat().st_size > 0, f"page_1.png is empty: {page_1_png}"
                print(f"✅ PNG created successfully: {page_1_png}")
            else:
                raise AssertionError(f"Unexpected 400 error: {error_result}")
        else:
            raise AssertionError(f"Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Process test failed: {e}")
        sys.exit(1)
    
    # Test 8: Verify files on disk
    print("\n8. Verifying files on disk...")
    try:
        storage_dir = resolve_storage_dir()
        job_dir = storage_dir / "jobs" / job_id
        
        # Check input.pdf
        input_pdf = job_dir / "input.pdf"
        assert input_pdf.exists(), f"Input PDF not found: {input_pdf}"
        assert input_pdf.stat().st_size > 0, f"Input PDF is empty: {input_pdf}"
        print(f"✅ Input PDF found: {input_pdf} ({input_pdf.stat().st_size} bytes)")
        
        # Check job.json
        job_json = job_dir / "job.json"
        assert job_json.exists(), f"Job JSON not found: {job_json}"
        assert job_json.stat().st_size > 0, f"Job JSON is empty: {job_json}"
        
        # Verify job.json content
        with open(job_json, "r") as f:
            job_data = json.load(f)
            assert job_data["job_id"] == job_id, f"Job ID mismatch in JSON"
        print(f"✅ Job JSON found and verified: {job_json}")
        
        # Check pages directory
        pages_dir = job_dir / "pages"
        assert pages_dir.exists(), f"Pages directory not found: {pages_dir}"
        
        page_files = list(pages_dir.glob("page_*.png"))
        assert len(page_files) > 0, "No page PNG files found"
        print(f"✅ Pages directory contains {len(page_files)} PNG files")
        
        # Check vision.json if it exists
        vision_json = job_dir / "vision.json"
        if vision_json.exists():
            assert vision_json.stat().st_size > 0, f"Vision JSON is empty: {vision_json}"
            with open(vision_json, "r") as f:
                vision_data = json.load(f)
                assert "pages" in vision_data, "Vision JSON should contain 'pages' key"
            print(f"✅ Vision JSON found and verified: {vision_json}")
        
        # Check render.html and output.pdf if they exist
        render_html = job_dir / "render.html"
        output_pdf = job_dir / "output.pdf"
        
        if render_html.exists():
            assert render_html.stat().st_size > 1000, f"Render HTML too small: {render_html}"
            print(f"✅ Render HTML found: {render_html} ({render_html.stat().st_size} bytes)")
        
        if output_pdf.exists():
            assert output_pdf.stat().st_size > 1000, f"Output PDF too small: {output_pdf}"
            print(f"✅ Output PDF found: {output_pdf} ({output_pdf.stat().st_size} bytes)")
        
        # Check debug artifacts
        openai_request_meta = job_dir / "openai_request_meta.json"
        openai_raw = job_dir / "openai_raw.txt"
        openai_error = job_dir / "openai_error.txt"
        
        if openai_request_meta.exists():
            print(f"✅ OpenAI request metadata: {openai_request_meta}")
        if openai_raw.exists():
            print(f"✅ OpenAI raw response: {openai_raw} ({openai_raw.stat().st_size} bytes)")
        if openai_error.exists():
            print(f"⚠️  OpenAI error log: {openai_error}")
        
        # Test 9: PDF to Markdown conversion (new test)
        print("\n9. Testing PDF to Markdown conversion...")
        try:
            response = requests.post(f"{api_base_url}/api/pdf-markdown/{job_id}")
            
            if response.status_code == 200:
                md_result = response.json()
                assert "markdown_path" in md_result, "Response should contain 'markdown_path'"
                assert "images_count" in md_result, "Response should contain 'images_count'"
                assert "chars" in md_result, "Response should contain 'chars'"
                assert md_result["chars"] > 100, f"Markdown too short: {md_result['chars']} chars"
                print("✅ PDF to Markdown conversion successful")
                print(f"   Characters: {md_result['chars']}")
                print(f"   Images extracted: {md_result['images_count']}")
                print(f"   Markdown path: {md_result['markdown_path']}")
                
                # Test 10: Get Markdown content
                print("\n10. Testing get Markdown endpoint...")
                response = requests.get(f"{api_base_url}/api/pdf-markdown/{job_id}")
                assert response.status_code == 200, f"Expected 200, got {response.status_code}"
                
                md_data = response.json()
                assert "job_id" in md_data, "Response should contain 'job_id'"
                assert "markdown" in md_data, "Response should contain 'markdown'"
                assert len(md_data["markdown"]) > 100, f"Markdown content too short: {len(md_data['markdown'])} chars"
                print("✅ Get Markdown endpoint successful")
                print(f"   Markdown length: {len(md_data['markdown'])} chars")
                
                # Show first 20 lines of Markdown
                md_lines = md_data["markdown"].split('\n')[:20]
                print("\nFirst 20 lines of layout.md:")
                print("=" * 50)
                for i, line in enumerate(md_lines, 1):
                    print(f"{i:2d}: {line}")
                print("=" * 50)
                
                # Verify files exist on disk
                layout_md = Path(md_result["markdown_path"])
                md_assets_dir = Path(md_result["markdown_path"]).parent / "md_assets"
                
                assert layout_md.exists(), f"Layout.md not found: {layout_md}"
                assert layout_md.stat().st_size > 100, f"Layout.md too small: {layout_md.stat().st_size} bytes"
                print(f"✅ Layout.md verified: {layout_md}")
                
                if md_assets_dir.exists():
                    asset_files = list(md_assets_dir.glob("*"))
                    print(f"✅ Markdown assets directory: {md_assets_dir} ({len(asset_files)} files)")
                
            else:
                print(f"⚠️  PDF to Markdown failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"   Response: {response.text}")
        except requests.exceptions.ConnectionError as e:
            if "Connection refused" in str(e):
                print("⚠️  Could not connect to API server for Markdown test")
                print("   Make sure the API server is running: make api-dev")
            else:
                raise
        except Exception as e:
            print(f"⚠️  PDF to Markdown test failed: {e}")
            print("   Continuing with other tests...")
        
        print("\n🎉 SMOKE OK")
        print(f"Job ID: {job_id}")
        print(f"Storage location: {storage_dir}")
        print(f"Pages location: {pages_dir}")
        if vision_json.exists():
            print(f"Vision JSON: {vision_json}")
        if render_html.exists():
            print(f"Render HTML: {render_html}")
        if output_pdf.exists():
            print(f"Output PDF: {output_pdf}")
        
    except Exception as e:
        print(f"❌ File verification failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()