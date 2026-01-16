#!/usr/bin/env python3
"""Main entry point for RuneMaster equipment group discovery and visualization.

Pipeline:
    1. Load configuration
    2. Fetch equipment from DofusAPI
    3. Transform equipment to dataclasses (with caching)
    4. Run RuneMaster processing pipeline
    5. Generate visualizations
    6. Start HTTP server
    7. Open index in browser
"""

import os
import sys
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from data import DofusAPIClient, CacheManager, EquipmentLoader
from models import Equipment
from processing import RuneMaster, ProcessingConfig
from visualization import HTMLGenerator


def load_equipment() -> tuple:
    """Load equipment from API with caching.

    Returns:
        Tuple of (List[Equipment], CacheManager, DofusAPIClient)
    """
    print("\n" + "="*60)
    print("📦 LOADING EQUIPMENT")
    print("="*60)

    # Initialize cache and API
    cache = CacheManager(cache_file=Config.CACHE_FILE)
    api = DofusAPIClient()
    loader = EquipmentLoader(cache=cache)

    # Load equipments
    print(f"\n📡 Fetching equipment from API...")
    start_time = time.time()

    try:
        raw_equipments = api.get_all_equipments()
        equipments = loader.from_raw_batch(raw_equipments)
    except Exception as e:
        print(f"\n❌ Error loading equipment: {e}")
        print("Make sure DofusAPI is accessible: https://api.dofusdu.de")
        raise

    elapsed = time.time() - start_time
    print(f"\n✅ Loaded {len(equipments)} equipments in {elapsed:.2f}s")

    # Pre-fetch and cache all resources from equipment recipes
    _cache_equipment_resources(equipments, cache, api)

    return equipments, cache, api


def _cache_equipment_resources(equipments: List[Equipment], cache: CacheManager, api: DofusAPIClient) -> None:
    """Extract and cache all resources from equipment recipes.
    
    This ensures all resource names are cached for quick lookups during processing.
    First run: fetches from API and caches (~1-2 min for ~200 resources)
    Subsequent runs: uses cache (fast)
    
    Args:
        equipments: List of Equipment objects
        cache: CacheManager instance
        api: DofusAPIClient instance
    """
    # Collect all unique resource IDs
    resource_ids = set()
    for eq in equipments:
        for req in eq.recipe:
            resource_ids.add(req.resource_id)
    
    # Check cache stats before
    stats_before = cache.get_stats()
    cached_before = stats_before['cached_resources']
    total_resources = len(resource_ids)
    uncached = total_resources - cached_before
    
    if uncached <= 0:
        print(f"\n✅ All {total_resources} resources already cached")
        return
    
    print(f"\n📚 Caching {uncached} resources ({cached_before}/{total_resources} already cached)...")
    start_time = time.time()
    
    fetched = 0
    for i, resource_id in enumerate(resource_ids, 1):
        # Skip if already cached
        if cache.has_resource(resource_id):
            continue
        
        try:
            resource_data = api.get_resource(resource_id)
            if resource_data:
                cache.set_resource(resource_id, resource_data)
                fetched += 1
                
                # Progress indicator
                if fetched % 20 == 0:
                    print(f"   ⏳ Cached {fetched}/{uncached} resources...")
        except Exception as e:
            print(f"   ⚠️  Failed to cache resource {resource_id}: {e}")
            continue
    
    elapsed = time.time() - start_time
    cache.save()
    print(f"✅ Cached {fetched} new resources in {elapsed:.2f}s")


def process_equipment(equipments: List[Equipment], cache_manager=None, api_client=None) -> List[dict]:
    """Run RuneMaster processing pipeline.

    Args:
        equipments: List of Equipment objects
        cache_manager: Optional CacheManager for resource name lookup
        api_client: Optional API client to fetch resource names

    Returns:
        List of equipment groups
    """
    print("\n" + "="*60)
    print("⚙️  PROCESSING EQUIPMENT")
    print("="*60)

    # Create processing configuration
    config = ProcessingConfig(
        graph_min_shared_ratio=0.2,
        graph_min_component_size=2,
        algorithm="louvain",
        resolution_range=(1, 10, 1),
        group_min_size=2,
        group_max_size=18,
        group_min_shared_resources=2,
        group_efficiency_threshold=0.15,
        use_inclusive_mapping=False,
        use_resource_optimizer=False,
        excluded_resource_ids=set(Config.EXCLUDED_RESOURCES or []),
    )

    # Run pipeline
    master = RuneMaster(equipments, config=config, cache_manager=cache_manager, api_client=api_client)
    groups = master.run_all()
    master.print_summary()

    return groups


