#!/usr/bin/env python3
"""Diagnostic script to check Playwright Chromium issues."""

import asyncio
from playwright.async_api import async_playwright
import sys

async def diagnose_chromium():
    """Diagnose Chromium launch issues."""
    print("🔍 Diagnosing Playwright Chromium...")
    
    try:
        async with async_playwright() as p:
            print(f"✅ Playwright context created")
            print(f" Chromium executable: {p.chromium.executable_path}")
            
            # Try to launch with more verbose logging
            print("🚀 Attempting to launch Chromium...")
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox']  # Try to bypass sandbox
            )
            print("✅ Chromium launched successfully")
            
            # Try to create a page
            page = await browser.new_page()
            print("✅ Page created successfully")
            
            # Try a simple operation
            await page.goto('about:blank')
            print("✅ Navigated to about:blank")
            
            # Try to generate a simple PDF
            pdf_bytes = await page.pdf()
            print(f"✅ PDF generated successfully ({len(pdf_bytes)} bytes)")
            
            await browser.close()
            print("✅ Browser closed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, '__cause__'):
            print(f"Cause: {e.__cause__}")
        return False

if __name__ == "__main__":
    print("Running Chromium diagnostics...")
    success = asyncio.run(diagnose_chromium())
    if success:
        print("\n🎉 Chromium is working correctly!")
    else:
        print("\n💥 Chromium has issues that need to be addressed")
    sys.exit(0 if success else 1)