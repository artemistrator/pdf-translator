from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
import json
import base64
from dotenv import load_dotenv
from storage import storage_manager, PROJECT_ROOT, resolve_storage_dir
import uuid
from datetime import datetime
from pathlib import Path
# Import processing modules
from pdf_render import render_pdf_to_pngs
from openai_vision import analyze_document_images, translate_image_with_openai_vision
from openai import OpenAI
import base64
from html_render import vision_to_html, generate_pdf_from_markdown
from pdf_generate import html_to_pdf_bytes_async
from pdf_overlay_generate import generate_overlay_pdf
from debug_render import render_all_debug_pages
from pdf_to_markdown import pdf_to_markdown_with_assets
from ocr_service import perform_ocr_on_image
from preview_overlay import generate_preview_overlay

# Pydantic models for OCR translations
class Box(BaseModel):
    id: str
    x: float
    y: float
    w: float
    h: float
    text: str
    font_size: Optional[float] = None
    color: Optional[str] = "#000000"

class BoxesPayload(BaseModel):
    boxes: List[Box]

# Pydantic model for vision translation
class VisionTranslatePayload(BaseModel):
    target_language: str

# Load environment variables with priority: apps/api/.env → .env
from pathlib import Path
api_env_path = Path(__file__).parent / ".env"
root_env_path = Path(__file__).parents[2] / ".env"

# Load API-specific .env first (higher priority)
if api_env_path.exists():
    load_dotenv(dotenv_path=api_env_path, override=True)

# Load root .env as fallback
if root_env_path.exists():
    load_dotenv(dotenv_path=root_env_path, override=False)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Document Translator API",
    description="Vision-LLM Document Translation Service",
    version="0.1.0"
)

# Log startup information
logger.info(f"Working directory: {Path.cwd()}")
storage_dir = resolve_storage_dir()
logger.info(f"Storage directory: {storage_dir}")

# Configure CORS for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:3004", "http://localhost:3005", "http://localhost:3006", "http://localhost:3007", "http://localhost:3007"],  # Next.js dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "document-translator-api",
        "version": "0.1.0"
    }

