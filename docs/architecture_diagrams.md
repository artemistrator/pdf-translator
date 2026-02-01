# PDF Translator Architecture Diagrams

## System Architecture Overview

```mermaid
graph TB
    A[Next.js Frontend<br/>localhost:3000] --> B[FastAPI Backend<br/>localhost:8000]
    B --> C[File Storage<br/>./data/jobs/]
    B --> D[OCR Service<br/>External API]
    B --> E[OpenAI Vision<br/>GPT-4 Analysis]
    B --> F[Playwright<br/>PDF Generation]
    
    subgraph "Frontend Components"
        A1[test/page.tsx<br/>Main Editor]
        A2[ImageEditor.tsx<br/>Visual Editor]
        A3[State Management<br/>React Hooks]
    end
    
    subgraph "Backend Services"
        B1[main.py<br/>API Routes]
        B2[storage.py<br/>File Management]
        B3[ocr_service.py<br/>Text Recognition]
        B4[html_render.py<br/>HTML/PDF]
    end
    
    A --> A1
    A --> A2
    A --> A3
    A1 --> B1
    A2 --> B1
    B1 --> B2
    B1 --> B3
    B1 --> B4
    B1 --> C
```

## Data Flow Architecture

```mermaid
flowchart TD
    %% PDF Processing Pipeline
    A[User Uploads PDF] --> B{Validate File}
    B -->|Valid| C[POST /api/translate]
    B -->|Invalid| D[Show Error]
    
    C --> E[Create Job ID]
    E --> F[Save input.pdf]
    F --> G[POST /api/process/{job_id}]
    
    G --> H[Render PDF to PNG]
    H --> I[OpenAI Vision Analysis]
    I --> J[Generate vision.json]
    
    J --> K[POST /api/pdf-markdown/{job_id}]
    K --> L[Convert to Markdown]
    L --> M[Extract Images to md_assets/]
    
    M --> N[GET /api/pdf-markdown/{job_id}]
    N --> O[Load in Editor]
    
    %% OCR Workflow
    O --> P[User clicks OCR Images]
    P --> Q[getImageNamesFromMarkdown()]
    Q --> R[For each image]
    
    R --> S[POST /api/ocr/{job_id}/{image}]
    S --> T[Perform OCR]
    T --> U[Return bounding boxes]
    U --> V[Store in state]
    
    %% Visual Editing
    V --> W[User selects image]
    W --> X[ImageEditor mounts]
    X --> Y[Load saved boxes or init from OCR]
    
    Y --> Z[User edits boxes<br/>- Drag to move<br/>- Resize handles<br/>- Edit text]
    Z --> AA[Click Save]
    AA --> AB[PUT /api/ocr-translations/{job_id}/{image}]
    AB --> AC[Save boxes to JSON]
    
    AC --> AD[Auto-generate preview]
    AD --> AE[GET /api/preview-overlay/{job_id}/{image}]
    AE --> AF[Show preview]
    
    %% PDF Generation
    AF --> AG[User clicks Generate PDF]
    AG --> AH[POST /api/pdf-from-markdown-with-ocr/{job_id}]
    AH --> AI[Process Markdown with OCR]
    AI --> AJ[Generate HTML with overlays]
    AJ --> AK[Playwright HTML→PDF]
    AK --> AL[Open result.pdf in browser]
```

## Component Interaction Diagram

```mermaid
sequenceDiagram
    participant User
    participant TestPage
    participant ImageEditor
    participant API
    participant Storage
    
    User->>TestPage: Upload PDF
    TestPage->>API: POST /api/translate
    API->>Storage: Save input.pdf
    API-->>TestPage: Return job_id
    
    TestPage->>API: POST /api/process/{job_id}
    API->>Storage: Create pages/ directory
    API->>API: Render PDF to PNGs
    API->>API: OpenAI vision analysis
    API->>Storage: Save vision.json
    API-->>TestPage: Processing complete
    
    TestPage->>API: POST /api/pdf-markdown/{job_id}
    API->>API: Convert vision to Markdown
    API->>Storage: Save layout.md and md_assets/
    API-->>TestPage: Conversion complete
    
    TestPage->>API: GET /api/pdf-markdown/{job_id}
    API->>Storage: Read layout.md
    API-->>TestPage: Return Markdown content
    
    User->>TestPage: Click "OCR Images"
    TestPage->>API: POST /api/ocr/{job_id}/{image}
    API->>Storage: Read image from md_assets/
    API->>API: Perform OCR
    API->>Storage: Check existing translations
    API-->>TestPage: Return OCR boxes + saved text
    
    User->>TestPage: Select image
    TestPage->>ImageEditor: Mount with OCR data
    ImageEditor->>API: GET /api/ocr-translations/{job_id}/{image}
    API->>Storage: Read ocr_translations.json
    API-->>ImageEditor: Return saved boxes or empty
    
    User->>ImageEditor: Edit boxes (drag/resize/text)
    ImageEditor->>ImageEditor: Update state with changes
    User->>ImageEditor: Click Save
    ImageEditor->>API: PUT /api/ocr-translations/{job_id}/{image}
    API->>Storage: Update ocr_translations.json
    API-->>ImageEditor: Confirm save
    
    ImageEditor->>API: GET /api/preview-overlay/{job_id}/{image}
    API->>Storage: Read image + translations
    API->>API: Generate preview with overlays
    API-->>ImageEditor: Return PNG preview
    
    User->>TestPage: Click "Generate PDF with OCR"
    TestPage->>API: POST /api/pdf-from-markdown-with-ocr/{job_id}
    API->>Storage: Read layout.md
    API->>API: Process with OCR overlays (variant=1)
    API->>API: Generate HTML with text overlays
    API->>API: Playwright HTML to PDF conversion
    API->>Storage: Save result_ocr_overlay.pdf
    API-->>TestPage: Return PDF path
    
    TestPage->>TestPage: window.open(/api/result/{job_id})
```

