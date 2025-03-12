# ~/ClientFactory/src/clientfactory/session/tests/test_state.py
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from clientfactory.session.state import SessionState, StateManager, FileStateStore

class TestSessionState:
    def test_state_defaults(self):
        state = SessionState()
        assert state.authenticated is False
        assert state.lastrequest is None
        assert state.failedattempts == 0
        assert state.tokens == {}
        assert state.metadata == {}

class TestFileStateStore:
    def test_save_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "state.json"
            store = FileStateStore(filepath)

            # Test save
            test_state = {
                "authenticated": True,
                "lastrequest": datetime.now().isoformat(),
                "metadata": {"token": "abc123"}
            }
            store.save(test_state)
            assert filepath.exists()

            # Test load
            loaded = store.load()
            assert loaded["authenticated"] is True
            assert loaded["metadata"]["token"] == "abc123"

    def test_nonexistent_file(self):
        store = FileStateStore("nonexistent.json")
        assert store.load() == {}

class TestStateManager:
    def test_basic_state(self):
        manager = StateManager()
        assert isinstance(manager.state, SessionState)

    def test_state_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileStateStore(Path(tmpdir) / "state.json")
            manager = StateManager(store)

            # Test updates
            manager.update(authenticated=True)
            assert manager.state.authenticated is True

            # Test persistence
            new_manager = StateManager(store)
            assert new_manager.state.authenticated is True

    def test_datetime_handling(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileStateStore(Path(tmpdir) / "state.json")
            manager = StateManager(store)

            now = datetime.now()
            manager.update(lastrequest=now)

            # Test reload
            new_manager = StateManager(store)
            assert new_manager.state.lastrequest.isoformat() == now.isoformat()
