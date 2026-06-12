"""Layout matching module to map unstructured OCR text boxes to item/price fields.

Defines a modular BaseLayoutMatcher and provides Template and Heuristic implementations.
The Heuristic matcher clusters OCR detections into rows and columns to robustly infer
item names and prices (x1, x10, x100, x1000) under varying window scales and layouts.
"""
from typing import List, Dict, Any, Tuple, Optional

class BaseLayoutMatcher:
    """Base class for mapping raw OCR bounding boxes to structured data fields."""
    
    def match_layout(self, boxes: List[Dict[str, Any]], window_size: Tuple[int, int]) -> Dict[str, Any]:
        """Map raw OCR boxes to structured data fields.
        
        Args:
            boxes: List of OCR results with "text", "bbox" (x, y, w, h), and "confidence".
            window_size: Width and height of the cropped region/window.
            
        Returns:
            Dict containing parsed fields, e.g.:
            {
                "item_name": Optional[str],
                "price_x1": Optional[int],
                "price_x10": Optional[int],
                "price_x100": Optional[int],
                "price_x1000": Optional[int]
            }
        """
        raise NotImplementedError("Layout matchers must implement match_layout")


class TemplateLayoutMatcher(BaseLayoutMatcher):
    """Maps OCR boxes using fixed coordinate bounding box templates (Regions of Interest)."""

    def __init__(self, templates: Dict[str, Tuple[float, float, float, float]] = None):
        """Initialize with relative templates.
        
        Args:
            templates: Dict of field_name -> relative bbox (x_rel, y_rel, w_rel, h_rel)
                       where coordinates are normalized percentages of the cropped region (0.0 to 1.0).
        """
        # Default template values for Dofus 3 shop layouts
        self.templates = templates or {
            "item_name": (0.05, 0.05, 0.90, 0.15),
            "price_x1": (0.10, 0.30, 0.80, 0.10),
            "price_x10": (0.10, 0.45, 0.80, 0.10),
            "price_x100": (0.10, 0.60, 0.80, 0.10),
            "price_x1000": (0.10, 0.75, 0.80, 0.10)
        }

    def match_layout(self, boxes: List[Dict[str, Any]], window_size: Tuple[int, int]) -> Dict[str, Any]:
        w, h = window_size
        results: Dict[str, Any] = {
            "item_name": None,
            "price_x1": None,
            "price_x10": None,
            "price_x100": None,
            "price_x1000": None
        }

        # Convert template boxes to absolute pixels
        abs_templates = {}
        for field, (rx, ry, rw, rh) in self.templates.items():
            abs_templates[field] = (rx * w, ry * h, rw * w, rh * h)

        for box in boxes:
            bx, by, bw, bh = box["bbox"]
            cx = bx + bw / 2.0
            cy = by + bh / 2.0

            # Find matching template
            for field, (tx, ty, tw, th) in abs_templates.items():
                if tx <= cx <= (tx + tw) and ty <= cy <= (ty + th):
                    # For prices, we append or update if confidence is higher
                    if field.startswith("price"):
                        if results[field] is None or box["confidence"] > results[field].get("confidence", 0):
                            results[field] = box
                    else:
                        if results[field] is None or box["confidence"] > results[field].get("confidence", 0):
                            results[field] = box

        # Extract just the text from matches
        final_results = {}
        for field, box in results.items():
            final_results[field] = box["text"] if box else None
            
        return final_results


class HeuristicLayoutMatcher(BaseLayoutMatcher):
    """Dynamically groups text boxes into rows and detects price associations.
    
    Robust against resolution scaling and shifting window boundaries.
    """

    def __init__(self, y_threshold: int = 15):
        """Initialize heuristic matcher.
        
        Args:
            y_threshold: Pixel threshold for grouping words into the same horizontal row.
        """
        self.y_threshold = y_threshold

    def match_layout(self, boxes: List[Dict[str, Any]], window_size: Tuple[int, int]) -> Dict[str, Any]:
        if not boxes:
            return {}

        # 1. Sort boxes by Y-coordinate
        sorted_boxes = sorted(boxes, key=lambda b: b["bbox"][1])
        
        # 2. Group into horizontal rows
        rows: List[List[Dict[str, Any]]] = []
        for box in sorted_boxes:
            bx, by, bw, bh = box["bbox"]
            cy = by + bh / 2.0
            
            # Try to place in an existing row
            placed = False
            for row in rows:
                # Calculate average Y center of this row
                row_cy = sum(b["bbox"][1] + b["bbox"][3] / 2.0 for b in row) / len(row)
                if abs(cy - row_cy) <= self.y_threshold:
                    row.append(box)
                    placed = True
                    break
            
            if not placed:
                rows.append([box])

        # 3. Sort each row from left to right (by X coordinate)
        for row in rows:
            row.sort(key=lambda b: b["bbox"][0])

        # 4. Extract name (usually the top-most distinct non-numeric string block)
        item_name = None
        for i, row in enumerate(rows):
            # If it's the first few rows, look for the title text
            if i < 3:
                row_text = " ".join(b["text"] for b in row if not b["text"].replace(" ", "").isdigit())
                if row_text and len(row_text) > 2:
                    item_name = row_text
                    break

        # 5. Extract prices by scanning rows for quantity markers (e.g. "Lot de 1", "x100", "10")
        prices = {
            "price_x1": None,
            "price_x10": None,
            "price_x100": None,
            "price_x1000": None
        }

        for row in rows:
            row_text_lower = " ".join(b["text"].lower() for b in row)
            
            # Find row numbers/digits
            numbers = []
            for b in row:
                cleaned = b["text"].replace(" ", "").replace(".", "").replace(",", "")
                if cleaned.isdigit():
                    numbers.append((int(cleaned), b))

            # Look for quantity labels
            qty = None
            if "1 000" in row_text_lower or "1000" in row_text_lower or "x1000" in row_text_lower or "x 1000" in row_text_lower:
                qty = 1000
            elif "100" in row_text_lower or "x100" in row_text_lower:
                qty = 100
            elif "10" in row_text_lower or "x10" in row_text_lower:
                qty = 10
            elif "1" in row_text_lower or "x1" in row_text_lower:
                # Ensure it's not matching 10, 100, or 1000
                if not any(q in row_text_lower for q in ["10", "100", "1000"]):
                    qty = 1

            if qty is not None:
                # Find the actual price (usually the largest number or the rightmost number in the row)
                # Filter out the quantity itself from numbers
                price_candidates = [num for num, box in numbers if num != qty]
                if price_candidates:
                    # Choose the rightmost number as the price (prices are usually on the right)
                    rightmost_num = max(numbers, key=lambda item: item[1]["bbox"][0])
                    prices[f"price_x{qty}"] = str(rightmost_num[0])
            else:
                # Fallback: if no label is matched, but the row contains exactly 2 numbers (e.g. quantity and price)
                if len(numbers) == 2:
                    val1, box1 = numbers[0]
                    val2, box2 = numbers[1]
                    # The first is likely quantity (1, 10, 100, 1000)
                    if val1 in [1, 10, 100, 1000]:
                        prices[f"price_x{val1}"] = str(val2)

        return {
            "item_name": item_name,
            **prices
        }