## State Management Flow

```mermaid
stateDiagram-v2
    [*] --> Idle: Page loads
    
    Idle --> Uploading: User drops PDF
    Uploading --> Processing: Upload complete
    Processing --> Editing: Processing complete
    Editing --> Editing: User makes changes
    
    Uploading --> Error: Upload fails
    Processing --> Error: Processing fails
    Editing --> Error: Operation fails
    
    Error --> Idle: User clears error
    
    Editing --> Generating: User clicks Generate PDF
    Generating --> Editing: Generation complete
    Generating --> Error: Generation fails
    
    state Uploading {
        [*] --> Validating
        Validating --> UploadingFile
        UploadingFile --> [*]
    }
    
    state Processing {
        [*] --> ConvertingPDF
        ConvertingPDF --> AnalyzingVision
        AnalyzingVision --> GeneratingMarkdown
        GeneratingMarkdown --> [*]
    }
    
    state Editing {
        [*] --> Ready
        Ready --> RunningOCR: User clicks OCR
        RunningOCR --> Ready
        Ready --> EditingImage: User selects image
        EditingImage --> Ready: User saves changes
        Ready --> [*]
    }
    
    state Generating {
        [*] --> PreparingContent
        PreparingContent --> RenderingHTML
        RenderingHTML --> ConvertingPDF
        ConvertingPDF --> [*]
    }
```

## File Storage Structure

```mermaid
graph TD
    A[data/] --> B[jobs/]
    B --> C[{job_id}/]
    C --> D[input.pdf]
    C --> E[job.json]
    C --> F[vision.json]
    C --> G[layout.md]
    C --> H[ocr_translations.json]
    C --> I[result.pdf]
    C --> J[result_ocr_overlay.pdf]
    C --> K[md_assets/]
    C --> L[pages/]
    
    K --> K1[page1_img1.png]
    K --> K2[page1_img2.png]
    K --> K3[...]
    
    L --> L1[page_1.png]
    L --> L2[page_2.png]
    L --> L3[debug_page_1.png]
    
    C --> M[render.html]
    C --> N[document_with_ocr_{job_id}.html]
    C --> O[markdown_for_pdf.md]
    C --> P[markdown_for_ocr_overlay.md]
```

## Coordinate System Transformation

```mermaid
graph LR
    A[Natural Image<br/>Coordinates<br/>(Raw Pixels)] --> B[Screen<br/>Coordinates<br/>(Viewport)]
    B --> C[Scaled<br/>Coordinates<br/>(Display)]

    subgraph "Transformation Process"
        T1[GetBoundingClientRect<br/>img element]
        T2[Calculate Scale Factors<br/>natural vs display size]
        T3[Apply Transformations<br/>with zoom factor]
        T4[Grid Snapping<br/>5px increments]
    end
    
    A --> T1
    T1 --> T2
    T2 --> T3
    T3 --> T4
    T4 --> B
    B --> C
```

## Error Handling Flow

```mermaid
flowchart TD
    A[User Action] --> B{Validation}
    B -->|Fail| C[Client-side Validation Error]
    B -->|Pass| D[API Request]
    
    D --> E{API Response}
    E -->|200 OK| F[Success Handler]
    E -->|400 Bad Request| G[Validation Error]
    E -->|404 Not Found| H[Resource Error]
    E -->|500 Server Error| I[Server Error]
    E -->|Network Error| J[Connection Error]
    
    C --> K[Show User Message]
    G --> K
    H --> K
    I --> K
    J --> K
    
    K --> L[Update UI State]
    L --> M[Log Error<br/>if in development]
    
    F --> N[Update Success State]
    N --> O[Proceed with Workflow]
```

## Performance Optimization Layers

```mermaid
graph TD
    A[Application Performance] --> B[Frontend Optimizations]
    A --> C[Backend Optimizations]
    A --> D[Infrastructure Optimizations]
    
    B --> B1[Virtual Scrolling<br/>react-window]
    B --> B2[Component Memoization<br/>useMemo/useCallback]
    B --> B3[Lazy Loading<br/>Image on demand]
    B --> B4[Batch Updates<br/>State grouping]
    
    C --> C1[Streaming Uploads<br/>copyfileobj]
    C --> C2[Atomic File Operations<br/>temp file + rename]
    C --> C3[Caching Layer<br/>Redis potential]
    C --> C4[Async Processing<br/>Background tasks]
    
    D --> D1[CDN for Assets<br/>Image delivery]
    D --> D2[Load Balancing<br/>Multiple instances]
    D --> D3[Database Optimization<br/>Query indexing]
    D --> D4[Monitoring & Metrics<br/>Performance tracking]
```

These diagrams provide visual representations of the key architectural patterns, data flows, and component interactions in the PDF Translator `/test` page implementation.