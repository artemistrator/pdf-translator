#!/usr/bin/env python3
"""Test script to verify HTML generation with embedded images."""

import json
from pathlib import Path
from html_render import vision_to_html

# Test with existing job data
job_id = "e2c298ac-4c1d-4eb0-9432-f3beff1c45e1"
job_dir = Path("/Users/artem/Desktop/pdf translator/data/jobs") / job_id

# Read vision data
vision_path = job_dir / "edited.json"
if not vision_path.exists():
    vision_path = job_dir / "vision.json"

with open(vision_path, "r", encoding="utf-8") as f:
    vision_data = json.load(f)

# Generate HTML with embedded images
html_content = vision_to_html(vision_data, "Test Document", job_dir=job_dir, embed_page_images=True)

# Save to file for inspection
output_path = Path("./test_render.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ HTML generated and saved to {output_path}")
print(f"✅ File size: {len(html_content)} characters")

# Check for base64 images
if "data:image/png;base64," in html_content:
    print("✅ Contains base64 embedded images")
else:
    print("❌ No base64 images found")

# Show first 500 characters as example
print("\nFirst 500 characters of HTML:")
print(html_content[:500])
