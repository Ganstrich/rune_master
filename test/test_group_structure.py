"""Tests for group structure validation.

Ensures both deterministic and random grouping methods produce
complete group objects with all required attributes.
"""

import pytest
from typing import Dict, List, Any
from models import Equipment, ResourceRequirement
from processing.equipment_filter import EquipmentFilteringStrategy
from processing.random_group_builder import RandomGroupBuilder


# Required fields for ALL groups
REQUIRED_FIELDS = {
    "equipments": (list, "List of Equipment objects"),
    "shared_resources_count": (int, "Number of shared resources"),
    "total_shared_resources": (set, "Set of shared resource IDs"),
    "sharing_efficiency": (float, "Efficiency ratio 0-1"),
    "average_density": (float, "Average stat weight / level"),
    "total_ingredients": (dict, "Aggregated resources with details"),
    "unique_ingredients_count": (int, "Count of unique resources"),
    "total_items_needed": (int, "Total quantity needed"),
}

# Required fields for random groups
RANDOM_ONLY_FIELDS = {
    "selection_method": (str, "How group was selected"),
    "seed_equipment_id": (int, "ID of seed equipment"),
    "randomness_seed": (int or None, "RNG seed for reproducibility"),
}


@pytest.fixture
def test_equipments():
    """Create test Equipment objects."""
    def create_test_equipment(ankama_id: int, level: int, stat_weight: float = 50.0):
        return Equipment(
            ankama_id=ankama_id,
            type={"id": 1, "name": "sword"},
            level=level,
            name=f"Test Equipment {ankama_id}",
            stat_weight=stat_weight,
            recipe=[
                ResourceRequirement(resource_id=100 + ankama_id, quantity=5),
                ResourceRequirement(resource_id=200, quantity=2),
            ],
        )
    
    return [create_test_equipment(i, 20 + i * 2, 15 + i * 2) for i in range(1, 6)]


def verify_group_structure(group: Dict[str, Any], is_random: bool = False):
    """Verify a group has all required fields.

    Args:
        group: Group dict to verify
        is_random: Whether this is a random group (has extra fields)

    Raises:
        AssertionError if any required field is missing or wrong type
    """
    # Check required fields
    for field_name, (expected_type, description) in REQUIRED_FIELDS.items():
        assert field_name in group, f"Missing required field: {field_name} ({description})"

        value = group[field_name]
        if field_name == "total_shared_resources":
            assert isinstance(value, set), f"{field_name} must be set, got {type(value)}"
        elif field_name == "sharing_efficiency":
            assert isinstance(value, (int, float)), f"{field_name} must be numeric, got {type(value)}"
            assert value >= 0.0, f"{field_name} must be >= 0, got {value}"
            assert value <= 1.0, f"{field_name} must be <= 1, got {value}"
        elif field_name == "average_density":
            assert isinstance(value, (int, float)), f"{field_name} must be numeric, got {type(value)}"
        elif field_name == "total_ingredients":
            assert isinstance(value, dict), f"{field_name} must be dict, got {type(value)}"
            # Validate ingredient structure
            for resource_id, ingredient_info in value.items():
                assert isinstance(ingredient_info, dict), \
                    f"Each ingredient must be dict, got {type(ingredient_info)}"
                assert "name" in ingredient_info, f"Ingredient {resource_id} missing 'name'"
                assert "total_quantity" in ingredient_info, \
                    f"Ingredient {resource_id} missing 'total_quantity'"
                assert "quantity_per_equipment" in ingredient_info, \
                    f"Ingredient {resource_id} missing 'quantity_per_equipment'"
                assert isinstance(ingredient_info["quantity_per_equipment"], dict), \
                    f"quantity_per_equipment must be dict"
        else:
            assert isinstance(value, expected_type), \
                f"{field_name} wrong type: expected {expected_type.__name__}, got {type(value).__name__}"

    # Check random-specific fields
    if is_random:
        for field_name, (expected_type, description) in RANDOM_ONLY_FIELDS.items():
            assert field_name in group, \
                f"Missing random-specific field: {field_name} ({description})"

            if field_name == "selection_method":
                assert group[field_name] == "random", f"selection_method must be 'random'"


def test_random_group_builder_produces_complete_structure(test_equipments):
    """Test RandomGroupBuilder produces complete group structure."""
    builder = RandomGroupBuilder(equipments=test_equipments, seed=42)
    groups = builder.build_multiple_random_groups(
        equipment_pool=test_equipments,
        count=3,
        min_shared_resources=1,
        max_group_size=5,
    )

    assert len(groups) > 0, "Should generate at least one group"

    # Verify each group
    for group in groups:
        verify_group_structure(group, is_random=True)
        assert group["selection_method"] == "random"
        assert group["seed_equipment_id"] is not None
        assert group["seed_equipment_id"] > 0


def test_random_group_has_all_required_fields(test_equipments):
    """Test that random groups don't remove any fields from required set."""
    builder = RandomGroupBuilder(equipments=test_equipments)
    group = builder.build_random_group(
        equipment_pool=test_equipments,
        min_shared_resources=1,
        max_group_size=5,
    )

    # Check all required fields exist
    missing_fields = [
        field_name for field_name in REQUIRED_FIELDS.keys()
        if field_name not in group
    ]

    assert missing_fields == [], f"Group missing required fields: {missing_fields}"


def test_total_ingredients_has_correct_nested_structure(test_equipments):
    """Test that total_ingredients has full nested structure."""
    builder = RandomGroupBuilder(equipments=test_equipments)
    group = builder.build_random_group(
        equipment_pool=test_equipments,
        min_shared_resources=1,
    )

    ingredients = group["total_ingredients"]
    assert isinstance(ingredients, dict)

    for resource_id, ingredient_info in ingredients.items():
        # Check all required sub-fields
        required_keys = {"name", "total_quantity", "quantity_per_equipment"}
        actual_keys = set(ingredient_info.keys())

        assert required_keys.issubset(actual_keys), \
            f"Resource {resource_id} missing keys. Expected {required_keys}, got {actual_keys}"

        # Validate types
        assert isinstance(ingredient_info["name"], str)
        assert isinstance(ingredient_info["total_quantity"], int)
        assert isinstance(ingredient_info["quantity_per_equipment"], dict)


def test_shared_resources_count_matches_set_size(test_equipments):
    """Test that shared_resources_count matches total_shared_resources."""
    builder = RandomGroupBuilder(equipments=test_equipments)
    group = builder.build_random_group(
        equipment_pool=test_equipments,
        min_shared_resources=1,
    )

    # Count should match set
    actual_count = group["shared_resources_count"]
    expected_count = len(group["total_shared_resources"])

    assert actual_count == expected_count, \
        f"shared_resources_count ({actual_count}) doesn't match len(total_shared_resources) ({expected_count})"


def test_unique_ingredients_count_consistency(test_equipments):
    """Test that unique_ingredients_count matches total_ingredients dict size."""
    builder = RandomGroupBuilder(equipments=test_equipments)
    group = builder.build_random_group(
        equipment_pool=test_equipments,
        min_shared_resources=1,
    )

    actual_count = group["unique_ingredients_count"]
    expected_count = len(group["total_ingredients"])

    assert actual_count == expected_count, \
        f"unique_ingredients_count ({actual_count}) doesn't match len(total_ingredients) ({expected_count})"


def test_total_items_needed_matches_sum(test_equipments):
    """Test that total_items_needed matches sum of quantities."""
    builder = RandomGroupBuilder(equipments=test_equipments)
    group = builder.build_random_group(
        equipment_pool=test_equipments,
        min_shared_resources=1,
    )

    actual_total = group["total_items_needed"]
    expected_total = sum(
        ing["total_quantity"]
        for ing in group["total_ingredients"].values()
    )

    assert actual_total == expected_total, \
        f"total_items_needed ({actual_total}) doesn't match sum of quantities ({expected_total})"


def test_efficiency_calculation_is_correct(test_equipments):
    """Test that sharing_efficiency is calculated correctly.
    
    Efficiency = shared_resources_count / total_unique_resources_count
    This represents the fraction of unique resources that are shared across all equipment.
    Matches GroupMapper formula for consistency and exploration purposes.
    """
    builder = RandomGroupBuilder(equipments=test_equipments)
    group = builder.build_random_group(
        equipment_pool=test_equipments,
        min_shared_resources=1,
    )

    efficiency = group["sharing_efficiency"]
    shared_count = group["shared_resources_count"]
    unique_count = group["unique_ingredients_count"]

    if unique_count > 0:
        expected_efficiency = shared_count / unique_count
        assert abs(efficiency - expected_efficiency) < 1e-5, \
            f"Efficiency calculation mismatch: expected {expected_efficiency}, got {efficiency}"


def test_average_density_calculation_is_correct(test_equipments):
    """Test that average_density is calculated correctly."""
    builder = RandomGroupBuilder(equipments=test_equipments)
    group = builder.build_random_group(
        equipment_pool=test_equipments,
        min_shared_resources=1,
    )

    avg_density = group["average_density"]
    equipments_in_group = group["equipments"]

    # Calculate expected average density
    if equipments_in_group:
        densities = [
            eq.stat_weight / eq.level
            for eq in equipments_in_group
            if eq.level > 0
        ]
        expected_avg = sum(densities) / len(densities) if densities else 0

        assert abs(avg_density - expected_avg) < 1e-5, \
            f"Average density calculation mismatch: expected {expected_avg}, got {avg_density}"


def test_equipment_filtering_preserves_integrity():
    """Test that filtering doesn't corrupt Equipment objects."""
    equipments = [
        Equipment(
            ankama_id=i,
            type={"id": 1, "name": "sword"},
            level=20 + i * 5,
            name=f"Equipment {i}",
            stat_weight=10.0 + i * 2,
            recipe=[
                ResourceRequirement(resource_id=100, quantity=5),
                ResourceRequirement(resource_id=200, quantity=3),
            ],
        )
        for i in range(1, 11)
    ]

    filtered, excluded = EquipmentFilteringStrategy.filter_by_density_ratio(
        equipments, ratio=0.15
    )

    # All filtered equipment should be valid
    for eq in filtered:
        assert isinstance(eq, Equipment)
        assert eq.ankama_id > 0
        assert eq.level > 0
        assert eq.stat_weight is not None

    # All excluded equipment should be valid
    for eq in excluded:
        assert isinstance(eq, Equipment)
        assert eq.ankama_id > 0
