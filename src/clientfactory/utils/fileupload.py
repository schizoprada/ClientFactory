# ~/clientfactory/utils/fileupload.py
from __future__ import annotations
import os
import mimetypes
import typing as t
from dataclasses import dataclass
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
from clientfactory.utils.request import Request, RequestMethod

@dataclass
class UploadConfig:
    """Configuration for file uploads"""
    chunk_size: int = 1024 * 1024  # 1MB chunks
    allowresumable: bool = True
    maxretries: int = 3
    timeout: float = 300.0  # 5 minutes
    progresscallback: t.Optional[t.Callable[[int, int], None]] = None  # current, total

class FileUpload:
    """
    Handles file upload preparation and request creation.
    Supports both direct multipart uploads and presigned URL uploads.
    """

    def __init__(self, config: t.Optional[UploadConfig] = None):
        self.config = config or UploadConfig()
        self._openfiles = []  # Track open file handles

    def _openfile(self, file: t.Union[str, t.BinaryIO], content_type: t.Optional[str] = None) -> t.Tuple[str, t.BinaryIO, str]:
        """Open file and return (filename, fileobject, content_type)"""
        if isinstance(file, str):
            filename = os.path.basename(file)
            content_type = content_type or mimetypes.guess_type(file)[0] or 'application/octet-stream'
            fileobj = open(file, 'rb')
            self._openfiles.append(fileobj)  # Track for cleanup
            return filename, fileobj, content_type
        else:
            filename = getattr(file, 'name', 'unnamed')
            if not content_type:
                raise ValueError("content_type must be provided when passing file object")
            return filename, file, content_type

    def _cleanup(self):
        """Close any tracked file handles"""
        for f in self._openfiles:
            try:
                f.close()
            except:
                pass
        self._openfiles.clear()

    def multipart(
        self,
        url: str,
        files: t.Dict[str, t.Union[str, t.Tuple[str, t.BinaryIO, str]]],
        fields: t.Optional[t.Dict[str, str]] = None
    ) -> Request:
        """
        Create a multipart form upload request

        Args:
            url: Upload endpoint
            files: Dict of field name -> filepath or (filename, file object, content type)
            fields: Additional form fields to include
        """
        try:
            formdata = fields.copy() if fields else {}

            # Process files
            for field, file_info in files.items():
                if isinstance(file_info, str):
                    filename, fileobj, content_type = self._openfile(file_info)
                    formdata[field] = (filename, fileobj, content_type)
                else:
                    formdata[field] = file_info

            # Create encoder
            encoder = MultipartEncoder(fields=formdata)

            if self.config.progresscallback:
                encoder = MultipartEncoderMonitor(
                    encoder,
                    lambda m: self.config.progresscallback(m.bytes_read, m.len)
                )

            # Create request
            request = Request(
                method=RequestMethod.POST,
                url=url,
                data=encoder,
                headers={'Content-Type': encoder.content_type},
                config=self.config
            )

            # Attach cleanup to request
            request._filecleanup = self._cleanup
            return request

        except Exception:
            self._cleanup()
            raise

    def presigned(
        self,
        url: str,
        file: t.Union[str, t.BinaryIO],
        fields: t.Dict[str, str],
        content_type: t.Optional[str] = None
    ) -> Request:
        """
        Create a request for uploading to a presigned URL

        Args:
            url: Presigned URL
            file: File path or file object to upload
            fields: Required fields from presigned URL response
            content_type: Optional content type, will be guessed if not provided
        """
        try:
            # Open file
            filename, fileobj, determinedtype = self._openfile(file, content_type)

            # Prepare form fields
            formfields = [
                *[(k, v) for k, v in fields.items()],
                ('Content-Type', determinedtype),
                ('file', (filename, fileobj, determinedtype))
            ]

            encoder = MultipartEncoder(fields=formfields)

            if self.config.progresscallback:
                encoder = MultipartEncoderMonitor(
                    encoder,
                    lambda m: self.config.progresscallback(m.bytes_read, m.len)
                )

            request = Request(
                method=RequestMethod.POST,
                url=url,
                data=encoder,
                headers={'Content-Type': encoder.content_type},
                config=self.config
            )

            # Attach cleanup to request
            request._filecleanup = self._cleanup
            return request

        except Exception:
            self._cleanup()
            raise
