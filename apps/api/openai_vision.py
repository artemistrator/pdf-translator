"""
OpenAI Vision API integration for document analysis with structured outputs
"""
import os
import base64
import json
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
import logging
from PIL import Image
import io


logger = logging.getLogger(__name__)


def encode_png_to_data_url(path: Path) -> str:
    """
    Encode PNG image to data URL format
    
    Args:
        path: Path to PNG file
        
    Returns:
        Data URL string in format: data:image/png;base64,...
    """
    with open(path, "rb") as f:
        image_bytes = f.read()
    
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def encode_image_to_base64(image_path: Path) -> str:
    """
    Encode image file to base64 string
    
    Args:
        image_path: Path to image file
        
    Returns:
        Base64 encoded string
    """
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    return base64.b64encode(image_bytes).decode("utf-8")


def decode_base64_to_image(base64_string: str) -> Image.Image:
    """
    Decode base64 string to PIL Image
    
    Args:
        base64_string: Base64 encoded image string
        
    Returns:
        PIL Image object
    """
    image_bytes = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(image_bytes))


def translate_image_with_openai_vision(
    image_path: Path,
    target_language: str,
    job_dir: Optional[Path] = None
) -> str:
    """
    Translate text in image using OpenAI Vision API with comprehensive logging
    
    Args:
        image_path: Path to the image file
        target_language: Target language for translation ("russian" or "english")
        job_dir: Directory to save debug artifacts (optional)
        
    Returns:
        Base64 encoded translated image
        
    Raises:
        RuntimeError: If OPENAI_API_KEY is not set
        ValueError: If image processing fails
    """
    logger.info(f"🟦 [VISION-TRANSLATE START] image={image_path.name}, language={target_language}")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ [API KEY MISSING] OPENAI_API_KEY is not set")
        raise RuntimeError("OPENAI_API_KEY is not set")
    
    client = OpenAI(api_key=api_key)
    
    # Get model from env
    model = os.getenv("OPENAI_MODEL", "gpt-4o")  # Using gpt-4o for better vision capabilities
    logger.info(f"🟦 [MODEL SELECTED] {model}")
    
    # Encode image to base64 for API
    try:
        logger.info(f"🟦 [LOADING IMAGE] from {image_path}")
        image_b64 = encode_image_to_base64(image_path)
        logger.info(f"🟦 [CONVERT TO BASE64] size={len(image_b64)} bytes")
    except Exception as e:
        logger.error(f"❌ [IMAGE ENCODE FAILED] {e}")
        raise ValueError(f"Failed to encode image: {e}")
    
    # Prepare prompt for translation
    prompt = (
        f"Analyze this image and extract all visible text. Translate each text element to {target_language}. "
        "Return a JSON object with 'text_elements' array, where each element has 'original', 'translation', 'x', 'y', 'width', 'height' fields. "
        "Coordinates should be relative to the image dimensions. "
        f"Example format: {{\"text_elements\":[{{\"original\":\"Hello\", \"translation\":\"Привет\", \"x\":100, \"y\":50, \"width\":200, \"height\":30}}]}}"
    )
    
    logger.info(f"🟦 [PREPARING REQUEST] Prompt length: {len(prompt)} chars")
    
    try:
        logger.info(f"🟦 [OPENAI CALL] model={model}, sending request...")
        
        # Send request to OpenAI Vision API with JSON response format
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            response_format={"type": "json_object"}  # Request JSON response
        )
        
        logger.info(f"✅ [OPENAI RESPONSE] received, usage: {response.usage}")
        
        # Extract the response
        response_content = response.choices[0].message.content
        logger.info(f"🟦 [RESPONSE CONTENT] length={len(response_content)} chars")
        
        # Save debug information
        if job_dir:
            import json  # Ensure json is imported locally
            debug_info = {
                "original_image": str(image_path.name),
                "target_language": target_language,
                "model": model,
                "prompt": prompt,
                "response_preview": response_content[:1000] + ("..." if len(response_content) > 1000 else ""),
                "full_response_length": len(response_content)
            }
            debug_path = job_dir / f"vision_translate_debug_{image_path.stem}.json"
            with open(debug_path, "w", encoding="utf-8") as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)
            logger.info(f"🟦 [DEBUG SAVED] {debug_path}")
        
        # Attempt to create actual translated image using the coordinates from the response
        logger.info(f"🟦 [CREATING TRANSLATED IMAGE] Using coordinates from response")
        
        try:
            # Parse the JSON response to extract text elements
            import json
            import re
            
            # Clean up the response if it contains markdown code blocks
            clean_content = response_content.strip()
            if clean_content.startswith('```json'):
                clean_content = re.sub(r'^```json\s*', '', clean_content)
                clean_content = re.sub(r'\s*```$', '', clean_content)
            elif clean_content.startswith('```'):
                clean_content = re.sub(r'^```\w*\s*', '', clean_content)
                clean_content = re.sub(r'\s*```$', '', clean_content)
            
            try:
                translation_data = json.loads(clean_content)
                text_elements = translation_data.get("text_elements", [])
                logger.info(f"✅ [PARSED] Found {len(text_elements)} text elements")
            except json.JSONDecodeError as e:
                logger.error(f"❌ [JSON PARSE ERROR] {e}")
                logger.info("⚠️  Using fallback approach with original response")
                text_elements = []

            # Create translated image with the parsed coordinates
            translated_image_b64 = _create_translated_image_with_coordinates(
                image_path, 
                text_elements, 
                target_language
            )
            logger.info(f"✅ [IMAGE GENERATED] Translated image created successfully")
            return translated_image_b64
            
        except Exception as pil_error:
            logger.warning(f"⚠️ [COORDINATES-BASED TRANSLATION FAILED] {pil_error}, falling back to basic PIL processing")
            # Fallback to original image
            return image_b64
        
    except Exception as e:
        logger.error(f"❌ [OPENAI API ERROR] {e}")
        raise RuntimeError(f"OpenAI Vision API call failed: {e}")


