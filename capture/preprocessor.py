"""Image preprocessing module using OpenCV.

Prepares raw screenshots of the Dofus game window for OCR by cropping 
regions of interest (ROIs), resizing, converting to grayscale, and 
applying thresholding filters.
"""
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Tuple, Union, Optional

class ImagePreprocessor:
    """Processes images to optimize them for optical character recognition (OCR)."""

    @staticmethod
    def to_cv2(img: Union[Image.Image, np.ndarray]) -> np.ndarray:
        """Convert a PIL Image or numpy array to an OpenCV BGR image."""
        if isinstance(img, Image.Image):
            # PIL Image -> NumPy array (RGB) -> OpenCV (BGR)
            arr = np.array(img)
            if len(arr.shape) == 2:  # Grayscale
                return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return img.copy()

    @staticmethod
    def to_pil(img: np.ndarray) -> Image.Image:
        """Convert an OpenCV BGR/Grayscale image to a PIL Image."""
        if len(img.shape) == 2:  # Grayscale
            return Image.fromarray(img)
        # BGR -> RGB
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    def crop_roi(self, img: np.ndarray, bbox: Tuple[float, float, float, float], relative: bool = True) -> np.ndarray:
        """Crop a specific Region of Interest (ROI) from the window image.
        
        Args:
            img: OpenCV BGR image.
            bbox: Bounding box as (x, y, width, height).
            relative: If True, coordinates are percentages of the image size (0.0 to 1.0).
                     If False, coordinates are in absolute pixels.
                     
        Returns:
            Cropped image.
        """
        h, w = img.shape[:2]
        x, y, width, height = bbox

        if relative:
            x_pixel = int(x * w)
            y_pixel = int(y * h)
            w_pixel = int(width * w)
            h_pixel = int(height * h)
        else:
            x_pixel = int(x)
            y_pixel = int(y)
            w_pixel = int(width)
            h_pixel = int(height)

        # Guard boundaries
        x1 = max(0, x_pixel)
        y1 = max(0, y_pixel)
        x2 = min(w, x_pixel + w_pixel)
        y2 = min(h, y_pixel + h_pixel)

        return img[y1:y2, x1:x2]

    def optimize_for_ocr(
        self, 
        img: np.ndarray, 
        scale_factor: float = 2.0, 
        binarize: bool = False,
        invert: bool = False
    ) -> np.ndarray:
        """Apply filters to make text/numbers stand out.
        
        Args:
            img: OpenCV image.
            scale_factor: Resize multiplier (larger image helps OCR engines read small text).
            binarize: Apply adaptive thresholding to convert to binary black/white.
            invert: Invert colors (sometimes OCR models read black-on-white better).
            
        Returns:
            Processed OpenCV image.
        """
        # Convert to Grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # Resize (Upscale) using cubic interpolation
        if scale_factor != 1.0:
            new_w = int(gray.shape[1] * scale_factor)
            new_h = int(gray.shape[0] * scale_factor)
            gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        processed = gray

        # Binarization
        if binarize:
            # Dofus has dark/light background gradients; adaptive thresholding works best
            processed = cv2.adaptiveThreshold(
                processed,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                15, # block size
                4   # constant subtracted from mean
            )
            
            # Reduce noise using a small morphological opening
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
            processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)

        # Invert colors if requested
        if invert:
            processed = cv2.bitwise_not(processed)

        return processed
