# ~/ClientFactory/src/clientfactory/clients/search/adapters/algolia.py
import enum, typing as t
from dataclasses import dataclass, field
import urllib.parse
from clientfactory.clients.search.adapters import Adapter

class AlgoliaSort(enum.Enum):
    BASIC = "basic"      # field:order
    REPLICA = "replica"  # uses index replicas
    CUSTOM = "custom"    # custom ranking rules

@dataclass
class AlgoliaConfig:
    index: str = ""  # Default index
    sortmode: AlgoliaSort = AlgoliaSort.BASIC
    replicas: dict[str, str] = field(default_factory=dict)  # field -> replica index mapping

@dataclass
class Algolia(Adapter):
    config: AlgoliaConfig = field(default_factory=AlgoliaConfig)

    def formatparams(self, params, **kwargs) -> dict:
        # Handle special Algolia parameters if needed
        # e.g., restrictSearchableAttributes, attributesToRetrieve, etc
        return params

    def formatfilters(self, filters, **kwargs) -> dict:
        # Support both simple and complex filters
        if isinstance(filters, dict):
            facets = [f"{k}:{v}" for k, v in filters.items()]
        else:
            # Allow passing pre-formatted filter strings
            facets = filters if isinstance(filters, list) else [filters]
        return {"facetFilters": facets}

    def formatpagination(self, page, hits, **kwargs) -> dict:
        # Ensure page is never negative
        page = max(1, page)
        return {
            "page": page - 1,  # Convert to 0-based
            "hitsPerPage": min(hits, 100)
        }

    def formatsorting(self, field, order, **kwargs) -> dict:
        match self.config.sortmode:
            case AlgoliaSort.BASIC:
                return {"ranking": [f"{field}:{order}"]}
            case AlgoliaSort.REPLICA:
                if field not in self.config.replicas:
                    raise ValueError(f"No replica index configured for {field}")
                # Return empty dict since we'll use replica index instead
                return {}
            case AlgoliaSort.CUSTOM:
                # Allow passing custom ranking rules
                return {"ranking": kwargs.get("ranking", [])}
            case _:
                raise ValueError(f"Invalid sort mode: {self.config.sortmode}")

    def formatall(self, **kwargs) -> dict:
        params = super().formatall(**kwargs)

        # Handle sorting separately since it needs special formatting
        if 'sort' in kwargs and 'order' in kwargs:
            sort_params = self.formatsorting(kwargs['sort'], kwargs['order'])
            params.update(sort_params)

        # Handle index selection with priority
        index = kwargs.get("index")
        if not index and self.config.sortmode == AlgoliaSort.REPLICA:
            field = kwargs.get("sort")
            if field in self.config.replicas:
                index = self.config.replicas[field]
        index = index or self.config.index

        if not index:
            raise ValueError("No index specified")

        return {
            "requests": [{
                "indexName": index,
                "params": urllib.parse.urlencode(params)
            }]
        }
