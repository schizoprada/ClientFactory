# ~/ClientFactory/src/clientfactory/decorators/payload.py
"""
Payload Decorators
-----------------
Breaking Python's Zen with style.
"""
from __future__ import annotations
import inspect, ast, typing as t
from datetime import datetime
from clientfactory.log import log

from clientfactory.core.payload import Payload, Parameter, ParameterType as PT
from clientfactory.declarative import DeclarativeComponent

class ParamDef:
    """Parameter definition builder using operator abuse"""
    def __init__(self, name: str):
        self.name = name
        self.settings = {}

    def __or__(self, other: 'ParamSetting') -> 'ParamDef':
        """Handle | operator for chaining settings"""
        self.settings.update(other.settings)
        return self

    def build(self) -> Parameter:
        """Build final Parameter from collected settings"""
        settings = self.settings.copy()
        if 'name' not in settings:
            settings['name'] = self.name
        return Parameter(**settings)

class ParamSetting:
    """Single parameter setting using function call syntax"""
    def __init__(self, settingtype: str):
        self.settingtype = settingtype
        self.settings = {}

    def __call__(self, value: t.Any) -> 'ParamSetting':
        """Capture the setting value"""
        self.settings[self.settingtype] = value
        return self

    def __or__(self, other: 'ParamSetting') -> dict:
        """Combine settings when chained with |"""
        settings = self.settings.copy()
        settings.update(other.settings)
        return settings

# Basic parameter settings
def name(value: str) -> ParamSetting:
    """Set parameter name"""
    return ParamSetting('name')(value)

def type(value: PT) -> ParamSetting:
    """Set parameter type"""
    return ParamSetting('type')(value)

def default(value: t.Any) -> ParamSetting:
    """Set default value"""
    return ParamSetting('default')(value)

def required(value: bool = True) -> ParamSetting:
    """Mark parameter as required"""
    return ParamSetting('required')(value)

def choices(*values: t.Any) -> ParamSetting:
    """Set allowed values"""
    return ParamSetting('choices')(list(values))

def transform(fn: t.Callable) -> ParamSetting:
    """Set transform function"""
    return ParamSetting('transform')(fn)

def description(text: str) -> ParamSetting:
    """Set parameter description"""
    return ParamSetting('description')(text)

def validate(fn: t.Callable[[t.Any], bool]) -> ParamSetting:
    """Set validation function"""
    return ParamSetting('validate')(fn)

# Shorthand type helpers
def strparam(default: t.Optional[str] = None) -> ParamSetting:
    """Create string parameter"""
    return type(PT.STRING) | (default(default) if default else EMPTY)

def numparam(default: t.Optional[float] = None) -> ParamSetting:
    """Create number parameter"""
    return type(PT.NUMBER) | (default(default) if default else EMPTY)

def boolparam(default: t.Optional[bool] = None) -> ParamSetting:
    """Create boolean parameter"""
    return type(PT.BOOLEAN) | (default(default) if default else EMPTY)

def arrayparam(default: t.Optional[list] = None) -> ParamSetting:
    """Create array parameter"""
    return type(PT.ARRAY) | (default(default if default else []))

def dateparam(fmt: str = "%Y-%m-%d") -> ParamSetting:
    """Create date parameter with format"""
    return (
        type(PT.STRING) |
        transform(lambda x: datetime.strptime(x, fmt)) |
        validate(lambda x: bool(datetime.strptime(x, fmt)))
    )

# Special empty param marker
class EmptyParam:
    """Represents an empty parameter definition"""
    def __repr__(self):
        return "EMPTY"
EMPTY = EmptyParam()
EMPTY = EmptyParam()

class PayloadMeta(type):
    """Metaclass for parsing parameter definitions"""
    def __new__(mcs, name, bases, namespace):
        # Get source and parse AST
        frame = inspect.currentframe().f_back
        source = inspect.getsource(frame)
        tree = ast.parse(source)

        parameters = {}

        # Find all assignment nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign):  # -> operator becomes annotation
                if isinstance(node, ast.Name):
                    param_name = node.target.id
                    # Parse the annotation (right side of ->)
                    settings = mcs._parse_settings(node.annotation)
                    parameters[param_name] = Parameter(name=param_name, **settings)

        namespace['__payload_parameters__'] = parameters
        return super().__new__(mcs, name, bases, namespace)

    @classmethod
    def _parse_settings(cls, node: ast.AST) -> dict:
        """Parse parameter settings from AST node"""
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Handle chained settings with |
            left = cls._parse_settings(node.left)
            right = cls._parse_settings(node.right)
            return {**left, **right}

        elif isinstance(node, ast.Call):
            # Handle function calls like name("x")
            settingtype = node.func.id
            args = [ast.literal_eval(arg) for arg in node.args]
            return {settingtype: args[0]}

        elif isinstance(node, ast.Name) and node.id == 'EMPTY':
            # Handle empty param marker
            return {}

        return {}

def payload(cls=None, *, static: t.Optional[dict] = None):
    """
    Decorator for defining payloads with fancy syntax.

    @payload
    class PAYLOAD:
        # Basic params
        keyword -> EMPTY
        status -> choices("active", "pending", "done")

        # Type helpers
        name -> strParam()
        age -> numParam(18)
        active -> boolParam(True)
        tags -> arrayParam()
        created -> dateParam("%Y-%m-%d")

        # Complex param
        brand -> (
            name("brandId") |
            type(PT.ARRAY) |
            default([]) |
            description("Brand IDs to filter by") |
            required()
        )
    """
    def decorator(cls):
        parameters = getattr(cls, '__payload_parameters__', {})
        payload_inst = Payload(**parameters)

        if static:
            payload_inst.static.update(static)

        class PayloadWrapper:
            def __new__(cls, *args, **kwargs):
                return payload_inst

        PayloadWrapper.__name__ = cls.__name__
        PayloadWrapper.__module__ = cls.__module__
        PayloadWrapper.__qualname__ = cls.__qualname__
        PayloadWrapper.__doc__ = cls.__doc__

        return PayloadWrapper

    return decorator if cls is None else decorator(cls)
