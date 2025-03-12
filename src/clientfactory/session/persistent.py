# ~/clientfactory/session/persistent.py
from __future__ import annotations
import typing as t
from dataclasses import dataclass, field
import pickle
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from abc import ABC, abstractmethod

class PersistenceError(Exception):
    """Base exception for persistence errors"""
    pass

@dataclass
class PersistConfig:
    """Configuration for session persistence"""
    path: str
    encrypt: bool = True
    key: t.Optional[bytes] = None
    createdir: bool = True

class BasePersist(ABC):
    """Base class for persistence implementations"""

    @abstractmethod
    def save(self, data: t.Any) -> None:
        """Save data to storage"""
        pass

    @abstractmethod
    def load(self) -> t.Optional[t.Any]:
        """Load data from storage"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear stored data"""
        pass

class DiskPersist(BasePersist):
    """File-based persistence with optional encryption"""

    def __init__(self, config: PersistConfig):
        self.config = config
        self._fernet: t.Optional[Fernet] = None

        if self.config.encrypt:
            if not self.config.key:
                self.config.key = Fernet.generate_key()
            self._fernet = Fernet(self.config.key)

    def save(self, data: t.Any) -> None:
        """Save data to file with optional encryption"""
        try:
            # Ensure directory exists
            path = Path(self.config.path).expanduser()
            if self.config.createdir:
                path.parent.mkdir(parents=True, exist_ok=True)

            # Pickle and optionally encrypt
            pickled = pickle.dumps(data)
            if self._fernet:
                pickled = self._fernet.encrypt(pickled)

            # Write to file
            with open(path, "wb") as f:
                f.write(pickled)

        except (pickle.PicklingError, OSError) as e:
            raise PersistenceError(f"Failed to save data: {str(e)}")

    def load(self) -> t.Optional[t.Any]:
        """Load and decrypt data from file"""
        path = Path(self.config.path).expanduser()
        if not path.exists():
            return None

        try:
            with open(path, "rb") as f:
                data = f.read()

            # Decrypt if needed
            if self._fernet:
                try:
                    data = self._fernet.decrypt(data)
                except InvalidToken as e:
                    raise PersistenceError(f"Failed to decrypt data: {str(e)}")

            return pickle.loads(data)

        except (pickle.UnpicklingError, OSError) as e:
            raise PersistenceError(f"Failed to load data: {str(e)}")

    def clear(self) -> None:
        """Delete stored data"""
        path = Path(self.config.path).expanduser()
        if path.exists():
            try:
                path.unlink()
            except OSError as e:
                raise PersistenceError(f"Failed to clear data: {str(e)}")

class MemoryPersist(BasePersist):
    """In-memory persistence for testing"""

    def __init__(self):
        self._storage: dict = {}

    def save(self, data: t.Any) -> None:
        """Save to memory"""
        self._storage["data"] = data

    def load(self) -> t.Optional[t.Any]:
        """Load from memory"""
        return self._storage.get("data")

    def clear(self) -> None:
        """Clear memory storage"""
        self._storage.clear()

# Factory function for common configurations
def persist(path: str, encrypt: bool = True) -> BasePersist:
    """Create persistence handler with common configuration"""
    config = PersistConfig(
        path=path,
        encrypt=encrypt,
        key=Fernet.generate_key() if encrypt else None
    )
    return DiskPersist(config)
