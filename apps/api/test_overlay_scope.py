#!/usr/bin/env python3
"""Test overlay scope functionality."""

import json
from pathlib import Path
from pdf_overlay_generate import should_replace_block, generate_overlay_pdf

def test_overlay_scopes():
    """Test the three overlay scopes with various block types."""
    
    # Test image dimensions
    img_width, img_height = 800, 600
    
    # Test blocks
    test_blocks = [
        {
            "bbox": [100, 50, 300, 80],
            "type": "heading",
            "text": "Main Title"
        },
        {
            "bbox": [50, 100, 750, 150],  # Wide heading
            "type": "title",
            "text": "Very Wide Title"
        },
        {
            "bbox": [100, 200, 200, 230],
            "type": "caption",
            "text": "Figure 1: Chart"
        },
        {
            "bbox": [150, 250, 650, 500],  # Large paragraph
            "type": "paragraph",
            "text": "This is a very long paragraph that covers most of the page and should definitely not be replaced."
        },
        {
            "bbox": [150, 520, 180, 540],  # Small paragraph
            "type": "paragraph",
            "text": "Small note"
        },
        {
            "bbox": [300, 300, 350, 320],
            "type": "label",
            "text": "A"
        }
    ]
    
    print("Testing Overlay Scopes")
    print("=" * 50)
    
    scopes = ["headings", "safe", "all"]
    
    for scope in scopes:
        print(f"\nSCOPE: {scope.upper()}")
        print("-" * 30)
        
        for i, block in enumerate(test_blocks):
            should_replace, reason = should_replace_block(block, img_width, img_height, scope)
            status = "✓ REPLACE" if should_replace else "✗ SKIP"
            block_type = block["type"]
            bbox = block["bbox"]
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            print(f"{i+1:2d}. [{block_type:10}] {status} - {reason}")
            print(f"     BBox: {bbox} ({width}×{height}px)")
    
    return True


def test_overlay_report_generation():
    """Test that overlay report is generated with detailed information."""
    
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
                        "text": "Large paragraph that should be skipped"
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
            "job_id": "test-scope-job",
            "target_language": "en"
        }
    }
    
    # Create temporary job directory
    test_dir = Path("test_scope_temp")
    test_dir.mkdir(exist_ok=True)
    
    pages_dir = test_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    
    # Create a minimal valid PNG file (1x1 pixel)
    dummy_png = pages_dir / "page_1.png"
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    with open(dummy_png, "wb") as f:
        f.write(png_data)
    
    print("\n\nTesting Overlay Report Generation")
    print("=" * 50)
    
    try:
        # Test each scope
        for scope in ["headings", "safe", "all"]:
            print(f"\nTesting scope: {scope}")
            
            # Generate overlay PDF
            pdf_bytes = generate_overlay_pdf(
                test_dir,
                test_vision_data,
                dpi=144,
                debug=False,
                overlay_scope=scope
            )
            
            print(f"  ✓ Generated PDF: {len(pdf_bytes)} bytes")
            
            # Check report exists and has detailed information
            report_path = test_dir / "overlay_report.json"
            if report_path.exists():
                with open(report_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                
                print(f"  ✓ Report generated:")
                print(f"    - Total blocks: {report['total_blocks']}")
                print(f"    - Replaced blocks: {report['replaced_blocks']}")
                print(f"    - Skipped blocks: {report['skipped_blocks']}")
                
                if report["skip_reasons"]:
                    print(f"    - Skip reasons:")
                    for reason, count in report["skip_reasons"].items():
                        print(f"      * {reason}: {count}")
                
                if report["replaced_details"]:
                    print(f"    - Replaced details:")
                    for detail in report["replaced_details"][:2]:  # Show first 2
                        print(f"      * Page {detail['page']}, Block {detail['block_index']}: "
                              f"{detail['type']} - {detail['replacement_reason']}")
                        print(f"        BBox: {detail['bbox_px']}")
                else:
                    print(f"    - No blocks were replaced")
            else:
                print("  ✗ No report generated")
        
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
    """Run all overlay scope tests."""
    print("Overlay Scope Control Tests")
    print("=" * 60)
    
    # Test 1: Scope logic
    test1_passed = test_overlay_scopes()
    
    # Test 2: Report generation
    test2_passed = test_overlay_report_generation()
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print(f"Scope logic test: {'PASS' if test1_passed else 'FAIL'}")
    print(f"Report generation test: {'PASS' if test2_passed else 'FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Overlay scope controls are working.")
        return 0
    else:
        print("\n❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    exit(main())