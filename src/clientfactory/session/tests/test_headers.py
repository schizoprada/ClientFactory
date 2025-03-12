# ~/ClientFactory/src/clientfactory/session/tests/test_headers.py
import pytest
from datetime import datetime, timedelta
import time
from clientfactory.session.headers import (
    HeaderGenerator, UserAgentGenerator,
    HeaderRotation, Headers
)

class TestUserAgentGenerator:
    def test_default_generation(self):
        gen = UserAgentGenerator()
        ua = gen.generate()["User-Agent"]
        assert "Mozilla/5.0" in ua
        assert any(browser in ua for browser in ["Chrome", "Firefox", "Safari"])

    def test_specific_browser(self):
        gen = UserAgentGenerator(browser="firefox")
        ua = gen.generate()["User-Agent"]
        assert "Firefox" in ua

    def test_system_info(self):
        gen = UserAgentGenerator(usesys=True)
        ua = gen.generate()["User-Agent"]
        # Should contain actual system info
        assert ua  # Basic existence check

    def test_custom_versions(self):
        gen = UserAgentGenerator(
            browser="chrome",
            browserversion="100.0.0.0",
            os="windows",
            osversion="10.0"
        )
        ua = gen.generate()["User-Agent"]
        assert "Chrome/100.0.0.0" in ua
        assert "Windows NT 10.0" in ua

class TestHeaderRotation:
    def test_immediate_rotation(self):
        rotation = HeaderRotation(["a", "b", "c"])
        assert rotation.rotate() == "a"
        assert rotation.rotate() == "b"
        assert rotation.rotate() == "c"
        assert rotation.rotate() == "a"  # wraps around

    def test_interval_rotation(self):
        rotation = HeaderRotation(["a", "b"], interval=1)
        first = rotation.rotate()
        assert rotation.rotate() == first  # shouldn't rotate yet
        time.sleep(1.1)  # wait for interval
        assert rotation.rotate() != first  # should rotate now

class TestHeaders:
    def test_static_headers(self):
        headers = Headers(static={"accept": "application/json"})
        assert headers.generate()["accept"] == "application/json"

    def test_dynamic_headers(self):
        headers = Headers(
            dynamic={"x-time": lambda ctx: str(ctx.get("time", 0))}
        )
        result = headers.generate({"time": 123})
        assert result["x-time"] == "123"

    def test_rotation_headers(self):
        headers = Headers(
            rotate={"x-key": HeaderRotation(["a", "b"])}
        )
        first = headers.generate()["x-key"]
        second = headers.generate()["x-key"]
        assert first != second

    def test_random_ua(self):
        headers = Headers(random=True)
        result = headers.generate()
        assert "User-Agent" in result
        assert "Mozilla/5.0" in result["User-Agent"]

    def test_context_management(self):
        headers = Headers(
            dynamic={"x-token": lambda ctx: ctx.get("token", "")}
        )
        headers.setcontext({"token": "123"})
        assert headers.generate()["x-token"] == "123"

        headers.updatecontext({"token": "456"})
        assert headers.generate()["x-token"] == "456"

    def test_multiple_generators(self):
        class CustomGen(HeaderGenerator):
            def generate(self) -> dict[str, str]:
                return {"X-Custom": "value"}

        headers = Headers(
            random=True,
            generators=[CustomGen()]
        )
        result = headers.generate()
        assert "User-Agent" in result
        assert "X-Custom" in result

    def test_error_handling(self):
        headers = Headers(
            dynamic={"x-error": lambda ctx: ctx["nonexistent"]}
        )
        result = headers.generate()  # should not raise
        assert "x-error" not in result

class TestHeadersIntegration:
    def test_full_configuration(self):
        headers = Headers(
            static={"accept": "application/json"},
            dynamic={"x-time": lambda ctx: str(ctx.get("time", 0))},
            rotate={"x-key": HeaderRotation(["a", "b"])},
            random=True
        )

        result = headers.generate({"time": 123})
        assert result["accept"] == "application/json"
        assert result["x-time"] == "123"
        assert result["x-key"] in ["a", "b"]
        assert "User-Agent" in result

    def test_header_updates(self):
        headers = Headers(static={"initial": "value"})
        headers.update({"new": "value"})
        headers.adddynamic("dynamic", lambda ctx: "dynamic_value")
        headers.addrotation("rotating", ["1", "2"])

        result = headers.generate()
        assert result["initial"] == "value"
        assert result["new"] == "value"
        assert result["dynamic"] == "dynamic_value"
        assert result["rotating"] in ["1", "2"]
