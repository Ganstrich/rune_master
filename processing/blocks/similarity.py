"""Pure set-similarity helpers."""

from collections.abc import Collection


def jaccard(left: Collection[object], right: Collection[object]) -> float:
    """Return the Jaccard similarity of two collections."""
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 0.0