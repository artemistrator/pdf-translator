"""PDF generation utilities using Playwright."""

import asyncio
import logging
import sys
from typing import Optional
from pathlib import Path

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)


async def html_to_pdf_bytes_async(html: str) -> bytes:
    """
    Convert HTML string to PDF bytes using Playwright with fallback mechanisms.
    
    Args:
        html: HTML content as string
        
    Returns:
        PDF content as bytes
        
    Raises:
        RuntimeError: If Playwright or browser is not available
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"
        )
    
    # Try different browser launch methods in order of preference
    launch_methods = [
        ("chromium", {}),
        ("chromium", {"channel": "chrome"}),
        ("chromium", {"executable_path": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}),
        ("chromium", {"executable_path": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"})
    ]
    
    last_exception = None
    
    for browser_type, kwargs in launch_methods:
        try:
            logger.info(f"Attempting to launch {browser_type} with args: {kwargs}")
            
            async with async_playwright() as p:
                # Add safe arguments for macOS compatibility
                launch_args = {
                    "headless": True,
                    "args": [
                        "--no-sandbox",
                        "--disable-setuid-sandbox", 
                        "--disable-dev-shm-usage",
                        "--disable-gpu"
                    ]
                }
                launch_args.update(kwargs)
                
                browser = await getattr(p, browser_type).launch(**launch_args)
                try:
                    page = await browser.new_page()
                    
                    # Set content and wait for network idle
                    await page.set_content(html, wait_until="networkidle")
                    
                    # Generate PDF
                    pdf_bytes = await page.pdf(
                        format="A4",
                        print_background=True,
                        prefer_css_page_size=True,
                        margin={
                            "top": "0mm",
                            "right": "0mm", 
                            "bottom": "0mm",
                            "left": "0mm"
                        }
                    )
                    
                    logger.info(f"Successfully generated PDF using {browser_type}")
                    return pdf_bytes
                finally:
                    await browser.close()
                    
        except Exception as e:
            error_msg = str(e).lower()
            logger.warning(f"Failed to launch {browser_type} with {kwargs}: {e}")
            last_exception = e
            
            # Early exit for certain fatal errors
            if "permission denied" in error_msg or "access denied" in error_msg:
                raise RuntimeError(
                    f"Permission denied when launching browser. "
                    f"Try: chmod +x /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome"
                ) from e
            elif "sandbox" in error_msg and ("signal 6" in error_msg or "sigsegv" in error_msg):
                raise RuntimeError(
                    f"Sandbox error occurred. "
                    f"Try: make api-playwright-install or use system Chrome"
                ) from e
            
            # Continue to next method
            continue
    
    # If all methods failed
    if last_exception:
        error_details = str(last_exception)
        if "executable doesn't exist" in error_details.lower():
            debug_hint = "Install Playwright Chromium: make api-playwright-install"
        elif "browser closed" in error_details.lower():
            debug_hint = "Browser crashed unexpectedly. Check system resources and try again."
        elif "permission denied" in error_details.lower():
            debug_hint = "Permission issue with browser executable. Check file permissions."
        elif "sandbox" in error_details.lower() and "signal 6" in error_details.lower():
            debug_hint = "Sandbox crash. Try installing fresh Playwright browsers or use system Chrome."
        else:
            debug_hint = "Unknown browser launch error. Check logs for details."
            
        raise RuntimeError(
            f"All browser launch attempts failed. Last error: {error_details}. "
            f"Debug hint: {debug_hint}"
        ) from last_exception
    
    raise RuntimeError("Failed to generate PDF: No working browser found")


# Keep sync wrapper for CLI usage only
def html_to_pdf_bytes_sync(html: str) -> bytes:
    """
    Synchronous wrapper for HTML to PDF conversion (for CLI usage).
    
    Args:
        html: HTML content as string
        
    Returns:
        PDF content as bytes
    """
    return asyncio.run(html_to_pdf_bytes_async(html))


# Alias for backward compatibility
html_to_pdf_bytes = html_to_pdf_bytes_async


async def generate_pdf_from_html_file(html_path: Path, output_pdf: Path):
    """
    Generate PDF from HTML file using Playwright with fallback mechanisms.
    This ensures relative assets are resolved correctly.
    
    Args:
        html_path: Path to HTML file
        output_pdf: Output PDF path
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"
        )
    
    # Try different browser launch methods in order of preference
    launch_methods = [
        ("chromium", {}),
        ("chromium", {"channel": "chrome"}),
        ("chromium", {"executable_path": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}),
        ("chromium", {"executable_path": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"})
    ]
    
    last_exception = None
    
    for browser_type, kwargs in launch_methods:
        try:
            logger.info(f"Attempting to launch {browser_type} with args: {kwargs}")
            
            async with async_playwright() as p:
                # Add safe arguments for macOS compatibility
                launch_args = {
                    "headless": True,
                    "args": [
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage", 
                        "--disable-gpu"
                    ]
                }
                launch_args.update(kwargs)
                
                browser = await getattr(p, browser_type).launch(**launch_args)
                try:
                    page = await browser.new_page()
                    
                    # Navigate to the HTML file (ensures relative paths work)
                    await page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
                    await page.emulate_media(media="screen")
                    
                    # Generate PDF
                    pdf_bytes = await page.pdf(
                        format="A4",
                        print_background=True,
                        prefer_css_page_size=True,
                        margin={
                            "top": "0mm",
                            "right": "0mm",
                            "bottom": "0mm", 
                            "left": "0mm"
                        }
                    )
                    
                    # Write to output file
                    output_pdf.parent.mkdir(parents=True, exist_ok=True)
                    output_pdf.write_bytes(pdf_bytes)
                    
                    logger.info(f"Successfully generated PDF using {browser_type}")
                    return
                finally:
                    await browser.close()
                    
        except Exception as e:
            error_msg = str(e).lower()
            logger.warning(f"Failed to launch {browser_type} with {kwargs}: {e}")
            last_exception = e
            
            # Early exit for certain fatal errors
            if "permission denied" in error_msg or "access denied" in error_msg:
                raise RuntimeError(
                    f"Permission denied when launching browser. "
                    f"Try: chmod +x /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome"
                ) from e
            elif "sandbox" in error_msg and ("signal 6" in error_msg or "sigsegv" in error_msg):
                raise RuntimeError(
                    f"Sandbox error occurred. "
                    f"Try: make api-playwright-install or use system Chrome"
                ) from e
            
            # Continue to next method
            continue
    
    # If all methods failed
    if last_exception:
        error_details = str(last_exception)
        if "executable doesn't exist" in error_details.lower():
            debug_hint = "Install Playwright Chromium: make api-playwright-install"
        elif "browser closed" in error_details.lower():
            debug_hint = "Browser crashed unexpectedly. Check system resources and try again."
        elif "permission denied" in error_details.lower():
            debug_hint = "Permission issue with browser executable. Check file permissions."
        elif "sandbox" in error_details.lower() and "signal 6" in error_details.lower():
            debug_hint = "Sandbox crash. Try installing fresh Playwright browsers or use system Chrome."
        else:
            debug_hint = "Unknown browser launch error. Check logs for details."
            
        raise RuntimeError(
            f"All browser launch attempts failed. Last error: {error_details}. "
            f"Debug hint: {debug_hint}"
        ) from last_exception
    
    raise RuntimeError("Failed to generate PDF: No working browser found")


async def generate_pdf_from_html(html_path: Path, output_pdf: Path):
    """
    Generate PDF from HTML file using Playwright (legacy method using set_content).
    
    Args:
        html_path: Path to HTML file
        output_pdf: Output PDF path
    """
    # Read HTML content
    html_content = html_path.read_text(encoding='utf-8')
    
    # Generate PDF bytes
    pdf_bytes = await html_to_pdf_bytes_async(html_content)
    
    # Write to output file
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    output_pdf.write_bytes(pdf_bytes)
