import os
import time
from typing import List, Tuple

from config import Config
from data import CacheManager, DofusAPIClient, EquipmentLoader
from data.cache_manager_utils import cache_equipment_resources
from models import Equipment
from processing import ProcessingConfig, RuneMaster
from processing.tuner import ParameterTuner
from visualization import HTMLGenerator


def load_equipment(processing_config: ProcessingConfig) -> Tuple:
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

    # Pre-fetch and cache all resources from equipment recipes.
    cache_equipment_resources(equipments, cache, api)

    return equipments, cache, api


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


def run_pipeline(
    config: ProcessingConfig,
    tune: bool = False,
    output_dir: str = "visualizations",
    cache_manager=None,
    api_client=None,
):
    """Orchestrate the high-level pipeline steps."""
    # This assumes dependencies are passed in or created locally.
    # To keep it simple for now, we'll follow the existing logic structure.

    # We need to bridge the gap between main.py, load_equipment, etc.
    # For now, let's just create a wrapper that calls the existing functions.
    equipments, cache, api = load_equipment(config)
    groups = process_equipment(equipments, config, cache, api, tune)
    if not groups:
        raise ValueError("No groups generated")

    index_path = generate_visualizations(groups, output_dir)
    return index_path
