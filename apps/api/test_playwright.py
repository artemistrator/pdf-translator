#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def test_playwright():
    try:
        async with async_playwright() as p:
            print("Available browsers:", [b.name for b in p.chromium.__dict__.get('_drivers', [])])
            print("Chromium executable path:", p.chromium.executable_path)
            browser = await p.chromium.launch(headless=True)
            print("SUCCESS: Chromium launched")
            await browser.close()
            return True
    except Exception as e:
        print("ERROR:", str(e))
        return False

if __name__ == "__main__":
    result = asyncio.run(test_playwright())
    print("Result:", result)