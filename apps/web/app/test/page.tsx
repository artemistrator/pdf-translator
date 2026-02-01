'use client'

import { useState, useRef, useEffect } from 'react'
import ImageEditor from '../components/ImageEditor'

interface ImageEditorContainerProps {
  jobId: string | null;
  imageName: string;
  ocrResult: OcrResult;
  onSave: (imageName: string, boxes: Box[]) => void;
  onStatusChange: (status: string) => void;
  onPreviewGenerated: (previewUrl: string) => void;
}

const ImageEditorContainer = ({ 
  jobId, 
  imageName, 
  ocrResult, 
  onSave, 
  onStatusChange,
  onPreviewGenerated
}: ImageEditorContainerProps) => {
  const [boxes, setBoxes] = useState<Box[]>([]);
  const hasLoadedRef = useRef(false);
  const [isLoading, setIsLoading] = useState(true);
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
  
  // Load saved translations or initialize from OCR
  useEffect(() => {
    console.log('=== USEEFFECT RUNNING ===');
    console.log('Job ID:', jobId);
    console.log('Image name:', imageName);
    console.log('OCR Result:', ocrResult);
    console.log('Current boxes state:', boxes);
    console.log('Has loaded:', hasLoadedRef.current);
    console.log('Boxes length:', boxes.length);
    console.log('Timestamp:', new Date().toISOString());
    
    // Prevent reloading if we already have boxes and have loaded once
    if (hasLoadedRef.current) {
      console.log('SKIPPING LOAD - ALREADY LOADED (hasLoadedRef=true)');
      return;
    }
    
    // Additional check: if we have boxes, don't reload
    if (boxes.length > 0) {
      console.log('SKIPPING LOAD - ALREADY HAVE BOXES (boxes.length > 0)');
      hasLoadedRef.current = true; // Mark as loaded to prevent future loads
      return;
    }
    
    const loadBoxes = async () => {
      if (!jobId) return;
      
      setIsLoading(true);
      
      try {
        // Try to get saved translations first
        const response = await fetch(`${API_BASE_URL}/api/ocr-translations/${jobId}/${imageName}`);
        
        console.log('GET response status:', response.status);
        console.log('GET response ok?', response.ok);
        
        if (response.ok) {
          const data = await response.json();
          
          console.log('Loaded data:', data);
          console.log('Data type:', typeof data);
          console.log('Data keys:', Object.keys(data));
          console.log('Boxes in data:', data.boxes);
          console.log('Boxes type:', Array.isArray(data.boxes) ? 'array' : typeof data.boxes);
          
          // Check if we have saved boxes
          if (data.boxes && data.boxes.length > 0) {
            console.log('Setting boxes from saved data:', data.boxes);
            console.log('Number of boxes:', data.boxes.length);
            setBoxes(data.boxes);
            hasLoadedRef.current = true;
            onStatusChange(`Loaded ${data.boxes.length} saved boxes for ${imageName}`);
            return;
          } else {
            console.log('No saved boxes found, data.boxes:', data.boxes);
          }
        } else {
          console.log('GET request failed with status:', response.status);
        }
        
        // If no saved boxes or error, initialize from OCR
        const initialBoxes = ocrResult.ocr_boxes.map((box, index) => ({
          id: `box-${index}`,
          x: box.bbox[0],
          y: box.bbox[1],
          w: box.bbox[2] - box.bbox[0],
          h: box.bbox[3] - box.bbox[1],
          text: box.text,
          fontSize: Math.max(8, Math.min((box.bbox[3] - box.bbox[1]) * 0.8, 24)),
          color: '#000000'
        }));
        
        setBoxes(initialBoxes);
        hasLoadedRef.current = true;
        onStatusChange(`Initialized ${initialBoxes.length} boxes from OCR for ${imageName}`);
        
      } catch (err) {
        console.error('Failed to load boxes:', err);
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
        }));
        
        setBoxes(initialBoxes);
        hasLoadedRef.current = true;
        onStatusChange(`Initialized ${initialBoxes.length} boxes from OCR (fallback)`);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadBoxes();
  }, [jobId, imageName, onStatusChange]); // Dependencies that trigger useEffect
  
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100%',
        color: '#666'
      }}>
        Loading editor...
      </div>
    );
  }
  
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div>
        <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1rem' }}>
          Editing: {imageName}
        </h3>
        <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
          Drag boxes to move, resize corners to adjust size, edit text directly
        </p>
      </div>
      
      <div style={{ flex: 1, minHeight: 0 }}>
        <ImageEditor
          imageUrl={ocrResult.image_url}
          jobId={jobId || ''}
          imageName={imageName}
          initialBoxes={boxes}
          onSave={(boxes) => onSave(imageName, boxes)}
          onReset={() => onStatusChange(`Reset positions for ${imageName}`)}
          onPreviewGenerated={onPreviewGenerated}
        />
      </div>
    </div>
  );
};

