"""Profit objective over craft costs and priced break density."""

from dataclasses import dataclass
from typing import Mapping

from models import Equipment
from processing.blocks.recipes import iter_recipe
from processing.valuation.focus import best_focus, break_density_focused
from processing.valuation.objective import GroupCandidate
from processing.valuation.overlap import OverlapObjective
from processing.valuation.prices import PriceSource


@dataclass(frozen=True)
class FlatTauxModel:
    """Return one constant taux until observed break data is available."""

    taux: float = 1.0

    def estimate(self, item: Equipment) -> float:
        del item
        return self.taux


class ProfitObjective:
    """Rank groups by theoretical kamas profit with an overlap fallback."""

    def __init__(
        self,
        price_source: PriceSource,
        taux_model: FlatTauxModel | None = None,
        acquisition_cost: float = 0.0,
        fallback: OverlapObjective | None = None,
    ) -> None:
        self.price_source = price_source
        self.taux_model = taux_model or FlatTauxModel()
        self.acquisition_cost = acquisition_cost
        self.fallback = fallback or OverlapObjective()

    def _item_value(
        self, item: Equipment
    ) -> tuple[float, str] | None:
        rho: dict[str, float] = {}
        for effect in getattr(item, "effects", []) or []:
            stat = getattr(effect, "stat_name", "")
            price = self.price_source.rune_price(stat)
            if price is not None:
                from processing.valuation.density import resolve_stat_name, RUNE_DENSITY

                try:
                    resolved = resolve_stat_name(stat)
                    rho[resolved] = price / RUNE_DENSITY[resolved]
                except KeyError:
                    continue
        focus = best_focus(item, rho)
        if focus is None:
            return None
        revenue = self.taux_model.estimate(item) * break_density_focused(item, focus) * rho[focus]
        craft_cost = 0.0
        for resource_id, quantity in iter_recipe(item):
            price = self.price_source.resource_price(resource_id)
            if price is None:
                return None
            craft_cost += quantity * price
        return revenue - craft_cost, focus

    def score_details(self, group: GroupCandidate) -> dict[str, object]:
        """Return the score plus focus and partial-price diagnostics."""
        values = 0.0
        focus_by_item: dict[int, str] = {}
        unknown_items: list[int] = []
        for item in group.equipments:
            value = self._item_value(item)
            if value is None:
                unknown_items.append(item.ankama_id)
                continue
            item_value, focus = value
            values += item_value
            focus_by_item[item.ankama_id] = focus
        if not focus_by_item:
            return {
                "score": self.fallback.score(group),
                "unit": "overlap",
                "fallback": True,
                "focus_by_item": {},
                "unknown_items": unknown_items,
            }
        distinct_resources = {
            resource_id
            for item in group.equipments
            for resource_id, _quantity in iter_recipe(item)
            if resource_id not in group.excluded_resource_ids
        }
        return {
            "score": values - self.acquisition_cost * len(distinct_resources),
            "unit": "kamas",
            "fallback": False,
            "focus_by_item": focus_by_item,
            "unknown_items": unknown_items,
        }

    def score(self, group: GroupCandidate) -> float:
        """Return theoretical profit, or the explicit overlap fallback."""
        return float(self.score_details(group)["score"])