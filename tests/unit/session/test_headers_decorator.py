# ~/ClientFactory/tests/unit/session/test_headers_decorator.py
"""Tests for headers decorator"""
import pytest
from clientfactory.decorators.session import headers
from clientfactory.session.headers import Headers

def test_headers_decorator_basic():
    """Test basic headers decorator usage"""
    @headers
    class TestHeaders:
        static = {"User-Agent": "Test/1.0"}

    h = TestHeaders()
    assert h.get()["User-Agent"] == "Test/1.0"

def test_headers_decorator_with_args():
    """Test headers decorator with arguments"""
    @headers(static={"User-Agent": "Test/1.0"})
    class TestHeaders:
        pass

    h = TestHeaders()
    assert h.get()["User-Agent"] == "Test/1.0"

def test_headers_decorator_dynamic():
    """Test headers decorator with dynamic headers"""
    counter = 0
    def get_count():
        nonlocal counter
        counter += 1
        return str(counter)

    @headers(
        static={"User-Agent": "Test/1.0"},
        dynamic={"X-Counter": get_count}
    )
    class TestHeaders:
        pass

    h = TestHeaders()
    headers1 = h.get()
    headers2 = h.get()

    assert headers1["User-Agent"] == "Test/1.0"
    assert headers1["X-Counter"] == "1"
    assert headers2["X-Counter"] == "2"

def test_headers_decorator_update():
    """Test updating headers after creation"""
    import traceback
    from clientfactory.decorators.session import headers
    print("\nDebugging headers decorator:")
    print(f"headers import: {headers}")

    try:
        @headers(static={"User-Agent": "Test/1.0"})
        class TestHeaders:
            pass
    except Exception as e:
        print(f"Exception during decoration: {e}")
        print("Traceback:")
        traceback.print_exc()
        raise

    h = TestHeaders()
    h.update({"Accept": "application/json"})

    result = h.get()
    print(f"Final headers: {result}")
    assert result["User-Agent"] == "Test/1.0"
    assert result["Accept"] == "application/json"
