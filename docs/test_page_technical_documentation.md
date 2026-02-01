# PDF Translator `/test` Page - Technical Documentation

## 📋 Executive Summary

This document provides a comprehensive technical analysis of the `/test` page implementation in the PDF Translator application. The page serves as a visual OCR editor with integrated PDF processing capabilities, featuring a three-panel interface for Markdown editing, live preview, and interactive image annotation.

## 🏗️ System Architecture Overview

### High-Level Architecture
The application follows a **client-server architecture** with clear separation of concerns:

```
┌─────────────────┐    HTTP/REST    ┌──────────────────┐
│   Next.js 14    │ ←─────────────→ │   FastAPI 0.104  │
│   Frontend      │                 │   Backend        │
│   (TypeScript)  │                 │   (Python 3.11)  │
└─────────────────┘                 └──────────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌──────────────────┐
│   Local State   │                 │   File Storage   │
│   Management    │                 │   (./data/jobs)  │
└─────────────────┘                 └──────────────────┘
```

### Core Components
1. **Frontend UI Layer** - React-based interactive editor
2. **Backend API Layer** - RESTful services for processing
3. **Storage Layer** - File-based job management system
4. **Processing Engine** - OCR and PDF conversion pipelines

## 📁 File Structure and Organization

### Frontend Application (`/apps/web/`)

```
apps/web/
├── app/
│   ├── test/
│   │   └── page.tsx              # Main test page component (1,304 lines)
│   ├── components/
│   │   └── ImageEditor.tsx       # Visual OCR editor (551 lines)
│   ├── layout.tsx                # Root layout configuration
│   └── globals.css               # Global styling
├── package.json                  # Dependencies and scripts
├── next.config.js                # Next.js configuration
├── tsconfig.json                 # TypeScript configuration
└── .env.example                  # Environment variables template
```

### Backend Services (`/apps/api/`)

```
apps/api/
├── main.py                       # FastAPI application router (1,826 lines)
├── storage.py                    # File storage manager (158 lines)
├── ocr_service.py                # OCR processing implementation
├── preview_overlay.py            # PNG preview generator (83 lines)
├── html_render.py                # HTML/PDF rendering utilities
├── pdf_generate.py               # Playwright PDF generation
├── pdf_to_markdown.py            # PDF to Markdown converter
├── openai_vision.py              # Vision analysis services
├── pdf_render.py                 # PDF rendering pipeline
└── requirements.txt              # Python dependencies
```

## 🧩 Frontend Implementation Details

### Main Test Page Component (`test/page.tsx`)

#### Component Structure
The main test page is a complex React component implementing a three-column layout:

```typescript
export default function TestPage() {
  // State Management
  const [jobId, setJobId] = useState<string | null>(null)
  const [markdown, setMarkdown] = useState<string>('')
  const [imageOcrData, setImageOcrData] = useState<ImageOcrData>({})
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>('')
  
  // UI State
  const [isUploading, setIsUploading] = useState(false)
  const [isRunningOcr, setIsRunningOcr] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
}
```

#### Key Functional Areas

##### 1. PDF Processing Pipeline
```typescript
const handleFile = async (file: File) => {
  // Step 1: Upload PDF
  const uploadResponse = await fetch(`${API_BASE_URL}/api/translate`, {
    method: 'POST',
    body: formData,
  })

  // Step 2: Process with Vision Analysis
  const processResponse = await fetch(`${API_BASE_URL}/api/process/${newJobId}`, {
    method: 'POST'
  })

  // Step 3: Convert to Markdown
  const markdownResponse = await fetch(`${API_BASE_URL}/api/pdf-markdown/${newJobId}`, {
    method: 'POST'
  })

  // Step 4: Load Markdown Content
  const contentResponse = await fetch(`${API_BASE_URL}/api/pdf-markdown/${newJobId}`)
}
```

##### 2. OCR Workflow Management
```typescript
const handleRunOcr = async () => {
  const imageNames = getImageNamesFromMarkdown()
  
  for (const imageName of imageNames) {
    const response = await fetch(`${API_BASE_URL}/api/ocr/${jobId}/${imageName}`, {
      method: 'POST'
    })
    
    const ocrResult: OcrResult = await response.json()
    // Store results in state
  }
}
```

