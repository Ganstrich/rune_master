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
import json
import webbrowser
from dataclasses import asdict, is_dataclass, replace
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from config import ALL_CRAFTABLE_TYPES, Config
from data import DofusAPIClient, CacheManager, EquipmentLoader
from models import Equipment
from processing import RuneMaster, ProcessingConfig
from processing.job_filter import JobLevelFilter
from processing.tuner import ParameterTuner
from visualization import HTMLGenerator

JOB_LEVEL_JOBS = set(JobLevelFilter.JOB_TO_TYPES)
PLAYER_CONFIG_PATH = PROJECT_ROOT / "player_config.json"


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


def item_types(value: str) -> list[str]:
    """Parse a comma-separated list of supported craftable item types."""
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    unsupported = sorted(set(parsed) - set(ALL_CRAFTABLE_TYPES))
    if not parsed or unsupported:
        choices = ", ".join(ALL_CRAFTABLE_TYPES)
        detail = f" unsupported: {', '.join(unsupported)}." if unsupported else ""
        raise argparse.ArgumentTypeError(f"item types must be from {choices}.{detail}")
    if len(parsed) != len(set(parsed)):
        raise argparse.ArgumentTypeError("item types must not contain duplicates")
    return parsed


def validate_scope(min_level: int, max_level: int, selected_types: list[str]) -> None:
    """Validate cross-field scope constraints before network work begins."""
    if min_level > max_level:
        raise ValueError("--min-level must be less than or equal to --max-level")
    if not selected_types:
        raise ValueError("at least one item type is required")


def job_levels(value: str) -> dict[str, int]:
    """Parse a comma-separated ``job:level`` mapping."""
    from processing.job_filter import JobLevelFilter

    try:
        return JobLevelFilter.parse_job_levels(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def load_player_config(path: Path) -> dict:
    """Load the optional persistent player configuration file.

    A missing or unreadable file is not fatal: the caller falls back to
    defaults. Malformed JSON or a missing ``job_levels`` mapping is reported
    so a typo cannot silently disable filtering.
    """
    if not path.exists():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"⚠️  Ignoring unreadable {path}: {error}")
        return {}
    if not isinstance(config, dict):
        print(f"⚠️  Ignoring {path}: expected a JSON object")
        return {}
    levels = config.get("job_levels", {})
    if not isinstance(levels, dict):
        print(f"⚠️  Ignoring {path}: 'job_levels' must be a JSON object")
        return {}
    return config


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser separately so scope validation stays offline-testable."""
    parser = argparse.ArgumentParser(description="RuneMaster: Equipment Group Discovery")
    parser.add_argument(
        "--grouping-method",
        choices=[
            "deterministic",
            "random",
            "hybrid",
            "committee",
            "genetic",
            "greedy",
            "evolutionary_committee",
            "survey",
        ],
    )
    parser.add_argument("--random-groups", type=positive_int, help="Number of random groups to generate")
    parser.add_argument("--density-ratio", type=nonnegative_float, help="Density/level ratio filter")
    parser.add_argument("--random-seed", type=int, help="Seed for reproducible random grouping")
    parser.add_argument("--min-level", type=positive_int, default=Config.MIN_LEVEL)
    parser.add_argument("--max-level", type=positive_int, default=Config.MAX_LEVEL)
    parser.add_argument("--item-types", type=item_types, default=list(Config.ITEM_TYPES))
    parser.add_argument("--tune", action="store_true", help="Search for best grouping parameters")
    parser.add_argument("--no-serve", action="store_true", help="Generate reports without starting server")
    parser.add_argument(
        "--job-levels",
        type=job_levels,
        metavar="JOB:LEVEL[,...]",
        help=(
            "Crafting job levels, e.g. 'forgeron:120,bijoutier:80'. "
            f"Jobs: {', '.join(sorted(JOB_LEVEL_JOBS))}. "
            "Enables craftability filtering; overrides player_config.json."
        ),
    )
    parser.add_argument(
        "--no-job-filter",
        action="store_true",
        help="Ignore configured job levels and keep the full equipment pool",
    )
    return parser


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    """Parse and validate CLI arguments without invoking the network."""
    parser = build_parser()
    args = parser.parse_args(arguments)
    try:
        validate_scope(args.min_level, args.max_level, args.item_types)
    except ValueError as error:
        parser.error(str(error))
    return args


def load_equipment(
    processing_config: ProcessingConfig, scope: dict[str, Any] | None = None
) -> tuple:
    """Load equipment from API with caching."""
    print("\n" + "="*60)
    print("📦 LOADING EQUIPMENT")
    print("="*60)

    effective_scope = scope or {
        "min_level": Config.MIN_LEVEL,
        "max_level": Config.MAX_LEVEL,
        "item_types": list(Config.ITEM_TYPES),
    }
    print(
        f"\n🔎 Scope: levels {effective_scope['min_level']}-{effective_scope['max_level']}; "
        f"types: {', '.join(effective_scope['item_types'])}"
    )

    # Initialize cache and API
    cache = CacheManager(cache_file=Config.CACHE_FILE)
    api = DofusAPIClient()
    loader = EquipmentLoader(cache=cache, set_index=_load_set_index(cache, api))

    # Load equipments
    print(f"\n📡 Fetching equipment from API...")
    start_time = time.time()

    try:
        raw_equipments = api.get_all_equipments(
            item_types=effective_scope["item_types"],
            min_level=effective_scope["min_level"],
            max_level=effective_scope["max_level"],
        )
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


def _load_set_index(cache: CacheManager, api: DofusAPIClient) -> dict[int, int]:
    """Return the equipment → panoplie map, fetching it once per cache lifetime."""
    index = cache.get_equipment_set_index()
    if index:
        return index
    index = api.get_equipment_set_index()
    if index:
        cache.set_equipment_set_index(index)
    return index


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
        api.resource_cache_status = {
            **cache.get_resource_cache_status(resource_ids),
            "status": "complete",
            "failed_ids": [],
        }
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
    api.resource_cache_status = {
        **cache.get_resource_cache_status(resource_ids),
        "status": "degraded" if failed else "complete",
        "failed_ids": sorted(failed),
    }


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
        groups = master.run_genetic()
    elif config.grouping_method == "greedy":
        groups = master.run_greedy()
    elif config.grouping_method == "survey":
        groups = master.run_survey()
    elif config.grouping_method == "evolutionary_committee":
        groups = master.run_evolutionary_committee()
    else:
        groups = master.run_all()

    master.print_summary()
    return groups


def _json_safe(value: Any) -> Any:
    """Convert configuration values into JSON-compatible primitives."""
    if is_dataclass(value):
        return {key: _json_safe(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (set, tuple, list)):
        return [_json_safe(item) for item in value]
    return value


def apply_job_level_filter(
    equipments: List[Equipment],
    processing_config: ProcessingConfig,
) -> tuple[List[Equipment], dict[str, Any]]:
    """Drop equipment the player's job levels cannot craft.

    Returns (equipments, filter_report). The report is ``{}`` when filtering
    is inactive so callers can omit it from the manifest unchanged.
    """
    if not processing_config.use_job_level_filter:
        return equipments, {}
    if not processing_config.job_levels:
        print("\n⚠️  Job-level filter enabled but no job levels configured — keeping full pool")
        return equipments, {}

    print("\n" + "=" * 60)
    print("🔧 JOB-LEVEL FILTER")
    print("=" * 60)
    craftable, filtered_out = JobLevelFilter.filter_equipments(
        equipments, processing_config.job_levels
    )
    excluded_by_job = JobLevelFilter.summarize_excluded(filtered_out)
    for job, count in sorted(excluded_by_job.items(), key=lambda item: -item[1]):
        print(f"   {job:<12} level {processing_config.job_levels.get(job, '?'):>3}: {count} items filtered")
    print(f"   {'kept':<12} {'':>5} {len(craftable)} items craftable")
    if not craftable:
        print("\n⚠️  No craftable equipment at these job levels — raise levels or widen the level scope")

    return craftable, {
        "job_levels": dict(processing_config.job_levels),
        "kept": len(craftable),
        "filtered_out": len(filtered_out),
        "filtered_by_job": excluded_by_job,
    }


def build_run_manifest(
    processing_config: ProcessingConfig,
    cli_overrides: dict[str, Any],
    scope: dict[str, Any] | None = None,
    cache_status: dict[str, Any] | None = None,
    job_filter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build reproducibility metadata without including API payloads or secrets."""
    effective_scope = scope or {
        "min_level": Config.MIN_LEVEL,
        "max_level": Config.MAX_LEVEL,
        "item_types": list(Config.ITEM_TYPES),
    }
    effective_scope["summary"] = (
        f"Levels {effective_scope['min_level']}-{effective_scope['max_level']}; "
        f"types: {', '.join(effective_scope['item_types'])}"
    )
    return {
        "grouping_method": processing_config.grouping_method,
        "processing_config": _json_safe(processing_config),
        "cli_overrides": _json_safe(cli_overrides),
        "scope": _json_safe(effective_scope),
        "job_filter": _json_safe(job_filter or {"status": "disabled"}),
        "source": {"api": "DofusAPI", "cache": _json_safe(cache_status or {"status": "unavailable"})},
    }


