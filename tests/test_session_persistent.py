# ~/clientfactory/tests/test_session_persistent.py
import unittest
import tempfile
import os
import pickle
from pathlib import Path
from cryptography.fernet import Fernet

from session.persistent import (
    DiskPersist, MemoryPersist, PersistConfig,
    PersistenceError, persist
)

class TestPersistence(unittest.TestCase):
    """Test session persistence functionality"""

    def setUp(self):
        """Setup test fixtures"""
        # Create temp directory for test files
        self.tempdir = tempfile.mkdtemp()
        self.persistpath = os.path.join(self.tempdir, "test-persist")

        # Test data
        self.testdata = {
            "cookies": {"sessionid": "abc123"},
            "timestamp": 1234567890
        }

    def tearDown(self):
        """Cleanup test files"""
        import shutil
        shutil.rmtree(self.tempdir)

    def test_memory_persist(self):
        """Test in-memory persistence"""
        storage = MemoryPersist()

        # Test save and load
        storage.save(self.testdata)
        loaded = storage.load()
        self.assertEqual(loaded, self.testdata)

        # Test clear
        storage.clear()
        self.assertIsNone(storage.load())

    def test_disk_persist_unencrypted(self):
        """Test unencrypted disk persistence"""
        config = PersistConfig(
            path=self.persistpath,
            encrypt=False
        )
        storage = DiskPersist(config)

        # Test save
        storage.save(self.testdata)
        self.assertTrue(os.path.exists(self.persistpath))

        # Verify raw data is pickled but not encrypted
        with open(self.persistpath, "rb") as f:
            raw = f.read()
        unpickled = pickle.loads(raw)
        self.assertEqual(unpickled, self.testdata)

        # Test load
        loaded = storage.load()
        self.assertEqual(loaded, self.testdata)

        # Test clear
        storage.clear()
        self.assertFalse(os.path.exists(self.persistpath))

    def test_disk_persist_encrypted(self):
        """Test encrypted disk persistence"""
        key = Fernet.generate_key()
        config = PersistConfig(
            path=self.persistpath,
            encrypt=True,
            key=key
        )
        storage = DiskPersist(config)

        # Test save
        storage.save(self.testdata)
        self.assertTrue(os.path.exists(self.persistpath))

        # Verify data is encrypted
        with open(self.persistpath, "rb") as f:
            raw = f.read()
        with self.assertRaises(pickle.UnpicklingError):
            pickle.loads(raw)

        # Test load with same key
        loaded = storage.load()
        self.assertEqual(loaded, self.testdata)

        # Test load with different key
        other_config = PersistConfig(
            path=self.persistpath,
            encrypt=True,
            key=Fernet.generate_key()
        )
        other_storage = DiskPersist(other_config)
        with self.assertRaises(PersistenceError):
            other_storage.load()

    def test_persist_factory(self):
        """Test persist factory function"""
        # Test with encryption
        storage = persist(self.persistpath, encrypt=True)
        self.assertIsInstance(storage, DiskPersist)
        self.assertTrue(storage.config.encrypt)
        self.assertIsNotNone(storage.config.key)

        # Test without encryption
        storage = persist(self.persistpath, encrypt=False)
        self.assertIsInstance(storage, DiskPersist)
        self.assertFalse(storage.config.encrypt)
        self.assertIsNone(storage.config.key)

    def test_directory_creation(self):
        """Test automatic directory creation"""
        nested_path = os.path.join(self.tempdir, "nested", "path", "test-persist")
        storage = persist(nested_path)

        storage.save(self.testdata)
        self.assertTrue(os.path.exists(nested_path))

        loaded = storage.load()
        self.assertEqual(loaded, self.testdata)

    def test_error_handling(self):
        """Test error conditions"""
        storage = persist(self.persistpath)

        # Test load nonexistent file
        self.assertIsNone(storage.load())

        # Test save to unwriteable location
        with self.assertRaises(PersistenceError):
            storage = persist("/root/unauthorized/path")
            storage.save(self.testdata)

        # Test load corrupted data
        storage = persist(self.persistpath, encrypt=False)
        with open(self.persistpath, "wb") as f:
            f.write(b"corrupted data")
        with self.assertRaises(PersistenceError):
            storage.load()

    def test_path_expansion(self):
        """Test path expansion for home directory"""
        home_path = "~/test-persist"
        storage = persist(home_path)

        expanded = str(Path(home_path).expanduser())
        self.assertEqual(storage.config.path, home_path)

        # Verify expanded path is used for operations
        storage.save(self.testdata)
        self.assertTrue(os.path.exists(expanded))

        loaded = storage.load()
        self.assertEqual(loaded, self.testdata)

if __name__ == '__main__':
    unittest.main()