def _create_json_schema() -> Dict:
    """
    Create JSON schema for document analysis response
    
    Returns:
        JSON schema dictionary
    """
    return {
        "type": "object",
        "properties": {
            "pages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer"},
                        "blocks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["heading", "paragraph", "list", "table", "header", "footer", "figure_caption", "other"]
                                    },
                                    "bbox": {
                                        "type": "array",
                                        "items": {"type": "number"},
                                        "minItems": 4,
                                        "maxItems": 4
                                    },
                                    "text": {"type": "string"}
                                },
                                "required": ["type", "bbox", "text"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["page", "blocks"],
                    "additionalProperties": False
                }
            },
            "meta": {
                "type": "object",
                "properties": {
                    "target_language": {"type": "string"}
                },
                "required": ["target_language"],
                "additionalProperties": False
            }
        },
        "required": ["pages", "meta"],
        "additionalProperties": False
    }


def analyze_document_images(
    image_paths: List[Path], 
    target_language: str, 
    model: Optional[str] = None,
    use_structured_outputs: Optional[bool] = None,
    job_dir: Optional[Path] = None
) -> Dict:
    """
    Analyze document images using OpenAI Vision API with structured outputs
    
    Args:
        image_paths: List of paths to PNG images
        target_language: Target language for translation
        model: OpenAI model to use (default: gpt-4o-mini)
        use_structured_outputs: Whether to use structured outputs with JSON schema (default: True)
        job_dir: Directory to save debug artifacts (optional)
        
    Returns:
        Dictionary with analyzed document structure
        
    Raises:
        RuntimeError: If OPENAI_API_KEY is not set
        ValueError: If response cannot be parsed as JSON
    """
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    
    client = OpenAI(api_key=api_key)
    
    # Get model from env if not provided
    if model is None:
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    
    # Get structured outputs setting from env if not provided
    if use_structured_outputs is None:
        use_structured_outputs = os.getenv("USE_STRUCTURED_OUTPUTS", "true").lower() == "true"
    
    # Save request metadata for debugging
    request_metadata = {
        "model": model,
        "num_pages": len(image_paths),
        "target_language": target_language,
        "use_structured_outputs": use_structured_outputs,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z",
        "structured_attempted": False,
        "structured_succeeded": False,
        "structured_error": None,
        "fallback_used": False
    }
    
    if job_dir:
        with open(job_dir / "openai_request_meta.json", "w") as f:
            json.dump(request_metadata, f, indent=2)
    
    # Prepare instruction
    instruction = (
        "You are a document analysis and translation AI. "
        "Return STRICT valid JSON only (no markdown, no extra text). "
        "Extract blocks with approximate bounding boxes in pixels relative to the page image. "
        f"Translate all text to {target_language}. "
        "Follow the exact JSON schema provided."
    )
    
    # Build content array
    content = [{"type": "text", "text": instruction}]
    
    # Add each image
    for image_path in image_paths:
        data_url = encode_png_to_data_url(image_path)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": data_url,
                "detail": "high"
            }
        })
    
    # Create message
    messages = [
        {
            "role": "user",
            "content": content
        }
    ]
    
    # Try structured outputs first
    if use_structured_outputs:
        request_metadata["structured_attempted"] = True
        try:
            logger.info(f"Attempting structured outputs with model {model}")
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "document_analysis",
                        "schema": _create_json_schema(),
                        "strict": True
                    }
                }
            )
            
            response_text = response.choices[0].message.content
            
            # Save raw response for debugging (limit to 200KB)
            if job_dir:
                raw_response_path = job_dir / "openai_raw.txt"
                with open(raw_response_path, "w", encoding="utf-8") as f:
                    truncated = response_text[:200000]  # 200KB limit
                    f.write(truncated)
                    if len(response_text) > 200000:
                        f.write("\n... [truncated]")
            
            # Parse JSON
            result = json.loads(response_text)
            logger.info("Structured outputs successful")
            request_metadata["structured_succeeded"] = True
            
            # Save updated metadata
            if job_dir:
                with open(job_dir / "openai_request_meta.json", "w") as f:
                    json.dump(request_metadata, f, indent=2)
            
            return result
            
        except Exception as e:
            logger.warning(f"Structured outputs failed: {e}")
            request_metadata["structured_error"] = str(e)[:500]  # Truncate to 500 chars
            request_metadata["fallback_used"] = True
            
            if job_dir:
                with open(job_dir / "openai_error.txt", "w") as f:
                    f.write(f"STRUCTURED OUTPUTS FAILED: {str(e)}\n")
                    f.write(f"Model: {model}\n")
                    f.write(f"Falling back to plain JSON mode\n")
            
            # Fall back to plain JSON mode
            logger.info("Falling back to plain JSON mode")
            
    # Plain JSON mode (fallback or when structured outputs disabled)
    try:
        logger.info(f"Using plain JSON mode with model {model}")
        
        # Update metadata for plain JSON mode
        if job_dir and not use_structured_outputs:
            request_metadata["structured_attempted"] = False
            request_metadata["structured_succeeded"] = False
            request_metadata["fallback_used"] = False
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content
        
        # Save raw response for debugging (limit to 200KB)
        if job_dir:
            raw_response_path = job_dir / "openai_raw.txt"
            with open(raw_response_path, "w", encoding="utf-8") as f:
                truncated = response_text[:200000]  # 200KB limit
                f.write(truncated)
                if len(response_text) > 200000:
                    f.write("\n... [truncated]")
        
        # Parse JSON
        result = json.loads(response_text)
        logger.info("Plain JSON mode successful")
        
        # Save final metadata
        if job_dir:
            with open(job_dir / "openai_request_meta.json", "w") as f:
                json.dump(request_metadata, f, indent=2)
        
        return result
        
    except Exception as e:
        logger.error(f"Plain JSON mode also failed: {e}")
        if job_dir:
            with open(job_dir / "openai_error.txt", "a") as f:
                f.write(f"\nPLAIN JSON MODE FAILED: {str(e)}\n")
        
        # Provide preview of problematic response (first 2000 chars)
        preview = response_text[:2000] + ("..." if len(response_text) > 2000 else "")
        raise ValueError(f"Failed to parse JSON response: {str(e)}\nResponse preview:\n{preview}")


