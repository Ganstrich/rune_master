import time
from typing import List

from data import CacheManager, DofusAPIClient
from models import Equipment


def cache_equipment_resources(
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
    for resource_id in resource_ids:
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
