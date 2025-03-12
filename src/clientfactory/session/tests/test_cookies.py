# ~/ClientFactory/src/clientfactory/session/tests/test_cookies.py
import pytest
import tempfile
from pathlib import Path
from clientfactory.session.cookies.core import Cookie, CookieManager
from clientfactory.session.cookies.generators import StaticCookieGenerator, DynamicCookieGenerator

class TestCookie:
    def test_cookie_creation(self):
        cookie = Cookie(name="test", value="value")
        assert cookie.name == "test"
        assert cookie.value == "value"
        assert cookie.secure is False
        assert cookie.httponly is False

    def test_cookie_fromstring(self):
        cookiestr = "sessionid=abc123; Domain=example.com; Path=/; Secure; HttpOnly"
        cookie = Cookie.fromstring(cookiestr)
        assert cookie.name == "sessionid"
        assert cookie.value == "abc123"
        assert cookie.domain == "example.com"
        assert cookie.path == "/"
        assert cookie.secure is True
        assert cookie.httponly is True

    def test_cookie_toheader(self):
        cookie = Cookie(
            name="sessionid",
            value="abc123",
            domain="example.com",
            path="/",
            secure=True,
            httponly=True
        )
        header = cookie.toheader()
        assert "sessionid=abc123" in header
        assert "Domain=example.com" in header
        assert "Path=/" in header
        assert "Secure" in header  # Changed from "Secure=True"
        assert "HttpOnly" in header  # Changed from "HttpOnly=True"

class TestCookieManager:
    def test_basic_manager(self):
        manager = CookieManager()
        assert manager.cookies == {}
        assert manager.persist is False
        assert manager.storepath is None

    def test_static_cookies(self):
        manager = CookieManager(
            static={"test": "value"}
        )
        cookies = manager.generate()
        assert "test" in cookies
        assert cookies["test"].value == "value"

    def test_dynamic_cookies(self):
        counter = 0
        def count_gen(_):
            nonlocal counter
            counter += 1
            return str(counter)

        manager = CookieManager(
            dynamic={"counter": count_gen}
        )
        cookies1 = manager.generate()
        cookies2 = manager.generate()
        assert cookies1["counter"].value == "1"
        assert cookies2["counter"].value == "2"

    def test_cookie_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "cookies.json"

            # Create manager and add cookies
            manager1 = CookieManager(
                persist=True,
                storepath=str(store_path)
            )
            manager1.update({
                "test": Cookie(
                    name="test",
                    value="value",
                    secure=True
                )
            })

            # Create new manager and verify cookies loaded
            manager2 = CookieManager(
                persist=True,
                storepath=str(store_path)
            )
            assert "test" in manager2.cookies
            assert manager2.cookies["test"].value == "value"
            assert manager2.cookies["test"].secure is True

    def test_cookie_update(self):
        manager = CookieManager()

        # Test string value update
        manager.update({"simple": "value"})
        assert isinstance(manager.cookies["simple"], Cookie)
        assert manager.cookies["simple"].value == "value"

        # Test Cookie object update
        manager.update({
            "complex": Cookie(
                name="complex",
                value="test",
                secure=True
            )
        })
        assert manager.cookies["complex"].secure is True

    def test_cookie_clear(self):
        manager = CookieManager(
            static={"test": "value"}
        )
        manager.update({"session": "abc123"})
        assert len(manager.cookies) > 0

        manager.clear()
        assert len(manager.cookies) == 0

    def test_asdict_and_asheaders(self):
        manager = CookieManager()
        manager.update({
            "test": Cookie(
                name="test",
                value="value",
                secure=True
            )
        })

        # Test asdict
        cookie_dict = manager.asdict()
        assert cookie_dict == {"test": "value"}

        # Test asheaders
        headers = manager.asheaders()
        assert len(headers) == 1
        assert "test=value" in headers[0]
        assert "Secure" in headers[0]  # Changed from "Secure=True"


from clientfactory.session.cookies.persistence import JSONPersistence, PicklePersistence

class TestPersistence:
    def test_json_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "cookies.json"
            persistence = JSONPersistence(filepath)

            # Create test cookies
            cookies = {
                "session": Cookie(
                    name="session",
                    value="abc123",
                    domain="example.com",
                    secure=True,
                    httponly=True
                ),
                "simple": Cookie(
                    name="simple",
                    value="test"
                )
            }

            # Test save
            persistence.save(cookies)
            assert filepath.exists()

            # Test load
            loaded = persistence.load()
            assert len(loaded) == 2
            assert loaded["session"].value == "abc123"
            assert loaded["session"].domain == "example.com"
            assert loaded["session"].secure is True
            assert loaded["session"].httponly is True
            assert loaded["simple"].value == "test"

    def test_pickle_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "cookies.pickle"
            persistence = PicklePersistence(filepath)

            # Create test cookies
            cookies = {
                "session": Cookie(
                    name="session",
                    value="abc123",
                    secure=True
                )
            }

            # Test save
            persistence.save(cookies)
            assert filepath.exists()

            # Test load
            loaded = persistence.load()
            assert len(loaded) == 1
            assert loaded["session"].value == "abc123"
            assert loaded["session"].secure is True

    def test_persistence_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "nonexistent.json"
            persistence = JSONPersistence(filepath)

            # Should return empty dict when file doesn't exist
            loaded = persistence.load()
            assert isinstance(loaded, dict)
            assert len(loaded) == 0

    def test_persistence_invalid_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "invalid.json"

            # Create invalid JSON file
            with open(filepath, 'wb') as f:
                f.write(b'{"invalid": json}')

            persistence = JSONPersistence(filepath)

            # Should handle invalid data gracefully
            loaded = persistence.load()
            assert isinstance(loaded, dict)
            assert len(loaded) == 0

    def test_persistence_directory_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test nested directory creation
            filepath = Path(tmpdir) / "nested" / "dir" / "cookies.json"
            persistence = JSONPersistence(filepath)

            cookies = {
                "test": Cookie(name="test", value="value")
            }

            # Should create directories if they don't exist
            persistence.save(cookies)
            assert filepath.exists()

            # Verify data was saved correctly
            loaded = persistence.load()
            assert loaded["test"].value == "value"
