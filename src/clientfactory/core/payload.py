# ~/ClientFactory/src/clientfactory/core/payload.py
"""
Payload Module
--------------
Defines classes and utilities for handling request payloads.
Provides structures for parameter validation, transformation, and mapping
"""
from __future__ import annotations
import enum, typing as t, copy as cp
from dataclasses import dataclass, field
from clientfactory.log import log

class ParameterType(enum.Enum):
    """Types of parameters for classification and processing"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ANY = "any"

PT = ParameterType # shorthand

class ValidationError(Exception):
    """Raised when parameter validation fails"""
    pass

@dataclass
class Parameter:
    """
    Definition of a parameter with validaiton and transformation capabilities.

    Parameters can have default values, type constraints, required flags, and transformation logic.
    """
    name: t.Optional[str] = None # we need to make this required if not being included in a payload, but otherwise the payload should set the name based on the variable its assigned to
    type: ParameterType = ParameterType.ANY
    required: bool = False
    default: t.Any = None
    description: str = ""
    choices: t.Optional[t.List[t.Any]] = None
    transform: t.Optional[t.Callable[[t.Any], t.Any]] = None
    valuemap: t.Optional[t.Dict] = None
    mapmethod: t.Optional[t.Callable[[t.Any, t.Dict], t.Any]] = None
    transient: bool = False

    def _validatetype(self, value: t.Any) -> bool:
        typemap = {
            PT.STRING: str,
            PT.NUMBER: (int, float),
            PT.BOOLEAN: bool,
            PT.ARRAY: (list, tuple),
            PT.OBJECT: dict
        }
        if self.type == PT.ANY:
            return True
        checkfor = typemap.get(self.type)
        if checkfor:
            return isinstance(value, checkfor)
        return False

    def validate(self, value: t.Any) -> bool:
        """Validate a value against parameter constraints"""
        # Handle None values
        if value is None:
            if self.required:
                if self.default is not None:
                    return True
                raise ValidationError(f"Parameter '{self.name}' is required")
            return True

        # For ARRAY type, check each item individually
        if self.type == PT.ARRAY:
            if not isinstance(value, (list, tuple)):
                raise ValidationError(f"Parameter '{self.name}' must be of type list/tuple, got {type(value).__name__}")
            for item in value:
                if self.choices is not None and item not in self.choices:
                    raise ValidationError(
                        f"Each element in parameter '{self.name}' must be one of {self.choices}, got <{item}>"
                    )
            return True

        if self.type != ParameterType.ANY:
            if not (typevalid:=self._validatetype(value)):
                if self.required:
                    raise ValidationError(f"Parameter '{self.name}' must be of type <{self.type.value}>, got <{type(value).__name__}>")
                return False

        if (self.choices is not None) and (value not in self.choices):
            if self.required:
                raise ValidationError(
                    f"Parameter '{self.name}' must be one of [{self.choices}], got <{value}>"
                )
            return False

        return True

    def _mapval(self, val: t.Any) -> t.Any:
        """Internal helper which maps a single value via valuemap, optionally using mapmethod."""
        if val is None:
            return val
        if self.valuemap is not None:
            if self.mapmethod is not None:
                from fuzzywuzzy import process
                #print(f"Using mapmethod: {self.mapmethod.__name__} | with value: {val}")
                result = self.mapmethod(val, list(self.valuemap.keys()))
                #print(f"Mapmethod result: {result}")
                if self.mapmethod == process.extractOne:
                    bestmatch = result[0]
                    #print(f"Extracted bestmatch: {bestmatch}")
                    mapped = self.valuemap.get(bestmatch, bestmatch)
                    #print(f"Final mapped value: {mapped}")
                    return mapped
                else:
                    #print(f"Using result directly: {result}")
                    return result
            else:
                #print(f"Direct valuemap lookup")
                return self.valuemap.get(val, val)
        #print(f"No mapping applied, returning: {val}")
        return val

    def apply(self, value: t.Any) -> t.Any:
        """Apply validation and transformation to a value"""
        if (value is None) and (self.default is not None):
            value = cp.deepcopy(self.default)
            #print(f"Using default: {value}")


        if self.valuemap is not None:
            #print(f"Applying valuemap")
            if self.type == PT.ARRAY:
                mapped = [self._mapval(v) for v in value]
                #print(f"Mapped array: {value} -> {mapped}")
                value = mapped
            else:
                mapped = self._mapval(value)
                #print(f"Mapped value: {value} -> {mapped}")
                value = mapped
            #print(f"\nValue after mapping: {value}\n")

        #print(f"About to validate: {value}")
        self.validate(value)
        #print(f"Validation passed")


        if (self.transform is not None) and (value is not None):
            transformed = self.transform(value)
            #print(f"Transformed: {value} -> {transformed}")
            return transformed

        return value

@dataclass
class NestedParameter(Parameter):
    """Parameter that contains nested parameters"""
    children: t.Dict[str, Parameter] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize with object type"""
        self.type = PT.OBJECT

    def validate(self, value: t.Any) -> t.Any:
        """Validate a value and its nested parameters."""
        if not super().validate(value):
            return False

        if value is None: # skip nested validation if None
            return True

        for name, param in self.children.items():
            if name in value:
                if not param.validate(value[name]):
                    return False
            elif param.required:
                raise ValidationError(f"Required nested parameter '{name}' is missing")
        return True

    def apply(self, value: t.Any) -> t.Dict[str, t.Any]:
        """Apply validation and transformation to a value and its nested parameters."""

        if value is None:
            if self.default is not None:
                value = cp.deepcopy(self.default)
            else:
                value = {}

        self.validate(value)

        result = {}
        for name, param in self.children.items():
            if name in value:
                result[name] = param.apply(value[name])
            elif param.default is not None:
                result = cp.deepcopy(param.default)

        if self.transform is not None:
            result = self.transform(result)

        return result


