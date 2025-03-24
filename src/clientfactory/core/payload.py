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

    def apply(self, value: t.Any) -> t.Any:
        """Apply validation and transformation to a value"""
        if (value is None) and (self.default is not None):
            value = cp.deepcopy(self.default)

        self.validate(value)

        if (self.transform is not None) and (value is not None):
            return self.transform(value)

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
    def __init__(self, **kwargs):
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
            print(payload.keyword.name) # outputs: "keyword"
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
        self.validate(data)
        result = cp.deepcopy(self.static)
        for name, param in self.parameters.items():
            if name in data:
                result[name] = param.apply(data[name])
            elif param.default is not None:
                result[name] = cp.deepcopy(param.default)
        return result


class PayloadBuilder:
    """Builder for creating Payload instances with fluent configuration"""

    def __init__(self):
        """Initialize with empty parameter set"""
        self.parameters = {}
        self.static = {}

    def addparam(self, name: str, **kwargs) -> PayloadBuidler:
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