@app.post("/api/translate")
async def create_translation_job(
    file: UploadFile = File(...),
    target_language: str = Form(...)
):
    """
    Create a new translation job
    
    Args:
        file: PDF file to translate
        target_language: Target language code (e.g., 'en', 'es', 'de')
        
    Returns:
        JSON with job_id
    """
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have .pdf extension"
        )
    
    # Validate file size (20MB limit)
    content = await file.read()
    file_size = len(content)
    if file_size > 20 * 1024 * 1024:  # 20MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 20MB limit"
        )
    
    # Reset file pointer
    await file.seek(0)
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save file
    input_path = storage_manager.save_uploadfile(job_id, file, "input.pdf")
    
    # Create job data
    job_data = {
        "job_id": job_id,
        "status": "queued",
        "target_language": target_language,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "input_path": str(input_path),
        "output_path": None,
        "error": None
    }
    
    # Save job metadata
    storage_manager.save_job(job_id, job_data)
    
    # Log operation details
    logger.info(f"Created job: {job_id}")
    logger.info(f"Input file saved to: {input_path}")
    logger.info(f"Job metadata saved to: {storage_manager.jobs_dir / job_id / 'job.json'}")
    
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Get job status
    
    Args:
        job_id: Job identifier
        
    Returns:
        JSON with job status
    """
    try:
        job_data = storage_manager.load_job(job_id)
        return {
            "job_id": job_id,
            "status": job_data["status"],
            "message": job_data.get("error", "")
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )


@app.post("/api/process/{job_id}")
async def process_job(
    job_id: str,
    force: bool = Query(False, description="Force reprocessing even if vision.json exists")
):
    """
    Process a translation job: PDF → PNG → Vision Analysis → vision.json
    
    Args:
        job_id: Job identifier
        force: Force reprocessing even if vision.json exists (default: False)
        
    Returns:
        JSON with processing result or error
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Load job data
    job_data = storage_manager.load_job(job_id)
    
    # Idempotency check - if already done and not forced, return early
    job_dir = storage_manager.jobs_dir / job_id
    vision_json_path = job_dir / "vision.json"
    
    if not force and job_data.get("status") == "done" and vision_json_path.exists():
        logger.info(f"Job {job_id} already completed, returning cached result")
        return {
            "job_id": job_id,
            "status": "done",
            "message": "Using cached result"
        }
    
    # Record processing start time
    processing_started_at = datetime.utcnow().isoformat() + "Z"
    
    # Update status to processing
    job_data["status"] = "processing"
    job_data["error"] = None
    job_data["processing_started_at"] = processing_started_at
    storage_manager.save_job(job_id, job_data)
    
    try:
        # Get input PDF path
        input_path_str = job_data.get("input_path")
        if not input_path_str:
            raise ValueError("input_path not found in job data")
        
        input_pdf_path = Path(input_path_str)
        if not input_pdf_path.exists():
            raise FileNotFoundError(f"Input PDF not found: {input_pdf_path}")
        
        # Get configuration from environment
        max_pages = int(os.getenv("VISION_MAX_PAGES", "2"))
        dpi = int(os.getenv("VISION_DPI", "144"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        target_language = job_data.get("target_language", "en")
        use_structured_outputs = os.getenv("USE_STRUCTURED_OUTPUTS", "true").lower() == "true"
        
        # Create pages directory
        pages_dir = job_dir / "pages"
        
        # Render PDF to PNGs
        png_paths = render_pdf_to_pngs(
            input_pdf_path=input_pdf_path,
            out_dir=pages_dir,
            max_pages=max_pages,
            dpi=dpi
        )
        
        if not png_paths:
            raise ValueError("No pages were rendered")
        
        # Record number of pages rendered
        vision_pages_rendered = len(png_paths)
        
        # Attempt OpenAI analysis
        try:
            vision_result = analyze_document_images(
                image_paths=png_paths,
                target_language=target_language,
                model=None,  # Let module get from env
                use_structured_outputs=None,  # Let module get from env
                job_dir=job_dir  # Pass job_dir for debug artifacts
            )
            
            # Record processing finish time
            processing_finished_at = datetime.utcnow().isoformat() + "Z"
            
            # Add metadata
            vision_result["meta"] = {
                "job_id": job_id,
                "target_language": target_language,
                "processed_at": processing_finished_at,
                "model": model,
                "vision_pages_rendered": vision_pages_rendered
            }
            
            # Save vision.json
            with open(vision_json_path, "w", encoding="utf-8") as f:
                json.dump(vision_result, f, indent=2, ensure_ascii=False)
            
            # Update job with completion data
            storage_manager.save_job(job_id, {
                **job_data,
                "status": "done",
                "output_path": str(vision_json_path),
                "error": None,
                "processing_finished_at": processing_finished_at,
                "vision_pages_rendered": vision_pages_rendered,
                "openai_model_used": model
            })
            
            logger.info(f"Job {job_id} completed successfully")
            return {
                "job_id": job_id,
                "status": "done"
            }
            
        except RuntimeError as e:
            # Handle missing API key
            if "OPENAI_API_KEY is not set" in str(e):
                error_msg = "OPENAI_API_KEY is not set"
                storage_manager.save_job(job_id, {
                    **job_data,
                    "status": "error",
                    "error": error_msg,
                    "processing_finished_at": datetime.utcnow().isoformat() + "Z"
                })
                # Return error response directly
                return {
                    "job_id": job_id,
                    "status": "error",
                    "error": error_msg
                }
            else:
                raise
                
    except Exception as e:
        # Handle all other errors
        error_msg = str(e)
        processing_finished_at = datetime.utcnow().isoformat() + "Z"
        
        storage_manager.save_job(job_id, {
            **job_data,
            "status": "error",
            "error": error_msg,
            "processing_finished_at": processing_finished_at
        })
        
        logger.error(f"Job {job_id} failed: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.post("/api/generate/{job_id}")
async def generate_pdf(
    job_id: str, 
    mode: str = Query("html", description="Generation mode: 'html' or 'overlay'"),
    debug_overlay: bool = Query(False, description="Enable debug mode for overlay (red outlines)"),
    overlay_scope: str = Query("headings", description="Overlay replacement scope: 'headings', 'safe', or 'all'")
):
    """
    Generate PDF from vision analysis result.
    
    Prerequisites:
    - job.status == "done"
    - vision.json exists
    
    Query Parameters:
    - mode: "html" (default) or "overlay"
    - overlay_scope: "headings" (default), "safe", or "all"
    
    Process:
    - Reads vision.json or edited.json
    - If mode=="html": generates HTML → PDF using Playwright
    - If mode=="overlay": generates overlay PDF using PyMuPDF
    - Saves to jobs/{job_id}/output.pdf or output_overlay.pdf
    - Updates job.json with output_path
    
    Returns:
        JSON with job status and output type
    """
    # Validate overlay_scope parameter
    valid_scopes = {"headings", "safe", "all"}
    if overlay_scope not in valid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid overlay_scope. Must be one of: {', '.join(valid_scopes)}"
        )
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Load job data
    job_data = storage_manager.load_job(job_id)
    
    # Check prerequisites
    if job_data.get("status") != "done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job must be in 'done' status. Run /api/process first."
        )
    
    job_dir = storage_manager.jobs_dir / job_id
    
    # Validate mode parameter
    if mode not in ["html", "overlay"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Must be 'html' or 'overlay'"
        )
    
    # Priority: edited.json > vision.json
    edited_json_path = job_dir / "edited.json"
    vision_json_path = job_dir / "vision.json"
    
    source_file = edited_json_path if edited_json_path.exists() else vision_json_path
    
    if not source_file.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vision data not found. Run /api/process first."
        )
    
    # Read vision/edited data
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            vision_data = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read vision data: {e}"
        )
    
    # Generate document title
    title = job_data.get("filename", f"Document {job_id}")
    
    try:
        if mode == "html":
            # Check if page images exist before rendering
            pages_dir = job_dir / "pages"
            first_page_image = pages_dir / "page_1.png"
            if not first_page_image.exists():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Run /api/process first (missing rendered page images)"
                )
            
            # Generate HTML with embedded page images (always embed)
            html_content = vision_to_html(vision_data, title, job_dir=job_dir, embed_page_images=True)
            render_html_path = job_dir / "render.html"
            
            with open(render_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Verify embedded images are present
            if "data:image/png;base64," not in html_content:
                # Save the problematic HTML for debugging
                with open(render_html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="HTML render missing embedded images; check pages/page_*.png exists"
                )
            
            # Log first img tag snippet for verification
            import re
            img_match = re.search(r'<img[^>]+src="data:image/png;base64,[^"]+"', html_content)
            if img_match:
                logger.info(f"Embedded image found: {img_match.group()[:300]}...")
            else:
                logger.warning("No embedded image tag found in HTML")
            
            # Generate PDF using Playwright
            pdf_bytes = await html_to_pdf_bytes_async(html_content)
            output_pdf_path = job_dir / "output.pdf"
            
            with open(output_pdf_path, "wb") as f:
                f.write(pdf_bytes)
            
            # Update job data
            storage_manager.save_job(job_id, {
                **job_data,
                "render_html_path": str(render_html_path),
                "output_path": str(output_pdf_path)
            })
            
            logger.info(f"HTML PDF generated for job {job_id}")
            
        else:  # mode == "overlay"
            # Generate overlay PDF using PyMuPDF
            # Get DPI from job metadata or use default
            dpi = job_data.get("dpi", 144)
            
            pdf_bytes = generate_overlay_pdf(
                job_dir, 
                vision_data, 
                dpi, 
                debug=debug_overlay,
                overlay_scope=overlay_scope
            )
            output_filename = "output_overlay_debug.pdf" if debug_overlay else "output_overlay.pdf"
            output_pdf_path = job_dir / output_filename
            
            with open(output_pdf_path, "wb") as f:
                f.write(pdf_bytes)
            
            # Update job data (keep render_html_path if it exists from previous HTML generation)
            updated_job_data = {
                **job_data,
                "output_path": str(output_pdf_path)
            }
            
            # Preserve render_html_path if it exists
            if "render_html_path" in job_data:
                updated_job_data["render_html_path"] = job_data["render_html_path"]
                
            storage_manager.save_job(job_id, updated_job_data)
            
            logger.info(f"Overlay PDF generated for job {job_id}")
        
        return {
            "job_id": job_id,
            "status": "done",
            "output": "pdf",
            "mode": mode
        }
        
    except RuntimeError as e:
        if "chromium" in str(e).lower() or "playwright" in str(e).lower():
            error_msg = f"{str(e)}. Run: make api-playwright-install"
        else:
            error_msg = str(e)
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"PDF generation failed for job {job_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.get("/api/page-image/{job_id}/{page_num}")
async def get_page_image(job_id: str, page_num: int):
    """
    Serve page image as static file response.
    
    Args:
        job_id: Job identifier
        page_num: Page number (1-indexed)
        
    Returns:
        PNG image file response
    """
    # Validate page number
    if page_num < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be positive"
        )
    
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Build image path
    job_dir = storage_manager.jobs_dir / job_id
    pages_dir = job_dir / "pages"
    image_path = pages_dir / f"page_{page_num}.png"
    
    # Check if file exists
    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page image {page_num} not found for job {job_id}"
        )
    
    # Return file response
    return FileResponse(
        image_path,
        media_type="image/png",
        filename=f"page_{page_num}.png"
    )