def _create_translated_image_with_coordinates(
    image_path: Path,
    text_elements: list,
    target_language: str
) -> str:
    """
    Create a translated image using PIL by adding text overlay at specific coordinates
    
    Args:
        image_path: Path to original image
        text_elements: List of text elements with coordinates and translations
        target_language: Target language for translation
        
    Returns:
        Base64 encoded image with translated text
    """
    logger.info(f"🟦 [PIL COORDINATE PROCESSING] Starting image processing with PIL using coordinates")
    
    try:
        # Open original image
        with Image.open(image_path) as img:
            # Convert to RGBA to support transparency
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            logger.info(f"🟦 [IMAGE LOADED] Size: {img.size}, Mode: {img.mode}")
            
            from PIL import ImageDraw, ImageFont
            
            draw = ImageDraw.Draw(img)
            
            # Try to get a font, fallback to default
            try:
                # Try to use a system font
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
                except:
                    font = ImageFont.load_default()
            
            # Get image dimensions for coordinate conversion
            img_width, img_height = img.size
            
            # Draw each translated text element at its coordinates
            for element in text_elements:
                original = element.get("original", "")
                translation = element.get("translation", "")
                norm_x = element.get("x", 0.1)  # Normalized x coordinate (0-1)
                norm_y = element.get("y", 0.1)  # Normalized y coordinate (0-1)
                norm_width = element.get("width", 0.2)  # Normalized width (0-1)
                norm_height = element.get("height", 0.1)  # Normalized height (0-1)
                
                # Convert normalized coordinates to pixel coordinates
                x = int(norm_x * img_width)
                y = int(norm_y * img_height)
                width = int(norm_width * img_width)
                height = int(norm_height * img_height)
                
                # Draw the translated text at the specified coordinates
                if translation.strip():
                    # Add a semi-transparent background to make text more readable
                    bbox = draw.textbbox((x, y), translation, font=font)
                    draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], fill=(255, 255, 255, 180))
                    draw.text((x, y), translation, fill=(0, 0, 0), font=font)
                    
                    logger.info(f"✅ [DRAWN TEXT] '{translation[:30]}...' at ({x}, {y})")
            
            # Add a small indicator that this is a vision-processed image
            draw.text((10, img.height - 20), "AI TRANSLATED", fill=(0, 128, 0), font=font)
            
            logger.info(f"🟦 [TEXT OVERLAYS ADDED] Processed {len(text_elements)} text elements")
            
            # Save to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Convert to base64
            image_b64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            logger.info(f"✅ [PIL COMPLETE] Generated image, size: {len(image_b64)} bytes")
            
            return image_b64
            
    except Exception as e:
        logger.error(f"❌ [PIL COORDINATE PROCESSING FAILED] {e}")
        raise RuntimeError(f"PIL coordinate-based image processing failed: {e}")


