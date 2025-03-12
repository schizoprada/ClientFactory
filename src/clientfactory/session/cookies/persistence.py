# ~/ClientFactory/src/clientfactory/session/cookies/persistence.py
from __future__ import annotations
import json, pickle, typing as t
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import fields
from clientfactory.session.cookies.core import Cookie, CookieStore
from loguru import logger as log


class CookiePersistenceStrategy(ABC):
    """Base class for cookie persistence strategies"""

    @abstractmethod
    def load(self) -> dict[str, Cookie]:
        """Load cookies from storage"""
        pass

    @abstractmethod
    def save(self, cookies: dict[str, Cookie]) -> None:
        """Save cookies to storage"""
        pass

class FilePersistence(CookiePersistenceStrategy):
    def __init__(self, filepath: (str | Path)):
        self.filepath = Path(filepath)

    @abstractmethod
    def serialize(self, cookies: dict[str, Cookie]) -> t.Any:
        """Convert cookies to serializaable format"""
        pass

    @abstractmethod
    def deserialize(self, data: t.Any) -> dict[str, Cookie]:
        """Convert serialized data back to cookies"""
        pass

    def load(self) -> dict[str, Cookie]:
        """Load cookies from file"""
        if not self.filepath.exists():
            # log a warning
            return {}

        try:
            with open(self.filepath, 'rb') as f:
                data = f.read()
                return self.deserialize(data)
        except Exception as e:
            log.error(f"FilePersistence.load | exception: {str(e)}")
            return {}

    def save(self, cookies: dict[str, Cookie]) -> None:
        """Save cookies to a file"""
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, 'wb') as f:
                data = self.serialize(cookies)
                f.write(data)
        except Exception as e:
            log.error(f"Failed to save cookies: {e}")

class JSONPersistence(FilePersistence):
    """JSON-based cookie persistence"""

    def serialize(self, cookies: dict[str, Cookie]) -> bytes:
        data = {
            name: {
                f.name: getattr(cookie, f.name, None)
                for f in fields(cookie)
            }
            for name, cookie in cookies.items()
        }
        return json.dumps(data).encode()

    def deserialize(self, data: t.Any) -> dict[str, Cookie]:
       return {
           name: Cookie(**cookiedata)
           for name, cookiedata in json.loads(data.decode()).items()
       }

class PicklePersistence(FilePersistence):
    """Pickle-based cookie persistence"""
    def serialize(self, cookies: dict[str, Cookie]) -> bytes:
        return pickle.dumps(cookies)

    def deserialize(self, data: t.Any) -> dict[str, Cookie]:
        return pickle.loads(data)
