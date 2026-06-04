"""Base class for grouping experts."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from models import Equipment
# Avoid circular import by importing inside methods or using type hints with string if needed
# but ProcessingConfig is usually safe to import.
from processing.config_dataclass import ProcessingConfig

class GroupingExpert(ABC):
    """Abstract base class for all grouping experts.
    
    An expert is a specialized algorithm that takes a pool of equipment
    and discovers potential groups based on specific criteria.
    """
    
    def __init__(
        self, 
        name: str,
        cache_manager: Optional[Any] = None,
        api_client: Optional[Any] = None
    ):
        self.name = name
        self.cache_manager = cache_manager
        self.api_client = api_client

    @abstractmethod
    def discover_groups(
        self, 
        equipments: List[Equipment], 
        config: ProcessingConfig
    ) -> List[Dict[str, Any]]:
        """Discover groups using the expert's specialized logic.
        
        Args:
            equipments: Pool of equipment to analyze
            config: Pipeline configuration
            
        Returns:
            List of group dictionaries with consistent format.
        """
        pass

    def evaluate_group(self, group: Dict[str, Any]) -> float:
        """Calculate a fitness score for a group.
        
        Default implementation uses sharing efficiency, which follows the
        "2+ equipment" definition (resources used by 2+ equipment / total unique resources).
        Experts can override this to prioritize different metrics 
        (e.g., economic value, level consistency).
        """
        return group.get("sharing_efficiency", 0.0)