@app.get("/api/debug-page-image/{job_id}/{page_num}")
async def get_debug_page_image(job_id: str, page_num: int):
    """
    Serve debug page image with bounding boxes.
    
    Args:
        job_id: Job identifier
        page_num: Page number (1-indexed)
        
    Returns:
        PNG image file response
    """
    # Validate page number
    if page_num < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be positive"
        )
    
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Build debug image path
    job_dir = storage_manager.jobs_dir / job_id
    pages_dir = job_dir / "pages"
    debug_image_path = pages_dir / f"debug_page_{page_num}.png"
    
    # Check if debug file exists
    if not debug_image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debug page image {page_num} not found for job {job_id}"
        )
    
    # Return file response
    return FileResponse(
        debug_image_path,
        media_type="image/png",
        filename=f"debug_page_{page_num}.png"
    )


@app.get("/api/render-html/{job_id}")
async def get_render_html(job_id: str):
    """
    Get rendered HTML for a job - returns render.html content
    
    Args:
        job_id: Job identifier
        
    Returns:
        HTML content of render.html
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job_dir = storage_manager.jobs_dir / job_id
    render_html_path = job_dir / "render.html"
    
    if not render_html_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rendered HTML not found. Run /api/generate with mode=html first."
        )
    
    try:
        with open(render_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Return as HTML response
        from fastapi.responses import Response
        return Response(
            content=html_content,
            media_type="text/html",
            headers={"Content-Disposition": "inline"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read render.html: {e}"
        )


@app.get("/api/pdf-markdown/{job_id}")
async def get_pdf_markdown(job_id: str):
    """
    Get Markdown content for a job that was converted from PDF.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JSON with job_id and full markdown text
        
    Raises:
        404: If job doesn't exist
        409: If layout.md doesn't exist (run POST /api/pdf-markdown/{job_id} first)
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Check if layout.md exists
    job_dir = storage_manager.jobs_dir / job_id
    layout_md_path = job_dir / "layout.md"
    
    if not layout_md_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run POST /api/pdf-markdown/{job_id} first"
        )
    
    try:
        # Read Markdown content
        with open(layout_md_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
        
        return {
            "job_id": job_id,
            "markdown": markdown_content
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to read Markdown for job {job_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.get("/api/md-asset/{job_id}/{asset:path}")
async def get_markdown_asset(job_id: str, asset: str):
    """
    Serve extracted markdown assets (images) with path traversal protection.
    
    Args:
        job_id: Job identifier
        asset: Asset path (e.g., page1_img1.png, subfolder/image.png)
        
    Returns:
        Image file response
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Build asset path
    job_dir = storage_manager.jobs_dir / job_id
    assets_dir = job_dir / "md_assets"
    asset_path = assets_dir / asset
    
    # Security: Prevent path traversal attacks
    # Ensure the resolved path is within the md_assets directory
    try:
        asset_path = asset_path.resolve()
        assets_dir = assets_dir.resolve()
        if not str(asset_path).startswith(str(assets_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Path traversal detected"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid asset path"
        )
    
    # Check if file exists
    if not asset_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset} not found for job {job_id}"
        )
    
    # Determine media type based on file extension
    media_type = "image/png"  # default
    if asset_path.suffix.lower() in [".jpg", ".jpeg"]:
        media_type = "image/jpeg"
    elif asset_path.suffix.lower() == ".gif":
        media_type = "image/gif"
    elif asset_path.suffix.lower() == ".webp":
        media_type = "image/webp"
    
    # Return file response
    return FileResponse(
        asset_path,
        media_type=media_type,
        filename=asset_path.name
    )


@app.get("/api/debug/paths")
async def debug_paths():
    """Debug endpoint to show path information"""
    cwd = Path.cwd()
    storage_dir = resolve_storage_dir()
    
    return {
        "cwd": str(cwd),
        "project_root": str(PROJECT_ROOT),
        "storage_dir": str(storage_dir),
        "storage_dir_exists": storage_dir.exists()
    }


@app.get("/api/result/{job_id}")
async def get_job_result(job_id: str, mode: str = None):
    """
    Get job result - returns vision.json content or PDF file for completed jobs
    
    Args:
        job_id: Job identifier
        mode: Optional mode ('pdf-from-markdown' for markdown-generated PDF)
        
    Returns:
        JSON content of vision.json or PDF file
    """
    try:
        job_data = storage_manager.load_job(job_id)
        
        if job_data["status"] != "done":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job is not completed yet. Current status: {job_data['status']}"
            )
        
        # Handle different modes
        if mode == "pdf-from-markdown":
            # Return PDF generated from markdown
            pdf_from_markdown_path = job_data.get("pdf_from_markdown_path")
            if not pdf_from_markdown_path:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="PDF from markdown not found for this job"
                )
            output_file = storage_manager.base_dir / pdf_from_markdown_path
            filename = "result_from_markdown.pdf"
        else:
            # Default behavior - return main output
            output_path = job_data.get("output_path")
            if not output_path:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Job marked as done but no output path specified"
                )
            output_file = Path(output_path)
            filename = "translated.pdf"
        
        if not output_file.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Output file not found"
            )
        
        # Check file extension to determine response type
        if output_file.suffix.lower() == ".pdf":
            # Return PDF file
            return FileResponse(
                output_file,
                media_type="application/pdf",
                filename=filename,
                headers={
                    "Content-Disposition": f"inline; filename=\"{filename}\""
                }
            )
        else:
            # Return vision.json content (backward compatibility)
            with open(output_file, "r", encoding="utf-8") as f:
                vision_data = json.load(f)
            return vision_data
            
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )


@app.get("/api/vision/{job_id}")
async def get_vision_data(job_id: str):
    """
    Get vision data for a job - returns edited.json if exists, otherwise vision.json
    
    Args:
        job_id: Job identifier
        
    Returns:
        JSON content of vision/edited data or error
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job_dir = storage_manager.jobs_dir / job_id
    
    # Priority: edited.json > vision.json
    edited_json_path = job_dir / "edited.json"
    vision_json_path = job_dir / "vision.json"
    
    target_file = edited_json_path if edited_json_path.exists() else vision_json_path
    
    if not target_file.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vision data not found. Run /api/process first."
        )
    
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            vision_data = json.load(f)
        return vision_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read vision data: {e}"
        )


@app.put("/api/vision/{job_id}")
async def save_vision_edits(job_id: str, vision_data: dict):
    """
    Save edited vision data
    
    Args:
        job_id: Job identifier
        vision_data: Edited vision data (same format as vision.json)
        
    Returns:
        Confirmation of save
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Basic validation
    if "pages" not in vision_data or "meta" not in vision_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vision data format: missing 'pages' or 'meta'"
        )
    
    job_dir = storage_manager.jobs_dir / job_id
    edited_json_path = job_dir / "edited.json"
    
    try:
        # Atomic write like job.json
        temp_path = edited_json_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(vision_data, f, indent=2, ensure_ascii=False)
        temp_path.replace(edited_json_path)
        
        # Update job.json
        job_data = storage_manager.load_job(job_id)
        storage_manager.save_job(job_id, {
            **job_data,
            "edited_path": str(edited_json_path),
            "has_manual_edits": True
        })
        
        logger.info(f"Saved edits for job {job_id} to {edited_json_path}")
        return {
            "job_id": job_id,
            "saved": True
        }
        
    except Exception as e:
        logger.error(f"Failed to save edits for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save edits: {e}"
        )


@app.post("/api/pdf-markdown/{job_id}")
async def convert_pdf_to_markdown(job_id: str):
    """
    Convert PDF to Markdown using PyMuPDF4LLM.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JSON with conversion result
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Load job data
    job_data = storage_manager.load_job(job_id)
    
    # Get input PDF path
    input_path_str = job_data.get("input_path")
    if not input_path_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="input_path not found in job data"
        )
    
    input_pdf_path = Path(input_path_str)
    if not input_pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input PDF not found: {input_pdf_path}"
        )
    
    # Validate it's a PDF file
    if not input_pdf_path.suffix.lower() == ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input file is not a PDF"
        )
    
    try:
        # Get job directory
        job_dir = storage_manager.jobs_dir / job_id
        
        # Convert PDF to Markdown
        result = pdf_to_markdown_with_assets(input_pdf_path, job_dir)
        
        # Update job data with markdown info
        updated_job_data = {
            **job_data,
            "markdown_path": result["markdown_path"],
            "markdown_assets_dir": result["assets_dir"],
            "has_markdown": True,
            "markdown_chars": result["chars"],
            "markdown_images_count": result["images_count"]
        }
        storage_manager.save_job(job_id, updated_job_data)
        
        logger.info(f"PDF to Markdown conversion completed for job {job_id}")
        
        return {
            "job_id": job_id,
            "markdown_path": result["markdown_path"],
            "images_count": result["images_count"],
            "chars": result["chars"]
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"PDF to Markdown conversion failed for job {job_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.post("/api/debug-render/{job_id}")
async def debug_render(job_id: str):
    """
    Generate debug page images with bounding boxes for all pages.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JSON with job_id and number of debug pages generated
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Load job data
    job_data = storage_manager.load_job(job_id)
    
    # Check prerequisites
    if job_data.get("status") != "done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job must be in 'done' status. Run /api/process first."
        )
    
    job_dir = storage_manager.jobs_dir / job_id
    
    # Priority: edited.json > vision.json
    edited_json_path = job_dir / "edited.json"
    vision_json_path = job_dir / "vision.json"
    
    source_file = edited_json_path if edited_json_path.exists() else vision_json_path
    
    if not source_file.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vision data not found. Run /api/process first."
        )
    
    # Read vision/edited data
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            vision_data = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read vision data: {e}"
        )
    
    try:
        # Generate debug images for all pages
        debug_count = render_all_debug_pages(job_dir, vision_data)
        
        logger.info(f"Generated {debug_count} debug page images for job {job_id}")
        
        return {
            "job_id": job_id,
            "debug_pages": debug_count
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Debug render failed for job {job_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.post("/api/pdf-from-markdown-with-ocr/{job_id}")
async def pdf_from_markdown_with_ocr(job_id: str, payload: dict):
    """
    Generate PDF from Markdown content with OCR overlays using Variant 1 approach.
    
    Args:
        job_id: Job identifier
        payload: { "markdown": "full markdown text" }
        
    Returns:
        JSON with status and pdf_path
    """
    # Validate input
    markdown_content = payload.get("markdown")
    if not markdown_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'markdown' field in request body"
        )
    
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job_dir = storage_manager.jobs_dir / job_id
    
    # 1) Save markdown to jobs/{job_id}/markdown_for_ocr_overlay.md
    markdown_path = job_dir / "markdown_for_ocr_overlay.md"
    markdown_path.write_text(markdown_content, encoding='utf-8')
    
    # 2) Define output PDF path
    output_pdf = job_dir / "result_ocr_overlay.pdf"
    
    # 3) Generate PDF from markdown with OCR overlays (Variant 1)
    try:
        from html_render import generate_pdf_from_markdown
        await generate_pdf_from_markdown(markdown_path, output_pdf, variant=1)
        
        # Update job status
        job_data = storage_manager.load_job(job_id)
        job_data["pdf_from_markdown_with_ocr_status"] = "completed"
        job_data["pdf_from_markdown_with_ocr_path"] = str(output_pdf.relative_to(storage_manager.base_dir))
        storage_manager.save_job(job_id, job_data)
        
        return {
            "status": "completed",
            "pdf_path": str(output_pdf.relative_to(storage_manager.base_dir)),
            "message": "PDF with OCR overlays generated successfully"
        }
        
    except RuntimeError as e:
        error_msg = str(e)
        logger.error(f"PDF generation with OCR failed for job {job_id}: {error_msg}")
        
        # Extract debug hint if present
        debug_hint = ""
        if "Debug hint:" in error_msg:
            debug_hint = error_msg.split("Debug hint:")[-1].strip()
            # Remove the debug hint from the main error message
            error_msg = error_msg.split("Debug hint:")[0].strip()
        
        # Determine if this is a recoverable error
        is_recoverable = (
            "chromium" in error_msg.lower() or 
            "playwright" in error_msg.lower() or
            "browser" in error_msg.lower()
        )
        
        if is_recoverable:
            # Provide helpful error message with fallback suggestion
            detailed_error = {
                "error": error_msg,
                "debug_hint": debug_hint or "Try installing Playwright browsers: make api-playwright-install",
                "fallback_available": True,
                "suggestion": "Use /api/download-html/{job_id} to get HTML file and manually generate PDF via browser Print→Save as PDF"
            }
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detailed_error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error in PDF generation with OCR for job {job_id}: {error_msg}")
        
        detailed_error = {
            "error": error_msg,
            "debug_hint": "Unexpected error occurred during PDF generation with OCR overlays",
            "fallback_available": True,
            "suggestion": "Use /api/download-html/{job_id} to get HTML file and manually generate PDF via browser Print→Save as PDF"
        }
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detailed_error
        )


@app.post("/api/pdf-from-markdown/{job_id}")
async def pdf_from_markdown(job_id: str, payload: dict):
    """
    Generate PDF from Markdown content with robust error handling.
    
    Args:
        job_id: Job identifier
        payload: { "markdown": "full markdown text" }
        
    Returns:
        JSON with status and pdf_path
    """
    # Validate input
    markdown_content = payload.get("markdown")
    if not markdown_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'markdown' field in request body"
        )
    
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job_dir = storage_manager.jobs_dir / job_id
    
    # 1) Save markdown to jobs/{job_id}/markdown_for_pdf.md
    markdown_path = job_dir / "markdown_for_pdf.md"
    markdown_path.write_text(markdown_content, encoding='utf-8')
    
    # 2) Define output PDF path
    output_pdf = job_dir / "result.pdf"
    
    # 3) Generate PDF from markdown with detailed error handling
    try:
        await generate_pdf_from_markdown(markdown_path, output_pdf)
        
        # Update job status
        job_data = storage_manager.load_job(job_id)
        job_data["pdf_from_markdown_status"] = "completed"
        job_data["pdf_from_markdown_path"] = str(output_pdf.relative_to(storage_manager.base_dir))
        storage_manager.save_job(job_id, job_data)
        
        return {
            "status": "completed",
            "pdf_path": str(output_pdf.relative_to(storage_manager.base_dir)),
            "message": "PDF generated successfully"
        }
        
    except RuntimeError as e:
        # Handle specific Playwright/Chromium errors with detailed diagnostics
        error_msg = str(e)
        logger.error(f"PDF generation failed for job {job_id}: {error_msg}")
        
        # Extract debug hint if present
        debug_hint = ""
        if "Debug hint:" in error_msg:
            debug_hint = error_msg.split("Debug hint:")[-1].strip()
            # Remove the debug hint from the main error message
            error_msg = error_msg.split("Debug hint:")[0].strip()
        
        # Determine if this is a recoverable error
        is_recoverable = (
            "chromium" in error_msg.lower() or 
            "playwright" in error_msg.lower() or
            "browser" in error_msg.lower()
        )
        
        if is_recoverable:
            # Provide helpful error message with fallback suggestion
            detailed_error = {
                "error": error_msg,
                "debug_hint": debug_hint or "Try installing Playwright browsers: make api-playwright-install",
                "fallback_available": True,
                "suggestion": "Use /api/download-html/{job_id} to get HTML file and manually generate PDF via browser Print→Save as PDF"
            }
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detailed_error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
            
    except Exception as e:
        # Handle unexpected errors
        error_msg = str(e)
        logger.error(f"Unexpected error in PDF generation for job {job_id}: {error_msg}")
        
        detailed_error = {
            "error": error_msg,
            "debug_hint": "Unexpected error occurred during PDF generation",
            "fallback_available": True,
            "suggestion": "Use /api/download-html/{job_id} to get HTML file and manually generate PDF via browser Print→Save as PDF"
        }
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detailed_error
        )


@app.post("/api/ocr/{job_id}/{image_name}")
async def ocr_image(job_id: str, image_name: str):
    """
    Perform OCR on an image from md_assets and return text with bounding boxes.
    Also includes saved translations if they exist.
    
    Args:
        job_id: Job identifier
        image_name: Image filename (e.g., page1_img1.png)
        
    Returns:
        JSON with image_url, ocr_boxes, and translations
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Build image path
    job_dir = storage_manager.jobs_dir / job_id
    assets_dir = job_dir / "md_assets"
    image_path = assets_dir / image_name
    
    # Security: Prevent path traversal
    try:
        image_path = image_path.resolve()
        assets_dir = assets_dir.resolve()
        if not str(image_path).startswith(str(assets_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Path traversal detected"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid image path"
        )
    
    # Check if image exists
    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image {image_name} not found in job {job_id}"
        )
    
    # Perform OCR
    try:
        ocr_boxes = perform_ocr_on_image(image_path)
        
        # Construct image URL
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
        image_url = f"{api_base}/api/md-asset/{job_id}/{image_name}"
        
        # Load saved translations for this image
        translations = {}
        try:
            all_translations = storage_manager.load_ocr_translations(job_id)
            translations = all_translations.get(image_name, {})
        except Exception:
            # Translations are optional
            pass
        
        return {
            "image_url": image_url,
            "ocr_boxes": ocr_boxes,
            "translations": translations
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"OCR failed for {image_name} in job {job_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.post("/api/vision-translate/{job_id}/{image_name}")
async def vision_translate(job_id: str, image_name: str):
    logger.info(f"🟦 [START] job={job_id}, image={image_name}")
    try:
        # Use storage manager to get correct path
        job_dir = storage_manager.jobs_dir / job_id
        image_path = job_dir / "md_assets" / image_name
        
        if not image_path.exists():
            logger.error(f"❌ FILE NOT FOUND: {image_path}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        with open(image_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode()
        logger.info(f"✅ [IMAGE LOADED] {len(image_base64)} bytes")
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                    {"type": "text", "text": "Extract all visible English text from this image. Return JSON with original text, Russian translation, and approximate coordinates for each text element. Format: {\"text_elements\": [{\"original\": \"text\", \"translation\": \"перевод\", \"x\": 100, \"y\": 50, \"width\": 200, \"height\": 30}]}}"}
                ]
            }],
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        logger.info(f"✅ [OPENAI RESPONSE]")
        
        content = response.choices[0].message.content
        logger.info(f"✅ [CONTENT] {content[:200]}...")
        
        # Parse the JSON response to extract text elements
        import re
        import json
        
        # Clean up the response if it contains markdown code blocks
        clean_content = content.strip()
        if clean_content.startswith('```json'):
            clean_content = re.sub(r'^```json\s*', '', clean_content)
            clean_content = re.sub(r'\s*```$', '', clean_content)
        elif clean_content.startswith('```'):
            clean_content = re.sub(r'^```\w*\s*', '', clean_content)
            clean_content = re.sub(r'\s*```$', '', clean_content)
        
        try:
            translation_data = json.loads(clean_content)
            text_elements = translation_data.get("text_elements", [])
            logger.info(f"✅ [PARSED] Found {len(text_elements)} text elements")
        except json.JSONDecodeError as e:
            logger.error(f"❌ [JSON PARSE ERROR] {e}")
            logger.info("⚠️  Using fallback approach with original response")
            text_elements = []
            # Save the original response for debugging
            translation_data = {"raw_response": content, "text_elements": []}
        
        # Save translation data
        translation_data_path = job_dir / f"{image_name}_translation.json"
        logger.info(f"💾 [SAVE TRANSLATION DATA] {translation_data_path}")
        with open(translation_data_path, 'w', encoding='utf-8') as f:
            json.dump(translation_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ [TRANSLATION DATA SAVED] {len(content)} chars")
        
        # Generate translated image with PIL using the coordinate data
        from PIL import Image, ImageDraw, ImageFont
        with Image.open(image_path) as img:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            draw = ImageDraw.Draw(img)
            
            # Try to load a better font
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
                except:
                    font = ImageFont.load_default()
            
            # Get image dimensions for coordinate conversion
            img_width, img_height = img.size
            
            # Draw each translated text element at its coordinates
            for element in text_elements:
                original = element.get("original", "")
                translation = element.get("translation", "")
                norm_x = element.get("x", 0.1)  # Normalized x coordinate (0-1)
                norm_y = element.get("y", 0.1)  # Normalized y coordinate (0-1)
                norm_width = element.get("width", 0.2)  # Normalized width (0-1)
                norm_height = element.get("height", 0.1)  # Normalized height (0-1)
                
                # Convert normalized coordinates to pixel coordinates
                x = int(norm_x * img_width)
                y = int(norm_y * img_height)
                width = int(norm_width * img_width)
                height = int(norm_height * img_height)
                
                # Draw the translated text
                if translation.strip():
                    # Add a semi-transparent background to make text more readable
                    bbox = draw.textbbox((x, y), translation, font=font)
                    draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], fill=(255, 255, 255, 180))
                    draw.text((x, y), translation, fill=(0, 0, 0), font=font)
                    
                    logger.info(f"✅ [DRAWN TEXT] '{translation[:30]}...' at ({x}, {y})")
            
            # Add a small indicator that this is a vision-processed image
            draw.text((10, img.height - 20), "AI TRANSLATED", fill=(0, 128, 0), font=font)
            
            output_filename = image_name.replace('.png', '_translated.png')
            output_path = job_dir / "md_assets" / output_filename
            img.save(output_path, 'PNG')
        
        logger.info(f"✅ [SAVED] {output_filename} ({output_path.stat().st_size} bytes)")
        
        return {"original_image_name": image_name, "translated_image_name": output_filename, "target_language": "russian"}
    except Exception as e:
        logger.error(f"❌ EXCEPTION: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get-translation-data/{job_id}/{image_name}")
