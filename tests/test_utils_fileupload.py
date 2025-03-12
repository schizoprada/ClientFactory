# ~/clientfactory/tests/test_utils_fileupload.py
from __future__ import annotations
import os
import unittest
import tempfile
import typing as t
from io import BytesIO
from unittest.mock import Mock, patch
from requests_toolbelt.multipart.encoder import MultipartEncoder
from utils.fileupload import FileUpload, UploadConfig
from utils.request import RequestMethod

class TestFileUpload(unittest.TestCase):
    def setUp(self):
        self.uploader = FileUpload()

        # Create a temporary test file
        self.test_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        self.test_file.write(b'test content')
        self.test_file.close()

        self.progress_callback = Mock()

    def tearDown(self):
        # Clean up temporary file
        try:
            os.unlink(self.test_file.name)
        except:
            pass

    def test_default_config(self):
        uploader = FileUpload()
        self.assertEqual(uploader.config.chunk_size, 1024 * 1024)
        self.assertTrue(uploader.config.allowresumable)
        self.assertEqual(uploader.config.maxretries, 3)
        self.assertEqual(uploader.config.timeout, 300.0)
        self.assertIsNone(uploader.config.progresscallback)

    def test_custom_config(self):
        config = UploadConfig(
            chunk_size=2048,
            allowresumable=False,
            maxretries=5,
            timeout=600.0,
            progresscallback=lambda x, y: None
        )
        uploader = FileUpload(config)
        self.assertEqual(uploader.config, config)

    def test_multipart_with_filepath(self):
        """Test multipart upload with file path"""
        request = self.uploader.multipart(
            url="http://example.com/upload",
            files={"file": self.test_file.name}
        )

        self.assertEqual(request.method, RequestMethod.POST)
        self.assertEqual(request.url, "http://example.com/upload")
        self.assertIsInstance(request.data, MultipartEncoder)
        self.assertIn("Content-Type", request.headers)
        self.assertTrue(request.headers["Content-Type"].startswith("multipart/form-data; boundary="))

    def test_multipart_with_file_tuple(self):
        """Test multipart upload with file tuple"""
        file_data = BytesIO(b"content")
        file_tuple = ("test.txt", file_data, "text/plain")
        request = self.uploader.multipart(
            url="http://example.com/upload",
            files={"file": file_tuple}
        )

        self.assertEqual(request.method, RequestMethod.POST)
        self.assertIsInstance(request.data, MultipartEncoder)
        self.assertIn("Content-Type", request.headers)

    def test_multipart_with_additional_fields(self):
        """Test multipart upload with additional form fields"""
        fields = {"field1": "value1", "field2": "value2"}
        request = self.uploader.multipart(
            url="http://example.com/upload",
            files={"file": self.test_file.name},
            fields=fields
        )

        self.assertIsInstance(request.data, MultipartEncoder)
        for field in fields:
            self.assertIn(field, dict(request.data.fields))

    def test_presigned_with_filepath(self):
        """Test presigned URL upload with file path"""
        fields = {
            "key": "test-key",
            "policy": "test-policy",
            "x-amz-credential": "test-cred"
        }
        request = self.uploader.presigned(
            url="http://example.com/presigned",
            file=self.test_file.name,
            fields=fields
        )

        self.assertEqual(request.method, RequestMethod.POST)
        self.assertEqual(request.url, "http://example.com/presigned")
        self.assertIsInstance(request.data, MultipartEncoder)

        # Convert multipart fields to dict for easier testing
        field_dict = dict(request.data.fields)
        for field in fields:
            self.assertIn(field, field_dict)

    def test_presigned_with_file_object_and_content_type(self):
        """Test presigned URL upload with file object and content type"""
        file_obj = BytesIO(b"test content")
        file_obj.name = "test.txt"  # Add name attribute
        fields = {"key": "test-key"}
        request = self.uploader.presigned(
            url="http://example.com/presigned",
            file=file_obj,
            fields=fields,
            content_type="text/plain"
        )
        self.assertIsInstance(request.data, MultipartEncoder)

    def test_presigned_with_file_object_no_content_type(self):
        """Test presigned URL upload with file object but no content type"""
        file_obj = BytesIO(b"test content")
        fields = {"key": "test-key"}

        with self.assertRaises(ValueError) as context:
            self.uploader.presigned(
                url="http://example.com/presigned",
                file=file_obj,
                fields=fields
            )
        self.assertIn("content_type must be provided", str(context.exception))

    def test_progress_callback(self):
        """Test progress callback is properly set up"""
        config = UploadConfig(progresscallback=self.progress_callback)
        uploader = FileUpload(config)

        request = uploader.multipart(
            url="http://example.com/upload",
            files={"file": self.test_file.name}
        )

        # Ensure the MultipartEncoderMonitor is set up with our callback
        self.assertTrue(hasattr(request.data, 'callback'))

        # Simulate some data being read
        request.data.bytes_read = 50
        request.data.len = 100
        request.data.callback(request.data)

        # Verify callback was called with correct arguments
        self.progress_callback.assert_called_once_with(50, 100)

if __name__ == '__main__':
    unittest.main()
