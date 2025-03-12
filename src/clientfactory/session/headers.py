# ~/ClientFactory/src/clientfactory/session/headers.py
from __future__ import annotations
import os, sys, platform, random, typing as t
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from datetime import datetime
from loguru import logger as log

class HeaderGenerator(ABC):
    """Base abstract class for header generators"""
    @abstractmethod
    def generate(self) -> dict[str, str]:
        """generate header key-value pair"""
        pass


class UserAgentGenerator(HeaderGenerator):
    """Generates realistic User-Agent headers"""
    class VERSIONS:
        # should find a way to expand or make this dynamic
        class BROWSERS:
            CHROME = ['106.0.0.0', '107.0.0.0', '108.0.0.0', '109.0.0.0']
            FIREFOX = ['106.0', '107.0', '108.0', '109.0']
            SAFARI = ['15.6.1', '16.0', '16.1']
        class OS:
            WINDOWS = ['10.0', '11.0']
            MAC = ['10_15_7', '11_6_8', '12_6']
            LINUX = ['Ubuntu', 'Debian', 'Fedora']

    def __init__(self, browser: str = "chrome", usesys: bool = True, os: t.Optional[str] = None, osversion: t.Optional[str] = None, browserversion: t.Optional[str] = None):
        self.browser = browser.lower()
        self.usesys = usesys
        self.os = os.lower() if os else None
        self.osversion = osversion
        self.browserversion = browserversion
        self._setupsystem()

    def _setupsystem(self) -> None:
        """Setup system information if usesys=True"""
        versionmap = {
            'windows': platform.version(),
            'mac': platform.mac_ver()[0].replace('.', '_'),
            'linux': platform.release()
        }
        if self.usesys:
            system = platform.system().lower()
            if self.os is None:
                self.os = system
            if self.osversion is None:
                self.osversion = versionmap.get(self.os)
            log.debug(f"UserAgentGenerator._setupsystem | OS: [{self.os}] | Version: [{self.osversion}]")

    def _platformstring(self) -> str:
        """Generate platform-specific string"""
        formatmap = {
            'windows': lambda v: f"Windows NT {v or random.choice(self.VERSIONS.OS.WINDOWS)}",
            'mac': lambda v: f"Macintosh; Intel Mac OS X {v or random.choice(self.VERSIONS.OS.MAC)}",
            'linux': lambda v: f"X11; Linux x86_64; {v or random.choice(self.VERSIONS.OS.LINUX)}"
        }
        return formatmap.get(self.os, formatmap['windows'])(self.osversion)

    def _construct(self) -> str:
        """Construct User-Agent string"""
        if not self.browserversion:
            self.browserversion = random.choice(
                getattr(
                    self.VERSIONS.BROWSERS,
                    self.browser.upper(),
                    self.VERSIONS.BROWSERS.CHROME
                )
            )
            log.debug(f"") # add a debug
        constructionmap = {
            'chrome': lambda p, v: (
                f"Mozilla/5.0 ({p}) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{v} Safari/537.36"
            ),
            'firefox': lambda p, v: (
                f"Mozilla/5.0 ({p}; rv:{v}) "
                f"Gecko/20100101 Firefox/{v}"
            ),
            'safari': lambda p, v: (
                f"Mozilla/5.0 ({p}) "
                f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
                f"Version/{v} Safari/605.1.15"
            )
        }
        return constructionmap.get(self.browser, constructionmap['chrome'])(self._platformstring(), self.browserversion)

    def generate(self) -> dict[str, str]:
        """Generate User-Agent header"""
        return {"User-Agent": self._construct()}


@dataclass
class HeaderRotation:
    """Configuration for header rotation"""
    values: list[str]
    interval: int = 0
    _lastrotation: float = field(default_factory=lambda:datetime.now().timestamp())
    _currentindex: int = -1 # first rotation goes to 0

    def shouldrotate(self) -> bool:
        """Check if rotation should occur"""
        if self.interval == 0: return True
        return ((datetime.now().timestamp() - self._lastrotation) >= self.interval)

    def rotate(self) -> str:
        """Get current or next value based on rotation interval"""
        if self.shouldrotate():
            self._currentindex = ((self._currentindex + 1) % len(self.values))
            self._lastrotation = datetime.now().timestamp()
        return self.values[self._currentindex]


