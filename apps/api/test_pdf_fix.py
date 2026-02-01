#!/usr/bin/env python3
"""Test PDF generation with current fixes."""

import asyncio
import sys
from pathlib import Path

# Add the api directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def test_pdf_generation():
    """Test PDF generation with the current fixes."""
    
    # Create test files
    test_dir = Path("./test_pdf_fix")
    test_dir.mkdir(exist_ok=True)
    
    # Create test markdown
    markdown_content = """# Test Document

![Test Image](md_assets/page1_img1.png)

This is a test document with an image reference.
"""
    
    markdown_path = test_dir / "test.md"
    markdown_path.write_text(markdown_content, encoding='utf-8')
    
    # Create md_assets directory and dummy image
    assets_dir = test_dir / "md_assets"
    assets_dir.mkdir(exist_ok=True)
    (assets_dir / "page1_img1.png").write_text("dummy", encoding='utf-8')
    
    # Test PDF generation
    output_pdf = test_dir / "output.pdf"
    
    try:
        from html_render import generate_pdf_from_markdown
        await generate_pdf_from_markdown(markdown_path, output_pdf)
        print("✅ PDF generation succeeded!")
        print(f"Output file: {output_pdf}")
        return True
        
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    success = asyncio.run(test_pdf_generation())
    sys.exit(0 if success else 1)