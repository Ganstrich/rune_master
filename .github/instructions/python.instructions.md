# Python Code Instructions

This document outlines best practices and standards for Python 3.12 code in this project.

## 1. Type Hints

### Always Use Type Hints
Use comprehensive type hints for all functions, methods, and complex variables.

```python
# ✓ Good - Clear, complete type hints
def process_data(items: list[dict[str, Any]], threshold: int = 10) -> dict[str, int]:
    """Process items and return aggregated results."""
    return {item['id']: len(item) for item in items if len(item) > threshold}

# ✗ Bad - Missing return type, unclear parameter types
def process_data(items, threshold=10):
    return {item['id']: len(item) for item in items if len(item) > threshold}
```

### Use PEP 604 Union Syntax (Python 3.10+)
Use `X | Y` instead of `Union[X, Y]`.

```python
# ✓ Good
def fetch_resource(resource_id: str) -> dict[str, Any] | None:
    pass

# ✗ Bad
from typing import Union, Optional
def fetch_resource(resource_id: str) -> Optional[dict[str, Any]]:
    pass
```

### Use TypedDict for Structured Data
Define clear data contracts using `TypedDict` instead of generic dicts.

```python
# ✓ Good
from typing import TypedDict

class EquipmentSpec(TypedDict):
    id: str
    name: str
    level: int
    rarity: str

def validate_equipment(spec: EquipmentSpec) -> bool:
    pass

# ✗ Bad
def validate_equipment(spec: dict) -> bool:
    # Unclear what keys are expected
    pass
```

## 2. PEP 8 & Project Standards

### Import Organization
Follow PEP 8 import ordering: stdlib, third-party, local.

```python
# ✓ Good
import json
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel

from data.loaders import load_equipment
from models.equipment import Equipment
```

### Naming Conventions
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Modules**: `lowercase_with_underscores`

```python
class ResourceOptimizer:
    """Process and optimize resources."""
    
    MAX_BATCH_SIZE = 1000
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self._cache: dict[str, Any] = {}
    
    def optimize_resources(self) -> None:
        """Optimize resource allocation."""
        pass
```

### Line Length & Formatting
- Maximum line length: 100 characters
- Use parentheses for long expressions instead of backslashes

```python
# ✓ Good
result = (
    execute_query(param1, param2)
    .filter(active=True)
    .order_by('timestamp')
)

# ✗ Bad
result = execute_query(param1, param2).filter(active=True).order_by('timestamp')
```

## 3. Separation of Responsibilities

### Single Responsibility Principle
Each module/class should have one reason to change.

```python
# ✓ Good - Clear separation
class CacheManager:
    """Manages data caching only."""
    def get(self, key: str) -> Any | None:
        pass
    
    def set(self, key: str, value: Any) -> None:
        pass

class DataProcessor:
    """Transforms raw data only."""
    def process(self, raw_data: list[dict]) -> list[dict]:
        pass

class Logger:
    """Logs events only."""
    def log(self, level: str, message: str) -> None:
        pass

# ✗ Bad - Too many responsibilities
class AllInOne:
    def load_data(self): pass
    def cache_data(self): pass
    def process_data(self): pass
    def optimize(self): pass
    def format_output(self): pass
    def send_notifications(self): pass
```

### Dependency Injection
Pass dependencies explicitly instead of importing globally or using global state.

```python
# ✓ Good
class DataService:
    def __init__(self, cache: CacheManager, logger: logging.Logger) -> None:
        self.cache = cache
        self.logger = logger
    
    def fetch_data(self, key: str) -> dict[str, Any]:
        self.logger.info(f"Fetching data for {key}")
        return self.cache.get(key) or {}

# Usage
cache = CacheManager()
logger = logging.getLogger(__name__)
service = DataService(cache, logger)

# ✗ Bad - Global imports, tight coupling
class DataService:
    def __init__(self) -> None:
        self.cache = cache_manager  # Global
        self.logger = logger  # Global
```

## 4. Error Handling

### Use Specific Exceptions
Define and raise specific exceptions, don't catch bare `Exception`.

```python
# ✓ Good
class ResourceNotFoundError(Exception):
    """Raised when a resource cannot be found."""
    pass

class InvalidResourceError(Exception):
    """Raised when a resource data is invalid."""
    pass

def fetch_resource(resource_id: str) -> Resource:
    if not resource_id:
        raise ValueError("resource_id must not be empty")
    
    resource = _get_resource_from_db(resource_id)
    if not resource:
        raise ResourceNotFoundError(f"Resource {resource_id} not found")
    
    return resource

# ✗ Bad
def fetch_resource(resource_id: str) -> Resource:
    try:
        return _get_resource_from_db(resource_id)
    except Exception:  # Too broad
        return None
```

