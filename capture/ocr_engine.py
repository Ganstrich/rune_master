"""Modular OCR Engine interfaces and implementations.

Provides a common interface (BaseOCREngine) and a concrete wrapper for EasyOCR.
Allows swapping to other backends (Tesseract, PaddleOCR) in the future.
"""
import numpy as np
from typing import List, Dict, Any, Tuple

class BaseOCREngine:
    """Base class for all OCR engines used in RuneMaster."""
    
    def extract_text(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """Run OCR on the provided image.
        
        Args:
            img: OpenCV numpy array (BGR or Grayscale).
            
        Returns:
            List of dicts: [
                {
                    "text": str,
                    "confidence": float,
                    # bbox as tuple: (x, y, width, height) of the word/line
                    "bbox": Tuple[int, int, int, int]
                },
                ...
            ]
        """
        raise NotImplementedError("OCR engines must implement extract_text")

class EasyOCREngine(BaseOCREngine):
    """Wrapper around the EasyOCR library."""
    
    def __init__(self, languages: List[str] = None, gpu: bool = True):
        """Initialize EasyOCR reader.
        
        Args:
            languages: List of language codes, defaults to ['fr', 'en'].
            gpu: Enable GPU acceleration (requires PyTorch with CUDA/MPS support).
        """
        self.languages = languages or ["fr", "en"]
        self.gpu = gpu
        self._reader = None

    @property
    def reader(self):
        """Lazy initialization of EasyOCR reader to speed up initial module import."""
        if self._reader is None:
            try:
                import easyocr
                # This may download language model files on first run
                self._reader = easyocr.Reader(self.languages, gpu=self.gpu)
            except ImportError:
                print("❌ Error: 'easyocr' is not installed. Run 'pip install easyocr'.")
                raise
            except Exception as e:
                print(f"❌ Failed to initialize EasyOCR: {e}")
                raise
        return self._reader

    def extract_text(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """Extract text boxes using EasyOCR.
        
        Returns:
            List of bounding box dicts.
        """
        # EasyOCR expects RGB numpy array or filepath
        # If OpenCV BGR is passed, convert to RGB
        if len(img.shape) == 3 and img.shape[2] == 3:
            import cv2
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        else:
            rgb_img = img

        results = self.reader.readtext(rgb_img)
        
        output = []
        for bbox, text, confidence in results:
            # bbox is list of 4 points: [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            
            x_min = int(min(x_coords))
            y_min = int(min(y_coords))
            width = int(max(x_coords) - x_min)
            height = int(max(y_coords) - y_min)
            
            output.append({
                "text": text.strip(),
                "confidence": float(confidence),
                "bbox": (x_min, y_min, width, height)
            })
            
        return output
