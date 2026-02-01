# PDF Generation API Examples

## Prerequisites

1. Start the API server:
```bash
make api-dev
```

2. Install Playwright Chromium (required for PDF generation):
```bash
make api-playwright-install
```

## API Flow

1. Translate (upload PDF)
2. Process (analyze with Vision API)
3. Generate (create PDF from vision result)

## Example Workflow

### 1. Translate - Upload PDF
```bash
curl -X POST http://localhost:8000/api/translate \
  -F "file=@sample.pdf" \
  -F "target_language=en"
```

Response:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "queued"
}
```

### 2. Process - Run Vision Analysis
```bash
curl -X POST http://localhost:8000/api/process/123e4567-e89b-12d3-a456-426614174000
```

Response (success):
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "done"
}
```

### 3. Generate - Create PDF from Vision Result
```bash
curl -X POST http://localhost:8000/api/generate/123e4567-e89b-12d3-a456-426614174000
```

Response (success):
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "done",
  "output": "pdf"
}
```

### 4. Download Generated PDF
```bash
curl -X GET http://localhost:8000/api/result/123e4567-e89b-12d3-a456-426614174000 \
  -H "Accept: application/pdf" \
  -o translated.pdf
```

Or view in browser:
```bash
open http://localhost:8000/api/result/123e4567-e89b-12d3-a456-426614174000
```

## Error Handling

### Missing Playwright/Chromium
If you get an error like:
```json
{
  "detail": "Chromium not installed for Playwright. Run: make api-playwright-install"
}
```

Solution:
```bash
make api-playwright-install
```

### Job Not Done
If you try to generate before processing:
```json
{
  "detail": "Job must be in 'done' status. Run /api/process first."
}
```

### Missing Vision Data
If vision.json doesn't exist:
```json
{
  "detail": "vision.json not found. Run /api/process first."
}
```

## Complete Script Example

```bash
#!/bin/bash

# Upload PDF
response=$(curl -s -X POST http://localhost:8000/api/translate \
  -F "file=@sample.pdf" \
  -F "target_language=en")

job_id=$(echo "$response" | jq -r '.job_id')
echo "Job ID: $job_id"

# Process
echo "Processing..."
curl -s -X POST http://localhost:8000/api/process/$job_id

# Generate PDF
echo "Generating PDF..."
curl -s -X POST http://localhost:8000/api/generate/$job_id

# Download
echo "Downloading PDF..."
curl -s -X GET http://localhost:8000/api/result/$job_id \
  -H "Accept: application/pdf" \
  -o "translated_$job_id.pdf"

echo "Done! Saved as translated_$job_id.pdf"
```

## Files Created

After successful generation, these files will be created in `data/jobs/{job_id}/`:

- `render.html` - Debug HTML representation of the document
- `output.pdf` - Final generated PDF
- `job.json` - Updated with `render_html_path` and `output_path`
