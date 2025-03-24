# ~/ClientFactory/src/clientfactory/client/config.py
"""
Client Configuration
-------------------
This module defines configuration classes for Client instances.
"""
from __future__ import annotations
import typing as t
from dataclasses import dataclass, field

@dataclass
class ClientConfig:
    """Configuration for client behavior"""
    baseurl: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    verifyssl: bool = True
    followredirects: bool = True