##### 3. Data Interfaces
```typescript
interface OcrBox {
  text: string;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  confidence: number;
}

interface Box {
  id: string;
  x: number;  // image coordinates (pixels)
  y: number;
  w: number;
  h: number;
  text: string;
  fontSize?: number;
  color?: string;
}

interface OcrResult {
  image_url: string;
  ocr_boxes: OcrBox[];
  translations: { [key: string]: any };
}

interface ImageOcrData {
  [imageName: string]: {
    ocr_result: OcrResult;
    translations: { [index: number]: string };
    boxes?: Box[]; // Image coordinates
  };
}
```

### ImageEditor Component (`components/ImageEditor.tsx`)

#### Core Features
- **Interactive Box Manipulation**: Drag to move, resize handles for dimension adjustment
- **Coordinate System Management**: Natural image coordinates with scaling support
- **History Tracking**: Undo/redo functionality with state snapshots
- **Zoom Controls**: Mouse wheel zoom (0.5x to 3x) with visual feedback
- **Real-time Preview**: Instant text overlay visualization

#### Event Handling System
```typescript
// Mouse Interaction Handlers
const handleBoxMouseDown = (e: React.MouseEvent, index: number) => {
  e.stopPropagation()
  setSelectedBoxIndex(index)
  setIsDragging(true)
  
  // Calculate offset for smooth dragging
  const imgRect = imageRef.current.getBoundingClientRect()
  const box = boxes[index]
  const naturalX = (e.clientX - imgRect.left) * (imageRef.current.naturalWidth / imgRect.width)
  const naturalY = (e.clientY - imgRect.top) * (imageRef.current.naturalHeight / imgRect.height)
  
  setDragOffset({ x: naturalX - box.x, y: naturalY - box.y })
}

const handleMouseMove = (e: MouseEvent) => {
  if (!imageRef.current) return
  
  const imgRect = imageRef.current.getBoundingClientRect()
  
  if (isDragging && selectedBoxIndex !== null) {
    // Convert screen to natural coordinates
    const naturalX = (e.clientX - imgRect.left) * (imageRef.current.naturalWidth / imgRect.width)
    const naturalY = (e.clientY - imgRect.top) * (imageRef.current.naturalHeight / imgRect.height)
    
    // Apply grid snapping (5px increments)
    setBoxes(prev => {
      const newBoxes = [...prev]
      const box = newBoxes[selectedBoxIndex]
      newBoxes[selectedBoxIndex] = {
        ...box,
        x: Math.max(0, Math.round((naturalX - dragOffset.x) / 5) * 5),
        y: Math.max(0, Math.round((naturalY - dragOffset.y) / 5) * 5)
      }
      return newBoxes
    })
  }
}
```

#### Coordinate Transformation Logic
```typescript
// Scale calculation for responsive rendering
const calculateScaleFactors = () => {
  const rect = imageRef.current?.getBoundingClientRect()
  const scaleX = rect ? rect.width / (imageRef.current!.naturalWidth || 1) : 1
  const scaleY = rect ? rect.height / (imageRef.current!.naturalHeight || 1) : 1
  return { scaleX, scaleY }
}

// Position rendering with scaling
<div
  className="text-overlay"
  style={{
    left: `${box.x * scaleX}px`,
    top: `${box.y * scaleY}px`,
    width: `${box.w * scaleX}px`,
    height: `${box.h * scaleY}px`
  }}
>
```

## 🔧 Backend API Implementation

### FastAPI Application Structure (`main.py`)

#### Core Dependencies and Imports
```python
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
import json
from dotenv import load_dotenv

# Internal modules
from storage import storage_manager
from pdf_render import render_pdf_to_pngs
from openai_vision import analyze_document_images
from html_render import vision_to_html, generate_pdf_from_markdown
from pdf_generate import html_to_pdf_bytes_async
from ocr_service import perform_ocr_on_image
from preview_overlay import generate_preview_overlay
```

