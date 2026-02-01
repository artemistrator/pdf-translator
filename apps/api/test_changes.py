#!/usr/bin/env python3
"""Test the implemented changes for HTML image embedding."""

import json
from pathlib import Path
from html_render import vision_to_html

def test_html_embedding_always_enabled():
    """Test that HTML rendering always embeds images when job_dir is provided."""
    
    # Create test data
    test_vision_data = {
        "pages": [
            {
                "page_number": 1,
                "image_path": "pages/page_1.png",
                "blocks": []
            }
        ],
        "meta": {
            "job_id": "test-job-123",
            "target_language": "en"
        }
    }
    
    # Create temporary job directory structure
    test_dir = Path("test_job_temp")
    test_dir.mkdir(exist_ok=True)
    
    pages_dir = test_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    
    # Create a dummy PNG file
    dummy_png = pages_dir / "page_1.png"
    with open(dummy_png, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")  # PNG header
    
    print("✓ Created test directory structure")
    
    try:
        # Test 1: HTML generation with embedding enabled
        html_content = vision_to_html(
            test_vision_data, 
            "Test Document", 
            job_dir=test_dir, 
            embed_page_images=True
        )
        
        # Verify base64 embedding
        assert "data:image/png;base64," in html_content, "Base64 embedding not found"
        print("✓ HTML contains base64 embedded images")
        
        # Save for inspection
        render_path = test_dir / "render.html"
        with open(render_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"✓ HTML saved to {render_path}")
        print(f"  File size: {len(html_content)} characters")
        
        # Show snippet
        print("\nFirst 500 characters:")
        print(html_content[:500])
        
        # Test 2: Verify job_dir validation works
        try:
            vision_to_html(test_vision_data, "Test", job_dir=None, embed_page_images=True)
            assert False, "Should have raised ValueError for missing job_dir"
        except ValueError as e:
            assert "job_dir is required" in str(e)
            print("✓ job_dir validation works correctly")
        
        print("\n🎉 All tests passed!")
        
    finally:
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("✓ Cleaned up test directory")

if __name__ == "__main__":
    test_html_embedding_always_enabled()