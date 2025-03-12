# ~/ClientFactory/src/clientfactory/session/cookies/core.py
from __future__ import annotations
import json, typing as t
import http.cookies
from pathlib import Path
from dataclasses import dataclass, field, fields
from clientfactory.session.cookies.generators import (
    StaticCookieGenerator, DynamicCookieGenerator
)

@dataclass
class Cookie:
    """HTTP Cookie representation"""
    name: str
    value: str
    domain: t.Optional[str] = None
    path: t.Optional[str] = None
    expires: t.Optional[str] = None
    secure: bool = False
    httponly: bool = False
    samesite: t.Optional[str] = None

    @classmethod
    def fromstring(cls, string: str) -> "Cookie":
        """Parse cookie from string"""
        simple = http.cookies.SimpleCookie()
        simple.load(string)
        morsel = next(iter(simple.values()))
        elsenone = lambda x: morsel[x] if x in morsel else None
        return cls(
            name = morsel.key,
            value = morsel.value,
            domain = elsenone("domain"),
            path = elsenone("path"),
            expires = elsenone("expires"),
            samesite = elsenone("samesite"),
            secure = ("secure" in morsel),
            httponly = ("httponly" in morsel)
        )

    def toheader(self) -> str:
        """Convert to Set-Cookie header format"""
        camel = {
            'httponly': 'HttpOnly',
            'samesite': 'SameSite'
        }
        parts = [f"{self.name}={self.value}"]
        for f in fields(self):
            if f.name not in ('name', 'value'):  # skip name/value as they're handled
                if (v := getattr(self, f.name, None)) is not None:
                    name = camel.get(f.name, f.name.capitalize())
                    if isinstance(v, bool) and v:
                        parts.append(name)  # boolean flags appear without values
                    else:
                        parts.append(f"{name}={v}")
        return "; ".join(parts)



class CookieStore:
    """Handles cookie persistence and state management"""

    def __init__(self, filepath: t.Optional[str | Path] = None):
        self.filepath = Path(filepath) if filepath else None
        self._cookies: dict = {}

        if self.filepath is not None:
            self.load()

    def load(self) -> None:
        """Load cookies from storage"""
        if self.filepath and self.filepath.exists():
            try:
                with open(self.filepath) as f:
                    self._cookies = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                # Start with empty state on error
                # # add configuration for custom exception handling, for now we can just pass
                self._cookies = {}

    def save(self) -> None:
        """Save current cookies to storage"""
        if self.filepath:
            try:
                self.filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(self.filepath, 'w') as f:
                    json.dump(self._cookies, f)
            except IOError:
                pass  # add configuration for custom exception handling, for now we can just pass

    def update(self, cookies: dict) -> None:
        """Update stored cookies and persist changes"""
        self._cookies.update(cookies)
        self.save()

    @property
    def cookies(self) -> dict:
        """Get current cookie state"""
        return self._cookies.copy()

    def clear(self) -> None:
        """Clear all stored cookies"""
        self._cookies.clear()
        self.save()


@dataclass
class CookieManager:
    cookies: t.Optional[t.Iterable[Cookie]] = field(default_factory=dict)
    static: t.Optional[dict] = field(default=None)
    dynamic: t.Optional[t.Dict[str, t.Callable]] = field(default=None)
    persist: bool = field(default=False)
    storepath: t.Optional[str] =field(default=None)


    def __post_init__(self):
        self._staticgen = StaticCookieGenerator(self.static or {})
        self._dynamicgen = DynamicCookieGenerator(self.dynamic or {})
        self._store = CookieStore(self.storepath) if self.persist else None

        if self._store:
            for name, data in self._store.cookies.items():
                if isinstance(data, dict):
                    self.cookies[name] = Cookie(name=name, **data)
                else:
                    self.cookies[name] = Cookie(name=name, value=data)

    def generate(self, context: t.Optional[dict] = {}) -> t.Dict[str, Cookie]:
        """Generate all cookies combining static, dynamic and stored values"""
        result = self.cookies.copy()
        for name, value in self._staticgen.generate().items():
            result[name] = value if isinstance(value, str) else value.value
        for name, value in self._dynamicgen.generate(context).items():
            result[name] = value if isinstance(value, str) else value.value
        return result

    def update(self, cookies: t.Dict[str, t.Union[str, Cookie]]) -> None:
        """Update cookie state"""
        for name, value in cookies.items():
            if isinstance(value, str):
                self.cookies[name] = Cookie(name=name, value=value)
            elif isinstance(value, Cookie):
                self.cookies[name] = value

        if self._store:
            self._store.update({
                name: {
                    f.name: getattr(cookie, f.name)
                    for f in fields(cookie)
                    if f.name != 'name' and getattr(cookie, f.name) is not None
                }
                for name, cookie in self.cookies.items()
            })

    def clear(self) -> None:
        """Clear all cookies"""
        self.cookies.clear()
        if self._store:
            self._store.clear()

    def get(self, name:str) -> t.Optional[Cookie]:
        """Get cookie by name"""
        return self.cookies.get(name)

    def asdict(self) -> dict[str, str]:
        """Convert all cookies to simple name-value pairs"""
        return {name: cookie.value for name, cookie in self.cookies.items()}

    def asheaders(self) -> list[str]:
        """Convert all cookies to Set-Cookie headers"""
        return [cookie.toheader() for cookie in self.cookies.values()]