#### Pydantic Data Models
```python
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
```

### Key API Endpoints

#### 1. PDF Processing Pipeline
```python
@app.post("/api/translate")
async def create_translation_job(file: UploadFile = File(...), target_language: str = Form(...)):
    """Create new translation job and save uploaded PDF"""
    job_id = str(uuid.uuid4())
    input_path = storage_manager.save_uploadfile(job_id, file, "input.pdf")
    # Save job metadata and return job_id

@app.post("/api/process/{job_id}")
async def process_job(job_id: str, force: bool = Query(False)):
    """Process PDF through vision analysis pipeline"""
    # Render PDF to PNGs
    png_paths = render_pdf_to_pngs(input_pdf_path, out_dir, max_pages, dpi)
    
    # Perform OpenAI vision analysis
    vision_result = analyze_document_images(
        image_paths=png_paths,
        target_language=target_language,
        model=None,
        use_structured_outputs=None,
        job_dir=job_dir
    )
    
    # Save results and update job status

@app.post("/api/pdf-markdown/{job_id}")
async def convert_pdf_to_markdown(job_id: str):
    """Convert processed PDF to Markdown format"""
    result = pdf_to_markdown_with_assets(input_pdf_path, job_dir)
    # Update job metadata with markdown info
```

#### 2. OCR Workflow Endpoints
```python
@app.post("/api/ocr/{job_id}/{image_name}")
async def ocr_image(job_id: str, image_name: str):
    """Perform OCR on specific image and return bounding boxes"""
    image_path = storage_manager.jobs_dir / job_id / "md_assets" / image_name
    
    # Security validation
    image_path = image_path.resolve()
    assets_dir = (storage_manager.jobs_dir / job_id / "md_assets").resolve()
    if not str(image_path).startswith(str(assets_dir)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Path traversal detected")
    
    # Perform OCR
    ocr_boxes = perform_ocr_on_image(image_path)
    
    # Load existing translations
    translations = {}
    try:
        all_translations = storage_manager.load_ocr_translations(job_id)
        translations = all_translations.get(image_name, {})
    except Exception:
        pass
    
    return {
        "image_url": f"{api_base}/api/md-asset/{job_id}/{image_name}",
        "ocr_boxes": ocr_boxes,
        "translations": translations
    }

@app.get("/api/ocr-translations/{job_id}/{image_name}")
async def get_ocr_translations(job_id: str, image_name: str):
    """Retrieve saved OCR translation boxes for specific image"""
    job_dir = storage_manager.jobs_dir / job_id
    trans_file = job_dir / "ocr_translations.json"
    
    if not trans_file.exists():
        return {"boxes": []}
    
    data = json.loads(trans_file.read_text())
    image_data = data.get(image_name, {})
    return {"boxes": image_data.get("boxes", [])}

@app.put("/api/ocr-translations/{job_id}/{image_name}")
async def save_ocr_translations(job_id: str, image_name: str, payload: BoxesPayload):
    """Save OCR translation boxes for specific image"""
    job_dir = storage_manager.jobs_dir / job_id
    trans_file = job_dir / "ocr_translations.json"
    
    # Load existing data
    data = {}
    if trans_file.exists():
        data = json.loads(trans_file.read_text())
    
    # Update with new payload
    boxes_data = [box.dict() for box in payload.boxes]
    data[image_name] = {"boxes": boxes_data}
    
    # Save file atomically
    trans_file.write_text(json.dumps(data, indent=2))
    return {"ok": True, "count": len(payload.boxes)}
```

