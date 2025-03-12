# ~/clientfactory/auth/session.py
from __future__ import annotations
import typing as t
from dataclasses import dataclass, field
import pickle
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests as rq
from clientfactory.auth.base import BaseAuth, AuthState, AuthError
from clientfactory.utils.request import Request

@dataclass
class BrowserAction:
    """Represents a browser automation action"""
    type: str  # fill, click, wait, etc
    selector: str
    value: t.Optional[str] = None
    wait: float = 0.0

class BrowserLogin:
    """Handles browser-based authentication flows"""
    def __init__(self,
                 url: str,
                 actions: list[BrowserAction],
                 successcheck: t.Callable[[webdriver.Remote], bool]):
        self.url = url
        self.actions = actions
        self.successcheck = successcheck
        self._driver: t.Optional[webdriver.Remote] = None

    def execute(self) -> dict:
        """Execute login flow and return captured cookies"""
        try:
            self._driver = webdriver.Chrome()  # Could make driver configurable
            self._driver.get(self.url)

            for action in self.actions:
                if action.wait:
                    WebDriverWait(self._driver, action.wait).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, action.selector))
                    )

                if action.type == "fill":
                    elem = self._driver.find_element(By.CSS_SELECTOR, action.selector)
                    elem.send_keys(action.value)
                elif action.type == "click":
                    elem = self._driver.find_element(By.CSS_SELECTOR, action.selector)
                    elem.click()
                elif action.type == "wait":
                    WebDriverWait(self._driver, float(action.value or "10")).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, action.selector))
                    )

            if not self.successcheck(self._driver):
                raise AuthError("Browser login flow did not succeed")

            return {c["name"]: c["value"] for c in self._driver.get_cookies()}

        finally:
            if self._driver:
                self._driver.quit()

@dataclass
class SessionConfig:
    """Configuration for session authentication"""
    loginurl: str
    formdata: dict = field(default_factory=dict)
    browserlogin: t.Optional[BrowserLogin] = None
    persistpath: t.Optional[str] = None
    extraheaders: dict = field(default_factory=dict)

class SessionAuth(BaseAuth):
    """
    Session-based authentication handler supporting both form and browser-based flows.
    Can persist authenticated sessions to disk.

    Usage:
        # Simple form login
        auth = SessionAuth.withcreds(
            loginurl="https://api.example.com/login",
            username="user",
            password="pass"
        )

        # Complex form with CSRF
        auth = SessionAuth.withform(
            loginurl="https://api.example.com/login",
            formdata={
                "username": "user",
                "password": "pass",
                "_csrf": "token"
            }
        )

        # Browser automation
        auth = SessionAuth.withbrowser(
            loginurl="https://api.example.com/login",
            actions=[
                BrowserAction("fill", "#email", "user@email.com"),
                BrowserAction("fill", "#password", "pass"),
                BrowserAction("click", ".submit")
            ],
            successcheck=lambda driver: "dashboard" in driver.current_url
        )
    """

    def __init__(self, config: SessionConfig):
        super().__init__()
        self.config = config
        self._cookies: dict = {}

    @classmethod
    def withcreds(cls,
                  loginurl: str,
                  username: str,
                  password: str,
                  **kwargs) -> SessionAuth:
        """Create auth handler with username/password"""
        config = SessionConfig(
            loginurl=loginurl,
            formdata={"username": username, "password": password},
            **kwargs
        )
        return cls(config)

    @classmethod
    def withform(cls,
                 loginurl: str,
                 formdata: dict,
                 **kwargs) -> SessionAuth:
        """Create auth handler with custom form data"""
        config = SessionConfig(
            loginurl=loginurl,
            formdata=formdata,
            **kwargs
        )
        return cls(config)

    @classmethod
    def withbrowser(cls,
                   loginurl: str,
                   actions: list[BrowserAction],
                   successcheck: t.Callable[[webdriver.Remote], bool],
                   **kwargs) -> SessionAuth:
        """Create auth handler with browser automation"""
        browserlogin = BrowserLogin(loginurl, actions, successcheck)
        config = SessionConfig(
            loginurl=loginurl,
            browserlogin=browserlogin,
            **kwargs
        )
        return cls(config)

    def authenticate(self) -> AuthState:
        """Authenticate using configured method"""
        # Try loading persisted session first
        if self.config.persistpath and self._loadsession():
            return self.state

        # Fall back to browser automation if configured
        if self.config.browserlogin:
            self._cookies = self.config.browserlogin.execute()
        else:
            # Standard form submission
            try:
                response = rq.post(
                    self.config.loginurl,
                    data=self.config.formdata,
                    headers=self.config.extraheaders,
                    allow_redirects=True
                )
                response.raise_for_status()
                self._cookies = response.cookies.get_dict()
            except rq.RequestException as e:
                raise AuthError(f"Form authentication failed: {str(e)}")

        if not self._cookies:
            raise AuthError("No session cookies received")

        # Update state
        self.state.authenticated = True
        self.state.metadata["cookies"] = self._cookies

        # Persist if configured
        if self.config.persistpath:
            self._savesession()

        return self.state

    def prepare(self, request: Request) -> Request:
        """Add session cookies to request"""
        if not self._cookies:
            raise AuthError("No active session")

        return request.WITH(cookies=self._cookies)

    def _savesession(self) -> None:
        """Save session data to disk"""
        if not self.config.persistpath:
            return

        path = Path(self.config.persistpath).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump(self._cookies, f)

    def _loadsession(self) -> bool:
        """Try to load saved session data"""
        if not self.config.persistpath:
            return False

        path = Path(self.config.persistpath).expanduser()
        if not path.exists():
            return False

        try:
            with open(path, "rb") as f:
                self._cookies = pickle.load(f)
                self.state.authenticated = True
                self.state.metadata["cookies"] = self._cookies
                return True
        except (pickle.UnpicklingError, EOFError):
            return False
