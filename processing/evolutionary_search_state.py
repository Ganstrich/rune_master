"""State representations for evolutionary portfolio search.

Defines immutable candidate portfolio state, provenance tracking,
and archive management for the evolutionary search engine.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple
from hashlib import sha256
import json

from models import Equipment


@dataclass(frozen=True)
class PortfolioCandidate:
    """Immutable representation of a candidate portfolio.

    Attributes:
        groups: List of group dictionaries (each with 'equipments' key).
        score: Objective fitness score for the complete portfolio.
        metrics: Portfolio quality metrics (coverage, overlap, etc.).
        generation: Which generation this candidate was created.
        parent_ids: Fingerprints of parent candidates (for provenance).
        provenance: Origin label ('baseline', 'random', 'evolved', 'warm_started', etc.).
        fingerprint: Stable hash for deduplication (frozen set of group signatures).
        feasibility_status: 'accepted', 'rejected', 'feasible', 'infeasible'.
        rejection_reason: Why candidate was rejected (if applicable).
        metadata: Extra tracking info (e.g., mutation operator used).
    """

    groups: Tuple[Dict[str, Any], ...] = field(default=())
    score: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    generation: int = 0
    parent_ids: FrozenSet[str] = field(default_factory=frozenset)
    provenance: str = "unknown"
    fingerprint: str = ""
    feasibility_status: str = "accepted"  # accepted, rejected, feasible, infeasible
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def equipment_ids(self) -> FrozenSet[int]:
        """Return all equipment IDs in this portfolio."""
        all_ids = set()
        for group in self.groups:
            for eq in group.get("equipments", []):
                all_ids.add(eq.ankama_id)
        return frozenset(all_ids)

    def group_count(self) -> int:
        """Return number of groups in portfolio."""
        return len(self.groups)

    def total_equipment(self) -> int:
        """Return total equipment assignments (with duplicates)."""
        count = 0
        for group in self.groups:
            count += len(group.get("equipments", []))
        return count

    def is_feasible(self) -> bool:
        """Return True if portfolio satisfies acceptance policy."""
        return self.feasibility_status in ("accepted", "feasible")

    def is_empty(self) -> bool:
        """Return True if portfolio has no groups."""
        return len(self.groups) == 0

    @staticmethod
    def compute_fingerprint(groups: List[Dict[str, Any]]) -> str:
        """Compute stable hash for portfolio deduplication.

        Hash is based on sorted equipment IDs per group, not metadata.
        Two portfolios with identical group memberships have identical fingerprints.
        """
        group_sigs = []
        for group in groups:
            eq_ids = tuple(
                sorted(eq.ankama_id for eq in group.get("equipments", []))
            )
            group_sigs.append(eq_ids)
        sorted_sigs = tuple(sorted(group_sigs))
        return sha256(
            json.dumps(sorted_sigs, default=str).encode()
        ).hexdigest()[:16]


@dataclass
class EvolutionaryArchive:
    """Archive of candidate portfolios for diversity and elite tracking.

    Maintains a searchable set of unique candidates and selection metrics.
    """

    candidates: List[PortfolioCandidate] = field(default_factory=list)
    fingerprints_seen: Set[str] = field(default_factory=set)
    diversity_threshold: float = 0.1  # Min fingerprint distance for diversity
    max_archive_size: int = 500
    elite_candidates: List[PortfolioCandidate] = field(default_factory=list)
    elite_size: int = 10

    def add_candidate(self, candidate: PortfolioCandidate) -> bool:
        """Add candidate if unique and within size limit.

        Returns True if added, False if already present or archive full.
        """
        if candidate.fingerprint in self.fingerprints_seen:
            return False

        if len(self.candidates) >= self.max_archive_size:
            return False

        self.candidates.append(candidate)
        self.fingerprints_seen.add(candidate.fingerprint)
        return True

    def update_elite(self) -> None:
        """Update elite set with best candidates."""
        self.elite_candidates = sorted(
            self.candidates, key=lambda c: c.score, reverse=True
        )[: self.elite_size]

    def best_candidate(self) -> Optional[PortfolioCandidate]:
        """Return highest-scoring candidate, or None."""
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda c: c.score)


@dataclass
class WarmStartConfig:
    """Configuration for warm-starting evolutionary search.

    Attributes:
        seed_portfolios: List of prior portfolios to seed population.
        cold_start_fraction: Fraction of initial population from cold starts.
        retain_eligible_seeds: If True, keep at least one seed if policy allows.
    """

    seed_portfolios: List[List[Dict[str, Any]]] = field(default_factory=list)
    cold_start_fraction: float = 0.2
    retain_eligible_seeds: bool = True