#### 3. Preview and PDF Generation
```python
@app.get("/api/preview-overlay/{job_id}/{image_name}")
async def preview_overlay(job_id: str, image_name: str):
    """Generate PNG preview with OCR overlays"""
    job_dir = storage_manager.jobs_dir / job_id
    png_path = job_dir / "md_assets" / image_name
    
    # Get OCR translations
    trans_file = job_dir / "ocr_translations.json"
    if not trans_file.exists():
        translations = {"boxes": []}
    else:
        translations = json.loads(trans_file.read_text()).get(image_name, {"boxes": []})
    
    # Generate preview
    buffer = generate_preview_overlay(str(png_path), translations)
    return StreamingResponse(buffer, media_type="image/png")

@app.post("/api/pdf-from-markdown-with-ocr/{job_id}")
async def pdf_from_markdown_with_ocr(job_id: str, payload: dict):
    """Generate PDF from Markdown with OCR text overlays"""
    job_dir = storage_manager.jobs_dir / job_id
    markdown_path = job_dir / "markdown_for_ocr_overlay.md"
    output_pdf = job_dir / "result_ocr_overlay.pdf"
    
    # Save markdown content
    markdown_path.write_text(payload.get("markdown"), encoding='utf-8')
    
    # Generate PDF with OCR overlays (Variant 1 approach)
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
```

## 📦 Storage Layer Implementation

### Storage Manager (`storage.py`)

#### Core Class Implementation
```python
class StorageManager:
    def __init__(self):
        self.base_dir = resolve_storage_dir()
        self.jobs_dir = self.base_dir / "jobs"
        self._ensure_storage_directories()
    
    def ensure_job_dir(self, job_id: str) -> Path:
        """Create job directory if it doesn't exist"""
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir
    
    def save_uploadfile(self, job_id: str, upload_file, filename: str = "input.pdf") -> Path:
        """Save uploaded file with streaming for memory efficiency"""
        job_dir = self.ensure_job_dir(job_id)
        file_path = job_dir / filename
        
        # Stream file content with copyfileobj
        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)
            f.flush()
            os.fsync(f.fileno())
        
        upload_file.file.seek(0)
        return file_path
```

#### Job Data Management
```python
def load_job(self, job_id: str) -> Dict[str, Any]:
    """Load job data from job.json"""
    job_file = self.jobs_dir / job_id / "job.json"
    if not job_file.exists():
        raise FileNotFoundError(f"Job {job_id} not found")
    
    with open(job_file, "r") as f:
        return json.load(f)

def save_job(self, job_id: str, job_dict: Dict[str, Any]) -> None:
    """Save job data atomically"""
    job_dir = self.ensure_job_dir(job_id)
    job_file = job_dir / "job.json"
    temp_file = job_dir / "job.json.tmp"
    
    # Write to temporary file first
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(job_dict, f, indent=2, ensure_ascii=False)
    
    # Atomic rename
    temp_file.replace(job_file)
```

#### File Organization Structure
```
data/
└── jobs/
    └── {uuid-job-id}/
        ├── input.pdf                 # Original uploaded PDF
        ├── job.json                  # Job metadata and status
        ├── vision.json               # Vision analysis results
        ├── edited.json               # Manual edits (if any)
        ├── layout.md                 # Generated Markdown content
        ├── markdown_for_pdf.md       # Markdown for PDF generation
        ├── markdown_for_ocr_overlay.md # Markdown with OCR data
        ├── md_assets/                # Extracted images directory
        │   ├── page1_img1.png
        │   ├── page1_img2.png
        │   └── ...
        ├── pages/                    # Rendered page images
        │   ├── page_1.png
        │   ├── page_2.png
        │   └── ...
        ├── ocr_translations.json     # Saved OCR boxes and text
        ├── render.html               # Generated HTML document
        ├── result.pdf                # Final PDF output
        ├── result_ocr_overlay.pdf    # PDF with OCR overlays
        └── document_with_ocr_{job_id}.html # HTML with overlays
```

## 🔄 Data Flow Architecture

### Complete Processing Pipeline

#### Phase 1: PDF Upload and Initial Processing
```
User Action: Drag/Drop PDF
    ↓
handleFile() function triggered
    ↓
1. POST /api/translate (file upload)
   - Creates job_id
   - Saves input.pdf
   - Returns job_id
    ↓
2. POST /api/process/{job_id}
   - Renders PDF to PNG pages
   - Performs vision analysis
   - Generates vision.json
   - Updates job status to "done"
    ↓
3. POST /api/pdf-markdown/{job_id}
   - Converts vision data to Markdown
   - Extracts images to md_assets/
   - Creates layout.md
    ↓
4. GET /api/pdf-markdown/{job_id}
   - Loads generated Markdown
   - Populates editor state
```

