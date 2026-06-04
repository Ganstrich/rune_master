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

import argparse
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
from data import CacheManager, DofusAPIClient, EquipmentLoader
from models import Equipment
from processing import ProcessingConfig, RuneMaster
from processing.tuner import ParameterTuner
from visualization import HTMLGenerator


def load_equipment(processing_config: ProcessingConfig) -> tuple:
    """Load equipment from API with caching."""
    print("\n" + "=" * 60)
    print("📦 LOADING EQUIPMENT")
    print("=" * 60)

    # Initialize cache and API
    cache = CacheManager(cache_file=Config.CACHE_FILE)
    api = DofusAPIClient()
    loader = EquipmentLoader(cache=cache)

    # Load equipments
    print(f"\n📡 Fetching equipment from API...")
    start_time = time.time()

    try:
        raw_equipments = api.get_all_equipments()
        equipments = loader.from_raw_batch(
            raw_equipments, processing_config=processing_config
        )
    except Exception as e:
        print(f"\n❌ Error loading equipment: {e}")
        print("Make sure DofusAPI is accessible: https://api.dofusdu.de")
        raise

    elapsed = time.time() - start_time
    print(f"\n✅ Loaded {len(equipments)} equipments in {elapsed:.2f}s")

    # Pre-fetch and cache all resources from equipment recipes
    _cache_equipment_resources(equipments, cache, api)

    return equipments, cache, api


def _cache_equipment_resources(
    equipments: List[Equipment], cache: CacheManager, api: DofusAPIClient
) -> None:
    """Extract and cache all resources from equipment recipes."""
    resource_ids = set()
    for eq in equipments:
        for req in eq.recipe:
            resource_ids.add(req.resource_id)

    stats_before = cache.get_stats()
    cached_before = stats_before["cached_resources"]
    total_resources = len(resource_ids)
    uncached = total_resources - cached_before

    if uncached <= 0:
        print(f"\n✅ All {total_resources} resources already cached")
        return

    print(
        f"\n📚 Caching {uncached} resources ({cached_before}/{total_resources} already cached)..."
    )
    start_time = time.time()

    fetched = 0
    for i, resource_id in enumerate(resource_ids, 1):
        if cache.has_resource(resource_id):
            continue

        try:
            resource_data = api.get_resource(resource_id)
            if resource_data:
                cache.set_resource(resource_id, resource_data)
                fetched += 1
                if fetched % 20 == 0:
                    print(f"   ⏳ Cached {fetched}/{uncached} resources...")
        except Exception as e:
            print(f"   ⚠️  Failed to cache resource {resource_id}: {e}")
            continue

    elapsed = time.time() - start_time
    cache.save()
    print(f"✅ Cached {fetched} new resources in {elapsed:.2f}s")


def process_equipment(
    equipments: List[Equipment],
    processing_config: ProcessingConfig,
    cache_manager=None,
    api_client=None,
    tune_params: bool = False,
) -> List[dict]:
    """Run RuneMaster processing pipeline."""
    print("\n" + "=" * 60)
    print("⚙️  PROCESSING EQUIPMENT")
    print("=" * 60)

    if tune_params:
        tuner = ParameterTuner(equipments, cache_manager, api_client)
        config, _ = tuner.tune(method=processing_config.grouping_method)
        config.grouping_method = processing_config.grouping_method
        config.random_group_count = processing_config.random_group_count
        config.equipment_density_level_ratio = (
            processing_config.equipment_density_level_ratio
        )
        config.min_equipment_density = processing_config.min_equipment_density
    else:
        config = processing_config

    master = RuneMaster(
        equipments, config=config, cache_manager=cache_manager, api_client=api_client
    )

    print(f"\n📋 Grouping Method: {config.grouping_method.upper()}")
    if tune_params:
        print(
            f"📊 Using Tuned Parameters: Ratio={config.graph_min_shared_ratio}, MinItems={config.group_min_shared_resources}"
        )

    if config.grouping_method == "random":
        groups = master.run_random_grouping()
    elif config.grouping_method == "hybrid":
        groups = master.run_hybrid_grouping()
    elif config.grouping_method == "committee":
        groups = master.run_committee()
    elif config.grouping_method == "genetic":
        expert = master.experts["genetic"]
        groups = expert.discover_groups(equipments, config)
    else:
        groups = master.run_all()

    master.print_summary()
    return groups


def generate_visualizations(
    groups: List[dict], output_dir: str = "visualizations"
) -> str:
    """Generate HTML visualizations for equipment groups."""
    print("\n" + "=" * 60)
    print("🎨 GENERATING VISUALIZATIONS")
    print("=" * 60)

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
    print(
        f"\n✅ Generated {len(file_paths)} HTML files ({total_size:.2f} MB) in {elapsed:.2f}s"
    )

    return os.path.join(output_dir, "index.html")


def start_server(port: int = 8000) -> tuple:
    """Start HTTP server to serve visualizations."""
    print("\n" + "=" * 60)
    print("🌐 STARTING WEB SERVER")
    print("=" * 60)

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
    parser = argparse.ArgumentParser(
        description="RuneMaster: Equipment Group Discovery"
    )
    parser.add_argument(
        "--grouping-method",
        choices=["deterministic", "random", "hybrid", "committee", "genetic"],
    )
    parser.add_argument(
        "--random-groups", type=int, help="Number of random groups to generate"
    )
    parser.add_argument(
        "--density-ratio", type=float, help="Density/level ratio filter"
    )
    parser.add_argument(
        "--tune", action="store_true", help="Search for best grouping parameters"
    )
    parser.add_argument(
        "--no-serve",
        action="store_true",
        help="Generate reports without starting server",
    )
    args = parser.parse_args()

    print("\n 🔥 RUNEMASTER - GROUP DISCOVERY 🔥 \n")

    # Build ProcessingConfig from CLI args + defaults
    processing_config = ProcessingConfig(
        graph_min_shared_ratio=Config.MIN_SIMILARITY,
        graph_min_component_size=Config.MIN_CLUSTER_SIZE,
        algorithm="louvain",
        resolution_range=(1, 10, 1),
        group_min_size=Config.MIN_CLUSTER_SIZE,
        group_max_size=18,
        group_min_shared_resources=Config.MIN_COMMON_ITEMS,
        group_efficiency_threshold=0.15,
        use_inclusive_mapping=False,
        excluded_resource_ids=set(Config.EXCLUDED_RESOURCES or []),
        use_density_filtering=True,
        equipment_density_level_ratio=args.density_ratio or Config.DENSITY_LEVEL_RATIO,
        fallback_to_unfiltered=Config.FALLBACK_TO_UNFILTERED,
        min_filtered_pool_size=Config.MIN_FILTERED_POOL_SIZE,
        grouping_method=args.grouping_method or Config.GROUPING_METHOD,
        random_group_count=args.random_groups or Config.RANDOM_GROUP_COUNT,
        random_seed=None,
        min_equipment_density=Config.MIN_EQUIPMENT_DENSITY,
    )

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
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.shutdown()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
