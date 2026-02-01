#!/usr/bin/env python3
"""Test overlay quality improvements."""

import json
from pathlib import Path
from pdf_overlay_generate import is_safe_block, generate_overlay_pdf

def test_safe_block_policy():
    """Test the safe block detection policy."""
    
    # Test image dimensions
    img_width, img_height = 800, 600
    
    # Test cases
    test_cases = [
        # (block_data, expected_is_safe, description)
        ({
            "bbox": [100, 50, 300, 80],
            "type": "heading",
            "text": "Main Heading"
        }, True, "Small heading should be safe"),
        
        ({
            "bbox": [50, 100, 750, 150],  # Very wide but exceeds area limit
            "type": "heading",
            "text": "Wide Heading"
        }, False, "Wide heading should not be safe (exceeds area limit)"),
        
        ({
            "bbox": [100, 200, 200, 400],
            "type": "paragraph",
            "text": "Long paragraph text that should not be replaced"
        }, False, "Large paragraph should not be safe"),
        
        ({
            "bbox": [150, 250, 200, 280],
            "type": "paragraph",
            "text": "Small paragraph"
        }, True, "Small paragraph should be safe"),
        
        ({
            "bbox": [100, 300, 400, 320],
            "type": "caption",
            "text": "Figure 1: Description"
        }, True, "Caption should be safe"),
        
        ({
            "bbox": [50, 50, 750, 550],
            "type": "paragraph",
            "text": "Full page paragraph"
        }, False, "Full page paragraph should not be safe"),
        
        ({
            "bbox": [10, 10, 15, 15],
            "type": "heading",
            "text": "Tiny"
        }, False, "Too small block should not be safe"),
    ]
    
    print("Testing safe block policy...")
    print("=" * 50)
    
    passed = 0
    total = len(test_cases)
    
    for i, (block, expected, description) in enumerate(test_cases):
        is_safe, reason = is_safe_block(block, img_width, img_height)
        status = "✓ PASS" if is_safe == expected else "✗ FAIL"
        print(f"{i+1:2d}. {status} - {description}")
        print(f"     Expected: {expected}, Got: {is_safe} ({reason})")
        
        if is_safe == expected:
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    return passed == total


def test_overlay_generation():
    """Test overlay PDF generation with scope policies."""
    
    # Create test data
    test_vision_data = {
        "pages": [
            {
                "page": 1,
                "blocks": [
                    {
                        "bbox": [100, 50, 300, 80],
                        "type": "heading",
                        "text": "Main Heading"
                    },
                    {
                        "bbox": [100, 100, 200, 130],
                        "type": "caption",
                        "text": "Figure 1: Chart"
                    },
                    {
                        "bbox": [50, 150, 750, 500],
                        "type": "paragraph",
                        "text": "This is a long paragraph that covers most of the page and should not be replaced because it's too large."
                    },
                    {
                        "bbox": [150, 520, 180, 540],
                        "type": "paragraph",
                        "text": "Small note"
                    }
                ]
            }
        ],
        "meta": {
            "job_id": "test-overlay-job",
            "target_language": "en"
        }
    }
    
    # Create temporary job directory
    test_dir = Path("test_overlay_temp")
    test_dir.mkdir(exist_ok=True)
    
    pages_dir = test_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    
    # Create a minimal valid PNG file (1x1 pixel)
    dummy_png = pages_dir / "page_1.png"
    # Minimal 1x1 transparent PNG
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    with open(dummy_png, "wb") as f:
        f.write(png_data)
    
    print("\nTesting overlay generation...")
    print("=" * 50)
    
    try:
        # Test different scopes
        scopes = ["safe", "headings", "all"]
        
        for scope in scopes:
            print(f"\nTesting scope: {scope}")
            
            # Generate overlay PDF
            pdf_bytes = generate_overlay_pdf(
                test_dir,
                test_vision_data,
                dpi=144,
                debug=False,
                overlay_scope=scope
            )
            
            # Save PDF
            pdf_path = test_dir / f"test_overlay_{scope}.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            
            print(f"  ✓ Generated PDF: {len(pdf_bytes)} bytes")
            
            # Check report
            report_path = test_dir / "overlay_report.json"
            if report_path.exists():
                with open(report_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                
                print(f"  ✓ Report: {report['total_blocks']} total, "
                      f"{report['replaced_blocks']} replaced, "
                      f"{report['skipped_blocks']} skipped")
                
                if report["skip_reasons"]:
                    print("  Skip reasons:")
                    for reason, count in report["skip_reasons"].items():
                        print(f"    - {reason}: {count}")
            else:
                print("  ✗ No report generated")
        
        print("\n✓ All scope tests completed")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("✓ Cleaned up test directory")


def main():
    """Run all overlay quality tests."""
    print("Overlay Quality Improvement Tests")
    print("=" * 60)
    
    # Test 1: Safe block policy
    policy_passed = test_safe_block_policy()
    
    # Test 2: Overlay generation
    generation_passed = test_overlay_generation()
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print(f"Safe block policy: {'PASS' if policy_passed else 'FAIL'}")
    print(f"Overlay generation: {'PASS' if generation_passed else 'FAIL'}")
    
    if policy_passed and generation_passed:
        print("\n🎉 All tests passed! Overlay quality improvements are working.")
        return 0
    else:
        print("\n❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    exit(main())