## 5. Common Anti-Patterns to Avoid

### Mutable Default Arguments
Never use mutable objects as default arguments.

```python
# ✗ Bad - Bug-prone
def add_resource(resource: Resource, inventory: list = []) -> None:
    inventory.append(resource)

# ✓ Good
def add_resource(resource: Resource, inventory: list[Resource] | None = None) -> None:
    if inventory is None:
        inventory = []
    inventory.append(resource)
```

### Type Ignore Comments
Avoid `# type: ignore`. If needed, use specific ignore codes.

```python
# ✗ Bad
x = some_function()  # type: ignore

# ✓ Good - Specific, with explanation
# Only suppressing specific type errors for well-documented reasons
x = some_function()  # type: ignore[assignment]  # External API returns untyped dict
```

### Large Functions
Keep functions focused and small (ideally < 30 lines).

```python
# ✗ Bad - Too many responsibilities
def process_equipment() -> None:
    # Load data
    # Validate data
    # Transform data
    # Cache data
    # Optimize resources
    # Generate reports
    pass

# ✓ Good - Clear, focused functions
def process_equipment() -> list[Equipment]:
    raw_data = load_equipment_data()
    validated_data = validate_equipment(raw_data)
    return transform_to_objects(validated_data)
```

### Global State
Avoid module-level mutable state; use classes instead.

```python
# ✗ Bad
cache = {}  # Global mutable state

def get_cached(key: str) -> Any | None:
    return cache.get(key)

# ✓ Good
class Cache:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
    
    def get(self, key: str) -> Any | None:
        return self._data.get(key)
```

## 6. Documentation & Docstrings

### Use Google-Style Docstrings
Provide clear, structured docstrings for all public functions and classes.

```python
def process_data(
    items: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Process and aggregate data items.
    
    Args:
        items: List of data dictionaries to process.
        config: Optional configuration dict. Keys:
            - 'batch_size': Size of processing batches (default: 100)
            - 'strategy': Processing strategy name (default: 'standard')
    
    Returns:
        Dict with processing results including 'count' and 'summary'.
    
    Raises:
        ValueError: If items list is empty or config invalid.
        KeyError: If required keys missing in item dicts.
    
    Example:
        >>> items = [{'id': '1', 'value': 100}, ...]
        >>> result = process_data(items, {'batch_size': 50})
        >>> print(result['count'])
    """
    if not items:
        raise ValueError("Items list cannot be empty")
    
    return {}
```

## 7. Python 3.12 Features

### Use Match Statements
Use `match` for clear, readable pattern matching.

```python
# ✓ Good - Python 3.10+
def process_item_type(item: dict[str, Any]) -> str:
    match item.get('type'):
        case 'document':
            return 'Process as document'
        case 'image':
            return 'Process as image'
        case 'audio':
            return 'Process as audio'
        case _:
            raise ValueError(f"Unknown type: {item.get('type')}")
```

### Use walrus operator (`:=`) judiciously

```python
# ✓ Good - Improves readability
if (data := load_json(path)) and data.get('status') == 'valid':
    process(data)

# ✗ Bad - Overuse makes code hard to follow
result = (data := load_json(path)) and (items := data.get('items', [])) and len(items) > 0
```

## 8. Testing

### Use Type-Safe Test Fixtures
```python
# ✓ Good
import pytest
from typing import Generator

@pytest.fixture
def sample_equipment() -> Generator[Equipment, None, None]:
    equipment = Equipment(id='test-1', name='Test', level=1)
    yield equipment
    equipment.cleanup()

def test_equipment_validation(sample_equipment: Equipment) -> None:
    assert sample_equipment.level >= 1
```

## 9. Module Structure Template

```python
"""Module description.

Describe the module's primary responsibility and key exports.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DataHandler:
    """Handle data operations."""
    
    def __init__(self, config_path: Path) -> None:
        """Initialize with configuration.
        
        Args:
            config_path: Path to configuration file.
        """
        self.config_path = config_path
    
    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process input data.
        
        Args:
            data: Raw input data.
        
        Returns:
            Processed results.
        """
        logger.debug("Processing data")
        return {}
```

## Summary Checklist

- [ ] All functions have type hints
- [ ] Imports organized per PEP 8
- [ ] No mutable default arguments
- [ ] Functions follow SRP (< 30 lines)
- [ ] Clear docstrings on public APIs
- [ ] Specific exception handling
- [ ] Dependency injection used
- [ ] No global mutable state
- [ ] Code follows PEP 8 (100 char lines)
- [ ] Tests are type-safe