def generate_visualizations(groups: List[dict], output_dir: str = "visualizations") -> str:
    """Generate HTML visualizations for equipment groups.

    Args:
        groups: List of equipment groups from RuneMaster
        output_dir: Directory to save HTML files

    Returns:
        Path to index.html
    """
    print("\n" + "="*60)
    print("🎨 GENERATING VISUALIZATIONS")
    print("="*60)

    gen = HTMLGenerator(output_dir=output_dir)

    print(f"\n📝 Generating {len(groups)} group pages...")
    start_time = time.time()

    try:
        file_paths = gen.generate_all(groups)
    except Exception as e:
        print(f"\n❌ Error generating visualizations: {e}")
        raise

    elapsed = time.time() - start_time

    # Get file sizes
    total_size = sum(os.path.getsize(f) for f in file_paths) / (1024 * 1024)

    print(f"\n✅ Generated {len(file_paths)} HTML files ({total_size:.2f} MB) in {elapsed:.2f}s")

    # Return path to index
    index_path = os.path.join(output_dir, "index.html")
    return index_path


def start_server(port: int = 8000) -> tuple:
    """Start HTTP server to serve visualizations.

    Args:
        port: Port to listen on

    Returns:
        Tuple of (server, thread)
    """
    print("\n" + "="*60)
    print("🌐 STARTING WEB SERVER")
    print("="*60)

    # Change to visualizations directory for serving files
    visualizations_dir = os.path.join(PROJECT_ROOT, "visualizations")
    os.chdir(visualizations_dir)

    class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
        """Suppress logging for favicon.ico requests."""

        def log_message(self, format, *args):
            # Check if it's the path argument (first positional arg)
            if args and isinstance(args[0], str):
                if "favicon.ico" not in args[0]:
                    super().log_message(format, *args)
            else:
                # Not a string argument, just log it
                super().log_message(format, *args)

    server = HTTPServer(("127.0.0.1", port), QuietHTTPRequestHandler)

    print(f"\n🚀 Server running at: http://127.0.0.1:{port}/")
    print(f"   View in browser: http://127.0.0.1:{port}/index.html")

    return server


def main():
    """Main entry point."""
    print("\n")
    print(" ╔══════════════════════════════════════════════════════╗")
    print(" ║           🔥 RUNEMASTER - GROUP DISCOVERY 🔥        ║")
    print(" ║                                                      ║")
    print(" ║  Equipment Analysis & Visualization Pipeline        ║")
    print(" ╚══════════════════════════════════════════════════════╝")
    print("\n")

    # Step 1: Load equipment
    try:
        equipments, cache_manager, api_client = load_equipment()
    except Exception as e:
        print(f"\n❌ Failed to load equipment. Exiting.")
        sys.exit(1)

    # Step 2: Process equipment
    try:
        groups = process_equipment(equipments, cache_manager=cache_manager, api_client=api_client)
    except Exception as e:
        print(f"\n❌ Failed to process equipment. Exiting.")
        sys.exit(1)

    if not groups:
        print("\n⚠️  No groups were generated. Exiting.")
        sys.exit(1)

    # Step 3: Generate visualizations
    try:
        index_path = generate_visualizations(groups)
    except Exception as e:
        print(f"\n❌ Failed to generate visualizations. Exiting.")
        sys.exit(1)

    # Step 4: Start server and open browser
    try:
        import threading

        server = start_server(port=8000)

        # Start server in background thread
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        # Open browser
        browser_url = f"http://127.0.0.1:8000/index.html"
        print(f"\n📖 Opening in browser: {browser_url}")
        time.sleep(1)  # Give server time to start
        webbrowser.open(browser_url)

        # Keep server running
        print("\n✅ Press Ctrl+C to stop the server\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down server...")
            server.shutdown()

    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
