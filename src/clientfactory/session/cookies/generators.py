# ~/ClientFactory/src/clientfactory/session/cookies/generators.py
import typing as t
from abc import ABC, abstractmethod
from loguru import logger as log

class CookieGenerator(ABC):
    """Protocol defining cookie generation behavior"""

    @abstractmethod
    def generate(self, context: t.Optional[dict] = None) -> dict:
        """Generate cookies based on optional context"""
        pass

    @abstractmethod
    def update(self, cookies: dict) -> None:
        """Update generator state with new cookies"""
        pass

class StaticCookieGenerator(CookieGenerator):
    """Handles static/predefined cookies"""

    def __init__(self, cookies: dict = {}):
        self.cookies = cookies

    def generate(self, context: t.Optional[dict] = None) -> dict:
        return self.cookies.copy()

    def update(self, cookies: dict) -> None:
        self.cookies.update(cookies)

class DynamicCookieGenerator(CookieGenerator):
    """Handles cookies that are generated via callables"""

    def __init__(self, generators: t.Dict[str, t.Callable] = {}):
        self.generators = generators

    def generate(self, context: t.Optional[dict] = None) -> dict:
        ctx = context or {}
        return {
            name: generator(ctx)
            for name, generator in self.generators.items()
        }

    def update(self, cookies: dict) -> None:
        # Dynamic generators can't be updated directly
        pass