@dataclass
class Headers:
    """
    Header management system supporting static, dynamic, and generated headers

    Usage:
        headers = Headers(
            static={"accept": "application/json"},
            dynamic={
                "x-csrf": lambda ctx: ctx.get("csrf_token")
            },
            rotate={
                "x-client-id": HeaderRotation(["id1", "id2", "id3"])
            },
            random=True  # Enables default UA generation
        )
    """
    static: dict[str, str] = field(default_factory=dict)
    dynamic: dict[str, t.Callable[[dict], str]] = field(default_factory=dict)
    rotate: dict[str, HeaderRotation] = field(default_factory=dict) # maybe handle instances where its [str, list] or [str, tuple[...]] to instantiate `HeaderRotation` dynamically?
    random: bool = False
    generators: list[HeaderGenerator] = field(default_factory=list) # same as the comment above regarding `HeaderRotation`
    _context: dict = field(default_factory=dict)

    def __post_init__(self):
        """Initialize generators based on configuration"""
        if self.random and not any(isinstance(g, UserAgentGenerator) for g in self.generators):
            self.generators.append(UserAgentGenerator())
        log.debug(f"Headers.__post_init__ | Random: {self.random} | Generators: {len(self.generators)}")

    def generate(self, context: t.Optional[dict] = None) -> dict[str, str]:
        """Generate complete set of headers"""
        if context:
            self._context.update(context)

        headers = self.static.copy()

        # Add dynamic headers
        for key, fn in self.dynamic.items():
            try:
                headers[key] = fn(self._context)
            except Exception as e:
                log.error(f"Headers.generate | Dynamic header error [{key}]: {str(e)}")

        # Add rotating headers
        for key, rotation in self.rotate.items():
            try:
                headers[key] = rotation.rotate()
            except Exception as e:
                log.error(f"Headers.generate | Rotation header error [{key}]: {str(e)}")

        # Add generated headers
        for generator in self.generators:
            try:
                headers.update(generator.generate())
            except Exception as e:
                log.error(f"Headers.generate | Generator error [{generator.__class__.__name__}]: {str(e)}")

        log.debug(f"Headers.generate | Generated headers: {headers}")
        return headers

    def update(self, headers: dict[str, str]) -> None:
        """Update static headers"""
        self.static.update(headers)
        log.debug(f"Headers.update | Updated static headers: {self.static}")

    def adddynamic(self, key: str, generator: t.Callable[[dict], str]) -> None:
        """Add dynamic header generator"""
        self.dynamic[key] = generator
        log.debug(f"Headers.adddynamic | Added dynamic header: {key}")

    def addrotation(self, key: str, values: list[str], interval: int = 0) -> None:
        """Add rotating header"""
        self.rotate[key] = HeaderRotation(values, interval)
        log.debug(f"Headers.addrotation | Added rotation header: {key} | Values: {len(values)} | Interval: {interval}")

    def addgenerator(self, generator: HeaderGenerator) -> None:
        """Add custom header generator"""
        self.generators.append(generator)
        log.debug(f"Headers.addgenerator | Added generator: {generator.__class__.__name__}")

    def getcontext(self) -> dict:
        """Get current context"""
        return self._context.copy()

    def setcontext(self, context: dict) -> None:
        """Set new context"""
        self._context = context.copy()
        log.debug(f"Headers.set_context | Updated context: {self._context}")

    def updatecontext(self, context: dict) -> None:
        """Update existing context"""
        self._context.update(context)
        log.debug(f"Headers.update_context | Updated context: {self._context}")

    def __call__(self, **kwargs) -> dict[str, str]:
        return self.generate(**kwargs)
