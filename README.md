# Document Translator (Vision-LLM) MVP

Advanced document translation platform using computer vision and LLMs for accurate document reconstruction with preserved formatting.

## ✨ Features

- **PDF Translation**: Upload PDF documents and translate text while preserving original layout
- **OCR Integration**: Advanced Optical Character Recognition for text extraction from images
- **Visual Text Editor**: Interactive editor to adjust translated text positioning
- **Image Translation**: Translation of embedded images with text overlays
- **Markdown Conversion**: Convert PDFs to editable Markdown with embedded images
- **PDF Regeneration**: Reconstruct PDFs from translated content with original formatting

## 🏗️ Project Structure

```
.
├── /apps/
│   ├── /api/          # FastAPI backend (Python 3.11) with Vision APIs
│   └── /web/          # Next.js frontend (TypeScript) with visual editor
├── /infra/            # Docker Compose and dev scripts
├── /docs/             # Technical documentation
├── /data/             # Storage directory (gitignored)
├── .env.example
├── Makefile
└── README.md
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11
- Node.js 18+
- Docker & Docker Compose
- pnpm (preferred) or npm

### 2. Install dependencies

```bash
make install
```

### 3. Start Redis

```bash
make redis-up
```

### 4. Start Backend (API)

In terminal 1:
```bash
make api-dev
```

API will be available at: http://localhost:8000

### 5. Start Frontend (Web)

In terminal 2:
```bash
make web-dev
```

Web app will be available at: http://localhost:3000

## 🛠️ Development Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make redis-up` | Start Redis container |
| `make redis-down` | Stop Redis container |
| `make api-dev` | Start FastAPI development server |
| `make web-dev` | Start Next.js development server |
| `make dev` | Start both API and Web in parallel |
| `make lint` | Run linters on all code |
| `make format` | Format all code |

## 🖼️ Features Showcase

### Markdown Support (including tables)
![Markdown Support](https://github.com/artemistrator/pdf-translator/blob/main/%D0%A1%D0%BD%D0%B8%D0%BC%D0%BE%D0%BA%20%D1%8D%D0%BA%D1%80%D0%B0%D0%BD%D0%B0%202026-02-02%20%D0%B2%2014.34.11.png)

### Image Editor
![Image Editor](https://github.com/artemistrator/pdf-translator/blob/main/%D0%A1%D0%BD%D0%B8%D0%BC%D0%BE%D0%BA%20%D1%8D%D0%BA%D1%80%D0%B0%D0%BD%D0%B0%202026-02-02%20%D0%B2%2014.32.26.png)

## 🔧 API Endpoints

### Upload a PDF file:
```bash
curl -X POST http://localhost:8000/api/translate \
  -F "file=@/path/to/document.pdf" \
  -F "target_language=en"
```

Expected response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Process PDF with Vision API:
```bash
curl -X POST http://localhost:8000/api/process/550e8400-e29b-41d4-a716-446655440000
```

Expected response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "done"
}
```

### Check job status:
```bash
curl http://localhost:8000/api/status/550e8400-e29b-41d4-a716-446655440000
```

Expected response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": ""
}
```

### Convert to Markdown:
```bash
curl -X POST http://localhost:8000/api/pdf-markdown/550e8400-e29b-41d4-a716-446655440000
```

### Get Markdown content:
```bash
curl http://localhost:8000/api/pdf-markdown/550e8400-e29b-41d4-a716-446655440000
```

### Generate PDF from Markdown:
```bash
curl -X POST http://localhost:8000/api/pdf-from-markdown/550e800-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"markdown": "# Hello World\n\nTranslated content here..."}'
```

### OCR on images:
```bash
curl -X POST http://localhost:8000/api/ocr/550e8400-e29b-41d4-a716-446655440000/page1_img1.png
```

## 🖼️ Visual OCR Editor

The application includes a visual editor for fine-tuning text positioning:

1. **Upload PDF** - Start the translation process
2. **Process Document** - Extract images and text with Vision API
3. **Edit Content** - Modify text content and positioning in the visual editor
4. **Generate Output** - Create final translated PDF

## 📁 File Storage Location

Uploaded files and job data are stored in:
```
./data/jobs/{job_id}/
├── input.pdf
├── job.json
├── vision.json
├── render.html
└── output.pdf
```

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Variables:
- `OPENAI_API_KEY` - Your OpenAI API key (for future use)
- `STORAGE_DIR` - Directory for file storage
- `REDIS_URL` - Redis connection URL
- `API_BASE_URL` - Backend API base URL for frontend

## 🧪 Testing

Run the complete workflow test:
```bash
python apps/api/test_complete_ocr_workflow.py
```

## 🌐 Ports

- **API**: http://localhost:8000
- **Web**: http://localhost:3000
- **Redis**: localhost:6379

## 📋 Supported Formats

- **Input**: PDF documents
- **Output**: PDF, Markdown
- **Image Processing**: PNG, JPG, JPEG, GIF, SVG