def generate_visualizations(
    groups: List[dict],
    output_dir: str = "visualizations",
    manifest: dict[str, Any] | None = None,
) -> str:
    """Generate HTML visualizations for equipment groups."""
    print("\n" + "="*60)
    print("🎨 GENERATING VISUALIZATIONS")
    print("="*60)

    gen = HTMLGenerator(output_dir=output_dir, manifest=manifest)
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
    args = parse_args()

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

    # Job levels: player_config.json is the baseline, --job-levels overrides
    # individual jobs, --no-job-filter disables filtering entirely.
    player_config = load_player_config(PLAYER_CONFIG_PATH)
    file_job_levels = dict(player_config.get("job_levels") or {})
    unknown = sorted(set(file_job_levels) - JOB_LEVEL_JOBS)
    if unknown:
        print(f"⚠️  Ignoring unknown jobs in {PLAYER_CONFIG_PATH}: {', '.join(unknown)}")
        for job in unknown:
            file_job_levels.pop(job)
    if args.job_levels:
        file_job_levels.update(args.job_levels)
    if file_job_levels and not args.no_job_filter:
        processing_config.use_job_level_filter = True
        processing_config.job_levels = file_job_levels

    scope = {
        "min_level": args.min_level,
        "max_level": args.max_level,
        "item_types": args.item_types,
    }

    try:
        equipments, cache_manager, api_client = load_equipment(processing_config, scope)
        equipments, job_filter_report = apply_job_level_filter(
            equipments, processing_config
        )
        if not equipments:
            print("\n⚠️  No equipment to process after filtering.")
            sys.exit(1)
        groups = process_equipment(
            equipments, processing_config, cache_manager, api_client, args.tune
        )
        
        if not groups:
            print("\n⚠️  No groups generated.")
            sys.exit(1)

        manifest = build_run_manifest(
            processing_config,
            {key: value for key, value in vars(args).items() if value not in (None, False)},
            scope=scope,
            cache_status=getattr(api_client, "resource_cache_status", {"status": "unavailable"}),
            job_filter=job_filter_report,
        )
        index_path = generate_visualizations(groups, manifest=manifest)

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
