'use client'

import { useState, useEffect, useRef } from 'react'
import MarkdownPreview from '../components/MarkdownPreview'

export default function TestLlmPage() {
  // State management
  const [jobId, setJobId] = useState<string | null>(null)
  const [markdown, setMarkdown] = useState('')
  const [translatedImages, setTranslatedImages] = useState<Record<string, string>>({})
  const [translatings, setTranslatings] = useState<Record<string, boolean>>({})
  const [status, setStatus] = useState('')
  const [error, setError] = useState<string | null>(null)
  
  // Image editor states
  const [editingImage, setEditingImage] = useState<any>(null)
  const [textBlocks, setTextBlocks] = useState<any[]>([])
  const [selectedBlock, setSelectedBlock] = useState<any>(null)
  const [draggingBlockId, setDraggingBlockId] = useState<number | null>(null)
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const [resizingBlockId, setResizingBlockId] = useState<number | null>(null)
  const [resizeHandle, setResizeHandle] = useState<'nw' | 'ne' | 'sw' | 'se' | null>(null)
  const [savedBlocksByImage, setSavedBlocksByImage] = useState<Record<string, any[]>>({})

  const editorContainerRef = useRef<HTMLDivElement | null>(null)
  
  // Simple image translation test states
  const [simpleImageFile, setSimpleImageFile] = useState<File | null>(null)
  const [simpleImagePreview, setSimpleImagePreview] = useState<string | null>(null)
  const [simpleTranslatedImage, setSimpleTranslatedImage] = useState<string | null>(null)
  const [simpleTranslating, setSimpleTranslating] = useState(false)
  
  // API base URL
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

  const activeBlock = selectedBlock
    ? textBlocks.find((block) => block.id === selectedBlock.id) || selectedBlock
    : null
  
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
  
  // Handle image translation with editor
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
      
      // Get translation data for editor
      const translateUrl = `${API_BASE_URL}/api/get-translation-data/${jobId}/${imageName}`
      console.log('🟦 [GET TRANSLATION DATA]', { translateUrl })
      
      const translateResponse = await fetch(translateUrl)
      const translationData = await translateResponse.json()
      console.log('✅ [TRANSLATION DATA]', translationData)
      
      // Open editor with translation data
      setEditingImage({
        name: imageName,
        originalUrl: `${API_BASE_URL}/api/md-asset/${jobId}/${imageName}`,
        translatedUrl: `${API_BASE_URL}/api/md-asset/${jobId}/${data.translated_image_name}`,
        translationData
      })
      
      // Initialize text blocks from translation data or previously saved state
      let blocks: any[] = []
      console.log('📊 [TRANSLATION ELEMENTS]', translationData.text_elements)

      const savedBlocks = savedBlocksByImage[imageName]

      if (savedBlocks && savedBlocks.length > 0) {
        // Re-use previously saved layout for this image
        blocks = savedBlocks
        console.log('♻️ [USING SAVED BLOCKS]', { imageName, count: blocks.length })
      } else if (translationData.text_elements && Array.isArray(translationData.text_elements)) {
        blocks = translationData.text_elements.map((element: any, index: number) => ({
          id: index,
          x: Math.max(10, Math.min(element.x || 50, 500)),
          y: Math.max(10, Math.min(element.y || 50 + index * 60, 700)),
          width: Math.max(100, Math.min(element.width || 200, 400)),
          height: Math.max(30, Math.min(element.height || 40, 100)),
          text: element.translation || element.original || 'Перевод',
          fontSize: element.fontSize || (element.text?.length > 20 ? 14 : 16),
          fontWeight: element.fontWeight || 'normal',
          fontStyle: element.fontStyle || 'normal',
          color: element.color || '#000000',
          backgroundColor: element.backgroundColor || 'rgba(255, 255, 255, 0.9)',
        }))
      } else {
        // Fallback blocks if no translation data
        blocks = [
          {
            id: 0,
            x: 50,
            y: 50,
            width: 200,
            height: 40,
            text: 'Пример текста',
            fontSize: 16,
            fontWeight: 'normal',
            fontStyle: 'normal',
            color: '#000000',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
          }
        ]
      }
      
      console.log('✅ [BLOCKS INITIALIZED]', blocks)
      setTextBlocks(blocks)
      setSelectedBlock(blocks[0] || null)
      
      setStatus(`Translation ready for editing: ${imageName}. Blocks: ${blocks.length}`)
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

  // Generate and download PDF that mirrors the current preview
  const handleDownloadPdf = async () => {
    if (!jobId || !markdown) return
    
    try {
      setStatus('Generating PDF from Markdown...')
      setError(null)

      // Переписываем markdown так, чтобы все картинки смотрели
      // на актуальные (переведённые/отредактированные) файлы,
      // как в превью.
      const imageRegex = /!\[[^\]]*\]\(([^)]+)\)/g
      const markdownForPdf = markdown.replace(imageRegex, (full, path) => {
        const rawPath = String(path)
        const noQuery = rawPath.split('?')[0]
        const originalName = noQuery.split('/').pop() || ''

        const mappedUrl = translatedImages[originalName]
        if (!mappedUrl) return full

        const mappedNoQuery = mappedUrl.split('?')[0]
        const mappedName = mappedNoQuery.split('/').pop() || originalName

        const newPath = rawPath.replace(originalName, mappedName)
        return full.replace(path, newPath)
      })

      const response = await fetch(`${API_BASE_URL}/api/pdf-from-markdown/${jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ markdown: markdownForPdf }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail?.error || data.detail || 'PDF generation failed')
      }

      setStatus('PDF generated. Opening preview...')

      // Open the generated PDF in a new tab (served by /api/result)
      const pdfUrl = `${API_BASE_URL}/api/result/${jobId}?mode=pdf-from-markdown`
      if (typeof window !== 'undefined') {
        window.open(pdfUrl, '_blank', 'noopener,noreferrer')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'PDF generation failed'
      setError(`PDF error: ${message}`)
    }
  }
  
  // Handle block updates
  const updateBlock = (id: number, updates: Partial<any>) => {
    setTextBlocks(prev => prev.map((block: any) => 
      block.id === id ? { ...block, ...updates } : block
    ))
  }

  const deleteBlock = (id: number) => {
    setTextBlocks(prev => prev.filter(block => block.id !== id))
    if (selectedBlock?.id === id) {
      setSelectedBlock(null)
    }
  }

  const handleBlockMouseDown = (e: React.MouseEvent<HTMLDivElement>, block: any) => {
    if (!editorContainerRef.current) return

    // Если клик пришёлся по элементу, помеченному как "no-drag" (кнопка удаления и т.п.),
    // не запускаем перетаскивание
    const target = e.target as HTMLElement
    if (target.closest('[data-no-drag="true"]')) {
      return
    }

    e.stopPropagation()
    const rect = editorContainerRef.current.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top

    setDraggingBlockId(block.id)
    setDragOffset({
      x: mouseX - block.x,
      y: mouseY - block.y,
    })
    setSelectedBlock(block)
  }

  const handleResizeMouseDown = (
    e: React.MouseEvent<HTMLDivElement>,
    block: any,
    handle: 'nw' | 'ne' | 'sw' | 'se'
  ) => {
    e.stopPropagation()
    setResizingBlockId(block.id)
    setResizeHandle(handle)
    setSelectedBlock(block)
  }

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!editorContainerRef.current) return
      const rect = editorContainerRef.current.getBoundingClientRect()
      const mouseX = e.clientX - rect.left
      const mouseY = e.clientY - rect.top

      if (draggingBlockId !== null) {
        setTextBlocks(prev =>
          prev.map(block => {
            if (block.id !== draggingBlockId) return block
            const newX = mouseX - dragOffset.x
            const newY = mouseY - dragOffset.y
            const clampedX = Math.max(0, Math.min(newX, rect.width - block.width))
            const clampedY = Math.max(0, Math.min(newY, rect.height - block.height))
            return { ...block, x: clampedX, y: clampedY }
          })
        )
      }

      if (resizingBlockId !== null && resizeHandle) {
        setTextBlocks(prev =>
          prev.map(block => {
            if (block.id !== resizingBlockId) return block

            let { x, y, width, height } = block
            const minWidth = 50
            const minHeight = 30

            const maxRight = rect.width
            const maxBottom = rect.height

            const right = x + width
            const bottom = y + height

            switch (resizeHandle) {
              case 'se': {
                const newRight = Math.min(mouseX, maxRight)
                const newBottom = Math.min(mouseY, maxBottom)
                width = Math.max(minWidth, newRight - x)
                height = Math.max(minHeight, newBottom - y)
                break
              }
              case 'sw': {
                const newLeft = Math.max(0, mouseX)
                const newBottom = Math.min(mouseY, maxBottom)
                width = Math.max(minWidth, right - newLeft)
                height = Math.max(minHeight, newBottom - y)
                x = Math.min(newLeft, right - minWidth)
                break
              }
              case 'ne': {
                const newRight = Math.min(mouseX, maxRight)
                const newTop = Math.max(0, mouseY)
                width = Math.max(minWidth, newRight - x)
                height = Math.max(minHeight, bottom - newTop)
                y = Math.min(newTop, bottom - minHeight)
                break
              }
              case 'nw': {
                const newLeft = Math.max(0, mouseX)
                const newTop = Math.max(0, mouseY)
                width = Math.max(minWidth, right - newLeft)
                height = Math.max(minHeight, bottom - newTop)
                x = Math.min(newLeft, right - minWidth)
                y = Math.min(newTop, bottom - minHeight)
                break
              }
            }

            return {
              ...block,
              x,
              y,
              width,
              height,
            }
          })
        )
      }
    }

    const handleMouseUp = () => {
      if (draggingBlockId !== null || resizingBlockId !== null) {
        setDraggingBlockId(null)
        setResizingBlockId(null)
        setResizeHandle(null)
      }
    }

    if (draggingBlockId !== null || resizingBlockId !== null) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [draggingBlockId, resizingBlockId, dragOffset, resizeHandle])
  
  // Save final image
  const saveEditedImage = async () => {
    if (!editingImage || !jobId) return
    
    try {
      setStatus('Saving edited image...')

      // Нормализуем координаты блоков относительно контейнера редактора,
      // чтобы backend мог корректно отрисовать их на исходном изображении.
      let payloadBlocks = textBlocks
      if (editorContainerRef.current) {
        const rect = editorContainerRef.current.getBoundingClientRect()
        const w = rect.width || 1
        const h = rect.height || 1
        payloadBlocks = textBlocks.map(block => ({
          ...block,
          normX: block.x / w,
          normY: block.y / h,
          normWidth: block.width / w,
          normHeight: block.height / h,
        }))
      }

      const response = await fetch(`${API_BASE_URL}/api/save-edited-image/${jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          imageName: editingImage.name,
          textBlocks: payloadBlocks,
        })
      })
      
      const data = await response.json()
      if (!response.ok) throw new Error(data.error)
      
      // Update translated images with cache busting
      const timestamp = Date.now()
      const newUrl = `${API_BASE_URL}/api/md-asset/${jobId}/${data.final_image_name}?t=${timestamp}`
      console.log('💾 [UPDATE TRANSLATED IMAGE]', { imageName: editingImage.name, newUrl, timestamp })
      
      // Force update the specific image in preview
      setTranslatedImages(prev => {
        const updated = { ...prev, [editingImage.name]: newUrl }
        console.log('🔄 [IMAGES STATE UPDATED]', updated)
        return updated
      })

      // Сохраняем актуальное состояние блоков для этого изображения,
      // чтобы при повторном открытии редактора сохранить layout / цвет / шрифт.
      setSavedBlocksByImage(prev => ({
        ...prev,
        [editingImage.name]: textBlocks,
      }))
      
      // Close editor
      setEditingImage(null)
      setTextBlocks([])
      setSelectedBlock(null)
      
      // Just update the preview - no page reload
      setStatus('Image saved successfully! Refreshing preview...')
      
      setStatus('Image saved successfully!')
    } catch (error) {
      setError(`Save failed: ${(error as Error).message}`)
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
  
  // Log image updates for debugging
  useEffect(() => {
    console.log('🖼️ [TRANSLATED IMAGES CHANGED]', translatedImages)
  }, [translatedImages])
  
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
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={handleDownloadPdf}
                  disabled={!markdown}
                  style={{
                    padding: '0.5rem 1rem',
                    background: markdown ? '#007bff' : '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: markdown ? 'pointer' : 'not-allowed',
                    fontSize: '0.85rem',
                    fontWeight: '500'
                  }}
                >
                  Скачать PDF
                </button>
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
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main style={{ 
        flex: 1, 
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 80px)',
        overflow: 'hidden',
        padding: '1rem'
      }}>
        {/* Upload Area - Above the dual panels */}
        {!jobId && (
          <div style={{
            marginBottom: '1rem',
            textAlign: 'center',
            padding: '2rem',
            border: '2px dashed #ccc',
            borderRadius: '8px'
          }}>
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
          </div>
        )}
        
        {/* Dual Panels Container */}
        <div style={{
          flex: 1,
          display: 'flex',
          gap: '1rem',
          minHeight: '0'
        }}>
          {/* Left Panel - Markdown Editor */}
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            border: '1px solid #ddd',
            borderRadius: '8px',
            overflow: 'hidden'
          }}>
            <div style={{
              padding: '1rem',
              borderBottom: '1px solid #eee',
              backgroundColor: '#f8f9fa',
              fontWeight: '500'
            }}>
              Markdown Editor
            </div>
            
            <div style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              padding: '1rem',
              overflow: 'hidden'
            }}>
              {jobId ? (
                <>
                  {/* Editor */}
                  <div style={{ flex: 1, marginBottom: '1rem' }}>
                    <textarea
                      value={markdown}
                      onChange={(e) => setMarkdown(e.target.value)}
                      style={{
                        width: '100%',
                        height: '100%',
                        minHeight: '300px',
                        fontFamily: 'monospace',
                        fontSize: '14px',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                        padding: '1rem',
                        resize: 'vertical'
                      }}
                      placeholder="Edit markdown here..."
                    />
                  </div>
                </>
              ) : (
                <div style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  color: '#666'
                }}>
                  <h3>📄 Load PDF First</h3>
                  <p>Upload a PDF to start editing</p>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Image Translation Editor */}
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            border: '1px solid #ddd',
            borderRadius: '8px',
            overflow: 'hidden'
          }}>
            <div style={{
              padding: '1rem',
              borderBottom: '1px solid #eee',
              backgroundColor: '#f8f9fa',
              fontWeight: '500'
            }}>
              {editingImage ? 'Image Editor' : 'Image Translation'}
            </div>
            
            <div style={{
              flex: 1,
              overflow: 'auto',
              padding: '1rem'
            }}>
              {editingImage ? (
                // Image Editor View
                <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                  <div 
                    ref={editorContainerRef}
                    style={{ 
                      position: 'relative', 
                      width: '100%', 
                      height: '400px',
                      border: '1px solid #ddd',
                      backgroundImage: `url(${editingImage.originalUrl})`,
                      backgroundSize: 'contain',
                      backgroundPosition: 'center',
                      backgroundRepeat: 'no-repeat'
                    }}
                  >
                    {textBlocks.map(block => (
                      <div
                        key={block.id}
                        onMouseDown={(e) => handleBlockMouseDown(e, block)}
                        style={{
                          position: 'absolute',
                          left: `${block.x}px`,
                          top: `${block.y}px`,
                          width: `${block.width}px`,
                          height: `${block.height}px`,
                          border: activeBlock?.id === block.id ? '2px solid #007bff' : '1px dashed #999',
                          backgroundColor: block.backgroundColor || 'rgba(255, 255, 255, 0.9)',
                          cursor: draggingBlockId === block.id ? 'grabbing' : 'move',
                          display: 'flex',
                          alignItems: 'center',
                          padding: '4px',
                          userSelect: 'none',
                          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                          boxSizing: 'border-box'
                        }}
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedBlock(block)
                        }}
                      >
                        <button
                          data-no-drag="true"
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteBlock(block.id)
                          }}
                          style={{
                            position: 'absolute',
                            top: '-12px',
                            right: '-16px',
                            width: '20px',
                            height: '20px',
                            borderRadius: '50%',
                            border: 'none',
                            backgroundColor: '#dc3545',
                            color: '#fff',
                            fontSize: '12px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.3)'
                          }}
                          title="Удалить блок"
                        >
                          ×
                        </button>

                        <input
                          type="text"
                          value={block.text}
                          onChange={(e) => updateBlock(block.id, { text: e.target.value })}
                          style={{
                            width: '100%',
                            height: '100%',
                            fontSize: `${block.fontSize}px`,
                            fontWeight: block.fontWeight,
                            fontStyle: block.fontStyle,
                            color: block.color,
                            border: 'none',
                            background: 'transparent',
                            outline: 'none',
                            fontFamily: 'inherit'
                          }}
                        />

                        {activeBlock?.id === block.id && (
                          <>
                            <div
                              onMouseDown={(e) => handleResizeMouseDown(e, block, 'nw')}
                              style={{
                                position: 'absolute',
                                width: '10px',
                                height: '10px',
                                left: '-5px',
                                top: '-5px',
                                borderRadius: '50%',
                                backgroundColor: '#007bff',
                                border: '2px solid #fff',
                                cursor: 'nw-resize',
                              }}
                            />
                            <div
                              onMouseDown={(e) => handleResizeMouseDown(e, block, 'ne')}
                              style={{
                                position: 'absolute',
                                width: '10px',
                                height: '10px',
                                right: '-5px',
                                top: '-5px',
                                borderRadius: '50%',
                                backgroundColor: '#007bff',
                                border: '2px solid #fff',
                                cursor: 'ne-resize',
                              }}
                            />
                            <div
                              onMouseDown={(e) => handleResizeMouseDown(e, block, 'sw')}
                              style={{
                                position: 'absolute',
                                width: '10px',
                                height: '10px',
                                left: '-5px',
                                bottom: '-5px',
                                borderRadius: '50%',
                                backgroundColor: '#007bff',
                                border: '2px solid #fff',
                                cursor: 'sw-resize',
                              }}
                            />
                            <div
                              onMouseDown={(e) => handleResizeMouseDown(e, block, 'se')}
                              style={{
                                position: 'absolute',
                                width: '10px',
                                height: '10px',
                                right: '-5px',
                                bottom: '-5px',
                                borderRadius: '50%',
                                backgroundColor: '#007bff',
                                border: '2px solid #fff',
                                cursor: 'se-resize',
                              }}
                            />
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                  
                  {/* Editor Controls */}
                  {activeBlock && (
                    <div style={{ 
                      marginTop: '1rem', 
                      padding: '1rem', 
                      border: '1px solid #ddd',
                      borderRadius: '4px'
                    }}>
                      <h4>Edit Text Block</h4>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                          <label>Font Size:</label>
                          <input
                            type="range"
                            min="8"
                            max="72"
                            value={activeBlock.fontSize}
                            onChange={(e) => updateBlock(activeBlock.id, { fontSize: parseInt(e.target.value) })}
                            style={{ width: '100%' }}
                          />
                          <span>{activeBlock.fontSize}px</span>
                        </div>
                        <div>
                          <label>Width:</label>
                          <input
                            type="range"
                            min="50"
                            max="500"
                            value={activeBlock.width}
                            onChange={(e) => updateBlock(activeBlock.id, { width: parseInt(e.target.value) })}
                            style={{ width: '100%' }}
                          />
                          <span>{activeBlock.width}px</span>
                        </div>
                      </div>
                      <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <button
                          onClick={() => updateBlock(activeBlock.id, { fontWeight: activeBlock.fontWeight === 'bold' ? 'normal' : 'bold' })}
                          style={{ 
                            padding: '0.5rem 1rem',
                            backgroundColor: activeBlock.fontWeight === 'bold' ? '#007bff' : '#f8f9fa',
                            border: '1px solid #ddd',
                            borderRadius: '4px'
                          }}
                        >
                          Bold
                        </button>
                        <button
                          onClick={() => updateBlock(activeBlock.id, { fontStyle: activeBlock.fontStyle === 'italic' ? 'normal' : 'italic' })}
                          style={{ 
                            padding: '0.5rem 1rem',
                            backgroundColor: activeBlock.fontStyle === 'italic' ? '#007bff' : '#f8f9fa',
                            border: '1px solid #ddd',
                            borderRadius: '4px'
                          }}
                        >
                          Italic
                        </button>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <label>Block color:</label>
                          <input
                            type="color"
                            value={activeBlock.backgroundColor || '#ffffff'}
                            onChange={(e) => updateBlock(activeBlock.id, { backgroundColor: e.target.value })}
                          />
                        </div>
                        <button
                          onClick={saveEditedImage}
                          style={{ 
                            padding: '0.5rem 1rem',
                            backgroundColor: '#28a745',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            marginLeft: 'auto'
                          }}
                        >
                          Save Image
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : jobId ? (
                // Show image translation interface
                <div>
                  <MarkdownPreview
                    jobId={jobId}
                    markdown={markdown}
                    apiBaseUrl={API_BASE_URL}
                    translatedImages={translatedImages}
                    translatingImages={new Set(Object.keys(translatings).filter(key => translatings[key]))}
                    onTranslateImage={handleTranslateImage}
                  />
                  <div style={{
                    marginTop: '1rem',
                    padding: '1rem',
                    backgroundColor: '#e9ecef',
                    borderRadius: '4px',
                    textAlign: 'center'
                  }}>
                    <p>👆 Click &apos;Translate to Russian&apos; buttons on images above to open the editor</p>
                  </div>
                </div>
              ) : (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  height: '100%',
                  color: '#666'
                }}>
                  <h3>🖼️ Image Translation</h3>
                  <p>Load a PDF and click translate buttons to edit images</p>
                </div>
              )}
            </div>
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