def _create_translated_image_with_pil(
    image_path: Path,
    vision_response: str,
    target_language: str
) -> str:
    """
    Create a translated image using PIL by adding text overlay
    This is a fallback when OpenAI Vision can't generate images directly
    
    Args:
        image_path: Path to original image
        vision_response: Response from OpenAI Vision API
        target_language: Target language for translation
        
    Returns:
        Base64 encoded image with translated text
    """
    logger.info(f"🟦 [PIL PROCESSING] Starting image processing with PIL")
    
    try:
        # Open original image
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            logger.info(f"🟦 [IMAGE LOADED] Size: {img.size}, Mode: {img.mode}")
            
            # For demonstration, we'll add a simple text overlay
            # In a real implementation, you'd parse bounding boxes from vision_response
            from PIL import ImageDraw, ImageFont
            
            draw = ImageDraw.Draw(img)
            
            # Try to get a font, fallback to default
            try:
                # Try to use a system font
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", 24)
                except:
                    font = ImageFont.load_default()
            
            # Add translated text watermark
            text = f"TRANSLATED TO {target_language.upper()}" if target_language != "english" else "TRANSLATED IMAGE"
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Position in bottom-right corner
            x = img.width - text_width - 20
            y = img.height - text_height - 20
            
            # Draw background rectangle
            draw.rectangle([x-5, y-5, x+text_width+5, y+text_height+5], fill=(255, 255, 255, 180))
            
            # Draw text
            draw.text((x, y), text, fill=(0, 0, 0), font=font)
            
            logger.info(f"🟦 [TEXT OVERLAY ADDED] '{text}' at position ({x}, {y})")
            
            # Save to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Convert to base64
            image_b64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            logger.info(f"✅ [PIL COMPLETE] Generated image, size: {len(image_b64)} bytes")
            
            return image_b64
            
    except Exception as e:
        logger.error(f"❌ [PIL PROCESSING FAILED] {e}")
        raise RuntimeError(f"PIL image processing failed: {e}")


# Additional utility functions for image processing with PIL

def save_translated_image(base64_image: str, output_path: Path) -> None:
    """
    Save base64 encoded image to file
    
    Args:
        base64_image: Base64 encoded image string
        output_path: Path where to save the image
    """
    try:
        image_bytes = base64.b64decode(base64_image)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        logger.info(f"Saved translated image to: {output_path}")
    except Exception as e:
        logger.error(f"Failed to save translated image: {e}")
        raise ValueError(f"Failed to save translated image: {e}")
