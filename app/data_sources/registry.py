from __future__ import annotations
from typing import Callable, TypeVar
from .base import DataSource
T = TypeVar("T", bound=type[DataSource])
DATA_SOURCES: dict[tuple[str, str], DataSource] = {}
def data_source(section: str, resource: str) -> Callable[[T], T]:
    def decorator(cls: T) -> T:
        DATA_SOURCES[(section, resource)] = cls(section, resource); return cls
    return decorator
def get_data_source(section: str, resource: str) -> DataSource:
    try: return DATA_SOURCES[(section, resource)]
    except KeyError as exc: raise KeyError(f"Unknown data source: {section}/{resource}") from exc
