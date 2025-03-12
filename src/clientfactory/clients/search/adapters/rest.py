# ~/ClientFactory/src/clientfactory/clients/search/adapters/rest.py
import enum, typing as t
from dataclasses import dataclass, field, fields, asdict
import urllib.parse
from clientfactory.clients.search.adapters import Adapter

class DEFAULT:
    PARAMSMAP = {
        "query": "query",
        "page": "page",
        "hits": "hits",
        "sort": "sort",
        "order": "order"
    }

class PaginationStyle(enum.Enum):
    NUMBER = "number" # page=1&per_page=20
    OFFSET = "offset" # offset=0&limit=20
    CURSOR = "cursor" # cursor=xyz&limit=20

class FilterStyle(enum.Enum):
    KV = "KV" # color:red
    EQ = "EQ" # color=red
    IDX = "IDX" # filter[color]=red


@dataclass
class RESTConfig:
    paginationstyle: PaginationStyle = PaginationStyle.NUMBER
    filterstyle: FilterStyle = FilterStyle.EQ
    paramsmap: dict[str, str] = field(default_factory=lambda: DEFAULT.PARAMSMAP)
    filterkey: str = "filter"
    offsetkey: str = "offset"
    limitkey: str = "limit"
    cursorkey: str = "cursor"
    pagekey: str = "page"
    hitskey: str = "hits"
    sortkey: str = "sort"
    orderkey: str = "order"
    combinekey: str = ":"

@dataclass
class REST(Adapter):
    """REST query adapter with configurable parameter formatting.

    Handles formatting of search parameters, filters, pagination, and sorting
    according to common REST API patterns. Supports multiple styles for each
    parameter type through configuration.

    Attributes:
        config (RESTConfig): Configuration object controlling formatting behavior
    """
    config: RESTConfig = field(default_factory=RESTConfig)


    def buildurl(self, base:str, path:str = "", params:t.Optional[dict] = None) -> str:
        """Builds a complete URL with optional path and query parameters.

        Args:
            base: Base URL (e.g., "https://api.example.com")
            path: Optional path to append to base URL
            params: Optional dict of query parameters to encode

        Returns:
            Complete URL with encoded parameters

        Example:
            >>> adapter.buildurl("https://api.com", "search", {"q": "shoes"})
            'https://api.com/search?q=shoes'
        """
        url = f"{base.rstrip('/')}/{path.lstrip('/')}"
        if params:
            return f"{url}?{urllib.parse.urlencode(params)}"
        return url


    def formatparams(self, params, **kwargs) -> dict:
        """Format basic search parameters using configured parameter mappings.

        Args:
            params: Dictionary of parameter names and values
            **kwargs: Additional formatting options

        Returns:
            Dictionary of formatted parameters

        Example:
            >>> adapter.formatparams({"query": "shoes"})
            {'q': 'shoes'}  # if configured to map 'query' to 'q'
        """
        return {
            self.config.paramsmap.get(k, k): v
            for k, v in params.items()
        }

    def formatfilters(self, filters, **kwargs) -> dict:
        """Format filter parameters according to configured style.

        Supports multiple filter styles:
            - IDX: Uses bracket notation {"filter[key]": "value"}
            - KV:  Uses key:value notation {"filter": "key:value"}
            - EQ:  Uses direct equality {"key": "value"}

        Args:
            filters: Dictionary of filter field names and values
            **kwargs: Additional formatting options

        Returns:
            Dictionary of formatted filter parameters

        Example:
            >>> adapter.formatfilters({"color": "red", "size": "large"})
            {'filter[color]': 'red', 'filter[size]': 'large'}  # with IDX style
        """
        match self.config.filterstyle:
            case FilterStyle.IDX:
                return {f"{self.config.filterkey}[{k}]": v for k,v in filters.items()}
            case FilterStyle.KV:
                filterstr = " ".join(f"{k}:{v}" for k, v in filters.items())
                return {self.config.filterkey: filterstr}
            case _:
                return filters


    def formatpagination(self, page, hits, cursor=None, **kwargs) -> dict:
        """Format pagination parameters according to configured style.

        Supports multiple pagination styles:
            - NUMBER: Page number based {"page": n, "hits": m}
            - OFFSET: Offset based {"offset": n, "limit": m}
            - CURSOR: Cursor based {"cursor": "xyz", "limit": m}

        Args:
            page: Page number (1-based) or offset position
            hits: Number of results per page
            cursor: Optional cursor value for cursor-based pagination
            **kwargs: Additional formatting options

        Returns:
            Dictionary of formatted pagination parameters

        Example:
            >>> adapter.formatpagination(2, 20)
            {'page': 2, 'hits': 20}  # with NUMBER style
        """
        match self.config.paginationstyle:
            case PaginationStyle.NUMBER:
                return {
                    self.config.paramsmap[self.config.pagekey]: page,
                    self.config.paramsmap[self.config.hitskey]: hits
                }
            case PaginationStyle.OFFSET:
                return {
                    self.config.offsetkey: ((page - 1) * hits),
                    self.config.limitkey: hits
                }
            case PaginationStyle.CURSOR:
                return {
                    self.config.cursorkey: cursor,
                    self.config.limitkey: hits
                } if cursor else {self.config.limitkey: hits}
            case _:
                return {
                    self.config.pagekey: page,
                    self.config.hitskey: hits
                }

    def formatsorting(self, field, order, combine:bool=False, **kwargs) -> dict:
        """Format sorting parameters with optional field/order combination.

        Args:
            field: Field name to sort by
            order: Sort direction ('asc' or 'desc')
            combine: If True, combines field and order into single parameter
            **kwargs: Additional formatting options

        Returns:
            Dictionary of formatted sort parameters

        Example:
            >>> adapter.formatsorting("price", "desc")
            {'sort': 'price', 'order': 'desc'}
            >>> adapter.formatsorting("price", "desc", combine=True)
            {'sort': 'price:desc'}
        """
        sortkey = self.config.paramsmap[self.config.sortkey]
        orderkey = self.config.paramsmap[self.config.orderkey]
        if combine:
            return {sortkey: f"{field}{self.config.combinekey}{order}"} # shouldnt we dynamically adapt for the combinator?
        return {sortkey: field, orderkey: order}

    def formatall(self, **kwargs) -> dict:
        """Format all parameters into final request format"""
        formatted = {}
        if 'params' in kwargs:
            formatted.update(self.formatparams(kwargs['params']))
        else:
            formatted.update(self.formatparams(kwargs))
        return super().formatall(params=formatted)