class Payload:
    """
    Defines a complete request payload structure with parameters.

    A payload consists of parameters with validation and transformation rules,
    as well as static values that are always included.
    """
    def __init__(self, transform: t.Optional[t.Callable] = None, **kwargs):
        """
        Initialize a payload with parameters.

        Parameters can be passed as keyword arguments, where the key becomes
        the parameter name if not explicitly set.

        Example:
            payload = Payload(
                keyword=Parameter(),  # name will be set to "keyword"
                hits=Parameter(name="count")  # name remains "count"
            )
        """
        self.parameters = {}
        self.static = {}
        if transform and not isinstance(transform, t.Callable):
            raise ValidationError(f"Transform must be callable")
        self.transform = transform
        # Process keyword arguments as parameters
        for name, value in kwargs.items():
            if isinstance(value, Parameter):
                # Set the parameter name if not explicitly provided
                if value.name is None:
                    value.name = name
                self.parameters[name] = value
            else:
                # Treat other values as static
                self.static[name] = value

    def __getattr__(self, name: str) -> Parameter:
        """
        Allow accessing parameters as attributes.

        Example:
            payload = Payload(keyword=Parameter())
            log.debug(payload.keyword.name) # outputs: "keyword"
        """
        if name in self.parameters:
            return self.parameters[name]
        raise AttributeError(f"'Payload' object has no attribute '{name}'")

    def validate(self, data: t.Dict[str, t.Any]) -> bool:
        """Validate data against parameter definitions."""
        if (unknown:=[k for k in data if k not in self.parameters]):
            raise ValidationError(f"Unknown Parameters: [{', '.join(unknown)}]")

        for name, param in self.parameters.items():
            if name in data:
                if not param.validate(data[name]):
                    raise ValidationError(f"Parameter '{name}' failed validation")
            elif (param.required) and (param.default is None):
                raise ValidationError(f"Required parameter '{name}' is missing")

        return True

    def apply(self, data: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        """Apply validation and transformation to data"""
        log.info(f"payload.apply: received data: {data}")
        self.validate(data)
        result = cp.deepcopy(self.static)
        processingctx = {}

        # First pass: process non-conditional parameters
        for attrname, param in self.parameters.items():
            if not isinstance(param, ConditionalParameter):
                log.info(f"payload.apply: processing payload kwarg ({attrname}) with parameter: {param}")
                paramname = param.name if param.name is not None else attrname

                if attrname in data:
                    value = data[attrname]
                elif param.default is not None:
                    value = cp.deepcopy(param.default)
                else:
                    value = None

                processed = param.apply(value)
                if processed is not None:
                    processingctx[attrname] = processed
                    if not getattr(param, 'transient', False):
                        result[paramname] = processed

        # Second pass: process conditional parameters in dependency order
        conditionalparams = [
            (name, param) for name, param in self.parameters.items()
            if isinstance(param, ConditionalParameter)
        ]

        # Process until all conditionals are handled or no progress can be made
        while conditionalparams:
            processedthisround = []

            for attrname, param in conditionalparams:
                # Check if all dependencies are available
                if all(dep in processingctx for dep in param.dependencies):
                    log.info(f"payload.apply: processing conditional param ({attrname}) with parameter: {param}")
                    paramname = param.name if param.name is not None else attrname

                    if attrname in data:
                        processed = param.apply(data[attrname], context=processingctx)
                    else:
                        processed = param.apply(None, context=processingctx)

                    if processed is not None:
                        processingctx[attrname] = processed
                        if not getattr(param, 'transient', False):
                            result[paramname] = processed

                    processedthisround.append((attrname, param))

            # Remove processed parameters from the list
            for item in processedthisround:
                conditionalparams.remove(item)

            # If no parameters were processed this round and there are still some left,
            # we have a circular dependency
            if not processedthisround and conditionalparams:
                remaining = [name for name, _ in conditionalparams]
                raise ValidationError(f"Circular or missing dependencies in conditional parameters: {remaining}")

        if self.transform is not None and callable(self.transform):
            log.info(f"payload.apply: applying transform func ({self.transform.__name__})")
            result = self.transform(result)
            log.info(f"payload.apply: result after transform: {result}")

        log.info(f"payload.apply: returning result: {result}")
        return result

class PayloadBuilder:
    """Builder for creating Payload instances with fluent configuration"""

    def __init__(self):
        """Initialize with empty parameter set"""
        self.parameters = {}
        self.static = {}

    def addparam(self, name: str, **kwargs) -> PayloadBuilder:
        """Add a parameter to the payload."""
        self.parameters[name] = Parameter(name=name, **kwargs)
        return self

    def addnestedparam(self, name: str, children: t.Dict[str, t.Dict[str, t.Any]], **kwargs) -> PayloadBuidler:
        """Add a nested parameter to the payload"""
        childparams = {}
        for childname, childconfig in children.items():
            childparams[childname] = Parameter(name=childname, **childconfig)
        self.parameters[name] = NestedParameter(name=name, children=childparams, **kwargs)
        return self

    def addstatic(self, **kwargs) -> PayloadBuidler:
        """Add static values to the payload."""
        self.static.update(kwargs)
        return self

    def build(self) -> Payload:
        """Build and return the payload"""
        payload = Payload()
        payload.parameters = self.parameters.copy()
        payload.static = self.static.copy()
        return payload


class PayloadTemplate:
    """
    Template for creating Payload instances with predefined structure.

    Templates allow for reuse of common payload structures with customization options.
    """

    def __init__(self, parameters: t.Optional[t.Dict[str, t.Dict[str, t.Any]]] = None, static: t.Optional[t.Dict[str, t.Any]] = None) -> None:
        self.paramdefs = (parameters or {})
        self.staticvals = (static or {})

    def build(self, **overrides) -> Payload:
        """Build a Payload from the template with optional overrides."""
        payload = Payload()

        for name, config in self.paramdefs.items():
            if name in overrides:
                paramconfig = overrides.pop(name)
                if isinstance(paramconfig, Parameter):
                    if paramconfig.name is None:
                        paramconfig.name = name
                    payload.parameters[name] = paramconfig
                else:
                    payload.parameters[name] = Parameter(name=name, **paramconfig)
            else:
                payload.parameters[name] = Parameter(name=name, **config)

        for name, config in overrides.items():
            if isinstance(config, Parameter):
                if config.name is None:
                    config.name = name
                payload.parameters[name] = config
            else:
                payload.parameters[name] = Parameter(name=name, **config)

        payload.static = cp.deepcopy(self.staticvals)

        return payload

    def extend(self, parameters: t.Optional[t.Dict[str, t.Dict[str, t.Any]]] = None, static: t.Optional[t.Dict[str, t.Any]] = None) -> PayloadTemplate:
        """Create a new template by extending this one."""
        newparams = cp.deepcopy(self.paramdefs)
        newstatic = cp.deepcopy(self.staticvals)

        if parameters:
            newparams.update(parameters)

        if static:
            newstatic.update(static)

        return PayloadTemplate(
            parameters=newparams,
            static=newstatic
        )


class PayloadParameter(Parameter):
    """
    Parameter that contains a nested Payload.

    Allows for composing complex payload structures by nesting
    payloads within parameters.
    """
    def __init__(self, payload: Payload, **kwargs):
        """
        Initialize a parameter with a nested payload.

        Args:
            payload: The nested Payload object to process values through
            **kwargs: Additional Parameter configuration options
        """
        super().__init__(**kwargs)
        self.nestedpayload = payload
        self.type = PT.OBJECT

    def validate(self, value: t.Any) -> bool:
        """
        Validate the value as an object.

        For nested payloads, we simply check if it's an object
        or None (which will be converted to an empty dict).
        """
        if value is None:
            return True

        if not isinstance(value, dict):
            if self.required:
                raise ValidationError(f"Parameter '{self.name}' must be an object, got {type(value).__name__}")
            return False

        return True

    def apply(self, value: t.Any) -> t.Dict[str, t.Any]:
        """
        Process value through the nested payload.

        This applies validation and processing in three steps:
        1. Validate as a regular parameter
        2. Process through the nested payload
        3. Apply any transformation
        """
        self.validate(value)

        valdict = value if value is not None else {}

        result = self.nestedpayload.apply(valdict)

        if self.transform is not None:
            result = self.transform(result)

        return result



class NestedPayload(Payload):
    """
    Payload that handles nested parameter structures.

    Can be initialized with either:
    - A dictionary of Parameters
    - One or more Payload objects
    """
    def __init__(
        self,
        root: str,
        params: t.Optional[dict[str, Parameter]] = None,
        payload: t.Optional[Payload] = None,
        payloads: t.Optional[t.Sequence[Payload]] = None,
        static: t.Optional[dict] = None
    ):
        """
        Initialize nested payload.

        Args:
            root: Key for nested parameters
            params: Parameter definitions (optional)
            payload: Single Payload object (optional)
            payloads: Multiple Payload objects (optional)
            static: Static values to include at root level
        """
        self.root = root
        self.static = (static or {})
        self.transform = None
        self.transforms = {}

        # Handle different input types
        if params is not None:
            super().__init__(**params)
        elif payload is not None:
            self.parameters = payload.parameters.copy()
            if hasattr(payload, 'transform'):
                self.transform = payload.transform
        elif payloads is not None:
            # Merge multiple payloads
            merged = {}
            for p in payloads:
                if hasattr(p, 'transform') and (p.transform is not None):
                    payloadname = getattr(p, '__name__', f"payload:{id(p)}")
                    self.transforms[payloadname] = p.transform
                merged.update(p.parameters)
            self.parameters = merged
        else:
            self.parameters = {}

    def apply(self, data: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        """Apply validation and transformation with nesting"""

        # TODO:
            # implement multi-payload application
        processed = super().apply(data)
        result = self.static.copy()
        result[self.root] = processed
        return result

class ConditionalParameter(Parameter):
    """
    Parameter whose attributes depend on the values of other parameters.

    Attributes:
        dependencies: List/tuple of parameter names this parameter depends on
        conditions: Dict of condition functions that determine parameter behavior
            Supported condition types:
            - 'value': lambda *deps: value - Sets parameter value
            - 'include': lambda *deps: bool - Determines if parameter should be included
            - 'required': lambda *deps: bool - Determines if parameter is required
            - 'validate': lambda value, *deps: bool - Additional validation based on dependencies
    """
    def __init__(self, dependencies: t.Sequence[str], conditions: t.Dict[str, t.Callable[..., t.Any]], **kwargs):
        super().__init__(**kwargs)
        self.dependencies = dependencies
        self.conditions = conditions
        self._validateconditions(conditions)

    def _validateconditions(self, conditions: t.Dict[str, t.Callable[..., t.Any]]) -> None:
        valid = {'value', 'include', 'required', 'validate'}
        invalid = set(conditions.keys() - valid)
        if invalid:
            raise ValidationError(f"Invalid condition types: {invalid}. Must be one of: {valid}")

    def _getdependentvals(self, data: dict) -> tuple:
        try:
            return tuple(data[dep] for dep in self.dependencies)
        except KeyError as e:
            raise ValidationError(f"Missing required dependency: {str(e)}")

    def validate(self, value: t.Any) -> bool:
        if hasattr(self, '_excluded') and self._excluded:
            return True
        return super().validate(value)

    def apply(self, value: t.Any, context: t.Optional[dict] = None) -> t.Any:
        if context is None:
            raise ValidationError("Context required for conditional parameter")

        depvals = self._getdependentvals(context)

        if 'include' in self.conditions:
            inclusion = self.conditions['include']
            shouldinclude = inclusion(*depvals)
            if not shouldinclude:
                self._excluded = True
                return None

        if 'required' in self.conditions:
            requirements = self.conditions['required']
            self.required = requirements(*depvals)

        if 'value' in self.conditions:
            valuation = self.conditions['value']
            value = valuation(*depvals)

        value = super().apply(value)

        if 'validate' in self.conditions:
            validator = self.conditions['validate']
            if not validator(value, *depvals):
                raise ValidationError(
                    f"Conditional validation failed for parameter '{self.name}'"
                )

        return value


##  param types

class StrParam(Parameter):
    type = ParameterType.STRING

class NumParam(Parameter):
    type = ParameterType.NUMBER

class BoolParam(Parameter):
    type = ParameterType.BOOLEAN

class ListParam(Parameter):
    type = ParameterType.ARRAY
    default = []

class DictParam(Parameter):
    type = ParameterType.OBJECT
    default = {}

class AnyParam(Parameter):
    type = ParameterType.ANY
