# ~/ClientFactory/src/clientfactory/backends/graphql.py
from __future__ import annotations
import typing as t
import gql
from gql.dsl import DSLSchema
from graphql.language.ast import DocumentNode
from dataclasses import dataclass, field

from clientfactory.log import log
from clientfactory.core.request import Request, RequestMethod
from clientfactory.core.response import Response
from clientfactory.backends.base import Backend, BackendType


@dataclass
class GQLVar:
    """GraphQL variable definition"""
    name: str
    type: str
    required: bool = False
    default: t.Any = None

@dataclass
class GQLConfig:
    """Configuration for GraphQL requests"""
    operation: str
    query: str
    variables: t.Dict[str, t.Any] = field(default_factory=dict)
    schema: t.Optional[DSLSchema] = None
    vardefs: t.Dict[str, GQLVar] = field(default_factory=dict)
    parsed: t.Optional[DocumentNode] = None


    def __post_init__(self):
        """Parse and validate query on initialization"""
        log.debug(f"\nGQLConfig.__post_init__:")
        log.debug(f"Initial variables template: {self.variables}")
        try:
            self.parsed = gql.gql(self.query)
            log.debug(f"Query parsed successfully")
            self._validatevars()
            log.debug(f"Variable definitions extracted: {self.vardefs}")
        except Exception as e:
            log.debug(f"Error during initialization: {e}")
            raise GQLError(f"Invalid GraphQL query: {e}")

    def _typestring(self, typenode) -> str:
        """Convert type AST node to string representation"""
        if hasattr(typenode, 'type'):
            return f"{self._typestring(typenode.type)}!"
        return typenode.name.value

    def _validatevars(self):
        """Extract and validate variable definitions from query"""
        log.debug(f"\nGQLConfig._validatevars:")
        if self.parsed is None:
            log.debug("No parsed query available")
            return

        self.vardefs = {}

        for defi in self.parsed.definitions:
            log.debug(f"Processing definition: {defi.kind}")
            if hasattr(defi, 'variable_definitions'):
                for vardef in (defi.variable_definitions or []):
                    varname = vardef.variable.name.value
                    vartype = self._typestring(vardef.type)
                    required = hasattr(vardef.type, 'type')
                    log.debug(f"Found variable: {varname} ({vartype}) - required: {required}")
                    self.vardefs[varname] = GQLVar(
                        name=varname,
                        type=vartype,
                        required=required,
                        default=vardef.default_value
                    )


    def prepvars(self, data: dict) -> dict:
        log.debug(f"\nGQLConfig.prepvars:")
        log.debug(f"Input data: {data}")
        log.debug(f"Variable definitions: {self.vardefs}")
        log.debug(f"Template variables: {self.variables}")

        result = self.variables.copy()
        log.debug(f"Starting with template copy: {result}")

        for k, v in data.items():
            log.debug(f"\nProcessing input: {k} = {v}")
            if '.' in k:
                parts = k.split('.')
                log.debug(f"Nested path: {parts}")
                current = result
                # Navigate to the nested location
                for part in parts[:-1]:
                    log.debug(f"Navigating to: {part}")
                    if part not in current:
                        log.debug(f"Creating nested dict for: {part}")
                        current[part] = {}
                    current = current[part]
                # Set the value
                log.debug(f"Setting {parts[-1]} = {v}")
                current[parts[-1]] = v
                log.debug(f"After nested assignment: {result}")
            else:
                # For non-nested keys, try to find their place in the template
                log.debug(f"Non-nested key: {k}")
                placed = False
                # First check if this key exists in any nested dictionaries
                for tk, tv in result.items():
                    if isinstance(tv, dict):
                        if k in tv:
                            log.debug(f"Found existing nested location under: {tk}")
                            result[tk][k] = v
                            placed = True
                            break
                # If not found in nested structures and exists at root, update root
                if not placed and k in result:
                    log.debug(f"Updating root key: {k}")
                    result[k] = v
                # Otherwise ignore it (don't add to root)
                elif not placed:
                    log.debug(f"Key {k} not found in template structure - ignoring")

        log.debug(f"\nChecking required variables:")
        for varname, vardef in self.vardefs.items():
            log.debug(f"Checking {varname} (required: {vardef.required})")
            if vardef.required and varname not in result:
                raise GQLError(f"Required variable '{varname}' not provided")

        log.debug(f"\nFinal variables: {result}")
        return result

    def topayload(self, data: dict) -> dict:
        log.debug(f"\nGQLConfig.topayload:")
        log.debug(f"Converting data to payload: {data}")
        payload = {
            "operationName": self.operation,
            "query": self.query,
            "variables": self.prepvars(data)
        }
        log.debug(f"Final payload: {payload}")
        return payload

class GQLError(Exception):
    """Raised for GraphQL related errors"""
    pass

class GraphQL(Backend):
    """
    GraphQL backend protocol adapter.

    Formats requests and parses responses according to GraphQL conventions.
    """
    __declarativetype__ = 'graphql'

    def __init__(
        self,
        config: t.Optional[GQLConfig] = None,
        operation: t.Optional[str] = None,
        query: t.Optional[str] = None,
        variables: t.Optional[dict[str, t.Any]] = None,
        schema: t.Optional[DSLSchema] = None,
        **kwargs
    ):
        if config is None:
            if not all((operation, query)):
                raise GQLError(f"GraphQL Backend requires either GQLConfig or kwargs: [operation, query, variables]")
            config = GQLConfig(
                operation=operation,
                query=query,
                variables=(variables or {}),
                schema=schema
            )
        self.config = config


    def preparerequest(self, request: Request, data: dict) -> Request:
        """Prepare a GraphQL request with the given data"""
        log.debug(f"Preparing GraphQL request with data: {data}")

        gqlpayload = self.config.topayload(data)

        log.debug(f"Perpared GraphQL payload: {gqlpayload}")

        return request.clone(
            method=RequestMethod.POST,
            json=gqlpayload
        )

    def _responseprocessor(self, response: Response) -> t.Any:
        """Helper for: Process a GraphQL response"""
        if not response.ok:
            response.raiseforstatus()

        data = response.json()

        if ("errors" in data) and (errors:=data["errors"]):
            errmsg = "; ".join(err.get("message", "Unknown Error") for err in errors)
            raise GQLError(f"GraphQL Errors: {errmsg}")

        return data.get('data', data)


    def processresponse(self, response: Response) -> t.Any:
        """Process a GraphQL response"""
        return super().processresponse(response)