#### Phase 2: OCR Processing and Editing
```
User Action: Click "OCR Images"
    ↓
handleRunOcr() function triggered
    ↓
1. getImageNamesFromMarkdown()
   - Parses ![alt](md_assets/filename.png) patterns
   - Returns list of image names
    ↓
2. For each image:
   POST /api/ocr/{job_id}/{image_name}
   - Performs OCR on image
   - Returns bounding boxes and text
   - Stores in imageOcrData state
    ↓
3. User selects image from dropdown
   ↓
4. ImageEditorContainer mounts
   useEffect() runs:
   - Attempts GET /api/ocr-translations/{job_id}/{image_name}
   - If exists: loads saved boxes
   - If not: initializes from OCR data
    ↓
5. User interacts with ImageEditor:
   - Drags boxes to reposition
   - Resizes using corner handles
   - Edits text content
   - Uses undo/redo functionality
    ↓
6. User clicks "Save Changes"
   handleImageEditorSave() triggered
   PUT /api/ocr-translations/{job_id}/{image_name}
   - Sends updated box data
   - Server saves to ocr_translations.json
    ↓
7. Auto-preview generation:
   GET /api/preview-overlay/{job_id}/{image_name}
   - Generates PNG with text overlays
   - Updates previewUrl state
```

#### Phase 3: PDF Generation with OCR Overlays
```
User Action: Click "Generate PDF with OCR Overlays"
    ↓
handleGeneratePdfWithOcrOverlays() triggered
    ↓
1. POST /api/pdf-from-markdown-with-ocr/{job_id}
   {
     "markdown": current_markdown_state
   }
    ↓
2. Backend processing:
   - Saves markdown to markdown_for_ocr_overlay.md
   - Calls generate_pdf_from_markdown() with variant=1
   - Processes Markdown → HTML with OCR overlays
   - Uses Playwright to convert HTML → PDF
   - Saves as result_ocr_overlay.pdf
    ↓
3. Response received:
   {
     "status": "completed",
     "pdf_path": "relative/path/to/pdf",
     "message": "PDF with OCR overlays generated successfully"
   }
    ↓
4. window.open(`${API_BASE_URL}/api/result/${job_id}?mode=pdf-from-markdown`)
   - Opens generated PDF in new tab
```

## 🎯 Technical Implementation Details

### Coordinate System Management

#### Three Coordinate Spaces
1. **Natural Image Coordinates**: Raw pixel coordinates from OCR/bounding boxes
2. **Screen Coordinates**: Browser viewport coordinates for UI interaction
3. **Scaled Coordinates**: Rendered coordinates accounting for zoom and display scaling

#### Coordinate Transformation Functions
```typescript
// Screen to Natural conversion (in ImageEditor)
const naturalX = (screenX - imgRect.left) * (imageRef.current.naturalWidth / imgRect.width)
const naturalY = (screenY - imgRect.top) * (imageRef.current.naturalHeight / imgRect.height)

// Scaling for display (in rendering)
const scaleX = displayWidth / naturalWidth
const scaleY = displayHeight / naturalHeight

// Box rendering with scaling
left: `${box.x * scaleX}px`
top: `${box.y * scaleY}px`
width: `${box.w * scaleX}px`
height: `${box.h * scaleY}px`
```

### State Management Patterns

#### React State Organization
```typescript
// Job-related state
const [jobId, setJobId] = useState<string | null>(null)
const [imageOcrData, setImageOcrData] = useState<ImageOcrData>({})

// UI interaction state
const [selectedImage, setSelectedImage] = useState<string | null>(null)
const [isDragging, setIsDragging] = useState(false)
const [selectedBoxIndex, setSelectedBoxIndex] = useState<number | null>(null)

// Loading and status state
const [isUploading, setIsUploading] = useState(false)
const [isRunningOcr, setIsRunningOcr] = useState(false)
const [status, setStatus] = useState<string | null>(null)
const [error, setError] = useState<string | null>(null)
```