interface OcrBox {
  text: string;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2] in image coordinates
  confidence: number;
}

// Box in image coordinates (native pixels)
interface Box {
  id: string;
  x: number;  // x coordinate in image pixels
  y: number;  // y coordinate in image pixels
  w: number;  // width in image pixels
  h: number;  // height in image pixels
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

export default function TestPage() {
  // State management
  const [jobId, setJobId] = useState<string | null>(null)
  const [markdown, setMarkdown] = useState<string>('')
  const [originalMarkdown, setOriginalMarkdown] = useState<string>('')
  const [isUploading, setIsUploading] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isGeneratingWithOcr, setIsGeneratingWithOcr] = useState(false)
  const [isRunningOcr, setIsRunningOcr] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [imageOcrData, setImageOcrData] = useState<ImageOcrData>({})
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>('')
  
  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // API base URL
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
  
  // Extract image names from markdown
  const getImageNamesFromMarkdown = (): string[] => {
    if (!markdown) return []
    
    // Match ![alt](md_assets/filename.png) patterns
    const regex = /!\[[^\]]*\]\(md_assets\/([^)]+)\)/g
    const matches: string[] = []
    let match
    
    while ((match = regex.exec(markdown)) !== null) {
      matches.push(match[1])
    }
    
    return matches
  }
  
  // Run OCR on all images
  const handleRunOcr = async () => {
    if (!jobId) return
    
    const imageNames = getImageNamesFromMarkdown()
    if (imageNames.length === 0) {
      setError('No images found in markdown')
      return
    }
    
    setIsRunningOcr(true)
    setError(null)
    setStatus(`Running OCR on ${imageNames.length} images...`)
    
    try {
      const newData: ImageOcrData = {}
      let successCount = 0
      
      for (const imageName of imageNames) {
        setStatus(`Running OCR on ${imageName}...`)
        
        try {
          const response = await fetch(`${API_BASE_URL}/api/ocr/${jobId}/${imageName}`, {
            method: 'POST'
          })
          
          if (!response.ok) {
            const errorData = await response.json()
            console.warn(`OCR failed for ${imageName}:`, errorData.detail)
            setError(`OCR failed for ${imageName}: ${errorData.detail}`)
            continue
          }
          
          const ocrResult: OcrResult = await response.json()
          
          // Initialize translations with original text
          const translations: { [index: number]: string } = {}
          ocrResult.ocr_boxes.forEach((box, index) => {
            translations[index] = box.text
          })
          
          newData[imageName] = {
            ocr_result: ocrResult,
            translations: translations
          }
          
          successCount++
          
        } catch (err) {
          console.warn(`Failed to process ${imageName}:`, err)
          setError(`Failed to process ${imageName}: ${(err as Error).message}`)
        }
      }
      
      if (successCount > 0) {
        setImageOcrData(newData)
        setStatus(`OCR completed for ${successCount}/${imageNames.length} images`)
        
        // Load saved translations if they exist
        await loadSavedTranslations()
      } else {
        setError('OCR failed for all images. Please check server logs.')
      }
      
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsRunningOcr(false)
    }
  }
  
  // Load saved OCR translations
  const loadSavedTranslations = async () => {
    if (!jobId) return
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/ocr-translations/${jobId}`)
      if (response.ok) {
        const data = await response.json()
        const savedTranslations = data.translations || {}
        
        // Merge with existing data
        setImageOcrData(prev => {
          const newData = { ...prev }
          Object.keys(savedTranslations).forEach(imageName => {
            if (newData[imageName]) {
              newData[imageName].translations = {
                ...newData[imageName].translations,
                ...savedTranslations[imageName]
              }
            }
          })
          return newData
        })
      }
    } catch (err) {
      console.warn('Failed to load saved translations:', err)
    }
  }
  
  // Save OCR translations (now uses boxes data)
  const saveOcrTranslations = async () => {
    if (!jobId) return
    
    try {
      // Convert current boxes to translations format
      const translationsToSave: { [imageName: string]: { [index: number]: string } } = {}
      
      Object.keys(imageOcrData).forEach(imageName => {
        const imageData = imageOcrData[imageName];
        if (imageData.boxes && imageData.boxes.length > 0) {
          // Use boxes data instead of old translations
          const boxesTranslations: { [index: number]: string } = {};
          imageData.boxes.forEach((box: Box, index: number) => {
            boxesTranslations[index] = box.text;
          });
          translationsToSave[imageName] = boxesTranslations;
        } else {
          // Fallback to old translations if no boxes
          translationsToSave[imageName] = imageData.translations || {};
        }
      })
      
      const response = await fetch(`${API_BASE_URL}/api/ocr-translations/${jobId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          translations: translationsToSave
        }),
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to save translations')
      }
      
      const result = await response.json()
      setStatus('OCR translations saved successfully')
      console.log('✅ OCR translations saved:', result)
    } catch (err) {
      const errorMessage = (err as Error).message
      setError(errorMessage)
      console.error('❌ Failed to save OCR translations:', errorMessage)
    }
  }
  
  // Update translation for a specific box
  const updateTranslation = (imageName: string, boxIndex: number, newText: string) => {
    setImageOcrData(prev => ({
      ...prev,
      [imageName]: {
        ...prev[imageName],
        translations: {
          ...prev[imageName].translations,
          [boxIndex]: newText
        }
      }
    }))
  }

  // Handle preview generation
  const handlePreviewGenerated = (url: string) => {
    setPreviewUrl(url)
    setStatus('Preview generated successfully')
  }

  // Handle save from ImageEditor
  const handleImageEditorSave = async (imageName: string, boxes: Box[]) => {
    if (!jobId) return
    
    console.log('=== SAVE FUNCTION CALLED ===');
    console.log('Job ID:', jobId);
    console.log('Image name:', imageName);
    console.log('Boxes to save:', boxes);
    console.log('Boxes length:', boxes.length);
    
    try {
      // Send all boxes at once using the new contract
      const url = `${API_BASE_URL}/api/ocr-translations/${jobId}/${imageName}`;
      console.log('Sending PUT request to:', url);
      
      const response = await fetch(url, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          boxes: boxes
        }),
      })
      
      console.log('Response status:', response.status);
      console.log('Response ok?', response.ok);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Save failed with status:', response.status);
        console.error('Error response:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const result = await response.json();
      console.log('Save successful, response:', result);
      setStatus(`✅ Saved ${result.count} boxes for ${imageName} - Preview updated below`)
      
      // Update local state without reloading from backend or OCR
      console.log('Updating local state with boxes:', boxes);
      
      // Also update translations to match boxes
      const updatedTranslations: { [index: number]: string } = {};
      boxes.forEach((box, index) => {
        updatedTranslations[index] = box.text;
      });
      
      setImageOcrData(prev => {
        const newState = {
          ...prev,
          [imageName]: {
            ...prev[imageName],
            boxes: boxes,
            translations: updatedTranslations
          }
        };
        console.log('New state:', newState);
        return newState;
      });
      console.log('Local state updated');
      
    } catch (err) {
      const errorMessage = (err as Error).message
      setError(errorMessage)
      console.error('❌ Failed to save image editor changes:', errorMessage)
    }
  }

  // Convert OCR boxes to editor format (image coordinates)
  const convertOcrBoxesToEditorFormat = (ocrBoxes: OcrBox[]): Box[] => {
    return ocrBoxes.map((box, index) => ({
      id: `box-${index}`,
      x: box.bbox[0],
      y: box.bbox[1],
      w: box.bbox[2] - box.bbox[0],
      h: box.bbox[3] - box.bbox[1],
      text: box.text,
      fontSize: Math.max(8, Math.min((box.bbox[3] - box.bbox[1]) * 0.8, 24)),
      color: '#000000'
    }))
  }

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 'z') {
          e.preventDefault()
          // Undo functionality would be handled by ImageEditor component
        } else if (e.key === 'y') {
          e.preventDefault()
          // Redo functionality would be handled by ImageEditor component
        }
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = async (file: File) => {
    if (file.type !== 'application/pdf') {
      setError('Please select a PDF file')
      return
    }
    
    if (file.size > 20 * 1024 * 1024) {
      setError('File size exceeds 20MB limit')
      return
    }

    setIsUploading(true)
    setError(null)
    setStatus('Uploading...')

    try {
      // Step 1: Upload PDF
      const formData = new FormData()
      formData.append('file', file)
      formData.append('target_language', 'en')

      const uploadResponse = await fetch(`${API_BASE_URL}/api/translate`, {
        method: 'POST',
        body: formData,
      })

      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const uploadData = await uploadResponse.json()
      const newJobId = uploadData.job_id
      setJobId(newJobId)
      setStatus(`Uploaded successfully! Job ID: ${newJobId}`)

      // Step 2: Process PDF (extract vision data)
      setStatus('Processing...')
      setIsProcessing(true)

      const processResponse = await fetch(`${API_BASE_URL}/api/process/${newJobId}`, {
        method: 'POST'
      })

      if (!processResponse.ok) {
        const errorData = await processResponse.json()
        throw new Error(errorData.detail || 'Processing failed')
      }

      const processData = await processResponse.json()
      if (processData.status !== 'done') {
        throw new Error(`Processing failed: ${processData.error || 'Unknown error'}`)
      }

      setStatus('Processing completed!')

      // Step 3: Convert to Markdown
      setStatus('Converting to Markdown...')
      
      const markdownResponse = await fetch(`${API_BASE_URL}/api/pdf-markdown/${newJobId}`, {
        method: 'POST'
      })

      if (!markdownResponse.ok) {
        const errorData = await markdownResponse.json()
        throw new Error(errorData.detail || 'Markdown conversion failed')
      }

      const markdownData = await markdownResponse.json()
      setStatus(`Converted to Markdown! Chars: ${markdownData.chars}, Images: ${markdownData.images_count}`)

      // Step 4: Load Markdown content
      const getContentResponse = await fetch(`${API_BASE_URL}/api/pdf-markdown/${newJobId}`)
      
      if (!getContentResponse.ok) {
        const errorData = await getContentResponse.json()
        throw new Error(errorData.detail || 'Failed to load Markdown')
      }

      const contentData = await getContentResponse.json()
      setMarkdown(contentData.markdown)
      setOriginalMarkdown(contentData.markdown)
      setStatus('Ready for editing!')

    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsUploading(false)
      setIsProcessing(false)
    }
  }

  const handleSaveMarkdown = async () => {
    if (!jobId || !markdown) return

    setIsSaving(true)
    setError(null)
    setStatus('Saving Markdown...')

    try {
      // Note: This would require a PUT endpoint for saving markdown
      // For now, we'll just show a success message
      setStatus('Markdown saved locally')
      setTimeout(() => setStatus('Ready for editing!'), 2000)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsSaving(false)
    }
  }

  const handleResetMarkdown = () => {
    setMarkdown(originalMarkdown)
    setStatus('Reset to original Markdown')
  }

  const handleGeneratePdf = async () => {
    if (!jobId) return

    setIsGenerating(true)
    setError(null)
    setStatus('Generating PDF...')

    try {
      const response = await fetch(`${API_BASE_URL}/api/generate/${jobId}?mode=html`, {
        method: 'POST'
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'PDF generation failed')
      }

      const data = await response.json()
      setStatus(`PDF generated successfully! Mode: ${data.mode}`)
      
      // Open PDF in new tab
      window.open(`${API_BASE_URL}/api/result/${jobId}`, '_blank')
      
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGeneratePdfFromMarkdown = async () => {
    if (!jobId || !markdown) return

    setIsGenerating(true)
    setError(null)
    setStatus('Generating PDF from Markdown...')

    try {
      const response = await fetch(`${API_BASE_URL}/api/pdf-from-markdown/${jobId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          markdown: markdown
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'PDF generation from Markdown failed')
      }

      const data = await response.json()
      setStatus(`PDF generated from Markdown successfully!`)
      
      // Open PDF in new tab
      window.open(`${API_BASE_URL}/api/result/${jobId}?mode=pdf-from-markdown`, '_blank')
      
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGeneratePdfWithOcrOverlays = async () => {
    if (!jobId || !markdown) return

    setIsGeneratingWithOcr(true)
    setError(null)
    setStatus('Generating PDF with OCR overlays...')

    try {
      const response = await fetch(`${API_BASE_URL}/api/pdf-from-markdown-with-ocr/${jobId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          markdown: markdown
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'PDF generation with OCR overlays failed')
      }

      const data = await response.json()
      setStatus(`PDF with OCR overlays generated successfully!`)
      
      // Open PDF in new tab
      window.open(`${API_BASE_URL}/api/result/${jobId}?mode=pdf-from-markdown`, '_blank')
      
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsGeneratingWithOcr(false)
    }
  }

  // Main Content */}
  const imageNames = getImageNamesFromMarkdown()
  
  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      fontFamily: 'system-ui, sans-serif'
    }}>
      {/* Header */}
      <header style={{
        padding: '1rem 2rem',
        borderBottom: '1px solid #eee',
        backgroundColor: '#f8f9fa'
      }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          maxWidth: '1600px',
          margin: '0 auto'
        }}>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: '600' }}>
            📄 PDF to Markdown Editor
          </h1>
          
          {jobId && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '1rem',
              fontSize: '0.9rem',
              color: '#666'
            }}>
              <span>Job ID: {jobId}</span>
              <button
                onClick={() => {
                  setJobId(null)
                  setMarkdown('')
                  setOriginalMarkdown('')
                  setStatus(null)
                  setError(null)
                }}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#dc3545',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.85rem'
                }}
              >
                New Document
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main style={{ 
        flex: 1, 
        display: 'grid', 
        gridTemplateColumns: imageNames.length > 0 ? '1fr 1fr 500px' : '1fr 1fr',
        height: 'calc(100vh - 80px)'
      }}>
        {/* Left Column - Markdown Editor */}
        <div style={{ 
          borderRight: '1px solid #eee', 
          display: 'flex', 
          flexDirection: 'column'
        }}>
          {/* Editor Toolbar */}
          <div style={{
            padding: '1rem',
            borderBottom: '1px solid #eee',
            backgroundColor: '#f8f9fa',
            display: 'flex',
            gap: '0.5rem',
            flexWrap: 'wrap'
          }}>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileInputChange}
              accept="application/pdf"
              style={{ display: 'none' }}
            />
            
            {!jobId ? (
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: '500'
                }}
              >
                {isUploading ? 'Uploading...' : 'Upload PDF'}
              </button>
            ) : (
              <>
                <button
                  onClick={handleSaveMarkdown}
                  disabled={isSaving}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: '500'
                  }}
                >
                  {isSaving ? 'Saving...' : 'Save Markdown'}
                </button>
                
                <button
                  onClick={handleResetMarkdown}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#ffc107',
                    color: '#212529',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: '500'
                  }}
                >
                  Reset to Original
                </button>
                
                <button
                  onClick={handleGeneratePdf}
                  disabled={isGenerating}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#17a2b8',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: '500'
                  }}
                >
                  {isGenerating ? 'Generating...' : 'Generate PDF (Vision)'}
                </button>
                
                <button
                  onClick={handleGeneratePdfFromMarkdown}
                  disabled={isGenerating || !markdown}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#6f42c1',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: '500'
                  }}
                >
                  {isGenerating ? 'Generating...' : 'Generate PDF from Markdown'}
                </button>
                
                <button
                  onClick={handleGeneratePdfWithOcrOverlays}
                  disabled={isGeneratingWithOcr || !markdown}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#fd7e14',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: '500'
                  }}
                >
                  {isGeneratingWithOcr ? 'Generating with OCR...' : 'Generate PDF with OCR Overlays'}
                </button>
              </>
            )}
          </div>

          {/* Drag & Drop Zone or Editor */}
          {!jobId ? (
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                padding: '2rem',
                border: dragActive ? '2px dashed #007bff' : '2px dashed #ccc',
                backgroundColor: dragActive ? '#e3f2fd' : '#fafafa',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <div style={{ textAlign: 'center' }}>
                <svg 
                  width="48" 
                  height="48" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="1.5"
                  style={{ marginBottom: '1rem', color: dragActive ? '#007bff' : '#666' }}
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                <h3 style={{ margin: '0 0 0.5rem 0', color: dragActive ? '#007bff' : '#333' }}>
                  {dragActive ? 'Drop PDF here' : 'Upload PDF Document'}
                </h3>
                <p style={{ margin: 0, color: '#666', fontSize: '0.9rem' }}>
                  Drag & drop a PDF file here, or click to browse
                </p>
                <p style={{ margin: '0.5rem 0 0 0', color: '#999', fontSize: '0.8rem' }}>
                  Supports PDF files up to 20MB
                </p>
              </div>
            </div>
          ) : (
            <textarea
              value={markdown}
              onChange={(e) => setMarkdown(e.target.value)}
              style={{
                flex: 1,
                padding: '1rem',
                border: 'none',
                outline: 'none',
                fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                fontSize: '0.9rem',
                lineHeight: '1.5',
                resize: 'none'
              }}
              placeholder="Edit your Markdown here..."
            />
          )}
        </div>

        {/* Right Column - Live Preview */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {/* Preview Header */}
          <div style={{
            padding: '1rem',
            borderBottom: '1px solid #eee',
            backgroundColor: '#f8f9fa',
            fontWeight: '500'
          }}>
            Live Preview
          </div>
          
          {/* Preview Content */}
          <div 
            style={{
              flex: 1,
              padding: '1.5rem',
              overflowY: 'auto',
              backgroundColor: 'white'
            }}
          >
            {markdown ? (
              <div style={{ 
                whiteSpace: 'pre-wrap',
                fontFamily: 'system-ui, sans-serif',
                lineHeight: '1.6'
              }}>
                {markdown}
              </div>
            ) : (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
                color: '#666',
                textAlign: 'center'
              }}>
                <svg 
                  width="64" 
                  height="64" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="1"
                  style={{ marginBottom: '1rem', opacity: 0.5 }}
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                <p style={{ margin: 0, fontSize: '1.1rem' }}>
                  {jobId 
                    ? 'Start editing to see the live preview' 
                    : 'Upload a PDF to see the Markdown preview'}
                </p>
              </div>
            )}
          </div>
        </div>
        
        {/* OCR Editor Panel (Right sidebar) */}
        {imageNames.length > 0 && (
          <div style={{ 
            borderLeft: '1px solid #eee', 
            display: 'flex', 
            flexDirection: 'column',
            backgroundColor: '#f8f9fa',
            overflow: 'hidden',
            minWidth: '500px'
          }}>
            {/* OCR Panel Header */}
            <div style={{
              padding: '1rem',
              borderBottom: '1px solid #eee',
              backgroundColor: '#e9ecef',
              fontWeight: '500'
            }}>
              🎨 Visual OCR Editor
            </div>
            
            {/* OCR Controls */}
            <div style={{
              padding: '1rem',
              borderBottom: '1px solid #eee',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem'
            }}>
              <button
                onClick={handleRunOcr}
                disabled={isRunningOcr || !jobId}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isRunningOcr || !jobId ? 'not-allowed' : 'pointer',
                  fontWeight: '500',
                  opacity: isRunningOcr || !jobId ? 0.6 : 1
                }}
              >
                {isRunningOcr ? 'Running OCR...' : 'OCR Images'}
              </button>
              
              <button
                onClick={saveOcrTranslations}
                disabled={!jobId || Object.keys(imageOcrData).length === 0}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: !jobId || Object.keys(imageOcrData).length === 0 ? 'not-allowed' : 'pointer',
                  fontWeight: '500',
                  opacity: !jobId || Object.keys(imageOcrData).length === 0 ? 0.6 : 1
                }}
              >
                Save Translations
              </button>
            </div>
            
            {/* Image Selection */}
            <div style={{
              padding: '1rem',
              borderBottom: '1px solid #eee'
            }}>
              <div style={{ fontWeight: '500', marginBottom: '0.5rem' }}>Select Image:</div>
              <select
                value={selectedImage || ''}
                onChange={(e) => setSelectedImage(e.target.value || null)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  background: 'white'
                }}
              >
                <option value="">-- Select an image --</option>
                {imageNames.map(name => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>
            
            {/* Action Buttons */}
            <div style={{
              padding: '1rem',
              borderBottom: '1px solid #eee',
              display: 'flex',
              gap: '0.5rem'
            }}>
              <button
                onClick={() => {
                  // Just show info that preview is automatic after save
                  setStatus('Preview updates automatically after saving text positions');
                }}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: '500'
                }}
              >
                ℹ️ Preview Updates Automatically
              </button>
            </div>
            
            {/* OCR Results */}
            <div style={{
              flex: 1,
              overflow: 'hidden',
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column'
            }}>
              {selectedImage && imageOcrData[selectedImage] ? (
                <ImageEditorContainer 
                  jobId={jobId}
                  imageName={selectedImage}
                  ocrResult={imageOcrData[selectedImage].ocr_result}
                  onSave={handleImageEditorSave}
                  onStatusChange={setStatus}
                  onPreviewGenerated={handlePreviewGenerated}
                />
              ) : (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  height: '100%',
                  color: '#666',
                  textAlign: 'center'
                }}>
                  <svg 
                    width="48" 
                    height="48" 
                    viewBox="0 0 24 24" 
                    fill="none" 
                    stroke="currentColor" 
                    strokeWidth="1"
                    style={{ marginBottom: '1rem', opacity: 0.5 }}
                  >
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <path d="M21 15l-5-5L5 21"></path>
                  </svg>
                  <p style={{ margin: 0 }}>
                    {Object.keys(imageOcrData).length === 0
                      ? 'Run OCR to extract text from images'
                      : 'Select an image to view/edit OCR results'}
                  </p>
                </div>
              )}
            </div>
            
            {/* Live Preview Section */}
            <div style={{
              padding: '1rem',
              borderTop: '1px solid #eee',
              backgroundColor: '#f8f9fa'
            }}>
              <div style={{
                fontWeight: '500',
                marginBottom: '0.75rem',
                fontSize: '0.9rem',
                color: '#495057'
              }}>
                📄 TEXT POSITION PREVIEW (updates after Save)
              </div>
              {previewUrl ? (
                <div style={{
                  textAlign: 'center',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  padding: '0.5rem',
                  border: '1px solid #dee2e6'
                }}>
                  <img
                    src={previewUrl}
                    alt="Preview with OCR overlay"
                    style={{
                      maxWidth: '100%',
                      maxHeight: '300px',
                      border: '1px solid #ced4da',
                      borderRadius: '2px'
                    }}
                  />
                </div>
              ) : (
                <div style={{
                  textAlign: 'center',
                  padding: '2rem',
                  color: '#6c757d',
                  fontStyle: 'italic'
                }}>
                  Save your text positions to see the preview
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Status Bar */}
      {(status || error) && (
        <div style={{
          padding: '0.75rem 2rem',
          borderTop: '1px solid #eee',
          backgroundColor: error ? '#f8d7da' : '#d4edda',
          color: error ? '#721c24' : '#155724',
          fontSize: '0.9rem'
        }}>
          {error ? `❌ ${error}` : `✅ ${status}`}
        </div>
      )}
    </div>
  )
}