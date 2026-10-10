"""Filter equipment by the player's job (profession) levels.

Crafting an item in Dofus 3 requires a minimum job level, so an equipment
whose type belongs to a job the player has not levelled enough cannot be
crafted by them. This module turns configured job levels into a craftability
predicate and applies it to a loaded equipment pool.

**Type identity.** The DofusDB API filter takes an English ``name_id``
(``sword``, ``ring``, ... — the lists in ``config.py``), but the equipment
payload returns ``type`` as a French display name plus a numeric ``id``::

    {"name": "Épée", "id": 80}

So the filter must resolve an equipment's type to its job without depending
on the response language. It matches, in order: the numeric ``type.id``, the
English ``name_id`` (as used by the API filter), then the French name.
``ITEM_TYPE_IDS`` below is the name_id -> numeric id table; it is the single
place to extend if a new craftable type is added.

Items whose type matches nothing are kept: a new or unmapped item type must
never silently disappear from the report.
"""

from typing import Dict, List, Mapping, Optional, Tuple

from config import (
    BIJOUTIER,
    CORDONNIER,
    FACONNEUR,
    FORGERON,
    SCULPTEUR,
    TAILLEUR,
)
from models import Equipment

# Job name -> item type name_ids (as used by config.py and the API filter).
# Every craftable type belongs to exactly one job.
JOB_TO_TYPES: Dict[str, frozenset] = {
    "cordonnier": frozenset(CORDONNIER),
    "bijoutier": frozenset(BIJOUTIER),
    "tailleur": frozenset(TAILLEUR),
    "forgeron": frozenset(FORGERON),
    "sculpteur": frozenset(SCULPTEUR),
    "faconneur": frozenset(FACONNEUR),
}

# name_id -> numeric type id, verified against the DofusDB payload for every
# type in config.py. The API filter matches on name_id while the equipment
# payload carries this id, so both must be known.
ITEM_TYPE_IDS: Dict[str, int] = {
    "ring": 17,
    "amulet": 33,
    "bow": 39,
    "hammer": 42,
    "cloak": 43,
    "boots": 45,
    "hat": 27,
    "shovel": 52,
    "belt": 58,
    "wand": 65,
    "axe": 73,
    "sword": 80,
    "shield": 87,
    "dagger": 93,
    "lance": 111,
    "staff": 125,
    "scythe": 163,
}

# French payload names (language "fr"), keyed to their English name_id.
FRENCH_TYPE_NAMES: Dict[str, str] = {
    "Anneau": "ring",
    "Amulette": "amulet",
    "Arc": "bow",
    "Marteau": "hammer",
    "Cape": "cloak",
    "Bottes": "boots",
    "Pelle": "shovel",
    "Ceinture": "belt",
    "Baguette": "wand",
    "Hache": "axe",
    "Épée": "sword",
    "Bouclier": "shield",
    "Dague": "dagger",
    "Lance": "lance",
    "Bâton": "staff",
    "Faux": "scythe",
    "Chapeau": "hat",
}


def _build_type_to_job() -> Dict[object, str]:
    """Map every recognized type spelling (name_id, id, French name) to a job."""
    mapping: Dict[object, str] = {}
    for job, name_ids in JOB_TO_TYPES.items():
        for name_id in name_ids:
            mapping[name_id] = job
            numeric_id = ITEM_TYPE_IDS.get(name_id)
            if numeric_id is not None:
                mapping[numeric_id] = job
    for french_name, name_id in FRENCH_TYPE_NAMES.items():
        job = mapping.get(name_id)
        if job is not None:
            mapping[french_name] = job
    return mapping


TYPE_TO_JOB: Dict[object, str] = _build_type_to_job()


class JobLevelFilter:
    """Keep only the equipment the player's job levels allow them to craft."""

    JOB_TO_TYPES = JOB_TO_TYPES
    ITEM_TYPE_IDS = ITEM_TYPE_IDS
    TYPE_TO_JOB = TYPE_TO_JOB

    @classmethod
    def resolve_job(cls, type_info: Mapping) -> Optional[str]:
        """Return the job that crafts an item of this type, or None.

        Accepts a raw ``type`` dict as returned by the API or snapshot: the
        numeric id wins, then the display name (English name_id or French).
        """
        name = type_info.get("name")
        numeric_id = type_info.get("id")
        for key in (numeric_id, name):
            if key is None:
                continue
            job = cls.TYPE_TO_JOB.get(key)
            if job is not None:
                return job
        return None

    @staticmethod
    def parse_job_levels(text: str) -> Dict[str, int]:
        """Parse ``"job:level,job:level"`` into a validated mapping.

        Raises:
            ValueError: If any entry is malformed or any level is negative.
        """
        levels: Dict[str, int] = {}
        for entry in text.split(","):
            entry = entry.strip()
            if not entry:
                continue
            job, separator, raw_level = entry.partition(":")
            if not separator:
                raise ValueError(
                    f"expected 'job:level', got {entry!r} "
                    "(example: forgeron:120,bijoutier:80)"
                )
            job = job.strip().lower()
            if job not in JobLevelFilter.JOB_TO_TYPES:
                known = ", ".join(sorted(JobLevelFilter.JOB_TO_TYPES))
                raise ValueError(
                    f"unknown job {job!r}. Known jobs: {known}"
                )
            try:
                level = int(raw_level.strip())
            except ValueError:
                raise ValueError(
                    f"job level must be an integer, got {raw_level.strip()!r}"
                ) from None
            if level < 0:
                raise ValueError(f"job level must not be negative, got {level}")
            levels[job] = level
        return levels

    @classmethod
    def can_craft(cls, equipment: Equipment, job_levels: Dict[str, int]) -> bool:
        """Return whether the player can craft one equipment item.

        An item is craftable when the level of the job that crafts its type
        is at least the item level. Items whose type is unknown, or whose
        job is not configured, are treated as craftable so that partial
        configurations and new item types never silently drop equipment.
        """
        job = cls.resolve_job(equipment.type)
        if job is None:
            return True
        level = job_levels.get(job)
        if level is None:
            return True
        return level >= equipment.level

    @classmethod
    def filter_equipments(
        cls,
        equipments: List[Equipment],
        job_levels: Dict[str, int],
    ) -> Tuple[List[Equipment], List[Equipment]]:
        """Split a pool into (craftable, filtered out).

        Args:
            equipments: Loaded equipment pool.
            job_levels: Player job levels by job name.

        Returns:
            Tuple of (kept, filtered_out) preserving input order.
        """
        craftable: List[Equipment] = []
        filtered_out: List[Equipment] = []
        for equipment in equipments:
            if cls.can_craft(equipment, job_levels):
                craftable.append(equipment)
            else:
                filtered_out.append(equipment)
        return craftable, filtered_out

    @classmethod
    def summarize_excluded(
        cls,
        filtered_out: List[Equipment],
    ) -> Dict[str, int]:
        """Count excluded items per job for a readable CLI summary line."""
        counts: Dict[str, int] = {}
        for equipment in filtered_out:
            job = cls.resolve_job(equipment.type) or "unknown-job"
            counts[job] = counts.get(job, 0) + 1
        return counts