async def get_translation_data(job_id: str, image_name: str):
    """Get translation data for image editor"""
    try:
        job_dir = storage_manager.jobs_dir / job_id
        translation_file = job_dir / f"{image_name}_translation.json"
        
        if not translation_file.exists():
            return {"text_elements": []}
        
        with open(translation_file, 'r', encoding='utf-8') as f:
            data = f.read()
        
        # Try to parse as JSON - handle markdown code blocks
        import json
        import re
        
        try:
            # Remove markdown code block wrappers if present
            clean_data = data.strip()
            if clean_data.startswith('```json'):
                clean_data = re.sub(r'^```json\s*', '', clean_data)
                clean_data = re.sub(r'\s*```$', '', clean_data)
            elif clean_data.startswith('```'):
                clean_data = re.sub(r'^```\w*\s*', '', clean_data)
                clean_data = re.sub(r'\s*```$', '', clean_data)
            
            logger.info(f"🔍 [PARSING CLEAN DATA] {clean_data[:100]}...")
            parsed = json.loads(clean_data)
            
            # Handle both formats: direct text_elements or nested in a larger object
            if 'text_elements' in parsed:
                text_elements = parsed['text_elements']
            else:
                # If the whole object is the text_elements array
                text_elements = parsed if isinstance(parsed, list) else []
            
            logger.info(f"✅ [PARSED SUCCESSFULLY] {len(text_elements)} elements")
            return {"text_elements": text_elements}
        except Exception as e:
            logger.error(f"❌ JSON parsing failed: {str(e)}")
            logger.error(f"📝 Raw data: {data[:200]}...")
            # Return fallback data
            return {"text_elements": [{"original": "Text", "translation": "Текст", "x": 50, "y": 50, "width": 200, "height": 30}]}
            
    except Exception as e:
        logger.error(f"❌ Get translation data error: {str(e)}")
        return {"text_elements": []}

