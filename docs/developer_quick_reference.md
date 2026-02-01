# PDF Translator `/test` Page - Developer Quick Reference

## 🚀 Quick Start Guide

### Starting the Development Environment

```bash
# 1. Install all dependencies
make install

# 2. Start Redis (required)
make redis-up

# 3. Start backend (terminal 1)
make api-dev

# 4. Start frontend (terminal 2) 
make web-dev

# Or start both simultaneously
make dev
```

**Access URLs:**
- Frontend: http://localhost:3000/test
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📁 Key File Locations

### Frontend Files
```
/apps/web/app/test/page.tsx          # Main test page (1,304 lines)
/apps/web/app/components/ImageEditor.tsx # Visual editor (551 lines)
/apps/web/package.json                # Frontend dependencies
```

### Backend Files
```
/apps/api/main.py                     # API routes (1,826 lines)
/apps/api/storage.py                  # File management (158 lines)
/apps/api/preview_overlay.py          # Preview generation (83 lines)
/apps/api/requirements.txt            # Backend dependencies
```

## 🔧 Common Development Tasks

### Adding a New API Endpoint

1. **Define the route in `main.py`:**
```python
@app.post("/api/new-feature/{job_id}")
async def new_feature_endpoint(job_id: str, payload: dict):
    # Implementation here
    return {"status": "success"}
```

2. **Add frontend integration in `test/page.tsx`:**
```typescript
const handleNewFeature = async () => {
  const response = await fetch(`${API_BASE_URL}/api/new-feature/${jobId}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({data: 'value'})
  });
  const result = await response.json();
  // Handle result
};
```

### Modifying the Image Editor

**Key files to modify:**
- `/apps/web/app/components/ImageEditor.tsx` - Visual editing logic
- `/apps/web/app/test/page.tsx` - Integration with main page
- `/apps/api/preview_overlay.py` - Preview generation

**Common modifications:**
- Adding new interaction modes
- Changing box styling
- Modifying coordinate transformations
- Adding new toolbar buttons

### Updating Data Models

**Frontend interface (TypeScript):**
```typescript
// In test/page.tsx
interface CustomBox extends Box {
  customField: string;
}
```

**Backend model (Pydantic):**
```python
# In main.py
class CustomBox(Box):
    custom_field: str
```

## 🐛 Debugging Guide

### Frontend Debugging

**Enable detailed logging:**
```typescript
// Add to useEffect or function
console.log('=== DEBUG INFO ===');
console.log('State:', { jobId, markdown, imageOcrData });
console.log('Timestamp:', new Date().toISOString());
```

**Component debugging:**
```typescript
// In ImageEditor.tsx
useEffect(() => {
  console.log('ImageEditor mounted with props:', {
    imageUrl,
    jobId,
    imageName,
    initialBoxes
  });
}, [imageUrl, jobId, imageName, initialBoxes]);
```

### Backend Debugging

**Add debug prints:**
```python
@app.post("/api/ocr/{job_id}/{image_name}")
async def ocr_image(job_id: str, image_name: str):
    print(f"=== OCR DEBUG ===")
    print(f"Job ID: {job_id}")
    print(f"Image: {image_name}")
    print(f"Job dir: {storage_manager.jobs_dir / job_id}")
    
    # Your logic here
    
    print(f"OCR result: {len(ocr_boxes)} boxes found")
    return result
```

**Check job files:**
```bash
# View job structure
ls -la data/jobs/{job_id}/

# Check job metadata
cat data/jobs/{job_id}/job.json

# View OCR translations
cat data/jobs/{job_id}/ocr_translations.json
```

### API Testing

**Using curl:**
```bash
# Upload PDF
curl -X POST http://localhost:8000/api/translate \
  -F "file=@sample.pdf" \
  -F "target_language=en"

# Process job
curl -X POST http://localhost:8000/api/process/{job_id}

# Run OCR on image
curl -X POST http://localhost:8000/api/ocr/{job_id}/page1_img1.png

# Get OCR translations
curl http://localhost:8000/api/ocr-translations/{job_id}/page1_img1.png

# Save OCR translations
curl -X PUT http://localhost:8000/api/ocr-translations/{job_id}/page1_img1.png \
  -H "Content-Type: application/json" \
  -d '{"boxes":[{"id":"box-1","x":100,"y":50,"w":200,"h":30,"text":"TEST"}]}'
