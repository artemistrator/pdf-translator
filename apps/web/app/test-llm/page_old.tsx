'use client'

import { useState, useEffect } from 'react'
import MarkdownPreview from '../components/MarkdownPreview'

export default function TestLlmPage() {
  // State management
  const [jobId, setJobId] = useState(null)
  const [markdown, setMarkdown] = useState('')
  const [translatedImages, setTranslatedImages] = useState({})
  const [translatings, setTranslatings] = useState<Record<string, boolean>>({})
  const [status, setStatus] = useState('')
  const [error, setError] = useState<string | null>(null)
  
  // Image editor states
  const [editingImage, setEditingImage] = useState<any>(null)
  const [textBlocks, setTextBlocks] = useState<any[]>([])
  const [selectedBlock, setSelectedBlock] = useState<any>(null)
  
  // API base URL
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
  
  // Handle PDF upload
  async function handleUploadPdf(file: File) {
    console.log('📁 [UPLOAD START]', { file: file.name, size: file.size })
    
    if (file.type !== 'application/pdf') {
      setError('Please select a PDF file')
      return
    }
    
    if (file.size > 20 * 1024 * 1024) {
      setError('File size exceeds 20MB limit')
      return
    }
    
    setStatus('Uploading PDF...')
    setError(null)
    
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
      console.log('✅ [UPLOAD SUCCESS]', { jobId: newJobId })
      
      // Step 2: Process PDF
      setStatus('Processing PDF...')
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
      console.log('✅ [PROCESS SUCCESS]')
      
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
      setStatus(`Converted to Markdown! (${markdownData.chars} chars, ${markdownData.images_count} images)`)
      console.log('✅ [MARKDOWN CONVERTED]', { chars: markdownData.chars, images: markdownData.images_count })
      
      // Step 4: Load Markdown content
      const getContentResponse = await fetch(`${API_BASE_URL}/api/pdf-markdown/${newJobId}`)
      
      if (!getContentResponse.ok) {
        const errorData = await getContentResponse.json()
        throw new Error(errorData.detail || 'Failed to load Markdown')
      }
      
      const contentData = await getContentResponse.json()
      setMarkdown(contentData.markdown)
      setStatus('Ready for editing!')
      console.log('✅ [MARKDOWN LOADED]')
      
    } catch (err) {
      const errorMessage = (err as Error).message
      setError(`Error: ${errorMessage}`)
      console.error('❌ [UPLOAD ERROR]', errorMessage)
    }
  }
  
  // Handle image translation
  async function handleTranslateImage(imageName: string) {
    console.log('🟦 [TRANSLATE START]', { imageName, jobId })
    if (!jobId) { 
      console.error('❌ jobId is null')
      return
    }
    
    // Set loading state
    setTranslatings(prev => ({ ...prev, [imageName]: true }))
    
    try {
      const url = `${API_BASE_URL}/api/vision-translate/${jobId}/${imageName}`
      console.log('🟦 [API CALL]', { url })
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_language: 'russian' })
      })
      
      const data = await response.json()
      if (!response.ok) { 
        console.error('❌ API ERROR', data)
        setError(`Error: ${data.error}`)
        return
      }
      
      const newUrl = `${API_BASE_URL}/api/md-asset/${jobId}/${data.translated_image_name}`
      console.log('✅ [SUCCESS]', { newUrl })
      
      setTranslatedImages(prev => ({ ...prev, [imageName]: newUrl }))
      setStatus(`Successfully translated ${imageName}`)
    } catch (error) {
      console.error('❌ EXCEPTION', error)
      setError(`Error: ${(error as Error).message}`)
    } finally {
      setTranslatings(prev => ({ ...prev, [imageName]: false }))
    }
  }
  
  // Handle file input change
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleUploadPdf(e.target.files[0])
    }
  }
  
  // Auto-hide error after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError(null)
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [error])
  

  
  // Save final image
  const saveEditedImage = async () => {
    if (!editingImage || !jobId) return
    
    try {
      setStatus('Saving edited image...')
      
      const response = await fetch(`${API_BASE_URL}/api/save-edited-image/${jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          imageName: editingImage.name,
          textBlocks
        })
      })
      
      const data = await response.json()
      if (!response.ok) throw new Error(data.error)
      
      // Update translated images
      const newUrl = `${API_BASE_URL}/api/md-asset/${jobId}/${data.final_image_name}`
      setTranslatedImages(prev => ({ ...prev, [editingImage.name]: newUrl }))
      
      // Close editor
      setEditingImage(null)
      setTextBlocks([])
      setSelectedBlock(null)
      
      setStatus('Image saved successfully!')
    } catch (error) {
      setError(`Save failed: ${(error as Error).message}`)
    }
  }
  
  // Handle block updates
  const updateBlock = (id: number, updates: Partial<any>) => {
    setTextBlocks(prev => prev.map(block => 
      block.id === id ? { ...block, ...updates } : block
    ))
  }
  
  // Save final image
  const saveEditedImage = async () => {
    if (!editingImage || !jobId) return
    
    try {
      setStatus('Saving edited image...')
      
      const response = await fetch(`${API_BASE_URL}/api/save-edited-image/${jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          imageName: editingImage.name,
          textBlocks
        })
      })
      
      const data = await response.json()
      if (!response.ok) throw new Error(data.error)
      
      // Update translated images
      const newUrl = `${API_BASE_URL}/api/md-asset/${jobId}/${data.final_image_name}`
      setTranslatedImages(prev => ({ ...prev, [editingImage.name]: newUrl }))
      
      // Close editor
      setEditingImage(null)
      setTextBlocks([])
      setSelectedBlock(null)
      
      setStatus('Image saved successfully!')
    } catch (error) {
      setError(`Save failed: ${(error as Error).message}`)
    }
  }
  
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
            🧠 LLM Markdown Editor
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
                  setTranslatedImages({})
                  setTranslatings({})
                  setStatus('')
                  setError(null)
                }}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#dc3545',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: '500'
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
        gridTemplateColumns: '1fr 1fr',
        height: 'calc(100vh - 80px)',
        overflow: 'hidden'
      }}>
        {/* Left Column - Upload Area */}
        <div style={{ 
          borderRight: '1px solid #eee', 
          display: 'flex', 
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          <div style={{
            padding: '1rem',
            borderBottom: '1px solid #eee',
            backgroundColor: '#f8f9fa',
            fontWeight: '500'
          }}>
            Upload PDF
          </div>
          
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            padding: '2rem'
          }}>
            {!jobId ? (
              <>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={handleFileChange}
                  style={{ 
                    padding: '1rem', 
                    border: '2px dashed #ccc',
                    borderRadius: '8px',
                    textAlign: 'center',
                    cursor: 'pointer'
                  }}
                />
                <p style={{ marginTop: '1rem', color: '#666' }}>
                  Select a PDF file to convert to Markdown
                </p>
              </>
            ) : (
              <div style={{ textAlign: 'center' }}>
                <h3>✅ Document Loaded</h3>
                <p>Job ID: {jobId}</p>
                <p>You can now edit the Markdown and translate images</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Markdown Preview */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          <div style={{
            padding: '1rem',
            borderBottom: '1px solid #eee',
            backgroundColor: '#f8f9fa',
            fontWeight: '500'
          }}>
            Live Markdown Preview
          </div>
          
          <div style={{ flex: 1, overflow: 'auto', padding: '1rem' }}>
            {markdown ? (
              <MarkdownPreview
                jobId={jobId}
                markdown={markdown}
                apiBaseUrl={API_BASE_URL}
                translatedImages={translatedImages}
                translatingImages={new Set(Object.keys(translatings).filter(key => translatings[key]))}
                onTranslateImage={handleTranslateImage}
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
                <h3>📄 Upload PDF to Begin</h3>
                <p>Upload a PDF document to convert it to editable markdown</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Status Bar */}
      {status && (
        <div style={{
          padding: '0.75rem 2rem',
          borderTop: '1px solid #eee',
          backgroundColor: '#d1ecf1',
          color: '#0c5460',
          fontSize: '0.9rem'
        }}>
          ℹ️ {status}
        </div>
      )}

      {/* Error Toast */}
      {error && (
        <div style={{
          position: 'fixed',
          top: '1rem',
          right: '1rem',
          zIndex: 1000,
          minWidth: '300px',
          padding: '1rem',
          backgroundColor: '#f8d7da',
          color: '#721c24',
          border: '1px solid #f5c6cb',
          borderRadius: '6px'
        }}>
          ❌ {error}
        </div>
      )}
    </div>
  )
}