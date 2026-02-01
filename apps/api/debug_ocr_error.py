#!/usr/bin/env python3
"""
Debug script to reproduce and fix the OCR error.
"""

import asyncio
import sys
from pathlib import Path

# Add the api directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def test_ocr_with_actual_image():
    """Test OCR with an actual image file to reproduce the error."""
    
    # Look for an existing job with images
    data_dir = Path("../data/jobs")
    if not data_dir.exists():
        data_dir = Path("./data/jobs")
    
    # Find a job with md_assets
    job_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
    
    for job_dir in job_dirs:
        md_assets = job_dir / "md_assets"
        if md_assets.exists():
            images = list(md_assets.glob("*.png"))
            if images:
                image_path = images[0]
                print(f"Found image: {image_path}")
                
                # Test OCR service
                try:
                    from ocr_service import perform_ocr_on_image
                    print("Testing OCR on image...")
                    result = perform_ocr_on_image(image_path)
                    print(f"✅ OCR succeeded! Found {len(result)} text boxes")
                    for i, box in enumerate(result[:3]):  # Show first 3
                        print(f"  Box {i}: '{box['text']}' at {box['bbox']} (conf: {box['confidence']:.2f})")
                    return True
                except Exception as e:
                    print(f"❌ OCR failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
    
    print("No images found in any job directories")
    return False

def test_ocr_initialization():
    """Test OCR service initialization."""
    print("Testing OCR service initialization...")
    
    try:
        from ocr_service import ocr_service
        print(f"OCR Engine: {ocr_service.ocr_engine}")
        if ocr_service.ocr_engine is None:
            print("❌ No OCR engine available!")
            print("Please install either:")
            print("  pip install paddleocr paddlepaddle")
            print("OR")
            print("  pip install pytesseract pillow")
            print("  brew install tesseract  # On macOS")
            return False
        else:
            print(f"✅ Using {ocr_service.ocr_engine} engine")
            return True
    except Exception as e:
        print(f"❌ OCR initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Debugging OCR Error")
    print("=" * 50)
    
    # Test 1: Initialization
    init_success = test_ocr_initialization()
    
    if init_success:
        # Test 2: Actual OCR on image
        ocr_success = asyncio.run(test_ocr_with_actual_image())
        
        if ocr_success:
            print("\n🎉 All tests passed!")
        else:
            print("\n💥 OCR test failed!")
    else:
        print("\n💥 Initialization failed!")
    
    print("=" * 50)