```

## 📊 Performance Monitoring

### Frontend Performance
```typescript
// Measure component render times
const startTime = performance.now();
// ... component logic
const endTime = performance.now();
console.log(`Component rendered in ${endTime - startTime}ms`);
```

### Backend Performance
```python
import time

start_time = time.time()
# ... processing logic
end_time = time.time()
print(f"Processing took {end_time - start_time:.2f} seconds")
```

### Memory Usage Monitoring
```bash
# Monitor process memory
ps aux | grep "uvicorn\|next-dev"

# Check file sizes
du -sh data/jobs/{job_id}/
```

## 🔒 Security Checklist

### Before Deployment
- [ ] Remove debug logging/print statements
- [ ] Validate all user inputs
- [ ] Implement rate limiting
- [ ] Set up proper CORS policies
- [ ] Configure HTTPS/SSL
- [ ] Review file upload restrictions
- [ ] Test path traversal protection
- [ ] Verify job isolation

### Security Testing
```bash
# Test path traversal attempts
curl "http://localhost:8000/api/md-asset/../etc/passwd"
curl "http://localhost:8000/api/md-asset/%2e%2e/etc/passwd"

# Test file upload limits
# Try uploading oversized files
# Try uploading non-PDF files with PDF extension
```

## 🧪 Testing Procedures

### Manual Testing Script

1. **PDF Upload Test**
   - Upload various PDF sizes (small, medium, large)
   - Try invalid file types
   - Test drag-and-drop vs file browser

2. **OCR Processing Test**
   - Process PDFs with different image qualities
   - Test multiple images per document
   - Verify bounding box accuracy

3. **Visual Editing Test**
   - Drag boxes to different positions
   - Resize boxes using corner handles
   - Edit text content
   - Test undo/redo functionality
   - Try zoom in/out functionality

4. **PDF Generation Test**
   - Generate PDF with OCR overlays
   - Verify text positioning accuracy
   - Check PDF quality and file size
   - Test opening generated PDF

### Automated Testing
```bash
# Run backend tests
cd apps/api
python -m pytest test_*.py -v

# Run specific test
python test_complete_ocr_workflow.py

# Frontend testing (if configured)
cd apps/web
pnpm test
```

## 🚨 Common Issues and Solutions

### Issue: "Job not found" errors
**Solution:**
```bash
# Check if job directory exists
ls data/jobs/

# Verify job.json exists
cat data/jobs/{job_id}/job.json

# Recreate job if needed
curl -X POST http://localhost:8000/api/translate -F "file=@sample.pdf" -F "target_language=en"
```

### Issue: OCR not working
**Solution:**
```bash
# Check if image exists
ls data/jobs/{job_id}/md_assets/

# Test OCR endpoint directly
curl -X POST http://localhost:8000/api/ocr/{job_id}/page1_img1.png

# Check backend logs for OCR errors
```

### Issue: Preview not updating
**Solution:**
```bash
# Check if ocr_translations.json exists
cat data/jobs/{job_id}/ocr_translations.json

# Verify image name matches
# Clear browser cache and reload
```

### Issue: PDF generation fails
**Solution:**
```bash
# Install Playwright browsers
make api-playwright-install

# Check if required dependencies are installed
make api-importcheck

# Verify sufficient disk space
df -h
```

## 📈 Monitoring and Metrics

### Key Metrics to Track
- Average PDF processing time
- OCR accuracy rates
- User session duration
- Error rates by endpoint
- File upload success rates
- Memory usage patterns

### Log Analysis
```bash
# Search backend logs
grep "ERROR" apps/api/logs/*.log

# Count API requests
grep "POST\|GET" apps/api/logs/*.log | wc -l

# Monitor specific endpoints
grep "/api/ocr" apps/api/logs/*.log
```

## 🆘 Emergency Procedures

### Service Recovery
```bash
# Restart backend
make api-dev

# Restart frontend  
make web-dev

# Clear job data (last resort)
rm -rf data/jobs/*
```

### Data Recovery
```bash
# Backup current jobs
tar -czf jobs_backup.tar.gz data/jobs/

# Restore from backup
tar -xzf jobs_backup.tar.gz
```

---

*This quick reference guide provides essential information for developers working with the PDF Translator `/test` page implementation.*