"""Break-density and focus formulas."""

from models import Equipment
from processing.valuation.density import RUNE_DENSITY, resolve_stat_name


def _lines(item: Equipment) -> list[tuple[str, float, float]]:
    lines: list[tuple[str, float, float]] = []
    for effect in getattr(item, "effects", []) or []:
        raw_name = getattr(effect, "stat_name", None)
        if not raw_name:
            stat_type = getattr(effect, "stat_type", {})
            raw_name = stat_type.get("name", "") if isinstance(stat_type, dict) else ""
        try:
            stat_name = resolve_stat_name(raw_name)
        except KeyError:
            continue
        value = max((float(effect.int_minimum) + float(effect.int_maximum)) / 2, 0.0)
        lines.append((stat_name, value, RUNE_DENSITY[stat_name]))
    return lines


def break_density(item: Equipment) -> float:
    """Return total rune density from the item's non-negative stat lines."""
    return sum(value * density for _name, value, density in _lines(item))


def break_density_focused(item: Equipment, stat: str) -> float:
    """Return density when one stat is focused and all other lines yield half."""
    try:
        focus_name = resolve_stat_name(stat)
    except KeyError:
        return 0.5 * break_density(item)
    return sum(
        value * density * (1.0 if name == focus_name else 0.5)
        for name, value, density in _lines(item)
    )


def best_focus(item: Equipment, rho: object = None) -> str | None:
    """Return no focus until rune price data is available."""
    del item, rho
    return None