#### Effect Hook Usage
```typescript
// Initialization effect in ImageEditorContainer
useEffect(() => {
  // Load saved data or initialize from OCR
  const loadBoxes = async () => {
    if (!jobId) return
    
    try {
      // Try to get saved translations first
      const response = await fetch(`${API_BASE_URL}/api/ocr-translations/${jobId}/${imageName}`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.boxes && data.boxes.length > 0) {
          setBoxes(data.boxes)
          hasLoadedRef.current = true
          return
        }
      }
      
      // Fallback to OCR initialization
      const initialBoxes = ocrResult.ocr_boxes.map((box, index) => ({
        id: `box-${index}`,
        x: box.bbox[0],
        y: box.bbox[1],
        w: box.bbox[2] - box.bbox[0],
        h: box.bbox[3] - box.bbox[1],
        text: box.text,
        fontSize: Math.max(8, Math.min((box.bbox[3] - box.bbox[1]) * 0.8, 24)),
        color: '#000000'
      }))
      
      setBoxes(initialBoxes)
      hasLoadedRef.current = true
      
    } catch (err) {
      // Error handling
    }
  }
  
  loadBoxes()
}, [jobId, imageName, onStatusChange])
```

### Performance Optimization Strategies

#### Virtual Scrolling
Although not currently implemented in the test page, the project includes `react-window` for handling large documents:
```typescript
import { FixedSizeList } from 'react-window'

// Would be used for large Markdown documents
const Row = ({ index, style }) => (
  <div style={style}>
    {markdownLines[index]}
  </div>
)

<FixedSizeList
  height={600}
  itemCount={lineCount}
  itemSize={20}
>
  {Row}
</FixedSizeList>
```

#### Memory Management
```typescript
// Streaming file uploads to prevent memory issues
const save_uploadfile(self, job_id: str, upload_file, filename: str = "input.pdf") -> Path:
    job_dir = self.ensure_job_dir(job_id)
    file_path = job_dir / filename
    
    # Stream instead of loading entire file into memory
    with open(file_path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
        f.flush()
        os.fsync(f.fileno())
```

#### Batch Operations
```typescript
// Batch OCR processing with progress updates
const handleRunOcr = async () => {
  const imageNames = getImageNamesFromMarkdown()
  let successCount = 0
  
  for (const imageName of imageNames) {
    setStatus(`Running OCR on ${imageName}...`)
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/ocr/${jobId}/${imageName}`, {
        method: 'POST'
      })
      
      if (response.ok) {
        const ocrResult = await response.json()
        // Process result...
        successCount++
      }
    } catch (err) {
      // Handle individual failures
    }
  }
  
  setStatus(`OCR completed for ${successCount}/${imageNames.length} images`)
}
```

## 🔒 Security Implementation

### Frontend Security Measures

#### Environment Variable Protection
```typescript
// API base URL from environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
```

#### Client-Side Validation
```typescript
const handleFile = async (file: File) => {
  // File type validation
  if (file.type !== 'application/pdf') {
    setError('Please select a PDF file')
    return
  }
  
  // File size validation (20MB limit)
  if (file.size > 20 * 1024 * 1024) {
    setError('File size exceeds 20MB limit')
    return
  }
  
  // Proceed with upload...
}
```

### Backend Security Measures

#### Path Traversal Prevention
```python
@app.get("/api/md-asset/{job_id}/{asset:path}")
async def get_markdown_asset(job_id: str, asset: str):
    # Build asset path
    job_dir = storage_manager.jobs_dir / job_id
    assets_dir = job_dir / "md_assets"
    asset_path = assets_dir / asset
    
    # Security: Prevent path traversal
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
```

#### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js default
        "http://localhost:3001",  # Alternative ports
        "http://localhost:3002",
        # ... more development ports
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Job Isolation
Each job operates in its own isolated directory:
```python
# Job directory structure ensures isolation
job_dir = storage_manager.jobs_dir / job_id  # UUID-based isolation
# All operations confined to job_dir
```

## 🛠️ Development Environment

### Setup Commands
```bash
# Install all dependencies
make install

