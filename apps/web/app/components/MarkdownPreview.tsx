'use client'

import React, { useMemo, useCallback, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './MarkdownPreview.module.css'

interface ImageTranslationState {
  translating: boolean
  error: string | null
  translatedUrl?: string
}

interface MarkdownPreviewProps {
  markdown: string
  jobId: string | null
  onTranslateImage: (imageName: string) => Promise<void>
  apiBaseUrl: string
  translatedImages?: Record<string, string>
  translatingImages?: Set<string>
}

const MarkdownPreview: React.FC<MarkdownPreviewProps> = ({ 
  markdown, 
  jobId, 
  onTranslateImage,
  apiBaseUrl,
  translatedImages = {},
  translatingImages = new Set()
}) => {
  const [imageStates, setImageStates] = useState<Record<string, ImageTranslationState>>({})
  
  // Component initialization logging
  React.useEffect(() => {
    console.log('🔷 [MARKDOWN PREVIEW INIT]', {
      jobId,
      markdownLength: markdown?.length || 0,
      apiBaseUrl
    })
  }, [jobId, markdown, apiBaseUrl])

  // Memoize the markdown parsing to avoid re-parsing on every render
  const memoizedMarkdown = useMemo(() => {
    if (!markdown) return ''
    return markdown
  }, [markdown])

  // Handle image translation with proper state management
  const handleTranslateClick = useCallback(async (imageName: string) => {
    if (!jobId) return

    // Set loading state
    setImageStates(prev => ({
      ...prev,
      [imageName]: { translating: true, error: null }
    }))

    try {
      await onTranslateImage(imageName)
      // Success - clear error, keep translating false
      setImageStates(prev => ({
        ...prev,
        [imageName]: { translating: false, error: null }
      }))
    } catch (error) {
      // Error - show error message
      setImageStates(prev => ({
        ...prev,
        [imageName]: { 
          translating: false, 
          error: error instanceof Error ? error.message : 'Translation failed' 
        }
      }))
    }
  }, [jobId, onTranslateImage])

  // Custom renderers for react-markdown
  const components = useMemo(() => ({
    // Image renderer with translate button
    img: ({ node, ...props }: any) => {
      const { src, alt } = props
      const imageName = src.split('/').pop()
      
      // ВАЖНО: Полный URL через API!
      const imageUrl = `${apiBaseUrl}/api/md-asset/${jobId}/${imageName}`
      const translatedImageUrl = translatedImages[imageName]
      const finalUrl = translatedImageUrl || imageUrl
      
      console.log('🔵 [IMAGE RENDER]', { imageName, hasTranslation: !!translatedImageUrl, finalUrl })
      
      return (
        <div style={{ marginBottom: '20px', display: 'block' }}>
          <img src={finalUrl} alt={alt || 'Image'} style={{ maxWidth: '100%', height: 'auto', display: 'block' }} />
          
          {!translatedImageUrl && (
            <button 
              onClick={() => handleTranslateClick(imageName)}
              disabled={translatingImages.has(imageName)}
              style={{ 
                marginTop: '10px', 
                padding: '8px 16px', 
                backgroundColor: translatingImages.has(imageName) ? '#ccc' : '#007bff', 
                color: 'white', 
                border: 'none', 
                cursor: 'pointer', 
                borderRadius: '4px',
                display: 'block'
              }}
            >
              {translatingImages.has(imageName) ? '⏳ Translating...' : '🌐 Translate to Russian'}
            </button>
          )}
        </div>
      )
    },

    // Table renderer with proper styling (GFM tables via remark-gfm)
    table: ({ node, ...props }: any) => (
      <div className={styles['table-wrapper']}>
        <table {...props} className={styles['markdown-table']} />
      </div>
    ),

    // Code renderer
    code: ({ node, inline, ...props }: any) => (
      <code {...props} className={inline ? 'inline-code' : 'block-code'} />
    ),

    // Blockquote renderer
    blockquote: ({ node, ...props }: any) => (
      <blockquote {...props} className="markdown-blockquote" />
    )
  }), [jobId, handleTranslateClick, translatedImages, translatingImages])

  if (!memoizedMarkdown) {
    return (
      <div className={`${styles['markdown-preview']} ${styles.empty}`}>
        <div className={styles['empty-state']}>
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
          <p>
            {jobId 
              ? 'Start editing to see the live preview' 
              : 'Upload a PDF to see the Markdown preview'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={styles['markdown-preview']}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
        skipHtml={false}
      >
        {memoizedMarkdown}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownPreview