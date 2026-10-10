"""Offline tests for the job-level craftability filter."""

import pytest

from models import Equipment, ResourceRequirement
from processing.config import ProcessingConfig
from processing.filters.job_filter import JobLevelFilter

# The DofusDB equipment payload carries a French display name plus a numeric
# id, so the tests use that real shape rather than the API filter's name_id.
FRENCH_TYPES = {
    "ring": {"name": "Anneau", "id": 17},
    "amulet": {"name": "Amulette", "id": 33},
    "bow": {"name": "Arc", "id": 39},
    "hammer": {"name": "Marteau", "id": 42},
    "cloak": {"name": "Cape", "id": 43},
    "boots": {"name": "Bottes", "id": 45},
    "shovel": {"name": "Pelle", "id": 52},
    "belt": {"name": "Ceinture", "id": 58},
    "wand": {"name": "Baguette", "id": 65},
    "axe": {"name": "Hache", "id": 73},
    "sword": {"name": "Épée", "id": 80},
    "shield": {"name": "Bouclier", "id": 87},
    "dagger": {"name": "Dague", "id": 93},
    "lance": {"name": "Lance", "id": 111},
    "staff": {"name": "Bâton", "id": 125},
    "scythe": {"name": "Faux", "id": 163},
    "hat": {"name": "Chapeau", "id": 27},
}


def make_equipment(equipment_id: int, name_id: str, level: int) -> Equipment:
    """Create one minimal equipment record with the real payload type shape."""
    return Equipment(
        ankama_id=equipment_id,
        type=FRENCH_TYPES[name_id],
        level=level,
        name=f"Equipment {equipment_id}",
        stat_weight=100.0,
        recipe=[ResourceRequirement(resource_id=10, quantity=2)],
    )


# --- Mapping ---

def test_every_craftable_type_maps_to_exactly_one_job() -> None:
    """The filter is only trustworthy if the type mapping is total and disjoint."""
    from config import ALL_CRAFTABLE_TYPES

    mapped = set(JobLevelFilter.ITEM_TYPE_IDS)
    assert mapped == set(ALL_CRAFTABLE_TYPES)
    # Each type appears under exactly one job.
    assert sum(len(types) for types in JobLevelFilter.JOB_TO_TYPES.values()) == len(
        ALL_CRAFTABLE_TYPES
    )


def test_resolve_job_accepts_french_payload_name() -> None:
    """The snapshot and live API return French names, not name_ids."""
    assert JobLevelFilter.resolve_job({"name": "Épée", "id": 80}) == "forgeron"
    assert JobLevelFilter.resolve_job({"name": "Anneau", "id": 17}) == "bijoutier"
    assert JobLevelFilter.resolve_job({"name": "Bâton", "id": 125}) == "sculpteur"


def test_resolve_job_accepts_numeric_id_and_name_id() -> None:
    """Numeric id first, then the English name_id, for robustness."""
    assert JobLevelFilter.resolve_job({"id": 80}) == "forgeron"
    assert JobLevelFilter.resolve_job({"name": "sword"}) == "forgeron"


def test_resolve_job_returns_none_for_unknown_type() -> None:
    assert JobLevelFilter.resolve_job({"name": "Familier", "id": 9999}) is None
    assert JobLevelFilter.resolve_job({}) is None


# --- can_craft ---

def test_item_at_exactly_the_job_level_is_craftable() -> None:
    """Boundary: level == job level is craftable (>=, not >)."""
    equipment = make_equipment(1, "sword", 100)
    assert JobLevelFilter.can_craft(equipment, {"forgeron": 100}) is True


def test_item_above_job_level_is_not_craftable() -> None:
    equipment = make_equipment(1, "sword", 101)
    assert JobLevelFilter.can_craft(equipment, {"forgeron": 100}) is False


def test_unknown_item_type_is_kept() -> None:
    """A type no job crafts must not silently disappear."""
    equipment = make_equipment(1, "sword", 200)
    equipment.type = {"name": "Familier", "id": 9999}
    assert JobLevelFilter.can_craft(equipment, {"forgeron": 10}) is True


def test_unconfigured_job_keeps_its_items() -> None:
    """Partial configurations must not drop items of unconfigured jobs."""
    equipment = make_equipment(1, "ring", 150)
    assert JobLevelFilter.can_craft(equipment, {"forgeron": 100}) is True


# --- filter_equipments ---

def test_filter_splits_pool_and_preserves_order() -> None:
    equipments = [
        make_equipment(1, "sword", 90),   # forgeron 100 -> kept
        make_equipment(2, "sword", 110),  # forgeron 100 -> out
        make_equipment(3, "ring", 80),    # bijoutier 100 -> kept
        make_equipment(4, "ring", 120),   # bijoutier 100 -> out
        make_equipment(5, "hat", 95),     # tailleur 50 -> out
    ]
    job_levels = {"forgeron": 100, "bijoutier": 100, "tailleur": 50}

    kept, filtered_out = JobLevelFilter.filter_equipments(equipments, job_levels)

    assert [e.ankama_id for e in kept] == [1, 3]
    assert [e.ankama_id for e in filtered_out] == [2, 4, 5]


def test_filter_keeps_unknown_types() -> None:
    equipments = [make_equipment(1, "sword", 200)]
    equipments[0].type = {"name": "Familier", "id": 9999}

    kept, filtered_out = JobLevelFilter.filter_equipments(
        equipments, {"forgeron": 10}
    )

    assert len(kept) == 1
    assert filtered_out == []


def test_empty_job_levels_filters_nothing() -> None:
    """No configured levels means no craftability information, so keep all."""
    equipments = [make_equipment(1, "sword", 200), make_equipment(2, "ring", 1)]

    kept, filtered_out = JobLevelFilter.filter_equipments(equipments, {})

    assert len(kept) == 2
    assert filtered_out == []


def test_summarize_excluded_counts_per_job() -> None:
    equipments = [
        make_equipment(1, "sword", 200),
        make_equipment(2, "ring", 200),
        make_equipment(3, "ring", 199),
        make_equipment(4, "hammer", 180),
    ]

    counts = JobLevelFilter.summarize_excluded(equipments)

    assert counts == {"forgeron": 2, "bijoutier": 2}


# --- parse_job_levels ---

def test_parse_job_levels_valid() -> None:
    parsed = JobLevelFilter.parse_job_levels("forgeron:120, bijoutier:80")

    assert parsed == {"forgeron": 120, "bijoutier": 80}


def test_parse_job_levels_rejects_unknown_job() -> None:
    with pytest.raises(ValueError, match="unknown job"):
        JobLevelFilter.parse_job_levels("farmer:100")


def test_parse_job_levels_rejects_missing_level() -> None:
    with pytest.raises(ValueError, match="expected 'job:level'"):
        JobLevelFilter.parse_job_levels("forgeron")


def test_parse_job_levels_rejects_non_integer_level() -> None:
    with pytest.raises(ValueError, match="must be an integer"):
        JobLevelFilter.parse_job_levels("forgeron:abc")


def test_parse_job_levels_rejects_negative_level() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        JobLevelFilter.parse_job_levels("forgeron:-5")


def test_parse_job_levels_empty_string_is_empty_mapping() -> None:
    assert JobLevelFilter.parse_job_levels("") == {}


# --- Config defaults ---

def test_config_defaults_to_disabled_with_no_levels() -> None:
    """Default behavior must be unchanged: full pool, no filtering."""
    config = ProcessingConfig()

    assert config.use_job_level_filter is False
    assert config.job_levels == {}


def test_config_job_levels_are_independent_per_instance() -> None:
    """The mutable default must not leak between configurations."""
    first = ProcessingConfig(use_job_level_filter=True, job_levels={"forgeron": 100})
    second = ProcessingConfig()

    assert second.job_levels == {}
    assert first.job_levels == {"forgeron": 100}