@app.post("/api/save-edited-image/{job_id}")
async def save_edited_image(job_id: str, payload: dict):
    """Save final edited image with text overlays"""
    try:
        image_name = payload.get("imageName")
        text_blocks = payload.get("textBlocks", [])
        
        if not image_name:
            raise HTTPException(status_code=400, detail="imageName required")
        
        job_dir = storage_manager.jobs_dir / job_id
        original_path = job_dir / "md_assets" / image_name
        final_filename = image_name.replace('.png', '_final.png')
        final_path = job_dir / "md_assets" / final_filename
        
        # Load original image
        from PIL import Image, ImageDraw, ImageFont
        with Image.open(original_path) as img:
            img_width, img_height = img.size

            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            draw = ImageDraw.Draw(img)
            
            # Add each text block with formatting
            for block in text_blocks:
                try:
                    # Create font with size and style
                    font_size = block.get("fontSize", 16)
                    font_style = block.get("fontStyle", "normal")
                    font_weight = block.get("fontWeight", "normal")
                    
                    # Try to use a font that supports bold/italic
                    if font_weight == "bold" and font_style == "italic":
                        font_path = "/System/Library/Fonts/Arial Bold Italic.ttf"
                    elif font_weight == "bold":
                        font_path = "/System/Library/Fonts/Arial Bold.ttf"
                    elif font_style == "italic":
                        font_path = "/System/Library/Fonts/Arial Italic.ttf"
                    else:
                        font_path = "/System/Library/Fonts/Arial.ttf"
                    
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                    except:
                        # Fallback to default font
                        font = ImageFont.load_default()
                        
                except:
                    font = ImageFont.load_default()
                
                # Resolve coordinates: prefer нормализованные, если они есть
                norm_x = block.get("normX")
                norm_y = block.get("normY")
                norm_w = block.get("normWidth")
                norm_h = block.get("normHeight")

                if isinstance(norm_x, (int, float)) and isinstance(norm_y, (int, float)) \
                   and isinstance(norm_w, (int, float)) and isinstance(norm_h, (int, float)) \
                   and 0 <= norm_x <= 1 and 0 <= norm_y <= 1 and norm_w > 0 and norm_h > 0:
                    x = int(norm_x * img_width)
                    y = int(norm_y * img_height)
                    width = int(norm_w * img_width)
                    height = int(norm_h * img_height)
                else:
                    # Fallback: используем пиксельные координаты как есть
                    x = int(block.get("x", 50))
                    y = int(block.get("y", 50))
                    width = int(block.get("width", 200))
                    height = int(block.get("height", 40))

                text = block.get("text", "")
                text_color_hex = block.get("color", "#000000")

                # Parse text color (#rrggbb)
                try:
                    text_color = tuple(int(text_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                except Exception:
                    text_color = (0, 0, 0)

                # Parse background color from редактора
                bg_raw = block.get("backgroundColor")
                bg_color = (255, 255, 255, 230)  # default white with alpha

                if isinstance(bg_raw, str):
                    if bg_raw.startswith("#") and len(bg_raw) in (4, 7):
                        try:
                            hex_val = bg_raw.lstrip('#')
                            if len(hex_val) == 3:
                                hex_val = ''.join([c * 2 for c in hex_val])
                            r = int(hex_val[0:2], 16)
                            g = int(hex_val[2:4], 16)
                            b = int(hex_val[4:6], 16)
                            bg_color = (r, g, b, 230)
                        except Exception:
                            pass
                    elif bg_raw.startswith("rgba"):
                        try:
                            # rgba(r,g,b,a)
                            inside = bg_raw[5:-1]
                            parts = [p.strip() for p in inside.split(",")]
                            if len(parts) >= 3:
                                r = int(float(parts[0]))
                                g = int(float(parts[1]))
                                b = int(float(parts[2]))
                                a = int(float(parts[3]) * 255) if len(parts) > 3 else 230
                                bg_color = (r, g, b, a)
                        except Exception:
                            pass

                # Draw блок-фон и текст
                if text.strip():
                    padding = 4
                    # Фон блока как прямоугольник
                    draw.rectangle(
                        [x, y, x + width, y + height],
                        fill=bg_color
                    )
                    # Текст внутри блока с небольшим отступом
                    draw.text((x + padding, y + padding), text, fill=text_color, font=font)
            
            # Save final image
            img.save(final_path, 'PNG')
        
        logger.info(f"✅ [FINAL IMAGE SAVED] {final_filename}")
        return {"final_image_name": final_filename}
        
    except Exception as e:
        logger.error(f"❌ Save edited image error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Moved to after the more specific endpoint to avoid routing conflict


@app.post("/api/ocr-translations/{job_id}")
async def save_ocr_translations(job_id: str, payload: dict):
    """
    Save OCR translations for a job.
    
    Args:
        job_id: Job identifier
        payload: { "translations": {...} }
        
    Returns:
        Success confirmation
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    translations = payload.get("translations")
    if translations is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'translations' field in request body"
        )
    
    try:
        storage_manager.save_ocr_translations(job_id, translations)
        return {"status": "success", "message": "Translations saved"}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to save OCR translations for job {job_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


# OLD ENDPOINT REMOVED - REPLACED BY NEW SIMPLE ENDPOINT BELOW


@app.get("/api/ocr-translations/{job_id}/{image_name}")
async def get_ocr_translations(job_id: str, image_name: str):
    """Simple GET endpoint for OCR translations"""
    print(f"=== GET REQUEST RECEIVED ===")
    print(f"Job ID: {job_id}")
    print(f"Image name: {image_name}")
    
    try:
        job_dir = storage_manager.jobs_dir / job_id
        trans_file = job_dir / "ocr_translations.json"
        
        print(f"Job directory: {job_dir}")
        print(f"Translation file path: {trans_file}")
        print(f"Translation file exists: {trans_file.exists()}")
        
        if not trans_file.exists():
            print(f"File not found, returning empty boxes")
            return {"boxes": []}  # 200, not 404!
        
        try:
            raw_data = trans_file.read_text()
            print(f"Raw file content: {raw_data}")
            
            data = json.loads(raw_data)
            print(f"Parsed data: {data}")
            
            # Return the boxes directly, not nested under image_name
            image_data = data.get(image_name, {})
            result = {"boxes": image_data.get("boxes", [])}
            print(f"Returning: {result}")
            return result
        except Exception as e:
            print(f"Error parsing file: {e}")
            return {"boxes": []}
    except:
        return {"boxes": []}


@app.put("/api/ocr-translations/{job_id}/{image_name}")
async def save_ocr_translations(job_id: str, image_name: str, payload: BoxesPayload):
    """PUT endpoint for OCR translations with Pydantic validation"""
    print(f"=== PUT REQUEST RECEIVED ===")
    print(f"Job ID: {job_id}")
    print(f"Image name: {image_name}")
    print(f"Payload boxes count: {len(payload.boxes)}")
    print(f"Payload boxes: {payload.boxes}")
    
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        print(f"Job {job_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    try:
        job_dir = storage_manager.jobs_dir / job_id
        trans_file = job_dir / "ocr_translations.json"
        
        print(f"Job directory: {job_dir}")
        print(f"Translation file path: {trans_file}")
        print(f"Translation file exists: {trans_file.exists()}")
        
        # Load existing data
        data = {}
        if trans_file.exists():
            try:
                data = json.loads(trans_file.read_text())
                print(f"Existing data loaded: {data}")
            except Exception as e:
                print(f"Error loading existing data: {e}")
                data = {}
        
        # Update with new payload - store as {"boxes": [...]} format
        boxes_data = [box.dict() for box in payload.boxes]
        data[image_name] = {"boxes": boxes_data}
        
        print(f"Data to save: {data}")
        
        # Save file
        trans_file.write_text(json.dumps(data, indent=2))
        print(f"File saved successfully")
        
        # Verify save
        if trans_file.exists():
            saved_data = json.loads(trans_file.read_text())
            print(f"Verified saved data: {saved_data}")
        
        return {"ok": True, "count": len(payload.boxes)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/download-html/{job_id}")
async def download_html_with_ocr(job_id: str, filename: str = None):
    """Download HTML file with OCR overlays for manual PDF generation."""
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    try:
        # Get job directory
        job_dir = storage_manager.jobs_dir / job_id
        
        # Try to get markdown content from different possible locations
        markdown_content = None
        markdown_paths = [
            job_dir / "layout.md",           # From PDF to Markdown conversion
            job_dir / "markdown_for_pdf.md"   # From manual markdown input
        ]
        
        for md_path in markdown_paths:
            if md_path.exists():
                markdown_content = md_path.read_text(encoding='utf-8')
                break
        
        if not markdown_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No markdown content found. Run PDF to Markdown conversion first."
            )
        
        # Get OCR translations
        ocr_translations = {}
        try:
            ocr_translations = storage_manager.load_ocr_translations(job_id)
        except Exception:
            # OCR translations are optional
            pass
        
        # Generate HTML with OCR overlays using existing function
        from html_render import generate_pdf_from_markdown
        import markdown2
        import os
        import re
        
        # Convert markdown to HTML (extras=['tables'] for GFM tables)
        html_content = markdown2.markdown(markdown_content, extras=['tables'])
        
        # Get API base URL for asset paths
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
        prefix = f'{api_base}/api/md-asset/{job_id}/'
        
        # Create complete HTML template
        html_template = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40mm;
            line-height: 1.6;
            position: relative;
        }
        img {
            max-width: 100%;
            height: auto;
            display: block;
        }
        .ocr-container {
            position: relative;
            display: inline-block;
        }
        .ocr-overlay {
            position: absolute;
            color: black;
            font-family: Arial, sans-serif;
            font-weight: normal;
            white-space: nowrap;
            pointer-events: none;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 24px;
            margin-bottom: 16px;
        }
        p {
            margin: 0 0 16px 0;
        }
        ul, ol {
            margin: 0 0 16px 0;
            padding-left: 30px;
        }
        li {
            margin: 4px 0;
        }
    </style>
</head>
<body>
''' + html_content + '''
</body>
</html>
'''
        
        # Replace asset paths with API URLs
        html_with_assets = html_template.replace('src="md_assets/', f'src="{prefix}')
        html_with_assets = html_with_assets.replace("src='md_assets/", f"src='{prefix}")
        html_with_assets = html_with_assets.replace('src="./md_assets/', f'src="{prefix}')
        html_with_assets = html_with_assets.replace("src='./md_assets/", f"src='{prefix}")
        
        # Add OCR text overlays for images
        if ocr_translations:
            img_pattern = r'<img[^>]+src=["\']([^"\']+/md_assets/([^"\']+\.\w+))["\'][^>]*/?>'
            matches = list(re.finditer(img_pattern, html_with_assets))
            
            # Process matches in reverse order to avoid offset issues
            for match in reversed(matches):
                full_src = match.group(1)
                image_name = match.group(2)
                start_pos = match.start()
                end_pos = match.end()
                
                # Check if we have OCR data for this image
                if image_name in ocr_translations:
                    translations = ocr_translations[image_name]
                    ocr_result = translations.get('ocr_result', {})
                    text_translations = translations.get('translations', {})
                    
                    if ocr_result and 'ocr_boxes' in ocr_result:
                        # Create container div
                        container_start = '<div class="ocr-container">'
                        container_end = '</div>'
                        
                        # Build overlay divs
                        overlay_divs = []
                        for i, box in enumerate(ocr_result['ocr_boxes']):
                            # Get translated text or original
                            translated_text = text_translations.get(str(i), box['text'])
                            
                            # Get bounding box coordinates
                            if len(box['bbox']) >= 4:
                                x1, y1, x2, y2 = box['bbox'][:4]
                                width = x2 - x1
                                height = y2 - y1
                                
                                # Calculate font size based on box height
                                font_size = max(8, min(height * 0.8, 24))
                                
                                overlay_div = (
                                    f'<div class="ocr-overlay" '
                                    f'style="left: {x1}px; top: {y1}px; '
                                    f'width: {width}px; height: {height}px; '
                                    f'font-size: {font_size}px; line-height: 1; '
                                    f'display: flex; align-items: center;">'
                                    f'{translated_text}'
                                    f'</div>'
                                )
                                overlay_divs.append(overlay_div)
                        
                        # Replace the img tag with container + img + overlays
                        img_tag = match.group(0)
                        replacement = (
                            container_start + 
                            img_tag + 
                            ''.join(overlay_divs) + 
                            container_end
                        )
                        
                        # Update HTML
                        html_with_assets = (
                            html_with_assets[:start_pos] + 
                            replacement + 
                            html_with_assets[end_pos:]
                        )
        
        # Save HTML file
        if filename:
            html_filename = filename
        else:
            html_filename = f"document_with_ocr_{job_id}.html"
        
        html_path = job_dir / html_filename
        html_path.write_text(html_with_assets, encoding='utf-8')
        
        logger.info(f"Generated HTML file for job {job_id}: {html_filename}")
        
        return FileResponse(
            path=str(html_path),
            filename=html_filename,
            media_type='text/html'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HTML download failed for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate HTML: {str(e)}"
        )


@app.get("/api/ocr-translations/{job_id}")
async def get_ocr_translations(job_id: str):
    """
    Get saved OCR translations for a job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        OCR translations dictionary
    """
    # Check if job exists
    if not storage_manager.job_exists(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    translations = storage_manager.load_ocr_translations(job_id)
    return {"translations": translations}


@app.get("/api/preview-overlay/{job_id}/{image_name}")
async def preview_overlay(job_id: str, image_name: str):
    """Generate PNG preview with OCR overlays for instant feedback."""
    try:
        job_dir = storage_manager.jobs_dir / job_id
        png_path = job_dir / "md_assets" / image_name
        
        # Check if image exists
        if not png_path.exists():
            raise HTTPException(status_code=404, detail=f"Image not found: {image_name}")
        
        # Get OCR translations
        trans_file = job_dir / "ocr_translations.json"
        if not trans_file.exists():
            translations = {"boxes": []}
        else:
            translations = json.loads(trans_file.read_text()).get(image_name, {"boxes": []})
        
        # Generate preview
        buffer = generate_preview_overlay(str(png_path), translations)
        
        return StreamingResponse(buffer, media_type="image/png")
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Document Translator API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)