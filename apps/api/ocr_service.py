"""OCR service for extracting text from images with bounding boxes."""

import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Try to import PaddleOCR first, fallback to Tesseract
def _detect_ocr_engine():
    """Detect and test available OCR engines."""
    # Try PaddleOCR first
    try:
        from paddleocr import PaddleOCR
        # Test if PaddleOCR can be initialized
        try:
            test_ocr = PaddleOCR(lang='en', use_angle_cls=True, show_log=False)
            del test_ocr  # Clean up
            logger.info("Using PaddleOCR engine")
            return "paddleocr", PaddleOCR
        except Exception as e:
            logger.warning(f"PaddleOCR available but failed to initialize: {e}")
    except ImportError:
        pass
    
    # Fallback to Tesseract
    try:
        import pytesseract
        from PIL import Image
        # Test if Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            logger.info("Using Tesseract engine")
            return "tesseract", (pytesseract, Image)
        except Exception as e:
            logger.warning(f"Tesseract available but failed to initialize: {e}")
    except ImportError:
        pass
    
    logger.warning("No OCR engine available. Please install paddleocr or pytesseract")
    return None, None

OCR_ENGINE, OCR_IMPORTS = _detect_ocr_engine()


class OCRService:
    """Service for performing OCR on images."""
    
    def __init__(self):
        self.ocr_engine, self.ocr_imports = OCR_ENGINE, OCR_IMPORTS
        self.ocr = None
        self._initialize_ocr()
    
    def _initialize_ocr(self):
        """Initialize the OCR engine."""
        if self.ocr_engine == "paddleocr":
            try:
                PaddleOCR = self.ocr_imports
                # Initialize PaddleOCR with English and Russian support
                self.ocr = PaddleOCR(
                    lang='en',
                    use_angle_cls=True,
                    show_log=False
                )
                logger.info("PaddleOCR initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR: {e}")
                self.ocr_engine = None
                self.ocr = None
        elif self.ocr_engine == "tesseract":
            try:
                pytesseract, _ = self.ocr_imports
                # Test Tesseract installation
                pytesseract.get_tesseract_version()
                logger.info("Tesseract initialized successfully")
            except Exception as e:
                logger.error(f"Tesseract not available: {e}")
                self.ocr_engine = None
    
    def extract_text_with_bboxes(self, image_path: Path) -> List[Dict[str, Any]]:
        """
        Extract text and bounding boxes from an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of dictionaries with 'text', 'bbox', and 'confidence' keys
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        if self.ocr_engine is None:
            raise RuntimeError("No OCR engine available. Install paddleocr or pytesseract.")
        
        if self.ocr_engine == "paddleocr":
            return self._extract_with_paddleocr(image_path)
        elif self.ocr_engine == "tesseract":
            return self._extract_with_tesseract(image_path)
        else:
            raise RuntimeError("Unsupported OCR engine")
    
    def _extract_with_paddleocr(self, image_path: Path) -> List[Dict[str, Any]]:
        """Extract text using PaddleOCR."""
        if self.ocr is None:
            raise RuntimeError("PaddleOCR not initialized")
            
        try:
            # Run OCR
            result = self.ocr.ocr(str(image_path), cls=True)
            
            boxes = []
            if result and result[0]:
                for line in result[0]:
                    if line is None or len(line) < 2:
                        continue
                    
                    bbox_points, (text, confidence) = line
                    
                    # Convert bbox points to [x1, y1, x2, y2] format
                    if len(bbox_points) >= 4:
                        x_coords = [point[0] for point in bbox_points]
                        y_coords = [point[1] for point in bbox_points]
                        x1, x2 = min(x_coords), max(x_coords)
                        y1, y2 = min(y_coords), max(y_coords)
                        
                        boxes.append({
                            "text": text,
                            "bbox": [int(x1), int(y1), int(x2), int(y2)],
                            "confidence": float(confidence)
                        })
            
            logger.info(f"PaddleOCR extracted {len(boxes)} text boxes from {image_path.name}")
            return boxes
            
        except Exception as e:
            logger.error(f"PaddleOCR failed on {image_path}: {e}")
            raise RuntimeError(f"OCR failed: {e}")
    
    def _extract_with_tesseract(self, image_path: Path) -> List[Dict[str, Any]]:
        """Extract text using Tesseract."""
        if self.ocr_engine != "tesseract" or self.ocr_imports is None:
            raise RuntimeError("Tesseract not available")
            
        try:
            _, Image = self.ocr_imports
            # Open image
            image = Image.open(image_path)
            
            pytesseract, _ = self.ocr_imports
            # Run OCR with bounding box data
            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                lang='eng+rus'  # English and Russian
            )
            
            boxes = []
            n_boxes = len(data['level'])
            
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if not text:  # Skip empty text
                    continue
                
                # Get bounding box coordinates
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                
                # Confidence score (0-100)
                conf = int(data['conf'][i])
                if conf < 0:  # Skip unreliable detections
                    continue
                
                boxes.append({
                    "text": text,
                    "bbox": [x, y, x + w, y + h],
                    "confidence": conf / 100.0  # Convert to 0-1 scale
                })
            
            logger.info(f"Tesseract extracted {len(boxes)} text boxes from {image_path.name}")
            return boxes
            
        except Exception as e:
            logger.error(f"Tesseract failed on {image_path}: {e}")
            raise RuntimeError(f"OCR failed: {e}")


# Global OCR service instance
ocr_service = OCRService()


def perform_ocr_on_image(image_path: Path) -> List[Dict[str, Any]]:
    """
    Perform OCR on an image and return text with bounding boxes.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        List of dictionaries with 'text', 'bbox', and 'confidence' keys
    """
    return ocr_service.extract_text_with_bboxes(image_path)