# ~/ClientFactory/src/clientfactory/session/state.py
from __future__ import annotations
import json, typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from clientfactory.utils.response import Response
from loguru import logger as log

@dataclass
class SessionState:
    """Session state container"""
    authenticated: bool = False
    lastrequest: t.Optional[datetime] = None
    failedattempts: int = 0
    tokens: dict[str, str] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    lastresponsecode: t.Optional[int] = None

class StateStore(ABC):
    """Base class for state storage strategies"""

    @abstractmethod
    def load(self) -> dict:
        """Load state from storage"""
        pass

    @abstractmethod
    def save(self, state: dict) -> None:
        """Save state to storage"""
        pass

class FileStateStore(StateStore):
    """File-based state storage"""
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)

    def load(self) -> dict:
        if not self.filepath.exists():
            return {}
        try:
            with open(self.filepath) as f:
                return json.load(f)
        except Exception as e:
            log.error(f"FileStateStore.load | Failed to load state: {e}")
            return {}

    def save(self, state: dict) -> None:
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            log.error(f"FileStateStore.save | Failed to save state: {e}")


class StateManager:
    """Session state manager"""
    def __init__(self, store: t.Optional[StateStore] = None):
        self.state = SessionState()
        self._store = store

        if self._store:
            self._load()

    def _load(self) -> None:
        if (self._store) and (data:=self._store.load()):
            if (lastreq := data.get('lastrequest')):
                data['lastrequest'] = datetime.fromisoformat(lastreq)
            for k, v in data.items():
                setattr(self.state, k, v)
        # probably raise otherwise

    def _save(self) -> None:
        """Save current state"""
        if self._store:
            data = asdict(self.state)
            if self.state.lastrequest:
                data['lastrequest'] = self.state.lastrequest.isoformat()
            self._store.save(data)

    def update(self, **updates) -> None:
        """Update state attributes"""
        for k, v in updates.items():
            setattr(self.state, k, v)
        self._save()
