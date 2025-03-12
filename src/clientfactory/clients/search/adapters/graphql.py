# ~/ClientFactory/src/clientfactory/clients/search/adapters/graphql.py
import enum, typing as t
from dataclasses import dataclass, field
from clientfactory.clients.search.adapters import Adapter
from loguru import logger as log

class GQLOps(enum.Enum):
    EQ = "eq"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    CONTAINS = "contains"

@dataclass
class GQLVar:
    """GraphQL Variable"""
    name: str
    path: t.Optional[str] = None
    process: t.Optional[t.Callable] = None
    default: t.Any = None

@dataclass
class GQLConfig:
    operation: str = "search"
    query: str = ""
    variables: t.Dict[str, GQLVar] = field(default_factory=dict)
    fragments: t.List[str] = field(default_factory=list)
    structure: t.Dict[str, t.Any] = field(default_factory=dict)

@dataclass
class GraphQL(Adapter):
    config: GQLConfig = field(default_factory=GQLConfig)

    def _resolvepath(self, data:dict, path:str, value:t.Any) -> dict:
        log.debug(f"GraphQL._resolvepath | resolving path[{path}] for value[{value}]")
        parts = path.split('.')
        current = data
        for part in parts[:-1]:
            current = current.setdefault(part, {})
            log.trace(f"GraphQL._resolvepath | building nested structure at [{part}]")
        current[parts[-1]] = value
        log.debug(f"GraphQL._resolvepath | resolved structure: {data}")
        return data  # Returns full data structure to maintain all nested updates

    def _applyvar(self, params:dict, var:GQLVar, value:t.Any) -> dict:
        log.debug(f"GraphQL._applyvar | applying variable[{var.name}] with value[{value}]")

        if (value is None) and (var.default is not None):
            value = var.default
            log.debug(f"GraphQL._applyvar | using default value[{value}]")

        if var.process:
            try:
                value = var.process(value)
                log.debug(f"GraphQL._applyvar | processed value to [{value}]")
            except Exception as e:
                log.error(f"GraphQL._applyvar | processing error for [{var.name}]: {str(e)}")
                raise

        if var.path:
            result = self._resolvepath(params, var.path, value)
            log.debug(f"GraphQL._applyvar | path-resolved result: {result}")
            return result

        result = {var.name: value}
        log.debug(f"GraphQL._applyvar | direct-mapped result: {result}")
        return result

    def _structurevars(self, vars: dict) -> dict:
        if not self.config.structure:
            log.debug("GraphQL._structurevars | no structure defined, returning original vars")
            return vars

        log.debug(f"GraphQL._structurevars | applying structure template to vars: {vars}")

        def applystructure(template: dict, data: dict) -> dict:
            result = {}
            for k, v in template.items():
                if isinstance(v, dict):
                    result[k] = applystructure(v, data)
                    log.trace(f"GraphQL._structurevars | nested structure at [{k}]: {result[k]}")
                else:
                    result[k] = data.get(v)
                    log.trace(f"GraphQL._structurevars | mapped [{v}] to [{k}]: {result[k]}")
            return result

        structured = applystructure(self.config.structure, vars)
        log.debug(f"GraphQL._structurevars | final structured result: {structured}")
        return structured

    def formatall(self, **kwargs) -> dict:
        log.info(f"GraphQL.formatall | formatting query[{self.config.operation}] with params: {kwargs}")
        variables = {}

        for paramname, value in kwargs.items():
            if paramname in self.config.variables:
                vardef = self.config.variables[paramname]
                log.debug(f"GraphQL.formatall | handling parameter[{paramname}] with definition[{vardef}]")
                variables.update(self._applyvar({}, vardef, value))

        variables = self._structurevars(variables)

        result = {
            "query": self.config.query,
            "operationName": self.config.operation,
            "variables": variables
        }
        log.info(f"GraphQL.formatall | formatted query result: {result}")
        return result

    def formatparams(self, params, **kwargs) -> dict:
        log.debug(f"GraphQL.formatparams | formatting params: {params}")
        return {"variables": params}

    def formatfilters(self, filters, **kwargs) -> dict:
        log.debug(f"GraphQL.formatfilters | formatting filters: {filters}")
        return {"variables": {"filter": filters}}

    def formatpagination(self, page, hits, **kwargs) -> dict:
        log.debug(f"GraphQL.formatpagination | formatting pagination: page={page}, hits={hits}")
        return {"variables": {
            "offset": (page - 1) * hits if page else 0,
            "limit": hits
        }}

    def formatsorting(self, field, order, **kwargs) -> dict:
        log.debug(f"GraphQL.formatsorting | formatting sorting: field={field}, order={order}")
        return {"variables": {"sort": field}}
