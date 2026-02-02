'use client'

import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
// @ts-ignore - react-window v1.8.10 doesn't include TypeScript definitions
import { FixedSizeList } from 'react-window'
import MarkdownPreview from './components/MarkdownPreview'

// Types for our data model
interface Block {
  id: string
  page: number
  blockIndex: number
  type: string
  text: string
  isChanged?: boolean
}

// Logger utility
const logger = {
  info: (...args: any[]) => console.log('🟦', ...args),
  error: (...args: any[]) => console.error('❌', ...args),
  warn: (...args: any[]) => console.warn('⚠️', ...args)
}

interface VisionData {
  pages: Array<{
    page: number
    blocks: Array<{
      type: string
      bbox: number[]
      text: string
    }>
  }>
  meta: any
}

export default function Home() {
  // State management
  const [step, setStep] = useState<'upload' | 'process' | 'edit' | 'generate'>('upload')
  const [jobId, setJobId] = useState<string | null>(null)
  const [visionOriginal, setVisionOriginal] = useState<VisionData | null>(null)
  const [flatBlocks, setFlatBlocks] = useState<Block[]>([])
  const [dirty, setDirty] = useState<boolean>(false)
  const [selectedPage, setSelectedPage] = useState<number | 'all'>('all')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [bulkFind, setBulkFind] = useState<string>('')
  const [bulkReplace, setBulkReplace] = useState<string>('')
  const [bulkPrefix, setBulkPrefix] = useState<string>('')
  const [generateMode, setGenerateMode] = useState<'html' | 'overlay'>('html')
  const [overlayScope, setOverlayScope] = useState<'headings' | 'safe' | 'all'>('headings')
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [totalPages, setTotalPages] = useState<number>(0)
  const [showDebugOverlays, setShowDebugOverlays] = useState<boolean>(false)
  const [isBuildingDebug, setIsBuildingDebug] = useState<boolean>(false)
  
  // New states for enhanced features
  const [changedBlocks, setChangedBlocks] = useState<Block[]>([])
  const [showChangesPanel, setShowChangesPanel] = useState<boolean>(false)
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null)
  const [history, setHistory] = useState<Block[][]>([])
  const [historyIndex, setHistoryIndex] = useState<number>(-1)
  const [autosaveStatus, setAutosaveStatus] = useState<string>('')
  const lastAutosaveTime = useRef<number>(0)
  
  // Markdown preview state
  const [markdownPreview, setMarkdownPreview] = useState<string>('')
  
  // Refs and form state
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [targetLanguage, setTargetLanguage] = useState('en')
  const containerRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<any>(null)
  const autosaveTimerRef = useRef<NodeJS.Timeout | null>(null)
  
  // Image translation states
  const [translatedImages, setTranslatedImages] = useState<Record<string, string>>({})
  const [translatingImages, setTranslatingImages] = useState<Set<string>>(new Set())

  // API base URL
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
  
  // Handle image translation
  const handleTranslateImage = async (imageName: string, targetLanguage: string) => {
    logger.info(`🟦 [TRANSLATE IMAGE] Start: ${imageName}`)
    
    if (!jobId) {
      logger.error('❌ [ERROR] jobId is null!')
      throw new Error('No job ID available')
    }
    
    // Add to translating set
    setTranslatingImages(prev => {
      const newSet = new Set(prev)
      newSet.add(imageName)
      logger.info('🟨 [SET TRANSLATING]', Array.from(newSet))
      return newSet
    })
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/vision-translate/${jobId}/${imageName}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target_language: targetLanguage })
        }
      )
      
      logger.info('🟦 [FETCH RESPONSE STATUS]', response.status, response.statusText)
      
      if (!response.ok) {
        const errorText = await response.text()
        logger.error('❌ [HTTP ERROR]', {
          status: response.status,
          statusText: response.statusText,
          errorBody: errorText
        })
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }
      
      const data = await response.json()
      logger.info('✅ [TRANSLATE RESPONSE]', data)
      
      // Update translated images object
      setTranslatedImages(prev => {
        const newObj = { ...prev }
        const translatedImageUrl = `${API_BASE_URL}/api/md-asset/${jobId}/${data.translated_image_name}`
        newObj[imageName] = translatedImageUrl
        logger.info('🟦 [OBJECT UPDATED]', {
          originalImage: imageName,
          translatedImage: translatedImageUrl,
          fullObject: newObj
        })
        return newObj
      })
      
    } catch (error) {
      logger.error('❌ [TRANSLATE ERROR]', error)
      throw error
    } finally {
      // Remove from translating set
      setTranslatingImages(prev => {
        const newSet = new Set(prev)
        newSet.delete(imageName)
        logger.info('🟨 [UNSET TRANSLATING]', Array.from(newSet))
        return newSet
      })
    }
  }

  // Convert vision data to markdown for preview
  const visionToMarkdown = (data: VisionData): string => {
    if (!data || !data.pages) return ''
    
    let markdown = ''
    
    data.pages.forEach((page, pageIndex) => {
      markdown += `\n## Page ${page.page}\n\n`
      
      page.blocks.forEach((block, blockIndex) => {
        if (block.type === 'image') {
          // Handle images
          const imageName = `page${page.page}_img${blockIndex}.png`
          markdown += `![Image from page ${page.page}](md_assets/${imageName})\n\n`
        } else if (block.type === 'heading') {
          // Handle headings
          const level = Math.min(block.text.length > 50 ? 3 : 2, 6)
          markdown += `${'#'.repeat(level)} ${block.text}\n\n`
        } else {
          // Handle text blocks
          if (block.text.trim()) {
            markdown += `${block.text}\n\n`
          }
        }
      })
    })
    
    return markdown.trim()
  }

  // Normalize vision data to flat blocks
  const normalizeVisionData = (data: VisionData): Block[] => {
    const blocks: Block[] = []
    data.pages.forEach((page, pageIndex) => {
      page.blocks.forEach((block, blockIndex) => {
        blocks.push({
          id: `${page.page}-${blockIndex}`,
          page: page.page,
          blockIndex: blockIndex,
          type: block.type,
          text: block.text
        })
      })
    })
    return blocks
  }

  // Calculate changed blocks
  const calculateChangedBlocks = useCallback((blocks: Block[], original: VisionData | null): Block[] => {
    if (!original) return []
    
    return blocks.map(block => {
      const originalPage = original.pages.find(p => p.page === block.page)
      const originalText = originalPage?.blocks[block.blockIndex]?.text || ''
      return {
        ...block,
        isChanged: block.text !== originalText
      }
    }).filter(block => block.isChanged)
  }, [])

  // Update changed blocks when flatBlocks or visionOriginal changes
  useEffect(() => {
    const newChangedBlocks = calculateChangedBlocks(flatBlocks, visionOriginal)
    setChangedBlocks(newChangedBlocks)
  }, [flatBlocks, visionOriginal, calculateChangedBlocks])

  // History management
  const addToHistory = useCallback((blocks: Block[]) => {
    setHistory(prev => {
      // Limit history to 20 steps
      const newHistory = prev.slice(0, historyIndex + 1)
      newHistory.push(JSON.parse(JSON.stringify(blocks)))
      return newHistory.slice(-20)
    })
    setHistoryIndex(prev => Math.min(prev + 1, 19))
  }, [historyIndex])

  // Debounced history addition for text changes
  const debouncedAddToHistory = useRef<NodeJS.Timeout | null>(null)
  
  const scheduleHistoryAdd = useCallback((blocks: Block[]) => {
    if (debouncedAddToHistory.current) {
      clearTimeout(debouncedAddToHistory.current)
    }
    debouncedAddToHistory.current = setTimeout(() => {
      addToHistory(blocks)
    }, 300)
  }, [addToHistory])

  // Initialize history when loading data
  useEffect(() => {
    if (flatBlocks.length > 0 && historyIndex === -1) {
      addToHistory(flatBlocks)
    }
  }, [flatBlocks, historyIndex, addToHistory])

  // Get unique page numbers and types for filters
  const uniquePages = useMemo(() => {
    if (!flatBlocks.length) return []
    const pages = Array.from(new Set(flatBlocks.map(b => b.page))).sort((a, b) => a - b)
    return pages
  }, [flatBlocks])

  const uniqueTypes = useMemo(() => {
    if (!flatBlocks.length) return []
    const types = Array.from(new Set(flatBlocks.map(b => b.type))).sort()
    return types
  }, [flatBlocks])

  // Filtered blocks with useMemo optimization
  const filteredBlocks = useMemo(() => {
    return flatBlocks.filter(block => {
      // Page filter
      if (selectedPage !== 'all' && block.page !== selectedPage) {
        return false
      }
      
      // Type filter
      if (typeFilter !== 'all' && block.type !== typeFilter) {
        return false
      }
      
      // Search filter (case insensitive)
      if (searchQuery && !block.text.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false
      }
      
      return true
    })
  }, [flatBlocks, selectedPage, typeFilter, searchQuery])

  // Handle beforeunload warning
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault()
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?'
        return e.returnValue
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [dirty])

  // Reset dirty state when loading new data
  useEffect(() => {
    setDirty(false)
    setHistory([])
    setHistoryIndex(-1)
  }, [jobId])

  // Autosave functionality
  const handleAutosave = useCallback(async () => {
    if (!jobId || !visionOriginal || !dirty) return
    
    try {
      // Reconstruct vision data format from flatBlocks
      const visionEdited = JSON.parse(JSON.stringify(visionOriginal))
      
      flatBlocks.forEach(block => {
        const page = visionEdited.pages.find((p: any) => p.page === block.page)
        if (page && page.blocks[block.blockIndex]) {
          page.blocks[block.blockIndex].text = block.text
        }
      })

      const response = await fetch(`${API_BASE_URL}/api/vision/${jobId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(visionEdited)
      })

      if (response.ok) {
        const now = new Date()
        setAutosaveStatus(`Autosaved at ${now.toLocaleTimeString()}`)
        lastAutosaveTime.current = Date.now()
        // Clear success message after 3 seconds
        setTimeout(() => setAutosaveStatus(''), 3000)
      } else {
        setAutosaveStatus('Autosave failed')
        setTimeout(() => setAutosaveStatus(''), 3000)
      }
    } catch (err) {
      console.error('Autosave failed:', err)
      setAutosaveStatus('Autosave failed')
      setTimeout(() => setAutosaveStatus(''), 3000)
    }
  }, [jobId, visionOriginal, dirty, flatBlocks, API_BASE_URL])

  // Setup autosave timer
  useEffect(() => {
    if (dirty && jobId && visionOriginal) {
      if (autosaveTimerRef.current) {
        clearInterval(autosaveTimerRef.current)
      }
      
      autosaveTimerRef.current = setInterval(() => {
        // Only autosave if 20 seconds have passed since last save
        if (Date.now() - lastAutosaveTime.current > 20000) {
          handleAutosave()
        }
      }, 5000) // Check every 5 seconds
      
      return () => {
        if (autosaveTimerRef.current) {
          clearInterval(autosaveTimerRef.current)
        }
      }
    } else {
      if (autosaveTimerRef.current) {
        clearInterval(autosaveTimerRef.current)
        autosaveTimerRef.current = null
      }
    }
  }, [dirty, jobId, visionOriginal, handleAutosave])

  // Step 1: Upload
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      if (file.type !== 'application/pdf') {
        setError('Please select a PDF file')
        return
      }
      if (file.size > 20 * 1024 * 1024) {
        setError('File size exceeds 20MB limit')
        return
      }
      setSelectedFile(file)
      setError(null)
    }
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedFile) {
      setError('Please select a file')
      return
    }

    setIsUploading(true)
    setError(null)
    setStatus('Uploading...')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('target_language', targetLanguage)

      const response = await fetch(`${API_BASE_URL}/api/translate`, {
        method: 'POST',
        body: formData,
        // IMPORTANT: Don't set Content-Type manually for multipart
      })

      if (response.ok) {
        const data = await response.json()
        setJobId(data.job_id)
        setStatus(`Uploaded successfully! Job ID: ${data.job_id}`)
        setStep('process')
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Upload failed')
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsUploading(false)
    }
  }

  // Step 2: Process
  const handleProcess = async () => {
    if (!jobId) return

    setIsProcessing(true)
    setError(null)
    setStatus('Processing...')

    try {
      const response = await fetch(`${API_BASE_URL}/api/process/${jobId}`, {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        if (data.status === 'done') {
          setStatus('Processing completed!')
          // Auto-load vision data
          await loadVisionData()
          setStep('edit')
        } else {
          setError(`Processing failed: ${data.error || 'Unknown error'}`)
        }
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Processing failed')
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsProcessing(false)
    }
  }

  const loadVisionData = async () => {
    if (!jobId) return

    try {
      const response = await fetch(`${API_BASE_URL}/api/vision/${jobId}`)
      if (response.ok) {
        const data: VisionData = await response.json()
        setVisionOriginal(data)
        setFlatBlocks(normalizeVisionData(data))
        setDirty(false)
        
        // Set markdown preview
        setMarkdownPreview(visionToMarkdown(data))
        
        // Set total pages
        const pageCount = data.pages.length
        setTotalPages(pageCount)
        if (pageCount > 0) {
          setCurrentPage(1)
        }
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to load vision data')
      }
    } catch (err) {
      setError((err as Error).message)
    }
  }

  // Step 3: Edit
  const handleTextChange = (blockId: string, newText: string) => {
    const newBlocks = flatBlocks.map(block => 
      block.id === blockId ? { ...block, text: newText } : block
    )
    setFlatBlocks(newBlocks)
    setDirty(true)
    scheduleHistoryAdd(newBlocks)
  }

  const handleResetBlock = (blockId: string) => {
    if (!visionOriginal) return
    
    const originalBlock = flatBlocks.find(b => b.id === blockId)
    if (!originalBlock) return
    
    // Find original text from visionOriginal
    const originalPage = visionOriginal.pages.find(p => p.page === originalBlock.page)
    if (originalPage && originalPage.blocks[originalBlock.blockIndex]) {
      const originalText = originalPage.blocks[originalBlock.blockIndex].text
      const newBlocks = flatBlocks.map(block => 
        block.id === blockId ? { ...block, text: originalText } : block
      )
      setFlatBlocks(newBlocks)
      setDirty(true)
      addToHistory(newBlocks)
    }
  }

  // Bulk operations
  const handleBulkReplace = () => {
    if (!bulkFind) return
    
    const newBlocks = flatBlocks.map(block => {
      if (filteredBlocks.some(fb => fb.id === block.id)) {
        return {
          ...block,
          text: block.text.replaceAll(bulkFind, bulkReplace)
        }
      }
      return block
    })
    setFlatBlocks(newBlocks)
    setDirty(true)
    addToHistory(newBlocks)
    setBulkFind('')
    setBulkReplace('')
  }

  const handleBulkTrim = () => {
    const newBlocks = flatBlocks.map(block => {
      if (filteredBlocks.some(fb => fb.id === block.id)) {
        return {
          ...block,
          text: block.text.trim()
        }
      }
      return block
    })
    setFlatBlocks(newBlocks)
    setDirty(true)
    addToHistory(newBlocks)
  }

  const handleBulkPrefix = () => {
    if (!bulkPrefix) return
    
    const newBlocks = flatBlocks.map(block => {
      if (filteredBlocks.some(fb => fb.id === block.id)) {
        return {
          ...block,
          text: bulkPrefix + block.text
        }
      }
      return block
    })
    setFlatBlocks(newBlocks)
    setDirty(true)
    addToHistory(newBlocks)
    setBulkPrefix('')
  }

  // Undo/Redo functionality
  const handleUndo = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1
      setHistoryIndex(newIndex)
      const prevState = history[newIndex]
      if (prevState) {
        setFlatBlocks(prevState)
        setDirty(true)
      }
    }
  }

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1
      setHistoryIndex(newIndex)
      const nextState = history[newIndex]
      if (nextState) {
        setFlatBlocks(nextState)
        setDirty(true)
      }
    }
  }

  // Highlight search matches in text
  const highlightText = (text: string, query: string) => {
    if (!query) return text
    const regex = new RegExp(`(${query})`, 'gi')
    const parts = text.split(regex)
    return parts.map((part, index) => 
      regex.test(part) ? <mark key={index}>{part}</mark> : part
    )
  }

  // Count total matches
  const totalMatches = useMemo(() => {
    if (!searchQuery) return 0
    return flatBlocks.filter(block => 
      block.text.toLowerCase().includes(searchQuery.toLowerCase())
    ).length
  }, [flatBlocks, searchQuery])

  // Jump to next match (circular navigation)
  const handleJumpToNext = () => {
    if (filteredBlocks.length === 0 || !searchQuery) return
    
    const matches = filteredBlocks.filter(block => 
      block.text.toLowerCase().includes(searchQuery.toLowerCase())
    )
    
    if (matches.length === 0) return
    
    // Find current position in matches
    const currentIndex = matches.findIndex(block => 
      selectedBlockId === block.id
    )
    
    // Get next match (circular)
    const nextIndex = (currentIndex + 1) % matches.length
    const nextBlock = matches[nextIndex]
    
    // Select and scroll to the block
    handleSelectBlock(nextBlock.id)
  }

  // Select block handler
  const handleSelectBlock = (blockId: string) => {
    setSelectedBlockId(blockId)
    
    // Scroll to block in virtualized list
    const blockIndex = filteredBlocks.findIndex(b => b.id === blockId)
    if (blockIndex >= 0 && listRef.current) {
      listRef.current.scrollToItem(blockIndex, 'center')
    }
    
    // For non-virtualized lists
    const element = document.getElementById(`block-${blockId}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  // Get original text for a block
  const getOriginalText = (blockId: string): string => {
    if (!visionOriginal) return ''
    const block = flatBlocks.find(b => b.id === blockId)
    if (!block) return ''
    
    const originalPage = visionOriginal.pages.find(p => p.page === block.page)
    return originalPage?.blocks[block.blockIndex]?.text || ''
  }

  // Diff view handlers
  const handleResetSelectedBlock = () => {
    if (!selectedBlockId) return
    handleResetBlock(selectedBlockId)
    setSelectedBlockId(null)
  }

  const handleCopyAfter = () => {
    if (!selectedBlockId) return
    const block = flatBlocks.find(b => b.id === selectedBlockId)
    if (block) {
      navigator.clipboard.writeText(block.text)
    }
  }

  const handleCopyBefore = () => {
    if (!selectedBlockId) return
    const originalText = getOriginalText(selectedBlockId)
    navigator.clipboard.writeText(originalText)
  }

  const handleSaveEdits = async () => {
    if (!jobId || !visionOriginal || !dirty) return

    setIsSaving(true)
    setError(null)
    setStatus('Saving edits...')

    try {
      // Reconstruct vision data format from flatBlocks
      const visionEdited = JSON.parse(JSON.stringify(visionOriginal))
      
      flatBlocks.forEach(block => {
        const page = visionEdited.pages.find((p: any) => p.page === block.page)
        if (page && page.blocks[block.blockIndex]) {
          page.blocks[block.blockIndex].text = block.text
        }
      })

      const response = await fetch(`${API_BASE_URL}/api/vision/${jobId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(visionEdited)
      })

      if (response.ok) {
        const data = await response.json()
        setStatus('Edits saved successfully!')
        setVisionOriginal(visionEdited)
        setDirty(false)
        setStep('generate')
        // Clear autosave status on manual save
        setAutosaveStatus('')
        lastAutosaveTime.current = Date.now()
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to save edits')
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsSaving(false)
    }
  }

  // Step 4: Generate
  const handleGenerate = async () => {
    if (!jobId) return

    setIsGenerating(true)
    setError(null)
    setStatus('Generating PDF...')

    try {
      // Build query parameters
      const params = new URLSearchParams({
        mode: generateMode
      })
      
      if (generateMode === 'overlay') {
        params.append('overlay_scope', overlayScope)
      }

      const response = await fetch(`${API_BASE_URL}/api/generate/${jobId}?${params.toString()}`, {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        setStatus(`PDF generated successfully! Mode: ${data.mode}${generateMode === 'overlay' ? `, Scope: ${overlayScope}` : ''}`)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to generate PDF')
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleOpenPdf = () => {
    if (!jobId) return
    window.open(`${API_BASE_URL}/api/result/${jobId}`, '_blank')
  }

  const handleDownloadPdf = async () => {
    if (!jobId) return

    try {
      const response = await fetch(`${API_BASE_URL}/api/result/${jobId}`)
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `translated_${jobId}.pdf`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } else {
        setError('Failed to download PDF')
      }
    } catch (err) {
      setError((err as Error).message)
    }
  }

  // Debug overlay functionality
  const handleBuildDebugOverlays = async () => {
    if (!jobId) return

    setIsBuildingDebug(true)
    setError(null)
    setStatus('Building debug overlays...')

    try {
      const response = await fetch(`${API_BASE_URL}/api/debug-render/${jobId}`, {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        setStatus(`Debug overlays built for ${data.debug_pages} pages`)
        setShowDebugOverlays(true)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to build debug overlays')
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsBuildingDebug(false)
    }
  }

  // Render a single block for virtualization
  const BlockRenderer = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const block = filteredBlocks[index]
    if (!block) return null

    const isSelected = selectedBlockId === block.id
    const originalText = getOriginalText(block.id)
    const hasChanged = block.text !== originalText

    return (
      <div 
        id={`block-${block.id}`}
        onClick={() => handleSelectBlock(block.id)}
        style={{
          ...style,
          cursor: 'pointer',
          backgroundColor: isSelected ? '#e3f2fd' : hasChanged ? '#fff8e1' : '#fafafa',
          borderLeft: isSelected ? '4px solid #2196f3' : hasChanged ? '4px solid #ff9800' : 'none',
          paddingLeft: isSelected || hasChanged ? '0.75rem' : '1rem'
        }}
      >
        <div style={{ 
          padding: '1rem 1rem 1rem 0',
          borderBottom: '1px solid #eee'
        }}>
          <div style={{ 
            fontSize: '0.8rem', 
            color: '#7f8c8d', 
            marginBottom: '0.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span>
              Page {block.page} • {block.type.toUpperCase()} • #{block.blockIndex}
              {hasChanged && <span style={{ color: '#ff9800', marginLeft: '0.5rem' }}>• CHANGED</span>}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleResetBlock(block.id)
              }}
              style={{
                background: '#e74c3c',
                color: 'white',
                border: 'none',
                padding: '0.25rem 0.5rem',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '0.7rem'
              }}
            >
              Reset
            </button>
          </div>
          <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.5rem' }}>
            {highlightText(block.text.substring(0, 100) + (block.text.length > 100 ? '...' : ''), searchQuery)}
          </div>
          <textarea
            value={block.text}
            onChange={(e) => handleTextChange(block.id, e.target.value)}
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              minHeight: '120px',
              padding: '0.5rem',
              border: '1px solid #ccc',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '0.9rem',
              resize: 'vertical'
            }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="card">
        <h1>📄 Document Translator</h1>
        <p>Vision-LLM powered document translation service</p>

        {/* Progress Steps */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          marginBottom: '2rem',
          maxWidth: '600px'
        }}>
          {(['upload', 'process', 'edit', 'generate'] as const).map((s, i) => (
            <div 
              key={s}
              style={{
                textAlign: 'center',
                padding: '0.5rem',
                backgroundColor: step === s ? '#3498db' : '#ecf0f1',
                color: step === s ? 'white' : '#7f8c8d',
                borderRadius: '4px',
                flex: 1,
                margin: '0 0.25rem'
              }}
            >
              <div style={{ fontWeight: 'bold' }}>{i + 1}</div>
              <div style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </div>
            </div>
          ))}
        </div>

        {/* Status/Error Messages */}
        {status && (
          <div className="status status-success" style={{ marginBottom: '1rem' }}>
            {status}
          </div>
        )}
        {error && (
          <div className="status status-error" style={{ marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        {/* Dirty state warning */}
        {dirty && step === 'edit' && (
          <div className="status status-warning" style={{ marginBottom: '1rem' }}>
            You have unsaved changes. Don&apos;t forget to save before leaving!
          </div>
        )}

        {/* Step 1: Upload */}
        {step === 'upload' && (
          <div>
            <h2>1. Upload Document</h2>
            <form onSubmit={handleUpload}>
              <div style={{ marginBottom: '1rem' }}>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept="application/pdf"
                  disabled={isUploading}
                />
                {selectedFile && (
                  <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
                    Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                  </p>
                )}
              </div>
              
              <div style={{ marginBottom: '1rem' }}>
                <label htmlFor="language">Target Language: </label>
                <select
                  id="language"
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  disabled={isUploading}
                >
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="de">German</option>
                  <option value="fr">French</option>
                  <option value="ru">Russian</option>
                </select>
              </div>
              
              <button 
                className="btn" 
                type="submit"
                disabled={isUploading || !selectedFile}
              >
                {isUploading ? 'Uploading...' : 'Upload'}
              </button>
            </form>
          </div>
        )}

        {/* Step 2: Process */}
        {step === 'process' && jobId && (
          <div>
            <h2>2. Process Document</h2>
            <p>Job ID: {jobId}</p>
            <button 
              className="btn" 
              onClick={handleProcess}
              disabled={isProcessing}
            >
              {isProcessing ? 'Processing...' : 'Process'}
            </button>
          </div>
        )}

        {/* Step 3: Edit */}
        {step === 'edit' && visionOriginal && (
          <div>
            <h2>3. Edit Text</h2>
            
            {/* Filters and Navigation */}
            <div style={{ 
              display: 'flex', 
              gap: '1rem', 
              marginBottom: '1rem', 
              flexWrap: 'wrap',
              padding: '1rem',
              backgroundColor: '#f8f9fa',
              borderRadius: '4px'
            }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.9rem' }}>
                  Page:
                </label>
                <select
                  value={selectedPage}
                  onChange={(e) => setSelectedPage(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                  style={{ padding: '0.5rem', minWidth: '100px' }}
                >
                  <option value="all">All</option>
                  {uniquePages.map(page => (
                    <option key={page} value={page}>Page {page}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.9rem' }}>
                  Type:
                </label>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  style={{ padding: '0.5rem', minWidth: '120px' }}
                >
                  <option value="all">All Types</option>
                  {uniqueTypes.map(type => (
                    <option key={type} value={type}>{type.toUpperCase()}</option>
                  ))}
                </select>
              </div>
              
              <div style={{ flex: 1, minWidth: '200px' }}>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.9rem' }}>
                  Search:
                </label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search text..."
                    style={{ 
                      flex: 1, 
                      padding: '0.5rem',
                      border: '1px solid #ccc',
                      borderRadius: '4px'
                    }}
                  />
                  {searchQuery && (
                    <button
                      onClick={handleJumpToNext}
                      style={{
                        padding: '0.5rem 1rem',
                        background: '#3498db',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      Next
                    </button>
                  )}
                </div>
                {searchQuery && (
                  <div style={{ fontSize: '0.8rem', color: '#666', marginTop: '0.25rem' }}>
                    Matches: {totalMatches}
                  </div>
                )}
              </div>
              
              <div style={{ alignSelf: 'flex-end', paddingTop: '1.5rem' }}>
                <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.5rem' }}>
                  Showing {filteredBlocks.length} / {flatBlocks.length} blocks
                </div>
                <div style={{ fontSize: '0.9rem', color: '#ff9800', fontWeight: 'bold' }}>
                  Changed: {changedBlocks.length}
                </div>
                <button
                  onClick={() => setShowChangesPanel(!showChangesPanel)}
                  style={{
                    marginTop: '0.5rem',
                    padding: '0.5rem 1rem',
                    background: showChangesPanel ? '#ff9800' : '#9e9e9e',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.8rem'
                  }}
                >
                  {showChangesPanel ? 'Hide Changes' : 'Show Changes'}
                </button>
              </div>
            </div>

            {/* Undo/Redo Controls */}
            <div style={{ 
              display: 'flex', 
              gap: '0.5rem', 
              marginBottom: '1rem',
              padding: '0.5rem',
              backgroundColor: '#e8f5e8',
              borderRadius: '4px'
            }}>
              <button
                onClick={handleUndo}
                disabled={historyIndex <= 0}
                style={{
                  padding: '0.5rem 1rem',
                  background: historyIndex <= 0 ? '#cccccc' : '#4caf50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: historyIndex <= 0 ? 'not-allowed' : 'pointer',
                  opacity: historyIndex <= 0 ? 0.6 : 1
                }}
              >
                ↶ Undo
              </button>
              <button
                onClick={handleRedo}
                disabled={historyIndex >= history.length - 1}
                style={{
                  padding: '0.5rem 1rem',
                  background: historyIndex >= history.length - 1 ? '#cccccc' : '#2196f3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: historyIndex >= history.length - 1 ? 'not-allowed' : 'pointer',
                  opacity: historyIndex >= history.length - 1 ? 0.6 : 1
                }}
              >
                ↷ Redo
              </button>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                fontSize: '0.8rem', 
                color: '#666',
                marginLeft: '1rem'
              }}>
                Step {historyIndex + 1} of {history.length}
              </div>
            </div>

            {/* Autosave Status */}
            {autosaveStatus && (
              <div className={`status ${autosaveStatus.includes('failed') ? 'status-error' : 'status-success'}`} 
                   style={{ marginBottom: '1rem' }}>
                {autosaveStatus}
              </div>
            )}

            {/* Bulk Operations Panel */}
            <div style={{ 
              marginBottom: '1rem', 
              padding: '1rem',
              backgroundColor: '#e8f4f8',
              borderRadius: '4px',
              border: '1px solid #bee5eb'
            }}>
              <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>Bulk Edit (Filtered Blocks)</h3>
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.9rem' }}>
                    Find:
                  </label>
                  <input
                    type="text"
                    value={bulkFind}
                    onChange={(e) => setBulkFind(e.target.value)}
                    placeholder="Text to find..."
                    style={{ padding: '0.5rem', minWidth: '150px' }}
                  />
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.9rem' }}>
                    Replace:
                  </label>
                  <input
                    type="text"
                    value={bulkReplace}
                    onChange={(e) => setBulkReplace(e.target.value)}
                    placeholder="Replacement text..."
                    style={{ padding: '0.5rem', minWidth: '150px' }}
                  />
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.9rem' }}>
                    Prefix:
                  </label>
                  <input
                    type="text"
                    value={bulkPrefix}
                    onChange={(e) => setBulkPrefix(e.target.value)}
                    placeholder="Prefix text..."
                    style={{ padding: '0.5rem', minWidth: '150px' }}
                  />
                </div>
                
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={handleBulkReplace}
                    disabled={!bulkFind}
                    style={{
                      padding: '0.5rem 1rem',
                      background: '#27ae60',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Replace
                  </button>
                  
                  <button
                    onClick={handleBulkTrim}
                    style={{
                      padding: '0.5rem 1rem',
                      background: '#f39c12',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Trim Spaces
                  </button>
                  
                  <button
                    onClick={handleBulkPrefix}
                    disabled={!bulkPrefix}
                    style={{
                      padding: '0.5rem 1rem',
                      background: '#9b59b6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Add Prefix
                  </button>
                </div>
              </div>
            </div>

            {/* Main Content Area with Changes Panel */}
            <div style={{ display: 'flex', gap: '1rem' }}>
              {/* Blocks List with Virtualization */}
              <div 
                ref={containerRef}
                style={{ 
                  border: '1px solid #ddd', 
                  borderRadius: '4px',
                  minHeight: '300px',
                  maxHeight: '600px',
                  overflow: 'hidden',
                  flex: 1
                }}
              >
              {filteredBlocks.length > 200 ? (
                // Virtualized list for performance
                <FixedSizeList
                  height={600}
                  itemCount={filteredBlocks.length}
                  itemSize={180}
                  width="100%"
                >
                  {BlockRenderer}
                </FixedSizeList>
              ) : (
                // Regular rendering for small lists
                <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
                  {filteredBlocks.map((block, index) => {
                    const isSelected = selectedBlockId === block.id
                    const originalText = getOriginalText(block.id)
                    const hasChanged = block.text !== originalText
                    
                    return (
                      <div 
                        key={block.id} 
                        id={`block-${block.id}`}
                        onClick={() => handleSelectBlock(block.id)}
                        style={{ 
                          padding: '1rem',
                          borderBottom: index < filteredBlocks.length - 1 ? '1px solid #eee' : 'none',
                          backgroundColor: isSelected ? '#e3f2fd' : hasChanged ? '#fff8e1' : '#fafafa',
                          borderLeft: isSelected ? '4px solid #2196f3' : hasChanged ? '4px solid #ff9800' : 'none',
                          paddingLeft: isSelected || hasChanged ? '0.75rem' : '1rem',
                          cursor: 'pointer'
                        }}
                      >
                        <div style={{ 
                          fontSize: '0.8rem', 
                          color: '#7f8c8d', 
                          marginBottom: '0.5rem',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}>
                          <span>
                            Page {block.page} • {block.type.toUpperCase()} • #{block.blockIndex}
                            {hasChanged && <span style={{ color: '#ff9800', marginLeft: '0.5rem' }}>• CHANGED</span>}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleResetBlock(block.id)
                            }}
                            style={{
                              background: '#e74c3c',
                              color: 'white',
                              border: 'none',
                              padding: '0.25rem 0.5rem',
                              borderRadius: '3px',
                              cursor: 'pointer',
                              fontSize: '0.7rem'
                            }}
                          >
                            Reset
                          </button>
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.5rem' }}>
                          {highlightText(block.text.substring(0, 100) + (block.text.length > 100 ? '...' : ''), searchQuery)}
                        </div>
                        <textarea
                          value={block.text}
                          onChange={(e) => handleTextChange(block.id, e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            width: '100%',
                            minHeight: '120px',
                            padding: '0.5rem',
                            border: '1px solid #ccc',
                            borderRadius: '4px',
                            fontFamily: 'monospace',
                            fontSize: '0.9rem',
                            resize: 'vertical'
                          }}
                        />
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Changes Panel and Markdown Preview */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '400px' }}>
              {showChangesPanel && (
                <div style={{
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  maxHeight: '300px',
                  overflowY: 'auto',
                  backgroundColor: '#fafafa'
                }}>
                  <div style={{ 
                    padding: '1rem', 
                    borderBottom: '1px solid #eee',
                    backgroundColor: '#ff9800',
                    color: 'white',
                    fontWeight: 'bold'
                  }}>
                    Changed Blocks ({changedBlocks.length})
                  </div>
                  <div>
                    {changedBlocks.map(block => {
                      const originalText = getOriginalText(block.id)
                      return (
                        <div
                          key={block.id}
                          onClick={() => handleSelectBlock(block.id)}
                          style={{
                            padding: '0.75rem 1rem',
                            borderBottom: '1px solid #eee',
                            cursor: 'pointer',
                            backgroundColor: selectedBlockId === block.id ? '#e3f2fd' : 'transparent'
                          }}
                        >
                          <div style={{ 
                            fontSize: '0.8rem', 
                            color: '#7f8c8d', 
                            marginBottom: '0.25rem'
                          }}>
                            Page {block.page} • {block.type.toUpperCase()} • #{block.blockIndex}
                          </div>
                          <div style={{ 
                            fontSize: '0.85rem',
                            color: '#333',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }}>
                            {block.text.substring(0, 60) + (block.text.length > 60 ? '...' : '')}
                          </div>
                        </div>
                      )
                    })}
                    {changedBlocks.length === 0 && (
                      <div style={{ padding: '1rem', textAlign: 'center', color: '#7f8c8d' }}>
                        No changes yet
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Markdown Preview Section */}
              <div style={{
                border: '1px solid #ddd',
                borderRadius: '4px',
                flex: 1,
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
                  📄 Markdown Preview with Image Translation
                </div>
                <div style={{ flex: 1, overflow: 'auto', padding: '1rem' }}>
                  {markdownPreview ? (
                    <MarkdownPreview
                      markdown={markdownPreview}
                      jobId={jobId}
                      onTranslateImage={(imageName) => handleTranslateImage(imageName, 'russian')}
                      apiBaseUrl={API_BASE_URL}
                      translatedImages={translatedImages}
                      translatingImages={translatingImages}
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
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10 9 9 9 8 9"></polyline>
                      </svg>
                      <p style={{ margin: 0 }}>
                        Vision data will appear here as Markdown
                      </p>
                      <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.9rem', color: '#888' }}>
                        Images will have translate buttons
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Diff View Panel */}
          {selectedBlockId && (
            <div style={{
              marginTop: '1rem',
              padding: '1rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
              backgroundColor: '#f8f9fa'
            }}>
              <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>
                Diff View: {selectedBlockId}
              </h3>
              <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <h4 style={{ color: '#e74c3c', marginBottom: '0.5rem' }}>Before:</h4>
                  <div style={{
                    padding: '0.75rem',
                    border: '1px solid #e74c3c',
                    borderRadius: '4px',
                    backgroundColor: '#fdf6f6',
                    minHeight: '100px',
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'monospace'
                  }}>
                    {getOriginalText(selectedBlockId)}
                  </div>
                </div>
                <div style={{ flex: 1 }}>
                  <h4 style={{ color: '#27ae60', marginBottom: '0.5rem' }}>After:</h4>
                  <div style={{
                    padding: '0.75rem',
                    border: '1px solid #27ae60',
                    borderRadius: '4px',
                    backgroundColor: '#f6fdf6',
                    minHeight: '100px',
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'monospace'
                  }}>
                    {flatBlocks.find(b => b.id === selectedBlockId)?.text || ''}
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={handleResetSelectedBlock}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#e74c3c',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Reset this block
                </button>
                <button
                  onClick={handleCopyAfter}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#3498db',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Copy after
                </button>
                <button
                  onClick={handleCopyBefore}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#9b59b6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Copy before
                </button>
                <button
                  onClick={() => setSelectedBlockId(null)}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#7f8c8d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Close
                </button>
              </div>
            </div>
          )}

          <button 
            className="btn" 
            onClick={handleSaveEdits}
            disabled={isSaving || !dirty}
            style={{ marginTop: '1rem' }}
          >
            {isSaving ? 'Saving...' : dirty ? 'Save Edits' : 'No Changes to Save'}
          </button>
        </div>
      )}

      {/* Step 3.5: Page Preview */}
      {step === 'edit' && visionOriginal && totalPages > 0 && (
        <div style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #ddd', borderRadius: '4px' }}>
          <h3>🔍 Page Preview</h3>
          
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.9rem' }}>
                Page:
              </label>
              <select
                value={currentPage}
                onChange={(e) => setCurrentPage(Number(e.target.value))}
                style={{ padding: '0.5rem', minWidth: '80px' }}
              >
                {Array.from({ length: totalPages }, (_, i) => i + 1).map(pageNum => (
                  <option key={pageNum} value={pageNum}>Page {pageNum}</option>
                ))}
              </select>
            </div>
            
            <div>
              <button
                onClick={handleBuildDebugOverlays}
                disabled={isBuildingDebug}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#9c27b0',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.9rem'
                }}
              >
                {isBuildingDebug ? 'Building...' : 'Build Debug Overlays'}
              </button>
            </div>
            
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
                <input
                  type="checkbox"
                  checked={showDebugOverlays}
                  onChange={(e) => setShowDebugOverlays(e.target.checked)}
                  disabled={!showDebugOverlays && !isBuildingDebug}
                />
                Show Debug Overlays
              </label>
            </div>
          </div>
          
          <div style={{ position: 'relative', maxWidth: '100%', overflow: 'auto' }}>
            <img
              src={`${API_BASE_URL}/api/${showDebugOverlays ? 'debug-page-image' : 'page-image'}/${jobId}/${currentPage}`}
              alt={`Page ${currentPage}`}
              style={{ 
                maxWidth: '100%', 
                height: 'auto',
                display: 'block',
                border: '1px solid #ccc'
              }}
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300"><rect width="400" height="300" fill="%23f0f0f0"/><text x="200" y="150" font-family="Arial" font-size="16" text-anchor="middle" fill="%23666">Image not available</text></svg>';
              }}
            />
          </div>
        </div>
      )}

        {/* Step 4: Generate */}
        {step === 'generate' && jobId && (
          <div>
            <h2>4. Generate PDF</h2>
            <p>Job ID: {jobId}</p>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                Generation Mode:
              </label>
              <select
                value={generateMode}
                onChange={(e) => setGenerateMode(e.target.value as 'html' | 'overlay')}
                style={{ 
                  padding: '0.5rem', 
                  minWidth: '200px',
                  border: '1px solid #ccc',
                  borderRadius: '4px'
                }}
              >
                <option value="html">HTML (reference image + text below)</option>
                <option value="overlay">Overlay (attempts to replace text on image using bbox)</option>
              </select>
              <div style={{ 
                fontSize: '0.85rem', 
                color: '#666', 
                marginTop: '0.5rem',
                maxWidth: '500px'
              }}>
                {generateMode === 'html' 
                  ? 'Reference image + text below - clean separation' 
                  : 'Attempts to replace text on image using bounding boxes - experimental'}
              </div>
            </div>
            
            {generateMode === 'overlay' && (
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                  Overlay Scope:
                </label>
                <select
                  value={overlayScope}
                  onChange={(e) => setOverlayScope(e.target.value as 'headings' | 'safe' | 'all')}
                  style={{ 
                    padding: '0.5rem', 
                    minWidth: '200px',
                    border: '1px solid #ccc',
                    borderRadius: '4px'
                  }}
                >
                  <option value="headings">Headings only (recommended)</option>
                  <option value="safe">Safe (headings + small labels)</option>
                  <option value="all">All (experimental)</option>
                </select>
                <div style={{ 
                  fontSize: '0.85rem', 
                  color: '#666', 
                  marginTop: '0.5rem',
                  maxWidth: '500px'
                }}>
                  {overlayScope === 'headings' 
                    ? 'Only replaces headings and titles - safest option' 
                    : overlayScope === 'safe' 
                      ? 'Replaces headings, captions, and small labels' 
                      : 'Replaces all detected text blocks (may cover images)'}
                </div>
              </div>
            )}
            
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
              <button 
                className="btn" 
                onClick={handleGenerate}
                disabled={isGenerating}
              >
                {isGenerating ? 'Generating...' : 'Generate PDF'}
              </button>
              
              <button 
                className="btn btn-secondary" 
                onClick={handleOpenPdf}
              >
                Open PDF
              </button>
              
              <button 
                className="btn btn-secondary" 
                onClick={handleDownloadPdf}
              >
                Download PDF
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}