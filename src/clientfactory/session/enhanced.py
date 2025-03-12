# ~/ClientFactory/src/clientfactory/session/enhanced.py
import typing as t
from datetime import datetime
from dataclasses import dataclass, field
from clientfactory.session.base import BaseSession, SessionConfig
from clientfactory.session.headers import Headers
from clientfactory.session.cookies import CookieManager
from clientfactory.session.state import StateManager, FileStateStore
from clientfactory.utils import Request, Response, RequestMethod
from loguru import logger as log

@dataclass
class EnhancedSession(BaseSession):
    """Session with state management"""
    headers: Headers = field(default_factory=Headers)
    cookies: CookieManager = field(default_factory=CookieManager)
    state: t.Optional[StateManager] = None

    def __post_init__(self):
        # Initialize base session with merged config
        config = SessionConfig(
            headers=self.headers.generate(),
            cookies=self.cookies.generate() if self.cookies else {}
        )
        super().__init__(config=config)

    def __prep__(self, request: Request) -> Request:
        """Enhanced request preparation"""
        # Update request with current headers/cookies
        headers = self.headers.generate()
        headers.update(request.headers)
        request.headers = headers

        if self.cookies:
            cookies = self.cookies.generate()
            cookies.update(request.cookies)
            request.cookies = cookies

        # Update state
        if self.state:
            self.state.update(last_request=datetime.now())

        # Let base session do final preparation
        return super().__prep__(request)

    def send(self, request: Request) -> Response:
        """Enhanced request sending with response handling"""
        response = super().send(request)

        # Handle response cookies
        if self.cookies and response.cookies:
            self.cookies.update(response.cookies)

        # Update session headers from config
        self.config.headers.update(self.headers.generate())

        return response

    def initialrequest(self, url: str, **kwargs) -> Response:
        """Perform initial session setup request"""
        extractmap = kwargs.pop('extract', None)
        response = self.send(Request(
            method=RequestMethod.GET,
            url=url,
            **kwargs
        ))

        # Extract and store important values
        if extractmap:
            for key, path in extractmap.items():
                if value := response.extract(path):
                    if self.state:
                        self.state.update(metadata={key: value})

        return response
