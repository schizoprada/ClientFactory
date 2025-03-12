# ~/clientfactory/tests/test_auth_session.py
# ~/clientfactory/tests/test_auth_session.py
import unittest
from unittest.mock import Mock, patch, MagicMock
import pickle
from pathlib import Path
import tempfile
import os
from selenium.webdriver.common.by import By
import requests as rq
from auth.session import (
    SessionAuth, SessionConfig, BrowserAction,
    BrowserLogin, AuthError
)
from utils.request import Request, RequestMethod

class TestSessionAuth(unittest.TestCase):
    """Test session-based authentication functionality"""

    def setUp(self):
        """Setup test fixtures"""
        self.loginurl = "https://api.test/login"
        self.username = "testuser"
        self.password = "testpass"

        # Temporary file for session persistence tests
        self.tempdir = tempfile.mkdtemp()
        self.persistpath = os.path.join(self.tempdir, "test-session")

    def tearDown(self):
        """Cleanup test files"""
        import shutil
        shutil.rmtree(self.tempdir)

    def test_creds_init(self):
        """Test basic credentials initialization"""
        auth = SessionAuth.withcreds(
            loginurl=self.loginurl,
            username=self.username,
            password=self.password
        )

        self.assertEqual(auth.config.loginurl, self.loginurl)
        self.assertEqual(auth.config.formdata["username"], self.username)
        self.assertEqual(auth.config.formdata["password"], self.password)

    def test_form_init(self):
        """Test custom form initialization"""
        formdata = {
            "email": "test@test.com",
            "pass": "secret",
            "_csrf": "token123"
        }

        auth = SessionAuth.withform(
            loginurl=self.loginurl,
            formdata=formdata
        )

        self.assertEqual(auth.config.loginurl, self.loginurl)
        self.assertEqual(auth.config.formdata, formdata)

    @patch('selenium.webdriver.Chrome')
    def test_browser_init(self, mock_chrome):
        """Test browser automation initialization"""
        actions = [
            BrowserAction("fill", "#email", "test@test.com"),
            BrowserAction("fill", "#password", "secret"),
            BrowserAction("click", ".submit")
        ]

        def success_check(driver):
            return True

        auth = SessionAuth.withbrowser(
            loginurl=self.loginurl,
            actions=actions,
            successcheck=success_check
        )

        self.assertEqual(auth.config.loginurl, self.loginurl)
        self.assertIsNotNone(auth.config.browserlogin)
        self.assertEqual(len(auth.config.browserlogin.actions), 3)

    @patch('requests.post')
    def test_form_authentication(self, mock_post):
        """Test successful form authentication"""
        mock_response = Mock()
        mock_response.cookies.get_dict.return_value = {"sessionid": "abc123"}
        mock_post.return_value = mock_response

        auth = SessionAuth.withcreds(
            loginurl=self.loginurl,
            username=self.username,
            password=self.password
        )

        state = auth.authenticate()

        self.assertTrue(state.authenticated)
        self.assertEqual(auth._cookies["sessionid"], "abc123")

        # Verify correct request
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], self.loginurl)
        self.assertEqual(call_args[1]["data"]["username"], self.username)

    @patch('requests.post')
    def test_form_authentication_failure(self, mock_post):
        """Test failed form authentication"""
        # Specify a RequestException instead of generic Exception
        mock_post.side_effect = rq.RequestException("Login failed")

        auth = SessionAuth.withcreds(
            loginurl=self.loginurl,
            username=self.username,
            password=self.password
        )

        with self.assertRaises(AuthError):
            auth.authenticate()

    @patch('selenium.webdriver.Chrome')
    def test_browser_authentication(self, mock_chrome):
        """Test browser-based authentication"""
        # Setup mock driver
        mock_driver = MagicMock()
        mock_driver.get_cookies.return_value = [
            {"name": "sessionid", "value": "browser123"}
        ]
        mock_chrome.return_value = mock_driver

        actions = [
            BrowserAction("fill", "#email", "test@test.com"),
            BrowserAction("fill", "#password", "secret"),
            BrowserAction("click", ".submit")
        ]

        auth = SessionAuth.withbrowser(
            loginurl=self.loginurl,
            actions=actions,
            successcheck=lambda d: True
        )

        state = auth.authenticate()

        self.assertTrue(state.authenticated)
        self.assertEqual(auth._cookies["sessionid"], "browser123")

        # Verify browser interactions
        mock_driver.get.assert_called_with(self.loginurl)
        self.assertEqual(mock_driver.find_element.call_count, 3)
        mock_driver.quit.assert_called_once()

    def test_session_persistence(self):
        """Test session saving and loading"""
        # Create auth with persistence
        auth = SessionAuth.withcreds(
            loginurl=self.loginurl,
            username=self.username,
            password=self.password,
            persistpath=self.persistpath
        )

        # Set some test cookies
        auth._cookies = {"sessionid": "test123"}
        auth.state.authenticated = True

        # Save session
        auth._savesession()

        # Verify file exists
        self.assertTrue(os.path.exists(self.persistpath))

        # Create new auth instance
        auth2 = SessionAuth.withcreds(
            loginurl=self.loginurl,
            username=self.username,
            password=self.password,
            persistpath=self.persistpath
        )

        # Load session
        success = auth2._loadsession()

        self.assertTrue(success)
        self.assertTrue(auth2.state.authenticated)
        self.assertEqual(auth2._cookies["sessionid"], "test123")

    def test_request_preparation(self):
        """Test cookie addition to requests"""
        auth = SessionAuth.withcreds(
            loginurl=self.loginurl,
            username=self.username,
            password=self.password
        )

        # Set test cookies
        auth._cookies = {"sessionid": "test123", "csrftoken": "abc"}
        auth.state.authenticated = True

        request = Request(method=RequestMethod.GET, url="https://api.test/resource")
        prepped = auth.prepare(request)

        self.assertEqual(prepped.cookies["sessionid"], "test123")
        self.assertEqual(prepped.cookies["csrftoken"], "abc")

    def test_error_handling(self):
        """Test various error conditions"""
        auth = SessionAuth.withcreds(
            loginurl=self.loginurl,
            username=self.username,
            password=self.password
        )

        # Test prepare without authentication
        request = Request(method=RequestMethod.GET, url="https://api.test/resource")
        with self.assertRaises(AuthError):
            auth.prepare(request)

        # Test invalid session file
        auth.config.persistpath = self.persistpath
        with open(self.persistpath, "wb") as f:
            f.write(b"invalid pickle data")
        self.assertFalse(auth._loadsession())

    @patch('selenium.webdriver.Chrome')
    def test_browser_action_wait(self, mock_chrome):
        """Test browser action wait functionality"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        # Add mock cookies to prevent "No session cookies" error
        mock_driver.get_cookies.return_value = [
            {"name": "sessionid", "value": "test123"}
        ]

        actions = [
            BrowserAction("wait", "#loading", wait=1.0),
            BrowserAction("click", "#submit")
        ]

        auth = SessionAuth.withbrowser(
            loginurl=self.loginurl,
            actions=actions,
            successcheck=lambda d: True
        )

        state = auth.authenticate()

        # Verify state and cookies
        self.assertTrue(state.authenticated)
        self.assertEqual(auth._cookies["sessionid"], "test123")

        # Verify WebDriverWait was used
        mock_driver.find_element.assert_called_with(By.CSS_SELECTOR, "#submit")
        # Verify driver was closed
        mock_driver.quit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
