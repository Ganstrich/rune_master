import os
from http.server import HTTPServer, SimpleHTTPRequestHandler


def start_dev_server(port: int = 8000, directory: str = "visualizations"):
    """Start HTTP server to serve visualizations."""
    print("\n" + "=" * 60)
    print("🌐 STARTING WEB SERVER")
    print("=" * 60)

    if not os.path.exists(directory):
        print(f"❌ Directory '{directory}' does not exist.")
        return None

    os.chdir(directory)

    class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            if args and isinstance(args[0], str):
                if "favicon.ico" not in args[0]:
                    super().log_message(format, *args)
            else:
                super().log_message(format, *args)

    server = HTTPServer(("127.0.0.1", port), QuietHTTPRequestHandler)
    print(f"\n🚀 Server running at: http://127.0.0.1:{port}/")
    print(f"   View in browser: http://127.0.0.1:{port}/index.html")
    return server
