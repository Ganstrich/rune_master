"""Cross-platform Dofus window detection and screen grabbing using mss.

Supports Windows (ctypes), Linux (wmctrl/xdotool), and macOS (AppleScript),
with manual calibration fallback.
"""
import os
import sys
import subprocess
from typing import Optional, Tuple, Dict, Any
import mss
from PIL import Image

class ScreenGrabber:
    """Handles locating the Dofus game client window and capturing its screen area."""

    def __init__(self, window_title: str = "Dofus"):
        self.window_title = window_title
        self.sct = mss.mss()

    def get_dofus_window_rect(self) -> Optional[Dict[str, int]]:
        """Attempt to find the Dofus window boundary coordinates.
        
        Returns:
            Dict containing 'left', 'top', 'width', 'height' or None if not found.
        """
        platform = sys.platform
        
        if platform.startswith("win"):
            return self._get_windows_rect()
        elif platform.startswith("linux"):
            return self._get_linux_rect()
        elif platform.startswith("darwin"):
            return self._get_macos_rect()
            
        return None

    def _get_windows_rect(self) -> Optional[Dict[str, int]]:
        """Find window on Windows using ctypes."""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Find window handle
            hwnd = ctypes.windll.user32.FindWindowW(None, self.window_title)
            if not hwnd:
                # Try finding by substring
                def callback(hwnd, extra):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                    if self.window_title.lower() in buff.value.lower():
                        extra.append(hwnd)
                    return True
                
                hwnds = []
                # WNDENUMPROC signature: BOOL CALLBACK EnumWindowsProc(HWND hwnd, LPARAM lParam)
                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
                ctypes.windll.user32.EnumWindows(WNDENUMPROC(callback), ctypes.py_object(hwnds))
                if hwnds:
                    hwnd = hwnds[0]
                else:
                    return None
            
            # Get window dimensions
            rect = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            
            # Check for minimized window
            if rect.left == -32000:
                return None
                
            return {
                "left": rect.left,
                "top": rect.top,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top
            }
        except Exception as e:
            print(f"⚠️  Windows window detection error: {e}")
            return None

    def _get_linux_rect(self) -> Optional[Dict[str, int]]:
        """Find window on Linux using wmctrl or xdotool."""
        try:
            # Try wmctrl first
            proc = subprocess.run(["wmctrl", "-lG"], capture_output=True, text=True, check=True)
            for line in proc.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 8:
                    title = " ".join(parts[7:])
                    if self.window_title.lower() in title.lower():
                        return {
                            "left": int(parts[2]),
                            "top": int(parts[3]),
                            "width": int(parts[4]),
                            "height": int(parts[5])
                        }
        except Exception:
            pass

        try:
            # Fallback to xdotool
            proc = subprocess.run(["xdotool", "search", "--name", self.window_title], capture_output=True, text=True, check=True)
            window_ids = proc.stdout.strip().split()
            if window_ids:
                window_id = window_ids[0]
                geom_proc = subprocess.run(["xdotool", "getwindowgeometry", window_id], capture_output=True, text=True, check=True)
                lines = geom_proc.stdout.splitlines()
                # Parse output:
                # Position: 120,45 (Screen 0)
                # Geometry: 1024x768
                left, top = 0, 0
                width, height = 0, 0
                for line in lines:
                    if "Position:" in line:
                        pos = line.split()[1].split("(")[0].split(",")
                        left, top = int(pos[0]), int(pos[1])
                    elif "Geometry:" in line:
                        geom = line.split()[1].split("x")
                        width, height = int(geom[0]), int(geom[1])
                return {"left": left, "top": top, "width": width, "height": height}
        except Exception:
            pass
            
        return None

    def _get_macos_rect(self) -> Optional[Dict[str, int]]:
        """Find window on macOS using AppleScript."""
        applescript = f'''
        tell application "System Events"
            try
                set proc to first process whose name contains "{self.window_title}"
                set win to window 1 of proc
                set pos to position of win
                set sz to size of win
                return (item 1 of pos as text) & "," & (item 2 of pos as text) & "," & (item 1 of sz as text) & "," & (item 2 of sz as text)
            on error
                return ""
            end try
        end tell
        '''
        try:
            proc = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
            res = proc.stdout.strip()
            if res:
                parts = res.split(",")
                return {
                    "left": int(parts[0]),
                    "top": int(parts[1]),
                    "width": int(parts[2]),
                    "height": int(parts[3])
                }
        except Exception as e:
            print(f"⚠️  macOS AppleScript detection error: {e}")
        return None

    def grab_screenshot(self, monitor_idx: int = 1) -> Image.Image:
        """Capture the full screen of a specific monitor.
        
        Args:
            monitor_idx: Monitor index starting at 1.
            
        Returns:
            PIL Image of the full screen.
        """
        # mss monitor 1 is primary monitor
        monitors = self.sct.monitors
        if monitor_idx < len(monitors):
            monitor = monitors[monitor_idx]
        else:
            monitor = monitors[0] # Entire virtual display
            
        sct_img = self.sct.grab(monitor)
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    def grab_window(self, calibration_offset: Optional[Tuple[int, int, int, int]] = None) -> Optional[Image.Image]:
        """Find and capture only the Dofus game client window.
        
        Args:
            calibration_offset: Optional manual override tuple (left, top, width, height).
            
        Returns:
            PIL Image of the window area, or None if the window is not found.
        """
        if calibration_offset:
            left, top, width, height = calibration_offset
            rect = {"left": left, "top": top, "width": width, "height": height}
        else:
            rect = self.get_dofus_window_rect()
            
        if not rect:
            print(f"⚠️  Dofus window '{self.window_title}' not found.")
            return None

        # Grab bounding box
        try:
            # mss needs coordinates inside a dictionary or tuple
            # If coordinates are slightly outside bounds, mss handles clipping
            sct_img = self.sct.grab(rect)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception as e:
            print(f"❌ Error grabbing window coordinates {rect}: {e}")
            return None
