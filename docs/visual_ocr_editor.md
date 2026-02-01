# Visual OCR Editor - User Guide

## Overview
The Visual OCR Editor allows you to visually edit text extracted from images in your PDF documents. You can drag, resize, and edit text boxes directly on the image.

## Features Implemented

### ✅ Core Functionality
- **Draggable text boxes**: Click and drag to move text boxes anywhere on the image
- **Resizable boxes**: Use corner handles to resize text boxes
- **Direct text editing**: Click inside any box to edit the text content
- **Multi-image support**: Tab navigation between different images in your document
- **Zoom functionality**: Mouse wheel to zoom in/out (0.5x to 3x)
- **Grid snapping**: Boxes snap to 5px grid for precise alignment

### ✅ Advanced Features
- **Undo/Redo**: Ctrl+Z / Ctrl+Y for history navigation
- **Preview toggle**: Show/hide overlays to see original image
- **Reset positions**: Button to restore original OCR positions
- **Auto font sizing**: Font size adjusts based on box height
- **Save functionality**: Persists changes to backend storage

### ✅ Backend API Endpoints
- `PUT /api/ocr-translations/{job_id}/{image_name}` - Save individual translations
- Enhanced `POST /api/ocr/{job_id}/{image_name}` - Returns saved translations
- `GET /api/ocr-translations/{job_id}` - Retrieve all translations for a job

## How to Use

### 1. Upload and Process Document
1. Go to http://localhost:3001/test
2. Upload a PDF document
3. Wait for processing to complete
4. Convert to Markdown to extract images

### 2. Run OCR
1. Click "OCR Images" button
2. Wait for OCR processing to complete
3. Select an image from the dropdown

### 3. Edit Text Visually
1. **Drag boxes**: Click and hold on a box to move it
2. **Resize boxes**: Click and drag the corner circles
3. **Edit text**: Click inside any box to edit the text
4. **Zoom**: Use mouse wheel to zoom in/out
5. **Undo/Redo**: Use Ctrl+Z / Ctrl+Y

### 4. Save Changes
1. Click "Save Changes" in the editor toolbar
2. Changes are automatically saved to the backend
3. The PDF generation will use your edited text positions

## Technical Details

### Frontend Components
- `ImageEditor.tsx` - Main visual editor component
- `test/page.tsx` - Updated test page with editor integration

### Data Structure
```typescript
interface BoundingBox {
  x: number        // X coordinate
  y: number        // Y coordinate  
  width: number    // Box width
  height: number   // Box height
  text: string     // Text content
  fontSize?: number // Font size (auto-calculated)
  color?: string   // Text color
}
```

### Storage Format
Translations are stored in `jobs/{job_id}/ocr_translations.json`:
```json
{
  "image1.png": {
    "100_50_200_30": {
      "bbox": [100, 50, 200, 30],
      "text": "Edited text",
      "font_size": 16,
      "color": "#000000"
    }
  }
}
```

## Testing
Run the test script to verify backend endpoints:
```bash
cd apps/api
python3 test_visual_editor.py
```

## Known Limitations
- Currently supports only basic text editing (no rich text)
- Font family is fixed (Arial-like)
- Color selection is limited to hex codes
- No batch operations across multiple images

## Future Improvements
- Rich text formatting (bold, italic, underline)
- Custom font selection
- Color picker for text
- Batch edit mode
- Export/import translation templates
- Real-time collaboration features