# ~/ClientFactory/src/clientfactory/session/state/file.py
"""
File-based State Storage
------------------------
Implements file-based state storage with different serialization options.
"""
from __future__ import annotations
import abc, json, pickle, typing as t
from pathlib import Path
from clientfactory.log import log

from clientfactory.session.state.base import StateStore, StateError

class FileStateStore(StateStore):
    """Base class for file-based state storage"""
    __declarativetype__ = 'filestore'

    def __init__(self, path: t.Optional[str] = None, **kwargs):
        super().__init__(path, **kwargs)
        self.filepath = Path(self.path)

    def exists(self) -> bool:
        """Check if state file exists"""
        return self.filepath.exists()

    @abc.abstractmethod
    def _read(self) -> dict:
        """Read state from file"""
        raise NotImplementedError

    @abc.abstractmethod
    def _write(self, state: dict) -> None:
        """Write state to file"""
        raise NotImplementedError

    def load(self) -> dict:
        if not self.exists():
            return {}
        return self._read()

    def save(self, state: dict) -> None:
        self._write(state)

    def clear(self) -> None:
        if self.exists():
            self.filepath.unlink()


class JSONStateStore(FileStateStore):
    """JSON file-based state storage"""
    format = "json"

    def _read(self) -> dict:
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise StateError(f"Failed to read JSON state: {e}")

    def _write(self, state: dict) -> None:
        try:
            with open(self.filepath, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            raise StateError(f"Failed to write JSON state: {e}")

class PickleStateStore(FileStateStore):
    """Pickle file-based state storage"""
    format = "pickle"

    def _read(self) -> dict:
        from requests import Session
        try:
            print(f"PickleStateStore: Reading file from {self.filepath}")
            with open(self.filepath, 'rb') as f:
                data = pickle.load(f)
                print(f"PickleStateStore: Loaded data type: {type(data)}")
                if isinstance(data, Session):
                    from requests.utils import dict_from_cookiejar
                    headers = dict(data.headers)
                    cookies = dict_from_cookiejar(data.cookies)
                    print(f"PickleStateStore: Converted Session - headers count: {len(headers)}, cookies count: {len(cookies)}")
                    return {
                        'headers': headers,
                        'cookies': cookies
                    }
                print(f"PickleStateStore: Data is not a Session, is dict? {isinstance(data, dict)}")
                return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"PickleStateStore: Error reading state: {e}")
            raise StateError(f"Failed to read pickle state: {e}")

    def _write(self, state: dict) -> None:
        try:
            with open(self.filepath, 'wb') as f:
                pickle.dump(state, f)
        except Exception as e:
            raise StateError(f"Failed to write pickle state: {e}")
