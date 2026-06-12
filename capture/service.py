"""Service coordinator and global hotkey listener for the OCR capture module.

Orchestrates the lifecycle: ScreenGrabber -> ImagePreprocessor -> EasyOCREngine ->
HeuristicLayoutMatcher -> MarketParser -> DatabaseWriter.
"""
import time
import sys
from typing import Optional, Tuple
from data.cache_manager import CacheManager
from capture.screen_grabber import ScreenGrabber
from capture.preprocessor import ImagePreprocessor
from capture.ocr_engine import EasyOCREngine
from capture.layout_matcher import HeuristicLayoutMatcher, TemplateLayoutMatcher
from capture.market_parser import MarketParser
from capture.database_writer import DatabaseWriter

class MarketCaptureService:
    """Orchestrates screen grabbing, preprocessing, OCR execution, and DB storage."""

    def __init__(self, cache_file: str = "resource_cache.db", window_title: str = "Dofus"):
        self.cache_manager = CacheManager(cache_file=cache_file)
        self.grabber = ScreenGrabber(window_title=window_title)
        self.preprocessor = ImagePreprocessor()
        
        # We start with the best possible engine (EasyOCR)
        print("🤖 Initializing OCR Engine (EasyOCR)...")
        self.ocr_engine = EasyOCREngine(languages=["fr", "en"], gpu=True)
        
        # Using the robust Heuristic matcher as the default
        self.layout_matcher = HeuristicLayoutMatcher()
        
        self.parser = MarketParser(self.cache_manager)
        self.db_writer = DatabaseWriter(self.cache_manager)
        
        self.is_active = False

    def capture_and_process(self, calibration_offset: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """Run a single capture, preprocess, OCR, and DB write cycle."""
        print("\n📸 [Capture] Triggered screenshot...")
        start_time = time.time()

        # 1. Grab window
        pil_img = self.grabber.grab_window(calibration_offset)
        if pil_img is None:
            print("❌ Capture failed: Dofus window not found.")
            return False

        # 2. Convert to OpenCV format
        cv_img = self.preprocessor.to_cv2(pil_img)
        h, w = cv_img.shape[:2]
        print(f"🖼️  Captured game client window: {w}x{h} pixels")

        # 3. Optimize image for OCR (Grayscale, upscaling)
        preprocessed_img = self.preprocessor.optimize_for_ocr(cv_img, scale_factor=2.0)

        # 4. Perform OCR
        print("🔍 Executing OCR detection...")
        ocr_results = self.ocr_engine.extract_text(preprocessed_img)
        if not ocr_results:
            print("⚠️  No text detected in the capture area.")
            return False
        
        # Adjust OCR coordinates back to original size (scale factor correction)
        # Because we upscaled the image by 2x for OCR accuracy
        for res in ocr_results:
            bx, by, bw, bh = res["bbox"]
            res["bbox"] = (int(bx / 2.0), int(by / 2.0), int(bw / 2.0), int(bh / 2.0))

        print(f"📝 OCR parsed {len(ocr_results)} text blocks.")

        # 5. Match bounding boxes to fields using heuristic rules
        matched_layout = self.layout_matcher.match_layout(ocr_results, (w, h))
        if not matched_layout.get("item_name") and not any(matched_layout.get(f"price_x{q}") for q in [1, 10, 100, 1000]):
            print("⚠️  Could not detect item name or price columns in the captured area.")
            return False

        # 6. Parse and clean values (resolve Ankama ID)
        parsed_record = self.parser.parse_market_record(matched_layout)

        # 7. Write to database
        success = self.db_writer.write_prices(parsed_record)
        
        elapsed = time.time() - start_time
        if success:
            print(f"🎉 Successful capture processed in {elapsed:.2f}s!")
        else:
            print(f"❌ Processing completed but failed to update database.")
            
        return success

    def run_hotkey_listener(self):
        """Start global keyboard listener (F10 to trigger capture)."""
        try:
            from pynput import keyboard
        except ImportError:
            print("⚠️  'pynput' not installed. Falling back to CLI mode.")
            self.run_cli_loop()
            return

        def on_press(key):
            try:
                # Check for F10 key
                if key == keyboard.Key.f10:
                    if self.is_active:
                        self.capture_and_process()
            except AttributeError:
                pass

        print("\n⚡ Running in Keyboard Hotkey Mode.")
        print("💡 Navigate to Dofus client shop window, hover over an item, and press [F10] to capture.")
        print("⌨️  Press Ctrl+C in this terminal to stop the service.\n")

        self.is_active = True
        
        # Start listener in blocking mode
        with keyboard.Listener(on_press=on_press) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                print("\n👋 Stopping capture service...")
            finally:
                self.is_active = False

    def run_cli_loop(self):
        """Fallback CLI input loop (type 'c' to capture)."""
        print("\n⌨️ Running in Terminal Command Mode.")
        print("💡 Navigate to Dofus client shop window, then:")
        print("   - Type 'c' and press Enter to capture prices.")
        print("   - Type 'q' and press Enter to quit.\n")
        
        try:
            while True:
                cmd = input("Command [c=Capture, q=Quit]: ").strip().lower()
                if cmd == 'c':
                    self.capture_and_process()
                elif cmd == 'q':
                    print("👋 Stopping capture service...")
                    break
        except KeyboardInterrupt:
            print("\n👋 Stopping capture service...")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RuneMaster OCR Market Capture Service")
    parser.add_argument("--cli", action="store_true", help="Force terminal command mode instead of keyboard hotkey listener")
    parser.add_argument("--db", type=str, default="resource_cache.db", help="Path to resource cache database")
    parser.add_argument("--title", type=str, default="Dofus", help="Game client window name")
    args = parser.parse_args()

    service = MarketCaptureService(cache_file=args.db, window_title=args.title)
    
    if args.cli:
        service.run_cli_loop()
    else:
        service.run_hotkey_listener()
