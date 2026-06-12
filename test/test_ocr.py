"""Unit tests for the OCR Capture module.

Tests image preprocessing, heuristic layout matching, price string cleaning,
fuzzy item resolution, and SQLite database storage updates.
"""
import os
import sqlite3
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from data.cache_manager import CacheManager
from capture.preprocessor import ImagePreprocessor
from capture.layout_matcher import HeuristicLayoutMatcher, TemplateLayoutMatcher
from capture.market_parser import MarketParser
from capture.database_writer import DatabaseWriter

@pytest.fixture
def temp_db(tmp_path):
    """Fixture to create a temporary SQLite DB for cache testing."""
    db_file = tmp_path / "test_cache.db"
    cache = CacheManager(cache_file=str(db_file))
    
    # Insert mock resources for fuzzy matching tests
    conn = cache._conn
    conn.execute("INSERT INTO resources (id, name, data) VALUES (1, 'Gelano', '{}')")
    conn.execute("INSERT INTO resources (id, name, data) VALUES (2, 'Coiffe du Bouftou', '{}')")
    conn.execute("INSERT INTO resources (id, name, data) VALUES (3, 'Anneau de l\'Invouqué', '{}')")
    conn.commit()
    
    yield cache
    
    # Close connection
    cache._conn.close()

def test_preprocessor_conversion():
    """Test PIL to OpenCV image conversion formats."""
    from PIL import Image
    # Create mock 10x10 RGB image
    pil_img = Image.new("RGB", (10, 10), color="red")
    cv_img = ImagePreprocessor.to_cv2(pil_img)
    
    assert isinstance(cv_img, np.ndarray)
    assert cv_img.shape == (10, 10, 3)
    # Check red channel placement (Red in BGR is index 2)
    assert cv_img[0, 0, 2] == 255
    assert cv_img[0, 0, 0] == 0

def test_preprocessor_cropping():
    """Test relative region of interest cropping."""
    prep = ImagePreprocessor()
    # Create black image with a white square in the center
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[40:60, 40:60] = 255
    
    # Crop central 20% relative box
    cropped = prep.crop_roi(img, (0.4, 0.4, 0.2, 0.2), relative=True)
    assert cropped.shape == (20, 20, 3)
    assert np.all(cropped == 255)

def test_heuristic_layout_matcher():
    """Test grouping of OCR boxes into rows and matching quantities to prices."""
    matcher = HeuristicLayoutMatcher(y_threshold=10)
    
    # Simulate OCR boxes in different rows
    # Row 0: Item Name
    # Row 1: Lot de 1 -> 450
    # Row 2: Lot de 10 -> 4 100
    # Row 3: Lot de 100 -> 39 000
    # Row 4: Lot de 1000 -> 385 000
    mock_boxes = [
        {"text": "Gelano", "confidence": 0.99, "bbox": (10, 10, 50, 15)},
        
        {"text": "Lot de 1", "confidence": 0.95, "bbox": (10, 40, 40, 15)},
        {"text": "450", "confidence": 0.97, "bbox": (200, 40, 30, 15)},
        
        {"text": "Lot de 10", "confidence": 0.95, "bbox": (10, 70, 45, 15)},
        {"text": "4 100", "confidence": 0.97, "bbox": (200, 70, 40, 15)},
        
        {"text": "Lot de 100", "confidence": 0.95, "bbox": (10, 100, 50, 15)},
        {"text": "39 000", "confidence": 0.97, "bbox": (200, 100, 45, 15)},
        
        {"text": "Lot de 1 000", "confidence": 0.95, "bbox": (10, 130, 55, 15)},
        {"text": "385 000", "confidence": 0.97, "bbox": (200, 130, 50, 15)},
    ]
    
    matched = matcher.match_layout(mock_boxes, (400, 200))
    
    assert matched["item_name"] == "Gelano"
    assert matched["price_x1"] == "450"
    assert matched["price_x10"] == "4100"
    assert matched["price_x100"] == "39000"
    assert matched["price_x1000"] == "385000"

def test_market_parser_cleaning():
    """Test converting formatted OCR price strings to integers."""
    assert MarketParser.clean_price("450") == 450
    assert MarketParser.clean_price("4 100") == 4100
    assert MarketParser.clean_price("39.000") == 39000
    assert MarketParser.clean_price("385,000 Kamas") == 385000
    assert MarketParser.clean_price("Kamas") is None

def test_market_parser_fuzzy_matching(temp_db):
    """Test resolving misspelled or shifted item names using database cache."""
    parser = MarketParser(temp_db)
    
    # Exact match
    assert parser.find_item_id("Gelano") == 1
    
    # Typo match
    assert parser.find_item_id("Coife du Bouftou") == 2
    
    # Accent and casing tolerance
    assert parser.find_item_id("coiffe du bouftou") == 2
    assert parser.find_item_id("ANNEAU DE L'INVOUQUE") == 3
    
    # Completely wrong shouldn't match
    assert parser.find_item_id("Unknown Item") is None

def test_database_writer_upsert(temp_db):
    """Test database schema creation and upsert updates (including x1000 price)."""
    writer = DatabaseWriter(temp_db)
    
    record = {
        "item_id": 1,
        "item_name": "Gelano",
        "price_x1": 500,
        "price_x10": 4800,
        "price_x100": 45000,
        "price_x1000": 420000
    }
    
    # Write new item prices
    assert writer.write_prices(record) is True
    
    # Verify values stored
    stored = writer.get_prices(1)
    assert stored is not None
    assert stored["price_x1"] == 500
    assert stored["price_x10"] == 4800
    assert stored["price_x100"] == 45000
    assert stored["price_x1000"] == 420000
    
    # Update prices (ON CONFLICT DO UPDATE check)
    record["price_x1"] = 490
    record["price_x1000"] = 415000
    assert writer.write_prices(record) is True
    
    # Verify updated values
    updated = writer.get_prices(1)
    assert updated["price_x1"] == 490
    assert updated["price_x10"] == 4800
    assert updated["price_x1000"] == 415000
