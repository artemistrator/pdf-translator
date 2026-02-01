# Manual Testing Guide for Editor UI

## Fix for asyncio.run error: use async Playwright

**Problem**: PDF generation was failing with "asyncio.run() cannot be called from a running event loop" because sync Playwright was used inside async FastAPI endpoints.

**Solution**: Implemented async Playwright in `pdf_generate.py`:

- New async function: `html_to_pdf_bytes_async(html: str) -> bytes`
- Kept sync wrapper `html_to_pdf_bytes_sync()` only for CLI usage
- Updated `/api/generate/{job_id}` endpoint to use async version

**Commands to test the fix**:

```bash
# 1. Install Chromium (if not already done)
make api-playwright-install

# 2. Restart API server
pkill -f uvicorn || true
make api-dev

# 3. Run regression test
make api-regression-pdf

# 4. Test in UI: Upload PDF → Process → Edit → Generate PDF
```

**Acceptance Criteria**:
- [ ] "Generate PDF" button in UI works without asyncio errors
- [ ] `make api-regression-pdf` passes completely
- [ ] Generated `render.html` contains "Тестируем пдф"
- [ ] Output PDF file is created and > 1000 bytes

## New Endpoints Added

### 1. GET /api/vision/{job_id}
Get vision data (returns edited.json if exists, otherwise vision.json)

```bash
curl -X GET http://localhost:8000/api/vision/YOUR_JOB_ID
```

### 2. PUT /api/vision/{job_id}
Save edited vision data

```bash
curl -X PUT http://localhost:8000/api/vision/YOUR_JOB_ID \
  -H "Content-Type: application/json" \
  -d @edited_data.json
```

Example edited_data.json:
```json
{
  "pages": [
    {
      "page": 1,
      "blocks": [
        {
          "type": "heading",
          "text": "My Edited Heading",
          "bbox": [100, 50, 300, 80]
        },
        {
          "type": "paragraph",
          "text": "This is my edited paragraph text.",
          "bbox": [100, 100, 500, 200]
        }
      ]
    }
  ],
  "meta": {
    "job_id": "YOUR_JOB_ID",
    "target_language": "en",
    "processed_at": "2024-01-01T00:00:00Z"
  }
}
```

### 3. POST /api/generate/{job_id} (Updated)
Now uses edited.json if it exists, otherwise vision.json

```bash
curl -X POST http://localhost:8000/api/generate/YOUR_JOB_ID
```

## Complete Manual Test Flow

### Step 1: Upload PDF
```bash
curl -X POST http://localhost:8000/api/translate \
  -F "file=@sample.pdf" \
  -F "target_language=en"
```

Get the job_id from response.

### Step 2: Process
```bash
curl -X POST http://localhost:8000/api/process/YOUR_JOB_ID
```

### Step 3: Get Original Vision Data
```bash
curl -X GET http://localhost:8000/api/vision/YOUR_JOB_ID > original_vision.json
```

### Step 4: Edit the Data
Manually edit `original_vision.json` and save as `edited_vision.json`.

### Step 5: Save Edits
```bash
curl -X PUT http://localhost:8000/api/vision/YOUR_JOB_ID \
  -H "Content-Type: application/json" \
  -d @edited_vision.json
```

### Step 6: Generate PDF with Edits
```bash
curl -X POST http://localhost:8000/api/generate/YOUR_JOB_ID
```

### Step 7: Download PDF
```bash
curl -X GET http://localhost:8000/api/result/YOUR_JOB_ID \
  -H "Accept: application/pdf" \
  -o edited_document.pdf
```

## Verification

Check that files were created:
```bash
ls data/jobs/YOUR_JOB_ID/
# Should show: edited.json, render.html, output.pdf
```

Check job.json was updated:
```bash
cat data/jobs/YOUR_JOB_ID/job.json | jq '.has_manual_edits, .edited_path'
# Should show: true and path to edited.json
```

## Error Cases to Test

### 1. Job Not Found
```bash
curl -X GET http://localhost:8000/api/vision/nonexistent-job
# Should return 404
```

### 2. Vision Data Not Processed Yet
```bash
# Upload but don't process
curl -X POST http://localhost:8000/api/translate -F "file=@sample.pdf" -F "target_language=en"
# Try to get vision data immediately
curl -X GET http://localhost:8000/api/vision/YOUR_NEW_JOB_ID
# Should return 409 Conflict
```

### 3. Invalid JSON Structure
```bash
curl -X PUT http://localhost:8000/api/vision/YOUR_JOB_ID \
  -H "Content-Type: application/json" \
  -d '{"invalid": "structure"}'
# Should return 400 Bad Request
```

## Web UI Testing

1. Start both servers:
```bash
# Terminal 1
make api-dev

# Terminal 2
make web-dev
```

2. Open browser: http://localhost:3000

3. Follow the 4 steps:
   - Upload a PDF
   - Click Process
   - Edit text in textareas
   - Save edits and Generate PDF
   - Open/Download the result
