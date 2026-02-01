# Asset Handling Implementation Summary

## Changes Made

### 1. Enhanced `/api/md-asset` Endpoint Security (`main.py`)

**Before:**
- Basic endpoint without path traversal protection
- Only served PNG files
- Used `{asset}` path parameter (limited to single path segment)

**After:**
- Added path traversal protection using `resolve()` and path prefix checking
- Supports multiple file types (PNG, JPEG, GIF, WebP)
- Uses `{asset:path}` parameter to support subdirectories
- Returns appropriate media types based on file extension

**Security Features:**
```python
# Prevent path traversal attacks
asset_path = asset_path.resolve()
assets_dir = assets_dir.resolve()
if not str(asset_path).startswith(str(assets_dir)):
    raise HTTPException(status_code=403, detail="Path traversal detected")
```

### 2. Improved Markdown to HTML Asset Replacement (`html_render.py`)

**Before:**
- Only replaced some `src="md_assets/` patterns
- Missing single quotes and `href` attributes
- Hardcoded API path

**After:**
- Comprehensive replacement of all asset references:
  - `src="md_assets/` → `src="{api_base}/api/md-asset/{job_id}/`
  - `src='md_assets/` → `src='{api_base}/api/md-asset/{job_id}/`
  - `src="./md_assets/` → `src="{api_base}/api/md-asset/{job_id}/`
  - `src='./md_assets/` → `src='{api_base}/api/md-asset/{job_id}/`
  - Same patterns for `href` attributes
- Uses configurable `API_BASE_URL` environment variable
- Added debug logging of first 5 image sources
- Preserves generated HTML for debugging

### 3. Playwright PDF Generation with File Navigation (`pdf_generate.py`)

**Added new function:**
```python
async def generate_pdf_from_html_file(html_path: Path, output_pdf: Path)
```

**Improvements:**
- Uses `page.goto()` instead of `page.set_content()`
- Navigates to file URL: `file://{html_path.resolve()}`
- Ensures relative assets are resolved correctly
- Better handling of network resources

### 4. Updated PDF Generation Pipeline

**Before:**
- Used `generate_pdf_from_html()` which calls `set_content()`

**After:**
- Uses `generate_pdf_from_html_file()` which calls `goto()`
- Maintains backward compatibility with legacy function

## Key Benefits

1. **Security**: Path traversal protection prevents unauthorized file access
2. **Reliability**: Absolute URLs ensure assets load correctly in PDFs
3. **Debugging**: Logging and preserved HTML files help troubleshoot issues
4. **Flexibility**: Configurable API base URL via environment variable
5. **Compatibility**: Supports various asset types and reference styles

## Environment Variables

- `API_BASE_URL`: Base URL for asset endpoints (default: "http://localhost:8000")

## Testing

Tests confirmed:
- ✅ Asset URLs are correctly replaced with absolute paths
- ✅ Path traversal attempts are properly blocked
- ✅ Various reference styles (quotes, relative paths) are handled
- ✅ Both `src` and `href` attributes are processed

## Acceptance Criteria Verification

✅ **Endpoint exists**: `/api/md-asset/{job_id}/{asset:path}` serves files from `jobs/{job_id}/md_assets/`
✅ **Path traversal protected**: Malicious paths like `../etc/passwd` are blocked
✅ **Absolute URLs in HTML**: All `md_assets/` references become `http://localhost:8000/api/md-asset/{job_id}/`
✅ **Playwright file navigation**: Uses `goto()` instead of `set_content()`
✅ **Debug mode**: HTML is preserved and image sources are logged
✅ **Images visible in browser**: Absolute URLs work when opening `markdown.html`
✅ **Images in PDF**: Playwright can access assets via absolute URLs