#!/usr/bin/env python3
"""Dedicated web server for RuneMaster visualizations.

Allows the visualization dashboard to remain active while the 
processing engine is iterated on in a separate terminal.
"""

import os
import sys
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()

def start_server(port: int = 8000):
    """Start HTTP server to serve visualizations."""
    print("\n" + "="*60)
    print("🌐 RUNEMASTER VISUALIZATION SERVER")
    print("="*60)

    # Ensure visualizations directory exists
    visualizations_dir = os.path.join(PROJECT_ROOT, "visualizations")
    if not os.path.exists(visualizations_dir):
        os.makedirs(visualizations_dir)
        # Create a dummy index if none exists
        index_path = os.path.join(visualizations_dir, "index.html")
        if not os.path.exists(index_path):
            with open(index_path, 'w') as f:
                f.write("<html><body><h1>No reports generated yet.</h1><p>Run main.py first.</p></body></html>")

    os.chdir(visualizations_dir)

    class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
        """Suppress logging for favicon.ico requests."""
        def log_message(self, format, *args):
            if args and isinstance(args[0], str):
                if "favicon.ico" not in args[0]:
                    super().log_message(format, *args)
            else:
                super().log_message(format, *args)

    try:
        server = HTTPServer(("127.0.0.1", port), QuietHTTPRequestHandler)
        
        url = f"http://127.0.0.1:{port}/index.html"
        print(f"\n🚀 Server running at: {url}")
        print(f"✅ Dashboard is active. You can now run 'main.py' to update reports.")
        print(f"✅ Refresh the browser to see changes.")
        print("\nPress Ctrl+C to stop the server\n")
        
        # Open browser automatically on first start
        webbrowser.open(url)
        
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down server...")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check for port override
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    
    start_server(port)
