'use client'

import { useState, useRef, useEffect } from 'react'

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

interface ImageEditorProps {
  imageUrl: string
  jobId: string
  imageName: string
  initialBoxes: Box[]  // Image coordinates
  onSave: (boxes: Box[]) => void
  onReset: () => void
  onPreviewGenerated?: (previewUrl: string) => void
}

export default function ImageEditor({ 
  imageUrl, 
  jobId,
  imageName,
  initialBoxes, 
  onSave, 
  onReset,
  onPreviewGenerated
}: ImageEditorProps) {
  const [boxes, setBoxes] = useState<Box[]>(initialBoxes)
  const [selectedBoxIndex, setSelectedBoxIndex] = useState<number | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [isResizing, setIsResizing] = useState(false)
  const [resizeHandle, setResizeHandle] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const [showOverlays, setShowOverlays] = useState(true)
  const [history, setHistory] = useState<Box[][]>([initialBoxes])
  const [historyIndex, setHistoryIndex] = useState(0)
  
  const containerRef = useRef<HTMLDivElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)

  // Initialize with initial boxes
  useEffect(() => {
    setBoxes(initialBoxes)
    setHistory([initialBoxes])
    setHistoryIndex(0)
    // Clear preview when boxes change
    if (onPreviewGenerated) {
      onPreviewGenerated('');
    }
  }, [initialBoxes, onPreviewGenerated])

  // Undo/Redo functionality
  const handleUndo = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1
      setHistoryIndex(newIndex)
      setBoxes(history[newIndex])
    }
  }

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1
      setHistoryIndex(newIndex)
      setBoxes(history[newIndex])
    }
  }

  // Save to history
  const saveToHistory = (newBoxes: Box[]) => {
    const newHistory = [...history.slice(0, historyIndex + 1), newBoxes]
    setHistory(newHistory)
    setHistoryIndex(newHistory.length - 1)
  }

  // Handle mouse down on box
  const handleBoxMouseDown = (e: React.MouseEvent, index: number) => {
    e.stopPropagation()
    setSelectedBoxIndex(index)
    setIsDragging(true)
    
    if (imageRef.current) {
      const imgRect = imageRef.current.getBoundingClientRect()
      const box = boxes[index]
      
      // Convert screen coordinates to natural image coordinates
      const naturalX = (e.clientX - imgRect.left) * (imageRef.current.naturalWidth / imgRect.width)
      const naturalY = (e.clientY - imgRect.top) * (imageRef.current.naturalHeight / imgRect.height)
      
      setDragOffset({
        x: naturalX - box.x,
        y: naturalY - box.y
      })
    }
  }

  // Handle mouse down on resize handle
  const handleResizeMouseDown = (e: React.MouseEvent, index: number, handle: string) => {
    e.stopPropagation()
    setSelectedBoxIndex(index)
    setIsResizing(true)
    setResizeHandle(handle)
  }

  // Handle mouse move
  const handleMouseMove = (e: MouseEvent) => {
    if (!imageRef.current) return
    
    const imgRect = imageRef.current.getBoundingClientRect()
    
    if (isDragging && selectedBoxIndex !== null) {
      // Convert screen coordinates to natural image coordinates
      const naturalX = (e.clientX - imgRect.left) * (imageRef.current.naturalWidth / imgRect.width)
      const naturalY = (e.clientY - imgRect.top) * (imageRef.current.naturalHeight / imgRect.height)
      
      setBoxes(prev => {
        const newBoxes = [...prev]
        const box = newBoxes[selectedBoxIndex]
        // Grid snapping (snap to 5px grid)
        newBoxes[selectedBoxIndex] = {
          ...box,
          x: Math.max(0, Math.round((naturalX - dragOffset.x) / 5) * 5),
          y: Math.max(0, Math.round((naturalY - dragOffset.y) / 5) * 5)
        }
        return newBoxes
      })
    }
    
    if (isResizing && selectedBoxIndex !== null && resizeHandle) {
      const box = boxes[selectedBoxIndex]
      // Convert screen coordinates to natural image coordinates
      const mouseX = (e.clientX - imgRect.left) * (imageRef.current.naturalWidth / imgRect.width)
      const mouseY = (e.clientY - imgRect.top) * (imageRef.current.naturalHeight / imgRect.height)
      
      setBoxes(prev => {
        const newBoxes = [...prev]
        let newWidth = box.w
        let newHeight = box.h
        let newX = box.x
        let newY = box.y
        
        // Handle different resize handles
        switch (resizeHandle) {
          case 'se': // bottom-right
            newWidth = Math.max(20, mouseX - box.x)
            newHeight = Math.max(20, mouseY - box.y)
            break
          case 'sw': // bottom-left
            newWidth = Math.max(20, box.x + box.w - mouseX)
            newHeight = Math.max(20, mouseY - box.y)
            newX = mouseX
            break
          case 'ne': // top-right
            newWidth = Math.max(20, mouseX - box.x)
            newHeight = Math.max(20, box.y + box.h - mouseY)
            newY = mouseY
            break
          case 'nw': // top-left
            newWidth = Math.max(20, box.x + box.w - mouseX)
            newHeight = Math.max(20, box.y + box.h - mouseY)
            newX = mouseX
            newY = mouseY
            break
        }
        
        // Grid snapping
        newBoxes[selectedBoxIndex] = {
          ...box,
          x: Math.max(0, Math.round(newX / 5) * 5),
          y: Math.max(0, Math.round(newY / 5) * 5),
          w: Math.max(20, Math.round(newWidth / 5) * 5),
          h: Math.max(20, Math.round(newHeight / 5) * 5)
        }
        return newBoxes
      })
    }
  }

  // Handle mouse up
  const handleMouseUp = () => {
    if (isDragging || isResizing) {
      setIsDragging(false)
      setIsResizing(false)
      setResizeHandle(null)
      saveToHistory(boxes)
    }
  }

  // Handle text change
  const handleTextChange = (index: number, text: string) => {
    setBoxes(prev => {
      const newBoxes = [...prev]
      newBoxes[index] = { ...newBoxes[index], text }
      return newBoxes
    })
  }

  // Handle zoom - moved to useEffect with proper event listener
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      setZoom(prev => Math.min(3, Math.max(0.5, prev + delta)));
    };

    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel as any);
  }, []);

  // Reset to original positions
  const handleResetPositions = () => {
    setBoxes(initialBoxes)
    saveToHistory(initialBoxes)
    onReset()
  }

  // Save changes
  const handleSave = async () => {
    onSave(boxes)
    
    // Generate preview after successful save
    if (jobId && imageName && onPreviewGenerated) {
      try {
        // Small delay to ensure save is processed
        setTimeout(() => {
          const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
          const previewUrl = `${API_BASE_URL}/api/preview-overlay/${jobId}/${imageName}`;
          onPreviewGenerated(previewUrl);
        }, 300);
      } catch (err) {
        console.error('Failed to generate preview:', err);
      }
    }
  }

  // Add event listeners
  useEffect(() => {
    if (isDragging || isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDragging, isResizing, selectedBoxIndex, dragOffset, resizeHandle])

  return (
    <div className="image-editor">
      {/* Toolbar */}
      <div className="editor-toolbar">
        <div className="toolbar-group">
          <button 
            onClick={handleUndo}
            disabled={historyIndex <= 0}
            className="toolbar-btn"
            title="Undo (Ctrl+Z)"
          >
            ↶
          </button>
          <button 
            onClick={handleRedo}
            disabled={historyIndex >= history.length - 1}
            className="toolbar-btn"
            title="Redo (Ctrl+Y)"
          >
            ↷
          </button>
        </div>
        
        <div className="toolbar-group">
          <button 
            onClick={() => setShowOverlays(!showOverlays)}
            className={`toolbar-btn ${showOverlays ? 'active' : ''}`}
          >
            {showOverlays ? 'Hide Overlays' : 'Show Overlays'}
          </button>
          <button 
            onClick={handleResetPositions}
            className="toolbar-btn"
          >
            Reset Positions
          </button>
        </div>
        
        <div className="toolbar-group">
          <span className="zoom-display">Zoom: {Math.round(zoom * 100)}%</span>
          <input
            type="range"
            min="0.5"
            max="3"
            step="0.1"
            value={zoom}
            onChange={(e) => setZoom(parseFloat(e.target.value))}
            className="zoom-slider"
          />
        </div>
        
        <div className="toolbar-group">
          <button 
            onClick={handleSave}
            className="toolbar-btn save-btn"
          >
            Save Changes
          </button>
        </div>
      </div>

      {/* Editor Canvas */}
      <div 
        ref={containerRef}
        className="editor-canvas"
        style={{ 
          cursor: isDragging ? 'grabbing' : isResizing ? 'nwse-resize' : 'default',
          overflow: 'auto',
          overscrollBehavior: 'contain',
          touchAction: 'none'
        }}
      >
        <div 
          style={{ 
            position: 'relative',
            transform: `scale(${zoom})`,
            transformOrigin: '0 0',
            width: 'fit-content'
          }}
        >
          <img
            ref={imageRef}
            src={imageUrl}
            alt="Editable image"
            style={{
              display: 'block',
              maxWidth: '100%',
              userSelect: 'none'
            }}
            draggable={false}
          />
          
          {showOverlays && boxes.map((box, index) => {
            // Calculate scale factors for rendering
            const rect = imageRef.current?.getBoundingClientRect()
            const scaleX = rect ? rect.width / (imageRef.current!.naturalWidth || 1) : 1
            const scaleY = rect ? rect.height / (imageRef.current!.naturalHeight || 1) : 1
            
            return (
              <div
                key={`${box.id}`}
                className={`text-overlay ${selectedBoxIndex === index ? 'selected' : ''}`}
                style={{
                  left: `${box.x * scaleX}px`,
                  top: `${box.y * scaleY}px`,
                  width: `${box.w * scaleX}px`,
                  height: `${box.h * scaleY}px`
                }}
                onMouseDown={(e) => handleBoxMouseDown(e, index)}
              >
                {/* Text input */}
                <input
                  type="text"
                  value={box.text}
                  onChange={(e) => handleTextChange(index, e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="overlay-input"
                  style={{
                    fontSize: `${box.fontSize || Math.max(8, Math.min(box.h * 0.8, 24))}px`,
                    color: box.color || '#000000'
                  }}
                />
                
                {/* Resize handles */}
                {selectedBoxIndex === index && (
                  <>
                    <div 
                      className="resize-handle nw"
                      onMouseDown={(e) => handleResizeMouseDown(e, index, 'nw')}
                    />
                    <div 
                      className="resize-handle ne"
                      onMouseDown={(e) => handleResizeMouseDown(e, index, 'ne')}
                    />
                    <div 
                      className="resize-handle sw"
                      onMouseDown={(e) => handleResizeMouseDown(e, index, 'sw')}
                    />
                    <div 
                      className="resize-handle se"
                      onMouseDown={(e) => handleResizeMouseDown(e, index, 'se')}
                    />
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <style jsx>{`
        .image-editor {
          display: flex;
          flex-direction: column;
          height: 100%;
          border: 1px solid #ddd;
          border-radius: 4px;
          overflow: hidden;
        }
        
        .editor-toolbar {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 0.75rem 1rem;
          background: #f8f9fa;
          border-bottom: 1px solid #ddd;
          flex-wrap: wrap;
        }
        
        .toolbar-group {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .toolbar-btn {
          padding: 0.375rem 0.75rem;
          background: white;
          border: 1px solid #ccc;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.875rem;
          transition: all 0.2s;
        }
        
        .toolbar-btn:hover:not(:disabled) {
          background: #e9ecef;
        }
        
        .toolbar-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .toolbar-btn.active {
          background: #007bff;
          color: white;
          border-color: #007bff;
        }
        
        .save-btn {
          background: #28a745;
          color: white;
          border-color: #28a745;
        }
        
        .save-btn:hover:not(:disabled) {
          background: #218838;
        }
        
        .zoom-display {
          font-size: 0.875rem;
          color: #666;
          min-width: 70px;
        }
        
        .zoom-slider {
          width: 100px;
        }
        
        .editor-canvas {
          flex: 1;
          position: relative;
          background: #f0f0f0;
          overflow: auto;
        }
        
        .text-overlay {
          position: absolute;
          border: 2px dashed #007bff;
          background: rgba(255, 255, 0, 0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: move;
          user-select: none;
        }
        
        .text-overlay.selected {
          border-color: #0056b3;
          background: rgba(255, 255, 0, 0.5);
          box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.3);
        }
        
        .overlay-input {
          width: 100%;
          height: 100%;
          border: none;
          background: transparent;
          text-align: center;
          outline: none;
          padding: 2px;
        }
        
        .resize-handle {
          position: absolute;
          width: 8px;
          height: 8px;
          background: #007bff;
          border: 1px solid white;
          border-radius: 50%;
          cursor: nwse-resize;
        }
        
        .resize-handle.nw {
          top: -4px;
          left: -4px;
          cursor: nw-resize;
        }
        
        .resize-handle.ne {
          top: -4px;
          right: -4px;
          cursor: ne-resize;
        }
        
        .resize-handle.sw {
          bottom: -4px;
          left: -4px;
          cursor: sw-resize;
        }
        
        .resize-handle.se {
          bottom: -4px;
          right: -4px;
          cursor: se-resize;
        }
      `}</style>
    </div>
  )
}