# ~/ClientFactory/tests/unit/session/test_headers.py
"""Tests for header management"""
import pytest
import time
from clientfactory.session import Headers

def test_headers_static():
    """Test static headers"""
    headers = Headers(static={
        "User-Agent": "TestClient/1.0",
        "Accept": "application/json"
    })

    result = headers.get()
    assert result["User-Agent"] == "TestClient/1.0"
    assert result["Accept"] == "application/json"

def test_headers_dynamic():
    """Test dynamic headers"""
    counter = 0
    def get_count():
        nonlocal counter
        counter += 1
        return str(counter)

    headers = Headers(
        static={"Static": "value"},
        dynamic={"Counter": get_count}
    )

    first = headers.get()
    second = headers.get()

    assert first["Counter"] == "1"
    assert second["Counter"] == "2"
    assert first["Static"] == second["Static"]

def test_headers_update():
    """Test header updates"""
    headers = Headers()
    headers.update({"New": "Header"})

    result = headers.get()
    assert result["New"] == "Header"

def test_headers_add_dynamic():
    """Test adding dynamic headers"""
    import time
    headers = Headers()
    headers.plusdynamic("Time", lambda: str(time.time_ns()))  # Use nanoseconds for higher precision

    first = headers.get()["Time"]
    time.sleep(0.001)  # Short sleep
    second = headers.get()["Time"]

    assert first != second
