# ~/ClientFactory/src/clientfactory/shorthands/__init__.py
"""
Shorthand reference aliases for extant components
"""

from clientfactory.core import (
    RequestMethod, Parameter, ParameterType,
    NestedParameter, Payload, NestedPayload,
    ConditionalParameter
)

from clientfactory.auth import (
    TokenScheme, KeyLocation
)

# Core Shorthands
RM = RequestMethod
P = Parameter
PT = ParameterType
NP = NestedParameter
CP = ConditionalParameter
PL = Payload
NPL = NestedPayload


# Auth Shorthands
TS = TokenScheme
KL = KeyLocation

FULLNAMES = [
    RequestMethod, Parameter, ParameterType, NestedParameter, Payload,
    TokenScheme, KeyLocation, NestedPayload, ConditionalParameter
]

SHORTHANDS = [
    RM, P, PT, NP, PL,
    TS, KL, NPL, CP
]

def genshortdoc(short, full) -> None:
    newdoc = f"""
    Shorthand for {full.__name__}
    -----------------------------
    {full.__doc__}
    """
    short.__doc__ = newdoc

for short, full in zip(SHORTHANDS, FULLNAMES):
    genshortdoc(short, full)

__all__ = [
    'RM', 'P', 'PT', 'NP', 'PL', 'TS', 'KL', 'NPL', 'CP'
]
