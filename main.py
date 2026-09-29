#!/usr/bin/env python3
"""Main entry point for RuneMaster equipment group discovery and visualization.

Pipeline:
    1. Load configuration
    2. Fetch equipment from DofusAPI
    3. Transform equipment to dataclasses (with caching)
    4. Run RuneMaster processing pipeline
    5. Generate visualizations
    6. Start HTTP server (optional)
"""

import os
import sys
import time
import argparse
import webbrowser
from dataclasses import replace
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
from processing.tuner import ParameterTuner
from visualization import HTMLGenerator


def positive_int(value: str) -> int:
    """Parse a strictly positive integer CLI argument."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def nonnegative_float(value: str) -> float:
    """Parse a non-negative floating-point CLI argument."""
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def load_equipment(processing_config: ProcessingConfig) -> tuple:
    """Load equipment from API with caching."""
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
        equipments = loader.from_raw_batch(raw_equipments, processing_config=processing_config)
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
    """Extract and cache all resources from equipment recipes."""
    resource_ids = set()
    for eq in equipments:
        for req in eq.recipe:
            resource_ids.add(req.resource_id)
    
    cached_before = sum(cache.has_resource(resource_id) for resource_id in resource_ids)
    total_resources = len(resource_ids)
    uncached = total_resources - cached_before
    
    if uncached <= 0:
        print(f"\n✅ All {total_resources} resources already cached")
        return
    
    print(f"\n📚 Caching {uncached} resources ({cached_before}/{total_resources} already cached)...")
    start_time = time.time()
    
    fetched = 0
    failed: List[int] = []
    for resource_id in resource_ids:
        if cache.has_resource(resource_id):
            continue
        
        try:
            resource_data = api.get_resource(resource_id)
            if isinstance(resource_data, dict) and resource_data.get("name"):
                cache.set_resource(resource_id, resource_data)
                fetched += 1
                if fetched % 20 == 0:
                    print(f"   ⏳ Cached {fetched}/{uncached} resources...")
            else:
                failed.append(resource_id)
        except Exception as e:
            failed.append(resource_id)
            print(f"   ⚠️  Failed to cache resource {resource_id}: {e}")
    
    elapsed = time.time() - start_time
    cache.save()
    print(f"✅ Cached {fetched} new resources in {elapsed:.2f}s")
    if failed:
        print(f"⚠️  Failed resources ({len(failed)}): {sorted(failed)}")


def process_equipment(
    equipments: List[Equipment],
    processing_config: ProcessingConfig,
    cache_manager=None,
    api_client=None,
    tune_params: bool = False,
) -> List[dict]:
    """Run RuneMaster processing pipeline."""
    print("\n" + "="*60)
    print("⚙️  PROCESSING EQUIPMENT")
    print("="*60)

    if tune_params:
        tuner = ParameterTuner(equipments, cache_manager, api_client)
        tuned_config, _ = tuner.tune(method=processing_config.grouping_method)
        config = replace(
            processing_config,
            graph_min_shared_ratio=tuned_config.graph_min_shared_ratio,
            group_min_shared_resources=tuned_config.group_min_shared_resources,
        )
    else:
        config = processing_config

    master = RuneMaster(equipments, config=config, cache_manager=cache_manager, api_client=api_client)

    print(f"\n📋 Grouping Method: {config.grouping_method.upper()}")
    if tune_params:
        print(f"📊 Using Tuned Parameters: Ratio={config.graph_min_shared_ratio}, MinItems={config.group_min_shared_resources}")

    if config.grouping_method == "random":
        groups = master.run_random_grouping()
    elif config.grouping_method == "hybrid":
        groups = master.run_hybrid_grouping()
    elif config.grouping_method == "committee":
        groups = master.run_committee()
    elif config.grouping_method == "genetic":
        groups = master.run_genetic_grouping()
    else:
        groups = master.run_all()

    master.print_summary()
    return groups


def generate_visualizations(groups: List[dict], output_dir: str = "visualizations") -> str:
    """Generate HTML visualizations for equipment groups."""
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
    total_size = sum(os.path.getsize(f) for f in file_paths) / (1024 * 1024)
    print(f"\n✅ Generated {len(file_paths)} HTML files ({total_size:.2f} MB) in {elapsed:.2f}s")

    return os.path.join(output_dir, "index.html")


def start_server(port: int = 8000) -> tuple:
    """Start HTTP server to serve visualizations."""
    print("\n" + "="*60)
    print("🌐 STARTING WEB SERVER")
    print("="*60)

    visualizations_dir = os.path.join(PROJECT_ROOT, "visualizations")
    os.chdir(visualizations_dir)

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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="RuneMaster: Equipment Group Discovery")
    parser.add_argument("--grouping-method", choices=["deterministic", "random", "hybrid", "committee", "genetic"])
    parser.add_argument(
        "--random-groups",
        type=positive_int,
        help="Number of random groups to generate",
    )
    parser.add_argument(
        "--density-ratio",
        type=nonnegative_float,
        help="Density/level ratio filter",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        help="Seed for reproducible random grouping",
    )
    parser.add_argument("--tune", action="store_true", help="Search for best grouping parameters")
    parser.add_argument("--no-serve", action="store_true", help="Generate reports without starting server")
    args = parser.parse_args()

    print("\n 🔥 RUNEMASTER - GROUP DISCOVERY 🔥 \n")

    # ProcessingConfig owns pipeline defaults; CLI arguments override them.
    processing_config = ProcessingConfig()
    if args.grouping_method is not None:
        processing_config.grouping_method = args.grouping_method
    if args.random_groups is not None:
        processing_config.random_group_count = args.random_groups
    if args.density_ratio is not None:
        processing_config.equipment_density_level_ratio = args.density_ratio
    if args.random_seed is not None:
        processing_config.random_seed = args.random_seed

    try:
        equipments, cache_manager, api_client = load_equipment(processing_config)
        groups = process_equipment(
            equipments, processing_config, cache_manager, api_client, args.tune
        )
        
        if not groups:
            print("\n⚠️  No groups generated.")
            sys.exit(1)

        index_path = generate_visualizations(groups)

        if args.no_serve:
            print(f"\n✅ Report ready at: {os.path.abspath(index_path)}")
            print("🚀 Dashboard update complete. Refresh your browser.")
            return

        import threading
        server = start_server(port=8000)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        
        browser_url = f"http://127.0.0.1:8000/index.html"
        print(f"\n📖 Opening in browser: {browser_url}")
        time.sleep(1)
        webbrowser.open(browser_url)

        print("\n✅ Press Ctrl+C to stop the server\n")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            server.shutdown()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
