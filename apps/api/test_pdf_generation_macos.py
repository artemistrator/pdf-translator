#!/usr/bin/env python3
"""
Test PDF generation on macOS with fallback mechanisms.
"""

import asyncio
import sys
from pathlib import Path

# Add the api directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def test_pdf_generation():
    """Test PDF generation with the improved fallback mechanisms."""
    
    # Create test files
    test_dir = Path("./test_pdf_macos")
    test_dir.mkdir(exist_ok=True)
    
    # Create test markdown with image reference
    markdown_content = """# Test Document
    
![Test Image](md_assets/page1_img1.png)

This is a test document with an image reference to test PDF generation on macOS.
"""

    markdown_path = test_dir / "test.md"
    markdown_path.write_text(markdown_content, encoding='utf-8')
    
    # Create md_assets directory and dummy image
    assets_dir = test_dir / "md_assets"
    assets_dir.mkdir(exist_ok=True)
    dummy_image_path = assets_dir / "page1_img1.png"
    
    # Create a simple dummy PNG image (1x1 pixel)
    dummy_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa75\x82\x00\x00\x00\x00IEND\xaeB`\x82'
    dummy_image_path.write_bytes(dummy_png)
    
    # Test PDF generation
    output_pdf = test_dir / "output.pdf"
    
    try:
        from html_render import generate_pdf_from_markdown
        print("🚀 Starting PDF generation test...")
        await generate_pdf_from_markdown(markdown_path, output_pdf)
        print("✅ PDF generation succeeded!")
        print(f"Output file: {output_pdf}")
        print(f"File size: {output_pdf.stat().st_size} bytes")
        return True
        
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Check if it's a known error that should have detailed diagnostics
        error_str = str(e).lower()
        if "chromium" in error_str or "playwright" in error_str:
            print("\n🔧 Diagnostic information:")
            if "executable doesn't exist" in error_str:
                print("  - Issue: Playwright Chromium not installed")
                print("  - Solution: Run 'make api-playwright-install'")
            elif "browser closed" in error_str:
                print("  - Issue: Browser crashed")
                print("  - Solution: Check system resources or try system Chrome")
            elif "permission denied" in error_str:
                print("  - Issue: Permission problem with browser executable")
                print("  - Solution: Fix file permissions")
            elif "sandbox" in error_str and "signal 6" in error_str:
                print("  - Issue: Sandbox crash")
                print("  - Solution: Try fresh Playwright install or system Chrome")
            else:
                print("  - Issue: Unknown browser error")
                print("  - Solution: Check detailed error message above")
                
            print("\n📋 Fallback options:")
            print("  1. Use /api/download-html/{job_id} to get HTML file")
            print("  2. Open HTML in browser and use Print → Save as PDF")
            
        return False
    finally:
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    print("🧪 Testing PDF Generation with macOS Fallback Mechanisms")
    print("=" * 60)
    
    success = asyncio.run(test_pdf_generation())
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests PASSED!")
    else:
        print("💥 Some tests FAILED!")
    
    sys.exit(0 if success else 1)