# Start Redis (required dependency)
make redis-up

# Start backend development server
make api-dev  # Runs on localhost:8000

# Start frontend development server  
make web-dev  # Runs on localhost:3000

# Start both services simultaneously
make dev
```

### Environment Configuration

#### Frontend Environment (`.env.local`)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

#### Backend Environment (`.env`)
```bash
OPENAI_API_KEY=sk-...              # Required for vision analysis
STORAGE_DIR=./data                 # File storage location
API_BASE_URL=http://localhost:8000 # For generating asset URLs
VISION_MAX_PAGES=2                 # Max pages to process
VISION_DPI=144                     # Rendering resolution
```

### Development Tools Integration

#### Package Management
- **Frontend**: pnpm (preferred over npm for speed)
- **Backend**: pip with virtual environments

#### Code Quality
```bash
# Linting
make lint

# Formatting
make format

# Type checking (TypeScript)
cd apps/web && pnpm tsc

# Python code quality
cd apps/api && .venv/bin/ruff check .
```

## 📊 Performance Characteristics

### Resource Usage Patterns

#### Memory Consumption
- **Frontend**: Virtual DOM with component-based rendering
- **Backend**: Streaming file processing to minimize memory footprint
- **Images**: Loaded on-demand rather than pre-loaded

#### Processing Bottlenecks
1. **OCR Processing**: External service dependency (variable timing)
2. **PDF Rendering**: Playwright browser startup overhead
3. **Network I/O**: Multiple round trips for image assets
4. **Large Documents**: Markdown parsing and state updates

### Scalability Considerations

#### Current Limitations
- **Synchronous Processing**: No job queueing system
- **File-based Storage**: Potential I/O bottlenecks
- **Single-threaded Operations**: Python GIL limitations

#### Future Enhancement Opportunities
- **Asynchronous Queuing**: Redis-backed job queue
- **Cloud Storage**: Migration from local filesystem
- **Caching Layer**: Redis for frequently accessed data
- **Load Balancing**: Multiple backend instances

## 🧪 Testing Strategy

### Manual Testing Workflows

#### Core User Journeys
1. **PDF Upload and Conversion**
   - Upload various PDF sizes and types
   - Verify Markdown generation accuracy
   - Test error handling for invalid files

2. **OCR Processing**
   - Test different image qualities
   - Verify bounding box accuracy
   - Test text recognition reliability

3. **Visual Editing**
   - Drag and resize operations
   - Text editing functionality
   - Undo/redo behavior
   - Zoom controls

4. **PDF Generation**
   - Overlay positioning accuracy
   - Text rendering quality
   - File size optimization

### Automated Testing Coverage

#### API Endpoint Tests
Files in `/apps/api/test_*.py` covering:
- Upload and processing workflows
- OCR functionality
- PDF generation
- Error conditions

#### Integration Testing
- End-to-end processing pipelines
- Cross-component interactions
- Data persistence validation

## 🚀 Deployment Architecture

### Production Considerations

#### Infrastructure Requirements
- **Reverse Proxy**: nginx/Apache for static asset serving
- **SSL Termination**: HTTPS certificate management
- **CDN Integration**: For image assets and static files
- **Monitoring**: Logging and performance metrics
- **Backup Strategy**: Regular job data backups

#### Container Orchestration
```yaml
# docker-compose.yml structure
version: '3.8'
services:
  api:
    build: ./apps/api
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - STORAGE_DIR=/app/data
  
  web:
    build: ./apps/web
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_BASE_URL=http://api:8000
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Scaling Strategy
- **Horizontal Scaling**: Multiple web frontend instances
- **Vertical Scaling**: Increased resources for processing backend
- **Database Migration**: From file-based to PostgreSQL/MongoDB
- **Microservices**: Split OCR, PDF, and vision services

---

*This documentation provides a comprehensive technical overview of the `/test` page implementation, covering architecture, implementation details, security measures, and deployment considerations.*